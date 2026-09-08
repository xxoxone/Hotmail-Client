import os

APP_NAME = "MicroTools"
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "55885502#@#")
COOKIE_FILE_PATH = os.path.join(os.path.dirname(__file__), "cookies", "x_cookies.txt")

FB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.113 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,bn-BD;q=0.8,bn;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://limited.facebook.com",
    "Referer": "https://limited.facebook.com/login/identify/?ctx=recover",
    "Sec-Ch-Ua": '"Chromium";v="124", "Android WebView";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?1",
    "Sec-Ch-Ua-Platform": '"Android"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
