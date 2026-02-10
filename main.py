import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiohttp import web
import database as db

# Читаем данные из переменных окружения (для безопасности)
TOKEN = os.getenv("BOT_TOKEN")
# ID пользователей через запятую в настройках, преобразуем в список int
ALLOWED_USERS = [int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Логика Бота ---

def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🍎 Еда"), builder.button(text="📦 Прочее")
    builder.button(text="📊 Отчет")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS: return
    await message.answer("Введите сумму, затем выберите категорию.", reply_markup=main_kb())

user_temp_data = {}

@dp.message(F.text.regexp(r'^\d+(\.\d+)?$'))
async def get_amount(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS: return
    user_temp_data[message.from_user.id] = float(message.text)
    await message.answer(f"Сумма {message.text} принята. Категория?", reply_markup=main_kb())

@dp.message(F.text.in_(["🍎 Еда", "📦 Прочее"]))
async def get_category(message: types.Message):
    uid = message.from_user.id
    if uid not in ALLOWED_USERS or uid not in user_temp_data: return
    
    amount = user_temp_data.pop(uid)
    category = "Еда" if "Еда" in message.text else "Прочее"
    db.add_expense(uid, message.from_user.first_name, category, amount)
    
    msg = f"✅ {message.from_user.first_name} добавил {amount}р ({category})"
    for user_id in ALLOWED_USERS:
        try: await bot.send_message(user_id, msg)
        except: pass

@dp.message(F.text == "📊 Отчет")
async def show_report(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS: return
    totals = db.get_total()
    history = db.get_history()
    
    res = "<b>💰 Итоги:</b>\n" + "\n".join([f"• {c}: {v}р" for c, v in totals])
    res += "\n\n<b>Последние записи:</b>\n" + "\n".join([f"- {u}: {a}р ({c})" for u, c, a, d in history])
    await message.answer(res, parse_mode="HTML")

# --- Веб-сервер для "оживления" хостинга ---
async def handle(request):
    return web.Response(text="Bot is alive!")

async def main():
    db.init_db()
    # Запуск веб-сервера на порту 8080 (стандарт для Render)
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    asyncio.create_task(site.start())
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())