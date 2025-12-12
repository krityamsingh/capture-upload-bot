# ==================== MAIN.PY ====================
# main.py - UPDATED
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UploadBot:
    """Main bot class that orchestrates all components"""
    
    def __init__(self):
        self.client = Client(
            "upload_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all message and callback handlers"""
        register_command_handlers(self.client)
        register_callback_handlers(self.client)
        register_character_management_handlers(self.client)
        register_mass_upload_handlers(self.client)
        register_sudo_handlers(self.client)
        
        # Register message handlers for character upload flow (private only)
        self.client.on_message(filters.private & (filters.text | filters.media | filters.document | filters.audio))(self._handle_message)
    
    async def _handle_message(self, client: Client, message: Message):
        """Handle non-command messages for character upload flow - FIXED: Proper state detection"""
        # Skip if it's a command
        if message.text and message.text.startswith('/'):
            return
        
        user_id = message.from_user.id
        
        # Check if user is sudo user
        if not await helpers.is_sudo_user(user_id):
            await message.reply_text("❌ You are not authorized to use this bot. Contact admin.")
            return
        
        # Check if user has active mass upload session (skip single character flow if true)
        mass_session = await db.get_mass_upload_session(user_id)
        if mass_session:
            return  # Mass upload session active, ignore non-command messages
            
        session = await db.get_session(user_id)
        
        if not session:
            # No active session, check if this might be a reply to bot's message
            return
        
        try:
            logger.info(f"Processing message in state: {session.state} for user {user_id}")
            
            if session.state == CharacterStates.WAITING_CHAR_NAME.value:
                await self._handle_char_name(client, message, session)
            elif session.state == CharacterStates.WAITING_ANIME_NAME.value:
                await self._handle_anime_name(client, message, session)
            elif session.state == CharacterStates.WAITING_MEDIA.value:
                await self._handle_media_upload(client, message, session)
            else:
                logger.warning(f"Unknown state: {session.state}")
                
        except Exception as e:
            logger.error(f"Error handling message in state {session.state}: {e}")
            await message.reply_text("❌ An error occurred. Please try again with /addchar")
            await db.delete_session(user_id)
    
    async def _handle_char_name(self, client: Client, message: Message, session: UserSession):
        """Handle character name input - FIXED: Better state management"""
        # Accept any text message as character name
        if not message.text:
            await message.reply_text("❌ Please send the character name as text.")
            return
        
        # Process character name
        session.char_name = message.text.strip()
        session.state = CharacterStates.WAITING_ANIME_NAME.value
        await db.save_session(session)
        
        logger.info(f"Character name saved for user {session.user_id}: {session.char_name}")
        
        # Send anime name request with forced reply
        await message.reply_text(
            "✅ **Character name saved!**\n\n"
            "💬 **Step 2: What anime does this character belong to?**\n\n"
            "Please send the anime name:",
            reply_markup=helpers.force_reply()
        )
    
    async def _handle_anime_name(self, client: Client, message: Message, session: UserSession):
        """Handle anime name input - FIXED: Better state management"""
        # Accept any text message as anime name
        if not message.text:
            await message.reply_text("❌ Please send the anime name as text.")
            return
        
        # Process anime name
        session.anime_name = message.text.strip()
        session.state = CharacterStates.WAITING_RARITY.value
        await db.save_session(session)
        
        logger.info(f"Anime name saved for user {session.user_id}: {session.anime_name}")
        
        await message.reply_text(
            "✅ **Anime name saved!**\n\n"
            "🎯 **Step 3: Select the character's rarity:**",
            reply_markup=keyboards.get_rarity_keyboard()
        )
    
    async def _handle_media_upload(self, client: Client, message: Message, session: UserSession):
        """Handle media upload with progress updates and Catbox support"""
        # Check if message contains valid media
        if not (message.photo or message.video or message.audio or message.document):
            await message.reply_text(
                "❌ **Please send a valid media file!**\n\n"
                "**Step 5: Media Upload**\n\n"
                "Supported formats:\n"
                "• 📷 Photos (JPEG, PNG, GIF)\n"
                "• 🎥 Videos (MP4, MKV, AVI)\n" 
                "• 🎵 Audio files (MP3, WAV)\n"
                "• 📄 Documents (PDF, TXT, etc.)\n\n"
                "**Max File Size:** 50MB\n\n"
                "**Upload Service:** Catbox.moe (Fast - 5-8 seconds)"
            )
            return
        
        # Check file size
        file_size = 0
        if message.photo:
            file_size = message.photo.file_size or 0
        elif message.video:
            file_size = message.video.file_size or 0
        elif message.audio:
            file_size = message.audio.file_size or 0
        elif message.document:
            file_size = message.document.file_size or 0
            
        if file_size > config.MAX_FILE_SIZE:
            await message.reply_text(
                f"❌ File too large. Maximum size is {config.MAX_FILE_SIZE // (1024*1024)}MB."
            )
            return
        
        # Send initial status message
        status_msg = await message.reply_text("🔄 Starting fast media upload...")
        
        async def update_status(text: str):
            """Helper function to update status message"""
            try:
                await status_msg.edit_text(text)
            except Exception as e:
                logger.warning(f"Failed to update status: {e}")
        
        try:
            # Upload media with Catbox
            await update_status("📥 Processing your media file...")
            
            media_url, media_type = await helpers.upload_media_with_fallback(
                client, 
                message,
                status_callback=update_status
            )
            
            if not media_url:
                await update_status(
                    "❌ **Failed to upload media to Catbox.**\n\n"
                    "This could be due to:\n"
                    "• File size too large\n" 
                    "• Unsupported file format\n"
                    "• Network issues\n"
                    "• Catbox service downtime\n\n"
                    "Please try again with a different file or check the file size."
                )
                return
            
            # Update session with media info
            session.media_url = media_url
            session.media_type = media_type
            session.state = CharacterStates.WAITING_CONFIRMATION.value
            await db.save_session(session)
            
            # Show confirmation with all character details
            preview = helpers.format_character_preview(session)
            await update_status(
                f"{preview}\n\n"
                "✅ **Media uploaded successfully to Catbox!**\n\n"
                "**Step 6: Please confirm to add this character to the database:**"
            )
            
            # Show confirmation keyboard
            await message.reply_text(
                "📋 **Please confirm your character details:**",
                reply_markup=keyboards.get_confirmation_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error handling media upload: {e}")
            await update_status(
                "❌ Error processing media. Please try again with a different file."
            )
    
    async def start(self):
        """Start the bot"""
        try:
            # Connect to MongoDB
            await db.connect()
            logger.info("Database connection established")
            
            # Start the Pyrogram client
            await self.client.start()
            logger.info("Bot started successfully")
            
            # Get bot info
            me = await self.client.get_me()
            logger.info(f"Logged in as @{me.username} (ID: {me.id})")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
        
        finally:
            # Cleanup
            await self.stop()
    
    async def stop(self):
        """Stop the bot gracefully"""
        try:
            await self.client.stop()
            await db.disconnect()
            logger.info("Bot stopped gracefully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

async def main():
    """Main entry point"""
    bot = UploadBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())