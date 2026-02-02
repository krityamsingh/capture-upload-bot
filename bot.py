import os
import random
import logging
import aiohttp
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp_socks import ProxyConnector

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("TeraboxBot")

# ---------------- CONFIG ----------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

PROXY_FILE = "proxies.txt"

# ---------------- LOAD PROXIES ----------------
def load_proxies():
    if not os.path.exists(PROXY_FILE):
        return []
    with open(PROXY_FILE, "r") as f:
        return [p.strip() for p in f if p.strip()]

PROXIES = load_proxies()

# ---------------- TERABOX ----------------
class Terabox:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=60)

    async def fetch(self, url: str):
        random.shuffle(PROXIES)

        last_error = None

        for proxy in PROXIES:
            try:
                connector = ProxyConnector.from_url(proxy)
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=self.timeout,
                    headers={
                        "User-Agent": "Mozilla/5.0 Chrome/120 Safari/537.36"
                    }
                ) as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            return await resp.text()
            except Exception as e:
                last_error = e
                log.warning(f"Proxy failed {proxy} → {e}")

        raise RuntimeError("All proxies failed") from last_error

    async def extract_download_url(self, link: str):
        html = await self.fetch(link)

        # TODO: your real extraction logic here
        if "terabox" not in html.lower():
            raise RuntimeError("Invalid Terabox response")

        return "DOWNLOAD_URL_EXTRACTED"

# ---------------- BOT ----------------
app = Client(
    "terabox-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

tera = Terabox()

@app.on_message(filters.private & filters.text)
async def handle_link(_, msg: Message):
    text = msg.text.strip()

    if "tera" not in text:
        return

    await msg.reply("🔄 Resolving Terabox link via proxy...")

    try:
        dlink = await tera.extract_download_url(text)
        await msg.reply(f"✅ Download link:\n{dlink}")
    except Exception as e:
        await msg.reply(f"❌ Cannot resolve Terabox link.\n`{e}`")

# ---------------- START ----------------
if __name__ == "__main__":
    log.info("Starting Terabox bot with proxy support")
    app.run()
