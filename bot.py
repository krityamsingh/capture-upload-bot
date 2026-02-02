import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import List, Optional

import aiohttp
import aiofiles
from aiohttp_socks import ProxyConnector
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

COOKIE_FILE = "cookies.txt"
PROXY_FILE = "data.txt"
DOWNLOAD_DIR = "downloads"

TERA_REGEX = r"(https?://(?:www\.)?(?:terabox\.com|terabox\.app|1024tera\.com|terafileshare\.com)/\S+)"

APP_ID = 250528
MAX_RETRIES = 3
MAX_CONCURRENT = 3
MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("TeraboxBot")

# ================= SESSION =================
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
            return
        cookies = []
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    cookies.append(line)
        self.cookies = "; ".join(cookies)

    def load_proxies(self):
        if not Path(PROXY_FILE).exists():
            return
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            self.proxies = [p.strip() for p in f if p.strip()]

    async def test_proxy(self, proxy: str) -> bool:
        try:
            connector = ProxyConnector.from_url(proxy)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=8)
            ) as s:
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
                    return proxy

            return None

    async def acquire(self) -> bool:
        async with self.lock:
            if self.active < MAX_CONCURRENT:
                self.active += 1
                return True
            return False

    def release(self):
        self.active = max(0, self.active - 1)

session = SessionManager()

# ================= TERABOX CORE =================
class Terabox:
    @staticmethod
    async def extract_files(link: str):
        last_error = None

        for _ in range(MAX_RETRIES):
            proxy = await session.get_proxy()
            if not proxy:
                raise Exception("No working proxy")

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Cookie": session.cookies,
                "Referer": "https://www.terabox.com/"
            }

            try:
                connector = ProxyConnector.from_url(proxy)
                async with aiohttp.ClientSession(
                    connector=connector,
                    headers=headers
                ) as s:

                    async with s.get(link, allow_redirects=True) as r:
                        html = await r.text()

                    surl = re.search(r'"surl"\s*:\s*"([^"]+)"', html)
                    if not surl:
                        raise Exception("surl not found")

                    list_api = (
                        f"https://www.terabox.com/share/list"
                        f"?app_id={APP_ID}&shorturl={surl.group(1)}&root=1"
                    )

                    async with s.get(list_api) as r:
                        data = await r.json()

                    files = []
                    for item in data.get("list", []):
                        if item.get("isdir") == 0:
                            files.append({
                                "fs_id": item["fs_id"],
                                "name": item["server_filename"],
                                "size": item["size"]
                            })

                    if not files:
                        raise Exception("No files found")

                    return files

            except Exception as e:
                session.working_proxy = None
                last_error = e

        raise Exception(last_error)

    @staticmethod
    async def download(fs_id: int, name: str, msg: Message):
        for _ in range(MAX_RETRIES):
            proxy = await session.get_proxy()
            if not proxy:
                raise Exception("Proxy lost")

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Cookie": session.cookies,
                "Referer": "https://www.terabox.com/"
            }

            try:
                connector = ProxyConnector.from_url(proxy)
                async with aiohttp.ClientSession(
                    connector=connector,
                    headers=headers
                ) as s:

                    dlink_api = (
                        f"https://www.terabox.com/api/download"
                        f"?app_id={APP_ID}&fs_id={fs_id}"
                    )

                    async with s.get(dlink_api) as r:
                        d = await r.json()

                    url = d.get("dlink")
                    if not url:
                        raise Exception("No dlink")

                    path = f"{DOWNLOAD_DIR}/{int(time.time())}_{name}"

                    async with s.get(url) as r:
                        if r.status != 200:
                            raise Exception("Download failed")

                        size = int(r.headers.get("content-length", 0))
                        if size > MAX_SIZE:
                            raise Exception("File too large")

                        async with aiofiles.open(path, "wb") as f:
                            async for chunk in r.content.iter_chunked(1024 * 1024):
                                await f.write(chunk)

                    return path

            except Exception:
                session.working_proxy = None
                await asyncio.sleep(1)

        raise Exception("Download failed")

# ================= BOT =================
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply_text(
        "🤖 Terabox Downloader\n\n"
        "Send any Terabox / Terafileshare link.\n"
        "Supports folders & multiple files."
    )

@app.on_message(filters.private & filters.text)
async def handle(_, m: Message):
    match = re.search(TERA_REGEX, m.text)
    if not match:
        return

    if not await session.acquire():
        await m.reply_text("⏳ Too many active downloads")
        return

    status = await m.reply_text("🔍 Analyzing link…")

    try:
        files = await Terabox.extract_files(match.group(1))
        await status.edit_text(f"📁 Found {len(files)} file(s)")

        for i, f in enumerate(files, 1):
            await status.edit_text(f"⬇️ {i}/{len(files)} — {f['name']}")
            path = await Terabox.download(f["fs_id"], f["name"], status)
            await m.reply_document(path, caption=f"✅ {f['name']}")
            os.remove(path)

        await status.edit_text("✅ All files sent")

    except Exception as e:
        await status.edit_text(f"❌ {e}")

    finally:
        session.release()

# ================= MAIN =================
async def main():
    if not API_ID or not API_HASH or not BOT_TOKEN:
        log.error("Missing API credentials")
        return

    await app.start()
    me = await app.get_me()
    log.info(f"🤖 Started as @{me.username}")

    try:
        await idle()
    finally:
        await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
