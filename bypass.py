import requests
import re
import time
import logging
from datetime import datetime

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

def refresh_cookies():
    # Генерация имени файла с текущей датой
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = f"FreshCookies_{timestamp}.txt"

    # Открытие файлов
    with open("cookies.txt", "r", encoding="utf-8") as infile, open(output_filename, "w", encoding="utf-8") as outfile:
        cookies = infile.readlines()

        for cookie in cookies:
            cookie = cookie.strip()
            if "_|WARNING" in cookie:
                new_cookie = cookie_fresher(cookie)
                if new_cookie:
                    outfile.write(new_cookie + "\n")
                    print(f"✅ Обновлен куки: {cookie[-10:]} -> {new_cookie[-10:]}")
                else:
                    print(f"❌ Не удалось обновить куки: {cookie[-10:]}")
            else:
                print(f"⚠️ Пропущен невалидный куки: {cookie[-10:]}")
    
    print(f"\nРезультаты сохранены в: {output_filename}")

# Запуск
refresh_cookies()
