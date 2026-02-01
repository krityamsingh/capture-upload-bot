# bot.py - SIMPLIFIED VERSION FOR HEROKU
import os
import sys
import re
import asyncio
import aiohttp
import logging
import time
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

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

logger.info("Starting Terabox Bot...")

# Simple Terabox extractor
class SimpleTeraboxExtractor:
    def __init__(self):
        self.session = None
        
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def extract_direct_link(self, url):
        """Extract direct download link from Terabox"""
        try:
            # Extract short code
            short_code = None
            patterns = [
                r'terabox\.com/s/([a-zA-Z0-9_-]+)',
                r'1024tera\.com/s/([a-zA-Z0-9_-]+)',
                r'terafileshare\.com/s/([a-zA-Z0-9_-]+)',
                r'/s/([a-zA-Z0-9_-]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    short_code = match.group(1)
                    break
            
            if not short_code:
                return None
            
            # Try to get direct link
            # This is a simplified approach - in production you'd need proper API calls
            api_url = f"https://www.terabox.com/api/shorturlinfo?shorturl={short_code}&root=1"
            
            session = await self.get_session()
            async with session.get(api_url) as response:
                if response.status == 200:
                    return f"https://example.com/direct-link-placeholder-{short_code}"
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting link: {e}")
            return None

# Create extractor
extractor = SimpleTeraboxExtractor()

# Create Pyrogram client
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True  # Important for Heroku
)

# Keep track of active tasks
active_tasks = {}

# Helper function to format size
def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

# Command handlers
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    """Handle /start command"""
    text = """
🤖 **Terabox Video Downloader Bot**

I can download videos from:
• terabox.com
• 1024tera.com  
• terafileshare.com

**How to use:**
1. Send me a Terabox share link
2. I'll process and download it
3. You'll receive the video

**Example:**
`https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA`

**Commands:**
/start - Show this message
/status - Check bot status
/ping - Test response

**Note:** Bot is running on Heroku!
    """
    await message.reply_text(text)

@app.on_message(filters.command("status"))
async def status_handler(client, message):
    """Handle /status command"""
    status_text = f"""
✅ **Bot Status**

**Active Downloads:** {len(active_tasks)}
**Uptime:** {time.time()}
**Platform:** Heroku

Bot is ready to receive links!
    """
    await message.reply_text(status_text)

@app.on_message(filters.command("ping"))
async def ping_handler(client, message):
    """Handle /ping command"""
    start = time.time()
    msg = await message.reply_text("🏓 Pong!")
    end = time.time()
    await msg.edit_text(f"🏓 Pong! `{round((end - start) * 1000, 2)}ms`")

@app.on_message(filters.regex(r'https?://'))
async def link_handler(client, message):
    """Handle any URL"""
    url = message.text.strip()
    
    # Check if it's a terabox link
    if not any(domain in url for domain in ['terabox', '1024tera', 'terafileshare']):
        await message.reply_text("⚠️ Please send a Terabox, 1024tera, or terafileshare link.")
        return
    
    try:
        # Send processing message
        status_msg = await message.reply_text("🔍 Processing your link...")
        
        # Extract short code for display
        short_code = None
        match = re.search(r'/s/([a-zA-Z0-9_-]+)', url)
        if match:
            short_code = match.group(1)
        
        # Simulate processing (in production, use actual extraction)
        await asyncio.sleep(2)
        
        # Create download button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇️ Download Now", callback_data=f"download_{short_code or 'video'}")]
        ])
        
        await status_msg.edit_text(
            f"✅ **Link Processed!**\n\n"
            f"**URL:** `{url[:50]}...`\n"
            f"**Status:** Ready to download\n\n"
            f"Click the button below to download:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error processing link: {e}")
        await message.reply_text(f"❌ Error processing link: {str(e)}")

@app.on_callback_query()
async def callback_handler(client, callback_query):
    """Handle button clicks"""
    data = callback_query.data
    message = callback_query.message
    
    if data.startswith("download_"):
        file_name = data.replace("download_", "")
        
        try:
            # Update message
            await message.edit_text("⬇️ Starting download... Please wait.")
            
            # Simulate download progress
            for i in range(1, 6):
                await asyncio.sleep(1)
                await message.edit_text(f"⬇️ Downloading... {i * 20}% complete")
            
            # Send a sample video (in production, send actual downloaded file)
            await message.edit_text("📤 Uploading to Telegram...")
            
            # For demo, send a message instead of actual file
            await client.send_message(
                message.chat.id,
                f"✅ **Download Complete!**\n\n"
                f"**File:** `{file_name}.mp4`\n"
                f"**Size:** 150.25 MB\n"
                f"**Status:** Successfully downloaded\n\n"
                f"Note: This is a demo. In production, actual video would be sent."
            )
            
            await message.delete()
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            await message.edit_text(f"❌ Download failed: {str(e)}")
        
        await callback_query.answer()

# Simplified main function
def main():
    """Main function to run the bot"""
    logger.info("=== Starting Terabox Bot ===")
    logger.info(f"API_ID: {API_ID}")
    logger.info(f"Bot should start now...")
    
    try:
        # Run the bot
        app.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        # Cleanup
        asyncio.run(extractor.close())
        logger.info("Bot cleanup complete")

if __name__ == "__main__":
    # Run the bot
    main()
