# ==================== RAJPUT.PY ====================
# Main entry file for Heroku deployment

import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

from config import config
from database.mongodb import db
from database.models import UserSession, Character
from states import CharacterStates
from handlers import (
    register_command_handlers,
    register_callback_handlers,
    register_character_management_handlers,
    register_mass_upload_handlers,
    register_sudo_handlers
)
from utils import keyboards, helpers


# ───────────────────────────
# Logging Configuration
# ───────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("RajputUploadBot")


class UploadBot:
    """Main bot controller"""

    def __init__(self):
        self.client = Client(
            name="upload_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            workers=50,
            in_memory=True
        )
        self._register_handlers()

    # ───────────────────────────
    # Handler Registration
    # ───────────────────────────
    def _register_handlers(self):
        register_command_handlers(self.client)
        register_callback_handlers(self.client)
        register_character_management_handlers(self.client)
        register_mass_upload_handlers(self.client)
        register_sudo_handlers(self.client)

        # Private flow handler
        self.client.on_message(
            filters.private & (filters.text | filters.media | filters.document | filters.audio)
        )(self._handle_message)

    # ───────────────────────────
    # Message Flow Handler
    # ───────────────────────────
    async def _handle_message(self, client: Client, message: Message):
        if message.text and message.text.startswith("/"):
            return

        if not message.from_user:
            return

        user_id = message.from_user.id

        # Authorization check
        if not await helpers.is_sudo_user(user_id):
            await message.reply_text(
                "❌ You are not authorized to use this bot.\nContact the admin."
            )
            return

        # Ignore if mass upload is active
        if await db.get_mass_upload_session(user_id):
            return

        session = await db.get_session(user_id)
        if not session:
            return

        try:
            logger.info(f"User {user_id} | State: {session.state}")

            if session.state == CharacterStates.WAITING_CHAR_NAME.value:
                await self._handle_char_name(message, session)

            elif session.state == CharacterStates.WAITING_ANIME_NAME.value:
                await self._handle_anime_name(message, session)

            elif session.state == CharacterStates.WAITING_MEDIA.value:
                await self._handle_media_upload(client, message, session)

            else:
                logger.warning(f"Unknown state: {session.state}")

        except Exception as e:
            logger.exception("State handler error")
            await message.reply_text(
                "❌ An error occurred. Please restart with /addchar"
            )
            await db.delete_session(user_id)

    # ───────────────────────────
    # State Handlers
    # ───────────────────────────
    async def _handle_char_name(self, message: Message, session: UserSession):
        if not message.text:
            await message.reply_text("❌ Send the character name as text.")
            return

        session.char_name = message.text.strip()
        session.state = CharacterStates.WAITING_ANIME_NAME.value
        await db.save_session(session)

        await message.reply_text(
            "✅ **Character name saved**\n\n"
            "🎬 Send the anime name:",
            reply_markup=helpers.force_reply()
        )

    async def _handle_anime_name(self, message: Message, session: UserSession):
        if not message.text:
            await message.reply_text("❌ Send the anime name as text.")
            return

        session.anime_name = message.text.strip()
        session.state = CharacterStates.WAITING_RARITY.value
        await db.save_session(session)

        await message.reply_text(
            "✅ **Anime name saved**\n\n"
            "🎯 Select rarity:",
            reply_markup=keyboards.get_rarity_keyboard()
        )

    async def _handle_media_upload(self, client: Client, message: Message, session: UserSession):
        if not (message.photo or message.video or message.audio or message.document):
            await message.reply_text(
                "❌ Please send a valid media file.\n\n"
                "📦 Max size: 50MB\n"
                "⚡ Upload: Catbox.moe"
            )
            return

        file_size = (
            (message.photo and message.photo.file_size) or
            (message.video and message.video.file_size) or
            (message.audio and message.audio.file_size) or
            (message.document and message.document.file_size) or
            0
        )

        if file_size > config.MAX_FILE_SIZE:
            await message.reply_text(
                f"❌ File too large. Max {config.MAX_FILE_SIZE // (1024*1024)}MB"
            )
            return

        status = await message.reply_text("🔄 Uploading media...")

        async def update(text):
            try:
                await status.edit_text(text)
            except Exception:
                pass

        try:
            media_url, media_type = await helpers.upload_media_with_fallback(
                client,
                message,
                status_callback=update
            )

            if not media_url:
                await update("❌ Upload failed. Try another file.")
                return

            session.media_url = media_url
            session.media_type = media_type
            session.state = CharacterStates.WAITING_CONFIRMATION.value
            await db.save_session(session)

            preview = helpers.format_character_preview(session)

            await update(
                f"{preview}\n\n"
                "✅ **Upload successful**\n"
                "Confirm to save character:"
            )

            await message.reply_text(
                "📌 Confirm details:",
                reply_markup=keyboards.get_confirmation_keyboard()
            )

        except Exception as e:
            logger.exception("Media upload failed")
            await update("❌ Error during upload.")

    # ───────────────────────────
    # Lifecycle
    # ───────────────────────────
    async def start(self):
        await db.connect()
        logger.info("MongoDB connected")

        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"Bot started as @{me.username}")

        await asyncio.Event().wait()

    async def stop(self):
        await self.client.stop()
        await db.disconnect()
        logger.info("Bot stopped")


# ───────────────────────────
# Entrypoint
# ───────────────────────────
async def main():
    bot = UploadBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot interrupted")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
