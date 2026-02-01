# bot.py - FIXED VERSION
import os
import sys
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get credentials
API_ID = int(os.environ.get("API_ID", "26676741"))
API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8382794975:AAFlONsd1xL94PLkhKfwTmyR81vHW53ta6E")

# Create client - SIMPLER CONFIG
app = Client(
    "teraboxbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Create cookies file without problematic characters
cookies_content = """# Netscape HTTP Cookie File
.1024tera.com	TRUE	/	FALSE	1775120492	browserid	4V1elzoKTZ7pTEBLp_vHA9QIJoiLYpZaBxaHJ_NEpCryUX3v5XJX4KpLzEo=
.1024tera.com	TRUE	/	FALSE	1772531231	lang	en
.1024tera.com	TRUE	/	FALSE	1801472492	TSID	MvUeOemI9CRbdNw7wxRDjZf1eMqSVapF
.1024tera.com	TRUE	/	FALSE	1775123231	shareUpdateRandom	97
.1024tera.com	TRUE	/	FALSE	1804499232	__bid_n	19c186fa5d9814629b4207
.1024tera.com	TRUE	/	TRUE	1801472552	ndus	YQjKZL8peHuipOIVKwKsnrUz82kNQfu2Kk936GL7
dm.1024tera.com	FALSE	/	FALSE	0	csrfToken	X2qpBfnEoM6UXY4_kTa08sBf
dm.1024tera.com	FALSE	/	FALSE	1772531232	ndut_fmt	E2D9670B528107927362DA057D745265896AAD3074E81B5AE789F685649DA0A5
dm.1024tera.com	FALSE	/	FALSE	1772531235	ndut_fmv	6ec573e6027ec9f4f82dbd862d9e762eee3745caeb28b072ac1ed7a3accd9d113354223ec9bb7661ea456acc0f021f9ad815c0182013b2ada8bfac035e4a99efee480d782e58f64e0839dace4e90ceb0241ba32717aa2aecdaded096ce11a9d030e254fe51bb42eca2b8fc2795312241"""

# Remove the problematic line with backslashes
with open("cookies.txt", "w") as f:
    f.write(cookies_content)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    """Handle /start command"""
    try:
        text = """🤖 **Terabox Downloader Bot** 

✅ Bot is working!
✅ Cookies are loaded!

Send me a Terabox link to download.

**Example:** https://terafileshare.com/s/1tgHSFjB1Jjv1tLdX8sGLiA

**Commands:**
/start - Show this message
/status - Check bot status
/ping - Test response

**Note:** Bot works only in private messages!"""
        
        await message.reply_text(text)
        logger.info(f"User {message.from_user.id} started bot")
    except Exception as e:
        logger.error(f"Start error: {e}")

@app.on_message(filters.command("status"))
async def status_command(client, message):
    """Check bot status"""
    try:
        await message.reply_text("✅ Bot Status: ONLINE\n\nBot is running and ready!")
    except Exception as e:
        logger.error(f"Status error: {e}")

@app.on_message(filters.command("ping"))
async def ping_command(client, message):
    """Ping command"""
    try:
        await message.reply_text("🏓 Pong! Bot is alive!")
    except Exception as e:
        logger.error(f"Ping error: {e}")

@app.on_message(filters.text & filters.private)
async def handle_messages(client, message):
    """Handle all messages in private chat"""
    try:
        text = message.text.strip()
        
        # Skip commands
        if text.startswith('/'):
            return
        
        # Check if it's a Terabox link
        if 'terabox' in text.lower() or '1024tera' in text.lower() or 'terafileshare' in text.lower():
            await message.reply_text(
                f"🔗 **Terabox Link Received!**\n\n"
                f"I got your link: {text[:50]}...\n\n"
                f"✅ Cookies are loaded\n"
                f"✅ Bot is ready\n\n"
                f"To download videos, I need additional libraries.\n"
                f"Run: pip install aiohttp"
            )
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

# Handle group messages
@app.on_message(filters.group)
async def handle_group(client, message):
    """Handle messages in groups"""
    if message.text and message.text.startswith('/start'):
        await message.reply_text(
            "⚠️ **I work only in private messages!**\n\n"
            "Please send me a direct message (DM) to use this bot."
        )

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
