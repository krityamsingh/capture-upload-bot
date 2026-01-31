from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import logging

from config import config
from handlers import (
    handle_start,
    handle_task_command,
    handle_group_message,
    handle_channel_post,
    handle_callback_query
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create bot client
app = Client(
    "ad_tracking_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Register handlers
@app.on_message(filters.command("start"))
async def start_wrapper(client, message):
    await handle_start(client, message)

@app.on_message(filters.command("task"))
async def task_wrapper(client, message):
    await handle_task_command(client, message)

@app.on_message(filters.group & filters.incoming)
async def group_message_wrapper(client, message):
    await handle_group_message(client, message)

@app.on_message(filters.chat(config.CHANNEL_IDS))
async def channel_post_wrapper(client, message):
    await handle_channel_post(client, message)

@app.on_callback_query()
async def callback_wrapper(client, callback_query):
    await handle_callback_query(client, callback_query)

async def main():
    await app.start()
    
    # Get bot info
    bot_info = await app.get_me()
    logger.info(f"🤖 Bot started: @{bot_info.username}")
    logger.info(f"📊 Monitoring {len(config.CHANNEL_IDS)} channels")
    
    if not config.GROUP_ID:
        logger.warning("⚠️ GROUP_ID not set! Group monitoring disabled.")
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    print("=" * 60)
    print("🚨 CRITICAL SECURITY WARNING")
    print("=" * 60)
    print("Your MongoDB password is publicly exposed!")
    print("Immediate actions required:")
    print("1. Change MongoDB password NOW")
    print("2. Rotate your bot token")
    print("3. Update API credentials if possible")
    print("=" * 60)
    
    # Uncomment after fixing security issues
    # app.run(main())
