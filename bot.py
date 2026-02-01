import os
import re
import asyncio
import aiohttp
import json
import logging
import time
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError
import aiofiles
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta

# ==================== CONFIGURATION ====================

# Load environment variables
load_dotenv()

# Get credentials from environment variables (MUST BE SET IN .env FILE)
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Validate credentials
if not all([API_ID, API_HASH, BOT_TOKEN]):
    print("❌ ERROR: Missing environment variables!")
    print("Please create a .env file with:")
    print("API_ID=your_api_id")
    print("API_HASH=your_api_hash")
    print("BOT_TOKEN=your_bot_token")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    print("❌ ERROR: API_ID must be a number!")
    sys.exit(1)

# Bot settings
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MAX_CONCURRENT_DOWNLOADS = 3
DOWNLOAD_TIMEOUT = 3600  # 1 hour
CLEANUP_INTERVAL = 300  # 5 minutes

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== RATE LIMITER ====================

class RateLimiter:
    def __init__(self, max_requests=5, per_minutes=10):
        self.user_requests = defaultdict(list)
        self.max_requests = max_requests
        self.per_minutes = per_minutes
    
    def is_allowed(self, user_id: int) -> bool:
        now = datetime.now()
        user_reqs = self.user_requests[user_id]
        
        # Remove old requests
        user_reqs = [req for req in user_reqs if now - req < timedelta(minutes=self.per_minutes)]
        self.user_requests[user_id] = user_reqs
        
        if len(user_reqs) >= self.max_requests:
            return False
        
        user_reqs.append(now)
        return True
    
    def get_wait_time(self, user_id: int) -> int:
        if not self.user_requests[user_id]:
            return 0
        
        now = datetime.now()
        oldest = min(self.user_requests[user_id])
        reset_time = oldest + timedelta(minutes=self.per_minutes)
        
        if reset_time > now:
            return int((reset_time - now).total_seconds())
        return 0

# ==================== TERABOX DOWNLOADER ====================

class TeraboxDownloader:
    def __init__(self):
        self.session = None
        self.cookies = {}
        self.load_cookies()
    
    def load_cookies(self) -> bool:
        """Load cookies from cookies.txt"""
        try:
            if os.path.exists("cookies.txt"):
                with open("cookies.txt", "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                name = parts[5].strip()
                                value = parts[6].strip()
                                self.cookies[name] = value
                logger.info(f"Loaded {len(self.cookies)} cookies")
                return True
            else:
                logger.warning("cookies.txt not found. Downloads may fail.")
                return False
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False
    
    def validate_cookies(self) -> bool:
        """Validate required cookies"""
        if not self.cookies:
            return False
        
        # Check for Terabox required cookies
        required_cookies = ['ndus', 'csrfToken']
        for cookie in required_cookies:
            if cookie not in self.cookies:
                logger.error(f"Missing required cookie: {cookie}")
                return False
        return True
    
    async def get_session(self):
        """Create aiohttp session with cookies"""
        if not self.session:
            jar = aiohttp.CookieJar()
            for name, value in self.cookies.items():
                jar.update_cookies({name: value})
            
            timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
            self.session = aiohttp.ClientSession(
                cookie_jar=jar,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                }
            )
        return self.session
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def extract_shortcode(self, url: str) -> str:
        """Extract shortcode from Terabox URL"""
        patterns = [
            r'terabox\.com/s/([a-zA-Z0-9_-]+)',
            r'1024tera\.com/s/([a-zA-Z0-9_-]+)',
            r'share\.terabox\.com/s/([a-zA-Z0-9_-]+)',
            r'/(?:s/|sharing/link\?surl=)([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try to extract from query parameters
        parsed = urlparse(url)
        if 'surl' in parse_qs(parsed.query):
            return parse_qs(parsed.query)['surl'][0]
        
        return None
    
    async def get_video_info(self, url: str) -> dict:
        """Get video information from Terabox URL"""
        try:
            session = await self.get_session()
            shortcode = await self.extract_shortcode(url)
            
            if not shortcode:
                logger.error(f"Could not extract shortcode from URL: {url}")
                return None
            
            logger.info(f"Processing shortcode: {shortcode}")
            
            # First, try to get the page to extract necessary tokens
            page_url = f"https://www.1024tera.com/s/{shortcode}"
            async with session.get(page_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch page: {response.status}")
                    return None
                
                html = await response.text()
                
                # Extract shareid and uk
                shareid_match = re.search(r'"shareid"\s*:\s*"(\d+)"', html)
                shareid = shareid_match.group(1) if shareid_match else None
                
                uk_match = re.search(r'"uk"\s*:\s*"([^"]+)"', html)
                uk = uk_match.group(1) if uk_match else None
                
                if not shareid or not uk:
                    logger.error("Could not extract shareid or uk")
                    return None
            
            # Get file list
            list_url = "https://www.1024tera.com/share/list"
            params = {
                'app_id': '250528',
                'shorturl': shortcode,
                'root': '1',
                'uk': uk,
                'shareid': shareid,
                'page': '1',
                'num': '100',
                'by': 'name',
                'order': 'asc',
                'web': '1',
                'channel': 'dubox',
                'app_id': '250528',
                'clienttype': '0',
            }
            
            async with session.get(list_url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Failed to get file list: {response.status}")
                    return None
                
                data = await response.json()
                
                if data.get('errno') != 0 or not data.get('list'):
                    logger.error(f"API error: {data.get('errno')} - {data.get('errmsg', 'Unknown error')}")
                    return None
                
                # Get first file from list
                file_info = data['list'][0]
                fs_id = file_info.get('fs_id')
                
                if not fs_id:
                    logger.error("No fs_id found in file info")
                    return None
                
                # Get download URL
                download_url = "https://www.1024tera.com/api/download"
                payload = {
                    'app_id': '250528',
                    'fs_id': fs_id,
                    'timestamp': int(time.time() * 1000),
                    'shareid': shareid,
                    'uk': uk,
                    'sign': '1',
                    'web': '1',
                    'channel': 'dubox',
                    'clienttype': '0',
                    'method': 'locatedownload'
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'Referer': f"https://www.1024tera.com/s/{shortcode}",
                    'X-Requested-With': 'XMLHttpRequest',
                }
                
                async with session.post(download_url, json=payload, headers=headers) as dl_response:
                    if dl_response.status != 200:
                        logger.error(f"Download API error: {dl_response.status}")
                        return None
                    
                    dl_data = await dl_response.json()
                    
                    if dl_data.get('errno') != 0:
                        logger.error(f"Download API error: {dl_data.get('errno')} - {dl_data.get('errmsg', 'Unknown error')}")
                        return None
                    
                    # Get download link
                    download_link = dl_data.get('url') or dl_data.get('dlink')
                    
                    if not download_link:
                        logger.error("No download link found in response")
                        return None
                    
                    return {
                        'download_url': download_link,
                        'filename': file_info.get('server_filename', f'video_{shortcode}.mp4'),
                        'size': file_info.get('size', 0),
                        'md5': file_info.get('md5'),
                        'success': True
                    }
        
        except asyncio.TimeoutError:
            logger.error("Timeout while fetching video info")
            return None
        except Exception as e:
            logger.error(f"Error getting video info: {e}", exc_info=True)
            return None
    
    async def download_file(self, url: str, filepath: str, progress_callback=None) -> bool:
        """Download file with progress tracking"""
        try:
            session = await self.get_session()
            
            # Get file size first
            async with session.head(url) as response:
                if response.status != 200:
                    logger.error(f"HEAD request failed: {response.status}")
                    return False
                
                total_size = int(response.headers.get('Content-Length', 0))
                
                if total_size > MAX_FILE_SIZE:
                    logger.error(f"File too large: {total_size} bytes")
                    return False
            
            # Download with progress
            downloaded = 0
            start_time = time.time()
            last_update = start_time
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"GET request failed: {response.status}")
                    return False
                
                async with aiofiles.open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                        if not chunk:
                            continue
                        
                        await f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress (throttle to once per second)
                        current_time = time.time()
                        if progress_callback and (current_time - last_update >= 1 or downloaded == total_size):
                            progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                            await progress_callback(progress, downloaded, total_size)
                            last_update = current_time
            
            # Verify file was downloaded completely
            if total_size > 0 and downloaded != total_size:
                logger.error(f"Incomplete download: {downloaded}/{total_size} bytes")
                return False
            
            return True
        
        except asyncio.TimeoutError:
            logger.error("Download timeout")
            return False
        except Exception as e:
            logger.error(f"Download error: {e}", exc_info=True)
            return False

# ==================== UTILITY FUNCTIONS ====================

def format_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if not size_bytes:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def format_time(seconds: int) -> str:
    """Format time in MM:SS or HH:MM:SS"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m {seconds%60}s"
    else:
        return f"{seconds//3600}h {(seconds%3600)//60}m"

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext
    
    return filename

# ==================== BOT SETUP ====================

# Initialize components
downloader = TeraboxDownloader()
rate_limiter = RateLimiter(max_requests=3, per_minutes=5)
active_downloads = {}

# Create Pyrogram client
app = Client(
    "terabox_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50,
    sleep_threshold=60,
    parse_mode="markdown"
)

# ==================== BOT HANDLERS ====================

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    try:
        welcome_text = """
🤖 **Terabox Video Downloader Bot**

I can download videos from Terabox links and send them to you directly!

**Features:**
✅ Download from terabox.com, 1024tera.com
✅ High-speed downloads
✅ Progress tracking
✅ Auto-cookie management
✅ File size up to 2GB

**Commands:**
/start - Show this message
/status - Check bot status
/ping - Check if bot is alive
/cancel - Cancel current download

**How to use:**
1. Send me any Terabox link
2. Click Download button
3. Wait for video to download
4. Receive video in your DM!

**Note:** Ensure cookies.txt is properly configured for downloads.
        """
        
        await message.reply_text(welcome_text)
        logger.info(f"User {message.from_user.id} started the bot")
    
    except Exception as e:
        logger.error(f"Start command error: {e}")

@app.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    """Check bot status"""
    try:
        cookies_status = "✅ Loaded" if downloader.validate_cookies() else "❌ Missing/Invalid"
        active_count = len([v for v in active_downloads.values() if v.get('status') == 'downloading'])
        
        status_text = f"""
📊 **Bot Status**

**Cookies:** {cookies_status}
**Active Downloads:** {active_count}
**Session:** {'✅ Active' if downloader.session else '❌ Inactive'}
**Rate Limit:** Available
**Storage:** Ready

**Stats:**
• Max file size: {format_size(MAX_FILE_SIZE)}
• Concurrent downloads: {MAX_CONCURRENT_DOWNLOADS}
• Download timeout: {DOWNLOAD_TIMEOUT//60} minutes
        """
        
        await message.reply_text(status_text)
    
    except Exception as e:
        logger.error(f"Status command error: {e}")

@app.on_message(filters.command("ping"))
async def ping_command(client: Client, message: Message):
    """Ping command"""
    try:
        start = time.time()
        msg = await message.reply_text("🏓 Pong!")
        end = time.time()
        latency = round((end - start) * 1000, 2)
        
        await msg.edit_text(f"🏓 Pong!\n**Latency:** {latency}ms")
    
    except Exception as e:
        logger.error(f"Ping command error: {e}")

@app.on_message(filters.command("cancel"))
async def cancel_command(client: Client, message: Message):
    """Cancel current download"""
    try:
        user_id = message.from_user.id
        
        if user_id in active_downloads:
            del active_downloads[user_id]
            await message.reply_text("✅ Download cancelled successfully.")
        else:
            await message.reply_text("⚠️ No active download found.")
    
    except Exception as e:
        logger.error(f"Cancel command error: {e}")

@app.on_message(filters.private & filters.text)
async def handle_terabox_link(client: Client, message: Message):
    """Handle Terabox links"""
    try:
        user_id = message.from_user.id
        text = message.text.strip()
        
        # Skip commands
        if text.startswith('/'):
            return
        
        # Check if it's a Terabox link
        terabox_domains = ['terabox.com', '1024tera.com', 'terafileshare.com', 'dubox.com']
        
        if not any(domain in text.lower() for domain in terabox_domains):
            await message.reply_text(
                "❌ **Invalid Link**\n\n"
                "Please send a valid Terabox link from:\n"
                "• terabox.com\n"
                "• 1024tera.com\n"
                "• share.terabox.com\n\n"
                "Example: `https://terabox.com/s/1abc123...`"
            )
            return
        
        # Rate limiting
        if not rate_limiter.is_allowed(user_id):
            wait_time = rate_limiter.get_wait_time(user_id)
            await message.reply_text(
                f"⏳ **Rate Limit Exceeded**\n\n"
                f"Please wait {format_time(wait_time)} before sending another link.\n"
                f"Limit: 3 downloads per 5 minutes."
            )
            return
        
        # Check if user already has active download
        if user_id in active_downloads:
            await message.reply_text(
                "⏳ **Download in Progress**\n\n"
                "You already have an active download.\n"
                "Use /cancel to stop it or wait for completion."
            )
            return
        
        # Check cookies
        if not downloader.validate_cookies():
            await message.reply_text(
                "❌ **Cookies Required**\n\n"
                "Please ensure cookies.txt file exists with valid Terabox cookies.\n"
                "Contact admin for assistance."
            )
            return
        
        # Start processing
        active_downloads[user_id] = {
            'status': 'processing',
            'start_time': time.time(),
            'message': None
        }
        
        processing_msg = await message.reply_text(
            "🔍 **Processing Link...**\n\n"
            "Extracting video information from Terabox...\n"
            "This may take a few seconds."
        )
        
        active_downloads[user_id]['message'] = processing_msg
        
        # Get video info
        video_info = await downloader.get_video_info(text)
        
        if not video_info or not video_info.get('success'):
            await processing_msg.edit_text(
                "❌ **Failed to Extract Video**\n\n"
                "Possible reasons:\n"
                "• Invalid or expired link\n"
                "• Cookies need refresh\n"
                "• Video is private/removed\n"
                "• Server is busy\n\n"
                "Try again or contact admin."
            )
            if user_id in active_downloads:
                del active_downloads[user_id]
            return
        
        # Check file size
        file_size = video_info.get('size', 0)
        if file_size > MAX_FILE_SIZE:
            await processing_msg.edit_text(
                f"❌ **File Too Large**\n\n"
                f"File size: {format_size(file_size)}\n"
                f"Maximum allowed: {format_size(MAX_FILE_SIZE)}\n\n"
                "Please use smaller files or contact admin."
            )
            if user_id in active_downloads:
                del active_downloads[user_id]
            return
        
        # Prepare download info
        download_url = video_info['download_url']
        filename = sanitize_filename(video_info['filename'])
        
        # Update active downloads
        active_downloads[user_id].update({
            'status': 'ready',
            'download_url': download_url,
            'filename': filename,
            'size': file_size,
            'video_info': video_info
        })
        
        # Show download confirmation
        confirm_text = (
            f"✅ **Video Found!**\n\n"
            f"**File:** `{filename}`\n"
            f"**Size:** `{format_size(file_size)}`\n"
            f"**Status:** Ready to download\n\n"
            f"Click below to start download:"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇️ Download Video", callback_data=f"dl_{user_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
        ])
        
        await processing_msg.edit_text(confirm_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Link handler error: {e}", exc_info=True)
        if message.from_user.id in active_downloads:
            try:
                await message.reply_text(f"❌ Error: {str(e)[:100]}")
            except:
                pass
            del active_downloads[message.from_user.id]

# ==================== CALLBACK HANDLERS ====================

@app.on_callback_query(filters.regex(r"^dl_"))
async def start_download_callback(client, callback_query):
    """Handle download button"""
    user_id = callback_query.from_user.id
    
    try:
        # Check if callback is for this user
        parts = callback_query.data.split('_')
        if len(parts) < 2 or int(parts[1]) != user_id:
            await callback_query.answer("This is not your download!", show_alert=True)
            return
        
        if user_id not in active_downloads:
            await callback_query.answer("Download expired or cancelled!", show_alert=True)
            return
        
        download_info = active_downloads[user_id]
        
        if download_info.get('status') != 'ready':
            await callback_query.answer("Download not ready!", show_alert=True)
            return
        
        await callback_query.answer("Starting download...")
        
        # Update status
        download_info['status'] = 'downloading'
        download_info['start_time'] = time.time()
        
        message = download_info['message']
        download_url = download_info['download_url']
        filename = download_info['filename']
        file_size = download_info['size']
        
        # Create downloads directory
        os.makedirs("downloads", exist_ok=True)
        
        # Create unique filepath
        timestamp = int(time.time())
        safe_filename = f"{user_id}_{timestamp}_{filename}"
        filepath = os.path.join("downloads", safe_filename)
        
        # Progress callback function
        last_progress_update = time.time()
        
        async def progress_callback(progress, downloaded, total):
            nonlocal last_progress_update
            current_time = time.time()
            
            # Throttle updates to once per 2 seconds
            if current_time - last_progress_update < 2 and progress < 100:
                return
            
            try:
                # Create progress bar
                bar_length = 20
                filled = int(bar_length * progress / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                # Calculate speed and ETA
                elapsed = current_time - download_info['start_time']
                if elapsed > 0 and downloaded > 0:
                    speed = downloaded / elapsed
                    eta = (total - downloaded) / speed if speed > 0 else 0
                    speed_text = f"{format_size(speed)}/s"
                    eta_text = format_time(int(eta))
                else:
                    speed_text = "0 B/s"
                    eta_text = "--"
                
                text = (
                    f"📥 **Downloading...**\n\n"
                    f"**File:** `{filename}`\n"
                    f"**Size:** `{format_size(downloaded)} / {format_size(total)}`\n\n"
                    f"`{bar}` **{progress:.1f}%**\n\n"
                    f"**Speed:** `{speed_text}`\n"
                    f"**ETA:** `{eta_text}`"
                )
                
                await message.edit_text(text)
                last_progress_update = current_time
                
            except Exception as e:
                logger.error(f"Progress update error: {e}")
        
        # Update initial status
        await message.edit_text(
            f"⬇️ **Starting Download...**\n\n"
            f"**File:** `{filename}`\n"
            f"**Size:** `{format_size(file_size)}`\n"
            f"**Status:** Connecting to server..."
        )
        
        # Start download
        success = await downloader.download_file(
            download_url,
            filepath,
            progress_callback
        )
        
        if not success:
            await message.edit_text(
                "❌ **Download Failed**\n\n"
                "Failed to download the file.\n"
                "Possible reasons:\n"
                "• Network error\n"
                "• Server timeout\n"
                "• File not accessible\n\n"
                "Try again later."
            )
            
            # Cleanup
            if os.path.exists(filepath):
                os.remove(filepath)
            
            if user_id in active_downloads:
                del active_downloads[user_id]
            
            return
        
        # Verify file
        if not os.path.exists(filepath):
            await message.edit_text("❌ Downloaded file not found!")
            if user_id in active_downloads:
                del active_downloads[user_id]
            return
        
        actual_size = os.path.getsize(filepath)
        if file_size > 0 and actual_size != file_size:
            logger.warning(f"Size mismatch: expected {file_size}, got {actual_size}")
        
        # Update status to uploading
        await message.edit_text(
            f"📤 **Uploading to Telegram...**\n\n"
            f"**File:** `{filename}`\n"
            f"**Size:** `{format_size(actual_size)}`\n"
            f"**Status:** Preparing to send..."
        )
        
        try:
            # Send as video
            sent_message = await client.send_video(
                chat_id=user_id,
                video=filepath,
                caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(actual_size)}`",
                supports_streaming=True,
                progress=lambda current, total: logger.debug(f"Upload: {current}/{total}")
            )
            
            await message.edit_text(
                f"✅ **Successfully Sent!**\n\n"
                f"**File:** `{filename}`\n"
                f"**Size:** `{format_size(actual_size)}`\n\n"
                f"Video has been sent to your DM!\n"
                f"[View Message]({sent_message.link})"
            )
            
        except FloodWait as e:
            wait_time = e.value
            await message.edit_text(f"⏳ **Rate Limited**\n\nPlease wait {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            
            # Retry
            await client.send_video(
                chat_id=user_id,
                video=filepath,
                caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(actual_size)}`",
                supports_streaming=True
            )
            await message.edit_text("✅ Video sent to your DM!")
            
        except RPCError as e:
            logger.error(f"Telegram upload error: {e}")
            
            # Try as document
            try:
                await client.send_document(
                    chat_id=user_id,
                    document=filepath,
                    caption=f"✅ **Download Complete**\n\n**File:** `{filename}`\n**Size:** `{format_size(actual_size)}`"
                )
                await message.edit_text("✅ File sent as document!")
            except Exception as e2:
                await message.edit_text(f"❌ Upload failed: {str(e2)[:200]}")
        
        finally:
            # Cleanup downloaded file
            try:
                os.remove(filepath)
            except:
                pass
            
            # Remove from active downloads
            if user_id in active_downloads:
                del active_downloads[user_id]
    
    except Exception as e:
        logger.error(f"Download callback error: {e}", exc_info=True)
        try:
            await callback_query.message.edit_text(f"❌ Error: {str(e)[:200]}")
        except:
            pass
        
        if user_id in active_downloads:
            del active_downloads[user_id]

@app.on_callback_query(filters.regex(r"^cancel_"))
async def cancel_download_callback(client, callback_query):
    """Handle cancel button"""
    user_id = callback_query.from_user.id
    
    try:
        parts = callback_query.data.split('_')
        if len(parts) < 2 or int(parts[1]) != user_id:
            await callback_query.answer("Not your download!", show_alert=True)
            return
        
        if user_id in active_downloads:
            del active_downloads[user_id]
            await callback_query.message.edit_text("❌ Download cancelled by user.")
        else:
            await callback_query.message.edit_text("✅ No active download found.")
        
        await callback_query.answer("Cancelled")
    
    except Exception as e:
        logger.error(f"Cancel callback error: {e}")

# ==================== CLEANUP TASK ====================

async def cleanup_task():
    """Periodic cleanup of old downloads"""
    while True:
        try:
            current_time = time.time()
            to_remove = []
            
            for user_id, download_info in list(active_downloads.items()):
                start_time = download_info.get('start_time', 0)
                
                # Remove if older than 1 hour
                if current_time - start_time > 3600:
                    to_remove.append(user_id)
            
            for user_id in to_remove:
                if user_id in active_downloads:
                    del active_downloads[user_id]
                    logger.info(f"Cleaned up stale download for user {user_id}")
            
            # Clean old download files
            if os.path.exists("downloads"):
                for file in os.listdir("downloads"):
                    filepath = os.path.join("downloads", file)
                    if os.path.isfile(filepath):
                        file_age = current_time - os.path.getctime(filepath)
                        if file_age > 3600:  # Older than 1 hour
                            try:
                                os.remove(filepath)
                                logger.info(f"Cleaned up old file: {file}")
                            except:
                                pass
        
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
        
        await asyncio.sleep(CLEANUP_INTERVAL)

# ==================== MAIN FUNCTION ====================

async def main():
    """Main function"""
    logger.info("=" * 50)
    logger.info("Starting Terabox Downloader Bot...")
    logger.info(f"API ID: {API_ID}")
    logger.info(f"Cookies loaded: {downloader.validate_cookies()}")
    logger.info(f"Max file size: {format_size(MAX_FILE_SIZE)}")
    logger.info("=" * 50)
    
    # Ensure directories exist
    os.makedirs("downloads", exist_ok=True)
    
    try:
        # Start bot
        await app.start()
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"Bot started: @{me.username}")
        logger.info(f"Bot ID: {me.id}")
        
        # Start cleanup task
        asyncio.create_task(cleanup_task())
        
        # Keep running
        await idle()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
    finally:
        # Clean shutdown
        try:
            await app.stop()
            await downloader.close()
            logger.info("Bot stopped cleanly")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")

# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    # Check for required directories
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
