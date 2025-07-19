import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from bypass import cookie_fresher  # из твоего кода
import logging

TOKEN = "8145614744:AAFSqIjLnxlvEPEhe9e1U_Vbcw6SOBdiHH0"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Обработчик кнопки старт
@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Отправить cookies.txt", callback_data="upload")
    await message.answer("👋 Привет! Отправь мне `cookies.txt`, и я обновлю все куки одним махом 💪", reply_markup=kb.as_markup())

# Обработка загрузки файла
@dp.message(lambda message: message.document and message.document.file_name.endswith("cookies.txt"))
async def handle_file(message: types.Message):
    user_id = message.from_user.id
    input_file_path = f"cookies_{user_id}.txt"
    result_file_path = f"fresh_{user_id}.txt"

    # Сохраняем файл
    file = await bot.download(message.document)
    with open(input_file_path, "wb") as f:
        f.write(file.read())

    await message.answer("🔄 Начинаю обновление cookies...")

    # Обработка кук
    valid, invalid = [], []

    with open(input_file_path, "r", encoding="utf-8") as f:
        cookies = [line.strip() for line in f if "_|WARNING" in line]

    for cookie in cookies:
        new_cookie = cookie_fresher(cookie)
        if new_cookie:
            valid.append(new_cookie)
        else:
            invalid.append(cookie)

    # Сохраняем результат
    with open(result_file_path, "w", encoding="utf-8") as f:
        for new in valid:
            f.write(new + "\n")

    # Формируем отчёт
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"✅ Обновление завершено\n\n"
        f"🕒 Время: {now}\n"
        f"🟢 Валидных: {len(valid)}\n"
        f"🔴 Невалидных: {len(invalid)}\n\n"
        f"📎 Файл: fresh_{user_id}.txt"
    )

    await message.answer_document(FSInputFile(result_file_path), caption=text)

    os.remove(input_file_path)
    os.remove(result_file_path)

# Файл не cookies.txt
@dp.message(lambda message: message.document)
async def not_valid_file(message: types.Message):
    await message.reply("❌ Пожалуйста, загрузи файл с именем `cookies.txt`!")

# Просто текст
@dp.message()
async def text_fallback(message: types.Message):
    await message.reply("📄 Пожалуйста, отправь мне файл `cookies.txt` для обновления кук.")

# Запуск
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
