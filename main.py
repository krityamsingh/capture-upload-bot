# ==================== CHARACTER BOT WITH RECYCLE BIN SYSTEM ====================
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
    InlineKeyboardMarkup, CallbackQuery
)
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
class Config:
    """Configuration class for bot settings"""
    
    # Get environment variables
    API_ID = int(os.getenv("API_ID", 26676741))
    API_HASH = os.getenv("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8496337458:AAF7ORldWpN-C6hpzSDt1bPCOeGVxfbU4qg")
    
    # MongoDB configuration
    MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://erenxironman09:erenxironman09@catcherbot.koejwre.mongodb.net/?appName=catcherbot")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "catcherbot")
    
    # Bot owner ID
    OWNER_ID = int(os.getenv("OWNER_ID", 7878477646))
    
    # Log channel
    LOG_CHANNEL = "@capture_database"
    
    # Upload settings
    UPLOAD_TIMEOUT = 60
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Rarity system
    RARITIES = {
        1: {"name": "🌸 Blossom", "subs": [], "emoji": "🌸"},
        2: {"name": "✨ Starlit", "subs": [], "emoji": "✨"},
        3: {
            "name": "🩸 Crimson",
            "subs": ["🩸 Bloodline", "🕯️ Cursed", "🌑 Shadowborn"],
            "emoji": "🩸"
        },
        4: {
            "name": "🌘 Eclipse",
            "subs": ["🌘 Lunar", "☀️ Solar", "🌓 Twilight", "🕳️ Void"],
            "emoji": "🌘"
        },
        5: {
            "name": "🌌 Celestia",
            "subs": ["🌌 Astral", "👼 Seraph", "🔮 Arcane", "🧿 Divine Relic"],
            "emoji": "🌌"
        },
        6: {
            "name": "🪽 Ascended",
            "subs": ["🪽 Mythborn", "👑 Sovereign", "👁️ Omniscient"],
            "emoji": "🪽"
        },
        7: {
            "name": "🧬 One-of-One",
            "subs": [],
            "emoji": "🧬"
        }
    }
    
    # Items per page for pagination
    ITEMS_PER_PAGE = 10
    
    # Recycle bin settings
    RECYCLE_BIN_MAX_DAYS = 30  # Keep deleted characters for 30 days

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
        timestamp: Optional[datetime] = None,
        deleted_at: Optional[datetime] = None,
        deleted_by: Optional[int] = None,
        deleted_reason: Optional[str] = None
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
        self.deleted_at = deleted_at
        self.deleted_by = deleted_by
        self.deleted_reason = deleted_reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character object to dictionary for MongoDB"""
        data = {
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
        
        if self.deleted_at:
            data["deleted_at"] = self.deleted_at
        if self.deleted_by:
            data["deleted_by"] = self.deleted_by
        if self.deleted_reason:
            data["deleted_reason"] = self.deleted_reason
        
        return data
    
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
            timestamp=data.get("timestamp"),
            deleted_at=data.get("deleted_at"),
            deleted_by=data.get("deleted_by"),
            deleted_reason=data.get("deleted_reason")
        )

# ==================== DATABASE ====================
class MongoDB:
    """MongoDB database operations handler with recycle bin"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.characters = None
        self.deleted_characters = None  # New collection for recycle bin
        self.counters = None
        self.sudo_users = None
    
    async def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(config.MONGO_URI)
            self.db = self.client[config.DATABASE_NAME]
            self.characters = self.db.characters
            self.deleted_characters = self.db.deleted_characters  # Recycle bin
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
            
            # Indexes for deleted characters
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.create_index("character_id")
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.create_index("deleted_at")
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.create_index("deleted_by")
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
        """Get total number of active characters in database"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.characters.count_documents({})
        )
    
    async def get_user_characters(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active characters uploaded by a user"""
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
        """Get active character by character ID"""
        try:
            character = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.find_one({"character_id": character_id})
            )
            return character
        except PyMongoError as e:
            logger.error(f"Error fetching character by ID: {e}")
            return None
    
    async def get_deleted_character_by_id(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Get deleted character by character ID"""
        try:
            character = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.find_one({"character_id": character_id})
            )
            return character
        except PyMongoError as e:
            logger.error(f"Error fetching deleted character by ID: {e}")
            return None
    
    async def soft_delete_character(self, character_id: int, deleted_by: int, reason: str = None) -> bool:
        """Move character to recycle bin (soft delete)"""
        try:
            # Get character from active collection
            character = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.find_one({"character_id": character_id})
            )
            
            if not character:
                return False
            
            # Add deletion metadata
            character["deleted_at"] = datetime.utcnow()
            character["deleted_by"] = deleted_by
            if reason:
                character["deleted_reason"] = reason
            
            # Insert into deleted collection
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.insert_one(character)
            )
            
            # Remove from active collection
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.delete_one({"character_id": character_id})
            )
            
            return result.deleted_count > 0
            
        except PyMongoError as e:
            logger.error(f"Error soft deleting character: {e}")
            return False
    
    async def restore_character(self, character_id: int) -> bool:
        """Restore character from recycle bin"""
        try:
            # Get character from deleted collection
            character = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.find_one({"character_id": character_id})
            )
            
            if not character:
                return False
            
            # Remove deletion metadata
            character.pop("deleted_at", None)
            character.pop("deleted_by", None)
            character.pop("deleted_reason", None)
            
            # Insert back into active collection
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.insert_one(character)
            )
            
            # Remove from deleted collection
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.delete_one({"character_id": character_id})
            )
            
            return result.deleted_count > 0
            
        except PyMongoError as e:
            logger.error(f"Error restoring character: {e}")
            return False
    
    async def permanent_delete_character(self, character_id: int) -> bool:
        """Permanently delete character from recycle bin"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.delete_one({"character_id": character_id})
            )
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error permanently deleting character: {e}")
            return False
    
    async def cleanup_old_deleted(self) -> int:
        """Clean up old deleted characters (older than RECYCLE_BIN_MAX_DAYS)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=config.RECYCLE_BIN_MAX_DAYS)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.delete_many({"deleted_at": {"$lt": cutoff_date}})
            )
            return result.deleted_count
        except PyMongoError as e:
            logger.error(f"Error cleaning up old deleted characters: {e}")
            return 0
    
    async def get_deleted_characters_count(self) -> int:
        """Get total number of deleted characters"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.deleted_characters.count_documents({})
        )
    
    async def get_deleted_characters(self, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get deleted characters with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            # Get deleted characters for current page
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.deleted_characters.find({})
                             .sort("deleted_at", -1)
                             .skip(skip)
                             .limit(config.ITEMS_PER_PAGE))
            )
            
            # Get total count
            total_count = await self.get_deleted_characters_count()
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching deleted characters: {e}")
            return [], 0
    
    async def get_user_deleted_characters(self, user_id: int, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get deleted characters uploaded by a user with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            # Get deleted characters for current page
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.deleted_characters.find({"added_by": user_id})
                             .sort("deleted_at", -1)
                             .skip(skip)
                             .limit(config.ITEMS_PER_PAGE))
            )
            
            # Get total count
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.count_documents({"added_by": user_id})
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching user deleted characters: {e}")
            return [], 0
    
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
        """Search active characters by name or anime"""
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
    
    async def search_deleted_characters(self, query: str, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Search deleted characters by name or anime with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            search_filter = {
                "$or": [
                    {"char_name": {"$regex": query, "$options": "i"}},
                    {"anime_name": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Get deleted characters for current page
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.deleted_characters.find(search_filter)
                             .sort("deleted_at", -1)
                             .skip(skip)
                             .limit(config.ITEMS_PER_PAGE))
            )
            
            # Get total count
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.count_documents(search_filter)
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error searching deleted characters: {e}")
            return [], 0
    
    async def get_characters_by_rarity(self, rarity_name: str, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get active characters by rarity with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            # Get characters for current page
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find(
                    {"rarity": rarity_name}
                ).skip(skip).limit(config.ITEMS_PER_PAGE))
            )
            
            # Get total count
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.count_documents({"rarity": rarity_name})
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching characters by rarity: {e}")
            return [], 0
    
    async def get_all_characters_paginated(self, page: int = 0, sort_by: str = "character_id") -> tuple[List[Dict[str, Any]], int]:
        """Get all active characters with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            # Get characters for current page
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({}).sort(sort_by, 1).skip(skip).limit(config.ITEMS_PER_PAGE))
            )
            
            # Get total count
            total_count = await self.get_character_count()
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching paginated characters: {e}")
            return [], 0
    
    async def search_characters_paginated(self, query: str, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Search active characters by name or anime with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            search_filter = {
                "$or": [
                    {"char_name": {"$regex": query, "$options": "i"}},
                    {"anime_name": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Get characters for current page
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find(search_filter).skip(skip).limit(config.ITEMS_PER_PAGE))
            )
            
            # Get total count
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.count_documents(search_filter)
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error searching characters: {e}")
            return [], 0
    
    async def get_rarity_stats(self) -> Dict[str, int]:
        """Get count of active characters per rarity"""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$rarity",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.aggregate(pipeline))
            )
            
            stats = {}
            for result in results:
                stats[result["_id"]] = result["count"]
            
            return stats
            
        except PyMongoError as e:
            logger.error(f"Error getting rarity stats: {e}")
            return {}
    
    async def get_top_uploaders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top uploaders by character count"""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$added_by",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.aggregate(pipeline))
            )
            
            return results
            
        except PyMongoError as e:
            logger.error(f"Error getting top uploaders: {e}")
            return []
    
    async def get_user_characters_paginated(self, user_id: int, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get all active characters uploaded by a user with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            # Get characters for current page
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({"added_by": user_id}).skip(skip).limit(config.ITEMS_PER_PAGE))
            )
            
            # Get total count
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.count_documents({"added_by": user_id})
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching user characters: {e}")
            return [], 0
    
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

from datetime import timedelta

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
        info = f"👤 **Name:** {character_data.get('char_name', 'N/A')}\n"
        info += f"🎞️ **Anime:** {character_data.get('anime_name', 'N/A')}\n"
        info += f"🏅 **Rarity:** {character_data.get('rarity', 'N/A')}\n"
        
        if character_data.get('subrarity'):
            info += f"💠 **Sub-Rarity:** {character_data.get('subrarity')}\n"
        
        info += f"🆔 **ID:** `{character_data.get('character_id', 'N/A')}`\n"
        
        if character_data.get('timestamp'):
            timestamp = character_data['timestamp']
            if isinstance(timestamp, datetime):
                info += f"📅 **Added:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if character_data.get('added_by'):
            info += f"👤 **Uploaded by:** {character_data['added_by']}\n"
        
        if character_data.get('media_url'):
            info += f"🔗 **Media:** [View]({character_data['media_url']})\n"
        
        return info
    
    @staticmethod
    def format_deleted_character_info(character_data: Dict[str, Any]) -> str:
        """Format deleted character data for display"""
        info = f"🗑️ **Deleted Character**\n\n"
        info += f"👤 **Name:** {character_data.get('char_name', 'N/A')}\n"
        info += f"🎞️ **Anime:** {character_data.get('anime_name', 'N/A')}\n"
        info += f"🏅 **Rarity:** {character_data.get('rarity', 'N/A')}\n"
        
        if character_data.get('subrarity'):
            info += f"💠 **Sub-Rarity:** {character_data.get('subrarity')}\n"
        
        info += f"🆔 **ID:** `{character_data.get('character_id', 'N/A')}`\n"
        
        if character_data.get('timestamp'):
            timestamp = character_data['timestamp']
            if isinstance(timestamp, datetime):
                info += f"📅 **Originally Added:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if character_data.get('deleted_at'):
            deleted_at = character_data['deleted_at']
            if isinstance(deleted_at, datetime):
                info += f"🗑️ **Deleted On:** {deleted_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                # Calculate days ago
                days_ago = (datetime.utcnow() - deleted_at).days
                info += f"⏳ **Deleted {days_ago} days ago**\n"
        
        if character_data.get('deleted_by'):
            info += f"👤 **Deleted by:** {character_data['deleted_by']}\n"
        
        if character_data.get('deleted_reason'):
            info += f"📝 **Reason:** {character_data['deleted_reason']}\n"
        
        if character_data.get('added_by'):
            info += f"📤 **Originally uploaded by:** {character_data['added_by']}\n"
        
        if character_data.get('media_url'):
            info += f"🔗 **Media:** [View]({character_data['media_url']})\n"
        
        return info
    
    @staticmethod
    def get_rarity_emoji(rarity_name: str) -> str:
        """Get emoji for rarity name"""
        for rarity_num, rarity_data in config.RARITIES.items():
            if rarity_data["name"] == rarity_name:
                return rarity_data["emoji"]
        return "⚪"
    
    @staticmethod
    def get_rarity_number(rarity_name: str) -> Optional[int]:
        """Get rarity number from rarity name"""
        for rarity_num, rarity_data in config.RARITIES.items():
            if rarity_data["name"] == rarity_name:
                return rarity_num
        return None
    
    @staticmethod
    def create_pagination_keyboard(current_page: int, total_pages: int, callback_prefix: str, extra_data: str = "") -> InlineKeyboardMarkup:
        """Create pagination keyboard"""
        keyboard = []
        
        # Previous button
        if current_page > 0:
            keyboard.append(
                InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=f"{callback_prefix}_page_{current_page - 1}_{extra_data}"
                )
            )
        
        # Page info
        keyboard.append(
            InlineKeyboardButton(
                f"📄 {current_page + 1}/{total_pages}",
                callback_data="noop"
            )
        )
        
        # Next button
        if current_page < total_pages - 1:
            keyboard.append(
                InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"{callback_prefix}_page_{current_page + 1}_{extra_data}"
                )
            )
        
        return InlineKeyboardMarkup([keyboard])
    
    @staticmethod
    def create_rarity_keyboard(current_view: str = "main") -> InlineKeyboardMarkup:
        """Create keyboard with all rarity options"""
        keyboard = []
        
        # Add main rarities
        for rarity_num, rarity_data in config.RARITIES.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{rarity_data['emoji']} {rarity_data['name']}",
                    callback_data=f"rarity_{rarity_num}_{current_view}"
                )
            ])
        
        # Add all characters option
        keyboard.append([
            InlineKeyboardButton(
                "📊 All Characters",
                callback_data=f"view_all_{current_view}"
            )
        ])
        
        # Add recycle bin option
        keyboard.append([
            InlineKeyboardButton(
                "🗑️ Recycle Bin",
                callback_data=f"deleted_list_0_{current_view}"
            )
        ])
        
        # Add search option
        keyboard.append([
            InlineKeyboardButton(
                "🔍 Search Characters",
                callback_data=f"search_{current_view}"
            )
        ])
        
        # Add stats option
        keyboard.append([
            InlineKeyboardButton(
                "📈 Statistics",
                callback_data=f"stats_{current_view}"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_subrarity_keyboard(rarity_num: int, current_view: str = "main") -> InlineKeyboardMarkup:
        """Create keyboard with sub-rarities for a specific rarity"""
        keyboard = []
        
        rarity_data = config.RARITIES.get(rarity_num, {})
        if not rarity_data:
            return InlineKeyboardMarkup([])
        
        # Add "All" option for this rarity
        keyboard.append([
            InlineKeyboardButton(
                f"📂 All {rarity_data['name']} Characters",
                callback_data=f"view_rarity_{rarity_num}_page_0_{current_view}"
            )
        ])
        
        # Add sub-rarities if they exist
        subs = rarity_data.get("subs", [])
        if subs:
            keyboard.append([
                InlineKeyboardButton(
                    "📁 Sub-Rarities:",
                    callback_data="noop"
                )
            ])
            
            for sub in subs:
                sub_key = sub.replace(' ', '_').replace('️', '')  # Remove emoji variation selector
                keyboard.append([
                    InlineKeyboardButton(
                        f"   {sub}",
                        callback_data=f"view_sub_{rarity_num}_{sub_key}_page_0_{current_view}"
                    )
                ])
        
        # Add back button
        keyboard.append([
            InlineKeyboardButton(
                "🔙 Back to Rarities",
                callback_data=f"menu_{current_view}"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def format_character_list(characters: List[Dict[str, Any]], page: int, total_count: int, title: str = "Characters") -> str:
        """Format a list of characters for display"""
        if not characters:
            return f"❌ No {title.lower()} found."
        
        start_num = page * config.ITEMS_PER_PAGE + 1
        end_num = min(start_num + len(characters) - 1, total_count)
        
        message = f"**{title}**\n"
        message += f"📊 **Showing {start_num}-{end_num} of {total_count}**\n\n"
        
        for i, char in enumerate(characters, start=start_num):
            emoji = Helpers.get_rarity_emoji(char.get('rarity', ''))
            subrarity_text = f" ({char.get('subrarity', '')})" if char.get('subrarity') else ""
            message += f"{i}. **{char.get('char_name', 'Unknown')}** - {char.get('anime_name', 'Unknown')}\n"
            message += f"   {emoji} {char.get('rarity', 'Unknown')}{subrarity_text} | ID: `{char.get('character_id', 'N/A')}`\n\n"
        
        return message
    
    @staticmethod
    def format_deleted_character_list(characters: List[Dict[str, Any]], page: int, total_count: int) -> str:
        """Format a list of deleted characters for display"""
        if not characters:
            return "🗑️ **Recycle Bin is empty!**\n\nNo deleted characters found."
        
        start_num = page * config.ITEMS_PER_PAGE + 1
        end_num = min(start_num + len(characters) - 1, total_count)
        
        message = f"🗑️ **Recycle Bin (Deleted Characters)**\n"
        message += f"📊 **Showing {start_num}-{end_num} of {total_count}**\n\n"
        
        for i, char in enumerate(characters, start=start_num):
            emoji = Helpers.get_rarity_emoji(char.get('rarity', ''))
            subrarity_text = f" ({char.get('subrarity', '')})" if char.get('subrarity') else ""
            
            # Calculate days since deletion
            days_ago = 0
            if char.get('deleted_at') and isinstance(char['deleted_at'], datetime):
                days_ago = (datetime.utcnow() - char['deleted_at']).days
            
            message += f"{i}. **{char.get('char_name', 'Unknown')}** - {char.get('anime_name', 'Unknown')}\n"
            message += f"   {emoji} {char.get('rarity', 'Unknown')}{subrarity_text}\n"
            message += f"   🆔 `{char.get('character_id', 'N/A')}` | 🗑️ {days_ago}d ago\n\n"
        
        return message
    
    @staticmethod
    async def get_username_from_id(client: Client, user_id: int) -> str:
        """Get username from user ID"""
        try:
            user = await client.get_users(user_id)
            return f"@{user.username}" if user.username else user.first_name
        except:
            return f"User ({user_id})"
    
    @staticmethod
    async def send_to_log_channel(
        client: Client, 
        character_data: Dict[str, Any], 
        username: str,
        user_id: int,
        action: str = "added"
    ) -> bool:
        """Send character data to log channel"""
        try:
            if action == "added":
                log_message = (
                    f"🆕 **New Character Added!**\n\n"
                    f"👤 **Name:** {character_data['char_name']}\n"
                    f"🎞️ **Anime:** {character_data['anime_name']}\n"
                    f"🏅 **Rarity:** {character_data['rarity']}\n"
                )
            elif action == "restored":
                log_message = (
                    f"♻️ **Character Restored from Recycle Bin!**\n\n"
                    f"👤 **Name:** {character_data['char_name']}\n"
                    f"🎞️ **Anime:** {character_data['anime_name']}\n"
                    f"🏅 **Rarity:** {character_data['rarity']}\n"
                )
            elif action == "deleted":
                log_message = (
                    f"🗑️ **Character Moved to Recycle Bin!**\n\n"
                    f"👤 **Name:** {character_data['char_name']}\n"
                    f"🎞️ **Anime:** {character_data['anime_name']}\n"
                    f"🏅 **Rarity:** {character_data['rarity']}\n"
                )
            else:
                log_message = (
                    f"👤 **Name:** {character_data['char_name']}\n"
                    f"🎞️ **Anime:** {character_data['anime_name']}\n"
                    f"🏅 **Rarity:** {character_data['rarity']}\n"
                )
            
            if character_data.get('subrarity'):
                log_message += f"💠 **Sub-Rarity:** {character_data['subrarity']}\n"
            
            log_message += f"🧍 **Action by:** @{username} ({user_id})\n"
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
            
            logger.info(f"Character {action} logged to: {config.LOG_CHANNEL}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending to log channel: {e}")
            return False
    
    @staticmethod
    def parse_rarity(rarity_input: str) -> tuple[Optional[str], Optional[str]]:
        """Parse rarity input for new rarity system"""
        try:
            parts = rarity_input.strip().split()
            if not parts:
                return None, None
            
            rarity_num = int(parts[0])
            if rarity_num not in config.RARITIES:
                return None, None
            
            rarity_data = config.RARITIES[rarity_num]
            rarity_name = rarity_data["name"]
            subrarity = None
            
            # Check for subrarity
            if len(parts) > 1:
                sub_input = ' '.join(parts[1:]).lower()
                for sub in rarity_data.get("subs", []):
                    # Remove emoji and spaces for comparison
                    sub_clean = sub.replace('️', '').replace(' ', '').lower()
                    if sub_input in sub_clean or sub_input in sub.lower():
                        subrarity = sub
                        break
            
            return rarity_name, subrarity
            
        except (ValueError, IndexError):
            return None, None
    
    @staticmethod
    def is_owner(user_id: int) -> bool:
        """Check if user is bot owner"""
        return user_id == config.OWNER_ID

helpers = Helpers()

# ==================== MAIN BOT ====================
class CharacterBot:
    """Main bot class with recycle bin system"""
    
    def __init__(self):
        self.client = Client(
            "character_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )
        self.user_states = {}
        self._register_handlers()
    
    # ==================== VIEWING SYSTEM METHODS ====================
    async def _show_main_menu(self, client: Client, callback_query: CallbackQuery = None, message: Message = None):
        """Show main menu"""
        total_chars = await db.get_character_count()
        total_deleted = await db.get_deleted_characters_count()
        
        menu_text = (
            f"📚 **Character Database Menu**\n"
            f"📊 **Active Characters:** {total_chars}\n"
            f"🗑️ **Deleted Characters:** {total_deleted}\n\n"
            "Select a rarity to browse characters:"
        )
        
        keyboard = helpers.create_rarity_keyboard("main")
        
        if callback_query:
            await callback_query.message.edit_text(menu_text, reply_markup=keyboard)
            await callback_query.answer()
        else:
            await message.reply_text(menu_text, reply_markup=keyboard)
    
    async def _show_rarity_submenu(self, client: Client, callback_query: CallbackQuery, rarity_num: int, current_view: str):
        """Show submenu for a specific rarity"""
        rarity_data = config.RARITIES.get(rarity_num, {})
        if not rarity_data:
            await callback_query.answer("Invalid rarity", show_alert=True)
            return
        
        # Get count for this rarity
        characters_count = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: db.characters.count_documents({"rarity": rarity_data["name"]})
        )
        
        menu_text = (
            f"{rarity_data['emoji']} **{rarity_data['name']}**\n"
            f"📊 **Characters:** {characters_count}\n\n"
        )
        
        if rarity_data.get("subs"):
            menu_text += "**Sub-Rarities Available:**\n"
            for sub in rarity_data["subs"]:
                menu_text += f"• {sub}\n"
            menu_text += "\nSelect an option below:"
        else:
            menu_text += "Select an option below:"
        
        keyboard = helpers.create_subrarity_keyboard(rarity_num, current_view)
        await callback_query.message.edit_text(menu_text, reply_markup=keyboard)
        await callback_query.answer()
    
    async def _show_all_characters(self, client: Client, callback_query: CallbackQuery, page: int, current_view: str):
        """Show all active characters"""
        characters, total_count = await db.get_all_characters_paginated(page)
        
        if not characters:
            await callback_query.answer("No characters found", show_alert=True)
            return
        
        total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
        
        # Format message
        message_text = helpers.format_character_list(
            characters, page, total_count, 
            "All Active Characters"
        )
        
        # Create keyboard
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "all", current_view)
        
        # Add view buttons for each character
        buttons = []
        for char in characters[:3]:  # Show first 3 characters
            char_id = char.get('character_id')
            if char_id:
                buttons.append([
                    InlineKeyboardButton(
                        f"👁️ {char.get('char_name', 'Unknown')[:15]}...",
                        callback_data=f"info_{char_id}"
                    )
                ])
        
        if buttons:
            keyboard.inline_keyboard.extend(buttons)
        
        # Add back button
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                "🔙 Back to Menu",
                callback_data="menu_main"
            )
        ])
        
        await callback_query.message.edit_text(message_text, reply_markup=keyboard)
        await callback_query.answer()
    
    async def _show_deleted_characters(self, client: Client, callback_query: CallbackQuery, page: int, current_view: str):
        """Show deleted characters (recycle bin)"""
        characters, total_count = await db.get_deleted_characters(page)
        
        if not characters:
            await callback_query.answer("Recycle bin is empty", show_alert=True)
            return
        
        total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
        
        # Format message
        message_text = helpers.format_deleted_character_list(characters, page, total_count)
        
        # Create keyboard
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "deleted_list", current_view)
        
        # Add action buttons for each character
        buttons = []
        for char in characters[:3]:  # Show first 3 characters
            char_id = char.get('character_id')
            if char_id:
                buttons.append([
                    InlineKeyboardButton(
                        f"♻️ Restore {char.get('char_name', 'Unknown')[:10]}...",
                        callback_data=f"restore_{char_id}"
                    )
                ])
                buttons.append([
                    InlineKeyboardButton(
                        f"👁️ View {char.get('char_name', 'Unknown')[:10]}...",
                        callback_data=f"deleted_info_{char_id}"
                    )
                ])
        
        if buttons:
            keyboard.inline_keyboard.extend(buttons)
        
        # Add back button and cleanup button
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                "🔄 Cleanup Old",
                callback_data=f"cleanup_deleted"
            )
        ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                "🔙 Back to Menu",
                callback_data="menu_main"
            )
        ])
        
        await callback_query.message.edit_text(message_text, reply_markup=keyboard)
        await callback_query.answer()
    
    async def _show_rarity_characters(self, client: Client, callback_query: CallbackQuery, rarity_num: int, page: int, current_view: str):
        """Show characters for a specific rarity"""
        rarity_data = config.RARITIES.get(rarity_num, {})
        if not rarity_data:
            await callback_query.answer("Invalid rarity", show_alert=True)
            return
        
        characters, total_count = await db.get_characters_by_rarity(rarity_data["name"], page)
        
        if not characters:
            await callback_query.answer(f"No {rarity_data['name']} characters found", show_alert=True)
            return
        
        total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
        
        # Format message
        message_text = helpers.format_character_list(
            characters, page, total_count, 
            f"{rarity_data['emoji']} {rarity_data['name']} Characters"
        )
        
        # Create keyboard
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "rarity", f"{rarity_num}_{current_view}")
        
        # Add view buttons for each character
        buttons = []
        for char in characters[:3]:  # Show first 3 characters
            char_id = char.get('character_id')
            if char_id:
                buttons.append([
                    InlineKeyboardButton(
                        f"👁️ {char.get('char_name', 'Unknown')[:15]}...",
                        callback_data=f"info_{char_id}"
                    )
                ])
        
        if buttons:
            keyboard.inline_keyboard.extend(buttons)
        
        # Add back button
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                "🔙 Back",
                callback_data=f"rarity_{rarity_num}_{current_view}"
            )
        ])
        
        await callback_query.message.edit_text(message_text, reply_markup=keyboard)
        await callback_query.answer()
    
    async def _show_subrarity_characters(self, client: Client, callback_query: CallbackQuery, rarity_num: int, subrarity: str, page: int, current_view: str):
        """Show characters for a specific sub-rarity"""
        rarity_data = config.RARITIES.get(rarity_num, {})
        if not rarity_data:
            await callback_query.answer("Invalid rarity", show_alert=True)
            return
        
        # Convert back from underscore to space
        subrarity = subrarity.replace('_', ' ')
        
        characters, total_count = await db.get_characters_by_subrarity(rarity_data["name"], subrarity, page)
        
        if not characters:
            await callback_query.answer(f"No {subrarity} characters found", show_alert=True)
            return
        
        total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
        
        # Format message
        message_text = helpers.format_character_list(
            characters, page, total_count, 
            f"{subrarity} Characters"
        )
        
        # Create keyboard
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "sub", f"{rarity_num}_{subrarity.replace(' ', '_')}_{current_view}")
        
        # Add view buttons for each character
        buttons = []
        for char in characters[:3]:  # Show first 3 characters
            char_id = char.get('character_id')
            if char_id:
                buttons.append([
                    InlineKeyboardButton(
                        f"👁️ {char.get('char_name', 'Unknown')[:15]}...",
                        callback_data=f"info_{char_id}"
                    )
                ])
        
        if buttons:
            keyboard.inline_keyboard.extend(buttons)
        
        # Add back button
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                "🔙 Back",
                callback_data=f"rarity_{rarity_num}_{current_view}"
            )
        ])
        
        await callback_query.message.edit_text(message_text, reply_markup=keyboard)
        await callback_query.answer()
    
    async def _show_search_results(self, client: Client, callback_query: CallbackQuery, query: str, page: int):
        """Show search results"""
        characters, total_count = await db.search_characters_paginated(query, page)
        
        if not characters:
            await callback_query.answer("No more results", show_alert=True)
            return
        
        total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
        
        # Format message
        message_text = helpers.format_character_list(
            characters, page, total_count, 
            f"Search Results for: '{query}'"
        )
        
        # Create keyboard
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "search", query)
        
        # Add view buttons for each character
        buttons = []
        for char in characters[:3]:  # Show first 3 characters
            char_id = char.get('character_id')
            if char_id:
                buttons.append([
                    InlineKeyboardButton(
                        f"👁️ {char.get('char_name', 'Unknown')[:15]}...",
                        callback_data=f"info_{char_id}"
                    )
                ])
        
        if buttons:
            keyboard.inline_keyboard.extend(buttons)
        
        # Add back to menu button
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                "🔙 Back to Menu",
                callback_data="menu_main"
            )
        ])
        
        await callback_query.message.edit_text(message_text, reply_markup=keyboard)
        await callback_query.answer()
    
    async def _show_myuploads(self, client: Client, callback_query: CallbackQuery, page: int):
        """Show user's uploaded characters"""
        user_id = callback_query.from_user.id
        characters, total_count = await db.get_user_characters_paginated(user_id, page)
        
        if not characters:
            await callback_query.answer("No more uploads", show_alert=True)
            return
        
        total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
        
        # Format message
        message_text = helpers.format_character_list(
            characters, page, total_count, 
            "Your Uploaded Characters"
        )
        
        # Create keyboard
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "myuploads", "")
        
        # Add view buttons for each character
        buttons = []
        for char in characters[:3]:  # Show first 3 characters
            char_id = char.get('character_id')
            if char_id:
                buttons.append([
                    InlineKeyboardButton(
                        f"👁️ {char.get('char_name', 'Unknown')[:15]}...",
                        callback_data=f"info_{char_id}"
                    )
                ])
        
        if buttons:
            keyboard.inline_keyboard.extend(buttons)
        
        # Add back button
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                "🔙 Back to Menu",
                callback_data="menu_main"
            )
        ])
        
        await callback_query.message.edit_text(message_text, reply_markup=keyboard)
        await callback_query.answer()
    
    async def _show_character_info(self, client: Client, message: Message, character_id: int):
        """Show character information"""
        # First check active characters
        character = await db.get_character_by_id(character_id)
        is_deleted = False
        
        # If not found in active, check deleted
        if not character:
            character = await db.get_deleted_character_by_id(character_id)
            is_deleted = True
        
        if not character:
            await message.reply_text(f"❌ Character with ID `{character_id}` not found!")
            return
        
        # Format character info
        if is_deleted:
            char_info = helpers.format_deleted_character_info(character)
            title = "🗑️ Deleted Character Information"
        else:
            char_info = helpers.format_character_info(character)
            title = "Character Information"
        
        # Create keyboard based on status
        if is_deleted:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("♻️ Restore Character", callback_data=f"restore_{character_id}"),
                    InlineKeyboardButton("🗑️ Delete Permanently", callback_data=f"perm_delete_{character_id}")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
                ]
            ])
        else:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🗑️ Move to Recycle Bin", callback_data=f"soft_delete_{character_id}")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
                ]
            ])
        
        # Check if character has media
        if character.get('media_url') and character.get('media_type'):
            try:
                if character.get('media_type') == 'photo':
                    await client.send_photo(
                        chat_id=message.chat.id,
                        photo=character['media_url'],
                        caption=f"**{title}**\n\n{char_info}",
                        reply_markup=keyboard
                    )
                elif character.get('media_type') == 'video':
                    await client.send_video(
                        chat_id=message.chat.id,
                        video=character['media_url'],
                        caption=f"**{title}**\n\n{char_info}",
                        reply_markup=keyboard
                    )
                elif character.get('media_type') == 'audio':
                    await client.send_audio(
                        chat_id=message.chat.id,
                        audio=character['media_url'],
                        caption=f"**{title}**\n\n{char_info}",
                        reply_markup=keyboard
                    )
                else:
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=character['media_url'],
                        caption=f"**{title}**\n\n{char_info}",
                        reply_markup=keyboard
                    )
            except Exception as e:
                logger.warning(f"Failed to send media: {e}")
                char_info += f"\n\n📸 **Media URL:** {character['media_url']}"
                await message.reply_text(f"**{title}**\n\n{char_info}", reply_markup=keyboard)
        else:
            await message.reply_text(f"**{title}**\n\n{char_info}", reply_markup=keyboard)
    
    async def _show_character_info_callback(self, client: Client, callback_query: CallbackQuery, character_id: int):
        """Show character information from callback"""
        # First check active characters
        character = await db.get_character_by_id(character_id)
        is_deleted = False
        
        # If not found in active, check deleted
        if not character:
            character = await db.get_deleted_character_by_id(character_id)
            is_deleted = True
        
        if not character:
            await callback_query.answer(f"Character with ID {character_id} not found", show_alert=True)
            return
        
        # Format character info
        if is_deleted:
            char_info = helpers.format_deleted_character_info(character)
            title = "🗑️ Deleted Character Information"
        else:
            char_info = helpers.format_character_info(character)
            title = "Character Information"
        
        # Create keyboard based on status
        if is_deleted:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("♻️ Restore Character", callback_data=f"restore_{character_id}"),
                    InlineKeyboardButton("🗑️ Delete Permanently", callback_data=f"perm_delete_{character_id}")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
                ]
            ])
        else:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🗑️ Move to Recycle Bin", callback_data=f"soft_delete_{character_id}")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
                ]
            ])
        
        # Since we can't edit message to media, send a new message
        await callback_query.message.reply_text(f"**{title}**\n\n{char_info}", reply_markup=keyboard)
        await callback_query.answer()
    
    async def _show_stats(self, client: Client, callback_query: CallbackQuery):
        """Show database statistics"""
        # Get various stats
        total_chars = await db.get_character_count()
        total_deleted = await db.get_deleted_characters_count()
        rarity_stats = await db.get_rarity_stats()
        top_uploaders = await db.get_top_uploaders(10)
        
        # Clean up old deleted characters
        cleaned_count = await db.cleanup_old_deleted()
        
        # Format stats message
        stats_text = f"📈 **Database Statistics**\n\n"
        stats_text += f"📊 **Active Characters:** {total_chars}\n"
        stats_text += f"🗑️ **Deleted Characters:** {total_deleted}\n"
        if cleaned_count > 0:
            stats_text += f"🧹 **Recently Cleaned:** {cleaned_count} (older than {config.RECYCLE_BIN_MAX_DAYS} days)\n"
        stats_text += f"📈 **Total (All Time):** {total_chars + total_deleted}\n\n"
        
        stats_text += "**Characters by Rarity:**\n"
        for rarity_num, rarity_data in config.RARITIES.items():
            count = rarity_stats.get(rarity_data["name"], 0)
            percentage = (count / total_chars * 100) if total_chars > 0 else 0
            stats_text += f"{rarity_data['emoji']} **{rarity_data['name']}:** {count} ({percentage:.1f}%)\n"
        
        stats_text += f"\n**Top Uploaders:**\n"
        for i, uploader in enumerate(top_uploaders, 1):
            user_id = uploader["_id"]
            count = uploader["count"]
            
            # Try to get username
            try:
                username = await helpers.get_username_from_id(client, user_id)
            except:
                username = f"User {user_id}"
            
            stats_text += f"{i}. {username}: {count} characters\n"
        
        # Add keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="stats_refresh")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
        ])
        
        await callback_query.message.edit_text(stats_text, reply_markup=keyboard)
        await callback_query.answer()
    
    # ==================== HANDLER REGISTRATION ====================
    def _register_handlers(self):
        """Register all message and callback handlers"""
        
        @self.client.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            """Handle /start command"""
            welcome_text = (
                "👋 **Welcome to Character Database Bot!**\n\n"
                "**This bot has three main functions:**\n\n"
                "📤 **UPLOAD SYSTEM:**\n"
                "• Upload characters with media files\n"
                "• Supports photos, videos, audio, and documents\n"
                "• Uses the new rarity system (1-7 with sub-rarities)\n"
                "• Automatically posts to @capture_database\n\n"
                "📚 **VIEWING SYSTEM:**\n"
                "• Browse characters by rarity\n"
                "• Search characters by name or anime\n"
                "• View character details and statistics\n"
                "• Paginated browsing\n\n"
                "🗑️ **RECYCLE BIN SYSTEM:**\n"
                "• Deleted characters go to recycle bin\n"
                "• Restore deleted characters anytime\n"
                "• Automatic cleanup after 30 days\n"
                "• View deleted character history\n\n"
                "**Main Commands:**\n"
                "• /menu - Browse character database\n"
                "• /upload - Upload a new character\n"
                "• /restore - Restore deleted character\n"
                "• /deleted - View recycle bin\n"
                "• /search - Search characters\n"
                "• /stats - View statistics\n"
                "• /help - Show detailed help\n\n"
                "**New Rarity System:**\n"
                "1. 🌸 Blossom\n"
                "2. ✨ Starlit\n"
                "3. 🩸 Crimson (with sub-rarities)\n"
                "4. 🌘 Eclipse (with sub-rarities)\n"
                "5. 🌌 Celestia (with sub-rarities)\n"
                "6. 🪽 Ascended (with sub-rarities)\n"
                "7. 🧬 One-of-One"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")],
                [InlineKeyboardButton("📤 Upload Character", callback_data="upload_help")],
                [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
                [InlineKeyboardButton("ℹ️ Help Guide", callback_data="help_main")]
            ])
            
            await message.reply_text(welcome_text, reply_markup=keyboard)
        
        @self.client.on_message(filters.command("menu"))
        async def menu_command(client: Client, message: Message):
            """Show main menu"""
            await self._show_main_menu(client, message=message)
        
        @self.client.on_message(filters.command("help"))
        async def help_command(client: Client, message: Message):
            """Show help message"""
            help_text = (
                "ℹ️ **Character Bot Help Guide**\n\n"
                "📤 **UPLOADING CHARACTERS:**\n"
                "1. Send a photo/video/audio/document\n"
                "2. Reply to it with: `/upload \"Character Name\" \"Anime Name\" Rarity [subrarity]`\n\n"
                "**Examples:**\n"
                "• `/upload \"Ichigo Kurosaki\" Bleach 3`\n"
                "• `/upload \"Goku\" \"Dragon Ball\" 5 astral`\n\n"
                "**Rarity Numbers (1-7):**\n"
                "1. 🌸 Blossom\n"
                "2. ✨ Starlit\n"
                "3. 🩸 Crimson (🩸 Bloodline, 🕯️ Cursed, 🌑 Shadowborn)\n"
                "4. 🌘 Eclipse (🌘 Lunar, ☀️ Solar, 🌓 Twilight, 🕳️ Void)\n"
                "5. 🌌 Celestia (🌌 Astral, 👼 Seraph, 🔮 Arcane, 🧿 Divine Relic)\n"
                "6. 🪽 Ascended (🪽 Mythborn, 👑 Sovereign, 👁️ Omniscient)\n"
                "7. 🧬 One-of-One\n\n"
                "🗑️ **RECYCLE BIN SYSTEM:**\n"
                "• /deleted - View deleted characters\n"
                "• /restore ID - Restore a deleted character\n"
                "• /searchdeleted query - Search deleted characters\n"
                "• Deleted characters auto-clean after 30 days\n\n"
                "📚 **BROWSING CHARACTERS:**\n"
                "• /menu - Browse by rarity\n"
                "• /search query - Search characters\n"
                "• /info ID - View character details\n"
                "• /myuploads - View your uploads\n"
                "• /stats - View database statistics\n\n"
                "⚙️ **EDITING CHARACTERS:**\n"
                "• /edit ID \"New Name\" \"New Anime\" Rarity [subrarity]\n"
                "• /editmedia ID - Edit media (reply to new media)\n\n"
                "**Note:** Only sudo users can upload/edit characters."
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")],
                [InlineKeyboardButton("📤 Upload Example", callback_data="upload_example")],
                [InlineKeyboardButton("🗑️ Recycle Bin", callback_data="deleted_list_0_main")],
                [InlineKeyboardButton("📊 View Stats", callback_data="stats_main")]
            ])
            
            await message.reply_text(help_text, reply_markup=keyboard)
        
        @self.client.on_message(filters.command("upload"))
        async def upload_command(client: Client, message: Message):
            """Handle /upload command"""
            user_id = message.from_user.id
            
            # Check authorization
            if not await db.is_sudo_user(user_id):
                await message.reply_text(
                    "❌ You are not authorized to upload characters.\n\n"
                    "Only sudo users can upload. Contact the bot owner for access."
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
                    "**Usage:** Reply to a photo/video/audio/document with:\n"
                    "`/upload \"Character Name\" \"Anime Name\" Rarity [subrarity]`\n\n"
                    "**Examples:**\n"
                    "• `/upload \"Ichigo Kurosaki\" Bleach 3`\n"
                    "• `/upload \"Goku\" \"Dragon Ball\" 5 astral`\n\n"
                    "**Rarity Numbers:**\n"
                    "1. 🌸 Blossom\n"
                    "2. ✨ Starlit\n"
                    "3. 🩸 Crimson\n"
                    "4. 🌘 Eclipse\n"
                    "5. 🌌 Celestia\n"
                    "6. 🪽 Ascended\n"
                    "7. 🧬 One-of-One"
                )
                return
            
            # Parse arguments
            args = message.text.split()
            if len(args) < 4:
                await message.reply_text(
                    "❌ **Invalid syntax!**\n\n"
                    "**Usage:** `/upload \"Character Name\" \"Anime Name\" Rarity [subrarity]`\n\n"
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
                await message.reply_text(
                    "❌ Invalid rarity.\n\n"
                    "**Valid Rarity Numbers:**\n"
                    "1. 🌸 Blossom\n"
                    "2. ✨ Starlit\n"
                    "3. 🩸 Crimson\n"
                    "4. 🌘 Eclipse\n"
                    "5. 🌌 Celestia\n"
                    "6. 🪽 Ascended\n"
                    "7. 🧬 One-of-One\n\n"
                    "**Some sub-rarities:**\n"
                    "• For rarity 3: bloodline, cursed, shadowborn\n"
                    "• For rarity 4: lunar, solar, twilight, void\n"
                    "• For rarity 5: astral, seraph, arcane, divinerelic\n"
                    "• For rarity 6: mythborn, sovereign, omniscient"
                )
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
                    client, character.to_dict(), username, user_id, "added"
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
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("👁️ View Character", callback_data=f"info_{character_id}")],
                    [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")]
                ])
                
                await update_status(success_text)
                await status_msg.edit_reply_markup(keyboard)
                
            except Exception as e:
                logger.error(f"Error saving character: {e}")
                await update_status("❌ Error saving character to database. Please try again.")
        
        @self.client.on_message(filters.command("restore"))
        async def restore_command(client: Client, message: Message):
            """Handle /restore command - restore deleted character"""
            user_id = message.from_user.id
            
            # Check authorization (only sudo users can restore)
            if not await db.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to restore characters.")
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "♻️ **Restore Deleted Character**\n\n"
                    "**Usage:** `/restore character_id`\n\n"
                    "**Example:** `/restore 123`\n\n"
                    "You can find character IDs in the recycle bin using /deleted command."
                )
                return
            
            try:
                character_id = int(args[1])
                
                # Check if character exists in deleted collection
                character = await db.get_deleted_character_by_id(character_id)
                if not character:
                    await message.reply_text(f"❌ Character with ID `{character_id}` not found in recycle bin!")
                    return
                
                # Restore character
                restored = await db.restore_character(character_id)
                
                if restored:
                    # Send to log channel
                    username = message.from_user.username or message.from_user.first_name or "Unknown"
                    await helpers.send_to_log_channel(
                        client, character, username, user_id, "restored"
                    )
                    
                    await message.reply_text(
                        f"♻️ **Character #{character_id} Restored Successfully!**\n\n"
                        f"👤 **Name:** {character.get('char_name', 'Unknown')}\n"
                        f"🎞️ **Anime:** {character.get('anime_name', 'Unknown')}\n"
                        f"🏅 **Rarity:** {character.get('rarity', 'Unknown')}\n\n"
                        f"The character has been moved back to the active database."
                    )
                    
                    logger.info(f"Character {character_id} restored by user {user_id}")
                else:
                    await message.reply_text("❌ Failed to restore character.")
                    
            except ValueError:
                await message.reply_text("❌ Invalid character ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in restore command: {e}")
                await message.reply_text("❌ Error restoring character.")
        
        @self.client.on_message(filters.command(["deleted", "recyclebin", "trash"]))
        async def deleted_command(client: Client, message: Message):
            """Show deleted characters (recycle bin)"""
            user_id = message.from_user.id
            
            # Check authorization (only sudo users can view recycle bin)
            if not await db.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to view the recycle bin.")
                return
            
            await message.reply_text("🗑️ Loading recycle bin...")
            
            # Get deleted characters
            characters, total_count = await db.get_deleted_characters(page=0)
            
            if not characters:
                await message.reply_text(
                    "🗑️ **Recycle Bin is Empty!**\n\n"
                    "No deleted characters found.\n"
                    "Deleted characters are automatically cleaned up after 30 days."
                )
                return
            
            total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
            
            # Format message
            message_text = helpers.format_deleted_character_list(characters, 0, total_count)
            
            # Create keyboard
            keyboard = helpers.create_pagination_keyboard(0, total_pages, "deleted_list", "main")
            
            # Add action buttons for each character
            buttons = []
            for char in characters[:3]:  # Show first 3 characters
                char_id = char.get('character_id')
                if char_id:
                    buttons.append([
                        InlineKeyboardButton(
                            f"♻️ Restore {char.get('char_name', 'Unknown')[:10]}...",
                            callback_data=f"restore_{char_id}"
                        )
                    ])
                    buttons.append([
                        InlineKeyboardButton(
                            f"👁️ View {char.get('char_name', 'Unknown')[:10]}...",
                            callback_data=f"deleted_info_{char_id}"
                        )
                    ])
            
            if buttons:
                keyboard.inline_keyboard.extend(buttons)
            
            # Add back button and cleanup button
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    "🔄 Cleanup Old",
                    callback_data=f"cleanup_deleted"
                )
            ])
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    "🔙 Back to Menu",
                    callback_data="menu_main"
                )
            ])
            
            await message.reply_text(message_text, reply_markup=keyboard)
        
        @self.client.on_message(filters.command(["searchdeleted", "finddeleted"]))
        async def searchdeleted_command(client: Client, message: Message):
            """Search deleted characters"""
            user_id = message.from_user.id
            
            # Check authorization
            if not await db.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to search deleted characters.")
                return
            
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "🔍 **Search Deleted Characters**\n\n"
                    "**Usage:** `/searchdeleted query`\n\n"
                    "**Examples:**\n"
                    "• `/searchdeleted naruto`\n"
                    "• `/searchdeleted bleach`\n\n"
                    "You can search by character name or anime name."
                )
                return
            
            query = ' '.join(args[1:])
            await message.reply_text(f"🔍 Searching deleted characters for: `{query}`...")
            
            # Perform search
            characters, total_count = await db.search_deleted_characters(query, page=0)
            
            if not characters:
                await message.reply_text(f"❌ No deleted characters found for: `{query}`")
                return
            
            total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
            
            # Format message
            message_text = helpers.format_deleted_character_list(characters, 0, total_count)
            message_text = f"🔍 **Search Results in Recycle Bin:**\n\n" + message_text
            
            # Create keyboard
            keyboard = helpers.create_pagination_keyboard(0, total_pages, "search_deleted", query)
            
            # Add action buttons for each character
            buttons = []
            for char in characters[:3]:  # Show first 3 characters
                char_id = char.get('character_id')
                if char_id:
                    buttons.append([
                        InlineKeyboardButton(
                            f"♻️ Restore {char.get('char_name', 'Unknown')[:10]}...",
                            callback_data=f"restore_{char_id}"
                        )
                    ])
                    buttons.append([
                        InlineKeyboardButton(
                            f"👁️ View {char.get('char_name', 'Unknown')[:10]}...",
                            callback_data=f"deleted_info_{char_id}"
                        )
                    ])
            
            if buttons:
                keyboard.inline_keyboard.extend(buttons)
            
            # Add back button
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    "🔙 Back to Menu",
                    callback_data="menu_main"
                )
            ])
            
            await message.reply_text(message_text, reply_markup=keyboard)
        
        @self.client.on_message(filters.command(["search", "find"]))
        async def search_command(client: Client, message: Message):
            """Handle /search command"""
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text(
                    "🔍 **Search Characters**\n\n"
                    "**Usage:** `/search query`\n\n"
                    "**Examples:**\n"
                    "• `/search naruto`\n"
                    "• `/search bleach`\n"
                    "• `/search ichigo kurosaki`\n\n"
                    "You can search by character name or anime name."
                )
                return
            
            query = ' '.join(args[1:])
            await message.reply_text(f"🔍 Searching for: `{query}`...")
            
            # Perform search
            characters, total_count = await db.search_characters_paginated(query, page=0)
            
            if not characters:
                await message.reply_text(f"❌ No results found for: `{query}`")
                return
            
            total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
            
            # Format message
            message_text = helpers.format_character_list(
                characters, 0, total_count, 
                f"Search Results for: '{query}'"
            )
            
            # Create keyboard
            keyboard = helpers.create_pagination_keyboard(0, total_pages, "search", query)
            
            # Add view buttons for each character
            buttons = []
            for char in characters[:5]:  # Show first 5 characters
                char_id = char.get('character_id')
                if char_id:
                    buttons.append([
                        InlineKeyboardButton(
                            f"👁️ {char.get('char_name', 'Unknown')[:15]}...",
                            callback_data=f"info_{char_id}"
                        )
                    ])
            
            if buttons:
                keyboard.inline_keyboard.extend(buttons)
            
            # Add back to menu button
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    "🔙 Back to Menu",
                    callback_data="menu_main"
                )
            ])
            
            await message.reply_text(message_text, reply_markup=keyboard)
        
        @self.client.on_message(filters.command("stats"))
        async def stats_command(client: Client, message: Message):
            """Show database statistics"""
            # Get various stats
            total_chars = await db.get_character_count()
            total_deleted = await db.get_deleted_characters_count()
            rarity_stats = await db.get_rarity_stats()
            top_uploaders = await db.get_top_uploaders(10)
            
            # Clean up old deleted characters
            cleaned_count = await db.cleanup_old_deleted()
            
            # Format stats message
            stats_text = f"📈 **Database Statistics**\n\n"
            stats_text += f"📊 **Active Characters:** {total_chars}\n"
            stats_text += f"🗑️ **Deleted Characters:** {total_deleted}\n"
            if cleaned_count > 0:
                stats_text += f"🧹 **Recently Cleaned:** {cleaned_count} (older than {config.RECYCLE_BIN_MAX_DAYS} days)\n"
            stats_text += f"📈 **Total (All Time):** {total_chars + total_deleted}\n\n"
            
            stats_text += "**Characters by Rarity:**\n"
            for rarity_num, rarity_data in config.RARITIES.items():
                count = rarity_stats.get(rarity_data["name"], 0)
                percentage = (count / total_chars * 100) if total_chars > 0 else 0
                stats_text += f"{rarity_data['emoji']} **{rarity_data['name']}:** {count} ({percentage:.1f}%)\n"
            
            stats_text += f"\n**Top Uploaders:**\n"
            for i, uploader in enumerate(top_uploaders, 1):
                user_id = uploader["_id"]
                count = uploader["count"]
                
                # Try to get username
                try:
                    username = await helpers.get_username_from_id(client, user_id)
                except:
                    username = f"User {user_id}"
                
                stats_text += f"{i}. {username}: {count} characters\n"
            
            # Add keyboard
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
                [InlineKeyboardButton("🔄 Refresh Stats", callback_data="stats_refresh")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
            ])
            
            await message.reply_text(stats_text, reply_markup=keyboard)
        
        @self.client.on_message(filters.command("myuploads"))
        async def myuploads_command(client: Client, message: Message):
            """Show user's uploaded characters"""
            user_id = message.from_user.id
            
            await message.reply_text("📂 Loading your uploaded characters...")
            
            # Get user's characters
            characters, total_count = await db.get_user_characters_paginated(user_id, page=0)
            
            if not characters:
                await message.reply_text("📭 You haven't uploaded any characters yet.")
                return
            
            total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
            
            # Format message
            message_text = helpers.format_character_list(
                characters, 0, total_count, 
                "Your Uploaded Characters"
            )
            
            # Create keyboard
            keyboard = helpers.create_pagination_keyboard(0, total_pages, "myuploads", "")
            
            # Add view buttons for each character
            buttons = []
            for char in characters[:5]:  # Show first 5 characters
                char_id = char.get('character_id')
                if char_id:
                    buttons.append([
                        InlineKeyboardButton(
                            f"👁️ {char.get('char_name', 'Unknown')[:15]}...",
                            callback_data=f"info_{char_id}"
                        )
                    ])
            
            if buttons:
                keyboard.inline_keyboard.extend(buttons)
            
            # Add back to menu button
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    "🔙 Back to Menu",
                    callback_data="menu_main"
                )
            ])
            
            await message.reply_text(message_text, reply_markup=keyboard)
        
        @self.client.on_message(filters.command("info"))
        async def info_command(client: Client, message: Message):
            """Show character information by ID"""
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "ℹ️ **Character Information**\n\n"
                    "**Usage:** `/info character_id`\n\n"
                    "**Example:** `/info 123`\n\n"
                    "You can find character IDs by browsing the database or searching."
                )
                return
            
            try:
                character_id = int(args[1])
                await self._show_character_info(client, message, character_id)
                
            except ValueError:
                await message.reply_text("❌ Invalid character ID. Please enter a number.")
            except Exception as e:
                logger.error(f"Error in info command: {e}")
                await message.reply_text("❌ Error fetching character information.")
        
        @self.client.on_message(filters.command("edit"))
        async def edit_command(client: Client, message: Message):
            """Handle /edit command - edit character details"""
            user_id = message.from_user.id
            
            # Check authorization
            if not await db.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to edit characters.")
                return
            
            args = message.text.split()
            if len(args) < 5:
                await message.reply_text(
                    "✏️ **Edit Character**\n\n"
                    "**Usage:** `/edit ID \"New Name\" \"New Anime\" Rarity [subrarity]`\n\n"
                    "**Examples:**\n"
                    "• `/edit 123 \"Naruto Uzumaki\" Naruto 3`\n"
                    "• `/edit 123 \"Sakura\" Naruto 5 astral`\n\n"
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
                    await message.reply_text("❌ Invalid rarity. Must be 1-7.")
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
            if not await db.is_sudo_user(user_id):
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
        
        @self.client.on_message(filters.command(["delete", "remove", "del"]))
        async def delete_command(client: Client, message: Message):
            """Handle /delete command - move character to recycle bin"""
            user_id = message.from_user.id
            
            # Only sudo users can delete
            if not await db.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to delete characters.")
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "🗑️ **Delete Character**\n\n"
                    "**Usage:** `/delete ID`\n\n"
                    "**Example:** `/delete 123`\n\n"
                    "**Note:** This moves the character to the recycle bin where it can be restored later."
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
                        InlineKeyboardButton("✅ Yes, Move to Recycle Bin", callback_data=f"soft_delete_{character_id}"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")
                    ]
                ])
                
                await message.reply_text(
                    f"⚠️ **Are you sure you want to move this character to the recycle bin?**\n\n"
                    f"**Name:** {character['char_name']}\n"
                    f"**Anime:** {character['anime_name']}\n"
                    f"**ID:** `{character_id}`\n\n"
                    f"**Note:** The character can be restored from the recycle bin later.",
                    reply_markup=keyboard
                )
                
            except ValueError:
                await message.reply_text("❌ Invalid character ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in delete command: {e}")
                await message.reply_text("❌ Error processing delete request.")
        
        # Callback query handler
        @self.client.on_callback_query()
        async def handle_callbacks(client: Client, callback_query: CallbackQuery):
            """Handle all callback queries"""
            data = callback_query.data
            user_id = callback_query.from_user.id
            
            try:
                # Handle noop (do nothing)
                if data == "noop":
                    await callback_query.answer()
                    return
                
                # Handle menu
                elif data == "menu_main":
                    await self._show_main_menu(client, callback_query)
                
                # Handle rarity selection
                elif data.startswith("rarity_"):
                    parts = data.split("_")
                    if len(parts) >= 3:
                        rarity_num = int(parts[1])
                        current_view = parts[2] if len(parts) > 2 else "main"
                        await self._show_rarity_submenu(client, callback_query, rarity_num, current_view)
                
                # View all characters
                elif data.startswith("view_all_"):
                    parts = data.split("_")
                    current_view = parts[2] if len(parts) > 2 else "main"
                    await self._show_all_characters(client, callback_query, 0, current_view)
                
                # View deleted characters
                elif data.startswith("deleted_list_"):
                    parts = data.split("_")
                    page = int(parts[2])
                    current_view = parts[3] if len(parts) > 3 else "main"
                    await self._show_deleted_characters(client, callback_query, page, current_view)
                
                # View characters by rarity
                elif data.startswith("view_rarity_"):
                    parts = data.split("_")
                    rarity_num = int(parts[2])
                    page = int(parts[4])
                    current_view = parts[5] if len(parts) > 5 else "main"
                    await self._show_rarity_characters(client, callback_query, rarity_num, page, current_view)
                
                # View characters by sub-rarity
                elif data.startswith("view_sub_"):
                    parts = data.split("_")
                    rarity_num = int(parts[2])
                    subrarity = '_'.join(parts[3:-2])  # Handle spaces in subrarity names
                    page = int(parts[-2])
                    current_view = parts[-1]
                    await self._show_subrarity_characters(client, callback_query, rarity_num, subrarity, page, current_view)
                
                # Pagination for search
                elif data.startswith("search_page_"):
                    parts = data.split("_")
                    page = int(parts[2])
                    query = '_'.join(parts[3:])  # Reconstruct query
                    await self._show_search_results(client, callback_query, query, page)
                
                # Pagination for deleted search
                elif data.startswith("search_deleted_page_"):
                    parts = data.split("_")
                    page = int(parts[3])
                    query = '_'.join(parts[4:])  # Reconstruct query
                    # Similar to show_search_results but for deleted
                    characters, total_count = await db.search_deleted_characters(query, page)
                    
                    if not characters:
                        await callback_query.answer("No more results", show_alert=True)
                        return
                    
                    total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
                    
                    # Format message
                    message_text = helpers.format_deleted_character_list(characters, page, total_count)
                    message_text = f"🔍 **Search Results in Recycle Bin:**\n\n" + message_text
                    
                    # Create keyboard
                    keyboard = helpers.create_pagination_keyboard(page, total_pages, "search_deleted", query)
                    
                    # Add action buttons
                    buttons = []
                    for char in characters[:3]:
                        char_id = char.get('character_id')
                        if char_id:
                            buttons.append([
                                InlineKeyboardButton(
                                    f"♻️ Restore {char.get('char_name', 'Unknown')[:10]}...",
                                    callback_data=f"restore_{char_id}"
                                )
                            ])
                            buttons.append([
                                InlineKeyboardButton(
                                    f"👁️ View {char.get('char_name', 'Unknown')[:10]}...",
                                    callback_data=f"deleted_info_{char_id}"
                                )
                            ])
                    
                    if buttons:
                        keyboard.inline_keyboard.extend(buttons)
                    
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
                    ])
                    
                    await callback_query.message.edit_text(message_text, reply_markup=keyboard)
                    await callback_query.answer()
                
                # Pagination for myuploads
                elif data.startswith("myuploads_page_"):
                    parts = data.split("_")
                    page = int(parts[2])
                    await self._show_myuploads(client, callback_query, page)
                
                # Pagination for all characters
                elif data.startswith("all_page_"):
                    parts = data.split("_")
                    page = int(parts[2])
                    current_view = parts[3] if len(parts) > 3 else "main"
                    await self._show_all_characters(client, callback_query, page, current_view)
                
                # Pagination for rarity
                elif data.startswith("rarity_page_"):
                    parts = data.split("_")
                    page = int(parts[2])
                    rarity_num = int(parts[3])
                    current_view = parts[4] if len(parts) > 4 else "main"
                    await self._show_rarity_characters(client, callback_query, rarity_num, page, current_view)
                
                # Pagination for subrarity
                elif data.startswith("sub_page_"):
                    parts = data.split("_")
                    page = int(parts[2])
                    rarity_num = int(parts[3])
                    subrarity = '_'.join(parts[4:-1])  # Handle spaces in subrarity names
                    current_view = parts[-1]
                    await self._show_subrarity_characters(client, callback_query, rarity_num, subrarity, page, current_view)
                
                # Character info
                elif data.startswith("info_"):
                    character_id = int(data.split("_")[1])
                    await self._show_character_info_callback(client, callback_query, character_id)
                
                # Deleted character info
                elif data.startswith("deleted_info_"):
                    character_id = int(data.split("_")[2])
                    character = await db.get_deleted_character_by_id(character_id)
                    
                    if not character:
                        await callback_query.answer("Character not found in recycle bin", show_alert=True)
                        return
                    
                    char_info = helpers.format_deleted_character_info(character)
                    
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("♻️ Restore Character", callback_data=f"restore_{character_id}"),
                            InlineKeyboardButton("🗑️ Delete Permanently", callback_data=f"perm_delete_{character_id}")
                        ],
                        [
                            InlineKeyboardButton("🔙 Back to Recycle Bin", callback_data="deleted_list_0_main")
                        ]
                    ])
                    
                    await callback_query.message.reply_text(f"**🗑️ Deleted Character Information**\n\n{char_info}", reply_markup=keyboard)
                    await callback_query.answer()
                
                # Soft delete (move to recycle bin)
                elif data.startswith("soft_delete_"):
                    character_id = int(data.split("_")[2])
                    
                    # Check authorization
                    if not await db.is_sudo_user(user_id):
                        await callback_query.answer("You are not authorized to delete characters", show_alert=True)
                        return
                    
                    # Move to recycle bin
                    deleted = await db.soft_delete_character(character_id, user_id, "Deleted via button")
                    
                    if deleted:
                        character = await db.get_deleted_character_by_id(character_id)
                        if character:
                            # Send to log channel
                            username = callback_query.from_user.username or callback_query.from_user.first_name or "Unknown"
                            await helpers.send_to_log_channel(
                                client, character, username, user_id, "deleted"
                            )
                        
                        await callback_query.message.edit_text(
                            f"🗑️ **Character `{character_id}` moved to recycle bin!**\n\n"
                            f"The character has been moved to the recycle bin and can be restored later.\n\n"
                            f"Use `/restore {character_id}` or the recycle bin menu to restore it."
                        )
                        logger.info(f"Character {character_id} moved to recycle bin by user {user_id}")
                    else:
                        await callback_query.answer("Failed to delete character", show_alert=True)
                
                # Restore character
                elif data.startswith("restore_"):
                    character_id = int(data.split("_")[1])
                    
                    # Check authorization
                    if not await db.is_sudo_user(user_id):
                        await callback_query.answer("You are not authorized to restore characters", show_alert=True)
                        return
                    
                    # Restore character
                    restored = await db.restore_character(character_id)
                    
                    if restored:
                        character = await db.get_character_by_id(character_id)
                        if character:
                            # Send to log channel
                            username = callback_query.from_user.username or callback_query.from_user.first_name or "Unknown"
                            await helpers.send_to_log_channel(
                                client, character, username, user_id, "restored"
                            )
                        
                        await callback_query.message.edit_text(
                            f"♻️ **Character `{character_id}` restored successfully!**\n\n"
                            f"The character has been moved back to the active database.\n\n"
                            f"Use `/info {character_id}` to view the character."
                        )
                        logger.info(f"Character {character_id} restored by user {user_id}")
                    else:
                        await callback_query.answer("Failed to restore character", show_alert=True)
                
                # Permanent delete
                elif data.startswith("perm_delete_"):
                    character_id = int(data.split("_")[2])
                    
                    # Only owner can permanently delete
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Only the bot owner can permanently delete characters", show_alert=True)
                        return
                    
                    # Show confirmation
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("⚠️ Yes, Delete Permanently", callback_data=f"confirm_perm_delete_{character_id}"),
                            InlineKeyboardButton("❌ Cancel", callback_data="cancel_perm_delete")
                        ]
                    ])
                    
                    await callback_query.message.edit_text(
                        f"🚨 **Permanent Deletion Warning!**\n\n"
                        f"Are you sure you want to **PERMANENTLY DELETE** character `{character_id}`?\n\n"
                        f"**This action cannot be undone!**\n"
                        f"The character will be removed from the recycle bin forever.\n\n"
                        f"⚠️ **This is irreversible!**",
                        reply_markup=keyboard
                    )
                    await callback_query.answer()
                
                # Confirm permanent delete
                elif data.startswith("confirm_perm_delete_"):
                    character_id = int(data.split("_")[3])
                    
                    # Only owner can permanently delete
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Unauthorized", show_alert=True)
                        return
                    
                    # Get character info before deleting
                    character = await db.get_deleted_character_by_id(character_id)
                    
                    # Permanently delete
                    deleted = await db.permanent_delete_character(character_id)
                    
                    if deleted:
                        await callback_query.message.edit_text(
                            f"💀 **Character `{character_id}` permanently deleted!**\n\n"
                            f"The character has been permanently removed from the database.\n\n"
                            f"**Name:** {character.get('char_name', 'Unknown') if character else 'Unknown'}\n"
                            f"**This action cannot be undone.**"
                        )
                        logger.info(f"Character {character_id} permanently deleted by owner {user_id}")
                    else:
                        await callback_query.message.edit_text(f"❌ Failed to permanently delete character `{character_id}`")
                    
                    await callback_query.answer()
                
                # Cancel permanent delete
                elif data == "cancel_perm_delete":
                    await callback_query.message.edit_text("✅ Permanent deletion cancelled.")
                    await callback_query.answer()
                
                # Cleanup old deleted characters
                elif data == "cleanup_deleted":
                    # Only owner can cleanup
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Only the bot owner can cleanup old deleted characters", show_alert=True)
                        return
                    
                    cleaned_count = await db.cleanup_old_deleted()
                    
                    if cleaned_count > 0:
                        await callback_query.message.edit_text(
                            f"🧹 **Cleanup Complete!**\n\n"
                            f"Removed {cleaned_count} old deleted characters (older than {config.RECYCLE_BIN_MAX_DAYS} days).\n\n"
                            f"The recycle bin has been cleaned up."
                        )
                        logger.info(f"Cleaned up {cleaned_count} old deleted characters by owner {user_id}")
                    else:
                        await callback_query.message.edit_text(
                            "🧹 **No old characters to clean up.**\n\n"
                            "All deleted characters are within the retention period."
                        )
                    await callback_query.answer()
                
                # Search from menu
                elif data == "search_main":
                    await callback_query.message.edit_text(
                        "🔍 **Search Characters**\n\n"
                        "Please use the /search command followed by your search query.\n\n"
                        "**Example:** `/search naruto`\n\n"
                        "You can search by character name or anime name.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                        ])
                    )
                    await callback_query.answer()
                
                # Stats from menu
                elif data == "stats_main" or data == "stats_refresh":
                    await self._show_stats(client, callback_query)
                
                # Upload help
                elif data == "upload_help":
                    await callback_query.message.edit_text(
                        "📤 **Upload Character**\n\n"
                        "1. Send a photo/video/audio/document\n"
                        "2. Reply to it with:\n"
                        "`/upload \"Character Name\" \"Anime Name\" Rarity [subrarity]`\n\n"
                        "**Example:**\n"
                        "`/upload \"Ichigo Kurosaki\" Bleach 3`\n"
                        "`/upload \"Goku\" \"Dragon Ball\" 5 astral`\n\n"
                        "**Rarity Numbers (1-7):**\n"
                        "1. 🌸 Blossom\n"
                        "2. ✨ Starlit\n"
                        "3. 🩸 Crimson (🩸 Bloodline, 🕯️ Cursed, 🌑 Shadowborn)\n"
                        "4. 🌘 Eclipse (🌘 Lunar, ☀️ Solar, 🌓 Twilight, 🕳️ Void)\n"
                        "5. 🌌 Celestia (🌌 Astral, 👼 Seraph, 🔮 Arcane, 🧿 Divine Relic)\n"
                        "6. 🪽 Ascended (🪽 Mythborn, 👑 Sovereign, 👁️ Omniscient)\n"
                        "7. 🧬 One-of-One",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                        ])
                    )
                    await callback_query.answer()
                
                # Upload example
                elif data == "upload_example":
                    await callback_query.message.edit_text(
                        "📤 **Upload Example:**\n\n"
                        "1. **Send a photo** of Naruto\n"
                        "2. **Reply to it with:**\n"
                        "`/upload \"Naruto Uzumaki\" Naruto 4 solar`\n\n"
                        "**This would create:**\n"
                        "• Character: Naruto Uzumaki\n"
                        "• Anime: Naruto\n"
                        "• Rarity: 🌘 Eclipse\n"
                        "• Sub-rarity: ☀️ Solar",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📤 Try Uploading", callback_data="upload_help")],
                            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                        ])
                    )
                    await callback_query.answer()
                
                # Help from callback
                elif data == "help_main":
                    await callback_query.message.edit_text(
                        "ℹ️ **Character Bot Help**\n\n"
                        "**Main Functions:**\n"
                        "📤 Upload characters with media\n"
                        "📚 Browse character database\n"
                        "🗑️ Recycle bin system (restore deleted)\n"
                        "🔍 Search for characters\n"
                        "📊 View statistics\n\n"
                        "**Use buttons below to explore:**",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📤 Upload System", callback_data="upload_help")],
                            [InlineKeyboardButton("📚 Viewing System", callback_data="menu_main")],
                            [InlineKeyboardButton("🗑️ Recycle Bin", callback_data="deleted_list_0_main")],
                            [InlineKeyboardButton("📊 Statistics", callback_data="stats_main")]
                        ])
                    )
                    await callback_query.answer()
                
                # Delete confirmation
                elif data.startswith("confirm_delete_"):
                    character_id = int(data.split("_")[2])
                    
                    # Only owner can permanently delete (old system)
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Unauthorized", show_alert=True)
                        return
                    
                    # For backward compatibility, use soft delete
                    deleted = await db.soft_delete_character(character_id, user_id, "Deleted via old delete command")
                    
                    if deleted:
                        await callback_query.message.edit_text(f"🗑️ Character `{character_id}` moved to recycle bin!")
                        logger.info(f"Character {character_id} moved to recycle bin by user {user_id}")
                    else:
                        await callback_query.message.edit_text(f"❌ Failed to delete character `{character_id}`")
                    
                    await callback_query.answer()
                
                elif data == "cancel_delete":
                    await callback_query.message.edit_text("✅ Delete cancelled.")
                    await callback_query.answer()
                
                # Unknown callback
                else:
                    await callback_query.answer("Unknown action", show_alert=True)
                    
            except Exception as e:
                logger.error(f"Error handling callback: {e}")
                await callback_query.answer("An error occurred", show_alert=True)
    
    async def start(self):
        """Start the bot"""
        try:
            await db.connect()
            logger.info("Database connection established")
            
            # Clean up old deleted characters on startup
            cleaned = await db.cleanup_old_deleted()
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} old deleted characters on startup")
            
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
    bot = CharacterBot()
    
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
