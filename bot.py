import asyncio
import logging
import os
import re
import aiohttp
import aiofiles

from pyrogram import Client, filters
from pyrogram.types import Message
from aiohttp_socks import ProxyConnector

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

PROXY_FILE = "data.txt"      # or data(1).txt
COOKIE_FILE = "cookies.txt"

TEST_URL = "https://www.google.com"
TERA_REGEX = r"(https?://(?:www\.)?(?:terabox|1024tera|terafileshare)\.com/\S+)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("TeraboxBot")

WORKING_PROXY = None
COOKIE_HEADER = None

# ================= UTILS =================
def load_cookies():
    cookies = []
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                cookies.append(line)
    return "; ".join(cookies)


def load_proxies():
    with open(PROXY_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


async def test_proxy(proxy: str) -> bool:
    try:
        connector = ProxyConnector.from_url(proxy)
        timeout = aiohttp.ClientTimeout(total=8)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:
            async with session.get(TEST_URL) as r:
                return r.status == 200
    except Exception:
        return False


async def get_working_proxy():
    global WORKING_PROXY

    if WORKING_PROXY:
        return WORKING_PROXY

    log.info("🔍 Testing proxies...")
    for proxy in load_proxies():
        if await test_proxy(proxy):
            WORKING_PROXY = proxy
            log.info(f"✅ Working proxy: {proxy}")
            return proxy

    return None


async def extract_terabox_download(link: str) -> str:
    proxy = await get_working_proxy()
    if not proxy:
        raise RuntimeError("No working proxy found")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": COOKIE_HEADER
    }

    connector = ProxyConnector.from_url(proxy)

    async with aiohttp.ClientSession(
        connector=connector,
        headers=headers
    ) as session:
        async with session.get(link, allow_redirects=True) as r:
            html = await r.text()

    match = re.search(r'"downloadUrl":"(https:[^"]+)"', html)
    if not match:
        raise RuntimeError("Download URL not found")

    return match.group(1).replace("\\/", "/")


async def download_file(url: str, path: str):
    connector = ProxyConnector.from_url(WORKING_PROXY)

    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url) as r:
            async with aiofiles.open(path, "wb") as f:
                async for chunk in r.content.iter_chunked(1024 * 1024):
                    await f.write(chunk)

# ================= BOT =================
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.private & filters.text)
async def handle_message(_, message: Message):
    match = re.search(TERA_REGEX, message.text)
    if not match:
        return

    await message.reply("🔍 Checking Terabox link & proxy...")

    try:
        dlink = await extract_terabox_download(match.group(1))
        await message.reply("⬇️ Downloading video...")

        file_path = f"/tmp/{message.id}.mp4"
        await download_file(dlink, file_path)

        await message.reply_video(
            video=file_path,
            caption="✅ Terabox video downloaded"
        )

        os.remove(file_path)

    except Exception as e:
        WORKING_PROXY = None  # reset proxy if failed
        log.exception(e)
        await message.reply(f"❌ Error: {e}")

# ================= MAIN =================
async def main():
    global COOKIE_HEADER

    COOKIE_HEADER = load_cookies()
    if not COOKIE_HEADER:
        log.error("cookies.txt missing or empty")
        return

    await app.start()
    log.info(f"🤖 Bot started as @{(await app.get_me()).username}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
