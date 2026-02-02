# bot.py - WORKING DOWNLOAD BOT
import os
import re
import asyncio
import aiohttp
import logging
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get credentials
API_ID = int(os.environ.get("API_ID", "26676741"))
API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E")

# Create client
app = Client("terabox_downloader", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store active downloads
active_downloads = {}

class SimpleTeraboxDownloader:
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
            jar = aiohttp.CookieJar()
            for name, value in self.cookies.items():
                jar.update_cookies({name: value})
            
            self.session = aiohttp.ClientSession(
                cookie_jar=jar,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                }
            )
        return self.session
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def get_download_url(self, url):
        """Get direct download URL using cookies"""
        try:
            session = await self.get_session()
            
            # Extract shortcode from URL
            shortcode = None
            patterns = [
                r'terabox\.com/s/([a-zA-Z0-9_-]+)',
                r'1024tera\.com/s/([a-zA-Z0-9_-]+)',
                r'terafileshare\.com/s/([a-zA-Z0-9_-]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    shortcode = match.group(1)
                    break
            
            if not shortcode:
                logger.error("No shortcode found in URL")
                return None
            
            logger.info(f"Extracted shortcode: {shortcode}")
            
            # First, get the share page
            share_url = f"https://www.1024tera.com/s/{shortcode}"
            async with session.get(share_url) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Look for download URL in the page
                    patterns = [
                        r'"dlink":"([^"]+)"',
                        r'"url":"([^"]+)"',
                        r'downloadUrl["\']?:\s*["\']([^"\']+)["\']',
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, html)
                        if matches:
                            download_url = matches[0].replace('\\/', '/')
                            logger.info(f"Found download URL: {download_url[:100]}...")
                            return download_url
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting download URL: {e}")
            return None
    
    async def download_video(self, url, filepath):
        """Download video from URL"""
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
                
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024*1024)  # 1MB chunks
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress every 10MB
                        if downloaded % (10*1024*1024) == 0:
                            progress = (downloaded / total_size * 100) if total_size > 0 else 0
                            speed = downloaded / (time.time() - start_time) / 1024 / 1024
                            logger.info(f"Download: {progress:.1f}% at {speed:.2f} MB/s")
            
            logger.info(f"Download complete: {downloaded} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False

# Create downloader
downloader = SimpleTeraboxDownloader()

def format_size(size_bytes):
    """Format file size"""
    if not size_bytes:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

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
            "**Need help?**\n"
            "Make sure link is valid and public.\n"
            "Bot uses cookies to access videos."
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
            active_downloads[user_id] = True
            
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
                        "• Server error"
                    )
                    if user_id in active_downloads:
                        del active_downloads[user_id]
                    return
                
                # Generate filename
                filename = f"video_{int(time.time())}.mp4"
                
                # Update status
                await status_msg.edit_text("⬇️ **Downloading video...**\n\nPlease wait...")
                
                # Create filepath
                filepath = f"downloads/{user_id}_{filename}"
                os.makedirs("downloads", exist_ok=True)
                
                # Download the video
                success = await downloader.download_video(download_url, filepath)
                
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
                        caption=f"✅ **Download Complete!**\n\n**Size:** `{format_size(file_size)}`",
                        supports_streaming=True
                    )
                    
                    # Update status
                    await status_msg.edit_text("✅ **Video sent to your DM!**")
                    
                except Exception as e:
                    logger.error(f"Upload error: {e}")
                    # Try as document
                    try:
                        await client.send_document(
                            chat_id=user_id,
                            document=filepath,
                            caption=f"✅ **Download Complete!**\n\n**Size:** `{format_size(file_size)}`"
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

# Main function
async def main():
    """Main function"""
    logger.info("=" * 50)
    logger.info("Starting Terabox Downloader Bot...")
    logger.info(f"Cookies loaded: {len(downloader.cookies)}")
    logger.info("=" * 50)
    
    try:
        await app.start()
        logger.info("✅ Bot started successfully!")
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"🤖 Bot: @{me.username}")
        
        # Keep running
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        try:
            await app.stop()
            await downloader.close()
            logger.info("Bot stopped")
        except:
            pass

if __name__ == "__main__":
    # Ensure downloads directory exists
    os.makedirs("downloads", exist_ok=True)
    
    # Run the bot
    asyncio.run(main())

