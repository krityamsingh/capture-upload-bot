# bot.py - COMPLETE DOWNLOAD BOT
import os
import re
import asyncio
import aiohttp
import logging
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get credentials
API_ID = int(os.environ.get("API_ID", "26676741"))
API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E")

# Log startup
logger.info("=" * 50)
logger.info("TERABOX DOWNLOAD BOT STARTING")
logger.info(f"API_ID: {API_ID}")
logger.info(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")
logger.info("=" * 50)

# Create client
app = Client(
    "terabox_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=2
)

# Create cookies.txt file with your cookies
COOKIES_CONTENT = """# Netscape HTTP Cookie File
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

# Write cookies file
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
            else:
                logger.error("cookies.txt not found!")
                return False
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False
    
    async def get_session(self):
        """Create aiohttp session with cookies"""
        if not self.session:
            # Create cookie jar
            jar = aiohttp.CookieJar()
            
            # Add cookies to jar
            for name, value in self.cookies.items():
                jar.update_cookies({name: value})
            
            self.session = aiohttp.ClientSession(
                cookie_jar=jar,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
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
            r'terabox\.com/s/([a-zA-Z0-9_-]+)',
            r'1024tera\.com/s/([a-zA-Z0-9_-]+)',
            r'terafileshare\.com/s/([a-zA-Z0-9_-]+)',
            r'/s/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def get_download_url(self, url):
        """Get direct download URL using cookies"""
        try:
            session = await self.get_session()
            shortcode = await self.extract_shortcode(url)
            
            if not shortcode:
                logger.error("No shortcode found in URL")
                return None
            
            logger.info(f"Processing shortcode: {shortcode}")
            
            # First, try to get the page
            share_url = f"https://www.1024tera.com/s/{shortcode}"
            async with session.get(share_url) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Try to find download URL patterns
                    patterns = [
                        r'"dlink":"([^"]+)"',
                        r'"url":"([^"]+)"',
                        r'downloadUrl["\']?:\s*["\']([^"\']+)["\']',
                        r'href="(https?://[^"]+\.(?:mp4|mkv|avi|mov|flv))"',
                        r'src="(https?://[^"]+\.(?:mp4|mkv|avi|mov|flv))"',
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, html, re.IGNORECASE)
                        if matches:
                            download_url = matches[0].replace('\\/', '/')
                            logger.info(f"Found download URL: {download_url[:100]}...")
                            return download_url
            
            # If not found, try API
            logger.info("Trying API method...")
            api_url = f"https://www.1024tera.com/api/shorturlinfo?shorturl={shortcode}&root=1"
            async with session.get(api_url) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        if data.get('list') and len(data['list']) > 0:
                            # Try to get download URL from API response
                            file_info = data['list'][0]
                            if file_info.get('dlink'):
                                return file_info['dlink'].replace('\\/', '/')
                    except:
                        pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
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
            last_update = start_time
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Download failed with status: {response.status}")
                    return False
                
                with open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024*1024):  # 1MB chunks
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress every 2 seconds
                            current_time = time.time()
                            if current_time - last_update >= 2:
                                if progress_callback and total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    await progress_callback(progress, downloaded, total_size)
                                last_update = current_time
            
            # Final progress update
            if progress_callback and total_size > 0:
                await progress_callback(100, downloaded, total_size)
            
            logger.info(f"Download complete: {downloaded} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False

# Create downloader
downloader = TeraboxDownloader()

def format_size(size_bytes):
    """Format file size"""
    if not size_bytes or size_bytes == 0:
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
        if 'start_time' in active_downloads.get(message.chat.id, {}):
            elapsed = time.time() - active_downloads[message.chat.id]['start_time']
            if elapsed > 0:
                speed = downloaded / elapsed
                eta = (total - downloaded) / speed if speed > 0 else 0
                speed_text = f"{format_size(speed)}/s"
                eta_text = f"{int(eta//60)}m {int(eta%60)}s"
            else:
                speed_text = "0 B/s"
                eta_text = "--"
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
    try:
        if message.chat.type != "private":
            await message.reply_text("⚠️ Please message me privately!")
            return
        
        cookies_status = "✅ Cookies loaded" if len(downloader.cookies) > 0 else "❌ No cookies"
        
        await message.reply_text(
            f"🤖 **Terabox Downloader Bot**\n\n"
            f"{cookies_status}\n"
            f"✅ Bot is ready!\n\n"
            "**How to use:**\n"
            "1. Send me any Terabox link\n"
            "2. I'll download it using cookies\n"
            "3. Video will be sent to your DM\n\n"
            "**Example:**\n"
            "`https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA`\n\n"
            "**Commands:**\n"
            "/start - Show this message\n"
            "/status - Check bot status\n"
            "/help - Get help"
        )
        logger.info(f"User {message.from_user.id} started bot")
    except Exception as e:
        logger.error(f"Start error: {e}")

@app.on_message(filters.command("status"))
async def status_command(client, message):
    """Check bot status"""
    try:
        cookies_status = f"{len(downloader.cookies)} cookies loaded" if len(downloader.cookies) > 0 else "No cookies"
        await message.reply_text(
            f"✅ **Bot Status**\n\n"
            f"**Cookies:** {cookies_status}\n"
            f"**Active Downloads:** {len(active_downloads)}\n"
            f"**Bot:** Online and working\n\n"
            "Send me a Terabox link to download!"
        )
        logger.info(f"Status checked by {message.from_user.id}")
    except Exception as e:
        logger.error(f"Status error: {e}")

@app.on_message(filters.command("help"))
async def help_command(client, message):
    """Help command"""
    try:
        await message.reply_text(
            "❓ **Help**\n\n"
            "**How to download:**\n"
            "1. Find a Terabox video\n"
            "2. Copy the share link\n"
            "3. Send link to this bot\n"
            "4. Wait for download\n\n"
            "**Supported sites:**\n"
            "• terabox.com\n"
            "• 1024tera.com\n"
            "• terafileshare.com\n\n"
            "**Note:** Bot uses cookies to access videos.\n"
            "Make sure cookies.txt is valid."
        )
    except Exception as e:
        logger.error(f"Help error: {e}")

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
            user_id = message.from_user.id
            
            if user_id in active_downloads:
                await message.reply_text("⏳ You already have a download in progress!")
                return
            
            # Check cookies
            if len(downloader.cookies) == 0:
                await message.reply_text("❌ No cookies loaded! Cannot download.")
                return
            
            # Send processing message
            status_msg = await message.reply_text(
                f"🔍 **Processing link...**\n\n"
                f"**URL:** `{text[:50]}...`\n"
                f"**Status:** Getting download URL..."
            )
            
            # Store as active
            active_downloads[user_id] = {
                'processing': True,
                'start_time': time.time(),
                'status_msg': status_msg
            }
            
            try:
                # Get download URL
                download_url = await downloader.get_download_url(text)
                
                if not download_url:
                    await status_msg.edit_text(
                        "❌ **Failed to get download URL!**\n\n"
                        "Possible reasons:\n"
                        "• Invalid link\n"
                        "• Cookies expired\n"
                        "• Video removed\n"
                        "• Server error\n\n"
                        "Try a different link."
                    )
                    if user_id in active_downloads:
                        del active_downloads[user_id]
                    return
                
                # Generate filename
                filename = f"video_{int(time.time())}.mp4"
                if '.mp4' in download_url.lower():
                    # Try to extract filename from URL
                    url_parts = download_url.split('/')
                    if len(url_parts) > 0:
                        last_part = url_parts[-1]
                        if '.' in last_part:
                            filename = last_part.split('?')[0]
                
                # Update status
                await status_msg.edit_text(
                    f"✅ **Download URL found!**\n\n"
                    f"**File:** `{filename}`\n"
                    f"**Status:** Starting download..."
                )
                
                # Create filepath
                filepath = f"downloads/{user_id}_{filename}"
                os.makedirs("downloads", exist_ok=True)
                
                # Define progress callback
                async def progress_callback(progress, downloaded, total):
                    if user_id in active_downloads:
                        await update_progress(status_msg, progress, downloaded, total)
                
                # Update active downloads
                active_downloads[user_id].update({
                    'download_url': download_url,
                    'filename': filename,
                    'filepath': filepath
                })
                
                # Download the video
                logger.info(f"Starting download for {user_id}")
                success = await downloader.download_file(download_url, filepath, progress_callback)
                
                if not success:
                    await status_msg.edit_text("❌ Download failed!")
                    try:
                        os.remove(filepath)
                    except:
                        pass
                    return
                
                # Get file size
                file_size = os.path.getsize(filepath)
                
                # Upload to Telegram
                await status_msg.edit_text("📤 **Sending to your DM...**")
                
                try:
                    # Send as video
                    await client.send_video(
                        chat_id=user_id,
                        video=filepath,
                        caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`",
                        supports_streaming=True
                    )
                    
                    # Update status
                    await status_msg.edit_text(
                        f"✅ **Successfully Sent!**\n\n"
                        f"**File:** `{filename}`\n"
                        f"**Size:** `{format_size(file_size)}`\n\n"
                        f"Video sent to your DM! 🎬"
                    )
                    
                    logger.info(f"Video sent to {user_id}: {filename}")
                    
                except Exception as e:
                    logger.error(f"Upload error: {e}")
                    # Try as document
                    try:
                        await client.send_document(
                            chat_id=user_id,
                            document=filepath,
                            caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(file_size)}`"
                        )
                        await status_msg.edit_text("✅ File sent to your DM!")
                    except Exception as e2:
                        await status_msg.edit_text(f"❌ Failed to send: {str(e2)}")
                
                # Cleanup
                try:
                    os.remove(filepath)
                except:
                    pass
                
            except Exception as e:
                logger.error(f"Download process error: {e}")
                await status_msg.edit_text(f"❌ Error: {str(e)}")
            
            finally:
                if user_id in active_downloads:
                    del active_downloads[user_id]
            
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

# Handle group messages
@app.on_message(filters.group & filters.command("start"))
async def group_start_handler(client, message):
    bot_info = await client.get_me()
    await message.reply_text(
        f"⚠️ **I work only in private messages!**\n\n"
        f"Please message me directly: @{bot_info.username}"
    )

# Main function
async def main():
    """Main function"""
    logger.info("=" * 50)
    logger.info("Bot starting with download functionality")
    logger.info(f"Cookies loaded: {len(downloader.cookies)}")
    logger.info("=" * 50)
    
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
    # Ensure downloads directory exists
    os.makedirs("downloads", exist_ok=True)
    
    # Run the bot
    asyncio.run(main())
