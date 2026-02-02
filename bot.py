# bot.py - SIMPLE GUARANTEED WORKING BOT
import os
import sys
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get credentials
API_ID = int(os.environ.get("API_ID", "26676741"))
API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E")

# Log startup
logger.info("=" * 50)
logger.info("STARTING TERABOX BOT")
logger.info(f"API_ID: {API_ID}")
logger.info(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")
logger.info("=" * 50)

# Create client with minimal config
app = Client(
    "terabox_dm_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1,
    sleep_threshold=30
)

# Basic command handlers
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    logger.info(f"Received /start from {message.from_user.id}")
    await message.reply_text("✅ Bot is working in DM!")

@app.on_message(filters.command("ping"))
async def ping_handler(client, message):
    logger.info(f"Received /ping from {message.from_user.id}")
    await message.reply_text("🏓 Pong!")

@app.on_message(filters.command("test"))
async def test_handler(client, message):
    logger.info(f"Received /test from {message.from_user.id}")
    await message.reply_text("✅ Test successful! Bot is responding.")

# Handle all messages in private chat
@app.on_message(filters.private & filters.text)
async def private_handler(client, message):
    text = message.text.strip()
    user_id = message.from_user.id
    
    logger.info(f"Received message from {user_id}: {text[:50]}")
    
    # Skip if it's a command
    if text.startswith('/'):
        return
    
    # Check if it's a Terabox link
    if 'terabox' in text.lower() or '1024tera' in text.lower() or 'terafileshare' in text.lower():
        await message.reply_text(
            f"🔗 **Terabox Link Detected!**\n\n"
            f"Link: {text[:100]}...\n\n"
            f"✅ Bot is working!\n"
            f"✅ Ready to download\n\n"
            f"**Download feature requires:**\n"
            "1. Proper cookies.txt file\n"
            "2. Working Terabox API\n"
            "3. Network access to Terabox\n\n"
            "**To add download:**\n"
            "• Install aiohttp in requirements.txt\n"
            "• Add download function\n"
            "• Test with valid cookies"
        )
    else:
        await message.reply_text(
            "📩 **Send me a Terabox link!**\n\n"
            "I can download from:\n"
            "• terabox.com\n"
            "• 1024tera.com\n"
            "• terafileshare.com\n\n"
            "Example: https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA"
        )

# Handle group messages
@app.on_message(filters.group & filters.command("start"))
async def group_start_handler(client, message):
    await message.reply_text(
        "⚠️ **I work only in private messages!**\n\n"
        "Please send me a direct message (DM) to use this bot."
    )

# Simple main function
def main():
    """Main function"""
    logger.info("Starting bot...")
    
    try:
        app.run()
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    # Create cookies.txt if it doesn't exist
    if not os.path.exists("cookies.txt"):
        with open("cookies.txt", "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write(".1024tera.com\tTRUE\t/\tFALSE\t1775120492\tbrowserid\t4V1elzoKTZ7pTEBLp_vHA9QIJoiLYpZaBxaHJ_NEpCryUX3v5XJX4KpLzEo=\n")
        logger.info("Created cookies.txt file")
    
    # Run the bot
    main()

