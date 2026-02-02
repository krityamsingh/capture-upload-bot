import os
import re
import time
import asyncio
import logging
import aiohttp

from pyrogram import Client, filters, idle
from pyrogram.types import Message

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

# ───────────────── BOT CLIENT ─────────────────
app = Client(
    "terabox_downloader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50
)

active_users = set()

# ───────────────── TERABOX HANDLER ─────────────────
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
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7:
                    domain = parts[0]
                    name = parts[5]
                    value = parts[6]
                    if "tera" in domain:
                        self.cookies[name] = value

        log.info(f"Loaded {len(self.cookies)} cookies")

    async def get_session(self):
        if self.session is None:
            jar = aiohttp.CookieJar()
            jar.update_cookies(self.cookies)

            timeout = aiohttp.ClientTimeout(
                total=600,
                sock_connect=30,
                sock_read=300
            )

            self.session = aiohttp.ClientSession(
                cookie_jar=jar,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 Chrome/120 Safari/537.36"
                }
            )
        return self.session

    async def extract_dlink(self, share_url: str) -> str | None:
        session = await self.get_session()

        async with session.get(share_url) as r:
            if r.status != 200:
                return None

            html = await r.text()

        # Common Terabox patterns
        patterns = [
            r'"dlink":"([^"]+)"',
            r'"downloadUrl":"([^"]+)"',
            r'"url":"([^"]+)"'
        ]

        for p in patterns:
            m = re.search(p, html)
            if m:
                return m.group(1).replace("\\/", "/")

        return None

    async def download(self, url: str, path: str) -> bool:
        session = await self.get_session()

        async with session.get(url) as r:
            if r.status != 200:
                return False

            with open(path, "wb") as f:
                async for chunk in r.content.iter_chunked(1024 * 1024):
                    f.write(chunk)

        return True


tera = Terabox()

# ───────────────── UTIL ─────────────────
def is_terabox_link(text: str) -> bool:
    return any(x in text.lower() for x in [
        "terabox.com",
        "1024tera.com",
        "terafileshare.com"
    ])

# ───────────────── COMMANDS ─────────────────
@app.on_message(filters.command("start") & filters.private)
async def start(_, msg: Message):
    await msg.reply_text(
        "🤖 **Terabox Downloader Bot**\n\n"
        "📥 Send me a Terabox link\n"
        "📤 I will download & send the file\n\n"
        f"🍪 Cookies loaded: **{len(tera.cookies)}**"
    )

@app.on_message(filters.command("status") & filters.private)
async def status(_, msg: Message):
    await msg.reply_text(
        f"✅ Bot Online\n"
        f"🍪 Cookies: {len(tera.cookies)}\n"
        f"📦 Active users: {len(active_users)}"
    )

# ───────────────── MAIN HANDLER ─────────────────
@app.on_message(filters.private & filters.text)
async def handle(_, msg: Message):
    text = msg.text.strip()

    if text.startswith("/"):
        return

    if not is_terabox_link(text):
        await msg.reply_text("📩 Send a valid **Terabox link**.")
        return

    user_id = msg.from_user.id

    if user_id in active_users:
        await msg.reply_text("⏳ You already have a download running.")
        return

    if not tera.cookies:
        await msg.reply_text("❌ Cookies not loaded.")
        return

    active_users.add(user_id)
    status = await msg.reply_text("🔍 Extracting download link...")

    try:
        dlink = await tera.extract_dlink(text)

        if not dlink:
            await status.edit("❌ Failed to extract download link.")
            return

        filename = f"{user_id}_{int(time.time())}.mp4"
        path = os.path.join(DOWNLOAD_DIR, filename)

        await status.edit("⬇️ Downloading file...")
        ok = await tera.download(dlink, path)

        if not ok:
            await status.edit("❌ Download failed.")
            return

        await status.edit("📤 Uploading to Telegram...")

        await app.send_document(
            chat_id=user_id,
            document=path,
            caption="✅ Download complete"
        )

        await status.edit("✅ Done!")

        os.remove(path)

    except Exception as e:
        log.exception("Handler error")
        await status.edit(f"❌ Error: {e}")

    finally:
        active_users.discard(user_id)

# ───────────────── START BOT ─────────────────
async def main():
    await app.start()
    me = await app.get_me()
    log.info(f"Bot started as @{me.username}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
