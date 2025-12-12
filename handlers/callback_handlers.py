# ==================== HANDLERS/CALLBACK_HANDLERS.PY ====================
# handlers/callback_handlers.py - UPDATED
import logging
from pyrogram import Client
from pyrogram.types import CallbackQuery
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import config
from database.mongodb import db
from database.models import UserSession, Character
from states import CharacterStates
from utils import keyboards, helpers

logger = logging.getLogger(__name__)

class CallbackHandlers:
    """Handle all callback queries from inline keyboards"""
    
    def __init__(self, client: Client):
        self.client = client
    
    async def handle_main_menu(self, client: Client, callback_query: CallbackQuery):
        """Handle main menu callback queries"""
        data = callback_query.data
        
        if data == "add_char":
            await self.start_character_upload(callback_query)
        elif data == "status":
            await self.show_status(callback_query)
        elif data == "help":
            await self.show_help(callback_query)
    
    async def start_character_upload(self, callback_query: CallbackQuery):
        """Start character upload from main menu"""
        user_id = callback_query.from_user.id
        
        # Check if user is sudo user
        if not await helpers.is_sudo_user(user_id):
            await callback_query.answer("❌ You are not authorized to use this bot. Contact admin.", show_alert=True)
            return
        
        await callback_query.message.edit_text(
            "📸 **To add a character, please use the /addchar command.**\n\n"
            "**NEW Upload Flow:**\n"
            "1. Character Name (Reply)\n"
            "2. Anime Name (Reply)\n"
            "3. Rarity Selection (Buttons)\n" 
            "4. Sub-rarity (if applicable, Buttons)\n"
            "5. Media Upload (Send file)\n"
            "6. Confirmation (Buttons)\n\n"
            "Use `/addchar` to start the process."
        )
    
    async def show_status(self, callback_query: CallbackQuery):
        """Show status from main menu"""
        try:
            total_chars = await db.get_character_count()
            user_chars = await db.get_user_characters(callback_query.from_user.id)
            
            status_text = (
                "📊 **Bot Status**\n\n"
                f"• **Total Characters:** {total_chars}\n"
                f"• **Your Characters:** {len(user_chars)}"
            )
            
            await callback_query.message.edit_text(
                status_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error in status callback: {e}")
            await callback_query.answer("Error fetching status", show_alert=True)
    
    async def show_help(self, callback_query: CallbackQuery):
        """Show help from main menu"""
        help_text = (
            "ℹ️ **Bot Help Guide**\n\n"
            "**NEW Character Upload Flow:**\n"
            "1. **Character Name** (Reply to bot's message)\n"
            "2. **Anime Name** (Reply to bot's message)\n"
            "3. **Rarity Selection** (Buttons)\n"
            "4. **Sub-rarity** (If applicable, Buttons)\n"
            "5. **Media Upload** (Send photo/video/audio/document)\n"
            "6. **Confirmation** (Buttons)\n\n"
            "Use `/addchar` to start uploading characters."
        )
        
        await callback_query.message.edit_text(
            help_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ])
        )
    
    async def handle_rarity_selection(self, client: Client, callback_query: CallbackQuery):
        """Handle rarity selection callback"""
        user_id = callback_query.from_user.id
        session = await db.get_session(user_id)
        
        if not session:
            await callback_query.answer("Session expired. Please start again with /addchar", show_alert=True)
            return
        
        rarity_id = int(callback_query.data.split("_")[1])
        rarity_name = config.RARITY_MAP[rarity_id]
        
        # Update session
        session.rarity = rarity_name
        
        # Check if rarity has subtypes
        if rarity_id in config.RARITIES_WITH_SUBTYPES:
            session.state = CharacterStates.WAITING_SUBRARITY.value
            if rarity_id == 5:  # Limited Edition
                keyboard = keyboards.get_limited_subtypes_keyboard()
                await callback_query.message.edit_text(
                    f"✅ **Rarity Selected: {rarity_name}**\n\n"
                    f"🎯 **Step 4: Select Limited Edition Subtype**",
                    reply_markup=keyboard
                )
            elif rarity_id == 6:  # Celestial
                keyboard = keyboards.get_celestial_subtypes_keyboard()
                await callback_query.message.edit_text(
                    f"✅ **Rarity Selected: {rarity_name}**\n\n"
                    f"🎯 **Step 4: Select Celestial Subtype**",
                    reply_markup=keyboard
                )
        else:
            # No subtypes, proceed to media upload
            session.state = CharacterStates.WAITING_MEDIA.value
            await callback_query.message.edit_text(
                f"✅ **Rarity Selected: {rarity_name}**\n\n"
                "📸 **Step 5: Now please send the character media file**\n\n"
                "**Supported formats:**\n"
                "• 📷 Photos (JPEG, PNG, GIF)\n"
                "• 🎥 Videos (MP4, MKV, AVI)\n"
                "• 🎵 Audio files (MP3, WAV)\n" 
                "• 📄 Documents (PDF, TXT, etc.)\n\n"
                "**Max File Size:** 50MB\n\n"
                "**Upload Service:** Catbox.moe (Fast - 5-8 seconds)"
            )
        
        await db.save_session(session)
        await callback_query.answer()
    
    async def handle_subrarity_selection(self, client: Client, callback_query: CallbackQuery):
        """Handle sub-rarity selection callback"""
        user_id = callback_query.from_user.id
        session = await db.get_session(user_id)
        
        if not session:
            await callback_query.answer("Session expired. Please start again with /addchar", show_alert=True)
            return
        
        # Parse callback data
        parts = callback_query.data.split("_")
        rarity_type = parts[1]  # limited or celestial
        subtype_key = parts[2]
        
        # Get subrarity name
        if rarity_type == "limited":
            subrarity_name = config.LIMITED_SUBTYPES[subtype_key]
        else:  # celestial
            subrarity_name = config.CELESTIAL_SUBTYPES[subtype_key]
        
        # Update session
        session.subrarity = subrarity_name
        session.state = CharacterStates.WAITING_MEDIA.value
        await db.save_session(session)
        
        # Ask for media upload
        await callback_query.message.edit_text(
            f"✅ **Rarity Selected: {session.rarity}**\n"
            f"✅ **Sub-rarity Selected: {subrarity_name}**\n\n"
            "📸 **Step 5: Now please send the character media file**\n\n"
            "**Supported formats:**\n"
            "• 📷 Photos (JPEG, PNG, GIF)\n"
            "• 🎥 Videos (MP4, MKV, AVI)\n"
            "• 🎵 Audio files (MP3, WAV)\n" 
            "• 📄 Documents (PDF, TXT, etc.)\n\n"
            "**Max File Size:** 50MB\n\n"
            "**Upload Service:** Catbox.moe (Fast - 5-8 seconds)"
        )
        await callback_query.answer()
    
    async def handle_confirmation(self, client: Client, callback_query: CallbackQuery):
        """Handle confirmation callback"""
        user_id = callback_query.from_user.id
        session = await db.get_session(user_id)
        
        if not session:
            await callback_query.answer("Session expired. Please start again with /addchar", show_alert=True)
            return
        
        if callback_query.data == "confirm_upload":
            # Get next character ID
            character_id = await db.get_next_character_id()
            
            # Save character to database
            character = Character(
                char_name=session.char_name,
                anime_name=session.anime_name,
                rarity=session.rarity,
                character_id=character_id,
                media_url=session.media_url,
                media_type=session.media_type,
                subrarity=session.subrarity,
                added_by=user_id
            )
            
            try:
                inserted_id = await db.insert_character(character)
                
                # Send to log channels
                username = callback_query.from_user.username or callback_query.from_user.first_name or "Unknown"
                await helpers.send_to_log_channels(
                    client, character.to_dict(), username, user_id, db
                )
                
                # Success message
                success_text = (
                    "🎉 **Character successfully added to the database!**\n\n"
                    f"👤 **Name:** {session.char_name}\n"
                    f"🎞️ **Anime:** {session.anime_name}\n"
                    f"🏅 **Rarity:** {session.rarity}" +
                    (f"\n💠 **Sub-Rarity:** {session.subrarity}" if session.subrarity else "") +
                    f"\n\n🆔 **Character ID:** `{character_id}`\n"
                    f"📸 **Media:** Uploaded to Catbox\n\n"
                    f"**Note:** Character IDs increase automatically — next one will be {character_id + 1}"
                )
                
                await callback_query.message.edit_text(success_text)
                
                # Clean up session
                await db.delete_session(user_id)
                
            except Exception as e:
                logger.error(f"Error saving character: {e}")
                await callback_query.message.edit_text(
                    "❌ **Error saving character to database.**\n\n"
                    "Please try again or contact admin."
                )
        
        elif callback_query.data == "reject_upload":
            await callback_query.message.edit_text("❌ **Upload cancelled.**")
            await db.delete_session(user_id)
        
        await callback_query.answer()
    
    async def handle_back_navigation(self, client: Client, callback_query: CallbackQuery):
        """Handle back button navigation"""
        user_id = callback_query.from_user.id
        session = await db.get_session(user_id)
        
        back_to = callback_query.data.split("_")[1]
        
        if back_to == "main":
            await callback_query.message.edit_text(
                "👋 **Welcome to Character Upload Bot!**\n\n"
                "I can help you upload and manage character data with rarity systems. "
                "Use the buttons below to get started!",
                reply_markup=keyboards.get_main_menu_keyboard()
            )
        
        elif back_to == "start" and session:
            # Back to character name
            session.state = CharacterStates.WAITING_CHAR_NAME.value
            await db.save_session(session)
            
            # Send new character name request
            await callback_query.message.reply_text(
                "💬 **Please reply to this message with the character name:**\n\n"
                "Please use the format: `Name [emoji]` if rarity has one\n"
                "Example: `Ichigo Kurosaki 🗡️`",
                reply_markup=helpers.force_reply()
            )
        
        elif back_to == "rarity" and session:
            # Back to rarity selection
            session.state = CharacterStates.WAITING_RARITY.value
            await db.save_session(session)
            await callback_query.message.edit_text(
                "🎯 **Select the character's rarity:**",
                reply_markup=keyboards.get_rarity_keyboard()
            )
        
        elif back_to == "subrarity" and session:
            # Back to subrarity selection
            session.state = CharacterStates.WAITING_SUBRARITY.value
            await db.save_session(session)
            
            # Determine which subrarity keyboard to show
            if "Limited Edition" in session.rarity:
                keyboard = keyboards.get_limited_subtypes_keyboard()
                await callback_query.message.edit_text(
                    f"🎯 **Select Limited Edition Subtype**\n\n"
                    f"Rarity: {session.rarity}",
                    reply_markup=keyboard
                )
            elif "Celestial" in session.rarity:
                keyboard = keyboards.get_celestial_subtypes_keyboard()
                await callback_query.message.edit_text(
                    f"🎯 **Select Celestial Subtype**\n\n"
                    f"Rarity: {session.rarity}",
                    reply_markup=keyboard
                )
        
        await callback_query.answer()

def register_callback_handlers(client: Client):
    """Register all callback query handlers"""
    handlers = CallbackHandlers(client)
    
    # Callback query filters
    @client.on_callback_query()
    async def handle_all_callbacks(client: Client, callback_query: CallbackQuery):
        data = callback_query.data
        
        try:
            if data in ["add_char", "status", "help"]:
                await handlers.handle_main_menu(client, callback_query)
            elif data.startswith("rarity_"):
                await handlers.handle_rarity_selection(client, callback_query)
            elif data.startswith("subrarity_"):
                await handlers.handle_subrarity_selection(client, callback_query)
            elif data in ["confirm_upload", "reject_upload"]:
                await handlers.handle_confirmation(client, callback_query)
            elif data.startswith("back_"):
                await handlers.handle_back_navigation(client, callback_query)
                
        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}")
            await callback_query.answer("An error occurred. Please try again.", show_alert=True)
    
    logger.info("Callback handlers registered successfully")