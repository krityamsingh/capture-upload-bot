# ==================== HANDLERS/MASS_UPLOAD_HANDLERS.PY ====================
# handlers/mass_upload_handlers.py - UPDATED
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from config import config
from database.mongodb import db
from database.models import MassUploadSession, Character
from utils import helpers, keyboards

logger = logging.getLogger(__name__)

class MassUploadHandlers:
    """Handlers for mass character upload functionality"""
    
    def __init__(self, client: Client):
        self.client = client
    
    async def setchar_command(self, client: Client, message: Message):
        """Handle /setchar command - start mass upload session"""
        # Check if user is sudo user
        if not await helpers.is_sudo_user(message.from_user.id):
            await message.reply_text("❌ You are not authorized to use this bot. Contact admin.")
            return
            
        try:
            args = message.text.split()
            if len(args) < 3:
                await message.reply_text(
                    "🚀 **Mass Upload Session Setup**\n\n"
                    "**Usage:**\n"
                    "`/setchar <character_name> <anime_name>`\n\n"
                    "**Example:**\n"
                    "`/setchar Ichigo_Kurosaki Bleach`\n"
                    "`/setchar \"Goku Ultra Instinct\" \"Dragon Ball Super\"`\n\n"
                    "**Note:** Use underscores for spaces or quotes for multi-word names"
                )
                return
            
            # Parse character and anime names (support quotes for multi-word)
            char_name = args[1].replace('_', ' ').replace('"', '')
            anime_name = ' '.join(args[2:]).replace('_', ' ').replace('"', '')
            
            # Check for existing sessions
            existing_session = await db.get_mass_upload_session(message.from_user.id)
            if existing_session:
                await message.reply_text(
                    "⚠️ **You already have an active mass upload session!**\n\n"
                    f"**Current Session:** {existing_session.char_name} ({existing_session.anime_name})\n\n"
                    "Use `/donechar` to end current session or `/currentchar` to view status."
                )
                return
            
            # Create new mass upload session
            session = MassUploadSession(
                user_id=message.from_user.id,
                char_name=char_name,
                anime_name=anime_name
            )
            
            await db.save_mass_upload_session(session)
            
            await message.reply_text(
                f"✅ **Mass Upload Session Started!**\n\n"
                f"👤 **Character:** {char_name}\n"
                f"🎞️ **Anime:** {anime_name}\n\n"
                "**Now you can upload media with rarities:**\n"
                "• Reply to a photo/video with `/madd <rarity> [subrarity]`\n"
                "• Example: `/madd 4` (Normal rarity)\n"
                "• Example: `/madd 5 hall` (Halloween subrarity)\n\n"
                "**Available Commands:**\n"
                "• `/currentchar` - Show session status\n"
                "• `/undochar` - Remove last upload\n" 
                "• `/bulkstatus` - Show upload statistics\n"
                "• `/donechar` - End session\n\n"
                "**Auto Emoji System:** Subrarities automatically add emojis to character names!\n"
                "**Fast Upload:** Catbox uploads now take 5-8 seconds!"
            )
            
        except Exception as e:
            logger.error(f"Error in setchar command: {e}")
            await message.reply_text("❌ Error starting mass upload session. Please try again.")
    
    async def madd_command(self, client: Client, message: Message):
        """Handle /madd command in mass upload context"""
        # Check if user is sudo user
        if not await helpers.is_sudo_user(message.from_user.id):
            await message.reply_text("❌ You are not authorized to use this bot. Contact admin.")
            return
            
        try:
            # Check if user has active mass upload session
            session = await db.get_mass_upload_session(message.from_user.id)
            if not session:
                await message.reply_text(
                    "❌ **No active mass upload session!**\n\n"
                    "Start a session first with `/setchar <name> <anime>`"
                )
                return
            
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
                    "2. Reply to it with: `/madd <rarity> [subrarity]`\n\n"
                    "**Examples:**\n"
                    "• `/madd 4` - Normal rarity\n"
                    "• `/madd 5 hall` - Halloween Limited Edition\n"
                    "• `/madd 6 dragonic` - Dragonic Celestial"
                )
                return
            
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "❌ **Invalid syntax!**\n\n"
                    "**Usage:** `/madd <rarity> [subrarity]`\n"
                    "**Example:** `/madd 5 hall`"
                )
                return
            
            # Parse rarity and subrarity
            try:
                rarity_num = int(args[1])
                if rarity_num not in config.RARITY_MAP:
                    await message.reply_text(f"❌ Invalid rarity number! Available: 1-{len(config.RARITY_MAP)}")
                    return
                
                rarity_name = config.RARITY_MAP[rarity_num]
                subrarity_key = args[2].lower() if len(args) > 2 else None
                subrarity_name = None
                emoji = None
                
                # Process subrarity and auto-emoji
                if subrarity_key:
                    if rarity_num == 5:  # Limited Edition
                        if subrarity_key in config.LIMITED_SUBTYPES:
                            subrarity_name = config.LIMITED_SUBTYPES[subrarity_key]
                            emoji = config.SUBRARITY_EMOJI_MAP.get(subrarity_key)
                        else:
                            await message.reply_text(
                                f"❌ Invalid Limited Edition subtype! Available: {', '.join(config.LIMITED_SUBTYPES.keys())}"
                            )
                            return
                    elif rarity_num == 6:  # Celestial
                        if subrarity_key in config.CELESTIAL_SUBTYPES:
                            subrarity_name = config.CELESTIAL_SUBTYPES[subrarity_key]
                            emoji = config.SUBRARITY_EMOJI_MAP.get(subrarity_key)
                        else:
                            await message.reply_text(
                                f"❌ Invalid Celestial subtype! Available: {', '.join(config.CELESTIAL_SUBTYPES.keys())}"
                            )
                            return
                    else:
                        await message.reply_text("❌ Subrarity only available for Limited Edition (5) and Celestial (6)")
                        return
                
                # Build final character name with emoji
                final_char_name = session.char_name
                if emoji:
                    final_char_name = f"{session.char_name} [{emoji}]"
                
            except ValueError:
                await message.reply_text("❌ Rarity must be a number!")
                return
            
            # Upload media
            status_msg = await message.reply_text("🔄 Starting fast media upload...")
            
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
            
            # Get next character ID and create character
            character_id = await db.get_next_character_id()
            character = Character(
                char_name=final_char_name,
                anime_name=session.anime_name,
                rarity=rarity_name,
                character_id=character_id,
                media_url=media_url,
                media_type=media_type,
                subrarity=subrarity_name,
                added_by=message.from_user.id
            )
            
            # Insert character into database
            try:
                inserted_id = await db.insert_character(character)
                
                # Add to session tracking
                session.add_character({
                    "character_id": character_id,
                    "rarity": rarity_name,
                    "subrarity": subrarity_name,
                    "media_url": media_url,
                    "media_type": media_type,
                    "timestamp": character.timestamp
                })
                await db.save_mass_upload_session(session)
                
                # Send to log channels
                username = message.from_user.username or message.from_user.first_name or "Unknown"
                await helpers.send_to_log_channels(
                    client, character.to_dict(), username, message.from_user.id, db
                )
                
                # Success message
                success_text = (
                    f"✅ **Character #{character_id} Added!**\n\n"
                    f"👤 **Name:** {final_char_name}\n"
                    f"🎞️ **Anime:** {session.anime_name}\n"
                    f"🏅 **Rarity:** {rarity_name}\n"
                )
                
                if subrarity_name:
                    success_text += f"💠 **Sub-Rarity:** {subrarity_name}\n"
                
                success_text += (
                    f"📸 **Media:** Uploaded successfully\n\n"
                    f"**Session Progress:** {session.get_character_count()} characters uploaded\n"
                    f"**Next ID:** {character_id + 1}"
                )
                
                await update_status(success_text)
                
            except Exception as e:
                logger.error(f"Error saving character in mass upload: {e}")
                await update_status("❌ Error saving character to database!")
                
        except Exception as e:
            logger.error(f"Error in mass upload madd: {e}")
            await message.reply_text("❌ Error processing character upload. Please try again.")
    
    async def donechar_command(self, client: Client, message: Message):
        """Handle /donechar command - end mass upload session"""
        try:
            session = await db.get_mass_upload_session(message.from_user.id)
            if not session:
                await message.reply_text("❌ No active mass upload session found!")
                return
            
            total_chars = session.get_character_count()
            
            # Delete session
            await db.delete_mass_upload_session(message.from_user.id)
            
            summary_text = (
                f"🎉 **Mass Upload Session Complete!**\n\n"
                f"👤 **Character:** {session.char_name}\n"
                f"🎞️ **Anime:** {session.anime_name}\n"
                f"📊 **Total Uploaded:** {total_chars} characters\n"
                f"⏱️ **Session Duration:** {helpers.format_session_duration(session.created_at)}\n\n"
                "All characters have been saved to the database and are now available."
            )
            
            await message.reply_text(summary_text)
            
        except Exception as e:
            logger.error(f"Error in donechar command: {e}")
            await message.reply_text("❌ Error ending mass upload session.")
    
    async def currentchar_command(self, client: Client, message: Message):
        """Handle /currentchar command - show current session status"""
        try:
            session = await db.get_mass_upload_session(message.from_user.id)
            if not session:
                await message.reply_text(
                    "❌ **No active mass upload session!**\n\n"
                    "Start a session with `/setchar <name> <anime>`"
                )
                return
            
            # Build detailed session info
            session_info = session.get_session_summary()
            
            # Add uploaded characters list
            if session.uploaded_characters:
                session_info += "\n\n**📋 Uploaded Characters:**\n"
                for i, char in enumerate(session.uploaded_characters[-10:], 1):  # Show last 10
                    char_text = f"`{char['character_id']}` - {char['rarity']}"
                    if char.get('subrarity'):
                        char_text += f" ({char['subrarity']})"
                    session_info += f"{i}. {char_text}\n"
                
                if len(session.uploaded_characters) > 10:
                    session_info += f"\n... and {len(session.uploaded_characters) - 10} more"
            
            await message.reply_text(session_info)
            
        except Exception as e:
            logger.error(f"Error in currentchar command: {e}")
            await message.reply_text("❌ Error fetching session information.")
    
    async def undochar_command(self, client: Client, message: Message):
        """Handle /undochar command - remove last uploaded character"""
        try:
            session = await db.get_mass_upload_session(message.from_user.id)
            if not session:
                await message.reply_text("❌ No active mass upload session!")
                return
            
            if not session.uploaded_characters:
                await message.reply_text("❌ No characters to undo!")
                return
            
            # Get last character data
            last_char = session.remove_last_character()
            if not last_char:
                await message.reply_text("❌ No characters to undo!")
                return
            
            # Delete character from database
            deleted = await db.delete_character(last_char['character_id'])
            
            if deleted:
                await db.save_mass_upload_session(session)
                await message.reply_text(
                    f"✅ **Last character undone!**\n\n"
                    f"🗑️ **Removed:** Character `{last_char['character_id']}`\n"
                    f"🏅 **Rarity:** {last_char['rarity']}\n"
                    f"📊 **Remaining:** {session.get_character_count()} characters in session"
                )
            else:
                await message.reply_text("❌ Failed to delete character from database!")
                
        except Exception as e:
            logger.error(f"Error in undochar command: {e}")
            await message.reply_text("❌ Error undoing last character.")
    
    async def bulkstatus_command(self, client: Client, message: Message):
        """Handle /bulkstatus command - show bulk upload statistics"""
        try:
            session = await db.get_mass_upload_session(message.from_user.id)
            if not session:
                await message.reply_text("❌ No active mass upload session!")
                return
            
            # Calculate statistics
            total_chars = session.get_character_count()
            rarity_count = {}
            
            for char in session.uploaded_characters:
                rarity = char['rarity']
                rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
            
            # Build status message
            status_text = (
                f"📊 **Mass Upload Statistics**\n\n"
                f"👤 **Character:** {session.char_name}\n"
                f"🎞️ **Anime:** {session.anime_name}\n"
                f"📈 **Total Uploaded:** {total_chars} characters\n"
                f"⏱️ **Session Active:** {helpers.format_session_duration(session.created_at)}\n\n"
            )
            
            if rarity_count:
                status_text += "**📋 Rarity Breakdown:**\n"
                for rarity, count in rarity_count.items():
                    status_text += f"• {rarity}: {count}\n"
            
            await message.reply_text(status_text)
            
        except Exception as e:
            logger.error(f"Error in bulkstatus command: {e}")
            await message.reply_text("❌ Error fetching bulk upload statistics.")

def register_mass_upload_handlers(client: Client):
    """Register mass upload command handlers"""
    handlers = MassUploadHandlers(client)
    
    client.on_message(filters.command("setchar"))(handlers.setchar_command)
    client.on_message(filters.command("madd"))(handlers.madd_command)
    client.on_message(filters.command("donechar"))(handlers.donechar_command)
    client.on_message(filters.command("currentchar"))(handlers.currentchar_command)
    client.on_message(filters.command("undochar"))(handlers.undochar_command)
    client.on_message(filters.command("bulkstatus"))(handlers.bulkstatus_command)
    
    logger.info("Mass upload handlers registered successfully")