# ==================== SIMPLE CHARACTER UPLOAD BOT ====================
import os
import logging
import asyncio
import aiohttp
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configure logging for Heroku
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
class Config:
    """Configuration class for bot settings"""
    
    # Get environment variables from Heroku
    API_ID = int(os.getenv("API_ID", 26676741))
    API_HASH = os.getenv("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8496337458:AAF7ORldWpN-C6hpzSDt1bPCOeGVxfbU4qg")
    
    # MongoDB configuration
    MONGO_URI = os.getenv("MONGODB_URI", os.getenv("MONGO_URI", "mongodb+srv://erenxironman09:erenxironman09@catcherbot.koejwre.mongodb.net/?appName=catcherbot"))
    DATABASE_NAME = os.getenv("DATABASE_NAME", "catcherbot")
    
    # Bot owner ID (for admin commands)
    OWNER_ID = int(os.getenv("OWNER_ID", 7878477646))
    
    # Default log channel - @capture_database
    LOG_CHANNEL = "@capture_database"
    
    # Upload service configuration
    UPLOAD_TIMEOUT = 60
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max file size
    
    # Updated rarity mappings
    RARITY_MAP = {
        1: "⚪ Common",
        2: "🔴 Rare",
        3: "🟡 Legendary",
        4: "🥵 Exotic",
        5: "🎐 Limited Edition",
        6: "🌩️ Thundra",
        7: "🎤 Celebrity",
        8: "🎬 Animated"
    }
    
    # Subtypes for Limited Edition (rarity 5)
    LIMITED_SUBTYPES = {
        "valentine": "💝 Valentine",
        "christmas": "🎄 Christmas", 
        "halloween": "🎃 Halloween",
        "summer": "🏖️ Summer",
        "winter": "❄️ Winter",
        "basketball": "🏀 Basketball",
        "police": "👮‍♀️ Police",
        "newyear": "🎆 New Year",
        "easter": "🐰 Easter",
        "wedding": "💒 Wedding",
        "karate": "🥋 Karate",
    }

config = Config()

# ==================== MODELS ====================
class Character:
    """Data model for character documents"""
    
    def __init__(
        self,
        char_name: str,
        anime_name: str,
        rarity: str,
        character_id: int,
        media_url: Optional[str] = None,
        subrarity: Optional[str] = None,
        media_type: Optional[str] = None,
        added_by: int = None,
        timestamp: Optional[datetime] = None
    ):
        self.char_name = char_name
        self.anime_name = anime_name
        self.rarity = rarity
        self.character_id = character_id
        self.media_url = media_url
        self.subrarity = subrarity
        self.media_type = media_type
        self.added_by = added_by
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character object to dictionary for MongoDB"""
        return {
            "char_name": self.char_name,
            "anime_name": self.anime_name,
            "rarity": self.rarity,
            "character_id": self.character_id,
            "media_url": self.media_url,
            "subrarity": self.subrarity,
            "media_type": self.media_type,
            "added_by": self.added_by,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """Create Character object from dictionary"""
        return cls(
            char_name=data.get("char_name"),
            anime_name=data.get("anime_name"),
            rarity=data.get("rarity"),
            character_id=data.get("character_id"),
            media_url=data.get("media_url"),
            subrarity=data.get("subrarity"),
            media_type=data.get("media_type"),
            added_by=data.get("added_by"),
            timestamp=data.get("timestamp")
        )

# ==================== DATABASE ====================
class MongoDB:
    """MongoDB database operations handler"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.characters = None
        self.counters = None
        self.sudo_users = None
    
    async def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(config.MONGO_URI)
            self.db = self.client[config.DATABASE_NAME]
            self.characters = self.db.characters
            self.counters = self.db.counters
            self.sudo_users = self.db.sudo_users
            
            # Create indexes
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.characters.create_index("char_name")
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.create_index("added_by")
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.create_index("character_id", unique=True)
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.create_index("user_id", unique=True)
            )
            
            # Initialize counter if not exists
            counter_exists = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.counters.find_one({"_id": "character_id"})
            )
            
            if not counter_exists:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.counters.insert_one({"_id": "character_id", "seq": 0})
                )
            
            logger.info("Connected to MongoDB successfully")
            
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            await asyncio.get_event_loop().run_in_executor(None, self.client.close)
            logger.info("Disconnected from MongoDB")
    
    async def get_next_character_id(self) -> int:
        """Get next sequential character ID"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.counters.find_one_and_update(
                    {"_id": "character_id"},
                    {"$inc": {"seq": 1}},
                    return_document=True
                )
            )
            return result["seq"]
        except PyMongoError as e:
            logger.error(f"Error getting next character ID: {e}")
            raise
    
    # Character operations
    async def insert_character(self, character: Character) -> str:
        """Insert a new character into database"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.insert_one(character.to_dict())
            )
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error inserting character: {e}")
            raise
    
    async def get_character_count(self) -> int:
        """Get total number of characters in database"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.characters.count_documents({})
        )
    
    async def get_user_characters(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all characters uploaded by a user"""
        try:
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({"added_by": user_id}))
            )
            return characters
        except PyMongoError as e:
            logger.error(f"Error fetching user characters: {e}")
            return []
    
    async def get_character_by_id(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Get character by character ID"""
        try:
            character = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.find_one({"character_id": character_id})
            )
            return character
        except PyMongoError as e:
            logger.error(f"Error fetching character by ID: {e}")
            return None
    
    async def delete_character(self, character_id: int) -> bool:
        """Delete character by ID"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.delete_one({"character_id": character_id})
            )
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error deleting character: {e}")
            return False
    
    async def update_character(
        self, 
        character_id: int, 
        char_name: str, 
        anime_name: str, 
        rarity: str, 
        subrarity: Optional[str] = None
    ) -> bool:
        """Update character details"""
        try:
            update_doc = {
                "char_name": char_name,
                "anime_name": anime_name,
                "rarity": rarity
            }
            
            if subrarity:
                update_doc["subrarity"] = subrarity
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.characters.update_one(
                        {"character_id": character_id},
                        {"$set": update_doc}
                    )
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.characters.update_one(
                        {"character_id": character_id},
                        {
                            "$set": update_doc,
                            "$unset": {"subrarity": ""}
                        }
                    )
                )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error updating character: {e}")
            return False
    
    async def update_character_media(self, character_id: int, media_url: str, media_type: str) -> bool:
        """Update character media"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.update_one(
                    {"character_id": character_id},
                    {"$set": {
                        "media_url": media_url,
                        "media_type": media_type
                    }}
                )
            )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error updating character media: {e}")
            return False
    
    async def search_characters(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search characters by name or anime"""
        try:
            search_filter = {
                "$or": [
                    {"char_name": {"$regex": query, "$options": "i"}},
                    {"anime_name": {"$regex": query, "$options": "i"}}
                ]
            }
            
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find(search_filter).limit(limit))
            )
            return characters
        except PyMongoError as e:
            logger.error(f"Error searching characters: {e}")
            return []
    
    # Sudo user operations
    async def add_sudo_user(self, user_id: int) -> bool:
        """Add a sudo user"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.insert_one({"user_id": user_id})
            )
            return result.inserted_id is not None
        except PyMongoError as e:
            logger.error(f"Error adding sudo user: {e}")
            return False
    
    async def remove_sudo_user(self, user_id: int) -> bool:
        """Remove a sudo user"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.delete_one({"user_id": user_id})
            )
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error removing sudo user: {e}")
            return False
    
    async def is_sudo_user(self, user_id: int) -> bool:
        """Check if user is sudo user"""
        try:
            if user_id == config.OWNER_ID:
                return True
            sudo_user = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.find_one({"user_id": user_id})
            )
            return sudo_user is not None
        except PyMongoError as e:
            logger.error(f"Error checking sudo user: {e}")
            return False
    
    async def get_sudo_users(self) -> List[int]:
        """Get all sudo user IDs"""
        try:
            sudo_users = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.sudo_users.find({}, {"user_id": 1}))
            )
            return [user["user_id"] for user in sudo_users]
        except PyMongoError as e:
            logger.error(f"Error fetching sudo users: {e}")
            return []

# Global database instance
db = MongoDB()

# ==================== HELPERS ====================
class UploadService:
    """Handles media uploads exclusively with Catbox service"""
    
    @staticmethod
    async def upload_to_catbox(file_path: str, filename: str) -> Optional[str]:
        """Upload file to Catbox.moe"""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                with open(file_path, 'rb') as file:
                    form_data = aiohttp.FormData()
                    form_data.add_field('reqtype', 'fileupload')
                    form_data.add_field('fileToUpload', file, filename=filename)
                    
                    async with session.post('https://catbox.moe/user/api.php', data=form_data) as response:
                        if response.status == 200:
                            media_url = await response.text()
                            if media_url and media_url.startswith('http'):
                                logger.info(f"Successfully uploaded to Catbox: {media_url}")
                                return media_url.strip()
                        logger.error(f"Catbox upload failed with status {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Catbox upload timeout")
            return None
        except Exception as e:
            logger.error(f"Catbox upload error: {e}")
            return None

class Helpers:
    """Utility functions for the bot"""
    
    def __init__(self):
        self.upload_service = UploadService()
    
    async def upload_media(
        self, 
        client: Client, 
        message: Message,
        status_callback: callable = None
    ) -> tuple[Optional[str], Optional[str]]:
        """Upload media using Catbox service"""
        import os
        
        try:
            # Determine media type and file ID
            media_type = None
            file_id = None
            filename = f"media_{uuid.uuid4().hex[:8]}"
            
            if message.photo:
                file_id = message.photo.file_id
                media_type = "photo"
                filename += ".jpg"
            elif message.video:
                file_id = message.video.file_id
                media_type = "video"
                filename = message.video.file_name or f"{filename}.mp4"
            elif message.audio:
                file_id = message.audio.file_id
                media_type = "audio"
                filename = message.audio.file_name or f"{filename}.mp3"
            elif message.document:
                file_id = message.document.file_id
                media_type = "document"
                filename = message.document.file_name or f"{filename}.bin"
            else:
                return None, None
            
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
                logger.error(f"File too large: {file_size} bytes")
                return None, None
            
            # Download file
            if status_callback:
                await status_callback("📥 Downloading media file...")
                
            file_path = await client.download_media(
                file_id, 
                file_name=filename
            )
            
            if not file_path:
                logger.error("Failed to download media file")
                return None, None
            
            try:
                # Upload to Catbox
                if status_callback:
                    await status_callback("🔄 Uploading to Catbox...")
                    
                media_url = await self.upload_service.upload_to_catbox(file_path, filename)
                
                if media_url:
                    if status_callback:
                        await status_callback("✅ Upload successful!")
                    return media_url, media_type
                else:
                    if status_callback:
                        await status_callback("❌ Catbox upload failed")
                    return None, None
                    
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")
            
        except Exception as e:
            logger.error(f"Error in upload_media: {e}")
            if status_callback:
                await status_callback("❌ Upload process failed")
            return None, None
    
    @staticmethod
    def format_character_info(character_data: Dict[str, Any]) -> str:
        """Format character data for display"""
        info = f"👤 **Name:** {character_data['char_name']}\n"
        info += f"🎞️ **Anime:** {character_data['anime_name']}\n"
        info += f"🏅 **Rarity:** {character_data['rarity']}\n"
        
        if character_data.get('subrarity'):
            info += f"💠 **Sub-Rarity:** {character_data['subrarity']}\n"
        
        info += f"🆔 **ID:** `{character_data['character_id']}`\n"
        
        if character_data.get('timestamp'):
            from datetime import datetime
            timestamp = character_data['timestamp']
            if isinstance(timestamp, datetime):
                info += f"📅 **Added:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return info
    
    @staticmethod
    async def send_to_log_channel(
        client: Client, 
        character_data: Dict[str, Any], 
        username: str,
        user_id: int
    ) -> bool:
        """Send character data to log channel"""
        try:
            log_message = (
                f"🆕 **New Character Added!**\n\n"
                f"👤 **Name:** {character_data['char_name']}\n"
                f"🎞️ **Anime:** {character_data['anime_name']}\n"
                f"🏅 **Rarity:** {character_data['rarity']}\n"
            )
            
            if character_data.get('subrarity'):
                log_message += f"💠 **Sub-Rarity:** {character_data['subrarity']}\n"
            
            log_message += f"🧍 **Added by:** @{username} ({user_id})\n"
            log_message += f"🆔 **Character ID:** {character_data['character_id']}"
            
            # Send media if available
            if character_data.get('media_url') and character_data.get('media_type'):
                try:
                    if character_data.get('media_type') == 'photo':
                        await client.send_photo(
                            chat_id=config.LOG_CHANNEL,
                            photo=character_data['media_url'],
                            caption=log_message
                        )
                    elif character_data.get('media_type') == 'video':
                        await client.send_video(
                            chat_id=config.LOG_CHANNEL,
                            video=character_data['media_url'],
                            caption=log_message
                        )
                    elif character_data.get('media_type') == 'audio':
                        await client.send_audio(
                            chat_id=config.LOG_CHANNEL,
                            audio=character_data['media_url'],
                            caption=log_message
                        )
                    else:
                        await client.send_document(
                            chat_id=config.LOG_CHANNEL,
                            document=character_data['media_url'],
                            caption=log_message
                        )
                except Exception as e:
                    logger.warning(f"Failed to send media to log channel: {e}")
                    log_message += f"\n\n📸 **Media URL:** {character_data['media_url']}"
                    await client.send_message(
                        chat_id=config.LOG_CHANNEL,
                        text=log_message
                    )
            else:
                await client.send_message(
                    chat_id=config.LOG_CHANNEL,
                    text=log_message
                )
            
            logger.info(f"Character sent to log channel: {config.LOG_CHANNEL}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending to log channel: {e}")
            return False
    
    @staticmethod
    def is_owner(user_id: int) -> bool:
        """Check if user is bot owner"""
        return user_id == config.OWNER_ID
    
    @staticmethod
    async def is_sudo_user(user_id: int) -> bool:
        """Check if user is sudo user"""
        try:
            return await db.is_sudo_user(user_id)
        except Exception as e:
            logger.error(f"Error checking sudo user: {e}")
            return False
    
    @staticmethod
    async def get_username_from_id(client: Client, user_id: int) -> str:
        """Get username from user ID"""
        try:
            user = await client.get_users(user_id)
            return f"@{user.username}" if user.username else user.first_name
        except:
            return f"User ({user_id})"
    
    @staticmethod
    def parse_rarity(rarity_input: str) -> tuple[Optional[str], Optional[str]]:
        """Parse rarity input (e.g., '5 valentine' or just '5')"""
        try:
            parts = rarity_input.strip().split()
            if not parts:
                return None, None
            
            rarity_num = int(parts[0])
            if rarity_num not in config.RARITY_MAP:
                return None, None
            
            rarity_name = config.RARITY_MAP[rarity_num]
            subrarity = None
            
            # Check for Limited Edition subtype
            if rarity_num == 5 and len(parts) > 1:
                subtype_key = parts[1].lower()
                if subtype_key in config.LIMITED_SUBTYPES:
                    subrarity = config.LIMITED_SUBTYPES[subtype_key]
            
            return rarity_name, subrarity
            
        except (ValueError, IndexError):
            return None, None

helpers = Helpers()

# ==================== MAIN COMMAND HANDLERS ====================
class SimpleUploadBot:
    """Main bot class with simplified upload system"""
    
    def __init__(self):
        self.client = Client(
            "upload_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all message handlers"""
        
        @self.client.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            """Handle /start command"""
            welcome_text = (
                "👋 **Welcome to Character Upload Bot!**\n\n"
                "**Simple Upload System:**\n"
                "Just reply to any media file (photo/video/audio/document) with:\n"
                "`/upload Character_Name Anime_Name Rarity_Number [subrarity]`\n\n"
                "**Example:**\n"
                "`/upload \"Ichigo Kurosaki\" Bleach 5 valentine`\n"
                "`/upload Naruto Naruto 4`\n\n"
                "**Available Rarities (1-14):**\n"
                "1. ⚪ Common\n"
                "2. 🔴 Rare\n"
                "3. 🟡 Legendary\n"
                "4. 🥵 Exotic\n"
                "5. 🎐 Limited Edition\n"
                "6. 🌩️ Thundra\n"
                "7. 🎤 Celebrity\n"
                "8. 🎬 Animated\n"
                "**Limited Edition Subtypes:**\n"
                "valentine, christmas, halloween, summer, winter, basketball, police, newyear, easter, wedding, karate\n\n"
                "**All uploads are posted to:** @capture_database\n\n"
                "**Other Commands:**\n"
                "• `/edit ID new_name new_anime rarity` - Edit character\n"
                "• `/editmedia ID` - Edit character media (reply to media)\n"
                "• `/search query` - Search characters\n"
                "• `/info ID` - View character details\n"
                "• `/delete ID` - Delete character (owner only)\n"
                "• `/stats` - View bot statistics\n"
                "• `/help` - Show this help message"
            )
            
            await message.reply_text(welcome_text)
        
        @self.client.on_message(filters.command("upload"))
        async def upload_command(client: Client, message: Message):
            """Handle /upload command - SIMPLE UPLOAD SYSTEM"""
            user_id = message.from_user.id
            
            # Check authorization
            if not await helpers.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to upload characters.")
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
                    "**Usage:** Reply to a photo/video/audio/document with:\n"
                    "`/upload \"Character Name\" \"Anime Name\" Rarity_Number [subrarity]`\n\n"
                    "**Examples:**\n"
                    "• `/upload \"Ichigo Kurosaki\" Bleach 4`\n"
                    "• `/upload \"Goku\" \"Dragon Ball\" 5 valentine`"
                )
                return
            
            # Parse arguments
            args = message.text.split()
            if len(args) < 4:
                await message.reply_text(
                    "❌ **Invalid syntax!**\n\n"
                    "**Usage:** `/upload \"Character Name\" \"Anime Name\" Rarity_Number [subrarity]`\n\n"
                    "**Note:** Use quotes for names with spaces\n"
                    "**Example:** `/upload \"Monkey D. Luffy\" OnePiece 3`"
                )
                return
            
            # Parse character name (support quotes)
            char_name = ""
            anime_name = ""
            rarity_input = ""
            
            # Simple parsing logic
            text = message.text
            # Remove command
            text = text.replace('/upload', '', 1).strip()
            
            # Parse character name (might be in quotes)
            if text.startswith('"'):
                # Find closing quote
                end_quote = text.find('"', 1)
                if end_quote == -1:
                    await message.reply_text("❌ Invalid format. Missing closing quote for character name.")
                    return
                char_name = text[1:end_quote]
                text = text[end_quote + 1:].strip()
            else:
                # Take first word as character name
                parts = text.split()
                char_name = parts[0]
                text = ' '.join(parts[1:])
            
            # Parse anime name (might be in quotes)
            if text.startswith('"'):
                end_quote = text.find('"', 1)
                if end_quote == -1:
                    await message.reply_text("❌ Invalid format. Missing closing quote for anime name.")
                    return
                anime_name = text[1:end_quote]
                text = text[end_quote + 1:].strip()
            else:
                # Take first word as anime name
                parts = text.split()
                if not parts:
                    await message.reply_text("❌ Missing anime name.")
                    return
                anime_name = parts[0]
                text = ' '.join(parts[1:])
            
            # The rest is rarity (and optional subrarity)
            rarity_input = text.strip()
            
            if not char_name or not anime_name or not rarity_input:
                await message.reply_text("❌ Missing required parameters.")
                return
            
            # Parse rarity
            rarity_name, subrarity = helpers.parse_rarity(rarity_input)
            if not rarity_name:
                await message.reply_text("❌ Invalid rarity number. Must be 1-14.")
                return
            
            # Check for file size
            file_size = 0
            if message.reply_to_message.photo:
                file_size = message.reply_to_message.photo.file_size or 0
            elif message.reply_to_message.video:
                file_size = message.reply_to_message.video.file_size or 0
            elif message.reply_to_message.audio:
                file_size = message.reply_to_message.audio.file_size or 0
            elif message.reply_to_message.document:
                file_size = message.reply_to_message.document.file_size or 0
                
            if file_size > config.MAX_FILE_SIZE:
                await message.reply_text(
                    f"❌ File too large. Maximum size is {config.MAX_FILE_SIZE // (1024*1024)}MB."
                )
                return
            
            # Start upload process
            status_msg = await message.reply_text("🔄 Starting upload process...")
            
            async def update_status(text: str):
                try:
                    await status_msg.edit_text(text)
                except Exception as e:
                    logger.warning(f"Failed to update status: {e}")
            
            # Upload media
            await update_status("📥 Uploading media to Catbox...")
            
            media_url, media_type = await helpers.upload_media(
                client, 
                message.reply_to_message,
                status_callback=update_status
            )
            
            if not media_url:
                await update_status("❌ Failed to upload media. Please try again.")
                return
            
            # Save to database
            character_id = await db.get_next_character_id()
            character = Character(
                char_name=char_name,
                anime_name=anime_name,
                rarity=rarity_name,
                character_id=character_id,
                media_url=media_url,
                media_type=media_type,
                subrarity=subrarity,
                added_by=user_id
            )
            
            try:
                inserted_id = await db.insert_character(character)
                
                # Send to log channel
                username = message.from_user.username or message.from_user.first_name or "Unknown"
                await helpers.send_to_log_channel(
                    client, character.to_dict(), username, user_id
                )
                
                # Success message
                success_text = (
                    f"✅ **Character #{character_id} Uploaded Successfully!**\n\n"
                    f"👤 **Name:** {char_name}\n"
                    f"🎞️ **Anime:** {anime_name}\n"
                    f"🏅 **Rarity:** {rarity_name}\n"
                )
                
                if subrarity:
                    success_text += f"💠 **Sub-Rarity:** {subrarity}\n"
                
                success_text += (
                    f"\n📸 **Media:** Uploaded to Catbox\n"
                    f"📢 **Posted to:** @capture_database\n"
                    f"🆔 **Character ID:** `{character_id}`\n\n"
                    f"**Use this ID to edit or delete the character.**"
                )
                
                await update_status(success_text)
                
            except Exception as e:
                logger.error(f"Error saving character: {e}")
                await update_status("❌ Error saving character to database. Please try again.")
        
        @self.client.on_message(filters.command("edit"))
        async def edit_command(client: Client, message: Message):
            """Handle /edit command - edit character details"""
            user_id = message.from_user.id
            
            # Check authorization
            if not await helpers.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to edit characters.")
                return
            
            args = message.text.split()
            if len(args) < 5:
                await message.reply_text(
                    "✏️ **Edit Character**\n\n"
                    "**Usage:** `/edit ID \"New Name\" \"New Anime\" Rarity [subrarity]`\n\n"
                    "**Examples:**\n"
                    "• `/edit 123 \"Naruto Uzumaki\" Naruto 4`\n"
                    "• `/edit 123 \"Sakura\" Naruto 5 valentine`\n\n"
                    "**Note:** Use quotes for names with spaces"
                )
                return
            
            try:
                character_id = int(args[1])
                
                # Simple parsing similar to upload
                text = message.text
                # Remove command and ID
                text = text.replace(f'/edit {args[1]}', '', 1).strip()
                
                # Parse new character name
                new_char_name = ""
                if text.startswith('"'):
                    end_quote = text.find('"', 1)
                    if end_quote == -1:
                        await message.reply_text("❌ Missing closing quote for character name.")
                        return
                    new_char_name = text[1:end_quote]
                    text = text[end_quote + 1:].strip()
                else:
                    parts = text.split()
                    new_char_name = parts[0]
                    text = ' '.join(parts[1:])
                
                # Parse new anime name
                new_anime_name = ""
                if text.startswith('"'):
                    end_quote = text.find('"', 1)
                    if end_quote == -1:
                        await message.reply_text("❌ Missing closing quote for anime name.")
                        return
                    new_anime_name = text[1:end_quote]
                    text = text[end_quote + 1:].strip()
                else:
                    parts = text.split()
                    if not parts:
                        await message.reply_text("❌ Missing anime name.")
                        return
                    new_anime_name = parts[0]
                    text = ' '.join(parts[1:])
                
                # Parse rarity
                rarity_input = text.strip()
                new_rarity, new_subrarity = helpers.parse_rarity(rarity_input)
                
                if not new_rarity:
                    await message.reply_text("❌ Invalid rarity. Must be 1-14.")
                    return
                
                # Check if character exists
                character = await db.get_character_by_id(character_id)
                if not character:
                    await message.reply_text("❌ Character not found!")
                    return
                
                # Update character
                updated = await db.update_character(
                    character_id=character_id,
                    char_name=new_char_name,
                    anime_name=new_anime_name,
                    rarity=new_rarity,
                    subrarity=new_subrarity
                )
                
                if updated:
                    await message.reply_text(f"✅ Character `{character_id}` updated successfully!")
                    logger.info(f"Character {character_id} edited by user {user_id}")
                else:
                    await message.reply_text("❌ Failed to update character.")
                    
            except ValueError:
                await message.reply_text("❌ Invalid character ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in edit command: {e}")
                await message.reply_text("❌ Error updating character. Please check the format.")
        
        @self.client.on_message(filters.command("editmedia"))
        async def editmedia_command(client: Client, message: Message):
            """Handle /editmedia command - edit character media"""
            user_id = message.from_user.id
            
            # Check authorization
            if not await helpers.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to edit character media.")
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
                    "**Usage:** Reply to media with:\n"
                    "`/editmedia Character_ID`\n\n"
                    "**Example:**\n"
                    "Send a photo, then reply: `/editmedia 123`"
                )
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text("❌ Usage: Reply to media with `/editmedia ID`")
                return
            
            try:
                character_id = int(args[1])
                
                # Check if character exists
                character = await db.get_character_by_id(character_id)
                if not character:
                    await message.reply_text("❌ Character not found!")
                    return
                
                # Check file size
                file_size = 0
                if message.reply_to_message.photo:
                    file_size = message.reply_to_message.photo.file_size or 0
                elif message.reply_to_message.video:
                    file_size = message.reply_to_message.video.file_size or 0
                elif message.reply_to_message.audio:
                    file_size = message.reply_to_message.audio.file_size or 0
                elif message.reply_to_message.document:
                    file_size = message.reply_to_message.document.file_size or 0
                    
                if file_size > config.MAX_FILE_SIZE:
                    await message.reply_text(
                        f"❌ File too large. Maximum size is {config.MAX_FILE_SIZE // (1024*1024)}MB."
                    )
                    return
                
                status_msg = await message.reply_text("🔄 Uploading new media...")
                
                # Upload new media
                media_url, media_type = await helpers.upload_media(
                    client, 
                    message.reply_to_message
                )
                
                if not media_url:
                    await status_msg.edit_text("❌ Failed to upload media.")
                    return
                
                # Update character media
                updated = await db.update_character_media(character_id, media_url, media_type)
                
                if updated:
                    await status_msg.edit_text(f"✅ Media updated for character `{character_id}`!")
                    logger.info(f"Character {character_id} media updated by user {user_id}")
                else:
                    await status_msg.edit_text("❌ Failed to update media.")
                    
            except ValueError:
                await message.reply_text("❌ Invalid character ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in editmedia command: {e}")
                await message.reply_text("❌ Error updating media.")
        
        @self.client.on_message(filters.command(["search", "find"]))
        async def search_command(client: Client, message: Message):
            """Handle /search command - find characters"""
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "🔍 **Search Characters**\n\n"
                    "**Usage:** `/search query`\n\n"
                    "**Examples:**\n"
                    "• `/search naruto`\n"
                    "• `/search bleach`\n"
                    "• `/search ichigo`"
                )
                return
            
            query = ' '.join(args[1:])
            await message.reply_text(f"🔍 Searching for: `{query}`...")
            
            try:
                results = await db.search_characters(query, limit=15)
                
                if not results:
                    await message.reply_text("❌ No characters found.")
                    return
                
                if len(results) == 1:
                    # Show single result with details
                    char = results[0]
                    char_info = helpers.format_character_info(char)
                    
                    if char.get('media_url'):
                        try:
                            if char.get('media_type') == 'photo':
                                await client.send_photo(
                                    chat_id=message.chat.id,
                                    photo=char['media_url'],
                                    caption=f"**Search Result:**\n\n{char_info}"
                                )
                            elif char.get('media_type') == 'video':
                                await client.send_video(
                                    chat_id=message.chat.id,
                                    video=char['media_url'],
                                    caption=f"**Search Result:**\n\n{char_info}"
                                )
                            elif char.get('media_type') == 'audio':
                                await client.send_audio(
                                    chat_id=message.chat.id,
                                    audio=char['media_url'],
                                    caption=f"**Search Result:**\n\n{char_info}"
                                )
                            else:
                                await client.send_document(
                                    chat_id=message.chat.id,
                                    document=char['media_url'],
                                    caption=f"**Search Result:**\n\n{char_info}"
                                )
                        except:
                            await message.reply_text(f"**Search Result:**\n\n{char_info}")
                    else:
                        await message.reply_text(f"**Search Result:**\n\n{char_info}")
                else:
                    # Show list of results
                    result_text = f"🔍 **Search Results for:** `{query}`\n\n"
                    
                    for i, char in enumerate(results[:10], 1):
                        result_text += f"{i}. **{char['char_name']}** - {char['anime_name']} - {char['rarity']} (ID: `{char['character_id']}`)\n"
                    
                    if len(results) > 10:
                        result_text += f"\n... and {len(results) - 10} more results"
                    
                    result_text += "\n\n**Use** `/info ID` **to view details of a specific character.**"
                    
                    await message.reply_text(result_text)
                    
            except Exception as e:
                logger.error(f"Error in search command: {e}")
                await message.reply_text("❌ Error searching characters.")
        
        @self.client.on_message(filters.command(["info", "view", "check"]))
        async def info_command(client: Client, message: Message):
            """Handle /info command - view character details"""
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "ℹ️ **Character Info**\n\n"
                    "**Usage:** `/info ID`\n\n"
                    "**Example:** `/info 123`"
                )
                return
            
            try:
                character_id = int(args[1])
                character = await db.get_character_by_id(character_id)
                
                if not character:
                    await message.reply_text("❌ Character not found!")
                    return
                
                char_info = helpers.format_character_info(character)
                uploaded_by = await helpers.get_username_from_id(client, character['added_by'])
                char_info += f"👤 **Uploaded by:** {uploaded_by}"
                
                # Add edit buttons if user is sudo
                if await helpers.is_sudo_user(message.from_user.id):
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("✏️ Edit Details", callback_data=f"edit_{character_id}"),
                            InlineKeyboardButton("🖼️ Edit Media", callback_data=f"editmedia_{character_id}")
                        ]
                    ])
                else:
                    keyboard = None
                
                if character.get('media_url'):
                    try:
                        if character.get('media_type') == 'photo':
                            await client.send_photo(
                                chat_id=message.chat.id,
                                photo=character['media_url'],
                                caption=char_info,
                                reply_markup=keyboard
                            )
                        elif character.get('media_type') == 'video':
                            await client.send_video(
                                chat_id=message.chat.id,
                                video=character['media_url'],
                                caption=char_info,
                                reply_markup=keyboard
                            )
                        elif character.get('media_type') == 'audio':
                            await client.send_audio(
                                chat_id=message.chat.id,
                                audio=character['media_url'],
                                caption=char_info,
                                reply_markup=keyboard
                            )
                        else:
                            await client.send_document(
                                chat_id=message.chat.id,
                                document=character['media_url'],
                                caption=char_info,
                                reply_markup=keyboard
                            )
                    except Exception as e:
                        logger.warning(f"Failed to send media: {e}")
                        char_info += f"\n\n📸 **Media URL:** {character['media_url']}"
                        await message.reply_text(char_info, reply_markup=keyboard)
                else:
                    await message.reply_text(char_info, reply_markup=keyboard)
                    
            except ValueError:
                await message.reply_text("❌ Invalid character ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in info command: {e}")
                await message.reply_text("❌ Error fetching character info.")
        
        @self.client.on_message(filters.command(["delete", "remove", "del"]))
        async def delete_command(client: Client, message: Message):
            """Handle /delete command - remove character"""
            # Only owner can delete
            if not helpers.is_owner(message.from_user.id):
                await message.reply_text("❌ Only the bot owner can delete characters.")
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "🗑️ **Delete Character**\n\n"
                    "**Usage:** `/delete ID`\n\n"
                    "**Example:** `/delete 123`"
                )
                return
            
            try:
                character_id = int(args[1])
                character = await db.get_character_by_id(character_id)
                
                if not character:
                    await message.reply_text("❌ Character not found!")
                    return
                
                # Show confirmation
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{character_id}"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")
                    ]
                ])
                
                await message.reply_text(
                    f"⚠️ **Are you sure you want to delete this character?**\n\n"
                    f"**Name:** {character['char_name']}\n"
                    f"**Anime:** {character['anime_name']}\n"
                    f"**ID:** `{character_id}`\n\n"
                    f"**This action cannot be undone!**",
                    reply_markup=keyboard
                )
                
            except ValueError:
                await message.reply_text("❌ Invalid character ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in delete command: {e}")
                await message.reply_text("❌ Error processing delete request.")
        
        @self.client.on_message(filters.command(["stats", "status"]))
        async def stats_command(client: Client, message: Message):
            """Handle /stats command - view bot statistics"""
            try:
                total_chars = await db.get_character_count()
                user_chars = await db.get_user_characters(message.from_user.id)
                is_sudo = await helpers.is_sudo_user(message.from_user.id)
                
                stats_text = (
                    "📊 **Bot Statistics**\n\n"
                    f"• **Total Characters:** {total_chars}\n"
                    f"• **Your Uploads:** {len(user_chars)}\n"
                    f"• **Your Status:** {'✅ Sudo User' if is_sudo else '❌ Regular User'}\n"
                    f"• **Log Channel:** {config.LOG_CHANNEL}\n"
                    f"• **Max File Size:** {config.MAX_FILE_SIZE // (1024*1024)}MB\n\n"
                    "**Commands:**\n"
                    "• `/upload` - Upload character\n"
                    "• `/edit` - Edit character\n"
                    "• `/search` - Search characters\n"
                    "• `/info` - View character info\n"
                    "• `/help` - Show help"
                )
                
                await message.reply_text(stats_text)
                
            except Exception as e:
                logger.error(f"Error in stats command: {e}")
                await message.reply_text("❌ Error fetching statistics.")
        
        @self.client.on_message(filters.command("help"))
        async def help_command(client: Client, message: Message):
            """Handle /help command"""
            help_text = (
                "ℹ️ **Character Upload Bot Help**\n\n"
                "**📤 UPLOAD COMMAND:**\n"
                "Reply to any media file with:\n"
                "`/upload \"Character Name\" \"Anime Name\" Rarity [subrarity]`\n\n"
                "**Examples:**\n"
                "• `/upload \"Ichigo Kurosaki\" Bleach 4`\n"
                "• `/upload \"Goku\" \"Dragon Ball\" 5 valentine`\n\n"
                "**🔄 EDIT COMMANDS:**\n"
                "• `/edit ID \"New Name\" \"New Anime\" Rarity [subrarity]`\n"
                "• `/editmedia ID` (reply to new media)\n\n"
                "**🔍 SEARCH COMMANDS:**\n"
                "• `/search query` - Search by name or anime\n"
                "• `/info ID` - View character details\n\n"
                "**⚙️ OTHER COMMANDS:**\n"
                "• `/stats` - View bot statistics\n"
                "• `/help` - Show this message\n\n"
                "**🎯 RARITIES (1-14):**\n"
                "1. ⚪ Common\n"
                "2. 🔴 Rare\n"
                "3. 🟡 Legendary\n"
                "4. 🥵 Exotic\n"
                "5. 🎐 Limited Edition\n"
                "6. 🌩️ Thundra\n"
                "7. 🎤 Celebrity\n"
                "8. 🎬 Animated\n"
                "**All uploads are automatically posted to:** @capture_database"
            )
            
            await message.reply_text(help_text)
        
        # Callback query handler for inline buttons
        @self.client.on_callback_query()
        async def handle_callbacks(client: Client, callback_query):
            data = callback_query.data
            
            try:
                if data.startswith("edit_"):
                    character_id = int(data.split("_")[1])
                    await callback_query.message.edit_text(
                        f"✏️ **Edit Character #{character_id}**\n\n"
                        "Please use the `/edit` command:\n"
                        "`/edit ID \"New Name\" \"New Anime\" Rarity [subrarity]`\n\n"
                        f"**Example:**\n"
                        f"`/edit {character_id} \"New Name\" \"New Anime\" 5 valentine`"
                    )
                    await callback_query.answer()
                
                elif data.startswith("editmedia_"):
                    character_id = int(data.split("_")[1])
                    await callback_query.message.edit_text(
                        f"🖼️ **Edit Media for Character #{character_id}**\n\n"
                        "Please reply to a media file with:\n"
                        f"`/editmedia {character_id}`"
                    )
                    await callback_query.answer()
                
                elif data.startswith("confirm_delete_"):
                    character_id = int(data.split("_")[2])
                    
                    deleted = await db.delete_character(character_id)
                    if deleted:
                        await callback_query.message.edit_text(f"✅ Character `{character_id}` deleted successfully!")
                        logger.info(f"Character {character_id} deleted by user {callback_query.from_user.id}")
                    else:
                        await callback_query.message.edit_text(f"❌ Failed to delete character `{character_id}`")
                    
                    await callback_query.answer()
                
                elif data == "cancel_delete":
                    await callback_query.message.edit_text("❌ Delete cancelled.")
                    await callback_query.answer()
                    
            except Exception as e:
                logger.error(f"Error handling callback: {e}")
                await callback_query.answer("An error occurred.", show_alert=True)
    
    async def start(self):
        """Start the bot"""
        try:
            await db.connect()
            logger.info("Database connection established")
            
            await self.client.start()
            logger.info("Bot started successfully")
            
            me = await self.client.get_me()
            logger.info(f"Logged in as @{me.username} (ID: {me.id})")
            logger.info(f"Log channel: {config.LOG_CHANNEL}")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
        
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot gracefully"""
        try:
            await self.client.stop()
            await db.disconnect()
            logger.info("Bot stopped gracefully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# ==================== MAIN FUNCTION ====================
async def main():
    """Main entry point"""
    bot = SimpleUploadBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())



