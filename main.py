import os
import asyncio
import re
import logging
from datetime import datetime, timedelta
import pytz
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext  # Было FContext, исправил на FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiohttp import web
import database as db

# Настройка логов, чтобы видеть ошибки в панели Render
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USERS = [int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x]
WARSAW_TZ = pytz.timezone('Europe/Warsaw')

bot = Bot(token=TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    waiting_for_input = State()

# --- Логика расчета периода ЗП ---
def get_payday(year, month):
    dt = datetime(year, month, 10)
    if dt.weekday() == 5: return dt - timedelta(days=1)
    if dt.weekday() == 6: return dt - timedelta(days=2)
    return dt

def get_current_cycle():
    now = datetime.now(WARSAW_TZ).replace(tzinfo=None)
    this_payday = get_payday(now.year, now.month)
    if now <= this_payday:
        last = now.replace(day=1) - timedelta(days=1)
        start = get_payday(last.year, last.month) + timedelta(days=1)
        end = this_payday
    else:
        nxt = (now.replace(day=28) + timedelta(days=5)).replace(day=1)
        start = this_payday + timedelta(days=1)
        end = get_payday(nxt.year, nxt.month)
    return start.strftime("%Y-%m-%d 00:00:00"), end.strftime("%Y-%m-%d 23:59:59")

# --- Клавиатуры ---
def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🍎 Jedzenie"), builder.button(text="📦 Inne")
    builder.button(text="📊 Raport"), builder.button(text="🕒 Historia")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def delete_kb(expense_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Usuń", callback_data=f"del_{expense_id}")
    return builder.as_markup()

# --- Обработчики ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS: return
    await message.answer("Cześć! Wybierz kategorię:", reply_markup=main_kb())

@dp.message(F.text.in_(["🍎 Jedzenie", "📦 Inne"]))
async def select_category(message: types.Message, state: FSMContext): # Исправлено на FSMContext
    if message.from_user.id not in ALLOWED_USERS: return
    category = "Jedzenie" if "Jedzenie" in message.text else "Inne"
    await state.update_data(selected_category=category)
    await state.set_state(Form.waiting_for_input)
    await message.answer(f"Wybrano: {category}. Wpisz kwotę i info (np. '50 biedronka'):")

@dp.message(Form.waiting_for_input)
async def process_expense(message: types.Message, state: FSMContext): # Исправлено на FSMContext
    if message.from_user.id not in ALLOWED_USERS: return
    
    match = re.match(r"^(\d+(?:[.,]\d+)?)(.*)", message.text.strip())
    if not match:
        await message.answer("Błąd! Wpisz najpierw liczbę, a potem info. Spróbuj jeszcze raz:")
        return

    amount = float(match.group(1).replace(',', '.'))
    description = match.group(2).strip() or "Brak opisu"
    
    data = await state.get_data()
    category = data.get("selected_category")
    username = message.from_user.first_name

    exp_id = db.add_expense(message.from_user.id, username, category, amount, description)
    await state.clear()

    notif = f"✅ <b>{username}</b> dodał(a):\n💰 {amount} zł ({category})\n📝 {description}"
    for uid in ALLOWED_USERS:
        try:
            await bot.send_message(uid, notif, parse_mode="HTML", reply_markup=delete_kb(exp_id))
        except:
            pass

@dp.callback_query(F.data.startswith("del_"))
async def delete_item(callback: types.CallbackQuery):
    exp_id = int(callback.data.split("_")[1])
    db.delete_expense(exp_id)
    await callback.message.edit_text("<s>" + callback.message.text + "</s>\n\n🗑 <b>Usunięto!</b>", parse_mode="HTML")

@dp.message(F.text == "📊 Raport")
async def show_report(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS: return
    start, end = get_current_cycle()
    detailed = db.get_detailed_report(start, end)
    totals = db.get_total_by_category(start, end)
    
    msg = f"📅 <b>Okres:</b> {start[:10]} — {end[:10]}\n\n"
    msg += "<b>👤 Użytkownicy:</b>\n"
    if not detailed:
        msg += "Brak wpisów в tym okresie."
    else:
        for user, cat, amt in detailed:
            msg += f"• {user}: {amt:.2f} zł ({cat})\n"
    
    msg += "\n<b>📈 Razem kategorie:</b>\n"
    grand = sum(amt for cat, amt in totals)
    for cat, amt in totals:
        msg += f"▫️ {cat}: {amt:.2f} zł\n"
    msg += f"\nSUMA: <b>{grand:.2f} zł</b>"
    await message.answer(msg, parse_mode="HTML")

@dp.message(F.text == "🕒 Historia")
async def show_history(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS: return
    history = db.get_last_history(10)
    if not history:
        await message.answer("Historia jest pusta.")
        return
    
    await message.answer("<b>Ostatnie 10 wpisów:</b>", parse_mode="HTML")
    for eid, user, cat, amt, desc in history:
        text = f"{user}: {amt} zł ({cat})\n📝 {desc}"
        await message.answer(text, reply_markup=delete_kb(eid))

# --- Веб-сервер для Render ---
async def handle(request):
    return web.Response(text="Bot is alive!")

async def main():
    db.init_db()
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Запуск сервера на порту 8080
    await web.TCPSite(runner, "0.0.0.0", 8080).start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
