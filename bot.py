# bot.py - COMPLETE DOWNLOAD BOT
import os
import re
import asyncio
import aiohttp
import json
import logging
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import aiofiles

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get credentials
API_ID = int(os.environ.get("API_ID", "26676741"))
API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E")

# Create client
app = Client("teraboxbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store active downloads
active_downloads = {}

class TeraboxDownloader:
    def __init__(self):
        self.session = None
        self.cookies = {}
        self.load_cookies()
    
    def load_cookies(self):
        """Load cookies from cookies.txt"""
        try:
            if os.path.exists("cookies.txt"):
                with open("cookies.txt", "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                name = parts[5]
                                value = parts[6]
                                self.cookies[name] = value
                logger.info(f"Loaded {len(self.cookies)} cookies")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False
    
    async def get_session(self):
        """Create aiohttp session with cookies"""
        if not self.session:
            jar = aiohttp.CookieJar()
            for name, value in self.cookies.items():
                jar.update_cookies({name: value})
            
            self.session = aiohttp.ClientSession(
                cookie_jar=jar,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )
        return self.session
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def extract_shortcode(self, url):
        """Extract shortcode from URL"""
        patterns = [
            r'/(?:s/|sharing/link\?surl=)([a-zA-Z0-9_-]+)',
            r'/([a-zA-Z0-9_-]{9,})(?:\?|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def get_video_info(self, url):
        """Get video information from Terabox URL"""
        try:
            session = await self.get_session()
            shortcode = await self.extract_shortcode(url)
            
            if not shortcode:
                return None
            
            # First get the page to extract tokens
            page_url = f"https://www.1024tera.com/s/{shortcode}"
            async with session.get(page_url) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Extract app_id (usually 250528)
                    app_id = "250528"
                    
                    # Extract shareid and uk
                    shareid_match = re.search(r'"shareid"\s*:\s*(\d+)', html)
                    shareid = shareid_match.group(1) if shareid_match else None
                    
                    uk_match = re.search(r'"uk"\s*:\s*"([^"]+)"', html)
                    uk = uk_match.group(1) if uk_match else None
                    
                    # Get file list
                    list_url = "https://www.1024tera.com/share/list"
                    params = {
                        'app_id': app_id,
                        'shorturl': shortcode,
                        'root': '1',
                    }
                    if uk:
                        params['uk'] = uk
                    
                    async with session.get(list_url, params=params) as list_response:
                        if list_response.status == 200:
                            data = await list_response.json()
                            if data.get('errno') == 0 and data.get('list'):
                                file_info = data['list'][0]
                                
                                # Get download URL
                                download_url = "https://www.1024tera.com/api/download"
                                payload = {
                                    'app_id': app_id,
                                    'fs_id': file_info.get('fs_id'),
                                    'timestamp': int(time.time() * 1000),
                                    'shareid': shareid,
                                    'uk': uk,
                                    'sign': '1',
                                    'method': 'locatedownload'
                                }
                                
                                headers = {
                                    'Content-Type': 'application/json',
                                    'Referer': f"https://www.1024tera.com/s/{shortcode}"
                                }
                                
                                async with session.post(download_url, json=payload, headers=headers) as dl_response:
                                    if dl_response.status == 200:
                                        dl_data = await dl_response.json()
                                        if dl_data.get('errno') == 0:
                                            # Get download link
                                            if dl_data.get('url'):
                                                download_link = dl_data['url']
                                            elif dl_data.get('dlink'):
                                                download_link = dl_data['dlink']
                                            else:
                                                return None
                                            
                                            return {
                                                'download_url': download_link,
                                                'filename': file_info.get('server_filename', f'video_{shortcode}.mp4'),
                                                'size': file_info.get('size', 0),
                                                'success': True
                                            }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
        
        return None
    
    async def download_file(self, url, filepath, progress_callback=None):
        """Download file with progress"""
        try:
            session = await self.get_session()
            
            # Get file size
            async with session.head(url) as response:
                total_size = int(response.headers.get('Content-Length', 0))
            
            # Download file
            downloaded = 0
            start_time = time.time()
            
            async with session.get(url) as response:
                if response.status != 200:
                    return False
                
                async with aiofiles.open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024*1024):  # 1MB chunks
                        if chunk:
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Call progress callback
                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                await progress_callback(progress, downloaded, total_size)
            
            return True
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False

# Create downloader
downloader = TeraboxDownloader()

def format_size(size_bytes):
    """Format file size"""
    if not size_bytes:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

async def update_progress(message, progress, downloaded, total):
    """Update progress message"""
    try:
        # Create progress bar
        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        # Calculate speed and ETA
        elapsed = time.time() - active_downloads.get(message.chat.id, {}).get('start_time', time.time())
        if elapsed > 0:
            speed = downloaded / elapsed
            eta = (total - downloaded) / speed if speed > 0 else 0
            speed_text = f"{format_size(speed)}/s"
            eta_text = f"{int(eta//60)}m {int(eta%60)}s"
        else:
            speed_text = "0 B/s"
            eta_text = "--"
        
        text = (
            f"📥 **Downloading...**\n\n"
            f"`{bar}` **{progress:.1f}%**\n\n"
            f"**Progress:** `{format_size(downloaded)} / {format_size(total)}`\n"
            f"**Speed:** `{speed_text}`\n"
            f"**ETA:** `{eta_text}`"
        )
        
        await message.edit_text(text)
    except Exception as e:
        logger.error(f"Progress update error: {e}")

@app.on_message(filters.command("start"))
async def start_command(client, message):
    """Handle /start command"""
    try:
        if message.chat.type != "private":
            await message.reply_text("⚠️ Please message me privately!")
            return
            
        cookies_status = "✅ Cookies loaded" if len(downloader.cookies) > 0 else "❌ No cookies"
        
        await message.reply_text(
            f"🤖 **Terabox Downloader Bot**\n\n"
            f"{cookies_status}\n"
            f"✅ Bot is ready!\n\n"
            "Send me any Terabox link to download videos directly to your DM!"
        )
    except Exception as e:
        logger.error(f"Start error: {e}")

@app.on_message(filters.command("status"))
async def status_command(client, message):
    """Check bot status"""
    try:
        cookies_status = f"{len(downloader.cookies)} cookies" if len(downloader.cookies) > 0 else "No cookies"
        await message.reply_text(
            f"✅ **Bot Status**\n\n"
            f"**Cookies:** {cookies_status}\n"
            f"**Active Downloads:** {len(active_downloads)}\n"
            f"**Session:** {'Active' if downloader.session else 'Inactive'}"
        )
    except Exception as e:
        logger.error(f"Status error: {e}")

@app.on_message(filters.command("ping"))
async def ping_command(client, message):
    """Ping command"""
    try:
        await message.reply_text("🏓 Pong! Bot is alive!")
    except Exception as e:
        logger.error(f"Ping error: {e}")

@app.on_message(filters.private & filters.text)
async def handle_messages(client, message):
    """Handle all private text messages"""
    try:
        text = message.text.strip()
        
        # Skip commands
        if text.startswith('/'):
            return
        
        # Check if it's a Terabox link
        if any(word in text.lower() for word in ['terabox', '1024tera', 'terafileshare']):
            if len(downloader.cookies) == 0:
                await message.reply_text("❌ No cookies loaded! Please add cookies.txt file.")
                return
            
            user_id = message.from_user.id
            if user_id in active_downloads:
                await message.reply_text("⏳ You already have an active download!")
                return
            
            # Mark as processing
            active_downloads[user_id] = {'processing': True}
            
            # Send processing message
            status_msg = await message.reply_text(
                f"🔍 **Processing link...**\n\n"
                f"**URL:** `{text[:50]}...`\n"
                f"**Status:** Extracting video information..."
            )
            
            # Get video info
            video_info = await downloader.get_video_info(text)
            
            if not video_info or not video_info.get('success'):
                await status_msg.edit_text(
                    "❌ **Failed to get video!**\n\n"
                    "Possible reasons:\n"
                    "• Invalid link\n"
                    "• Cookies expired\n"
                    "• Video removed\n"
                    "• Server error"
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
                f"**File:** `{filename}`\n"
                f"**Size:** `{format_size(file_size)}`\n\n"
                f"Click below to download:"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬇️ Download Now", callback_data=f"download_{user_id}_{filename}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
            ])
            
            # Store download info
            active_downloads[user_id] = {
                'download_url': download_url,
                'filename': filename,
                'size': file_size,
                'status_msg': status_msg,
                'processing': False
            }
            
            await status_msg.edit_text(confirm_text, reply_markup=keyboard)
            
        else:
            await message.reply_text(
                "📩 **Send me a Terabox link!**\n\n"
                "I can download from:\n"
                "• terabox.com\n"
                "• 1024tera.com\n"
                "• terafileshare.com\n\n"
                "Just paste your link here!"
            )
    except Exception as e:
        logger.error(f"Message handler error: {e}")
        if message.from_user.id in active_downloads:
            del active_downloads[message.from_user.id]

@app.on_callback_query(filters.regex(r"^download_"))
async def download_callback(client, callback_query):
    """Handle download button"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    try:
        # Extract filename from callback data
        parts = data.split('_')
        if len(parts) < 3:
            await callback_query.answer("Invalid request!")
            return
        
        callback_user_id = int(parts[1])
        filename = '_'.join(parts[2:])
        
        if callback_user_id != user_id:
            await callback_query.answer("Not your download!", show_alert=True)
            return
        
        if user_id not in active_downloads:
            await callback_query.answer("Download expired!", show_alert=True)
            return
        
        await callback_query.answer("Starting download...")
        
        download_info = active_downloads[user_id]
        download_url = download_info['download_url']
        message = download_info['status_msg']
        
        # Start download
        await message.edit_text(
            f"⬇️ **Starting Download...**\n\n"
            f"**File:** `{filename}`\n"
            f"**Size:** `{format_size(download_info['size'])}`\n"
            f"**Status:** Downloading..."
        )
        
        # Define progress callback
        async def progress_callback(progress, downloaded, total):
            if user_id in active_downloads:
                await update_progress(message, progress, downloaded, total)
        
        # Create filepath
        timestamp = int(time.time())
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filepath = f"downloads/{user_id}_{timestamp}_{safe_filename}"
        
        # Ensure downloads directory exists
        os.makedirs("downloads", exist_ok=True)
        
        # Start time for progress
        active_downloads[user_id]['start_time'] = time.time()
        
        # Download file
        success = await downloader.download_file(
            download_url,
            filepath,
            progress_callback
        )
        
        if not success:
            await message.edit_text("❌ Download failed!")
            if os.path.exists(filepath):
                os.remove(filepath)
            if user_id in active_downloads:
                del active_downloads[user_id]
            return
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Upload to Telegram
        await message.edit_text("📤 **Uploading to your DM...**")
        
        try:
            # Send as video
            await client.send_video(
                chat_id=user_id,
                video=filepath,
                caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`",
                supports_streaming=True
            )
            
            # Update message
            await message.edit_text(
                f"✅ **Successfully Sent!**\n\n"
                f"**File:** `{filename}`\n"
                f"**Size:** `{format_size(file_size)}`\n\n"
                f"Video sent to your DM!"
            )
            
        except FloodWait as e:
            # Handle flood wait
            wait_time = e.value
            await message.edit_text(f"⏳ Please wait {wait_time}s...")
            await asyncio.sleep(wait_time)
            
            # Retry
            await client.send_video(
                chat_id=user_id,
                video=filepath,
                caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`",
                supports_streaming=True
            )
            await message.edit_text("✅ Video sent to your DM!")
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            # Try as document
            try:
                await client.send_document(
                    chat_id=user_id,
                    document=filepath,
                    caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`"
                )
                await message.edit_text("✅ File sent to your DM!")
            except Exception as e2:
                await message.edit_text(f"❌ Upload failed: {str(e2)}")
        
        # Cleanup
        try:
            os.remove(filepath)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Download callback error: {e}")
        await callback_query.message.edit_text(f"❌ Error: {str(e)}")
    
    finally:
        if user_id in active_downloads:
            del active_downloads[user_id]

@app.on_callback_query(filters.regex(r"^cancel_"))
async def cancel_callback(client, callback_query):
    """Handle cancel button"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    try:
        parts = data.split('_')
        if len(parts) < 2:
            return
        
        callback_user_id = int(parts[1])
        
        if callback_user_id != user_id:
            await callback_query.answer("Not your download!", show_alert=True)
            return
        
        if user_id in active_downloads:
            del active_downloads[user_id]
        
        await callback_query.message.edit_text("❌ Download cancelled.")
        await callback_query.answer("Cancelled")
    except Exception as e:
        logger.error(f"Cancel callback error: {e}")

# Main function
async def main():
    """Main function"""
    logger.info("Starting Terabox Downloader Bot...")
    logger.info(f"Cookies loaded: {len(downloader.cookies)}")
    
    try:
        await app.start()
        logger.info("✅ Bot started successfully!")
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"Bot: @{me.username}")
        
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
    # Ensure downloads directory exists
    os.makedirs("downloads", exist_ok=True)
    
    # Run the bot
    asyncio.run(main())
