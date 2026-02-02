import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional, List

import aiohttp
import aiofiles
from aiohttp_socks import ProxyConnector
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# ================== CONFIG ==================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

COOKIE_FILE = "cookies.txt"
PROXY_FILE = "data.txt"
DOWNLOAD_DIR = "downloads"

MAX_CONCURRENT_DOWNLOADS = 3
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

TERA_REGEX = r"(https?://(?:www\.)?(?:terabox\.app|terabox\.com|1024tera\.com|terafileshare\.com)/\S+)"

Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("TeraboxBot")

# ================== SESSION MANAGER ==================
class SessionManager:
    def __init__(self):
        self.cookies: Optional[str] = None
        self.proxies: List[str] = []
        self.working_proxy: Optional[str] = None
        self.active = 0
        self.lock = asyncio.Lock()
        self.load_cookies()
        self.load_proxies()

    def load_cookies(self):
        if not Path(COOKIE_FILE).exists():
            log.error("❌ cookies.txt missing")
            return
        cookies = []
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    cookies.append(line)
        self.cookies = "; ".join(cookies) if cookies else None
        log.info(f"✅ Loaded {len(cookies)} cookies")

    def load_proxies(self):
        if not Path(PROXY_FILE).exists():
            log.warning("⚠️ data.txt missing (no proxy)")
            return
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            self.proxies = [p.strip() for p in f if p.strip()]
        log.info(f"✅ Loaded {len(self.proxies)} proxies")

    async def test_proxy(self, proxy: str) -> bool:
        try:
            connector = ProxyConnector.from_url(proxy)
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as s:
                async with s.get("https://httpbin.org/ip") as r:
                    return r.status == 200
        except:
            return False

    async def get_proxy(self) -> Optional[str]:
        async with self.lock:
            if self.working_proxy:
                return self.working_proxy

            for proxy in self.proxies:
                if await self.test_proxy(proxy):
                    self.working_proxy = proxy
                    log.info(f"✅ Using proxy: {proxy}")
                    return proxy

            log.error("❌ No working proxy")
            return None

    async def acquire(self) -> bool:
        async with self.lock:
            if self.active < MAX_CONCURRENT_DOWNLOADS:
                self.active += 1
                return True
            return False

    def release(self):
        self.active = max(0, self.active - 1)

session = SessionManager()

# ================== TERABOX ==================
class Terabox:
    @staticmethod
    async def extract(link: str) -> str:
        proxy = await session.get_proxy()
        if not proxy:
            raise Exception("No proxy available")

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Cookie": session.cookies or "",
            "Referer": "https://www.terabox.com/"
        }

        try:
            connector = ProxyConnector.from_url(proxy)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as s:
                async with s.get(link, allow_redirects=True) as r:
                    html = await r.text()

            patterns = [
                r'"downloadUrl":"([^"]+)"',
                r'"playUrl":"([^"]+)"',
                r'"url":"([^"]+\.mp4[^"]*)"'
            ]

            for p in patterns:
                m = re.search(p, html)
                if m:
                    return m.group(1).replace("\\/", "/")

            raise Exception("Download URL not found")

        except Exception as e:
            session.working_proxy = None
            raise e

    @staticmethod
    async def download(url: str, path: str, msg: Message):
        proxy = await session.get_proxy()
        if not proxy:
            raise Exception("Proxy lost")

        connector = ProxyConnector.from_url(proxy)
        last_update = time.time()

        async with aiohttp.ClientSession(connector=connector) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    raise Exception("Download failed")

                size = int(r.headers.get("content-length", 0))
                if size > MAX_FILE_SIZE:
                    raise Exception("File too large")

                downloaded = 0
                async with aiofiles.open(path, "wb") as f:
                    async for chunk in r.content.iter_chunked(1024 * 1024):
                        await f.write(chunk)
                        downloaded += len(chunk)

                        if time.time() - last_update > 3:
                            await msg.edit_text(
                                f"⬇️ Downloading… {downloaded//(1024*1024)}MB"
                            )
                            last_update = time.time()

# ================== BOT ==================
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply_text(
        "🤖 **Terabox Downloader**\n\n"
        "Send a Terabox link and I’ll download it.\n\n"
        f"Cookies: {'✅' if session.cookies else '❌'}\n"
        f"Proxies: {len(session.proxies)}"
    )

@app.on_message(filters.private & filters.text)
async def handler(_, m: Message):
    match = re.search(TERA_REGEX, m.text)
    if not match:
        return

    if not await session.acquire():
        await m.reply_text("⏳ Too many downloads. Try later.")
        return

    status = await m.reply_text("🔍 Processing link…")
    file_path = None

    try:
        dlink = await Terabox.extract(match.group(1))
        file_path = f"{DOWNLOAD_DIR}/{m.from_user.id}_{int(time.time())}.mp4"

        await status.edit_text("⬇️ Downloading…")
        await Terabox.download(dlink, file_path, status)

        await status.edit_text("📤 Uploading…")
        await m.reply_video(file_path, caption="✅ Download complete")
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ {e}")

    finally:
        session.release()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ================== MAIN ==================
async def main():
    if not API_ID or not API_HASH or not BOT_TOKEN:
        log.error("❌ Missing API credentials")
        return

    await app.start()
    me = await app.get_me()
    log.info(f"🤖 Bot started: @{me.username}")

    try:
        await idle()
    finally:
        await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
