# ==================== COMPLETE CHARACTER UPLOAD BOT - SINGLE FILE ====================
import os
import sys
import logging
import asyncio
import aiohttp
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, 
    InlineKeyboardMarkup, ForceReply
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
    DEFAULT_LOG_CHANNEL = "@capture_database"
    
    # Upload service configuration
    UPLOAD_TIMEOUT = 60
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max file size
    
    # Mass upload configuration
    MAX_BATCH_SIZE = 50
    BATCH_PROCESSING_TIMEOUT = 300
    
    # Updated rarity mappings as per request
    RARITY_MAP = {
        1: "⚪ Common",
        2: "🟢 Uncommon",
        3: "🔴 Rare",
        4: "🟡 Legendary",
        5: "🎐 Limited Edition",
        6: "💎 Premium",
        7: "🥵 Exotic",
        8: "🎬 Animated",
        9: "🌩️ Thundra",
        10: "☄️ Galvoria",
        11: "🌈 Neon",
        12: "🛡️ Supreme",
        13: "🔮 Crystal",
        14: "🎤 Celebrity"
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
    
    # Subrarity to emoji mapping for auto-emoji system
    SUBRARITY_EMOJI_MAP = {
        "valentine": "💝",
        "christmas": "🎄", 
        "halloween": "🎃",
        "summer": "🏖️",
        "winter": "❄️",
        "basketball": "🏀",
        "police": "👮‍♀️",
        "newyear": "🎆",
        "easter": "🐰",
        "wedding": "💒",
        "karate": "🥋",
    }
    
    # Rarities that have sub-types (only Limited Edition now)
    RARITIES_WITH_SUBTYPES = [5]

config = Config()

# ==================== STATES ====================
class CharacterStates(Enum):
    """State management for character upload flow"""
    WAITING_CHAR_NAME = "waiting_char_name"
    WAITING_ANIME_NAME = "waiting_anime_name" 
    WAITING_RARITY = "waiting_rarity"
    WAITING_SUBRARITY = "waiting_subrarity"
    WAITING_MEDIA = "waiting_media"
    WAITING_CONFIRMATION = "waiting_confirmation"

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

class UserSession:
    """Temporary session data for character upload flow"""
    
    def __init__(
        self,
        user_id: int,
        state: str,
        char_name: Optional[str] = None,
        anime_name: Optional[str] = None,
        rarity: Optional[str] = None,
        subrarity: Optional[str] = None,
        media_file_id: Optional[str] = None,
        media_type: Optional[str] = None,
        media_url: Optional[str] = None
    ):
        self.user_id = user_id
        self.state = state
        self.char_name = char_name
        self.anime_name = anime_name
        self.rarity = rarity
        self.subrarity = subrarity
        self.media_file_id = media_file_id
        self.media_type = media_type
        self.media_url = media_url
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "user_id": self.user_id,
            "state": self.state,
            "char_name": self.char_name,
            "anime_name": self.anime_name,
            "rarity": self.rarity,
            "subrarity": self.subrarity,
            "media_file_id": self.media_file_id,
            "media_type": self.media_type,
            "media_url": self.media_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create UserSession from dictionary"""
        return cls(
            user_id=data.get("user_id"),
            state=data.get("state"),
            char_name=data.get("char_name"),
            anime_name=data.get("anime_name"),
            rarity=data.get("rarity"),
            subrarity=data.get("subrarity"),
            media_file_id=data.get("media_file_id"),
            media_type=data.get("media_type"),
            media_url=data.get("media_url")
        )

@dataclass
class MassUploadSession:
    """Mass upload session for batch character processing"""
    user_id: int
    char_name: str
    anime_name: str
    uploaded_characters: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mass upload session to dictionary"""
        return {
            "user_id": self.user_id,
            "char_name": self.char_name,
            "anime_name": self.anime_name,
            "uploaded_characters": self.uploaded_characters,
            "created_at": self.created_at,
            "last_activity": self.last_activity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MassUploadSession':
        """Create MassUploadSession from dictionary"""
        session = cls(
            user_id=data.get("user_id"),
            char_name=data.get("char_name"),
            anime_name=data.get("anime_name"),
            uploaded_characters=data.get("uploaded_characters", []),
            created_at=data.get("created_at", datetime.utcnow())
        )
        session.last_activity = data.get("last_activity", session.created_at)
        return session
    
    def add_character(self, character_data: Dict[str, Any]):
        """Add a character to the session"""
        self.uploaded_characters.append(character_data)
        self.last_activity = datetime.utcnow()
    
    def remove_last_character(self) -> Optional[Dict[str, Any]]:
        """Remove and return the last uploaded character"""
        if self.uploaded_characters:
            return self.uploaded_characters.pop()
        return None
    
    def get_character_count(self) -> int:
        """Get total characters uploaded in this session"""
        return len(self.uploaded_characters)
    
    def get_session_summary(self) -> str:
        """Get formatted session summary"""
        return (
            f"📋 **Current Session**\n\n"
            f"👤 **Character:** {self.char_name}\n"
            f"🎞️ **Anime:** {self.anime_name}\n"
            f"📊 **Uploaded:** {self.get_character_count()} characters\n"
            f"🕐 **Started:** {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

# ==================== DATABASE ====================
class MongoDB:
    """MongoDB database operations handler"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.characters = None
        self.sessions = None
        self.mass_upload_sessions = None
        self.config = None
        self.counters = None
        self.sudo_users = None
    
    async def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(config.MONGO_URI)
            self.db = self.client[config.DATABASE_NAME]
            self.characters = self.db.characters
            self.sessions = self.db.user_sessions
            self.mass_upload_sessions = self.db.mass_upload_sessions
            self.config = self.db.config
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
                lambda: self.sessions.create_index("user_id", unique=True)
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.mass_upload_sessions.create_index("user_id", unique=True)
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
            
            # Initialize log channel to @capture_database if not set
            log_config = await self.get_log_config()
            if not log_config.get('log_chat_1'):
                # Try to get chat ID for @capture_database
                logger.info("Setting default log channel to @capture_database")
            
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
    
    # Session operations
    async def save_session(self, session: UserSession):
        """Save or update user session"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sessions.update_one(
                    {"user_id": session.user_id},
                    {"$set": session.to_dict()},
                    upsert=True
                )
            )
        except PyMongoError as e:
            logger.error(f"Error saving session: {e}")
            raise
    
    async def get_session(self, user_id: int) -> Optional[UserSession]:
        """Get user session by user ID"""
        try:
            session_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sessions.find_one({"user_id": user_id})
            )
            if session_data:
                return UserSession.from_dict(session_data)
            return None
        except PyMongoError as e:
            logger.error(f"Error fetching session: {e}")
            return None
    
    async def delete_session(self, user_id: int):
        """Delete user session"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sessions.delete_one({"user_id": user_id})
            )
        except PyMongoError as e:
            logger.error(f"Error deleting session: {e}")
            raise
    
    # Mass Upload Session operations
    async def save_mass_upload_session(self, session: MassUploadSession):
        """Save or update mass upload session"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.mass_upload_sessions.update_one(
                    {"user_id": session.user_id},
                    {"$set": session.to_dict()},
                    upsert=True
                )
            )
        except PyMongoError as e:
            logger.error(f"Error saving mass upload session: {e}")
            raise
    
    async def get_mass_upload_session(self, user_id: int) -> Optional[MassUploadSession]:
        """Get mass upload session by user ID"""
        try:
            session_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.mass_upload_sessions.find_one({"user_id": user_id})
            )
            if session_data:
                return MassUploadSession.from_dict(session_data)
            return None
        except PyMongoError as e:
            logger.error(f"Error fetching mass upload session: {e}")
            return None
    
    async def delete_mass_upload_session(self, user_id: int):
        """Delete mass upload session"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.mass_upload_sessions.delete_one({"user_id": user_id})
            )
        except PyMongoError as e:
            logger.error(f"Error deleting mass upload session: {e}")
            raise
    
    # Configuration operations
    async def get_log_config(self) -> Dict[str, Any]:
        """Get log channel configuration"""
        try:
            config_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.config.find_one({"_id": "log_config"})
            )
            if config_data:
                return config_data
            return {"log_chat_1": config.DEFAULT_LOG_CHANNEL, "log_chat_2": None}
        except PyMongoError as e:
            logger.error(f"Error fetching log config: {e}")
            return {"log_chat_1": config.DEFAULT_LOG_CHANNEL, "log_chat_2": None}
    
    async def update_log_chat(self, chat_type: str, chat_id: int):
        """Update log chat configuration"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.config.update_one(
                    {"_id": "log_config"},
                    {"$set": {f"log_chat_{chat_type}": chat_id}},
                    upsert=True
                )
            )
        except PyMongoError as e:
            logger.error(f"Error updating log config: {e}")
            raise
    
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

# ==================== KEYBOARDS ====================
class Keyboards:
    """Inline keyboard generators for the bot"""
    
    @staticmethod
    def get_rarity_keyboard() -> InlineKeyboardMarkup:
        """Generate rarity selection keyboard with 14 rarities, 3 per row"""
        buttons = []
        row = []
        
        for rarity_id, rarity_name in config.RARITY_MAP.items():
            row.append(InlineKeyboardButton(
                rarity_name, 
                callback_data=f"rarity_{rarity_id}"
            ))
            if len(row) == 3:  # 3 buttons per row for better layout
                buttons.append(row)
                row = []
        
        # Add remaining buttons if any
        if row:
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_start")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def get_limited_subtypes_keyboard() -> InlineKeyboardMarkup:
        """Generate Limited Edition subtypes keyboard"""
        buttons = []
        row = []
        
        for subtype_key, subtype_name in config.LIMITED_SUBTYPES.items():
            row.append(InlineKeyboardButton(
                subtype_name,
                callback_data=f"subrarity_limited_{subtype_key}"
            ))
            if len(row) == 3:  # 3 per row
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_rarity")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def get_confirmation_keyboard() -> InlineKeyboardMarkup:
        """Generate confirmation keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data="confirm_upload"),
                InlineKeyboardButton("❌ Reject", callback_data="reject_upload")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="back_subrarity")]
        ])
    
    @staticmethod
    def get_main_menu_keyboard() -> InlineKeyboardMarkup:
        """Generate main menu keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Add Character", callback_data="add_char"),
                InlineKeyboardButton("📊 Status", callback_data="status")
            ],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ])

keyboards = Keyboards()

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
    
    @staticmethod
    def force_reply():
        """Create a force reply markup"""
        return ForceReply(selective=True)
    
    async def upload_media_with_fallback(
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
                file_name=filename,
                progress=self._download_progress,
                progress_args=(status_callback,)
            )
            
            if not file_path:
                logger.error("Failed to download media file")
                return None, None
            
            try:
                # Upload to Catbox
                if status_callback:
                    await status_callback("🔄 Uploading to Catbox... (5-8 seconds)")
                    
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
            logger.error(f"Error in upload_media_with_fallback: {e}")
            if status_callback:
                await status_callback("❌ Upload process failed")
            return None, None
    
    async def _download_progress(self, current, total, status_callback):
        """Progress callback for download"""
        if status_callback and total > 0:
            percentage = (current / total) * 100
            if int(percentage) % 25 == 0:
                await status_callback(f"📥 Downloading... {int(percentage)}%")
    
    @staticmethod
    def format_character_preview(session: UserSession) -> str:
        """Format character data for preview"""
        preview = "📋 **Character Upload Preview**\n\n"
        preview += f"👤 **Name:** {session.char_name}\n"
        preview += f"🎞️ **Anime:** {session.anime_name}\n"
        preview += f"🏅 **Rarity:** {session.rarity}\n"
        
        if session.subrarity:
            preview += f"💠 **Sub-Rarity:** {session.subrarity}\n"
        
        if session.media_url:
            preview += f"📸 **Media:** Uploaded successfully\n"
        else:
            preview += f"📸 **Media:** Waiting for upload\n"
        
        return preview
    
    @staticmethod
    def format_log_message(character_data: Dict[str, Any], username: str, user_id: int) -> str:
        """Format character data for log channels"""
        log_msg = "🆕 **New Character Added!**\n\n"
        log_msg += f"👤 **Name:** {character_data['char_name']}\n"
        log_msg += f"🎞️ **Anime:** {character_data['anime_name']}\n"
        log_msg += f"🏅 **Rarity:** {character_data['rarity']}\n"
        
        if character_data.get('subrarity'):
            log_msg += f"💠 **Sub-Rarity:** {character_data['subrarity']}\n"
        
        log_msg += f"🧍 **Added by:** @{username} ({user_id})\n"
        log_msg += f"🆔 **Character ID:** {character_data['character_id']}\n\n"
        
        if character_data.get('media_url'):
            log_msg += "📸 Character media uploaded successfully\n\n"
        
        log_msg += "**Note:** Character IDs increase automatically — next one will be " \
                  f"{character_data['character_id'] + 1}"
        
        return log_msg
    
    @staticmethod
    async def send_to_log_channels(
        client: Client, 
        character_data: Dict[str, Any], 
        username: str,
        user_id: int,
        db: MongoDB
    ) -> bool:
        """Send character data to configured log channels (default: @capture_database)"""
        try:
            log_config = await db.get_log_config()
            log_message = Helpers.format_log_message(character_data, username, user_id)
            
            success = True
            sent_to = []
            
            # Send to @capture_database (log_chat_1)
            log_chat = log_config.get('log_chat_1', config.DEFAULT_LOG_CHANNEL)
            if log_chat:
                try:
                    if character_data.get('media_url') and character_data.get('media_type'):
                        try:
                            if character_data.get('media_type') == 'photo':
                                await client.send_photo(
                                    chat_id=log_chat,
                                    photo=character_data['media_url'],
                                    caption=log_message
                                )
                            elif character_data.get('media_type') == 'video':
                                await client.send_video(
                                    chat_id=log_chat,
                                    video=character_data['media_url'],
                                    caption=log_message
                                )
                            elif character_data.get('media_type') == 'audio':
                                await client.send_audio(
                                    chat_id=log_chat,
                                    audio=character_data['media_url'],
                                    caption=log_message
                                )
                            else:
                                await client.send_document(
                                    chat_id=log_chat,
                                    document=character_data['media_url'],
                                    caption=log_message
                                )
                        except Exception as e:
                            logger.warning(f"Failed to send media to log channel: {e}")
                            log_message += f"\n\n📸 **Media URL:** {character_data['media_url']}"
                            await client.send_message(
                                chat_id=log_chat,
                                text=log_message
                            )
                    else:
                        await client.send_message(
                            chat_id=log_chat,
                            text=log_message
                        )
                    sent_to.append("Capture Database (@capture_database)")
                except Exception as e:
                    logger.error(f"Failed to send to @capture_database: {e}")
                    success = False
            
            if not sent_to:
                logger.warning("No log channels configured")
                return False
                
            logger.info(f"Log message sent to: {', '.join(sent_to)}")
            return success
            
        except Exception as e:
            logger.error(f"Error in send_to_log_channels: {e}")
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
    def format_session_duration(start_time: datetime) -> str:
        """Format session duration for display"""
        duration = datetime.utcnow() - start_time
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

helpers = Helpers()

# ==================== COMMAND HANDLERS ====================
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
            "**Log Channel:** All uploaded characters are sent to @capture_database"
        )
        
        await message.reply_text(
            welcome_text,
            reply_markup=keyboards.get_main_menu_keyboard()
        )
    
    async def addchar_command(self, client: Client, message: Message):
        """Handle /addchar command - starts with character name"""
        user_id = message.from_user.id
        
        if not await helpers.is_sudo_user(user_id):
            await message.reply_text("❌ You are not authorized to use this bot. Contact admin.")
            return
        
        mass_session = await db.get_mass_upload_session(user_id)
        if mass_session:
            await message.reply_text(
                "⚠️ **You have an active mass upload session!**\n\n"
                f"**Current Session:** {mass_session.char_name} ({mass_session.anime_name})\n\n"
                "Use `/donechar` to end mass session first."
            )
            return
        
        existing_session = await db.get_session(user_id)
        if existing_session:
            await message.reply_text(
                "⚠️ **You already have an active upload session!**\n\n"
                "Use `/cs` to clear your current session first."
            )
            return
        
        session = UserSession(
            user_id=user_id,
            state=CharacterStates.WAITING_CHAR_NAME.value
        )
        await db.save_session(session)
        
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
        
        mass_session = await db.get_mass_upload_session(user_id)
        if mass_session:
            await db.delete_mass_upload_session(user_id)
            await message.reply_text("✅ Mass upload session cleared!")
            return
        
        session = await db.get_session(user_id)
        if session:
            await db.delete_session(user_id)
            await message.reply_text("✅ Single character upload session cleared!")
            return
        
        await message.reply_text("ℹ️ No active session to clear.")
    
    async def check_command(self, client: Client, message: Message):
        """Handle /c command - check character by ID"""
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
                await message.reply_text("⚠️ Character not found!")
                return
            
            character_info = (
                "🔍 **Character Preview**\n\n"
                f"👤 **Name:** {character['char_name']}\n"
                f"🎞️ **Anime:** {character['anime_name']}\n"
                f"🏅 **Rarity:** {character['rarity']}\n"
                f"🆔 **Character ID:** {character['character_id']}\n"
                f"🧍 **Uploaded by:** {await helpers.get_username_from_id(client, character['added_by'])}"
            )
            
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
                    character_info += f"\n\n📸 **Media URL:** {character['media_url']}"
                    await message.reply_text(character_info)
            else:
                await message.reply_text(character_info)
                
        except ValueError:
            await message.reply_text("❌ Invalid character ID.")
        except Exception as e:
            logger.error(f"Error in check command: {e}")
            await message.reply_text("❌ Error fetching character.")
    
    async def status_command(self, client: Client, message: Message):
        """Handle /status command - show bot statistics"""
        try:
            total_chars = await db.get_character_count()
            user_chars = await db.get_user_characters(message.from_user.id)
            
            mass_session = await db.get_mass_upload_session(message.from_user.id)
            mass_session_info = ""
            if mass_session:
                mass_session_info = f"• **Active Mass Session:** {mass_session.char_name} ({mass_session.get_character_count()} chars)\n"
            
            is_sudo = await helpers.is_sudo_user(message.from_user.id)
            
            status_text = (
                "📊 **Bot Status**\n\n"
                f"• **Total Characters:** {total_chars}\n"
                f"• **Your Characters:** {len(user_chars)}\n"
                f"{mass_session_info}"
                f"• **Bot Owner:** {('Yes' if helpers.is_owner(message.from_user.id) else 'No')}\n"
                f"• **Sudo User:** {('Yes' if is_sudo else 'No')}\n"
                f"• **Upload Service:** Catbox.moe (Fast)\n"
                f"• **Log Channel:** @capture_database\n"
                f"• **Upload Flow:** Character → Anime → Rarity → Media → Confirm"
            )
            
            await message.reply_text(status_text)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await message.reply_text("❌ Error fetching status.")
    
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
            "**Available Rarities (14 Total):**\n"
            "1. ⚪ Common\n"
            "2. 🟢 Uncommon\n"
            "3. 🔴 Rare\n"
            "4. 🟡 Legendary\n"
            "5. 🎐 Limited Edition\n"
            "6. 💎 Premium\n"
            "7. 🥵 Exotic\n"
            "8. 🎬 Animated\n"
            "9. 🌩️ Thundra\n"
            "10. ☄️ Galvoria\n"
            "11. 🌈 Neon\n"
            "12. 🛡️ Supreme\n"
            "13. 🔮 Crystal\n"
            "14. 🎤 Celebrity\n\n"
            "**Commands:**\n"
            "• `/start` - Start the bot\n"
            "• `/addchar` - Add a single character\n" 
            "• `/cs` - Clear current upload session\n"
            "• `/c [id]` - Check character by ID\n"
            "• `/status` - Check bot statistics\n"
            "• `/help` - Show this help message\n\n"
            "**Supported Media:** Photos, Videos, Audio, Documents (max 50MB)\n"
            "**Upload Service:** Catbox.moe (Fast - 5-8 seconds)\n"
            "**Log Channel:** All uploaded characters are sent to @capture_database\n"
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
                await message.reply_text("❌ Usage: /setlog1 <chat_id or username>")
                return
            
            chat_id = args[1]
            # Try to convert to int if it's a numeric ID
            try:
                chat_id = int(chat_id)
            except ValueError:
                # It's a username, keep as string
                pass
            
            await db.update_log_chat("1", chat_id)
            
            await message.reply_text(f"✅ Log Channel 1 set to: `{chat_id}`")
            
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
                await message.reply_text("❌ Usage: /setlog2 <chat_id or username>")
                return
            
            chat_id = args[1]
            try:
                chat_id = int(chat_id)
            except ValueError:
                pass
            
            await db.update_log_chat("2", chat_id)
            
            await message.reply_text(f"✅ Log Channel 2 set to: `{chat_id}`")
            
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
            log_text += f"• **Log Channel 2:** `{log_config.get('log_chat_2', 'Not set')}`\n\n"
            log_text += f"**Default:** {config.DEFAULT_LOG_CHANNEL}"
            
            await message.reply_text(log_text)
            
        except Exception as e:
            logger.error(f"Error showing logs: {e}")
            await message.reply_text("❌ Error fetching log configuration.")

# ==================== CALLBACK HANDLERS ====================
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
        
        if not await helpers.is_sudo_user(user_id):
            await callback_query.answer("❌ You are not authorized to use this bot.", show_alert=True)
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
                f"• **Your Characters:** {len(user_chars)}\n"
                f"• **Log Channel:** @capture_database"
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
            "Use `/addchar` to start uploading characters.\n\n"
            "**All uploaded characters are sent to @capture_database**"
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
        
        session.rarity = rarity_name
        
        # Check if rarity has subtypes (only Limited Edition - rarity 5)
        if rarity_id in config.RARITIES_WITH_SUBTYPES:
            session.state = CharacterStates.WAITING_SUBRARITY.value
            if rarity_id == 5:  # Limited Edition
                keyboard = keyboards.get_limited_subtypes_keyboard()
                await callback_query.message.edit_text(
                    f"✅ **Rarity Selected: {rarity_name}**\n\n"
                    f"🎯 **Step 4: Select Limited Edition Subtype**",
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
                "**Upload Service:** Catbox.moe (Fast - 5-8 seconds)\n\n"
                "**Note:** Character will be sent to @capture_database"
            )
        
        await db.save_session(session)
        await callback_query.answer()
    
    async def handle_subrarity_selection(self, client: Client, callback_query: CallbackQuery):
        """Handle sub-rarity selection callback (only for Limited Edition)"""
        user_id = callback_query.from_user.id
        session = await db.get_session(user_id)
        
        if not session:
            await callback_query.answer("Session expired. Please start again with /addchar", show_alert=True)
            return
        
        parts = callback_query.data.split("_")
        subtype_key = parts[2]
        
        subrarity_name = config.LIMITED_SUBTYPES[subtype_key]
        
        session.subrarity = subrarity_name
        session.state = CharacterStates.WAITING_MEDIA.value
        await db.save_session(session)
        
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
            "**Upload Service:** Catbox.moe (Fast - 5-8 seconds)\n\n"
            "**Note:** Character will be sent to @capture_database"
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
            character_id = await db.get_next_character_id()
            
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
                
                username = callback_query.from_user.username or callback_query.from_user.first_name or "Unknown"
                await helpers.send_to_log_channels(
                    client, character.to_dict(), username, user_id, db
                )
                
                success_text = (
                    "🎉 **Character successfully added to the database!**\n\n"
                    f"👤 **Name:** {session.char_name}\n"
                    f"🎞️ **Anime:** {session.anime_name}\n"
                    f"🏅 **Rarity:** {session.rarity}" +
                    (f"\n💠 **Sub-Rarity:** {session.subrarity}" if session.subrarity else "") +
                    f"\n\n🆔 **Character ID:** `{character_id}`\n"
                    f"📸 **Media:** Uploaded to Catbox\n"
                    f"📢 **Posted to:** @capture_database\n\n"
                    f"**Note:** Character IDs increase automatically — next one will be {character_id + 1}"
                )
                
                await callback_query.message.edit_text(success_text)
                
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
            session.state = CharacterStates.WAITING_CHAR_NAME.value
            await db.save_session(session)
            
            await callback_query.message.reply_text(
                "💬 **Please reply to this message with the character name:**\n\n"
                "Please use the format: `Name [emoji]` if rarity has one\n"
                "Example: `Ichigo Kurosaki 🗡️`",
                reply_markup=helpers.force_reply()
            )
        
        elif back_to == "rarity" and session:
            session.state = CharacterStates.WAITING_RARITY.value
            await db.save_session(session)
            await callback_query.message.edit_text(
                "🎯 **Select the character's rarity:**",
                reply_markup=keyboards.get_rarity_keyboard()
            )
        
        elif back_to == "subrarity" and session:
            session.state = CharacterStates.WAITING_SUBRARITY.value
            await db.save_session(session)
            
            if "Limited Edition" in session.rarity:
                keyboard = keyboards.get_limited_subtypes_keyboard()
                await callback_query.message.edit_text(
                    f"🎯 **Select Limited Edition Subtype**\n\n"
                    f"Rarity: {session.rarity}",
                    reply_markup=keyboard
                )
        
        await callback_query.answer()

# ==================== CHARACTER MANAGEMENT HANDLERS ====================
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
            
            deleted = await db.delete_character(character_id)
            
            if deleted:
                await message.reply_text("✅ Character deleted successfully!")
                logger.info(f"Character {character_id} deleted by user {message.from_user.id}")
            else:
                await message.reply_text("❌ Failed to delete character!")
                
        except ValueError:
            await message.reply_text("❌ Invalid character ID.")
        except Exception as e:
            logger.error(f"Error in delchar command: {e}")
            await message.reply_text("❌ Error deleting character.")
    
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
                    "`/uchar 1 Zoro OnePiece 5 valentine`\n\n"
                    "**Rarity Numbers (1-14):**\n"
                    "1: Common, 2: Uncommon, 3: Rare, 4: Legendary\n"
                    "5: Limited Edition, 6: Premium, 7: Exotic, 8: Animated\n"
                    "9: Thundra, 10: Galvoria, 11: Neon, 12: Supreme\n"
                    "13: Crystal, 14: Celebrity"
                )
                return
            
            character_id = int(args[1])
            char_name = args[2]
            anime_name = args[3]
            rarity_no = int(args[4])
            subrarity = args[5] if len(args) > 5 else None
            
            if rarity_no not in config.RARITY_MAP:
                await message.reply_text(f"❌ Invalid rarity number! Must be 1-{len(config.RARITY_MAP)}")
                return
            
            character = await db.get_character_by_id(character_id)
            if not character:
                await message.reply_text("❌ Character not found!")
                return
            
            rarity_name = config.RARITY_MAP[rarity_no]
            
            # Handle subrarity for Limited Edition (rarity 5)
            if rarity_no in config.RARITIES_WITH_SUBTYPES and subrarity:
                if rarity_no == 5:  # Limited Edition
                    if subrarity not in config.LIMITED_SUBTYPES:
                        await message.reply_text("❌ Invalid Limited Edition subtype!")
                        return
                    subrarity_name = config.LIMITED_SUBTYPES[subrarity]
                else:
                    subrarity_name = None
            else:
                subrarity_name = None
            
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
            await message.reply_text("❌ Invalid input.")
        except Exception as e:
            logger.error(f"Error in uchar command: {e}")
            await message.reply_text("❌ Error updating character.")
    
    async def uimage_command(self, client: Client, message: Message):
        """Handle /uimage command - update character media"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
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
            
            character = await db.get_character_by_id(character_id)
            if not character:
                await message.reply_text("❌ Character not found!")
                return
            
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
            
            updated = await db.update_character_media(character_id, media_url, media_type)
            
            if updated:
                await update_status("✅ Character media updated successfully!")
                logger.info(f"Character {character_id} media updated by user {message.from_user.id}")
            else:
                await update_status("❌ Failed to update character media!")
                
        except ValueError:
            await message.reply_text("❌ Invalid character ID.")
        except Exception as e:
            logger.error(f"Error in uimage command: {e}")
            await message.reply_text("❌ Error updating character media.")
    
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
            await message.reply_text("❌ Invalid character ID.")
        except Exception as e:
            logger.error(f"Error in uinfo command: {e}")
            await message.reply_text("❌ Error fetching character info.")

# ==================== MASS UPLOAD HANDLERS ====================
class MassUploadHandlers:
    """Handlers for mass character upload functionality"""
    
    def __init__(self, client: Client):
        self.client = client
    
    async def setchar_command(self, client: Client, message: Message):
        """Handle /setchar command - start mass upload session"""
        if not await helpers.is_sudo_user(message.from_user.id):
            await message.reply_text("❌ You are not authorized to use this bot.")
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
            
            char_name = args[1].replace('_', ' ').replace('"', '')
            anime_name = ' '.join(args[2:]).replace('_', ' ').replace('"', '')
            
            existing_session = await db.get_mass_upload_session(message.from_user.id)
            if existing_session:
                await message.reply_text(
                    "⚠️ **You already have an active mass upload session!**\n\n"
                    f"**Current Session:** {existing_session.char_name} ({existing_session.anime_name})\n\n"
                    "Use `/donechar` to end current session or `/currentchar` to view status."
                )
                return
            
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
                "• Example: `/madd 4` (Legendary rarity)\n"
                "• Example: `/madd 5 valentine` (Valentine Limited Edition)\n\n"
                "**Available Commands:**\n"
                "• `/currentchar` - Show session status\n"
                "• `/undochar` - Remove last upload\n" 
                "• `/bulkstatus` - Show upload statistics\n"
                "• `/donechar` - End session\n\n"
                "**Auto Emoji System:** Subrarities automatically add emojis to character names!\n"
                "**Fast Upload:** Catbox uploads now take 5-8 seconds!\n"
                "**Log Channel:** All characters sent to @capture_database"
            )
            
        except Exception as e:
            logger.error(f"Error in setchar command: {e}")
            await message.reply_text("❌ Error starting mass upload session.")
    
    async def madd_command(self, client: Client, message: Message):
        """Handle /madd command in mass upload context"""
        if not await helpers.is_sudo_user(message.from_user.id):
            await message.reply_text("❌ You are not authorized to use this bot.")
            return
            
        try:
            session = await db.get_mass_upload_session(message.from_user.id)
            if not session:
                await message.reply_text(
                    "❌ **No active mass upload session!**\n\n"
                    "Start a session first with `/setchar <name> <anime>`"
                )
                return
            
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
                    "• `/madd 4` - Legendary rarity\n"
                    "• `/madd 5 valentine` - Valentine Limited Edition\n"
                    "• `/madd 6` - Premium rarity"
                )
                return
            
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "❌ **Invalid syntax!**\n\n"
                    "**Usage:** `/madd <rarity> [subrarity]`\n"
                    "**Example:** `/madd 5 valentine`"
                )
                return
            
            try:
                rarity_num = int(args[1])
                if rarity_num not in config.RARITY_MAP:
                    await message.reply_text(f"❌ Invalid rarity number! Available: 1-{len(config.RARITY_MAP)}")
                    return
                
                rarity_name = config.RARITY_MAP[rarity_num]
                subrarity_key = args[2].lower() if len(args) > 2 else None
                subrarity_name = None
                emoji = None
                
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
                    else:
                        await message.reply_text("❌ Subrarity only available for Limited Edition (rarity 5)")
                        return
                
                final_char_name = session.char_name
                if emoji:
                    final_char_name = f"{session.char_name} [{emoji}]"
                
            except ValueError:
                await message.reply_text("❌ Rarity must be a number!")
                return
            
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
            
            try:
                inserted_id = await db.insert_character(character)
                
                session.add_character({
                    "character_id": character_id,
                    "rarity": rarity_name,
                    "subrarity": subrarity_name,
                    "media_url": media_url,
                    "media_type": media_type,
                    "timestamp": character.timestamp
                })
                await db.save_mass_upload_session(session)
                
                username = message.from_user.username or message.from_user.first_name or "Unknown"
                await helpers.send_to_log_channels(
                    client, character.to_dict(), username, message.from_user.id, db
                )
                
                success_text = (
                    f"✅ **Character #{character_id} Added!**\n\n"
                    f"👤 **Name:** {final_char_name}\n"
                    f"🎞️ **Anime:** {session.anime_name}\n"
                    f"🏅 **Rarity:** {rarity_name}\n"
                )
                
                if subrarity_name:
                    success_text += f"💠 **Sub-Rarity:** {subrarity_name}\n"
                
                success_text += (
                    f"📸 **Media:** Uploaded successfully\n"
                    f"📢 **Posted to:** @capture_database\n\n"
                    f"**Session Progress:** {session.get_character_count()} characters uploaded\n"
                    f"**Next ID:** {character_id + 1}"
                )
                
                await update_status(success_text)
                
            except Exception as e:
                logger.error(f"Error saving character in mass upload: {e}")
                await update_status("❌ Error saving character to database!")
                
        except Exception as e:
            logger.error(f"Error in mass upload madd: {e}")
            await message.reply_text("❌ Error processing character upload.")
    
    async def donechar_command(self, client: Client, message: Message):
        """Handle /donechar command - end mass upload session"""
        try:
            session = await db.get_mass_upload_session(message.from_user.id)
            if not session:
                await message.reply_text("❌ No active mass upload session found!")
                return
            
            total_chars = session.get_character_count()
            
            await db.delete_mass_upload_session(message.from_user.id)
            
            summary_text = (
                f"🎉 **Mass Upload Session Complete!**\n\n"
                f"👤 **Character:** {session.char_name}\n"
                f"🎞️ **Anime:** {session.anime_name}\n"
                f"📊 **Total Uploaded:** {total_chars} characters\n"
                f"⏱️ **Session Duration:** {helpers.format_session_duration(session.created_at)}\n\n"
                "All characters have been saved to the database and posted to @capture_database."
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
            
            session_info = session.get_session_summary()
            
            if session.uploaded_characters:
                session_info += "\n\n**📋 Uploaded Characters:**\n"
                for i, char in enumerate(session.uploaded_characters[-10:], 1):
                    char_text = f"`{char['character_id']}` - {char['rarity']}"
                    if char.get('subrarity'):
                        char_text += f" ({char['subrarity']})"
                    session_info += f"{i}. {char_text}\n"
                
                if len(session.uploaded_characters) > 10:
                    session_info += f"\n... and {len(session.uploaded_characters) - 10} more"
            
            session_info += "\n\n**📢 All characters posted to @capture_database**"
            
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
            
            last_char = session.remove_last_character()
            if not last_char:
                await message.reply_text("❌ No characters to undo!")
                return
            
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
            
            total_chars = session.get_character_count()
            rarity_count = {}
            
            for char in session.uploaded_characters:
                rarity = char['rarity']
                rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
            
            status_text = (
                f"📊 **Mass Upload Statistics**\n\n"
                f"👤 **Character:** {session.char_name}\n"
                f"🎞️ **Anime:** {session.anime_name}\n"
                f"📈 **Total Uploaded:** {total_chars} characters\n"
                f"⏱️ **Session Active:** {helpers.format_session_duration(session.created_at)}\n"
                f"📢 **Posted to:** @capture_database\n\n"
            )
            
            if rarity_count:
                status_text += "**📋 Rarity Breakdown:**\n"
                for rarity, count in rarity_count.items():
                    status_text += f"• {rarity}: {count}\n"
            
            await message.reply_text(status_text)
            
        except Exception as e:
            logger.error(f"Error in bulkstatus command: {e}")
            await message.reply_text("❌ Error fetching bulk upload statistics.")

# ==================== SUDO HANDLERS ====================
class SudoHandlers:
    """Handlers for sudo user management"""
    
    def __init__(self, client: Client):
        self.client = client
    
    async def addsudo_command(self, client: Client, message: Message):
        """Handle /addsudo command - add sudo user (owner only)"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "👑 **Add Sudo User**\n\n"
                    "**Usage:**\n"
                    "`/addsudo <user_id>`\n\n"
                    "**Example:**\n"
                    "`/addsudo 123456789`\n\n"
                    "**Note:** You can get user ID by forwarding user's message to @userinfobot"
                )
                return
            
            user_id = int(args[1])
            
            if await db.is_sudo_user(user_id):
                await message.reply_text("❌ User is already a sudo user!")
                return
            
            success = await db.add_sudo_user(user_id)
            
            if success:
                try:
                    username = await helpers.get_username_from_id(client, user_id)
                    await message.reply_text(f"✅ **Sudo user added successfully!**\n\nUser: {username}\nID: `{user_id}`")
                except:
                    await message.reply_text(f"✅ **Sudo user added successfully!**\n\nUser ID: `{user_id}`")
                
                logger.info(f"Sudo user {user_id} added by {message.from_user.id}")
            else:
                await message.reply_text("❌ Failed to add sudo user!")
                
        except ValueError:
            await message.reply_text("❌ Invalid user ID.")
        except Exception as e:
            logger.error(f"Error in addsudo command: {e}")
            await message.reply_text("❌ Error adding sudo user.")
    
    async def rmsudo_command(self, client: Client, message: Message):
        """Handle /rmsudo command - remove sudo user (owner only)"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "🗑️ **Remove Sudo User**\n\n"
                    "**Usage:**\n"
                    "`/rmsudo <user_id>`\n\n"
                    "**Example:**\n"
                    "`/rmsudo 123456789`"
                )
                return
            
            user_id = int(args[1])
            
            if not await db.is_sudo_user(user_id):
                await message.reply_text("❌ User is not a sudo user!")
                return
            
            if user_id == config.OWNER_ID:
                await message.reply_text("❌ Cannot remove bot owner from sudo users!")
                return
            
            success = await db.remove_sudo_user(user_id)
            
            if success:
                try:
                    username = await helpers.get_username_from_id(client, user_id)
                    await message.reply_text(f"✅ **Sudo user removed successfully!**\n\nUser: {username}\nID: `{user_id}`")
                except:
                    await message.reply_text(f"✅ **Sudo user removed successfully!**\n\nUser ID: `{user_id}`")
                
                logger.info(f"Sudo user {user_id} removed by {message.from_user.id}")
            else:
                await message.reply_text("❌ Failed to remove sudo user!")
                
        except ValueError:
            await message.reply_text("❌ Invalid user ID.")
        except Exception as e:
            logger.error(f"Error in rmsudo command: {e}")
            await message.reply_text("❌ Error removing sudo user.")
    
    async def staff_command(self, client: Client, message: Message):
        """Handle /staff command - show all sudo users"""
        if not await helpers.is_sudo_user(message.from_user.id):
            await message.reply_text("❌ You are not authorized to view staff list.")
            return
        
        try:
            sudo_users = await db.get_sudo_users()
            
            staff_text = "👑 **Bot Staff Members**\n\n"
            
            owner_username = await helpers.get_username_from_id(client, config.OWNER_ID)
            staff_text += f"👑 **Owner:** {owner_username} (`{config.OWNER_ID}`)\n\n"
            
            if sudo_users:
                staff_text += "**Sudo Users:**\n"
                for user_id in sudo_users:
                    if user_id != config.OWNER_ID:
                        username = await helpers.get_username_from_id(client, user_id)
                        staff_text += f"• {username} (`{user_id}`)\n"
            else:
                staff_text += "**Sudo Users:** None\n"
            
            staff_text += f"\n**Total Staff:** {len(sudo_users) + 1} users"
            
            await message.reply_text(staff_text)
            
        except Exception as e:
            logger.error(f"Error in staff command: {e}")
            await message.reply_text("❌ Error fetching staff list.")

# ==================== MAIN BOT CLASS ====================
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
        # Initialize handler classes
        command_handlers = CommandHandlers(self.client)
        callback_handlers = CallbackHandlers(self.client)
        char_management_handlers = CharacterManagementHandlers(self.client)
        mass_upload_handlers = MassUploadHandlers(self.client)
        sudo_handlers = SudoHandlers(self.client)
        
        # Register command handlers
        self.client.on_message(filters.command("start"))(command_handlers.start_command)
        self.client.on_message(filters.command("addchar"))(command_handlers.addchar_command)
        self.client.on_message(filters.command("cs"))(command_handlers.cs_command)
        self.client.on_message(filters.command(["c", "check"]))(command_handlers.check_command)
        self.client.on_message(filters.command("status"))(command_handlers.status_command)
        self.client.on_message(filters.command("help"))(command_handlers.help_command)
        self.client.on_message(filters.command("setlog1"))(command_handlers.setlog1_command)
        self.client.on_message(filters.command("setlog2"))(command_handlers.setlog2_command)
        self.client.on_message(filters.command("showlogs"))(command_handlers.showlogs_command)
        
        # Register character management handlers
        self.client.on_message(filters.command("delchar"))(char_management_handlers.delchar_command)
        self.client.on_message(filters.command("uchar"))(char_management_handlers.uchar_command)
        self.client.on_message(filters.command("uimage"))(char_management_handlers.uimage_command)
        self.client.on_message(filters.command("uinfo"))(char_management_handlers.uinfo_command)
        
        # Register mass upload handlers
        self.client.on_message(filters.command("setchar"))(mass_upload_handlers.setchar_command)
        self.client.on_message(filters.command("madd"))(mass_upload_handlers.madd_command)
        self.client.on_message(filters.command("donechar"))(mass_upload_handlers.donechar_command)
        self.client.on_message(filters.command("currentchar"))(mass_upload_handlers.currentchar_command)
        self.client.on_message(filters.command("undochar"))(mass_upload_handlers.undochar_command)
        self.client.on_message(filters.command("bulkstatus"))(mass_upload_handlers.bulkstatus_command)
        
        # Register sudo handlers
        self.client.on_message(filters.command("addsudo"))(sudo_handlers.addsudo_command)
        self.client.on_message(filters.command("rmsudo"))(sudo_handlers.rmsudo_command)
        self.client.on_message(filters.command("staff"))(sudo_handlers.staff_command)
        
        # Register callback handler
        @self.client.on_callback_query()
        async def handle_all_callbacks(client: Client, callback_query: CallbackQuery):
            data = callback_query.data
            
            try:
                if data in ["add_char", "status", "help"]:
                    await callback_handlers.handle_main_menu(client, callback_query)
                elif data.startswith("rarity_"):
                    await callback_handlers.handle_rarity_selection(client, callback_query)
                elif data.startswith("subrarity_"):
                    await callback_handlers.handle_subrarity_selection(client, callback_query)
                elif data in ["confirm_upload", "reject_upload"]:
                    await callback_handlers.handle_confirmation(client, callback_query)
                elif data.startswith("back_"):
                    await callback_handlers.handle_back_navigation(client, callback_query)
                    
            except Exception as e:
                logger.error(f"Error handling callback {data}: {e}")
                await callback_query.answer("An error occurred. Please try again.", show_alert=True)
        
        # Register message handlers for character upload flow
        self.client.on_message(filters.private & (filters.text | filters.media | filters.document | filters.audio))(self._handle_message)
    
    async def _handle_message(self, client: Client, message: Message):
        """Handle non-command messages for character upload flow"""
        if message.text and message.text.startswith('/'):
            return
        
        user_id = message.from_user.id
        
        if not await helpers.is_sudo_user(user_id):
            await message.reply_text("❌ You are not authorized to use this bot. Contact admin.")
            return
        
        mass_session = await db.get_mass_upload_session(user_id)
        if mass_session:
            return
            
        session = await db.get_session(user_id)
        
        if not session:
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
        """Handle character name input"""
        if not message.text:
            await message.reply_text("❌ Please send the character name as text.")
            return
        
        session.char_name = message.text.strip()
        session.state = CharacterStates.WAITING_ANIME_NAME.value
        await db.save_session(session)
        
        logger.info(f"Character name saved for user {session.user_id}: {session.char_name}")
        
        await message.reply_text(
            "✅ **Character name saved!**\n\n"
            "💬 **Step 2: What anime does this character belong to?**\n\n"
            "Please send the anime name:",
            reply_markup=helpers.force_reply()
        )
    
    async def _handle_anime_name(self, client: Client, message: Message, session: UserSession):
        """Handle anime name input"""
        if not message.text:
            await message.reply_text("❌ Please send the anime name as text.")
            return
        
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
        """Handle media upload"""
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
                "**Upload Service:** Catbox.moe (Fast - 5-8 seconds)\n\n"
                "**Note:** Character will be posted to @capture_database"
            )
            return
        
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
        
        status_msg = await message.reply_text("🔄 Starting fast media upload...")
        
        async def update_status(text: str):
            try:
                await status_msg.edit_text(text)
            except Exception as e:
                logger.warning(f"Failed to update status: {e}")
        
        try:
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
            
            session.media_url = media_url
            session.media_type = media_type
            session.state = CharacterStates.WAITING_CONFIRMATION.value
            await db.save_session(session)
            
            preview = helpers.format_character_preview(session)
            await update_status(
                f"{preview}\n\n"
                "✅ **Media uploaded successfully to Catbox!**\n\n"
                "**Step 6: Please confirm to add this character to the database:**\n\n"
                "**Note:** Character will be posted to @capture_database"
            )
            
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
            await db.connect()
            logger.info("Database connection established")
            
            await self.client.start()
            logger.info("Bot started successfully")
            
            me = await self.client.get_me()
            logger.info(f"Logged in as @{me.username} (ID: {me.id})")
            
            # Show startup message
            logger.info(f"Default log channel: {config.DEFAULT_LOG_CHANNEL}")
            logger.info(f"Using rarity system with {len(config.RARITY_MAP)} rarities")
            
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
    asyncio.run(main())
