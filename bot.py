import asyncio
import logging
import os
import re
import aiohttp
import aiofiles
import time
from pathlib import Path
from typing import Optional, List

from pyrogram import Client, filters, idle
from pyrogram.types import Message
from aiohttp_socks import ProxyConnector

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

PROXY_FILE = "data.txt"
COOKIE_FILE = "cookies.txt"
DOWNLOAD_DIR = "downloads"
MAX_FILE_SIZE = 2000 * 1024 * 1024  # 2GB
MAX_CONCURRENT_DOWNLOADS = 3

# Support multiple Terabox domains
TERA_REGEX = r"(https?://(?:www\.)?(?:terabox\.app|1024tera\.com|terabox\.com|terafileshare\.com)/\S+)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("TeraboxBot")

# Ensure download directory exists
Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

# ================= SESSION MANAGEMENT =================
class SessionManager:
    def __init__(self):
        self.cookie_header = None
        self.proxies: List[str] = []
        self.working_proxy: Optional[str] = None
        self.active_downloads = 0
        self.lock = asyncio.Lock()
        self.load_cookies()
        self.load_proxies()
    
    def load_cookies(self):
        try:
            if Path(COOKIE_FILE).exists():
                cookies = []
                with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and ("terabox" in line.lower() or "ndus" in line.lower()):
                            cookies.append(line)
                if cookies:
                    self.cookie_header = "; ".join(cookies)
                    log.info(f"✅ Loaded {len(cookies)} cookies")
                else:
                    log.error("❌ No valid cookies found in cookies.txt")
            else:
                log.error(f"❌ Cookie file not found: {COOKIE_FILE}")
        except Exception as e:
            log.error(f"❌ Failed to load cookies: {e}")
    
    def load_proxies(self):
        try:
            if Path(PROXY_FILE).exists():
                with open(PROXY_FILE, "r", encoding="utf-8") as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
                log.info(f"✅ Loaded {len(self.proxies)} proxies")
            else:
                log.warning(f"⚠️ Proxy file not found: {PROXY_FILE}")
        except Exception as e:
            log.error(f"❌ Failed to load proxies: {e}")
    
    async def get_working_proxy(self, force_test: bool = False) -> Optional[str]:
        await self.lock.acquire()
        try:
            if not force_test and self.working_proxy:
                return self.working_proxy
            
            if not self.proxies:
                log.warning("⚠️ No proxies available")
                return None
            
            log.info(f"🔍 Testing {len(self.proxies)} proxies...")
            
            # Test proxies in parallel
            tasks = []
            for proxy in self.proxies:
                task = asyncio.create_task(self.test_proxy(proxy))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for proxy, result in zip(self.proxies, results):
                if result is True:
                    self.working_proxy = proxy
                    log.info(f"✅ Working proxy found: {proxy}")
                    return proxy
            
            log.error("❌ No working proxy found")
            return None
        finally:
            self.lock.release()
    
    async def test_proxy(self, proxy: str) -> bool:
        try:
            connector = ProxyConnector.from_url(proxy)
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                async with session.get("https://httpbin.org/ip", ssl=False) as r:
                    if r.status == 200:
                        data = await r.json()
                        log.debug(f"Proxy {proxy} returned IP: {data.get('origin')}")
                        return True
        except Exception as e:
            log.debug(f"Proxy {proxy} failed: {e}")
        return False
    
    async def acquire_download_slot(self) -> bool:
        await self.lock.acquire()
        try:
            if self.active_downloads < MAX_CONCURRENT_DOWNLOADS:
                self.active_downloads += 1
                return True
            return False
        finally:
            self.lock.release()
    
    def release_download_slot(self):
        self.active_downloads = max(0, self.active_downloads - 1)

# Global session manager instance
session_manager = SessionManager()

# ================= DOWNLOAD UTILITIES =================
class TeraboxDownloader:
    @staticmethod
    async def extract_download_url(link: str) -> Optional[str]:
        proxy = await session_manager.get_working_proxy()
        if not proxy:
            raise Exception("No working proxy available")
        
        if not session_manager.cookie_header:
            raise Exception("Cookies not configured")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": session_manager.cookie_header,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.terabox.com/"
        }
        
        try:
            connector = ProxyConnector.from_url(proxy)
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(
                connector=connector,
                headers=headers,
                timeout=timeout
            ) as session:
                # First request to get the page
                async with session.get(link, allow_redirects=True, ssl=False) as r:
                    html = await r.text()
                
                # Try multiple patterns to extract download URL
                patterns = [
                    r'"downloadUrl"\s*:\s*"([^"]+)"',
                    r'downloadUrl":"([^"]+)"',
                    r'video_url"\s*:\s*"([^"]+)"',
                    r'"url"\s*:\s*"([^"]+)"',
                    r'"play_url"\s*:\s*"([^"]+)"',
                    r'playUrl":"([^"]+)"',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, html)
                    if match:
                        url = match.group(1).replace("\\/", "/")
                        if url.startswith("http"):
                            return url
                
                # If not found, try to find video tags
                video_match = re.search(r'<video[^>]+src="([^"]+)"', html)
                if video_match:
                    return video_match.group(1)
                
                # Try to find direct file links
                file_match = re.search(r'"(https://[^"]+?\.(?:mp4|mkv|avi|mov|wmv|flv|webm)[^"]*)"', html)
                if file_match:
                    return file_match.group(1)
                
                raise Exception("Cannot extract download link")
                
        except Exception as e:
            log.error(f"Failed to extract link: {e}")
            raise Exception(f"Failed to extract link: {str(e)}")
    
    @staticmethod
    async def download_file(url: str, file_path: str, message: Message):
        """Download file with progress display"""
        proxy = await session_manager.get_working_proxy()
        if not proxy:
            raise Exception("Proxy not available")
        
        connector = ProxyConnector.from_url(proxy)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.terabox.com/",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        try:
            async with aiohttp.ClientSession(
                connector=connector,
                headers=headers
            ) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3600)) as r:
                    if r.status != 200:
                        raise Exception(f"Download failed: HTTP {r.status}")
                    
                    total_size = int(r.headers.get('content-length', 0))
                    if total_size > MAX_FILE_SIZE:
                        raise Exception(f"File too large ({total_size//(1024*1024)}MB), exceeds limit")
                    
                    downloaded = 0
                    last_update = 0
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in r.content.iter_chunked(1024*1024):
                            if chunk:
                                await f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Update progress every 5%
                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    if progress - last_update >= 5:
                                        try:
                                            await message.edit_text(
                                                f"📥 Downloading... {progress:.1f}% "
                                                f"({downloaded//(1024*1024)}MB/{total_size//(1024*1024)}MB)"
                                            )
                                            last_update = progress
                                        except:
                                            pass
                    
                    return downloaded
                    
        except asyncio.TimeoutError:
            raise Exception("Download timeout")
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

# ================= BOT =================
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

downloader = TeraboxDownloader()

@app.on_message(filters.command("start"))
async def start_command(_, message: Message):
    await message.reply_text(
        "🤖 Terabox Download Bot\n\n"
        "Send me a Terabox link and I'll download the video for you.\n\n"
        "Supported domains:\n"
        "• terabox.app\n"
        "• 1024tera.com\n"
        "• terabox.com\n"
        "• terafileshare.com\n\n"
        "Status:\n"
        f"• Proxies: {'✅ Configured' if session_manager.proxies else '❌ Not configured'}\n"
        f"• Cookies: {'✅ Configured' if session_manager.cookie_header else '❌ Not configured'}\n"
        f"• Active downloads: {session_manager.active_downloads}/{MAX_CONCURRENT_DOWNLOADS}"
    )

@app.on_message(filters.command("status"))
async def status_command(_, message: Message):
    proxy_status = "✅ Working" if session_manager.working_proxy else "❌ Not available"
    await message.reply_text(
        f"📊 Bot Status\n\n"
        f"• Proxy status: {proxy_status}\n"
        f"• Proxy count: {len(session_manager.proxies)}\n"
        f"• Cookies: {'✅ Configured' if session_manager.cookie_header else '❌ Not configured'}\n"
        f"• Active downloads: {session_manager.active_downloads}/{MAX_CONCURRENT_DOWNLOADS}\n"
        f"• Working proxy: {session_manager.working_proxy or 'None'}"
    )

@app.on_message(filters.command("reload"))
async def reload_command(_, message: Message):
    # You can remove this check or add your Telegram user ID
    # if message.from_user.id not in [12345678]:
    #     return await message.reply_text("❌ This command is for admins only")
    
    session_manager.load_cookies()
    session_manager.load_proxies()
    await session_manager.get_working_proxy(force_test=True)
    await message.reply_text("✅ Configuration reloaded")

@app.on_message(filters.command("supported"))
async def supported_command(_, message: Message):
    await message.reply_text(
        "🌐 Supported Terabox Link Formats:\n\n"
        "• https://terabox.app/s/xxxxxxxx\n"
        "• https://www.terabox.com/s/xxxxxxxx\n"
        "• https://1024tera.com/s/xxxxxxxx\n"
        "• https://terafileshare.com/s/xxxxxxxx\n\n"
        "Examples:\n"
        "• https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA\n"
        "• https://terabox.app/s/12abcdefghijklmnopqr\n"
        "• https://www.terabox.com/sharing/link?surl=xxxx"
    )

@app.on_message(filters.private & filters.text)
async def handle_message(_, message: Message):
    match = re.search(TERA_REGEX, message.text, re.IGNORECASE)
    if not match:
        return
    
    link = match.group(0)
    user_id = message.from_user.id
    
    # Check concurrent download limit
    if not await session_manager.acquire_download_slot():
        await message.reply_text("⏳ Download queue is full, please try again later")
        return
    
    status_msg = await message.reply_text("🔍 Parsing link...")
    file_path = None
    
    try:
        # Get download URL
        await status_msg.edit_text("🔗 Getting download URL...")
        download_url = await downloader.extract_download_url(link)
        
        if not download_url:
            await status_msg.edit_text("❌ Cannot get download URL")
            return
        
        # Generate filename with proper extension
        file_ext = await get_file_extension(download_url)
        file_name = f"terabox_{user_id}_{int(time.time())}{file_ext}"
        file_path = os.path.join(DOWNLOAD_DIR, file_name)
        
        # Start download
        await status_msg.edit_text("⬇️ Starting download...")
        
        try:
            await downloader.download_file(download_url, file_path, status_msg)
            
            # Send file to Telegram
            await status_msg.edit_text("📤 Uploading to Telegram...")
            
            # Determine file type and send accordingly
            if file_ext.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']:
                await message.reply_video(
                    video=file_path,
                    caption="✅ Terabox video downloaded"
                )
            elif file_ext.lower() in ['.mp3', '.wav', '.flac', '.m4a', '.aac']:
                await message.reply_audio(
                    audio=file_path,
                    caption="✅ Terabox audio downloaded"
                )
            elif file_ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                await message.reply_photo(
                    photo=file_path,
                    caption="✅ Terabox image downloaded"
                )
            else:
                await message.reply_document(
                    document=file_path,
                    caption="✅ Terabox file downloaded"
                )
            
            await status_msg.delete()
                
        except Exception as e:
            log.error(f"Failed to send file: {e}")
            await status_msg.edit_text(f"✅ Download complete but failed to send: {str(e)}")
            
    except Exception as e:
        log.exception("Error processing message")
        await status_msg.edit_text(f"❌ Error: {str(e)}")
        
    finally:
        # Clean up downloaded file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        # Release download slot
        session_manager.release_download_slot()

async def get_file_extension(url: str) -> str:
    """Extract file extension from URL"""
    # Common video extensions
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']
    audio_extensions = ['.mp3', '.wav', '.flac', '.m4a', '.aac']
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    
    # Check URL for extension
    for ext in video_extensions + audio_extensions + image_extensions:
        if ext in url.lower():
            return ext
    
    # Default to mp4
    return '.mp4'

# ================= MAIN =================
async def main():
    # Check required configuration
    if not API_ID or not API_HASH or not BOT_TOKEN:
        log.error("❌ Please set API_ID, API_HASH and BOT_TOKEN environment variables")
        return
    
    if not session_manager.cookie_header:
        log.error("❌ Please configure cookies.txt file")
        # Can continue but won't be able to download
    
    # Test proxies
    proxy = await session_manager.get_working_proxy()
    if proxy:
        log.info(f"✅ Working proxy: {proxy}")
    else:
        log.warning("⚠️ No working proxy found, will try direct connection")
    
    await app.start()
    bot_info = await app.get_me()
    log.info(f"🤖 Bot started as @{bot_info.username}")
    
    await idle()
    
    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 Bot stopped")
