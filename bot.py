# bot.py - COMPLETE TERABOX DOWNLOADER WITH COOKIES
import os
import re
import asyncio
import aiohttp
import json
import time
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError
import aiofiles
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get environment variables
API_ID = int(os.environ.get("API_ID", "26676741"))
API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a"))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E")

# Ensure directories exist
os.makedirs("downloads", exist_ok=True)
os.makedirs("cookies", exist_ok=True)

# Store active downloads
active_downloads = {}

class TeraboxDownloader:
    def __init__(self, cookies_file="cookies.txt"):
        self.session = None
        self.cookies = {}
        self.cookies_file = cookies_file
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        self.load_cookies()
    
    def load_cookies(self):
        """Load cookies from cookies.txt file"""
        try:
            # Try multiple locations
            cookie_paths = [
                self.cookies_file,
                "cookies/cookies.txt",
                "cookies.txt",
                "/app/cookies.txt"
            ]
            
            for path in cookie_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                parts = line.split('\t')
                                if len(parts) >= 7:
                                    domain, _, path, secure, expires, name, value = parts[:7]
                                    self.cookies[name] = value
                    logger.info(f"Loaded {len(self.cookies)} cookies from {path}")
                    return
                    
            logger.warning(f"No cookies file found at {self.cookies_file}")
            
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
    
    async def create_session(self):
        """Create aiohttp session with cookies"""
        if not self.session or self.session.closed:
            # Create cookie jar
            cookie_jar = aiohttp.CookieJar()
            
            # Add cookies to jar
            for name, value in self.cookies.items():
                cookie = aiohttp.Cookie(
                    name=name,
                    value=value,
                    domain='.1024tera.com',
                    path='/',
                    expires=None,
                    secure=True,
                    http_only=True
                )
                cookie_jar.update_cookies({name: cookie})
            
            self.session = aiohttp.ClientSession(
                headers=self.base_headers,
                cookie_jar=cookie_jar,
                timeout=aiohttp.ClientTimeout(total=60)
            )
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def extract_shortcode(self, url: str) -> str:
        """Extract shortcode from Terabox URL"""
        patterns = [
            r'(?:terabox\.com|1024tera\.com|terafileshare\.com)/s/([a-zA-Z0-9_-]+)',
            r'/sharing/link\?surl=([a-zA-Z0-9_-]+)',
            r'/s/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try to extract from query parameters
        parsed = urlparse(url)
        if 'surl' in parsed.query:
            return parse_qs(parsed.query)['surl'][0]
        
        return None
    
    async def get_share_info(self, shortcode: str) -> dict:
        """Get share information using cookies"""
        try:
            await self.create_session()
            
            # Try multiple domains
            domains = [
                "https://www.1024tera.com",
                "https://www.terabox.com",
                "https://www.terafileshare.com"
            ]
            
            for domain in domains:
                try:
                    url = f"{domain}/s/{shortcode}"
                    logger.info(f"Fetching share info from: {url}")
                    
                    headers = self.base_headers.copy()
                    headers['Referer'] = f"{domain}/"
                    headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    
                    async with self.session.get(url, headers=headers) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Extract app_id (usually 250528 for Terabox)
                            app_id = "250528"  # Default app_id for Terabox
                            
                            # Try to extract from JavaScript
                            app_id_match = re.search(r'"app_id"\s*:\s*"(\d+)"', html)
                            if app_id_match:
                                app_id = app_id_match.group(1)
                            
                            # Extract share ID and other info
                            shareid_match = re.search(r'"shareid"\s*:\s*(\d+)', html)
                            shareid = shareid_match.group(1) if shareid_match else None
                            
                            uk_match = re.search(r'"uk"\s*:\s*"([^"]+)"', html)
                            uk = uk_match.group(1) if uk_match else None
                            
                            sign_match = re.search(r'"sign"\s*:\s*"([^"]+)"', html)
                            sign = sign_match.group(1) if sign_match else None
                            
                            timestamp_match = re.search(r'"timestamp"\s*:\s*(\d+)', html)
                            timestamp = timestamp_match.group(1) if timestamp_match else str(int(time.time()))
                            
                            return {
                                'success': True,
                                'domain': domain,
                                'app_id': app_id,
                                'shortcode': shortcode,
                                'shareid': shareid,
                                'uk': uk,
                                'sign': sign,
                                'timestamp': timestamp
                            }
                            
                except Exception as e:
                    logger.warning(f"Failed with domain {domain}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting share info: {e}")
            return None
    
    async def get_file_list(self, share_info: dict) -> dict:
        """Get file list from share"""
        try:
            await self.create_session()
            
            url = f"{share_info['domain']}/share/list"
            params = {
                'app_id': share_info['app_id'],
                'shorturl': share_info['shortcode'],
                'root': '1',
            }
            
            if share_info.get('uk'):
                params['uk'] = share_info['uk']
            
            headers = self.base_headers.copy()
            headers['Referer'] = f"{share_info['domain']}/s/{share_info['shortcode']}"
            
            logger.info(f"Getting file list with params: {params}")
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"File list API response: {data}")
                    
                    if data.get('errno') == 0:
                        return data
                    else:
                        logger.error(f"API error: {data}")
                else:
                    logger.error(f"HTTP error: {response.status}")
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting file list: {e}")
            return None
    
    async def get_download_url(self, share_info: dict, fs_id: str) -> str:
        """Get direct download URL"""
        try:
            await self.create_session()
            
            url = f"{share_info['domain']}/api/download"
            
            # Prepare payload
            payload = {
                'app_id': share_info['app_id'],
                'fs_id': fs_id,
                'timestamp': share_info.get('timestamp', str(int(time.time()))),
                'sign': share_info.get('sign', '1'),
                'randsk': '',
                'shareid': share_info.get('shareid', ''),
                'uk': share_info.get('uk', '')
            }
            
            headers = self.base_headers.copy()
            headers['Referer'] = f"{share_info['domain']}/s/{share_info['shortcode']}"
            headers['Content-Type'] = 'application/json'
            
            logger.info(f"Getting download URL with payload: {payload}")
            
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Download API response: {data}")
                    
                    if data.get('errno') == 0 and data.get('dlink'):
                        download_url = data['dlink']
                        # Clean the URL
                        download_url = download_url.replace('\\/', '/')
                        return download_url
                    elif data.get('info'):
                        # Try alternative format
                        for item in data.get('info', []):
                            if item.get('dlink'):
                                download_url = item['dlink'].replace('\\/', '/')
                                return download_url
                
                logger.error(f"Failed to get download URL: {await response.text()}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
            return None
    
    async def extract_video_info(self, terabox_url: str) -> dict:
        """Main function to extract video information"""
        try:
            # Extract shortcode
            shortcode = await self.extract_shortcode(terabox_url)
            if not shortcode:
                logger.error(f"Could not extract shortcode from: {terabox_url}")
                return None
            
            logger.info(f"Extracted shortcode: {shortcode}")
            
            # Get share information
            share_info = await self.get_share_info(shortcode)
            if not share_info or not share_info.get('success'):
                logger.error("Failed to get share information")
                return None
            
            logger.info(f"Got share info: {share_info}")
            
            # Get file list
            file_data = await self.get_file_list(share_info)
            if not file_data:
                logger.error("Failed to get file list")
                return None
            
            # Get first file (assuming single file share)
            file_list = file_data.get('list', [])
            if not file_list:
                logger.error("No files found in share")
                return None
            
            # Find video files
            video_files = []
            for file_item in file_list:
                if file_item.get('isdir') == 0:  # Not a directory
                    # Check if it's a video by extension or category
                    filename = file_item.get('server_filename', '').lower()
                    if any(filename.endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']):
                        video_files.append(file_item)
            
            if not video_files:
                # If no videos, take first file
                video_files = [file_list[0]]
            
            # Get download URL for first video
            fs_id = video_files[0].get('fs_id')
            download_url = await self.get_download_url(share_info, fs_id)
            
            if not download_url:
                logger.error("Failed to get download URL")
                return None
            
            # Prepare response
            return {
                'success': True,
                'download_url': download_url,
                'filename': video_files[0].get('server_filename', f'video_{shortcode}.mp4'),
                'size': video_files[0].get('size', 0),
                'shortcode': shortcode,
                'file_count': len(file_list),
                'video_count': len(video_files)
            }
            
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None
    
    async def download_video(self, url: str, filename: str, message: Message, user_id: int) -> str:
        """Download video with progress"""
        try:
            await self.create_session()
            
            # Create unique file path
            timestamp = int(time.time())
            safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = f"downloads/{user_id}_{timestamp}_{safe_filename}"
            
            # Get file size first
            headers = self.base_headers.copy()
            headers['Range'] = 'bytes=0-0'  # Just get headers
            
            async with self.session.head(url, headers=headers, allow_redirects=True) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                
                if total_size == 0:
                    # Try without Range header
                    async with self.session.head(url, allow_redirects=True) as response2:
                        total_size = int(response2.headers.get('Content-Length', 50 * 1024 * 1024))  # 50MB fallback
            
            # Download file with progress
            downloaded = 0
            start_time = time.time()
            last_update = time.time()
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Download failed with status: {response.status}")
                    return None
                
                # Write to file
                async with aiofiles.open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024*1024):  # 1MB chunks
                        if user_id in active_downloads and active_downloads[user_id].get('cancelled'):
                            await f.close()
                            try:
                                os.remove(filepath)
                            except:
                                pass
                            return None
                        
                        if chunk:
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress every 2 seconds or when download completes
                            current_time = time.time()
                            if current_time - last_update >= 2 or downloaded >= total_size:
                                progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                                await self.update_progress(message, progress, downloaded, total_size)
                                last_update = current_time
            
            return filepath
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
    async def update_progress(self, message: Message, progress: float, downloaded: int, total: int):
        """Update download progress in message"""
        try:
            # Format progress bar
            bar_length = 20
            filled_length = int(bar_length * progress / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Format sizes
            def format_size(size):
                if not size or size == 0:
                    return "0 B"
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        return f"{size:.2f} {unit}"
                    size /= 1024.0
                return f"{size:.2f} TB"
            
            # Calculate speed and ETA
            current_time = time.time()
            elapsed = current_time - active_downloads.get(message.chat.id, {}).get('start_time', current_time)
            if elapsed > 0:
                speed = downloaded / elapsed
                remaining = total - downloaded
                eta = remaining / speed if speed > 0 else 0
                
                speed_text = f"{format_size(speed)}/s"
                eta_text = f"{int(eta // 60)}m {int(eta % 60)}s" if eta > 0 else "--"
            else:
                speed_text = "0 B/s"
                eta_text = "--"
            
            # Create progress text
            text = (
                f"📥 **Downloading...**\n\n"
                f"`{bar}` **{progress:.1f}%**\n\n"
                f"**Progress:** `{format_size(downloaded)} / {format_size(total)}`\n"
                f"**Speed:** `{speed_text}`\n"
                f"**ETA:** `{eta_text}`\n\n"
                f"_Downloading to your DM..._"
            )
            
            await message.edit_text(text)
            
        except Exception as e:
            logger.error(f"Progress update error: {e}")

# Create downloader instance
downloader = TeraboxDownloader("cookies.txt")

# Create Pyrogram client
app = Client(
    "terabox_downloader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=2,
    sleep_threshold=60
)

# Helper functions
def format_size(size_bytes):
    """Format file size in human readable format"""
    if not size_bytes:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

# =============== COMMAND HANDLERS ===============

@app.on_message(filters.command(["start", "help"]))
async def start_handler(client: Client, message: Message):
    """Handle /start command"""
    # Only respond in private chats
    if message.chat.type != "private":
        await message.reply_text(
            "⚠️ **Please message me in private!**\n\n"
            "I only work in direct messages (DMs).\n"
            "Send me a private message to use this bot."
        )
        return
    
    welcome_text = f"""
🎬 **Terabox Video Downloader Bot** 🎬

**Hello {message.from_user.first_name}!** 👋

I can download videos from Terabox using your cookies!

**Supported sites:**
✅ terabox.com
✅ 1024tera.com  
✅ terafileshare.com

**How to use:**
1. Send me any Terabox share link
2. I'll use your cookies to download
3. Video will be sent to this DM

**Example links:**
`https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA`
`https://terabox.com/s/xxxxxxx`
`https://1024tera.com/s/xxxxxxx`

**Commands:**
/start - Show this message
/status - Check bot and cookies status
/cookies - Refresh cookies
/cancel - Cancel current download

**Note:** I only work in private messages!
"""
    
    await message.reply_text(welcome_text, disable_web_page_preview=True)
    logger.info(f"User {message.from_user.id} started bot")

@app.on_message(filters.command("status"))
async def status_handler(client: Client, message: Message):
    """Handle /status command"""
    if message.chat.type != "private":
        return
    
    # Check cookies
    cookies_count = len(downloader.cookies)
    cookies_status = "✅ Loaded" if cookies_count > 0 else "❌ Missing"
    
    status_text = f"""
🤖 **Bot Status Report**

**User:** {message.from_user.first_name}
**User ID:** `{message.from_user.id}`
**Active Downloads:** {len(active_downloads)}
**Cookies:** {cookies_status} ({cookies_count} cookies)
**Session:** {'✅ Active' if downloader.session else '❌ Inactive'}

**Bot is ready!** Send me a Terabox link to download.
"""
    
    await message.reply_text(status_text)

@app.on_message(filters.command("cookies"))
async def cookies_handler(client: Client, message: Message):
    """Handle cookies refresh"""
    if message.chat.type != "private":
        return
    
    try:
        # Check if user sent a file
        if message.reply_to_message and message.reply_to_message.document:
            file_name = message.reply_to_message.document.file_name
            if file_name.endswith('.txt'):
                # Download the cookies file
                cookies_path = await message.reply_to_message.download(file_name="cookies/cookies.txt")
                
                # Reload cookies
                downloader.cookies_file = cookies_path
                downloader.load_cookies()
                
                await message.reply_text(f"✅ Cookies updated! Loaded {len(downloader.cookies)} cookies.")
                return
        
        # Just refresh existing cookies
        downloader.load_cookies()
        await message.reply_text(f"✅ Cookies refreshed! Currently have {len(downloader.cookies)} cookies.")
        
    except Exception as e:
        logger.error(f"Cookies error: {e}")
        await message.reply_text(f"❌ Error updating cookies: {str(e)}")

@app.on_message(filters.command("cancel"))
async def cancel_handler(client: Client, message: Message):
    """Handle /cancel command"""
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    if user_id in active_downloads:
        active_downloads[user_id]['cancelled'] = True
        await message.reply_text("✅ Download cancelled successfully!")
    else:
        await message.reply_text("ℹ️ No active download to cancel.")

@app.on_message(filters.text & filters.private & ~filters.command(["start", "status", "cookies", "cancel"]))
async def handle_links(client: Client, message: Message):
    """Handle Terabox links in DM"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Check if it's a Terabox URL
    if not any(domain in text.lower() for domain in ['terabox', '1024tera', 'terafileshare']):
        await message.reply_text(
            "📩 **Please send me a Terabox link!**\n\n"
            "I can download videos from:\n"
            "• terabox.com\n"
            "• 1024tera.com\n"
            "• terafileshare.com\n\n"
            "Just paste your link here!"
        )
        return
    
    # Check if user already has active download
    if user_id in active_downloads and not active_downloads[user_id].get('cancelled'):
        await message.reply_text("⏳ You already have a download in progress. Please wait or use /cancel")
        return
    
    # Check if cookies are loaded
    if len(downloader.cookies) == 0:
        await message.reply_text(
            "❌ **No cookies loaded!**\n\n"
            "Please upload a cookies.txt file by replying to it with /cookies command.\n\n"
            "**How to get cookies:**\n"
            "1. Login to Terabox in browser\n"
            "2. Use a cookie exporter extension\n"
            "3. Export cookies as Netscape format\n"
            "4. Send the cookies.txt file to me\n"
            "5. Reply to it with: /cookies"
        )
        return
    
    try:
        # Mark as downloading
        active_downloads[user_id] = {
            'cancelled': False,
            'start_time': time.time()
        }
        
        # Send processing message
        processing_msg = await message.reply_text(
            f"🔍 **Processing your link...**\n\n"
            f"**URL:** `{text[:50]}...`\n"
            f"**Status:** Extracting video information using cookies..."
        )
        
        # Extract video info
        video_info = await downloader.extract_video_info(text)
        
        if not video_info or not video_info.get('success'):
            await processing_msg.edit_text(
                "❌ **Failed to extract video!**\n\n"
                "Possible reasons:\n"
                "• Invalid or expired link\n"
                "• Cookies are expired\n"
                "• Video is private/removed\n"
                "• Server error\n\n"
                "**Try:**\n"
                "1. Check if link is valid\n"
                "2. Update cookies with /cookies\n"
                "3. Try a different link"
            )
            if user_id in active_downloads:
                del active_downloads[user_id]
            return
        
        # Show video info
        download_url = video_info['download_url']
        filename = video_info['filename']
        file_size = video_info['size']
        
        confirm_text = (
            f"✅ **Video Found!**\n\n"
            f"**📹 File:** `{filename}`\n"
            f"**📦 Size:** `{format_size(file_size)}`\n"
            f"**🔗 Status:** Ready to download\n\n"
            f"Click below to download to your DM:"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬇️ Download Now", callback_data=f"dl_{user_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")
            ]
        ])
        
        # Update active downloads with video info
        active_downloads[user_id].update({
            'download_url': download_url,
            'filename': filename,
            'size': file_size,
            'processing_msg': processing_msg
        })
        
        await processing_msg.edit_text(confirm_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Link processing error: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")
        if user_id in active_downloads:
            del active_downloads[user_id]

@app.on_callback_query(filters.regex(r"^dl_"))
async def download_callback(client, callback_query):
    """Handle download button click"""
    user_id = callback_query.from_user.id
    
    # Extract user ID from callback
    try:
        callback_user_id = int(callback_query.data.split('_')[1])
    except:
        callback_user_id = None
    
    # Verify it's the same user
    if callback_user_id != user_id:
        await callback_query.answer("This is not your download!", show_alert=True)
        return
    
    # Check if user has active download
    if user_id not in active_downloads:
        await callback_query.answer("Download expired or cancelled", show_alert=True)
        return
    
    await callback_query.answer("Starting download...")
    
    # Get download info
    download_info = active_downloads[user_id]
    
    if download_info.get('cancelled'):
        await callback_query.message.edit_text("❌ Download was cancelled.")
        return
    
    download_url = download_info['download_url']
    filename = download_info['filename']
    message = download_info['processing_msg']
    
    try:
        # Update message
        await message.edit_text(
            f"⬇️ **Starting Download...**\n\n"
            f"**File:** `{filename}`\n"
            f"**Size:** `{format_size(download_info['size'])}`\n"
            f"**Status:** Downloading using cookies..."
        )
        
        # Download the video
        filepath = await downloader.download_video(download_url, filename, message, user_id)
        
        if not filepath or (user_id in active_downloads and active_downloads[user_id].get('cancelled')):
            await message.edit_text("❌ Download failed or was cancelled.")
            if os.path.exists(filepath):
                os.remove(filepath)
            if user_id in active_downloads:
                del active_downloads[user_id]
            return
        
        # Get actual file size
        file_size = os.path.getsize(filepath)
        
        # Upload to DM
        await message.edit_text("📤 **Uploading to your DM...**\n\nPlease wait...")
        
        try:
            # Send as video
            await client.send_video(
                chat_id=user_id,
                video=filepath,
                caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`",
                supports_streaming=True,
                progress=lambda current, total: logger.info(f"Uploading {current}/{total}")
            )
            
            # Update success message
            success_text = (
                f"✅ **Successfully Sent!**\n\n"
                f"**File:** `{filename}`\n"
                f"**Size:** `{format_size(file_size)}`\n"
                f"**Status:** ✅ Delivered to your DM\n\n"
                f"Check above for your video! 👆"
            )
            
            await message.edit_text(success_text)
            
            logger.info(f"Video sent to user {user_id}: {filename}")
            
        except FloodWait as e:
            # Handle flood wait
            wait_time = e.value
            await message.edit_text(f"⏳ Please wait {wait_time} seconds (Telegram limit)...")
            await asyncio.sleep(wait_time)
            
            # Retry
            await client.send_video(
                chat_id=user_id,
                video=filepath,
                caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`",
                supports_streaming=True
            )
            await message.edit_text(success_text)
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            # Try as document if video fails
            try:
                await client.send_document(
                    chat_id=user_id,
                    document=filepath,
                    caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`"
                )
                await message.edit_text(success_text)
            except Exception as e2:
                await message.edit_text(f"❌ Upload failed: {str(e2)}")
        
        # Cleanup
        try:
            os.remove(filepath)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Download callback error: {e}")
        await message.edit_text(f"❌ Download failed: {str(e)}")
    
    finally:
        # Remove from active downloads
        if user_id in active_downloads:
            del active_downloads[user_id]

@app.on_callback_query(filters.regex(r"^cancel_"))
async def cancel_callback(client, callback_query):
    """Handle cancel button"""
    user_id = callback_query.from_user.id
    
    try:
        callback_user_id = int(callback_query.data.split('_')[1])
    except:
        callback_user_id = None
    
    if callback_user_id != user_id:
        await callback_query.answer("Not your download!", show_alert=True)
        return
    
    if user_id in active_downloads:
        active_downloads[user_id]['cancelled'] = True
        del active_downloads[user_id]
    
    await callback_query.message.edit_text("❌ Download cancelled.")
    await callback_query.answer("Cancelled")

# =============== MAIN FUNCTION ===============

async def main():
    """Main function"""
    logger.info("Starting Terabox Downloader Bot with cookies...")
    logger.info(f"Loaded {len(downloader.cookies)} cookies")
    
    try:
        await app.start()
        logger.info("✅ Bot started!")
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"🤖 Bot: @{me.username}")
        logger.info(f"🆔 ID: {me.id}")
        
        # Keep running
        await idle()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        try:
            await app.stop()
            await downloader.close()
            logger.info("Bot stopped cleanly")
        except:
            pass

if __name__ == "__main__":
    # Create cookies.txt file from environment or use default
    cookies_content = """# Netscape HTTP Cookie File
# https://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file! Do not edit.

.1024tera.com	TRUE	/	FALSE	1775120492	browserid	4V1elzoKTZ7pTEBLp_vHA9QIJoiLYpZaBxaHJ_NEpCryUX3v5XJX4KpLzEo=
.1024tera.com	TRUE	/	FALSE	1772531231	lang	en
.1024tera.com	TRUE	/	FALSE	1801472492	TSID	MvUeOemI9CRbdNw7wxRDjZf1eMqSVapF
.1024tera.com	TRUE	/	FALSE	1775123231	shareUpdateRandom	97
.1024tera.com	TRUE	/	FALSE	1804499232	__bid_n	19c186fa5d9814629b4207
.1024tera.com	TRUE	/	TRUE	1801472552	ndus	YQjKZL8peHuipOIVKwKsnrUz82kNQfu2Kk936GL7
dm.1024tera.com	FALSE	/	FALSE	0	csrfToken	X2qpBfnEoM6UXY4_kTa08sBf
dm.1024tera.com	FALSE	/	FALSE	1772531232	ndut_fmt	E2D9670B528107927362DA057D745265896AAD3074E81B5AE789F685649DA0A5
dm.1024tera.com	FALSE	/	FALSE	1772531235	ndut_fmv	6ec573e6027ec9f4f82dbd862d9e762eee3745caeb28b072ac1ed7a3accd9d113354223ec9bb7661ea456acc0f021f9ad815c0182013b2ada8bfac035e4a99efee480d782e58f64e0839dace4e90ceb0241ba32717aa2aecdaded096ce11a9d030e254fe51bb42eca2b8fc2795312241
dm.1024tera.com	FALSE	/	FALSE	1785491239	g_state	{"i_l":0,"i_ll":1769939239740,"i_b":"QJOqM5CSUpHTv9zkWvDGbOJ/td/iWmp+uQdfRpwZsP4","i_e":{"enable_itp_optimization":3}}"""
    
    # Write cookies to file
    with open("cookies.txt", "w", encoding="utf-8") as f:
        f.write(cookies_content)
    
    logger.info("Created cookies.txt file")
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
