# ==================== HANDLERS/CHARACTER_MANAGEMENT_HANDLERS.PY ====================
# handlers/character_management_handlers.py - UPDATED
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

from config import config
from database.mongodb import db
from utils import helpers

logger = logging.getLogger(__name__)

class CharacterManagementHandlers:
    """Handlers for character management commands"""
    
    def __init__(self, client: Client):
        self.client = client
    
    async def delchar_command(self, client: Client, message: Message):
        """Handle /delchar command - delete character by ID"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "🗑️ **Delete Character Command**\n\n"
                    "**Usage:**\n"
                    "`/delchar [character_id]`\n\n"
                    "**Example:**\n"
                    "`/delchar 1`"
                )
                return
            
            character_id = int(args[1])
            character = await db.get_character_by_id(character_id)
            
            if not character:
                await message.reply_text("❌ Character not found!")
                return
            
            # Delete character from database
            deleted = await db.delete_character(character_id)
            
            if deleted:
                await message.reply_text("✅ Character deleted successfully!")
                logger.info(f"Character {character_id} deleted by user {message.from_user.id}")
            else:
                await message.reply_text("❌ Failed to delete character!")
                
        except ValueError:
            await message.reply_text("❌ Invalid character ID. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in delchar command: {e}")
            await message.reply_text("❌ Error deleting character. Please try again.")
    
    async def uchar_command(self, client: Client, message: Message):
        """Handle /uchar command - update character details"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            args = message.text.split()
            if len(args) < 5:
                await message.reply_text(
                    "✏️ **Update Character Command**\n\n"
                    "**Usage:**\n"
                    "`/uchar [char_id] [name] [anime] [rarity_no] [optional_subrarity]`\n\n"
                    "**Example:**\n"
                    "`/uchar 1 Zoro OnePiece 4`\n"
                    "`/uchar 1 Zoro OnePiece 5 1`\n\n"
                    "**Rarity Numbers:**\n"
                    "1: Common, 2: Rare, 3: Legendary, 4: Exclusive\n"
                    "5: Limited Edition, 6: Celestial, 7: Eternal\n"
                    "8: Cinematic, 9: Diwali"
                )
                return
            
            character_id = int(args[1])
            char_name = args[2]
            anime_name = args[3]
            rarity_no = int(args[4])
            subrarity = args[5] if len(args) > 5 else None
            
            # Validate rarity number
            if rarity_no not in config.RARITY_MAP:
                await message.reply_text("❌ Invalid rarity number!")
                return
            
            # Check if character exists
            character = await db.get_character_by_id(character_id)
            if not character:
                await message.reply_text("❌ Character not found!")
                return
            
            # Get rarity name
            rarity_name = config.RARITY_MAP[rarity_no]
            
            # Handle subrarity for Limited Edition and Celestial
            if rarity_no in config.RARITIES_WITH_SUBTYPES and subrarity:
                if rarity_no == 5:  # Limited Edition
                    if subrarity not in config.LIMITED_SUBTYPES:
                        await message.reply_text("❌ Invalid Limited Edition subtype!")
                        return
                    subrarity_name = config.LIMITED_SUBTYPES[subrarity]
                elif rarity_no == 6:  # Celestial
                    if subrarity not in config.CELESTIAL_SUBTYPES:
                        await message.reply_text("❌ Invalid Celestial subtype!")
                        return
                    subrarity_name = config.CELESTIAL_SUBTYPES[subrarity]
            else:
                subrarity_name = None
            
            # Update character
            updated = await db.update_character(
                character_id=character_id,
                char_name=char_name,
                anime_name=anime_name,
                rarity=rarity_name,
                subrarity=subrarity_name
            )
            
            if updated:
                await message.reply_text("✅ Character updated successfully!")
                logger.info(f"Character {character_id} updated by user {message.from_user.id}")
            else:
                await message.reply_text("❌ Failed to update character!")
                
        except ValueError as e:
            await message.reply_text("❌ Invalid input. Please check the command format.")
        except Exception as e:
            logger.error(f"Error in uchar command: {e}")
            await message.reply_text("❌ Error updating character. Please try again.")
    
    async def uimage_command(self, client: Client, message: Message):
        """Handle /uimage command - update character media"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            # Check if message is a reply to media
            if not message.reply_to_message or not (
                message.reply_to_message.photo or 
                message.reply_to_message.video or 
                message.reply_to_message.audio or 
                message.reply_to_message.document
            ):
                await message.reply_text(
                    "❌ **Please reply to a media file with this command!**\n\n"
                    "**Usage:**\n"
                    "1. Send a photo/video/audio/document\n"
                    "2. Reply to it with: `/uimage [character_id]`\n\n"
                    "**Example:**\n"
                    "Send a photo, then reply: `/uimage 1`"
                )
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text("❌ Usage: Reply to media with `/uimage [character_id]`")
                return
            
            character_id = int(args[1])
            
            # Check if character exists
            character = await db.get_character_by_id(character_id)
            if not character:
                await message.reply_text("❌ Character not found!")
                return
            
            # Upload media to Catbox
            status_msg = await message.reply_text("🔄 Starting media upload...")
            
            async def update_status(text: str):
                try:
                    await status_msg.edit_text(text)
                except Exception as e:
                    logger.warning(f"Failed to update status: {e}")
            
            media_url, media_type = await helpers.upload_media_with_fallback(
                client, 
                message.reply_to_message,
                status_callback=update_status
            )
            
            if not media_url:
                await update_status("❌ Failed to upload media to Catbox!")
                return
            
            # Update character media
            updated = await db.update_character_media(character_id, media_url, media_type)
            
            if updated:
                await update_status("✅ Character media updated successfully!")
                logger.info(f"Character {character_id} media updated by user {message.from_user.id}")
            else:
                await update_status("❌ Failed to update character media!")
                
        except ValueError:
            await message.reply_text("❌ Invalid character ID. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in uimage command: {e}")
            await message.reply_text("❌ Error updating character media. Please try again.")
    
    async def uinfo_command(self, client: Client, message: Message):
        """Handle /uinfo command - show detailed character info"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "🔍 **Character Info Command**\n\n"
                    "**Usage:**\n"
                    "`/uinfo [character_id]`\n\n"
                    "**Example:**\n"
                    "`/uinfo 1`"
                )
                return
            
            character_id = int(args[1])
            character = await db.get_character_by_id(character_id)
            
            if not character:
                await message.reply_text("❌ Character not found!")
                return
            
            # Format detailed character info
            char_info = (
                "🔍 **Character Detailed Info**\n\n"
                f"🆔 **Character ID:** `{character['character_id']}`\n"
                f"👤 **Name:** `{character['char_name']}`\n"
                f"🎞️ **Anime:** `{character['anime_name']}`\n"
                f"🏅 **Rarity:** `{character['rarity']}`\n"
                f"💠 **Sub-Rarity:** `{character.get('subrarity', 'None')}`\n"
                f"📸 **Media Type:** `{character.get('media_type', 'None')}`\n"
                f"🔗 **Media URL:** `{character.get('media_url', 'None')}`\n"
                f"🧍 **Added by:** `{character['added_by']}`\n"
                f"🕐 **Timestamp:** `{character.get('timestamp', 'Unknown')}`\n\n"
                "**Use this info to verify before updating with /uchar**"
            )
            
            # Send media if available
            if character.get('media_url'):
                if character.get('media_type') == 'photo':
                    await client.send_photo(
                        chat_id=message.chat.id,
                        photo=character['media_url'],
                        caption=char_info
                    )
                elif character.get('media_type') == 'video':
                    await client.send_video(
                        chat_id=message.chat.id,
                        video=character['media_url'],
                        caption=char_info
                    )
                elif character.get('media_type') == 'audio':
                    await client.send_audio(
                        chat_id=message.chat.id,
                        audio=character['media_url'],
                        caption=char_info
                    )
                else:
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=character['media_url'],
                        caption=char_info
                    )
            else:
                await message.reply_text(char_info)
                
        except ValueError:
            await message.reply_text("❌ Invalid character ID. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in uinfo command: {e}")
            await message.reply_text("❌ Error fetching character info. Please try again.")

def register_character_management_handlers(client: Client):
    """Register character management command handlers"""
    handlers = CharacterManagementHandlers(client)
    
    # REMOVED: filters.private to make commands available in groups
    client.on_message(filters.command("delchar"))(handlers.delchar_command)
    client.on_message(filters.command("uchar"))(handlers.uchar_command)
    client.on_message(filters.command("uimage"))(handlers.uimage_command)
    client.on_message(filters.command("uinfo"))(handlers.uinfo_command)
    
    logger.info("Character management handlers registered successfully")