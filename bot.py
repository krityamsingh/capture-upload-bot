import asyncio
import json
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

PROXY_FILE = "data.json"
COOKIE_FILE = "cookies.txt"

TEST_URL = "https://www.google.com"
TERA_REGEX = r"(https?://(?:www\.)?(?:terabox|1024tera|terafileshare)\.com/\S+)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("TeraboxBot")

# ================= GLOBALS =================
WORKING_PROXY = None
COOKIE_HEADER = None

# ================= HELPERS =================
def load_cookies():
    if not os.path.exists(COOKIE_FILE):
        return None

    cookies = {}
    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                cookies[k] = v
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def load_proxies():
    with open(PROXY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [p["proxy"] for p in data if p.get("proxy")]


async def test_proxy(proxy: str) -> bool:
    try:
        connector = ProxyConnector.from_url(proxy)
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(TEST_URL) as r:
                return r.status == 200
    except Exception:
        return False


async def get_working_proxy():
    global WORKING_PROXY
    if WORKING_PROXY:
        return WORKING_PROXY

    log.info("Testing proxies...")
    for proxy in load_proxies():
        if await test_proxy(proxy):
            WORKING_PROXY = proxy
            log.info(f"Working proxy found: {proxy}")
            return proxy

    return None


async def terabox_extract(link: str) -> str:
    proxy = await get_workING_proxy()
    if not proxy:
        raise RuntimeError("No working proxy")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": COOKIE_HEADER
    }

    connector = ProxyConnector.from_url(proxy)
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(
        connector=connector,
        headers=headers,
        timeout=timeout
    ) as session:
        async with session.get(link, allow_redirects=True) as r:
            html = await r.text()

    match = re.search(r'"downloadUrl":"(https:[^"]+)"', html)
    if not match:
        raise RuntimeError("Download link not found")

    return match.group(1).replace("\\/", "/")


async def download_file(url: str, path: str):
    proxy = WORKING_PROXY
    connector = ProxyConnector.from_url(proxy)
    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
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
async def handle_link(_, message: Message):
    match = re.search(TERA_REGEX, message.text)
    if not match:
        return

    await message.reply("🔍 Analyzing Terabox link...")

    try:
        dlink = await terabox_extract(match.group(1))
        await message.reply("⬇️ Downloading video...")

        file_path = f"/tmp/{message.id}.mp4"
        await download_file(dlink, file_path)

        await message.reply_video(
            video=file_path,
            caption="✅ Here is your Terabox video"
        )

        os.remove(file_path)

    except Exception as e:
        log.exception(e)
        await message.reply(f"❌ Failed: {e}")

# ================= MAIN =================
async def main():
    global COOKIE_HEADER
    COOKIE_HEADER = load_cookies()

    if not COOKIE_HEADER:
        log.error("cookies.txt missing")
        return

    await app.start()
    log.info(f"Bot started as @{(await app.get_me()).username}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
