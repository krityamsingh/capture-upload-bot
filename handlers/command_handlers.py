# ==================== HANDLERS/COMMAND_HANDLERS.PY ====================
# handlers/command_handlers.py - UPDATED
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

from config import config
from database.mongodb import db
from database.models import UserSession
from states import CharacterStates
from utils import keyboards, helpers

logger = logging.getLogger(__name__)

class CommandHandlers:
    """Handle all bot commands"""
    
    def __init__(self, client: Client):
        self.client = client
    
    async def start_command(self, client: Client, message: Message):
        """Handle /start command"""
        welcome_text = (
            "👋 **Welcome to Character Upload Bot!**\n\n"
            "I can help you upload and manage character data with rarity systems. "
            "Use the buttons below to get started!\n\n"
            "**NEW Character Upload Flow:**\n"
            "1. Character Name\n"
            "2. Anime Name\n" 
            "3. Rarity Selection\n"
            "4. Sub-rarity (if applicable)\n"
            "5. Media Upload\n"
            "6. Confirmation\n\n"
            "**Supported Media Types:**\n"
            "• 📷 Photos (JPEG, PNG, GIF)\n" 
            "• 🎥 Videos (MP4, MKV, AVI)\n"
            "• 🎵 Audio files (MP3, WAV)\n"
            "• 📄 Documents (PDF, TXT, etc.)\n\n"
            "**Max File Size:** 50MB\n\n"
            "**Upload Service:** Catbox.moe (Fast - 5-8 seconds)\n\n"
            "**Auto Reply Mode:** The bot will automatically set reply mode for text inputs!"
        )
        
        await message.reply_text(
            welcome_text,
            reply_markup=keyboards.get_main_menu_keyboard()
        )
    
    async def addchar_command(self, client: Client, message: Message):
        """Handle /addchar command - NEW FLOW: starts with character name"""
        user_id = message.from_user.id
        
        # Check if user is sudo user
        if not await helpers.is_sudo_user(user_id):
            await message.reply_text("❌ You are not authorized to use this bot. Contact admin.")
            return
        
        # Check if user has active mass upload session
        mass_session = await db.get_mass_upload_session(user_id)
        if mass_session:
            await message.reply_text(
                "⚠️ **You have an active mass upload session!**\n\n"
                f"**Current Session:** {mass_session.char_name} ({mass_session.anime_name})\n\n"
                "Use `/donechar` to end mass session first, or use `/madd` for mass uploads."
            )
            return
        
        # Check for existing session
        existing_session = await db.get_session(user_id)
        if existing_session:
            await message.reply_text(
                "⚠️ **You already have an active upload session!**\n\n"
                "Use `/cs` to clear your current session first."
            )
            return
        
        # Create new session starting with character name
        session = UserSession(
            user_id=user_id,
            state=CharacterStates.WAITING_CHAR_NAME.value
        )
        await db.save_session(session)
        
        # Send character name request with forced reply
        await message.reply_text(
            "🚀 **Starting Character Upload Process**\n\n"
            "💬 **Step 1: What is the character's name?**\n\n"
            "Please use the format: `Name [emoji]` if rarity has one\n"
            "Example: `Ichigo Kurosaki 🗡️`\n\n"
            "**Please send the character name:**",
            reply_markup=helpers.force_reply()
        )
    
    async def cs_command(self, client: Client, message: Message):
        """Handle /cs command - clear current session"""
        user_id = message.from_user.id
        
        # Check for active mass session
        mass_session = await db.get_mass_upload_session(user_id)
        if mass_session:
            await db.delete_mass_upload_session(user_id)
            await message.reply_text("✅ Mass upload session cleared!")
            return
        
        # Check for active single character session
        session = await db.get_session(user_id)
        if session:
            await db.delete_session(user_id)
            await message.reply_text("✅ Single character upload session cleared!")
            return
        
        await message.reply_text("ℹ️ No active session to clear.")
    
    async def check_command(self, client: Client, message: Message):
        """Handle /c command - check character by ID - FIXED: Media URL issues"""
        try:
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "🔍 **Character Check Command**\n\n"
                    "**Usage:**\n"
                    "`/c [character_id]`\n\n"
                    "**Example:**\n"
                    "`/c 1`"
                )
                return
            
            character_id = int(args[1])
            character = await db.get_character_by_id(character_id)
            
            if not character:
                await message.reply_text(
                    "⚠️ Character not found! Please check the ID and try again."
                )
                return
            
            # Format character info
            character_info = (
                "🔍 **Character Preview**\n\n"
                f"👤 **Name:** {character['char_name']}\n"
                f"🎞️ **Anime:** {character['anime_name']}\n"
                f"🏅 **Rarity:** {character['rarity']}\n"
                f"🆔 **Character ID:** {character['character_id']}\n"
                f"🧍 **Uploaded by:** {await helpers.get_username_from_id(client, character['added_by'])}"
            )
            
            # Send media if available and valid
            if character.get('media_url') and character.get('media_type'):
                try:
                    if character.get('media_type') == 'photo':
                        await client.send_photo(
                            chat_id=message.chat.id,
                            photo=character['media_url'],
                            caption=character_info
                        )
                    elif character.get('media_type') == 'video':
                        await client.send_video(
                            chat_id=message.chat.id,
                            video=character['media_url'],
                            caption=character_info
                        )
                    elif character.get('media_type') == 'audio':
                        await client.send_audio(
                            chat_id=message.chat.id,
                            audio=character['media_url'],
                            caption=character_info
                        )
                    else:
                        await client.send_document(
                            chat_id=message.chat.id,
                            document=character['media_url'],
                            caption=character_info
                        )
                except Exception as e:
                    logger.warning(f"Failed to send media for character {character_id}: {e}")
                    # Fallback to text only
                    character_info += f"\n\n📸 **Media URL:** {character['media_url']}"
                    await message.reply_text(character_info)
            else:
                await message.reply_text(character_info)
                
        except ValueError:
            await message.reply_text("❌ Invalid character ID. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in check command: {e}")
            await message.reply_text("❌ Error fetching character. Please try again.")
    
    async def status_command(self, client: Client, message: Message):
        """Handle /status command - show bot statistics"""
        try:
            total_chars = await db.get_character_count()
            user_chars = await db.get_user_characters(message.from_user.id)
            
            # Check for active mass session
            mass_session = await db.get_mass_upload_session(message.from_user.id)
            mass_session_info = ""
            if mass_session:
                mass_session_info = f"• **Active Mass Session:** {mass_session.char_name} ({mass_session.get_character_count()} chars)\n"
            
            # Check sudo status
            is_sudo = await helpers.is_sudo_user(message.from_user.id)
            
            status_text = (
                "📊 **Bot Status**\n\n"
                f"• **Total Characters:** {total_chars}\n"
                f"• **Your Characters:** {len(user_chars)}\n"
                f"{mass_session_info}"
                f"• **Bot Owner:** {('Yes' if helpers.is_owner(message.from_user.id) else 'No')}\n"
                f"• **Sudo User:** {('Yes' if is_sudo else 'No')}\n"
                f"• **Upload Service:** Catbox.moe (Fast)\n"
                f"• **Upload Flow:** Character → Anime → Rarity → Media → Confirm"
            )
            
            await message.reply_text(status_text)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await message.reply_text("❌ Error fetching status. Please try again.")
    
    async def help_command(self, client: Client, message: Message):
        """Handle /help command - show help information"""
        help_text = (
            "ℹ️ **Bot Help Guide**\n\n"
            "**NEW Character Upload Flow:**\n"
            "1. **Character Name** (Auto reply mode)\n"
            "2. **Anime Name** (Auto reply mode)\n"
            "3. **Rarity Selection** (Buttons)\n"
            "4. **Sub-rarity** (If applicable, Buttons)\n"
            "5. **Media Upload** (Send photo/video/audio/document)\n"
            "6. **Confirmation** (Buttons)\n\n"
            "**Commands:**\n"
            "• `/start` - Start the bot\n"
            "• `/addchar` - Add a single character (NEW FLOW)\n" 
            "• `/cs` - Clear current upload session\n"
            "• `/c [id]` - Check character by ID\n"
            "• `/status` - Check bot statistics\n"
            "• `/help` - Show this help message\n\n"
            "**Supported Media:** Photos, Videos, Audio, Documents (max 50MB)\n"
            "**Upload Service:** Catbox.moe (Fast - 5-8 seconds)\n"
            "**Auto Reply:** The bot automatically sets reply mode for text inputs\n"
            "**Authorization:** Only sudo users can upload characters"
        )
        
        await message.reply_text(help_text)
    
    async def setlog1_command(self, client: Client, message: Message):
        """Handle /setlog1 command - set first log channel (owner only)"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text("❌ Usage: /setlog1 <chat_id>")
                return
            
            chat_id = int(args[1])
            await db.update_log_chat("1", chat_id)
            
            await message.reply_text(f"✅ Log Channel 1 set to: `{chat_id}`")
            
        except ValueError:
            await message.reply_text("❌ Invalid chat ID. Please provide a valid integer.")
        except Exception as e:
            logger.error(f"Error setting log1: {e}")
            await message.reply_text("❌ Error setting log channel.")
    
    async def setlog2_command(self, client: Client, message: Message):
        """Handle /setlog2 command - set second log channel (owner only)"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text("❌ Usage: /setlog2 <chat_id>")
                return
            
            chat_id = int(args[1])
            await db.update_log_chat("2", chat_id)
            
            await message.reply_text(f"✅ Log Channel 2 set to: `{chat_id}`")
            
        except ValueError:
            await message.reply_text("❌ Invalid chat ID. Please provide a valid integer.")
        except Exception as e:
            logger.error(f"Error setting log2: {e}")
            await message.reply_text("❌ Error setting log channel.")
    
    async def showlogs_command(self, client: Client, message: Message):
        """Handle /showlogs command - show current log channels (owner only)"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            log_config = await db.get_log_config()
            
            log_text = "📋 **Current Log Channels**\n\n"
            log_text += f"• **Log Channel 1:** `{log_config.get('log_chat_1', 'Not set')}`\n"
            log_text += f"• **Log Channel 2:** `{log_config.get('log_chat_2', 'Not set')}`"
            
            await message.reply_text(log_text)
            
        except Exception as e:
            logger.error(f"Error showing logs: {e}")
            await message.reply_text("❌ Error fetching log configuration.")

def register_command_handlers(client: Client):
    """Register all command handlers"""
    handlers = CommandHandlers(client)
    
    client.on_message(filters.command("start"))(handlers.start_command)
    client.on_message(filters.command("addchar"))(handlers.addchar_command)
    client.on_message(filters.command("cs"))(handlers.cs_command)
    client.on_message(filters.command(["c", "check"]))(handlers.check_command)
    client.on_message(filters.command("status"))(handlers.status_command)
    client.on_message(filters.command("help"))(handlers.help_command)
    client.on_message(filters.command("setlog1"))(handlers.setlog1_command)
    client.on_message(filters.command("setlog2"))(handlers.setlog2_command)
    client.on_message(filters.command("showlogs"))(handlers.showlogs_command)
    
    logger.info("Command handlers registered successfully")