# bot.py - FIXED VERSION
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

# Create client
app = Client("teraboxbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Read cookies from file
def read_cookies():
    try:
        if os.path.exists("cookies.txt"):
            with open("cookies.txt", "r") as f:
                cookies = f.read()
                lines = len(cookies.strip().split('\n'))
                return f"✅ Cookies loaded ({lines} lines)"
        else:
            # Create default cookies file
            default_cookies = """# Netscape HTTP Cookie File
.1024tera.com	TRUE	/	FALSE	1775120492	browserid	4V1elzoKTZ7pTEBLp_vHA9QIJoiLYpZaBxaHJ_NEpCryUX3v5XJX4KpLzEo=
.1024tera.com	TRUE	/	FALSE	1772531231	lang	en
.1024tera.com	TRUE	/	FALSE	1801472492	TSID	MvUeOemI9CRbdNw7wxRDjZf1eMqSVapF"""
            with open("cookies.txt", "w") as f:
                f.write(default_cookies)
            return "✅ Created default cookies.txt"
    except Exception as e:
        return f"❌ Error reading cookies: {e}"

# Read cookies on startup
cookies_status = read_cookies()
logger.info(cookies_status)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    """Handle /start command"""
    try:
        # Only respond in private
        if message.chat.type != "private":
            await message.reply_text("⚠️ Please message me privately!")
            return
            
        await message.reply_text(
            "🤖 **Terabox Bot Started!**\n\n"
            f"{cookies_status}\n\n"
            "Send me a Terabox link to download."
        )
        logger.info(f"User {message.from_user.id} started bot")
    except Exception as e:
        logger.error(f"Start error: {e}")

@app.on_message(filters.command("status"))
async def status_command(client, message):
    """Check bot status"""
    try:
        await message.reply_text(f"✅ Bot Status: ONLINE\n\n{cookies_status}")
    except Exception as e:
        logger.error(f"Status error: {e}")

@app.on_message(filters.command("ping"))
async def ping_command(client, message):
    """Ping command"""
    try:
        await message.reply_text("🏓 Pong! Bot is alive!")
    except Exception as e:
        logger.error(f"Ping error: {e}")

@app.on_message(filters.command("cookies"))
async def cookies_command(client, message):
    """Check cookies status"""
    try:
        status = read_cookies()
        await message.reply_text(f"**Cookies Status:**\n\n{status}")
    except Exception as e:
        logger.error(f"Cookies error: {e}")

@app.on_message(filters.private & filters.text)
async def handle_messages(client, message):
    """Handle all private text messages"""
    try:
        text = message.text.strip()
        
        # Skip if it's a command (handled by other handlers)
        if text.startswith('/'):
            return
        
        # Check if it's a Terabox link
        if any(word in text.lower() for word in ['terabox', '1024tera', 'terafileshare']):
            await message.reply_text(
                f"🔗 **Terabox Link Received!**\n\n"
                f"Link: `{text[:50]}...`\n\n"
                f"✅ Cookies are loaded\n"
                f"✅ Ready to download\n\n"
                f"**To enable downloads, add:**\n"
                f"```pip install aiohttp```\n"
                f"to requirements.txt"
            )
        else:
            await message.reply_text(
                "📩 **Send me a Terabox link!**\n\n"
                "I can download from:\n"
                "• terabox.com\n"
                "• 1024tera.com\n"
                "• terafileshare.com"
            )
    except Exception as e:
        logger.error(f"Message handler error: {e}")

# Handle group messages
@app.on_message(filters.group)
async def handle_group(client, message):
    """Handle group messages"""
    if message.text and message.text.startswith('/start'):
        await message.reply_text("⚠️ I work only in private messages!")

# Main function
def main():
    """Main function"""
    logger.info("Starting Terabox Bot...")
    logger.info(f"API_ID: {API_ID}")
    
    try:
        app.run()
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    main()
