# bot.py
import os
import re
import asyncio
import aiohttp
import logging
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import time
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot Configuration
API_ID = 26676741
API_HASH = "6fbc29f23c15bdb0c7fbbefe65c9193a"
BOT_TOKEN = "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E"

# Cookie file path
COOKIE_FILE = "cookies.txt"

class TeraboxDownloader:
    def __init__(self):
        self.session = None
        self.cookies = self.load_cookies()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
    def load_cookies(self):
        """Load cookies from cookies.txt file"""
        cookies = {}
        try:
            with open(COOKIE_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            domain, _, path, secure, expires, name, value = parts[:7]
                            cookies[name] = value
            logger.info(f"Loaded {len(cookies)} cookies from {COOKIE_FILE}")
            return cookies
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return {}
    
    async def create_session(self):
        """Create aiohttp session with cookies"""
        if not self.session:
            cookie_jar = aiohttp.CookieJar()
            self.session = aiohttp.ClientSession(
                cookie_jar=cookie_jar,
                headers=self.headers
            )
            
            # Add cookies to session
            for name, value in self.cookies.items():
                self.session.cookie_jar.update_cookies({name: value})
    
    async def extract_video_info(self, url: str):
        """Extract video information from Terabox URL"""
        try:
            await self.create_session()
            
            # Pattern to extract shortcode or ID
            patterns = [
                r'terabox\.app/(?:s/)?([a-zA-Z0-9_-]+)',
                r'1024tera\.com/(?:s/)?([a-zA-Z0-9_-]+)',
                r'share/([a-zA-Z0-9_-]+)',
                r'id=([a-zA-Z0-9_-]+)'
            ]
            
            shortcode = None
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    shortcode = match.group(1)
                    break
            
            if not shortcode:
                return None
            
            # Try to get download link
            api_url = f"https://www.1024tera.com/share/{shortcode}"
            
            async with self.session.get(api_url, allow_redirects=True) as response:
                html = await response.text()
                
                # Try to find download URL in the page
                download_patterns = [
                    r'"dlink":"([^"]+)"',
                    r'downloadUrl["\']?:\s*["\']([^"\']+)["\']',
                    r'href=["\'](https?://[^"\']+\.(?:mp4|mkv|avi|mov|wmv|flv))["\']',
                    r'url["\']?:\s*["\'](https?://[^"\']+)["\']',
                ]
                
                for pattern in download_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    if matches:
                        # Clean the URL
                        download_url = matches[0].replace('\\/', '/')
                        
                        # Get file information
                        file_info = await self.get_file_info(download_url)
                        return {
                            'download_url': download_url,
                            'file_info': file_info,
                            'shortcode': shortcode
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None
    
    async def get_file_info(self, url: str):
        """Get file information without downloading entire file"""
        try:
            async with self.session.head(url, allow_redirects=True) as response:
                headers = response.headers
                
                # Try to get filename from Content-Disposition
                content_disposition = headers.get('Content-Disposition', '')
                filename_match = re.search(r'filename="([^"]+)"', content_disposition)
                
                if filename_match:
                    filename = filename_match.group(1)
                else:
                    # Extract from URL
                    filename = url.split('/')[-1].split('?')[0]
                    if not filename:
                        filename = f"video_{int(time.time())}.mp4"
                
                # Get file size
                content_length = headers.get('Content-Length')
                size = int(content_length) if content_length else None
                
                # Get content type
                content_type = headers.get('Content-Type', 'video/mp4')
                
                return {
                    'filename': filename,
                    'size': size,
                    'content_type': content_type,
                    'headers': dict(headers)
                }
                
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return {'filename': f'video_{int(time.time())}.mp4', 'size': None}
    
    async def download_video(self, url: str, message: Message, progress_callback=None):
        """Download video with progress tracking"""
        try:
            await self.create_session()
            
            # Get file info first
            file_info = await self.get_file_info(url)
            filename = file_info['filename']
            total_size = file_info['size']
            
            # Clean filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # Create downloads directory if not exists
            os.makedirs('downloads', exist_ok=True)
            filepath = os.path.join('downloads', filename)
            
            # Download with progress
            chunk_size = 1024 * 1024  # 1MB chunks
            
            async with self.session.get(url) as response:
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    downloaded = 0
                    start_time = time.time()
                    
                    async for chunk in response.content.iter_chunked(chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Calculate progress
                            if total_size and progress_callback:
                                progress = (downloaded / total_size) * 100
                                
                                # Calculate speed
                                elapsed_time = time.time() - start_time
                                if elapsed_time > 0:
                                    speed = downloaded / elapsed_time / 1024 / 1024  # MB/s
                                    
                                    # Estimate remaining time
                                    if speed > 0 and total_size:
                                        remaining = (total_size - downloaded) / (speed * 1024 * 1024)
                                    else:
                                        remaining = 0
                                    
                                    await progress_callback(
                                        progress=min(progress, 100),
                                        downloaded=downloaded,
                                        total=total_size,
                                        speed=speed,
                                        remaining=remaining
                                    )
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            raise
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()

# Create downloader instance
downloader = TeraboxDownloader()

# Create Pyrogram Client
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Store active downloads
active_downloads = {}

def format_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes is None:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

async def progress_message(message: Message, progress_data: dict):
    """Update progress message"""
    try:
        progress = progress_data.get('progress', 0)
        downloaded = progress_data.get('downloaded', 0)
        total = progress_data.get('total', 0)
        speed = progress_data.get('speed', 0)
        remaining = progress_data.get('remaining', 0)
        
        # Create progress bar
        bar_length = 20
        filled_length = int(bar_length * progress / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Format text
        text = (
            f"**Download Progress:**\n\n"
            f"`{bar}` {progress:.1f}%\n\n"
            f"**Downloaded:** `{format_size(downloaded)} / {format_size(total)}`\n"
            f"**Speed:** `{speed:.2f} MB/s`\n"
            f"**Time Remaining:** `{remaining:.1f}s`\n\n"
            f"⏳ Downloading..."
        )
        
        # Edit message
        await message.edit_text(text)
        
    except Exception as e:
        logger.error(f"Error updating progress: {e}")

@app.on_message(filters.command(["start", "help"]))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    welcome_text = """
    🤖 **Terabox Video Downloader Bot**
    
    **Commands:**
    /start - Show this message
    /download - Download video from Terabox
    /status - Check bot status
    
    **How to use:**
    1. Send a Terabox share link
    2. Or use /download <terabox_url>
    
    **Features:**
    • Fast parallel downloads
    • Progress tracking
    • Resume support
    • High-speed downloads
    
    **Note:** Ensure your cookies are up-to-date!
    """
    
    await message.reply_text(welcome_text)

@app.on_message(filters.command("download"))
async def download_command(client: Client, message: Message):
    """Handle /download command"""
    if len(message.command) < 2:
        await message.reply_text("Please provide a Terabox URL.\nUsage: `/download https://terabox.com/s/...`")
        return
    
    url = message.command[1]
    await process_download(client, message, url)

@app.on_message(filters.regex(r'https?://(?:www\.)?(?:terabox\.app|1024tera\.com)'))
async def handle_terabox_link(client: Client, message: Message):
    """Handle Terabox links directly"""
    url = message.text
    await process_download(client, message, url)

async def process_download(client: Client, message: Message, url: str):
    """Process download request"""
    chat_id = message.chat.id
    
    # Check if already downloading
    if chat_id in active_downloads:
        await message.reply_text("You already have an active download. Please wait...")
        return
    
    try:
        # Send initial message
        status_msg = await message.reply_text("🔍 **Processing URL...**\n\nExtracting video information...")
        
        # Extract video info
        video_info = await downloader.extract_video_info(url)
        
        if not video_info or 'download_url' not in video_info:
            await status_msg.edit_text("❌ **Failed to extract video information.**\n\nPlease check:\n1. URL is valid\n2. Cookies are working\n3. Video is accessible")
            return
        
        download_url = video_info['download_url']
        file_info = video_info.get('file_info', {})
        filename = file_info.get('filename', 'video.mp4')
        file_size = file_info.get('size')
        
        # Confirm download
        confirm_text = (
            f"✅ **Video Found!**\n\n"
            f"**File:** `{filename}`\n"
            f"**Size:** `{format_size(file_size)}`\n\n"
            f"Do you want to download this video?"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, Download", callback_data=f"download_{url}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]
        ])
        
        await status_msg.edit_text(confirm_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error processing download: {e}")
        await message.reply_text(f"❌ **Error:** {str(e)}")

@app.on_callback_query()
async def handle_callback(client, callback_query):
    """Handle callback queries"""
    data = callback_query.data
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.id
    
    if data == "cancel":
        await callback_query.message.edit_text("❌ Download cancelled.")
        await callback_query.answer()
        return
    
    if data.startswith("download_"):
        url = data.replace("download_", "")
        
        # Mark as active download
        active_downloads[chat_id] = True
        
        try:
            # Update status
            await callback_query.message.edit_text("⬇️ **Starting download...**\n\nPlease wait, this may take a while...")
            
            # Create progress callback
            async def progress_callback(**kwargs):
                try:
                    await progress_message(callback_query.message, kwargs)
                except:
                    pass
            
            # Download the video
            download_path = await downloader.download_video(
                url,
                callback_query.message,
                progress_callback
            )
            
            # Get file info
            file_size = os.path.getsize(download_path)
            
            # Send video to user
            await callback_query.message.edit_text("📤 **Uploading to Telegram...**\n\nPlease wait...")
            
            # Split large files if needed (Telegram limit: 2GB)
            max_file_size = 1.9 * 1024 * 1024 * 1024  # 1.9GB
            
            if file_size > max_file_size:
                # Split file or send as document
                await client.send_document(
                    chat_id=chat_id,
                    document=download_path,
                    caption=f"📁 **File too large for streaming**\n\n**Size:** {format_size(file_size)}"
                )
            else:
                # Send as video
                await client.send_video(
                    chat_id=chat_id,
                    video=download_path,
                    caption=f"✅ **Download Complete!**\n\n**File:** `{os.path.basename(download_path)}`\n**Size:** `{format_size(file_size)}`"
                )
            
            # Clean up
            try:
                os.remove(download_path)
            except:
                pass
            
            await callback_query.message.edit_text("✅ **Download completed successfully!**")
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            await callback_query.message.edit_text(f"❌ **Download failed:** {str(e)}")
        
        finally:
            # Remove from active downloads
            active_downloads.pop(chat_id, None)
        
        await callback_query.answer()

@app.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    """Check bot status"""
    status_text = (
        f"🤖 **Bot Status**\n\n"
        f"**Active Downloads:** `{len(active_downloads)}`\n"
        f"**Cookies Loaded:** `{len(downloader.cookies)}`\n"
        f"**Session:** `{'Active' if downloader.session else 'Inactive'}`\n"
        f"**Uptime:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
        f"✅ **Bot is running normally**"
    )
    await message.reply_text(status_text)

@app.on_message(filters.command("refresh"))
async def refresh_cookies(client: Client, message: Message):
    """Refresh cookies"""
    try:
        downloader.cookies = downloader.load_cookies()
        await downloader.close()
        downloader.session = None
        await message.reply_text(f"✅ **Cookies refreshed!**\nLoaded {len(downloader.cookies)} cookies.")
    except Exception as e:
        await message.reply_text(f"❌ **Error refreshing cookies:** {str(e)}")

# Start the bot
if __name__ == "__main__":
    logger.info("Starting Terabox Downloader Bot...")
    
    # Ensure cookie file exists
    if not os.path.exists(COOKIE_FILE):
        logger.error(f"Cookie file {COOKIE_FILE} not found!")
        exit(1)
    
    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        # Clean up
        asyncio.run(downloader.close())
