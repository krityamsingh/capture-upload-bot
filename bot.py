import os
import re
import time
import random
import logging
import aiohttp

from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp_socks import ProxyConnector

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

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ───────────────── LOAD PROXIES ─────────────────
def load_proxies():
    if not os.path.exists(PROXY_FILE):
        return []
    with open(PROXY_FILE, "r") as f:
        return [p.strip() for p in f if p.strip()]

PROXIES = load_proxies()

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
        self.load_cookies()

    def load_cookies(self):
        if not os.path.exists("cookies.txt"):
            log.warning("cookies.txt missing")
            return

        with open("cookies.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7 and "tera" in parts[0]:
                    self.cookies[parts[5]] = parts[6]

        log.info(f"Loaded {len(self.cookies)} cookies")

    def normalize_link(self, text: str):
        m = re.search(r"/s/([A-Za-z0-9_-]+)", text)
        if not m:
            return None
        return f"https://www.1024tera.com/s/{m.group(1)}"

    async def request(self, url: str):
        random.shuffle(PROXIES)

        for proxy in PROXIES:
            try:
                connector = ProxyConnector.from_url(proxy)
                async with aiohttp.ClientSession(
                    connector=connector,
                    cookies=self.cookies,
                    timeout=aiohttp.ClientTimeout(total=600),
                    headers={
                        "User-Agent": "Mozilla/5.0 Chrome/120 Safari/537.36"
                    }
                ) as session:
                    async with session.get(url) as r:
                        if r.status == 200:
                            return await r.text(), session, proxy
            except Exception as e:
                log.warning(f"Proxy failed {proxy}")

        return None, None, None

    async def extract_download_url(self, share_link: str):
        safe = self.normalize_link(share_link)
        if not safe:
            return None, None

        html, session, proxy = await self.request(safe)
        if not html:
            return None, None

        m = re.search(r'"dlink":"([^"]+)"', html)
        if not m:
            return None, None

        return m.group(1).replace("\\/", "/"), proxy

    async def download(self, url: str, path: str, proxy: str):
        connector = ProxyConnector.from_url(proxy)
        async with aiohttp.ClientSession(
            connector=connector,
            cookies=self.cookies,
            timeout=aiohttp.ClientTimeout(total=0),
            headers={
                "User-Agent": "Mozilla/5.0 Chrome/120 Safari/537.36"
            }
        ) as session:
            async with session.get(url) as r:
                if r.status != 200:
                    return False
                with open(path, "wb") as f:
                    async for chunk in r.content.iter_chunked(1024 * 1024):
                        f.write(chunk)
        return True


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
        await msg.reply_text("⏳ Download already running.")
        return

    active_users.add(user_id)
    status = await msg.reply_text("🔍 Resolving Terabox link via proxy...")

    try:
        dlink, proxy = await tera.extract_download_url(text)
        if not dlink:
            await status.edit_text("❌ Cannot resolve Terabox link.")
            return

        filename = f"{user_id}_{int(time.time())}.mp4"
        filepath = f"{DOWNLOAD_DIR}/{filename}"

        await status.edit_text("⬇️ Downloading video...")
        ok = await tera.download(dlink, filepath, proxy)
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

        await status.edit_text("✅ Video sent successfully!")

        os.remove(filepath)

    except Exception as e:
        log.exception("Download error")
        await status.edit_text(f"❌ Error: {e}")

    finally:
        active_users.discard(user_id)

# ───────────────── START ─────────────────
if __name__ == "__main__":
    log.info("Starting Terabox bot (proxy + video send enabled)")
    app.run()
