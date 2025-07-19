import re
import time
import requests
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

API_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Bypass:
    def __init__(self, cookie: str) -> None:
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
                import re
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

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Отправь мне файл .txt с Roblox cookies, я их обновлю.")

@dp.message(F.text)
async def not_a_file(message: Message):
    if not message.document:
        await message.answer("Пожалуйста, отправьте файл .txt с Roblox cookies.")

@dp.message(F.document)
async def handle_file(message: Message):
    if not message.document.file_name.endswith(".txt"):
        await message.answer("Пожалуйста, пришлите именно .txt файл.")
        return

    file_path = f"temp_{message.from_user.id}.txt"
    file = await bot.get_file(message.document.file_id)
    await bot.download_file(file.file_path, destination=file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_cookies = []
    invalid_count = 0
    refreshed_count = 0

    start_time = datetime.now()

    # Обрабатываем все строки, НЕ прерываясь
    for idx, line in enumerate(lines, start=1):
        line = line.strip()
        cookie_match = re.search(r"(_\|WARNING.*)", line)
        if cookie_match:
            old_cookie = cookie_match.group(1)
            new_cookie = cookie_fresher(old_cookie)
            if new_cookie:
                updated_line = line.replace(old_cookie, new_cookie)
                updated_cookies.append(updated_line)
                refreshed_count += 1
            else:
                updated_cookies.append(line)
                invalid_count += 1
        else:
            updated_cookies.append(line)

        # Лог прогресса для дебага
        if idx % 10 == 0:
            print(f"Обработано {idx} куки...")

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = f"RefreshedCookies_{timestamp}.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(updated_cookies))

    await message.answer(f"✅ 1Рефреш завершён за {elapsed:.2f} сек.\n"
                         f"✔️ Обновлено куки: {refreshed_count}\n"
                         f"❌ Не удалось обновить: {invalid_count}")

    await message.answer_document(document=FSInputFile(output_filename), filename=output_filename)

if __name__ == "__main__":
    print("✅ Бот запущен.")
    asyncio.run(dp.start_polling(bot))
