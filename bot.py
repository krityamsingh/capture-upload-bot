#!/usr/bin/env python3
import os
import sys
import re
import asyncio
import aiohttp
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError
import time

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get environment variables
API_ID = int(os.environ.get("API_ID", "26676741"))
API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E")

# Check if all required variables are set
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("Missing environment variables!")
    sys.exit(1)

logger.info(f"API_ID: {API_ID}")
logger.info(f"API_HASH: {API_HASH[:10]}...")
logger.info(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")

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
        }
        
    async def create_session(self):
        """Create aiohttp session"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.base_headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def extract_share_id(self, url: str) -> str:
        """Extract share ID from URL"""
        patterns = [
            r'(?:terabox\.(?:com|app)|1024tera\.com|terafileshare\.com)/s/([a-zA-Z0-9_-]+)',
            r'/sharing/link\?surl=([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Fallback: extract last part of URL
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else None
    
    async def get_share_info(self, share_id: str) -> dict:
        """Get share information from Terabox"""
        try:
            await self.create_session()
            
            # Try multiple domains
            test_urls = [
                f"https://www.terabox.com/s/{share_id}",
                f"https://www.1024tera.com/s/{share_id}",
                f"https://www.terafileshare.com/s/{share_id}",
            ]
            
            for url in test_urls:
                try:
                    logger.info(f"Trying URL: {url}")
                    async with self.session.get(url, timeout=10) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Look for app_id
                            app_id_match = re.search(r'"app_id"\s*:\s*"(\d+)"', html)
                            if not app_id_match:
                                app_id_match = re.search(r"'app_id'\s*:\s*'(\d+)'", html)
                            if not app_id_match:
                                app_id_match = re.search(r'app_id["\']?\s*:\s*["\']?(\d+)', html)
                            
                            # Look for shorturl
                            shorturl_match = re.search(r'"shorturl"\s*:\s*"([^"]+)"', html)
                            if not shorturl_match:
                                shorturl_match = re.search(r"'shorturl'\s*:\s*'([^']+)'", html)
                            
                            if app_id_match and shorturl_match:
                                domain = url.split('/s/')[0]
                                return {
                                    'app_id': app_id_match.group(1),
                                    'shorturl': shorturl_match.group(1),
                                    'domain': domain,
                                    'share_id': share_id
                                }
                except Exception as e:
                    logger.warning(f"Failed to fetch {url}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error in get_share_info: {e}")
            return None
    
    async def get_file_list(self, share_info: dict) -> dict:
        """Get list of files from share"""
        try:
            await self.create_session()
            
            api_url = f"{share_info['domain']}/share/list"
            params = {
                'app_id': share_info['app_id'],
                'shorturl': share_info['shorturl'],
                'root': '1',
            }
            
            async with self.session.get(api_url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('errno') == 0:
                        return data
                    else:
                        logger.error(f"API error: {data}")
                else:
                    logger.error(f"HTTP error: {response.status}")
                return None
                
        except Exception as e:
            logger.error(f"Error in get_file_list: {e}")
            return None
    
    async def get_download_url(self, share_info: dict, fs_id: str) -> str:
        """Get direct download URL for file"""
        try:
            await self.create_session()
            
            api_url = f"{share_info['domain']}/api/download"
            payload = {
                'method': 'locatedownload',
                'app_id': share_info['app_id'],
                'fs_id': fs_id,
                'timestamp': int(time.time() * 1000),
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Referer': f"{share_info['domain']}/s/{share_info['share_id']}",
                **self.base_headers
            }
            
            async with self.session.post(api_url, json=payload, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('errno') == 0 and data.get('url'):
                        return data['url']
                    else:
                        logger.error(f"Download API error: {data}")
                return None
                
        except Exception as e:
            logger.error(f"Error in get_download_url: {e}")
            return None
    
    async def extract_video_info(self, url: str) -> dict:
        """Main function to extract video information"""
        try:
            # Extract share ID
            share_id = await self.extract_share_id(url)
            if not share_id:
                logger.error(f"Could not extract share ID from: {url}")
                return None
            
            logger.info(f"Extracted share ID: {share_id}")
            
            # Get share info
            share_info = await self.get_share_info(share_id)
            if not share_info:
                logger.error("Could not get share info")
                return None
            
            logger.info(f"Got share info: {share_info}")
            
            # Get file list
            file_data = await self.get_file_list(share_info)
            if not file_data:
                logger.error("Could not get file list")
                return None
            
            file_list = file_data.get('list', [])
            if not file_list:
                logger.error("Empty file list")
                return None
            
            # Find first video file
            video_file = None
            for file_item in file_list:
                if file_item.get('isdir') == 0:  # Not a directory
                    filename = file_item.get('server_filename', '').lower()
                    if any(filename.endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']):
                        video_file = file_item
                        break
            
            # If no video found, use first file
            if not video_file and file_list:
                video_file = file_list[0]
            
            if not video_file:
                logger.error("No files found in share")
                return None
            
            # Get download URL
            fs_id = video_file.get('fs_id')
            download_url = await self.get_download_url(share_info, fs_id)
            
            if not download_url:
                logger.error("Could not get download URL")
                return None
            
            return {
                'download_url': download_url,
                'filename': video_file.get('server_filename', 'video.mp4'),
                'size': video_file.get('size', 0),
                'share_id': share_id,
            }
            
        except Exception as e:
            logger.error(f"Error in extract_video_info: {e}")
            return None
    
    async def download_video(self, url: str, filename: str, progress_callback=None) -> str:
        """Download video with progress tracking"""
        try:
            await self.create_session()
            
            # Create downloads directory
            os.makedirs('downloads', exist_ok=True)
            
            # Clean filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = os.path.join('downloads', filename)
            
            # Get file size first
            async with self.session.head(url, allow_redirects=True) as response:
                total_size = int(response.headers.get('Content-Length', 0))
            
            # Download file
            async with self.session.get(url) as response:
                response.raise_for_status()
                
                downloaded = 0
                start_time = time.time()
                
                with open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024*1024):  # 1MB chunks
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Call progress callback if provided
                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed / 1024 / 1024 if elapsed > 0 else 0
                                remaining = (total_size - downloaded) / (speed * 1024 * 1024) if speed > 0 else 0
                                
                                # Call async callback
                                if asyncio.iscoroutinefunction(progress_callback):
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

# Create downloader instance
downloader = TeraboxDownloader()

# Create Pyrogram client
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

# Helper functions
def format_size(size_bytes):
    """Format file size in human readable format"""
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
        
        # Create progress bar
        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        text = (
            f"**📥 Downloading...**\n\n"
            f"`{bar}` **{progress:.1f}%**\n\n"
            f"**📊 Progress:** `{format_size(downloaded)} / {format_size(total)}`\n"
            f"**⚡ Speed:** `{speed:.2f} MB/s`\n"
            f"**⏳ Time Left:** `{remaining:.1f}s`"
        )
        
        await message.edit_text(text)
        
    except Exception as e:
        logger.error(f"Error updating progress: {e}")

# Command handlers
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    text = """
    🤖 **Terabox Video Downloader Bot** 🤖
    
    **I can download videos from:**
    • terabox.com
    • 1024tera.com
    • terafileshare.com
    
    **How to use:**
    1. Send me a Terabox share link
    2. I'll extract and download the video
    3. You'll receive the video directly
    
    **Example links:**
    `https://terabox.com/s/1tgHSFjB1Jjv1tLdX8sGLiA`
    `https://terafileshare.com/s/xxxxxxx`
    `https://1024tera.com/s/xxxxxxx`
    
    **Commands:**
    /start - Show this message
    /status - Check bot status
    /ping - Test bot response
    
    **Note:** Only works with public links!
    """
    
    await message.reply_text(text)

@app.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    """Handle /status command"""
    status_text = """
    ✅ **Bot Status: Online**
    
    **Service:** Heroku
    **Session:** Active
    **Downloader:** Ready
    
    Send me a Terabox link to test!
    """
    await message.reply_text(status_text)

@app.on_message(filters.command("ping"))
async def ping_command(client: Client, message: Message):
    """Handle /ping command"""
    start = time.time()
    msg = await message.reply_text("🏓 Pong!")
    end = time.time()
    await msg.edit_text(f"🏓 Pong! `{round((end - start) * 1000, 2)}ms`")

@app.on_message(filters.regex(
    r'https?://(?:www\.)?(?:terabox\.(?:com|app)|1024tera\.com|terafileshare\.com)'
))
async def handle_terabox_link(client: Client, message: Message):
    """Handle Terabox links"""
    url = message.text.strip()
    
    try:
        # Send initial message
        status_msg = await message.reply_text("🔍 **Processing link...**\n\nExtracting video information...")
        
        # Extract video info
        video_info = await downloader.extract_video_info(url)
        
        if not video_info:
            await status_msg.edit_text(
                "❌ **Failed to extract video information.**\n\n"
                "Possible reasons:\n"
                "• Link is private or requires password\n"
                "• Link has expired\n"
                "• Video was removed\n"
                "• Server is busy\n\n"
                "**Try:**\n"
                "1. Make sure the link is public\n"
                "2. Check if the link is still valid\n"
                "3. Try again in a few minutes"
            )
            return
        
        download_url = video_info['download_url']
        filename = video_info['filename']
        size = video_info['size']
        
        # Show video info
        info_text = (
            f"✅ **Video Found!**\n\n"
            f"**📹 File:** `{filename}`\n"
            f"**📦 Size:** `{format_size(size)}`\n"
            f"**🔗 Type:** Public Link\n\n"
            f"Click Download to start!"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬇️ Download", callback_data=f"dl_{url}"),
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
            
            # Get video info again
            video_info = await downloader.extract_video_info(url)
            if not video_info:
                await message.edit_text("❌ Failed to get video information.")
                await callback_query.answer()
                return
            
            download_url = video_info['download_url']
            filename = video_info['filename']
            
            # Progress callback
            async def progress_callback(**kwargs):
                try:
                    await update_progress(message, kwargs)
                except:
                    pass
            
            # Download video
            download_path = await downloader.download_video(
                download_url,
                filename,
                progress_callback
            )
            
            # Get file size
            file_size = os.path.getsize(download_path)
            
            # Upload to Telegram
            await message.edit_text("📤 **Uploading to Telegram...**")
            
            try:
                # Try to send as video
                await client.send_video(
                    chat_id=message.chat.id,
                    video=download_path,
                    caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`",
                    supports_streaming=True,
                    progress=lambda current, total: logger.info(f"Upload: {current}/{total}")
                )
                await message.delete()
            except Exception as e:
                # If video fails, send as document
                logger.error(f"Video upload failed: {e}, sending as document")
                await client.send_document(
                    chat_id=message.chat.id,
                    document=download_path,
                    caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`"
                )
                await message.delete()
            
            # Clean up
            try:
                os.remove(download_path)
            except:
                pass
            
            logger.info(f"Successfully sent video: {filename}")
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            await message.edit_text(f"❌ **Download failed:** {str(e)}")
        
        await callback_query.answer()

async def main():
    """Main function to run the bot"""
    logger.info("Starting Terabox Downloader Bot...")
    
    # Ensure downloads directory exists
    os.makedirs('downloads', exist_ok=True)
    
    try:
        await app.start()
        logger.info("Bot started successfully!")
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"Bot: @{me.username} (ID: {me.id})")
        
        # Send startup message to owner (optional)
        # You can add your Telegram ID here
        # await app.send_message(YOUR_CHAT_ID, "🤖 Bot started successfully!")
        
        # Keep bot running
        await idle()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
    finally:
        await app.stop()
        await downloader.close()
        logger.info("Bot stopped.")

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())
