import asyncio
import logging
import sys

from pyrogram import Client
from motor.motor_asyncio import AsyncIOMotorClient

from config import config


# ─────────────────────────────
# Logging setup
# ─────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
LOGGER = logging.getLogger("RajputBot")


# ─────────────────────────────
# MongoDB
# ─────────────────────────────
mongo_client = AsyncIOMotorClient(config.MONGO_URI)
db = mongo_client[config.DATABASE_NAME]


# ─────────────────────────────
# Pyrogram Client
# ─────────────────────────────
app = Client(
    name="rajput-bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    workers=50,
    in_memory=True,
)


# ─────────────────────────────
# Startup / Shutdown hooks
# ─────────────────────────────
async def start_bot():
    try:
        await app.start()
        LOGGER.info("✅ Bot started successfully")

        # Test MongoDB
        await db.command("ping")
        LOGGER.info("✅ MongoDB connected")

        # Idle
        await asyncio.Event().wait()

    except Exception as e:
        LOGGER.exception("❌ Fatal error while running bot")
        raise e

    finally:
        await app.stop()
        mongo_client.close()
        LOGGER.info("🛑 Bot stopped")


# ─────────────────────────────
# Entrypoint
# ─────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        LOGGER.info("⏹️ Bot interrupted by user")
