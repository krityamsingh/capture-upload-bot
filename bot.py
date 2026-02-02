import os
import re
import time
import random
import logging
import aiohttp

from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp_socks import ProxyConnector
from aiohttp import ClientTimeout, ClientConnectorError

# ───────────────── LOGGING ─────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("TeraboxBot")

# ───────────────── CONFIG ─────────────────
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

DOWNLOAD_DIR = "downloads"
PROXY_FILE = "proxies.txt"
COOKIE_FILE = "cookies.txt"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ───────────────── LOAD PROXIES ─────────────────
def load_proxies():
    if not os.path.exists(PROXY_FILE):
        return []
    with open(PROXY_FILE, "r") as f:
        return [p.strip() for p in f if p.strip()]

ALL_PROXIES = load_proxies()

# ───────────────── PYROGRAM CLIENT ─────────────────
app = Client(
    "terabox_downloader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

active_users = set()

# ───────────────── TERABOX ENGINE ─────────────────
class Terabox:
    def __init__(self):
        self.cookies = {}
        self.good_proxy = None   # 🔥 TEMP CACHED WORKING PROXY
        self.load_cookies()

    # -------- Cookies --------
    def load_cookies(self):
        if not os.path.exists(COOKIE_FILE):
            log.warning("cookies.txt not found")
            return

        with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7 and "tera" in parts[0]:
                    self.cookies[parts[5]] = parts[6]

        log.info(f"Loaded {len(self.cookies)} cookies")

    # -------- Normalize link --------
    def normalize_link(self, text: str):
        m = re.search(r"/s/([A-Za-z0-9_-]+)", text)
        if not m:
            return None
        return f"https://www.1024tera.com/s/{m.group(1)}"

    # -------- Create session --------
    async def make_session(self, proxy: str):
        connector = ProxyConnector.from_url(proxy)
        return aiohttp.ClientSession(
            connector=connector,
            cookies=self.cookies,
            timeout=ClientTimeout(total=300),
            headers={
                "User-Agent": "Mozilla/5.0 Chrome/120 Safari/537.36"
            }
        )

    # -------- Test proxy --------
    async def test_proxy(self, proxy: str, test_url: str):
        try:
            session = await self.make_session(proxy)
            async with session.get(test_url) as r:
                ok = r.status == 200
            await session.close()
            return ok
        except Exception:
            return False

    # -------- Find working proxy --------
    async def get_working_proxy(self, test_url: str):
        if self.good_proxy:
            return self.good_proxy

        random.shuffle(ALL_PROXIES)
        log.info("Testing proxies...")

        for proxy in ALL_PROXIES:
            if await self.test_proxy(proxy, test_url):
                self.good_proxy = proxy
                log.info(f"Working proxy found: {proxy}")
                return proxy

        return None

    # -------- Extract download URL --------
    async def extract_download_url(self, share_link: str):
        safe_url = self.normalize_link(share_link)
        if not safe_url:
            return None

        proxy = await self.get_working_proxy(safe_url)
        if not proxy:
            return None

        try:
            session = await self.make_session(proxy)
            async with session.get(safe_url) as r:
                html = await r.text()
            await session.close()

            m = re.search(r'"dlink":"([^"]+)"', html)
            if not m:
                return None

            return m.group(1).replace("\\/", "/")

        except ClientConnectorError:
            log.warning("Cached proxy failed, resetting")
            self.good_proxy = None
            return None

    # -------- Download file --------
    async def download(self, url: str, path: str):
        proxy = self.good_proxy
        if not proxy:
            return False

        try:
            session = await self.make_session(proxy)
            async with session.get(url) as r:
                if r.status != 200:
                    return False
                with open(path, "wb") as f:
                    async for chunk in r.content.iter_chunked(1024 * 1024):
                        f.write(chunk)
            await session.close()
            return True

        except Exception:
            self.good_proxy = None
            return False


tera = Terabox()

# ───────────────── HELPERS ─────────────────
def is_terabox_link(text: str):
    return any(x in text.lower() for x in (
        "terabox.com", "1024tera.com", "terafileshare.com"
    ))

# ───────────────── BOT HANDLER ─────────────────
@app.on_message(filters.private & filters.text)
async def handle(_, msg: Message):
    text = msg.text.strip()
    user_id = msg.from_user.id

    if not is_terabox_link(text):
        return

    if user_id in active_users:
        await msg.reply_text("⏳ Download already in progress.")
        return

    active_users.add(user_id)
    status = await msg.reply_text("🔍 Analyzing proxies...")

    try:
        dlink = await tera.extract_download_url(text)
        if not dlink:
            await status.edit_text("❌ No working proxy found.")
            return

        filename = f"{user_id}_{int(time.time())}.mp4"
        filepath = f"{DOWNLOAD_DIR}/{filename}"

        await status.edit_text("⬇️ Downloading video...")
        ok = await tera.download(dlink, filepath)
        if not ok:
            await status.edit_text("❌ Download failed.")
            return

        await status.edit_text("📤 Sending video to your DM...")
        await app.send_video(
            chat_id=user_id,
            video=filepath,
            supports_streaming=True,
            caption="✅ Terabox download complete"
        )

        await status.edit_text("✅ Done!")
        os.remove(filepath)

    finally:
        active_users.discard(user_id)

# ───────────────── START ─────────────────
if __name__ == "__main__":
    log.info("Starting Terabox bot (proxy auto-analysis enabled)")
    app.run()
