import os
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiohttp import web
import database as db

# Настройки
TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USERS = [int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x]
WARSAW_TZ = pytz.timezone('Europe/Warsaw')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Логика расчета периода ЗП ---

def get_payday(year, month):
    """Рассчитывает дату ЗП: 10 число или пятница, если 10-е - это Сб или Вс"""
    dt = datetime(year, month, 10)
    # 5 - Суббота, 6 - Воскресенье
    if dt.weekday() == 5: 
        return dt - timedelta(days=1) # Пятница 9-е
    if dt.weekday() == 6:
        return dt - timedelta(days=2) # Пятница 8-е
    return dt

def get_current_cycle():
    """Определяет начало и конец текущего финансового месяца"""
    now = datetime.now(WARSAW_TZ).replace(tzinfo=None)
    this_month_payday = get_payday(now.year, now.month)
    
    if now <= this_month_payday:
        # Мы еще в цикле, который начался после ЗП прошлого месяца
        last_month = now.replace(day=1) - timedelta(days=1)
        start_date = get_payday(last_month.year, last_month.month) + timedelta(days=1)
        end_date = this_month_payday
    else:
        # Мы в цикле, который начался после ЗП этого месяца
        next_month = (now.replace(day=28) + timedelta(days=5)).replace(day=1)
        start_date = this_month_payday + timedelta(days=1)
        end_date = get_payday(next_month.year, next_month.month)
        
    return start_date.strftime("%Y-%m-%d 00:00:00"), end_date.strftime("%Y-%m-%d 23:59:59")

# --- Интерфейс ---

def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🍎 Еда")
    builder.button(text="📦 Прочее")
    builder.button(text="📊 Отчет")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS: return
    await message.answer("Cześć! Введи сумму (только цифры), а потом выбери категорию.", reply_markup=main_kb())

user_temp_data = {}

@dp.message(F.text.regexp(r'^\d+(\.\d+)?$'))
async def get_amount(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS: return
    user_temp_data[message.from_user.id] = float(message.text)
    await message.answer(f"Сумма {message.text} zł принята. Категория?", reply_markup=main_kb())

@dp.message(F.text.in_(["🍎 Еда", "📦 Прочее"]))
async def get_category(message: types.Message):
    uid = message.from_user.id
    if uid not in ALLOWED_USERS or uid not in user_temp_data: return
    
    amount = user_temp_data.pop(uid)
    category = "Еда" if "Еда" in message.text else "Прочее"
    username = message.from_user.first_name
    
    db.add_expense(uid, username, category, amount)
    
    # Уведомляем ОБОИХ пользователей
    notif_text = f"💰 <b>Новая трата!</b>\n👤 Кто: {username}\n💵 Сумма: {amount} zł\n📂 Категория: {category}"
    for user_id in ALLOWED_USERS:
        try:
            await bot.send_message(user_id, notif_text, parse_mode="HTML")
        except:
            pass

@dp.message(F.text == "📊 Отчет")
async def show_report(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS: return
    
    start, end = get_current_cycle()
    detailed = db.get_detailed_report(start, end)
    totals = db.get_total_by_category(start, end)
    
    msg = f"📅 <b>Период:</b> {start[:10]} — {end[:10]}\n\n"
    
    if not detailed:
        await message.answer(msg + "За этот период трат пока нет.")
        return

    msg += "<b>👤 По пользователям:</b>\n"
    for user, cat, amt in detailed:
        msg += f"• {user}: {amt:.2f} zł ({cat})\n"
    
    msg += "\n<b>📈 Итого по категориям:</b>\n"
    grand_total = 0
    for cat, amt in totals:
        msg += f"▫️ {cat}: {amt:.2f} zł\n"
        grand_total += amt
        
    msg += f"\nИТОГО: <b>{grand_total:.2f} zł</b>"
    
    await message.answer(msg, parse_mode="HTML")

# --- Запуск ---

async def handle(request): return web.Response(text="Bot is alive!")

async def main():
    db.init_db()
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
