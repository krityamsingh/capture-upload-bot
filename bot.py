# bot.py - MINIMAL WORKING BOT
import os
import logging
from pyrogram import Client, filters

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get credentials from environment
API_ID = int(os.environ.get("API_ID", "26676741"))
API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E")

# Log credentials (hide full token)
logger.info(f"API_ID: {API_ID}")
logger.info(f"BOT_TOKEN first 10: {BOT_TOKEN[:10]}...")

# Create simple client
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Test command - should work immediately
@app.on_message(filters.command("start"))
async def start(client, message):
    logger.info(f"Received /start from {message.from_user.id}")
    try:
        await message.reply_text("✅ Bot is working! Try /ping")
    except Exception as e:
        logger.error(f"Error in /start: {e}")

@app.on_message(filters.command("ping"))
async def ping(client, message):
    logger.info(f"Received /ping from {message.from_user.id}")
    try:
        await message.reply_text("🏓 Pong! Bot is alive!")
    except Exception as e:
        logger.error(f"Error in /ping: {e}")

@app.on_message(filters.command("help"))
async def help_cmd(client, message):
    logger.info(f"Received /help from {message.from_user.id}")
    try:
        await message.reply_text(
            "🤖 **Terabox Bot Help**\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/ping - Check if bot is alive\n"
            "/help - Show this message\n\n"
            "Send any Terabox link to download."
        )
    except Exception as e:
        logger.error(f"Error in /help: {e}")

@app.on_message(filters.text)
async def echo(client, message):
    logger.info(f"Received text from {message.from_user.id}: {message.text[:50]}")
    try:
        if not message.text.startswith('/'):
            await message.reply_text(
                f"📩 You sent: {message.text[:100]}\n\n"
                f"Bot is working! Test commands:\n"
                f"/start - /ping - /help"
            )
    except Exception as e:
        logger.error(f"Error in echo: {e}")

# Simple main function
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Starting Terabox Bot...")
    logger.info("=" * 50)
    
    try:
        app.run()
        logger.info("Bot stopped normally")
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
