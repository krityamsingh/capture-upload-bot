import os
import re
import time
import logging
import aiohttp

from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp import ClientConnectorError

# ───────────────── LOGGING ─────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("TeraboxBot")

# ───────────────── CONFIG ─────────────────
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ───────────────── PYROGRAM CLIENT ─────────────────
app = Client(
    "terabox_downloader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50
)

active_users = set()

# ───────────────── TERABOX ENGINE ─────────────────
class Terabox:
    def __init__(self):
        self.cookies = {}
        self.session = None
        self.load_cookies()

    def load_cookies(self):
        if not os.path.exists("cookies.txt"):
            log.warning("cookies.txt not found")
            return

        with open("cookies.txt", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7:
                    domain, name, value = parts[0], parts[5], parts[6]
                    if "tera" in domain:
                        self.cookies[name] = value

        log.info(f"Loaded {len(self.cookies)} cookies")

    async def get_session(self):
        if not self.session:
            jar = aiohttp.CookieJar()
            jar.update_cookies(self.cookies)

            self.session = aiohttp.ClientSession(
                cookie_jar=jar,
                timeout=aiohttp.ClientTimeout(total=600),
                headers={
                    "User-Agent": "Mozilla/5.0 Chrome/120 Safari/537.36"
                }
            )
        return self.session

    # 🔥 IMPORTANT FIX
    def normalize_share_url(self, text: str) -> str | None:
        patterns = [
            r"/s/([A-Za-z0-9_-]+)",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                code = m.group(1)
                return f"https://www.1024tera.com/s/{code}"
        return None

    async def extract_download_url(self, text: str) -> str | None:
        safe_url = self.normalize_share_url(text)
        if not safe_url:
            return None

        session = await self.get_session()

        try:
            async with session.get(safe_url) as r:
                if r.status != 200:
                    return None
                html = await r.text()
        except ClientConnectorError:
            log.error("DNS resolution failed for Terabox domain")
            return None

        patterns = [
            r'"dlink":"([^"]+)"',
            r'"downloadUrl":"([^"]+)"'
        ]

        for p in patterns:
            m = re.search(p, html)
            if m:
                return m.group(1).replace("\\/", "/")

        return None

    async def download(self, url: str, path: str) -> bool:
        session = await self.get_session()
        try:
            async with session.get(url) as r:
                if r.status != 200:
                    return False
                with open(path, "wb") as f:
                    async for chunk in r.content.iter_chunked(1024 * 1024):
                        f.write(chunk)
            return True
        except ClientConnectorError:
            return False


tera = Terabox()

# ───────────────── HELPERS ─────────────────
def is_terabox_link(text: str) -> bool:
    return any(x in text.lower() for x in (
        "terabox.com",
        "1024tera.com",
        "terafileshare.com"
    ))

# ───────────────── COMMANDS ─────────────────
@app.on_message(filters.command("start") & filters.private)
async def start(_, msg: Message):
    await msg.reply_text(
        "🤖 **Terabox Downloader Bot**\n\n"
        "📥 Send a Terabox link\n"
        "📤 Download will start automatically"
    )

@app.on_message(filters.private & filters.text)
async def handle_link(_, msg: Message):
    text = msg.text.strip()
    user_id = msg.from_user.id

    if not is_terabox_link(text):
        await msg.reply_text("📩 Send a valid Terabox link.")
        return

    if user_id in active_users:
        await msg.reply_text("⏳ Download already running.")
        return

    active_users.add(user_id)
    status = await msg.reply_text("🔍 Processing link...")

    try:
        dlink = await tera.extract_download_url(text)
        if not dlink:
            await status.edit_text("❌ Cannot resolve Terabox link (DNS blocked).")
            return

        file_path = f"{DOWNLOAD_DIR}/{user_id}_{int(time.time())}.mp4"

        await status.edit_text("⬇️ Downloading...")
        ok = await tera.download(dlink, file_path)
        if not ok:
            await status.edit_text("❌ Download failed.")
            return

        await status.edit_text("📤 Uploading...")
        await app.send_document(msg.chat.id, file_path)
        await status.edit_text("✅ Done")

        os.remove(file_path)

    finally:
        active_users.discard(user_id)

# ───────────────── ENTRYPOINT ─────────────────
if __name__ == "__main__":
    log.info("Starting Terabox bot (DNS-safe)")
    app.run()
