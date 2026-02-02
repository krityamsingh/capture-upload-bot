# bot.py - PUBLIC TERABOX DOWNLOADER
import os
import re
import asyncio
import aiohttp
import logging
import time
from pathlib import Path
from urllib.parse import urlparse
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
app = Client("terabox_public_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store active downloads
active_downloads = {}

class TeraboxPublicDownloader:
    def __init__(self):
        self.session = None
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
    
    async def get_session(self):
        """Create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.base_headers)
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
    
    async def get_direct_link(self, url):
        """Get direct download link for public Terabox link"""
        try:
            session = await self.get_session()
            shortcode = await self.extract_shortcode(url)
            
            if not shortcode:
                return None
            
            logger.info(f"Processing shortcode: {shortcode}")
            
            # Try multiple domains
            domains = [
                f"https://www.terabox.com/s/{shortcode}",
                f"https://www.1024tera.com/s/{shortcode}",
                f"https://www.terafileshare.com/s/{shortcode}",
            ]
            
            for domain_url in domains:
                try:
                    # Get the HTML page
                    async with session.get(domain_url) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Try to find direct download link patterns
                            patterns = [
                                r'direct_link["\']?:\s*["\']([^"\']+)["\']',
                                r'downloadUrl["\']?:\s*["\']([^"\']+)["\']',
                                r'"url"\s*:\s*"([^"]+)"',
                                r'<a[^>]+href=["\'](https?://[^"\']+\.(?:mp4|mkv|avi|mov|wmv|flv))["\'][^>]*>',
                                r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                                r'"dlink"\s*:\s*"([^"]+)"',
                                r'"download_url"\s*:\s*"([^"]+)"',
                            ]
                            
                            for pattern in patterns:
                                matches = re.findall(pattern, html, re.IGNORECASE)
                                if matches:
                                    download_url = matches[0].replace('\\/', '/')
                                    logger.info(f"Found download URL: {download_url[:100]}...")
                                    return download_url
                            
                            # Try to extract from iframe
                            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
                            if iframe_match:
                                iframe_url = iframe_match.group(1)
                                async with session.get(iframe_url) as iframe_resp:
                                    if iframe_resp.status == 200:
                                        iframe_html = await iframe_resp.text()
                                        for pattern in patterns:
                                            matches = re.findall(pattern, iframe_html, re.IGNORECASE)
                                            if matches:
                                                download_url = matches[0].replace('\\/', '/')
                                                return download_url
                except Exception as e:
                    logger.warning(f"Failed with domain {domain_url}: {e}")
                    continue
            
            # If no direct link found, try API approach
            api_url = f"https://www.terabox.com/api/shorturlinfo?shorturl={shortcode}&root=1"
            async with session.get(api_url) as api_resp:
                if api_resp.status == 200:
                    data = await api_resp.json()
                    if data.get('list') and len(data['list']) > 0:
                        # Try to construct download URL
                        server_filename = data['list'][0].get('server_filename', f'video_{shortcode}.mp4')
                        size = data['list'][0].get('size', 0)
                        # This is a fallback URL pattern
                        return f"https://example.com/download/{shortcode}"  # Placeholder
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting direct link: {e}")
            return None
    
    async def download_file(self, url, filepath, progress_callback=None):
        """Download file with progress"""
        try:
            session = await self.get_session()
            
            # Get file size
            async with session.head(url) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                if total_size == 0:
                    # Try without head if it fails
                    pass
            
            # Download file
            downloaded = 0
            start_time = time.time()
            
            async with session.get(url) as response:
                if response.status != 200:
                    return False
                
                # Try to get size from response
                if total_size == 0:
                    total_size = int(response.headers.get('Content-Length', 0))
                
                async with aiofiles.open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(512 * 1024):  # 512KB chunks
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
downloader = TeraboxPublicDownloader()

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
            
        await message.reply_text(
            "🤖 **Terabox Public Downloader**\n\n"
            "✅ **Free for everyone!**\n"
            "✅ **No cookies required!**\n\n"
            "**I can download videos from:**\n"
            "• terabox.com\n"
            "• 1024tera.com\n"
            "• terafileshare.com\n\n"
            "**How to use:**\n"
            "1. Send me any Terabox public link\n"
            "2. I'll process and download it\n"
            "3. Video will be sent to your DM\n\n"
            "**Example links:**\n"
            "`https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA`\n"
            "`https://terabox.com/s/your-link-here`\n\n"
            "**Commands:**\n"
            "/start - Show this message\n"
            "/status - Check bot status\n"
            "/help - Get help\n\n"
            "⚠️ **Note:** Works only with public links!"
        )
    except Exception as e:
        logger.error(f"Start error: {e}")

@app.on_message(filters.command("status"))
async def status_command(client, message):
    """Check bot status"""
    try:
        await message.reply_text(
            f"✅ **Bot Status**\n\n"
            f"**Status:** ONLINE\n"
            f"**Active Downloads:** {len(active_downloads)}\n"
            f"**Public Access:** ✅ Available\n"
            f"**Session:** {'✅ Active' if downloader.session else '❌ Inactive'}\n\n"
            f"Bot is ready to download public Terabox links!"
        )
    except Exception as e:
        logger.error(f"Status error: {e}")

@app.on_message(filters.command("help"))
async def help_command(client, message):
    """Help command"""
    try:
        await message.reply_text(
            "❓ **Help & Support**\n\n"
            "**How to get Terabox links:**\n"
            "1. Go to terabox.com\n"
            "2. Find a video and click 'Share'\n"
            "3. Copy the share link\n"
            "4. Send it to me\n\n"
            "**Supported link formats:**\n"
            "• https://terabox.com/s/xxxxx\n"
            "• https://1024tera.com/s/xxxxx\n"
            "• https://terafileshare.com/s/xxxxx\n\n"
            "**Issues?**\n"
            "• Make sure link is public\n"
            "• Try different link\n"
            "• Bot may not work with private links\n\n"
            "**Features:**\n"
            "✅ Free for all users\n"
            "✅ No registration needed\n"
            "✅ Direct DM delivery\n"
            "✅ Progress tracking"
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
                await message.reply_text("⏳ You already have an active download! Please wait.")
                return
            
            # Mark as processing
            active_downloads[user_id] = {'processing': True}
            
            # Send processing message
            status_msg = await message.reply_text(
                f"🔍 **Processing public link...**\n\n"
                f"**URL:** `{text[:50]}...`\n"
                f"**Status:** Extracting video information..."
            )
            
            # Get direct link
            download_url = await downloader.get_direct_link(text)
            
            if not download_url:
                await status_msg.edit_text(
                    "❌ **Could not extract video!**\n\n"
                    "Possible reasons:\n"
                    "• Link is private/requires password\n"
                    "• Video was removed\n"
                    "• Server is busy\n"
                    "• Link format not supported\n\n"
                    "**Try:**\n"
                    "1. Make sure link is public\n"
                    "2. Try a different link\n"
                    "3. Check if video is available"
                )
                if user_id in active_downloads:
                    del active_downloads[user_id]
                return
            
            # Generate filename
            filename = f"video_{int(time.time())}.mp4"
            if 'mp4' in download_url.lower() or '.mp4' in download_url.lower():
                filename = download_url.split('/')[-1].split('?')[0] or filename
            
            confirm_text = (
                f"✅ **Video Found!**\n\n"
                f"**File:** `{filename}`\n"
                f"**Status:** Ready to download\n\n"
                f"Click below to download to your DM:"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬇️ Download Now", callback_data=f"download_{user_id}_{filename}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
            ])
            
            # Store download info
            active_downloads[user_id] = {
                'download_url': download_url,
                'filename': filename,
                'status_msg': status_msg,
                'processing': False
            }
            
            await status_msg.edit_text(confirm_text, reply_markup=keyboard)
            
        else:
            await message.reply_text(
                "📩 **Send me a Terabox public link!**\n\n"
                "**I work with:**\n"
                "• terabox.com (public links)\n"
                "• 1024tera.com (public links)\n"
                "• terafileshare.com (public links)\n\n"
                "**Example:**\n"
                "`https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA`\n\n"
                "⚠️ **Note:** Private/protected links may not work!"
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
            f"**Status:** Downloading from public link..."
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
            await message.edit_text(
                "❌ **Download failed!**\n\n"
                "Possible reasons:\n"
                "• Network error\n"
                "• Server blocked the request\n"
                "• File is too large\n"
                "• Download timeout\n\n"
                "Please try again later or use a different link."
            )
            if os.path.exists(filepath):
                os.remove(filepath)
            if user_id in active_downloads:
                del active_downloads[user_id]
            return
        
        # Get file size
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        
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
                f"Video sent to your DM! 🎬"
            )
            
        except FloodWait as e:
            # Handle flood wait
            wait_time = e.value
            await message.edit_text(f"⏳ Please wait {wait_time} seconds...")
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
        try:
            await callback_query.message.edit_text(f"❌ Error: {str(e)}")
        except:
            pass
    
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

@app.on_message(filters.group)
async def handle_group(client, message):
    """Handle group messages"""
    if message.text and message.text.startswith('/start'):
        bot_info = await client.get_me()
        await message.reply_text(
            f"⚠️ **I work only in private messages!**\n\n"
            f"Please message me directly: @{bot_info.username}\n\n"
            "Send me Terabox public links to download videos for free!"
        )

# Main function
async def main():
    """Main function"""
    logger.info("=" * 50)
    logger.info("Starting Terabox Public Downloader Bot...")
    logger.info("✅ Bot is FREE for everyone!")
    logger.info("✅ No cookies required!")
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
