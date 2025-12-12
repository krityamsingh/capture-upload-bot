# ==================== HANDLERS/CHARACTER_MANAGEMENT_HANDLERS.PY ====================
# FINAL CLEAN VERSION (SUDO / OWNER SAFE)

import logging
from pyrogram import Client, filters
from pyrogram.types import Message

from config import config
from database.mongodb import db
from handlers.sudo_handlers import is_sudo_user
from utils import helpers

logger = logging.getLogger(__name__)


# ------------------------------------------------
# Permission Check
# ------------------------------------------------
async def owner_or_sudo(message: Message) -> bool:
    if message.from_user.id == config.OWNER_ID:
        return True
    return await is_sudo_user(None, None, message)


# ------------------------------------------------
# Character Management Class
# ------------------------------------------------
class CharacterManagementHandlers:

    def __init__(self, client: Client):
        self.client = client

    # ---------------- DEL CHARACTER ----------------
    async def delchar_command(self, client: Client, message: Message):
        if not await owner_or_sudo(message):
            return await message.reply_text("❌ You are not authorized to use this command.")

        args = message.text.split()
        if len(args) != 2:
            return await message.reply_text(
                "🗑️ **Delete Character**\n\n"
                "**Usage:** `/delchar <character_id>`"
            )

        try:
            character_id = int(args[1])
            character = await db.get_character_by_id(character_id)

            if not character:
                return await message.reply_text("❌ Character not found.")

            deleted = await db.delete_character(character_id)
            if deleted:
                await message.reply_text("✅ Character deleted successfully.")
                logger.info(f"Deleted character {character_id}")
            else:
                await message.reply_text("❌ Failed to delete character.")

        except ValueError:
            await message.reply_text("❌ Invalid character ID.")
        except Exception:
            logger.exception("delchar error")
            await message.reply_text("❌ Error deleting character.")

    # ---------------- UPDATE CHARACTER INFO ----------------
    async def uchar_command(self, client: Client, message: Message):
        if not await owner_or_sudo(message):
            return await message.reply_text("❌ You are not authorized to use this command.")

        args = message.text.split()
        if len(args) < 5:
            return await message.reply_text(
                "✏️ **Update Character**\n\n"
                "`/uchar <id> <name> <anime> <rarity_no> [subrarity]`"
            )

        try:
            char_id = int(args[1])
            name = args[2]
            anime = args[3]
            rarity_no = int(args[4])
            subrarity = args[5] if len(args) > 5 else None

            if rarity_no not in config.RARITY_MAP:
                return await message.reply_text("❌ Invalid rarity number.")

            character = await db.get_character_by_id(char_id)
            if not character:
                return await message.reply_text("❌ Character not found.")

            rarity_name = config.RARITY_MAP[rarity_no]
            subrarity_name = None

            if rarity_no == 5 and subrarity:
                subrarity_name = config.LIMITED_SUBTYPES.get(subrarity)
            elif rarity_no == 6 and subrarity:
                subrarity_name = config.CELESTIAL_SUBTYPES.get(subrarity)

            updated = await db.update_character(
                character_id=char_id,
                char_name=name,
                anime_name=anime,
                rarity=rarity_name,
                subrarity=subrarity_name
            )

            if updated:
                await message.reply_text("✅ Character updated successfully.")
                logger.info(f"Updated character {char_id}")
            else:
                await message.reply_text("❌ Update failed.")

        except ValueError:
            await message.reply_text("❌ Invalid input format.")
        except Exception:
            logger.exception("uchar error")
            await message.reply_text("❌ Error updating character.")

    # ---------------- UPDATE CHARACTER MEDIA ----------------
    async def uimage_command(self, client: Client, message: Message):
        if not await owner_or_sudo(message):
            return await message.reply_text("❌ You are not authorized to use this command.")

        if not message.reply_to_message or not (
            message.reply_to_message.photo or
            message.reply_to_message.video or
            message.reply_to_message.audio or
            message.reply_to_message.document
        ):
            return await message.reply_text(
                "❌ Reply to a media file with `/uimage <character_id>`"
            )

        args = message.text.split()
        if len(args) != 2:
            return await message.reply_text("❌ Usage: `/uimage <character_id>`")

        try:
            char_id = int(args[1])
            character = await db.get_character_by_id(char_id)

            if not character:
                return await message.reply_text("❌ Character not found.")

            status = await message.reply_text("🔄 Uploading media...")

            async def update(text):
                try:
                    await status.edit_text(text)
                except:
                    pass

            media_url, media_type = await helpers.upload_media_with_fallback(
                client,
                message.reply_to_message,
                status_callback=update
            )

            if not media_url:
                return await update("❌ Media upload failed.")

            updated = await db.update_character_media(char_id, media_url, media_type)

            if updated:
                await update("✅ Media updated successfully.")
                logger.info(f"Updated media for character {char_id}")
            else:
                await update("❌ Media update failed.")

        except ValueError:
            await message.reply_text("❌ Invalid character ID.")
        except Exception:
            logger.exception("uimage error")
            await message.reply_text("❌ Error updating media.")

    # ---------------- CHARACTER INFO ----------------
    async def uinfo_command(self, client: Client, message: Message):
        if not await owner_or_sudo(message):
            return await message.reply_text("❌ You are not authorized to use this command.")

        args = message.text.split()
        if len(args) != 2:
            return await message.reply_text("❌ Usage: `/uinfo <character_id>`")

        try:
            char_id = int(args[1])
            character = await db.get_character_by_id(char_id)

            if not character:
                return await message.reply_text("❌ Character not found.")

            info = (
                "🔍 **Character Info**\n\n"
                f"🆔 ID: `{character['character_id']}`\n"
                f"👤 Name: `{character['char_name']}`\n"
                f"🎞 Anime: `{character['anime_name']}`\n"
                f"⭐ Rarity: `{character['rarity']}`\n"
                f"💠 Sub: `{character.get('subrarity', 'None')}`\n"
                f"🔗 Media: `{character.get('media_url', 'None')}`"
            )

            if character.get("media_url"):
                sender = {
                    "photo": client.send_photo,
                    "video": client.send_video,
                    "audio": client.send_audio
                }.get(character.get("media_type"), client.send_document)

                await sender(message.chat.id, character["media_url"], caption=info)
            else:
                await message.reply_text(info)

        except ValueError:
            await message.reply_text("❌ Invalid character ID.")
        except Exception:
            logger.exception("uinfo error")
            await message.reply_text("❌ Error fetching character info.")


# ------------------------------------------------
# Register Handlers
# ------------------------------------------------
def register_character_management_handlers(client: Client):
    handlers = CharacterManagementHandlers(client)

    client.on_message(filters.command("delchar"))(handlers.delchar_command)
    client.on_message(filters.command("uchar"))(handlers.uchar_command)
    client.on_message(filters.command("uimage"))(handlers.uimage_command)
    client.on_message(filters.command("uinfo"))(handlers.uinfo_command)

    logger.info("Character management handlers registered")
