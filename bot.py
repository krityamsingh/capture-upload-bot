import os
import re
import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import base64
import hashlib
from datetime import datetime

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

class TeraboxDownloader:
    def __init__(self):
        self.session = None
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Referer': 'https://www.terabox.com/',
            'Origin': 'https://www.terabox.com',
        }
        
    async def create_session(self):
        """Create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.base_headers)
    
    async def extract_share_id(self, url: str) -> Optional[str]:
        """Extract share ID from various Terabox URL formats"""
        patterns = [
            r'terabox\.(?:com|app)/(?:s/|sharing/link\?surl=)?([a-zA-Z0-9_-]+)',
            r'1024tera\.com/(?:s/)?([a-zA-Z0-9_-]+)',
            r'/([a-zA-Z0-9_-]{9,})(?:\?|$)',
            r'pwd=([a-zA-Z0-9]+)',
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
    
    async def get_share_info(self, share_id: str) -> Optional[Dict]:
        """Get share information from Terabox API"""
        try:
            await self.create_session()
            
            # Get share page to extract tokens
            share_url = f"https://www.terabox.com/s/{share_id}"
            
            async with self.session.get(share_url) as response:
                html = await response.text()
                
                # Extract app_id and shorturl
                app_id_match = re.search(r'"app_id"\s*:\s*(\d+)', html)
                shorturl_match = re.search(r'"shorturl"\s*:\s*"([^"]+)"', html)
                uk_match = re.search(r'"uk"\s*:\s*"([^"]+)"', html)
                shareid_match = re.search(r'"shareid"\s*:\s*(\d+)', html)
                
                if not all([app_id_match, shorturl_match]):
                    # Try alternative pattern
                    app_id_match = re.search(r'window\.APP_ID\s*=\s*(\d+)', html)
                    shorturl_match = re.search(r'window\.SHORT_URL\s*=\s*"([^"]+)"', html)
                
                if app_id_match and shorturl_match:
                    return {
                        'app_id': app_id_match.group(1),
                        'shorturl': shorturl_match.group(1),
                        'uk': uk_match.group(1) if uk_match else None,
                        'shareid': shareid_match.group(1) if shareid_match else None,
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting share info: {e}")
            return None
    
    async def get_file_list(self, share_info: Dict) -> Optional[Dict]:
        """Get file list from share"""
        try:
            headers = self.base_headers.copy()
            headers.update({
                'Content-Type': 'application/json',
            })
            
            # Build API URL
            api_url = "https://www.terabox.com/share/list"
            
            params = {
                'app_id': share_info['app_id'],
                'shorturl': share_info['shorturl'],
                'root': '1',
            }
            
            if share_info.get('uk'):
                params['uk'] = share_info['uk']
            
            async with self.session.get(api_url, params=params, headers=headers) as response:
                data = await response.json()
                
                if data.get('errno') == 0:
                    return data
                else:
                    logger.error(f"API Error: {data}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting file list: {e}")
            return None
    
    async def get_download_url(self, file_data: Dict) -> Optional[str]:
        """Get download URL for a file"""
        try:
            headers = self.base_headers.copy()
            headers.update({
                'Content-Type': 'application/json',
            })
            
            api_url = "https://www.terabox.com/api/download"
            
            payload = {
                'method': 'locatedownload',
                'app_id': file_data.get('app_id', '250528'),
                'fs_id': file_data['fs_id'],
                'timestamp': int(time.time() * 1000),
                'sign': '1',
                'uid': file_data.get('uk'),
                'web': '1',
            }
            
            async with self.session.post(api_url, json=payload, headers=headers) as response:
                data = await response.json()
                
                if data.get('errno') == 0:
                    return data.get('url')
                else:
                    logger.error(f"Download API Error: {data}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
            return None
    
    async def extract_video_info(self, url: str) -> Optional[Dict]:
        """Extract video information from Terabox URL"""
        try:
            await self.create_session()
            
            # Extract share ID
            share_id = await self.extract_share_id(url)
            if not share_id:
                logger.error(f"Could not extract share ID from: {url}")
                return None
            
            logger.info(f"Extracted share ID: {share_id}")
            
            # Get share information
            share_info = await self.get_share_info(share_id)
            if not share_info:
                logger.error("Could not get share information")
                return None
            
            logger.info(f"Share info: {share_info}")
            
            # Get file list
            file_list = await self.get_file_list(share_info)
            if not file_list or 'list' not in file_list:
                logger.error("Could not get file list")
                return None
            
            # Find video files
            video_files = []
            for item in file_list['list']:
                if item.get('isdir') == 0:  # Not a directory
                    # Check if it's a video file
                    category = item.get('category', 0)
                    if category == 6 or item.get('server_filename', '').lower().endswith(
                        ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v')
                    ):
                        video_files.append(item)
            
            if not video_files:
                logger.error("No video files found in share")
                return None
            
            # Get download URL for the first video
            video_data = video_files[0]
            video_data['app_id'] = share_info['app_id']
            video_data['uk'] = share_info.get('uk')
            
            download_url = await self.get_download_url(video_data)
            if not download_url:
                logger.error("Could not get download URL")
                return None
            
            # Prepare file info
            file_info = {
                'filename': video_data.get('server_filename', f'video_{int(time.time())}.mp4'),
                'size': video_data.get('size', 0),
                'fs_id': video_data.get('fs_id'),
                'md5': video_data.get('md5'),
            }
            
            return {
                'download_url': download_url,
                'file_info': file_info,
                'share_id': share_id,
                'video_count': len(video_files),
                'all_files': video_files,
            }
            
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            return None
    
    async def download_video(self, url: str, message: Message, progress_callback=None):
        """Download video with progress tracking"""
        try:
            await self.create_session()
            
            # Get file info
            async with self.session.head(url, allow_redirects=True) as response:
                headers = response.headers
                
                # Get filename
                content_disposition = headers.get('Content-Disposition', '')
                filename_match = re.search(r'filename="([^"]+)"', content_disposition)
                
                if filename_match:
                    filename = filename_match.group(1)
                else:
                    filename = url.split('/')[-1].split('?')[0] or f'video_{int(time.time())}.mp4'
                
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                total_size = int(headers.get('Content-Length', 0))
            
            # Create downloads directory
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
                            
                            # Call progress callback
                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed / 1024 / 1024 if elapsed > 0 else 0
                                remaining = (total_size - downloaded) / (speed * 1024 * 1024) if speed > 0 else 0
                                
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
        """Close session"""
        if self.session:
            await self.session.close()

# Create downloader instance
downloader = TeraboxDownloader()

# Create Pyrogram Client
app = Client(
    "terabox_downloader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Helper functions
def format_size(size_bytes):
    """Format file size"""
    if not size_bytes or size_bytes == 0:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

async def update_progress(message: Message, progress_data: dict):
    """Update progress message"""
    try:
        progress = progress_data.get('progress', 0)
        downloaded = progress_data.get('downloaded', 0)
        total = progress_data.get('total', 0)
        speed = progress_data.get('speed', 0)
        remaining = progress_data.get('remaining', 0)
        
        # Progress bar
        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        text = (
            f"**📥 Downloading...**\n\n"
            f"`{bar}` **{progress:.1f}%**\n\n"
            f"**📊 Progress:** `{format_size(downloaded)} / {format_size(total)}`\n"
            f"**⚡ Speed:** `{speed:.2f} MB/s`\n"
            f"**⏳ Time Left:** `{remaining:.1f}s`\n\n"
            f"🔄 Processing..."
        )
        
        await message.edit_text(text)
        
    except Exception as e:
        logger.error(f"Progress update error: {e}")

# Command handlers
@app.on_message(filters.command(["start", "help"]))
async def start_command(client: Client, message: Message):
    """Start command handler"""
    text = """
    🤖 **Terabox Video Downloader Bot** 🤖
    
    **I can download videos from:**
    • terabox.com
    • 1024tera.com
    • terabox.app
    
    **How to use:**
    1. Send me a Terabox share link
    2. I'll extract and download the video
    3. You'll receive the video directly
    
    **Features:**
    ✅ Fast downloads
    ✅ Progress tracking
    ✅ Multiple video support
    ✅ No size limits (if supported by Telegram)
    
    **Examples:**
    `https://terabox.com/s/1AbcDeFgHiJk`
    `https://www.terabox.com/sharing/link?surl=xyz123`
    
    **Note:** For private links, you may need to use /cookie command
    """
    
    await message.reply_text(text)

@app.on_message(filters.command("cookie"))
async def cookie_command(client: Client, message: Message):
    """Handle cookie submission"""
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text(
            "Please reply to a cookies.txt file with this command.\n\n"
            "How to get cookies:\n"
            "1. Login to Terabox in browser\n"
            "2. Export cookies using an extension\n"
            "3. Send the cookies.txt file\n\n"
            "Reply to your cookies.txt file with: `/cookie`"
        )
        return
    
    try:
        # Download the cookie file
        cookie_file = await message.reply_to_message.download()
        
        # Read and parse cookies
        cookies = {}
        with open(cookie_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        name, value = parts[5], parts[6]
                        cookies[name] = value
        
        # Update downloader session
        if downloader.session:
            await downloader.close()
            downloader.session = None
        
        # Recreate session with cookies
        await downloader.create_session()
        downloader.session.cookie_jar.update_cookies(cookies)
        
        await message.reply_text(f"✅ Cookies updated! Loaded {len(cookies)} cookies.")
        
        # Clean up
        os.remove(cookie_file)
        
    except Exception as e:
        await message.reply_text(f"❌ Error updating cookies: {str(e)}")

@app.on_message(filters.regex(
    r'https?://(?:www\.)?(?:terabox\.(?:com|app)|1024tera\.com)'
))
async def handle_terabox_link(client: Client, message: Message):
    """Handle Terabox links"""
    url = message.text.strip()
    chat_id = message.chat.id
    
    try:
        # Send initial message
        status_msg = await message.reply_text(
            "🔍 **Processing URL...**\n\n"
            "Extracting video information..."
        )
        
        # Extract video info
        video_info = await downloader.extract_video_info(url)
        
        if not video_info:
            await status_msg.edit_text(
                "❌ **Failed to extract video information.**\n\n"
                "Possible reasons:\n"
                "• Link is private/protected\n"
                "• Link has expired\n"
                "• Video was removed\n\n"
                "**Try:**\n"
                "1. Make sure link is public\n"
                "2. Use /cookie command with your cookies\n"
                "3. Check if link is valid"
            )
            return
        
        download_url = video_info['download_url']
        file_info = video_info['file_info']
        filename = file_info['filename']
        size = file_info['size']
        
        # Show video info
        info_text = (
            f"✅ **Video Found!**\n\n"
            f"**📹 Title:** `{filename}`\n"
            f"**📦 Size:** `{format_size(size)}`\n"
            f"**🔗 Type:** Public Link\n\n"
            f"Do you want to download this video?"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Download", callback_data=f"dl_{url}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]
        ])
        
        await status_msg.edit_text(info_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error handling link: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

@app.on_callback_query()
async def handle_callback(client, callback_query):
    """Handle callback queries"""
    data = callback_query.data
    message = callback_query.message
    
    if data == "cancel":
        await message.edit_text("❌ Download cancelled.")
        await callback_query.answer()
        return
    
    if data.startswith("dl_"):
        url = data.replace("dl_", "")
        
        try:
            # Update status
            await message.edit_text("⬇️ **Starting download...**\n\nPlease wait...")
            
            # Progress callback
            async def progress_callback(**kwargs):
                try:
                    await update_progress(message, kwargs)
                except:
                    pass
            
            # Download video
            download_path = await downloader.download_video(
                url,
                message,
                progress_callback
            )
            
            # Get file info
            file_size = os.path.getsize(download_path)
            
            # Upload to Telegram
            await message.edit_text("📤 **Uploading to Telegram...**")
            
            try:
                # Try to send as video
                await client.send_video(
                    chat_id=message.chat.id,
                    video=download_path,
                    caption=f"✅ **Download Complete!**\n\n**File:** `{os.path.basename(download_path)}`\n**Size:** `{format_size(file_size)}`",
                    progress=lambda current, total: logger.info(f"Upload progress: {current}/{total}")
                )
                await message.delete()
            except Exception as e:
                # If video fails, try as document
                logger.error(f"Video upload failed, trying document: {e}")
                await client.send_document(
                    chat_id=message.chat.id,
                    document=download_path,
                    caption=f"✅ **Download Complete!**\n\n**File:** `{os.path.basename(download_path)}`\n**Size:** `{format_size(file_size)}`"
                )
                await message.delete()
            
            # Clean up
            try:
                os.remove(download_path)
            except:
                pass
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            await message.edit_text(f"❌ **Download failed:** {str(e)}")
        
        await callback_query.answer()

@app.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    """Check bot status"""
    status_text = (
        "🤖 **Bot Status**\n\n"
        f"**Status:** ✅ Running\n"
        f"**Session:** {'✅ Active' if downloader.session else '❌ Inactive'}\n"
        f"**Uptime:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "Ready to download videos!"
    )
    await message.reply_text(status_text)

@app.on_message(filters.command("ping"))
async def ping_command(client: Client, message: Message):
    """Ping command"""
    start_time = time.time()
    msg = await message.reply_text("🏓 Pong!")
    end_time = time.time()
    await msg.edit_text(f"🏓 Pong! `{round((end_time - start_time) * 1000, 2)}ms`")

# Start bot
async def main():
    """Main function"""
    logger.info("Starting Terabox Downloader Bot...")
    await app.start()
    logger.info("Bot started!")
    await idle()
    await app.stop()
    await downloader.close()
    logger.info("Bot stopped!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
