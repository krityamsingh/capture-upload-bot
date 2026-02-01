# bot.py - WORKING VERSION FOR HEROKU
import os
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
import sys

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

# Validate credentials
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("Missing environment variables!")
    sys.exit(1)

logger.info("Starting Terabox DM Bot...")
logger.info(f"API_ID: {API_ID}")
logger.info(f"BOT_TOKEN first 10 chars: {BOT_TOKEN[:10]}...")

# Create the client
app = Client(
    "terabox_dm_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

# Start command handler
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    """Handle /start command in DM"""
    try:
        welcome_text = """
🤖 **Terabox Downloader Bot** 

**Hello!** I'm here to help you download videos from:
• terabox.com
• 1024tera.com  
• terafileshare.com

**How to use:**
1. Send me any Terabox link in this chat
2. I'll process it
3. You'll get the video here

**Commands:**
/start - Show this message
/status - Check bot status
/test - Test the bot

**Note:** I work only in private messages!
"""
        await message.reply_text(welcome_text)
        logger.info(f"User {message.from_user.id} started bot")
    except Exception as e:
        logger.error(f"Start command error: {e}")

@app.on_message(filters.command("status") & filters.private)
async def status_command(client, message):
    """Handle /status command"""
    try:
        await message.reply_text("✅ Bot is online and running in your DM!")
        logger.info(f"Status checked by {message.from_user.id}")
    except Exception as e:
        logger.error(f"Status command error: {e}")

@app.on_message(filters.command("test") & filters.private)
async def test_command(client, message):
    """Test if bot is working"""
    try:
        await message.reply_text("✅ Bot is working! Try sending a Terabox link.")
    except Exception as e:
        logger.error(f"Test command error: {e}")

@app.on_message(filters.text & filters.private & ~filters.command(["start", "status", "test"]))
async def handle_text_messages(client, message):
    """Handle all text messages in private chat"""
    try:
        text = message.text.strip()
        
        # Check if it looks like a Terabox link
        if any(domain in text.lower() for domain in ['terabox', '1024tera', 'terafileshare']):
            await message.reply_text(
                f"🔗 **Link Received!**\n\n"
                f"I got your Terabox link:\n`{text[:50]}...`\n\n"
                f"**Note:** The download functionality requires proper Terabox API integration.\n\n"
                f"**To implement actual downloads:**\n"
                f"1. You need to implement Terabox API calls\n"
                f"2. Handle authentication and file extraction\n"
                f"3. Download and send videos\n\n"
                f"For now, I'm working as a demo bot in your DM!"
            )
        else:
            await message.reply_text(
                "📩 **Send me a Terabox link!**\n\n"
                "I can download videos from:\n"
                "• terabox.com\n"
                "• 1024tera.com\n"
                "• terafileshare.com\n\n"
                "Just paste your link here!"
            )
            
    except Exception as e:
        logger.error(f"Text handler error: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

# Handle group messages
@app.on_message(filters.group & filters.command("start"))
async def start_group(client, message):
    """Handle /start in groups"""
    await message.reply_text(
        "⚠️ **I work only in private messages!**\n\n"
        "Please send me a direct message (DM) to use this bot.\n"
        "Click here to start a private chat: [Message Me Privately](https://t.me/terabox_downloader_bot)"
    )

# Main function
async def main():
    """Main function to run the bot"""
    logger.info("=== Starting Bot ===")
    
    try:
        await app.start()
        logger.info("✅ Bot started successfully!")
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"🤖 Bot: @{me.username}")
        logger.info(f"🆔 Bot ID: {me.id}")
        logger.info(f"📝 Bot name: {me.first_name}")
        
        # Keep running
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        try:
            await app.stop()
            logger.info("Bot stopped cleanly")
        except:
            logger.info("Bot stopped")

# Run the bot
if __name__ == "__main__":
    # Use this simple approach
    logger.info("Starting bot with simple runner...")
    
    try:
        # Create event loop
        loop = asyncio.get_event_loop()
        
        # Run the main function
        if loop.is_running():
            # If loop is already running (like in some environments)
            loop.create_task(main())
        else:
            # Run in new loop
            loop.run_until_complete(main())
            
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Failed to start: {e}")
