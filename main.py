# ==================== MAIN.PY ====================
# Capture Upload Bot – FINAL FIXED VERSION

import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

from config import config
from database.mongodb import db
from database.models import UserSession
from states import CharacterStates

from handlers import (
    register_sudo_handlers,
    register_command_handlers,
    register_callback_handlers,
    register_character_management_handlers,
    register_mass_upload_handlers
)

from handlers.sudo_handlers import is_sudo_user
from utils import keyboards, helpers

# ------------------------------------------------
# Logging Configuration
# ------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ------------------------------------------------
# Main Bot Class
# ------------------------------------------------
class UploadBot:
    """Main bot class"""

    def __init__(self):
        self.client = Client(
            "upload_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )

        self._register_handlers()

    # ------------------------------------------------
    # Register Handlers (ORDER MATTERS)
    # ------------------------------------------------
    def _register_handlers(self):
        # 1️⃣ SUDO FIRST
        register_sudo_handlers(self.client)

        # 2️⃣ NORMAL HANDLERS
        register_command_handlers(self.client)
        register_callback_handlers(self.client)
        register_character_management_handlers(self.client)
        register_mass_upload_handlers(self.client)

        # 3️⃣ PRIVATE MESSAGE FLOW HANDLER
        self.client.on_message(
            filters.private & (filters.text | filters.media | filters.document | filters.audio)
        )(self._handle_message)

    # ------------------------------------------------
    # Main Message Handler (State Machine)
    # ------------------------------------------------
    async def _handle_message(self, client: Client, message: Message):
        # Ignore commands
        if message.text and message.text.startswith("/"):
            return

        if not message.from_user:
            return

        user_id = message.from_user.id

        # Fetch sessions FIRST
        session = await db.get_session(user_id)
        mass_session = await db.get_mass_upload_session(user_id)

        # No active flow → ignore
        if not session and not mass_session:
            return

        # Authorization check (DB-based sudo only)
        if not await is_sudo_user(None, None, message):
            await message.reply_text("❌ You are not authorized to use this bot.")
            return

        # If mass upload active, do not handle single flow
        if mass_session:
            return

        try:
            logger.info(f"User {user_id} | State: {session.state}")

            if session.state == CharacterStates.WAITING_CHAR_NAME.value:
                await self._handle_char_name(message, session)

            elif session.state == CharacterStates.WAITING_ANIME_NAME.value:
                await self._handle_anime_name(message, session)

            elif session.state == CharacterStates.WAITING_MEDIA.value:
                await self._handle_media_upload(message, session)

            else:
                logger.warning(f"Unknown state {session.state} for user {user_id}")

        except Exception as e:
            logger.exception("State handling error")
            await message.reply_text("❌ Error occurred. Restart with /addchar")
            await db.delete_session(user_id)

    # ------------------------------------------------
    # Step 1: Character Name
    # ------------------------------------------------
    async def _handle_char_name(self, message: Message, session: UserSession):
        if not message.text:
            await message.reply_text("❌ Send character name as text.")
            return

        session.char_name = message.text.strip()
        session.state = CharacterStates.WAITING_ANIME_NAME.value
        await db.save_session(session)

        await message.reply_text(
            "✅ **Character name saved!**\n\n"
            "📺 **Send the anime name:**",
            reply_markup=helpers.force_reply()
        )

    # ------------------------------------------------
    # Step 2: Anime Name
    # ------------------------------------------------
    async def _handle_anime_name(self, message: Message, session: UserSession):
        if not message.text:
            await message.reply_text("❌ Send anime name as text.")
            return

        session.anime_name = message.text.strip()
        session.state = CharacterStates.WAITING_RARITY.value
        await db.save_session(session)

        await message.reply_text(
            "✅ **Anime name saved!**\n\n"
            "⭐ **Select character rarity:**",
            reply_markup=keyboards.get_rarity_keyboard()
        )

    # ------------------------------------------------
    # Step 3: Media Upload
    # ------------------------------------------------
    async def _handle_media_upload(self, message: Message, session: UserSession):
        if not (message.photo or message.video or message.audio or message.document):
            await message.reply_text("❌ Send a valid media file.")
            return

        file_size = 0
        media = message.photo or message.video or message.audio or message.document
        file_size = media.file_size or 0

        if file_size > config.MAX_FILE_SIZE:
            await message.reply_text(
                f"❌ File too large (Max {config.MAX_FILE_SIZE // (1024*1024)}MB)"
            )
            return

        status = await message.reply_text("🔄 Uploading media...")

        async def update(text):
            try:
                await status.edit_text(text)
            except:
                pass

        try:
            media_url, media_type = await helpers.upload_media_with_fallback(
                self.client,
                message,
                status_callback=update
            )

            if not media_url:
                await update("❌ Upload failed. Try again.")
                return

            session.media_url = media_url
            session.media_type = media_type
            session.state = CharacterStates.WAITING_CONFIRMATION.value
            await db.save_session(session)

            preview = helpers.format_character_preview(session)

            await update(
                f"{preview}\n\n"
                "✅ **Media uploaded successfully!**"
            )

            await message.reply_text(
                "📋 **Confirm character:**",
                reply_markup=keyboards.get_confirmation_keyboard()
            )

        except Exception:
            logger.exception("Media upload error")
            await update("❌ Media upload failed.")

    # ------------------------------------------------
    # Bot Lifecycle
    # ------------------------------------------------
    async def start(self):
        try:
            await db.connect()
            logger.info("Database connected")

            await self.client.start()
            me = await self.client.get_me()
            logger.info(f"Bot started as @{me.username}")

            await asyncio.Event().wait()

        finally:
            await self.stop()

    async def stop(self):
        try:
            await self.client.stop()
            await db.disconnect()
            logger.info("Bot stopped")
        except Exception:
            logger.exception("Shutdown error")


# ------------------------------------------------
# Entry Point
# ------------------------------------------------
async def main():
    bot = UploadBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
