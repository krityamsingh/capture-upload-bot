# bot.py - Main bot file for Heroku
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

class TeraboxDownloader:
    def __init__(self):
        self.session = None
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
    
    async def create_session(self):
        """Create aiohttp session"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.base_headers)
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_direct_link(self, url: str) -> Optional[Dict]:
        """
        Extract direct download link from Terabox URLs
        This is a simplified version - in production you'd need proper API implementation
        """
        try:
            await self.create_session()
            
            # Extract shortcode from URL
            patterns = [
                r'(?:terabox\.com|1024tera\.com|terafileshare\.com)/s/([a-zA-Z0-9_-]+)',
                r'/([a-zA-Z0-9_-]{9,})(?:\?|$)',
            ]
            
            shortcode = None
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    shortcode = match.group(1)
                    break
            
            if not shortcode:
                logger.error(f"No shortcode found in URL: {url}")
                return None
            
            logger.info(f"Extracted shortcode: {shortcode}")
            
            # For demo purposes, we'll simulate getting a direct link
            # In production, you would make actual API calls to Terabox
            
            # Simulate API response
            # NOTE: Replace this with actual Terabox API implementation
            return {
                'direct_url': f"https://example.com/video_{shortcode}.mp4",  # Placeholder
                'filename': f"video_{shortcode}.mp4",
                'size': 1024 * 1024 * 50,  # 50MB placeholder
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error getting direct link: {e}")
            return None
    
    async def download_file(self, url: str, filepath: str, progress_callback=None) -> bool:
        """Download file with progress tracking"""
        try:
            await self.create_session()
            
            # For demo, simulate download
            # Replace with actual download logic
            
            file_size = 1024 * 1024 * 50  # 50MB placeholder
            chunk_size = 1024 * 1024  # 1MB
            
            # Simulate download progress
            downloaded = 0
            async with aiofiles.open(filepath, 'wb') as f:
                while downloaded < file_size:
                    chunk = min(chunk_size, file_size - downloaded)
                    # Write dummy data (replace with actual download)
                    await f.write(b'\x00' * chunk)
                    downloaded += chunk
                    
                    # Update progress
                    if progress_callback:
                        progress = (downloaded / file_size) * 100
                        await progress_callback(progress, downloaded, file_size)
                    
                    # Simulate network delay
                    await asyncio.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False

# Create downloader instance
downloader = TeraboxDownloader()

# Create Pyrogram client
app = Client(
    "terabox_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=2
)

# Store user download states
user_downloads = {}

# Helper functions
def format_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {units[i]}"

def format_time(seconds: int) -> str:
    """Format time in MM:SS format"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

# Command handlers
@app.on_message(filters.command(["start", "help"]))
async def start_command(client: Client, message: Message):
    """Handle /start command in DM"""
    user_id = message.from_user.id
    chat_type = message.chat.type
    
    # Only respond in private chats (DM)
    if chat_type != "private":
        await message.reply_text(
            "⚠️ **Please message me in private!**\n\n"
            "Send me a direct message (DM) to use this bot.\n"
            "Click here to start a private chat: [@terabox_downloader_bot](https://t.me/terabox_downloader_bot)"
        )
        return
    
    welcome_text = f"""
🎬 **Terabox Video Downloader Bot** 🎬

**Hello {message.from_user.first_name}!** 👋

I can download videos from:
• terabox.com
• 1024tera.com  
• terafileshare.com

**How to use me:**
1. Send me any Terabox link
2. I'll process and download it
3. I'll send the video directly to this DM

**Example links:**
`https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA`
`https://terabox.com/s/AbC123def`
`https://1024tera.com/s/XyZ789`

**Features:**
✅ Direct DM delivery
✅ Fast downloads
✅ Progress tracking
✅ Multiple formats supported

**Commands:**
/start - Show this message
/status - Check bot status
/cancel - Cancel current download

**Note:** I only work in private messages!
"""
    
    await message.reply_text(welcome_text, disable_web_page_preview=True)
    logger.info(f"User {user_id} started the bot")

@app.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    """Check bot status"""
    if message.chat.type != "private":
        return
    
    status_text = f"""
🤖 **Bot Status**

**User:** {message.from_user.first_name}
**ID:** `{message.from_user.id}`
**Active Downloads:** {len(user_downloads)}
**Server:** Heroku
**Status:** ✅ Online

Send me a Terabox link to get started!
"""
    await message.reply_text(status_text)

@app.on_message(filters.command("cancel"))
async def cancel_command(client: Client, message: Message):
    """Cancel current download"""
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    if user_id in user_downloads:
        user_downloads[user_id] = {'cancelled': True}
        await message.reply_text("⏹️ Download cancelled successfully!")
    else:
        await message.reply_text("No active download to cancel.")

@app.on_message(filters.regex(r'https?://(?:www\.)?(?:terabox\.(?:com|app)|1024tera\.com|terafileshare\.com)'))
async def handle_terabox_link(client: Client, message: Message):
    """Handle Terabox links in DM"""
    
    # Only process in private chats
    if message.chat.type != "private":
        await message.reply_text(
            "📩 **Please use me in private messages!**\n\n"
            "I can only download videos when you message me directly.\n"
            "Send the link to me in a private chat."
        )
        return
    
    user_id = message.from_user.id
    url = message.text.strip()
    
    # Check if user already has active download
    if user_id in user_downloads:
        await message.reply_text("⏳ You already have a download in progress. Please wait or use /cancel")
        return
    
    try:
        # Send initial processing message
        processing_msg = await message.reply_text(
            f"🔍 **Processing your link...**\n\n"
            f"**URL:** `{url[:50]}...`\n"
            f"**Status:** Extracting video information..."
        )
        
        # Extract direct link
        link_info = await downloader.get_direct_link(url)
        
        if not link_info or not link_info.get('success'):
            await processing_msg.edit_text(
                "❌ **Failed to process link**\n\n"
                "Possible reasons:\n"
                "• Invalid or expired link\n"
                "• Video is private/removed\n"
                "• Server error\n\n"
                "Please try another link or try again later."
            )
            return
        
        # Get video info
        direct_url = link_info.get('direct_url')
        filename = link_info.get('filename', 'video.mp4')
        file_size = link_info.get('size', 0)
        
        # Create download task for user
        user_downloads[user_id] = {
            'url': direct_url,
            'filename': filename,
            'size': file_size,
            'cancelled': False,
            'start_time': time.time()
        }
        
        # Show download confirmation
        confirm_text = (
            f"✅ **Video Found!**\n\n"
            f"**📹 File:** `{filename}`\n"
            f"**📦 Size:** `{format_size(file_size)}`\n"
            f"**🔗 Status:** Ready to download\n\n"
            f"Click below to start downloading to your DM:"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇️ Download Now", callback_data=f"dl_{user_id}_{filename}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_dl")]
        ])
        
        await processing_msg.edit_text(confirm_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error processing link: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

@app.on_callback_query()
async def handle_callback(client, callback_query):
    """Handle button callbacks"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    message = callback_query.message
    
    # Only process in private chats
    if message.chat.type != "private":
        await callback_query.answer("Please use in private chat", show_alert=True)
        return
    
    if data == "cancel_dl":
        # Cancel download confirmation
        if user_id in user_downloads:
            user_downloads[user_id]['cancelled'] = True
            await message.edit_text("⏹️ Download cancelled.")
        else:
            await message.edit_text("No active download.")
        
        await callback_query.answer()
        return
    
    if data.startswith("dl_"):
        # Start download
        await callback_query.answer("Starting download...")
        
        # Extract data
        parts = data.split('_')
        if len(parts) < 3:
            return
        
        file_user_id = int(parts[1])
        filename = '_'.join(parts[2:])
        
        # Verify user
        if user_id != file_user_id:
            await callback_query.answer("This download is not for you!", show_alert=True)
            return
        
        # Get download info
        if user_id not in user_downloads:
            await message.edit_text("Download expired or cancelled.")
            return
        
        download_info = user_downloads[user_id]
        if download_info.get('cancelled'):
            await message.edit_text("Download was cancelled.")
            return
        
        try:
            # Update message to show download started
            await message.edit_text(
                f"⬇️ **Starting Download...**\n\n"
                f"**File:** `{filename}`\n"
                f"**Size:** `{format_size(download_info['size'])}`\n"
                f"**Status:** Downloading to your DM..."
            )
            
            # Define progress callback
            async def update_progress(progress, downloaded, total):
                try:
                    if user_id in user_downloads and user_downloads[user_id].get('cancelled'):
                        return False
                    
                    # Update progress in message
                    bar_length = 20
                    filled_length = int(bar_length * progress / 100)
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    
                    speed = downloaded / (time.time() - download_info['start_time']) if time.time() > download_info['start_time'] else 0
                    eta = (total - downloaded) / speed if speed > 0 else 0
                    
                    text = (
                        f"📥 **Downloading...**\n\n"
                        f"**File:** `{filename}`\n"
                        f"**Progress:** `{bar}` {progress:.1f}%\n"
                        f"**Downloaded:** `{format_size(downloaded)} / {format_size(total)}`\n"
                        f"**Speed:** `{format_size(speed)}/s`\n"
                        f"**ETA:** `{format_time(eta)}`\n\n"
                        f"_Sending to your DM..._"
                    )
                    
                    await message.edit_text(text)
                    return True
                    
                except Exception as e:
                    logger.error(f"Progress update error: {e}")
                    return True
            
            # Download file
            filepath = f"downloads/{user_id}_{filename}"
            success = await downloader.download_file(
                download_info['url'],
                filepath,
                update_progress
            )
            
            if not success or (user_id in user_downloads and user_downloads[user_id].get('cancelled')):
                await message.edit_text("❌ Download failed or was cancelled.")
                # Clean up
                try:
                    os.remove(filepath)
                except:
                    pass
                return
            
            # Update message
            await message.edit_text("📤 **Uploading to your DM...**")
            
            # Send video to user's DM
            try:
                # Check file size
                actual_size = os.path.getsize(filepath)
                
                # Send as video if it's a video file
                if filename.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
                    await client.send_video(
                        chat_id=user_id,
                        video=filepath,
                        caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(actual_size)}`",
                        supports_streaming=True,
                        progress=lambda current, total: logger.info(f"Uploading: {current}/{total}")
                    )
                else:
                    # Send as document for other file types
                    await client.send_document(
                        chat_id=user_id,
                        document=filepath,
                        caption=f"✅ **Download Complete!**\n\n**File:** `{filename}`\n**Size:** `{format_size(actual_size)}`"
                    )
                
                # Update success message
                await message.edit_text(
                    f"✅ **Video sent to your DM!**\n\n"
                    f"**File:** `{filename}`\n"
                    f"**Size:** `{format_size(actual_size)}`\n"
                    f"**Status:** ✅ Successfully delivered\n\n"
                    f"_Check your private messages for the video._"
                )
                
                logger.info(f"Video sent to user {user_id}: {filename}")
                
            except FloodWait as e:
                # Handle flood wait
                await message.edit_text(f"⏳ Please wait {e.value} seconds before sending another video.")
                await asyncio.sleep(e.value)
            except Exception as e:
                logger.error(f"Error sending video: {e}")
                await message.edit_text(f"❌ Error sending video: {str(e)}")
            
            # Clean up
            try:
                os.remove(filepath)
            except:
                pass
            
            # Clear user download state
            if user_id in user_downloads:
                del user_downloads[user_id]
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            await message.edit_text(f"❌ Download failed: {str(e)}")
            
            # Clean up
            if user_id in user_downloads:
                del user_downloads[user_id]
            
            try:
                os.remove(filepath)
            except:
                pass
        
        await callback_query.answer()

# Handle all other messages in private chat
@app.on_message(filters.private & ~filters.command(["start", "help", "status", "cancel"]))
async def handle_private_messages(client: Client, message: Message):
    """Handle other private messages"""
    if message.text and not message.text.startswith('http'):
        await message.reply_text(
            "📩 **Send me a Terabox link!**\n\n"
            "I can download videos from:\n"
            "• terabox.com\n"
            "• 1024tera.com\n"
            "• terafileshare.com\n\n"
            "Just paste your link here and I'll download it to your DM!"
        )

# Start the bot
async def main():
    """Main function"""
    logger.info("Starting Terabox Downloader Bot...")
    
    try:
        await app.start()
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"Bot started: @{me.username} (ID: {me.id})")
        logger.info(f"Bot will send videos directly to user DMs")
        
        # Keep bot running
        await idle()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
    finally:
        # Cleanup
        await app.stop()
        await downloader.close()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
