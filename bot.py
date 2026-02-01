# bot.py - FIXED VERSION FOR HEROKU DM BOT
import os
import re
import asyncio
import aiohttp
import logging
import time
import json
from typing import Dict, Optional
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError
import aiofiles
from datetime import datetime

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

# Ensure downloads directory exists
os.makedirs("downloads", exist_ok=True)

# Store active downloads
active_downloads = {}

class TeraboxDownloader:
    def __init__(self):
        self.session = None
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    async def create_session(self):
        """Create aiohttp session"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.base_headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def extract_shortcode(self, url: str) -> Optional[str]:
        """Extract shortcode from Terabox URL"""
        patterns = [
            r'(?:terabox\.com|1024tera\.com|terafileshare\.com)/s/([a-zA-Z0-9_-]+)',
            r'share/([a-zA-Z0-9_-]+)',
            r'/([a-zA-Z0-9_-]{9,})(?:\?|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def get_video_info(self, url: str) -> Optional[Dict]:
        """
        Get video information from Terabox URL
        This is a placeholder - replace with actual Terabox API implementation
        """
        try:
            shortcode = await self.extract_shortcode(url)
            if not shortcode:
                return None
            
            # Simulate getting video info (REPLACE WITH REAL API CALL)
            # In production, make actual API call to Terabox
            return {
                'success': True,
                'title': f"Video_{shortcode}.mp4",
                'size': 52428800,  # 50MB placeholder
                'download_url': f"https://example.com/video_{shortcode}.mp4",  # Placeholder
                'shortcode': shortcode
            }
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    async def download_video(self, url: str, filename: str, message: Message) -> Optional[str]:
        """Download video with progress"""
        try:
            session = await self.create_session()
            
            # Create unique file path
            timestamp = int(time.time())
            filepath = f"downloads/{timestamp}_{filename}"
            
            # Get file size first
            async with session.head(url, allow_redirects=True) as response:
                total_size = int(response.headers.get('Content-Length', 50 * 1024 * 1024))  # 50MB fallback
            
            # Download file
            downloaded = 0
            start_time = time.time()
            
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                # Write to file
                async with aiofiles.open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024*1024):  # 1MB chunks
                        if chunk:
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress every 5% or 5MB
                            if downloaded % (5 * 1024 * 1024) == 0 or downloaded == total_size:
                                progress = (downloaded / total_size) * 100
                                try:
                                    await self.update_progress(message, progress, downloaded, total_size)
                                except:
                                    pass
            
            return filepath
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
    async def update_progress(self, message: Message, progress: float, downloaded: int, total: int):
        """Update download progress"""
        try:
            # Format progress bar
            bar_length = 20
            filled_length = int(bar_length * progress / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Format sizes
            def format_size(size):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        return f"{size:.2f} {unit}"
                    size /= 1024.0
                return f"{size:.2f} TB"
            
            # Create progress text
            text = (
                f"📥 **Downloading...**\n\n"
                f"`{bar}` **{progress:.1f}%**\n\n"
                f"**Progress:** `{format_size(downloaded)} / {format_size(total)}`\n"
                f"**Status:** Downloading to your DM..."
            )
            
            await message.edit_text(text)
            
        except Exception as e:
            logger.error(f"Progress update error: {e}")

# Create downloader
downloader = TeraboxDownloader()

# Create Pyrogram client with proper configuration
app = Client(
    name="terabox_dm_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=3,
    sleep_threshold=60,
    no_updates=True
)

# Helper function to format file size
def format_size(size_bytes):
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
    user_id = message.from_user.id if message.from_user else message.chat.id
    
    # Check if it's a private chat
    if message.chat.type != "private":
        await message.reply_text(
            "⚠️ **This bot works only in private messages!**\n\n"
            "Please send me a direct message (DM) to use this bot.\n\n"
            "Click here to start a private chat: [Message Me Privately](https://t.me/terabox_downloader_bot)"
        )
        return
    
    welcome_text = f"""
🎬 **Terabox Video Downloader Bot** 🎬

**Hello!** 👋 I'm your personal Terabox downloader.

**I can download videos from:**
✅ terabox.com
✅ 1024tera.com  
✅ terafileshare.com

**How to use me:**
1. Send me any Terabox link in this private chat
2. I'll process and download it
3. I'll send the video directly to this DM

**Example links to try:**
`https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA`
`https://terabox.com/s/your-link-here`
`https://1024tera.com/s/your-link-here`

**Commands:**
/start - Show this message
/status - Check bot status
/cancel - Cancel current download

**Note:** I only work in private messages!
"""
    
    await message.reply_text(welcome_text, disable_web_page_preview=True)
    logger.info(f"User {user_id} started bot in DM")

@app.on_message(filters.command("status"))
async def status_handler(client: Client, message: Message):
    """Handle /status command"""
    if message.chat.type != "private":
        return
    
    bot_info = await client.get_me()
    status_text = f"""
🤖 **Bot Status Report**

**Bot:** @{bot_info.username}
**User:** {message.from_user.first_name}
**User ID:** `{message.from_user.id}`
**Active Downloads:** {len(active_downloads)}
**Server Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Platform:** Heroku

**Status:** ✅ **ONLINE & READY**

Send me a Terabox link to download videos!
"""
    await message.reply_text(status_text)

@app.on_message(filters.command("cancel"))
async def cancel_handler(client: Client, message: Message):
    """Handle /cancel command"""
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    if user_id in active_downloads:
        del active_downloads[user_id]
        await message.reply_text("✅ Download cancelled successfully!")
    else:
        await message.reply_text("ℹ️ No active download to cancel.")

@app.on_message(filters.text & filters.private)
async def handle_private_messages(client: Client, message: Message):
    """Handle all text messages in private chat"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Skip if it's a command (already handled)
    if text.startswith('/'):
        return
    
    # Check if it's a Terabox URL
    if not any(domain in text.lower() for domain in ['terabox', '1024tera', 'terafileshare']):
        # Not a Terabox link
        await message.reply_text(
            "📩 **Please send me a Terabox link!**\n\n"
            "I can download videos from:\n"
            "• terabox.com\n"
            "• 1024tera.com\n"
            "• terafileshare.com\n\n"
            "Just paste your link here and I'll download it directly to this DM!"
        )
        return
    
    # Check if user already has active download
    if user_id in active_downloads:
        await message.reply_text("⏳ You already have a download in progress. Please wait or use /cancel")
        return
    
    try:
        # Mark user as downloading
        active_downloads[user_id] = True
        
        # Send processing message
        processing_msg = await message.reply_text(
            f"🔍 **Processing your link...**\n\n"
            f"**URL:** `{text[:60]}...`\n"
            f"**Status:** Analyzing link..."
        )
        
        # Extract video information
        video_info = await downloader.get_video_info(text)
        
        if not video_info or not video_info.get('success'):
            await processing_msg.edit_text(
                "❌ **Unable to process this link**\n\n"
                "Possible reasons:\n"
                "• Invalid or broken link\n"
                "• Video is private/removed\n"
                "• Server is temporarily unavailable\n\n"
                "Please check the link and try again."
            )
            if user_id in active_downloads:
                del active_downloads[user_id]
            return
        
        # Get video details
        video_title = video_info.get('title', 'video.mp4')
        video_size = video_info.get('size', 0)
        download_url = video_info.get('download_url')
        
        # Show video info and ask for confirmation
        confirm_text = (
            f"✅ **Video Found!**\n\n"
            f"**Title:** `{video_title}`\n"
            f"**Size:** `{format_size(video_size)}`\n"
            f"**Status:** Ready to download\n\n"
            f"Do you want to download this video to your DM?"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬇️ Download Now", callback_data=f"download_{user_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")
            ]
        ])
        
        await processing_msg.edit_text(confirm_text, reply_markup=keyboard)
        
        # Store download info
        active_downloads[user_id] = {
            'url': download_url,
            'title': video_title,
            'size': video_size,
            'message_id': processing_msg.id,
            'processing_msg': processing_msg
        }
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")
        if user_id in active_downloads:
            del active_downloads[user_id]

@app.on_callback_query(filters.regex(r"^download_"))
async def download_callback(client, callback_query):
    """Handle download button click"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Extract user ID from callback data
    try:
        callback_user_id = int(data.split('_')[1])
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
    download_url = download_info['url']
    video_title = download_info['title']
    message = download_info['processing_msg']
    
    try:
        # Update message to show download started
        await message.edit_text(
            f"⬇️ **Starting Download...**\n\n"
            f"**File:** `{video_title}`\n"
            f"**Size:** `{format_size(download_info['size'])}`\n"
            f"**Status:** Downloading to your DM..."
        )
        
        # Download the video
        filepath = await downloader.download_video(download_url, video_title, message)
        
        if not filepath:
            await message.edit_text("❌ Download failed. Please try again.")
            if user_id in active_downloads:
                del active_downloads[user_id]
            return
        
        # Get actual file size
        file_size = os.path.getsize(filepath)
        
        # Send uploading message
        await message.edit_text("📤 **Uploading to your DM...**\n\nPlease wait, this may take a while...")
        
        try:
            # Send video to user's DM
            await client.send_video(
                chat_id=user_id,
                video=filepath,
                caption=f"✅ **Download Complete!**\n\n**File:** `{video_title}`\n**Size:** `{format_size(file_size)}`",
                supports_streaming=True
            )
            
            # Update success message
            success_text = (
                f"✅ **Successfully Sent!**\n\n"
                f"**File:** `{video_title}`\n"
                f"**Size:** `{format_size(file_size)}`\n"
                f"**Status:** ✅ Delivered to your DM\n\n"
                f"Check your messages above! 👆"
            )
            
            await message.edit_text(success_text)
            
            logger.info(f"Video sent to user {user_id}: {video_title}")
            
        except FloodWait as e:
            # Handle flood wait
            wait_time = e.value
            await message.edit_text(f"⏳ Please wait {wait_time} seconds (Telegram limit). I'll try again automatically...")
            await asyncio.sleep(wait_time)
            
            # Retry sending
            await client.send_video(
                chat_id=user_id,
                video=filepath,
                caption=f"✅ **Download Complete!**\n\n**File:** `{video_title}`\n**Size:** `{format_size(file_size)}`",
                supports_streaming=True
            )
            await message.edit_text(success_text)
            
        except Exception as e:
            logger.error(f"Error sending video: {e}")
            await message.edit_text(f"❌ Error sending video: {str(e)}")
        
        # Clean up
        try:
            os.remove(filepath)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        await message.edit_text(f"❌ Download failed: {str(e)}")
    
    finally:
        # Remove from active downloads
        if user_id in active_downloads:
            del active_downloads[user_id]

@app.on_callback_query(filters.regex(r"^cancel_"))
async def cancel_callback(client, callback_query):
    """Handle cancel button"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    try:
        callback_user_id = int(data.split('_')[1])
    except:
        callback_user_id = None
    
    if callback_user_id != user_id:
        await callback_query.answer("This is not your download!", show_alert=True)
        return
    
    if user_id in active_downloads:
        del active_downloads[user_id]
    
    await callback_query.message.edit_text("❌ Download cancelled.")
    await callback_query.answer("Download cancelled")

# =============== MAIN FUNCTION ===============

async def run_bot():
    """Main function to run the bot"""
    logger.info("Starting Terabox DM Bot...")
    
    try:
        await app.start()
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"Bot started successfully!")
        logger.info(f"Bot username: @{me.username}")
        logger.info(f"Bot ID: {me.id}")
        
        # Send startup notification
        startup_msg = f"""
🚀 Terabox DM Bot Started!
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Bot: @{me.username}
✅ Status: Running on Heroku
📝 Log: Bot is ready to receive DMs
        """
        logger.info(startup_msg)
        
        # Keep bot running
        await idle()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
    finally:
        # Cleanup
        await app.stop()
        await downloader.close()
        logger.info("Bot stopped.")

# Run the bot
if __name__ == "__main__":
    # Create event loop for asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        loop.close()
