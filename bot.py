# bot.py - COMPLETE DOWNLOAD SYSTEM
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
from pyrogram.errors import FloodWait, RPCError
import aiofiles

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get credentials
API_ID = int(os.environ.get("API_ID", "26676741"))
API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E")

# Ensure directories exist
os.makedirs("downloads", exist_ok=True)

# Create cookies file
COOKIES_CONTENT = """.1024tera.com	TRUE	/	FALSE	1775120492	browserid	4V1elzoKTZ7pTEBLp_vHA9QIJoiLYpZaBxaHJ_NEpCryUX3v5XJX4KpLzEo=
.1024tera.com	TRUE	/	FALSE	1772531231	lang	en
.1024tera.com	TRUE	/	FALSE	1801472492	TSID	MvUeOemI9CRbdNw7wxRDjZf1eMqSVapF
.1024tera.com	TRUE	/	FALSE	1775123231	shareUpdateRandom	97
.1024tera.com	TRUE	/	FALSE	1804499232	__bid_n	19c186fa5d9814629b4207
.1024tera.com	TRUE	/	TRUE	1801472552	ndus	YQjKZL8peHuipOIVKwKsnrUz82kNQfu2Kk936GL7
dm.1024tera.com	FALSE	/	FALSE	0	csrfToken	X2qpBfnEoM6UXY4_kTa08sBf
dm.1024tera.com	FALSE	/	FALSE	1772531232	ndut_fmt	E2D9670B528107927362DA057D745265896AAD3074E81B5AE789F685649DA0A5
dm.1024tera.com	FALSE	/	FALSE	1772531235	ndut_fmv	6ec573e6027ec9f4f82dbd862d9e762eee3745caeb28b072ac1ed7a3accd9d113354223ec9bb7661ea456acc0f021f9ad815c0182013b2ada8bfac035e4a99efee480d782e58f64e0839dace4e90ceb0241ba32717aa2aecdaded096ce11a9d030e254fe51bb42eca2b8fc2795312241
dm.1024tera.com	FALSE	/	FALSE	1785491239	g_state	{"i_l":0,"i_ll":1769939239740,"i_b":"QJOqM5CSUpHTv9zkWvDGbOJ/td/iWmp+uQdfRpwZsP4","i_e":{"enable_itp_optimization":3}}"""

with open("cookies.txt", "w") as f:
    f.write(COOKIES_CONTENT)

logger.info("Created cookies.txt file")

# Store active downloads
active_downloads = {}

class TeraboxDownloader:
    def __init__(self):
        self.session = None
        self.cookies = {}
        self.load_cookies()
        
    def load_cookies(self):
        """Load cookies from file"""
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
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
    
    async def get_session(self):
        """Get or create aiohttp session"""
        if not self.session:
            jar = aiohttp.CookieJar()
            for name, value in self.cookies.items():
                jar.update_cookies({name: value})
            
            self.session = aiohttp.ClientSession(
                cookie_jar=jar,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            )
        return self.session
    
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
    
    async def get_share_info(self, shortcode):
        """Get share information from Terabox"""
        try:
            session = await self.get_session()
            url = f"https://www.1024tera.com/s/{shortcode}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Extract app_id (usually 250528 for Terabox)
                    app_id = "250528"
                    
                    # Extract shareid and uk
                    shareid_match = re.search(r'"shareid"\s*:\s*(\d+)', html)
                    shareid = shareid_match.group(1) if shareid_match else None
                    
                    uk_match = re.search(r'"uk"\s*:\s*"([^"]+)"', html)
                    uk = uk_match.group(1) if uk_match else None
                    
                    return {
                        'app_id': app_id,
                        'shareid': shareid,
                        'uk': uk,
                        'shortcode': shortcode
                    }
        except Exception as e:
            logger.error(f"Error getting share info: {e}")
            return None
    
    async def get_file_list(self, share_info):
        """Get file list from share"""
        try:
            session = await self.get_session()
            url = "https://www.1024tera.com/share/list"
            
            params = {
                'app_id': share_info['app_id'],
                'shorturl': share_info['shortcode'],
                'root': '1',
            }
            
            if share_info.get('uk'):
                params['uk'] = share_info['uk']
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('errno') == 0:
                        return data.get('list', [])
        except Exception as e:
            logger.error(f"Error getting file list: {e}")
        return None
    
    async def get_download_url(self, share_info, fs_id):
        """Get download URL for file"""
        try:
            session = await self.get_session()
            url = "https://www.1024tera.com/api/download"
            
            payload = {
                'app_id': share_info['app_id'],
                'fs_id': fs_id,
                'timestamp': int(time.time() * 1000),
                'shareid': share_info.get('shareid', ''),
                'uk': share_info.get('uk', ''),
                'sign': '1',
                'method': 'locatedownload'
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Referer': f"https://www.1024tera.com/s/{share_info['shortcode']}"
            }
            
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('errno') == 0:
                        # Try different possible response formats
                        if data.get('url'):
                            return data['url']
                        elif data.get('dlink'):
                            return data['dlink']
                        elif data.get('info') and len(data['info']) > 0:
                            return data['info'][0].get('dlink')
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
        return None
    
    async def extract_video_info(self, terabox_url):
        """Extract video information from Terabox URL"""
        try:
            # Extract shortcode
            shortcode = await self.extract_shortcode(terabox_url)
            if not shortcode:
                return None
            
            # Get share information
            share_info = await self.get_share_info(shortcode)
            if not share_info:
                return None
            
            # Get file list
            files = await self.get_file_list(share_info)
            if not files:
                return None
            
            # Get first file (assuming single file)
            file_info = files[0]
            fs_id = file_info.get('fs_id')
            
            # Get download URL
            download_url = await self.get_download_url(share_info, fs_id)
            if not download_url:
                return None
            
            return {
                'download_url': download_url,
                'filename': file_info.get('server_filename', f'video_{shortcode}.mp4'),
                'size': file_info.get('size', 0),
                'shortcode': shortcode
            }
            
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None
    
    async def download_file(self, url, filepath, progress_callback=None):
        """Download file with progress tracking"""
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
                            
                            # Call progress callback if provided
                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                await progress_callback(progress, downloaded, total_size)
            
            return True
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()

# Create downloader
downloader = TeraboxDownloader()

# Create client
app = Client(
    "terabox_downloader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

def format_size(size_bytes):
    """Format file size"""
    if not size_bytes:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

async def update_progress_message(message, progress, downloaded, total):
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

# =============== COMMAND HANDLERS ===============

@app.on_message(filters.command("start"))
async def start_command(client, message):
    """Handle /start command"""
    if message.chat.type != "private":
        await message.reply_text("⚠️ Please message me privately to use this bot.")
        return
    
    text = """🤖 **Terabox Video Downloader** 

✅ **Bot is working!**
✅ **Cookies loaded!**
✅ **Ready to download!**

**How to use:**
1. Send me any Terabox link
2. I'll download it using cookies
3. Video will be sent to this DM

**Supported sites:**
• terabox.com
• 1024tera.com  
• terafileshare.com

**Example:**
`https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA`

**Commands:**
/start - Show this message
/status - Check bot status
/cancel - Cancel download

**Note:** Works only in private messages!"""
    
    await message.reply_text(text)

@app.on_message(filters.command("status"))
async def status_command(client, message):
    """Handle /status command"""
    if message.chat.type != "private":
        return
    
    status_text = f"""
✅ **Bot Status**

**Cookies:** {len(downloader.cookies)} loaded
**Active Downloads:** {len(active_downloads)}
**Session:** {'✅ Active' if downloader.session else '❌ Inactive'}

**Bot is ready!** Send me a Terabox link.
"""
    await message.reply_text(status_text)

@app.on_message(filters.command("cancel"))
async def cancel_command(client, message):
    """Handle /cancel command"""
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    if user_id in active_downloads:
        active_downloads[user_id]['cancelled'] = True
        await message.reply_text("✅ Download cancelled!")
    else:
        await message.reply_text("No active download to cancel.")

@app.on_message(filters.text & filters.private & ~filters.command(["start", "status", "cancel"]))
async def handle_link(client, message):
    """Handle Terabox links in DM"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Check if it's a Terabox URL
    if not any(domain in text.lower() for domain in ['terabox', '1024tera', 'terafileshare']):
        await message.reply_text(
            "📩 **Please send me a Terabox link!**\n\n"
            "I can download from:\n"
            "• terabox.com\n"
            "• 1024tera.com\n"
            "• terafileshare.com\n\n"
            "Just paste your link here!"
        )
        return
    
    # Check for active download
    if user_id in active_downloads and not active_downloads[user_id].get('cancelled'):
        await message.reply_text("⏳ You already have a download in progress. Use /cancel first.")
        return
    
    # Check cookies
    if len(downloader.cookies) == 0:
        await message.reply_text("❌ No cookies loaded! Bot cannot download.")
        return
    
    try:
        # Mark as downloading
        active_downloads[user_id] = {
            'cancelled': False,
            'start_time': time.time()
        }
        
        # Send processing message
        status_msg = await message.reply_text(
            f"🔍 **Processing link...**\n\n"
            f"**URL:** `{text[:50]}...`\n"
            f"**Status:** Extracting video information..."
        )
        
        # Extract video info
        video_info = await downloader.extract_video_info(text)
        
        if not video_info:
            await status_msg.edit_text(
                "❌ **Failed to extract video!**\n\n"
                "Possible reasons:\n"
                "• Invalid or expired link\n"
                "• Cookies are expired\n"
                "• Video is private/removed\n"
                "• Server error\n\n"
                "Try a different link or check cookies."
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
                InlineKeyboardButton("⬇️ Download Now", callback_data=f"download_{user_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_btn_{user_id}")
            ]
        ])
        
        # Store download info
        active_downloads[user_id].update({
            'download_url': download_url,
            'filename': filename,
            'size': file_size,
            'status_msg': status_msg
        })
        
        await status_msg.edit_text(confirm_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Link processing error: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")
        if user_id in active_downloads:
            del active_downloads[user_id]

@app.on_callback_query(filters.regex(r"^download_"))
async def download_callback(client, callback_query):
    """Handle download button"""
    user_id = callback_query.from_user.id
    
    try:
        callback_user_id = int(callback_query.data.split('_')[1])
    except:
        callback_user_id = None
    
    if callback_user_id != user_id:
        await callback_query.answer("Not your download!", show_alert=True)
        return
    
    if user_id not in active_downloads:
        await callback_query.answer("Download expired!", show_alert=True)
        return
    
    await callback_query.answer("Starting download...")
    
    download_info = active_downloads[user_id]
    download_url = download_info['download_url']
    filename = download_info['filename']
    message = download_info['status_msg']
    
    if download_info.get('cancelled'):
        await message.edit_text("❌ Download was cancelled.")
        return
    
    try:
        # Start download
        await message.edit_text(
            f"⬇️ **Starting Download...**\n\n"
            f"**File:** `{filename}`\n"
            f"**Size:** `{format_size(download_info['size'])}`\n"
            f"**Status:** Downloading..."
        )
        
        # Define progress callback
        async def progress_callback(progress, downloaded, total):
            if user_id in active_downloads and active_downloads[user_id].get('cancelled'):
                return False
            await update_progress_message(message, progress, downloaded, total)
            return True
        
        # Create filepath
        timestamp = int(time.time())
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filepath = f"downloads/{user_id}_{timestamp}_{safe_filename}"
        
        # Download file
        success = await downloader.download_file(
            download_url,
            filepath,
            progress_callback
        )
        
        if not success or (user_id in active_downloads and active_downloads[user_id].get('cancelled')):
            await message.edit_text("❌ Download failed or cancelled.")
            try:
                os.remove(filepath)
            except:
                pass
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
                f"Video sent to your DM! Check above. 👆"
            )
            
            logger.info(f"Video sent to {user_id}: {filename}")
            
        except FloodWait as e:
            # Handle flood wait
            wait_time = e.value
            await message.edit_text(f"⏳ Please wait {wait_time}s (Telegram limit)...")
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
        await message.edit_text(f"❌ Download failed: {str(e)}")
    
    finally:
        if user_id in active_downloads:
            del active_downloads[user_id]

@app.on_callback_query(filters.regex(r"^cancel_btn_"))
async def cancel_callback(client, callback_query):
    """Handle cancel button"""
    user_id = callback_query.from_user.id
    
    try:
        callback_user_id = int(callback_query.data.split('_')[2])
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

# Handle group messages
@app.on_message(filters.group & filters.command("start"))
async def start_group(client, message):
    """Handle /start in groups"""
    await message.reply_text(
        "⚠️ **I work only in private messages!**\n\n"
        "Please send me a direct message (DM) to use this bot."
    )

# Main function
async def main():
    """Main function"""
    logger.info("Starting Terabox Downloader...")
    logger.info(f"API_ID: {API_ID}")
    logger.info(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")
    logger.info(f"Cookies loaded: {len(downloader.cookies)}")
    
    try:
        await app.start()
        logger.info("✅ Bot started successfully!")
        
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
    # Run the bot
    asyncio.run(main())
