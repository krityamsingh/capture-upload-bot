# ==================== COMPLETE CHARACTER BOT WITH ALL FEATURES ====================
import os
import logging
import asyncio
import aiohttp
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardButton, 
    InlineKeyboardMarkup, CallbackQuery
)
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# ==================== LOGGING CONFIGURATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
class Config:
    """Configuration class for bot settings"""
    
    # Telegram API credentials
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
    
    # New rarity system (1-14)
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
        14: "🎤 Celebrity",
    }
    
    # Pagination settings
    ITEMS_PER_PAGE = 10
    
    # Recycle bin settings
    RECYCLE_BIN_MAX_DAYS = 30
    
    # Sudo permission levels
    PERMISSIONS = {
        'upload': 'Upload characters',
        'delete': 'Delete characters',
        'edit': 'Edit characters',
        'restore': 'Restore deleted characters',
        'fill': 'Fill deleted slots',
        'view_deleted': 'View recycle bin',
        'add_sudo': 'Add sudo users',
        'remove_sudo': 'Remove sudo users',
        'reset_db': 'Reset database'
    }

config = Config()

# ==================== DATA MODELS ====================
class Character:
    """Data model for character documents"""
    
    def __init__(
        self,
        char_name: str,
        anime_name: str,
        rarity: str,
        character_id: int,
        media_url: Optional[str] = None,
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
            media_type=data.get("media_type"),
            added_by=data.get("added_by"),
            timestamp=data.get("timestamp"),
            deleted_at=data.get("deleted_at"),
            deleted_by=data.get("deleted_by"),
            deleted_reason=data.get("deleted_reason")
        )

# ==================== DATABASE CLASS ====================
class MongoDB:
    """MongoDB database operations handler"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.characters = None
        self.deleted_characters = None
        self.counters = None
        self.sudo_users = None
        self.db_warnings = None  # For reset warnings
    
    async def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(config.MONGO_URI)
            self.db = self.client[config.DATABASE_NAME]
            self.characters = self.db.characters
            self.deleted_characters = self.db.deleted_characters
            self.counters = self.db.counters
            self.sudo_users = self.db.sudo_users
            self.db_warnings = self.db.db_warnings
            
            # Create indexes
            await self._create_indexes()
            
            # Initialize counter
            await self._initialize_counter()
            
            # Initialize warnings
            await self._initialize_warnings()
            
            logger.info("Connected to MongoDB successfully")
            
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def _create_indexes(self):
        """Create all necessary indexes"""
        indexes = [
            (self.characters, "char_name"),
            (self.characters, "added_by"),
            (self.characters, "character_id", True),
            (self.characters, "rarity"),
            (self.deleted_characters, "character_id"),
            (self.deleted_characters, "deleted_at"),
            (self.deleted_characters, "deleted_by"),
            (self.sudo_users, "user_id", True)
        ]
        
        for collection, field, *unique in indexes:
            unique_flag = unique[0] if unique else False
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda c=collection, f=field, u=unique_flag: c.create_index([(f, 1)], unique=u)
            )
    
    async def _initialize_counter(self):
        """Initialize counter if not exists"""
        counter_exists = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.counters.find_one({"_id": "character_id"})
        )
        
        if not counter_exists:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.counters.insert_one({"_id": "character_id", "seq": 0})
            )
    
    async def _initialize_warnings(self):
        """Initialize reset warnings collection"""
        warning_exists = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.db_warnings.find_one({"_id": "reset_warnings"})
        )
        
        if not warning_exists:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.db_warnings.insert_one({
                    "_id": "reset_warnings",
                    "warnings": {},
                    "last_warning": None
                })
            )
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            await asyncio.get_event_loop().run_in_executor(None, self.client.close)
            logger.info("Disconnected from MongoDB")
    
    # ==================== ID MANAGEMENT ====================
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
    
    # ==================== CHARACTER OPERATIONS ====================
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
        """Get total number of active characters"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.characters.count_documents({})
        )
    
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
    
    async def update_character(
        self, 
        character_id: int, 
        char_name: str, 
        anime_name: str, 
        rarity: str
    ) -> bool:
        """Update character details"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.update_one(
                    {"character_id": character_id},
                    {"$set": {
                        "char_name": char_name,
                        "anime_name": anime_name,
                        "rarity": rarity
                    }}
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
    
    # ==================== RECYCLE BIN OPERATIONS ====================
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
    
    async def fill_deleted_character(self, character_id: int, character: Character) -> bool:
        """Replace a deleted character with new character data"""
        try:
            # Check if character exists in deleted collection
            deleted_char = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.find_one({"character_id": character_id})
            )
            
            if not deleted_char:
                return False
            
            # Remove from deleted collection
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.delete_one({"character_id": character_id})
            )
            
            # Insert new character with the same ID
            character_dict = character.to_dict()
            character_dict["character_id"] = character_id
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.insert_one(character_dict)
            )
            
            return True
            
        except PyMongoError as e:
            logger.error(f"Error filling deleted character: {e}")
            return False
    
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
    
    async def get_deleted_characters_count(self) -> int:
        """Get total number of deleted characters"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.deleted_characters.count_documents({})
        )
    
    async def get_oldest_deleted_character(self) -> Optional[Dict[str, Any]]:
        """Get the oldest deleted character (first to be deleted)"""
        try:
            character = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.find_one(
                    {}, 
                    sort=[("deleted_at", 1)]
                )
            )
            return character
        except PyMongoError as e:
            logger.error(f"Error getting oldest deleted character: {e}")
            return None
    
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
    
    # ==================== DATABASE RESET FUNCTIONS ====================
    async def add_reset_warning(self, user_id: int) -> tuple[int, datetime]:
        """Add a reset warning for a user"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.db_warnings.find_one_and_update(
                    {"_id": "reset_warnings"},
                    {
                        "$set": {
                            f"warnings.{user_id}.last_warning": datetime.utcnow(),
                            "last_warning": datetime.utcnow()
                        },
                        "$inc": {f"warnings.{user_id}.count": 1}
                    },
                    upsert=True,
                    return_document=True
                )
            )
            
            warnings = result.get("warnings", {})
            user_warnings = warnings.get(str(user_id), {})
            warning_count = user_warnings.get("count", 1)
            
            return warning_count, datetime.utcnow()
            
        except PyMongoError as e:
            logger.error(f"Error adding reset warning: {e}")
            return 1, datetime.utcnow()
    
    async def get_reset_warnings(self, user_id: int) -> tuple[int, Optional[datetime]]:
        """Get reset warnings for a user"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.db_warnings.find_one({"_id": "reset_warnings"})
            )
            
            if result and "warnings" in result:
                warnings = result["warnings"]
                user_warnings = warnings.get(str(user_id), {})
                warning_count = user_warnings.get("count", 0)
                last_warning = user_warnings.get("last_warning")
                if last_warning and isinstance(last_warning, str):
                    last_warning = datetime.fromisoformat(last_warning.replace('Z', '+00:00'))
                return warning_count, last_warning
            
            return 0, None
            
        except PyMongoError as e:
            logger.error(f"Error getting reset warnings: {e}")
            return 0, None
    
    async def clear_reset_warnings(self, user_id: int) -> bool:
        """Clear reset warnings for a user"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.db_warnings.update_one(
                    {"_id": "reset_warnings"},
                    {"$unset": {f"warnings.{user_id}": ""}}
                )
            )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error clearing reset warnings: {e}")
            return False
    
    async def reset_database(self) -> bool:
        """Reset the entire database (clear all collections)"""
        try:
            # Drop all collections
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.drop()
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.drop()
            )
            
            # Reset counter
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.counters.delete_one({"_id": "character_id"})
            )
            
            # Reinitialize counter
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.counters.insert_one({"_id": "character_id", "seq": 0})
            )
            
            # Clear all warnings
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.db_warnings.delete_one({"_id": "reset_warnings"})
            )
            
            # Reinitialize warnings
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.db_warnings.insert_one({
                    "_id": "reset_warnings",
                    "warnings": {},
                    "last_warning": None
                })
            )
            
            logger.info("Database reset successfully")
            return True
            
        except PyMongoError as e:
            logger.error(f"Error resetting database: {e}")
            return False
    
    # ==================== SEARCH AND LIST OPERATIONS ====================
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
            
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.deleted_characters.find(search_filter)
                             .sort("deleted_at", -1)
                             .skip(skip)
                             .limit(config.ITEMS_PER_PAGE))
            )
            
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
            
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find(
                    {"rarity": rarity_name}
                ).skip(skip).limit(config.ITEMS_PER_PAGE))
            )
            
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.count_documents({"rarity": rarity_name})
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching characters by rarity: {e}")
            return [], 0
    
    async def get_all_characters_paginated(self, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get all active characters with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({})
                             .sort("character_id", 1)
                             .skip(skip)
                             .limit(config.ITEMS_PER_PAGE))
            )
            
            total_count = await self.get_character_count()
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching paginated characters: {e}")
            return [], 0
    
    async def get_deleted_characters(self, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get deleted characters with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.deleted_characters.find({})
                             .sort("deleted_at", -1)
                             .skip(skip)
                             .limit(config.ITEMS_PER_PAGE))
            )
            
            total_count = await self.get_deleted_characters_count()
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching deleted characters: {e}")
            return [], 0
    
    async def get_user_characters_paginated(self, user_id: int, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get all active characters uploaded by a user with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({"added_by": user_id})
                             .skip(skip)
                             .limit(config.ITEMS_PER_PAGE))
            )
            
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.count_documents({"added_by": user_id})
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching user characters: {e}")
            return [], 0
    
    async def get_user_deleted_characters(self, user_id: int, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get deleted characters uploaded by a user with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.deleted_characters.find({"added_by": user_id})
                             .sort("deleted_at", -1)
                             .skip(skip)
                             .limit(config.ITEMS_PER_PAGE))
            )
            
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.deleted_characters.count_documents({"added_by": user_id})
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching user deleted characters: {e}")
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
            
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find(search_filter)
                             .skip(skip)
                             .limit(config.ITEMS_PER_PAGE))
            )
            
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.count_documents(search_filter)
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error searching characters: {e}")
            return [], 0
    
    # ==================== STATISTICS ====================
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
    
    # ==================== SUDO USER OPERATIONS ====================
    async def add_sudo_user(self, user_id: int, permissions: List[str]) -> bool:
        """Add a sudo user with specific permissions"""
        try:
            sudo_doc = {
                "user_id": user_id,
                "permissions": permissions,
                "added_at": datetime.utcnow(),
                "added_by": config.OWNER_ID
            }
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.update_one(
                    {"user_id": user_id},
                    {"$set": sudo_doc},
                    upsert=True
                )
            )
            return True
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
    
    async def get_sudo_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get sudo user details"""
        try:
            sudo_user = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.find_one({"user_id": user_id})
            )
            return sudo_user
        except PyMongoError as e:
            logger.error(f"Error getting sudo user: {e}")
            return None
    
    async def get_all_sudo_users(self) -> List[Dict[str, Any]]:
        """Get all sudo users"""
        try:
            sudo_users = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.sudo_users.find({}))
            )
            return sudo_users
        except PyMongoError as e:
            logger.error(f"Error getting sudo users: {e}")
            return []
    
    async def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has specific permission"""
        try:
            if user_id == config.OWNER_ID:
                return True
            
            sudo_user = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.find_one({"user_id": user_id})
            )
            
            if not sudo_user:
                return False
            
            permissions = sudo_user.get("permissions", [])
            return permission in permissions
            
        except PyMongoError as e:
            logger.error(f"Error checking permission: {e}")
            return False
    
    async def update_sudo_permissions(self, user_id: int, permissions: List[str]) -> bool:
        """Update sudo user permissions"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.update_one(
                    {"user_id": user_id},
                    {"$set": {"permissions": permissions}}
                )
            )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Error updating sudo permissions: {e}")
            return False

# Global database instance
db = MongoDB()

# ==================== HELPERS CLASS ====================
class UploadService:
    """Handles media uploads to Catbox.moe"""
    
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
        info = f"👤 **Name:** {character_data.get('char_name', 'N/A')}\n"
        info += f"🎞️ **Anime:** {character_data.get('anime_name', 'N/A')}\n"
        info += f"🏅 **Rarity:** {character_data.get('rarity', 'N/A')}\n"
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
        info += f"🆔 **ID:** `{character_data.get('character_id', 'N/A')}`\n"
        
        if character_data.get('timestamp'):
            timestamp = character_data['timestamp']
            if isinstance(timestamp, datetime):
                info += f"📅 **Originally Added:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if character_data.get('deleted_at'):
            deleted_at = character_data['deleted_at']
            if isinstance(deleted_at, datetime):
                info += f"🗑️ **Deleted On:** {deleted_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
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
        # Extract emoji from rarity string (first character)
        if rarity_name and len(rarity_name) > 0:
            # Find the first character that's not a letter or number (likely emoji)
            for char in rarity_name:
                if not char.isalnum() and char not in ' .-_':
                    return char
        return "⚪"
    
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
        
        # Add main rarities in 2 columns
        row = []
        for rarity_num, rarity_name in config.RARITY_MAP.items():
            emoji = Helpers.get_rarity_emoji(rarity_name)
            button = InlineKeyboardButton(
                f"{emoji} {rarity_num}",
                callback_data=f"rarity_{rarity_num}_{current_view}"
            )
            row.append(button)
            
            # Every 2 buttons, start a new row
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        # Add any remaining buttons
        if row:
            keyboard.append(row)
        
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
    def create_permission_keyboard(user_id: int, current_permissions: Set[str] = None) -> InlineKeyboardMarkup:
        """Create keyboard for selecting sudo permissions"""
        keyboard = []
        
        if current_permissions is None:
            current_permissions = set()
        
        # Create permission buttons (2 per row)
        row = []
        for perm_key, perm_desc in config.PERMISSIONS.items():
            # Create button with checkbox
            checked = "✅" if perm_key in current_permissions else "⬜"
            button_text = f"{checked} {perm_desc}"
            
            button = InlineKeyboardButton(
                button_text,
                callback_data=f"toggle_perm_{user_id}_{perm_key}"
            )
            row.append(button)
            
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        # Add action buttons
        keyboard.append([
            InlineKeyboardButton("✅ Save Permissions", callback_data=f"save_perms_{user_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_perms")
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
            message += f"{i}. **{char.get('char_name', 'Unknown')}** - {char.get('anime_name', 'Unknown')}\n"
            message += f"   {emoji} {char.get('rarity', 'Unknown')} | ID: `{char.get('character_id', 'N/A')}`\n\n"
        
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
            
            # Calculate days since deletion
            days_ago = 0
            if char.get('deleted_at') and isinstance(char['deleted_at'], datetime):
                days_ago = (datetime.utcnow() - char['deleted_at']).days
            
            message += f"{i}. **{char.get('char_name', 'Unknown')}** - {char.get('anime_name', 'Unknown')}\n"
            message += f"   {emoji} {char.get('rarity', 'Unknown')}\n"
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
            elif action == "filled":
                log_message = (
                    f"🔄 **Deleted Character Slot Filled!**\n\n"
                    f"♻️ **Reused ID:** {character_data['character_id']}\n"
                    f"👤 **New Name:** {character_data['char_name']}\n"
                    f"🎞️ **New Anime:** {character_data['anime_name']}\n"
                    f"🏅 **New Rarity:** {character_data['rarity']}\n"
                )
            else:
                log_message = (
                    f"👤 **Name:** {character_data['char_name']}\n"
                    f"🎞️ **Anime:** {character_data['anime_name']}\n"
                    f"🏅 **Rarity:** {character_data['rarity']}\n"
                )
            
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
    def parse_rarity(rarity_input: str) -> Optional[str]:
        """Parse rarity input for new rarity system (1-14)"""
        try:
            rarity_num = int(rarity_input.strip())
            if 1 <= rarity_num <= 14:
                return config.RARITY_MAP[rarity_num]
            return None
        except (ValueError, KeyError):
            return None
    
    @staticmethod
    def is_owner(user_id: int) -> bool:
        """Check if user is bot owner"""
        return user_id == config.OWNER_ID

helpers = Helpers()

# ==================== MAIN BOT CLASS ====================
class CharacterBot:
    """Main bot class with all features"""
    
    def __init__(self):
        self.client = Client(
            "character_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )
        self.user_states = {}
        self.reset_warnings = {}  # Track reset warnings per user
        self._register_handlers()
    
    # ==================== COMMAND HANDLERS ====================
    def _register_handlers(self):
        """Register all message and callback handlers"""
        
        # ========== START COMMAND ==========
        @self.client.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            """Handle /start command"""
            welcome_text = (
                "👋 **Welcome to Character Database Bot!**\n\n"
                "**Complete Bot with All Features:**\n\n"
                "📤 **UPLOAD SYSTEM:**\n"
                "• Upload characters with media files\n"
                "• Supports photos, videos, audio, documents\n"
                "• Uses new rarity system (1-14)\n"
                "• Automatically posts to @capture_database\n\n"
                "📚 **VIEWING SYSTEM:**\n"
                "• Browse characters by rarity\n"
                "• Search characters by name or anime\n"
                "• View character details and statistics\n"
                "• Paginated browsing\n\n"
                "🗑️ **RECYCLE BIN SYSTEM:**\n"
                "• Deleted characters go to recycle bin\n"
                "• Restore deleted characters anytime\n"
                "• Auto-cleanup after 30 days\n"
                "• View deleted character history\n\n"
                "🔄 **FILL SYSTEM:**\n"
                "• Fill deleted character slots with new characters\n"
                "• Reuse deleted character IDs\n"
                "• Maintains ID continuity\n\n"
                "👑 **SUDO SYSTEM:**\n"
                "• Granular permission control\n"
                "• Different access levels\n"
                "• Inline permission management\n\n"
                "**Main Commands:**\n"
                "• /menu - Browse character database\n"
                "• /upload - Upload new character\n"
                "• /fill - Fill deleted slot\n"
                "• /restore - Restore deleted character\n"
                "• /deleted - View recycle bin\n"
                "• /search - Search characters\n"
                "• /stats - View statistics\n"
                "• /help - Show detailed help\n"
                "• /sudolist - View sudo users (Owner only)\n"
                "• /addsudo - Add sudo user (Owner only)\n"
                "• /removesudo - Remove sudo user (Owner only)\n\n"
                "**New Rarity System (1-14):**\n"
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
                "14. 🎤 Celebrity"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")],
                [InlineKeyboardButton("📤 Upload Character", callback_data="upload_help")],
                [InlineKeyboardButton("🔄 Fill Deleted Slot", callback_data="fill_example")],
                [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
                [InlineKeyboardButton("ℹ️ Help Guide", callback_data="help_main")]
            ])
            
            await message.reply_text(welcome_text, reply_markup=keyboard)
        
        # ========== HELP COMMAND ==========
        @self.client.on_message(filters.command("help"))
        async def help_command(client: Client, message: Message):
            """Show help message"""
            help_text = (
                "ℹ️ **Character Bot Help Guide**\n\n"
                "📤 **UPLOADING CHARACTERS:**\n"
                "1. Send a photo/video/audio/document\n"
                "2. Reply to it with: `/upload \"Character Name\" \"Anime Name\" Rarity`\n\n"
                "**Examples:**\n"
                "• `/upload \"Ichigo Kurosaki\" Bleach 3`\n"
                "• `/upload \"Goku\" \"Dragon Ball\" 10`\n\n"
                "**Rarity Numbers (1-14):**\n"
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
                "🔄 **FILLING DELETED SLOTS:**\n"
                "• `/fill ID \"Character Name\" \"Anime Name\" Rarity`\n"
                "• `/fill oldest \"Character Name\" \"Anime Name\" Rarity`\n"
                "• Reuses deleted character IDs from recycle bin\n\n"
                "🗑️ **RECYCLE BIN SYSTEM:**\n"
                "• /deleted - View deleted characters\n"
                "• /restore ID - Restore a deleted character\n"
                "• /searchdeleted query - Search deleted characters\n"
                "• /delete ID - Move character to recycle bin\n"
                "• Deleted characters auto-clean after 30 days\n\n"
                "📚 **BROWSING CHARACTERS:**\n"
                "• /menu - Browse by rarity\n"
                "• /search query - Search characters\n"
                "• /info ID - View character details\n"
                "• /myuploads - View your uploads\n"
                "• /stats - View database statistics\n\n"
                "⚙️ **EDITING CHARACTERS:**\n"
                "• /edit ID \"New Name\" \"New Anime\" Rarity\n"
                "• /editmedia ID - Edit media (reply to new media)\n\n"
                "👑 **SUDO MANAGEMENT (Owner only):**\n"
                "• /addsudo @username - Add sudo user\n"
                "• /removesudo @username - Remove sudo user\n"
                "• /sudolist - List all sudo users\n"
                "• /setsudo @username - Set specific permissions\n\n"
                "⚠️ **DATABASE RESET (Owner only):**\n"
                "• /reset - Reset database (requires 3 confirmations)\n\n"
                "**Note:** Commands require appropriate sudo permissions."
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")],
                [InlineKeyboardButton("📤 Upload Example", callback_data="upload_example")],
                [InlineKeyboardButton("🔄 Fill Example", callback_data="fill_example")],
                [InlineKeyboardButton("🗑️ Recycle Bin", callback_data="deleted_list_0_main")],
                [InlineKeyboardButton("📊 View Stats", callback_data="stats_main")]
            ])
            
            await message.reply_text(help_text, reply_markup=keyboard)
        
        # ========== UPLOAD COMMAND (with permission check) ==========
        @self.client.on_message(filters.command("upload"))
        async def upload_command(client: Client, message: Message):
            """Handle /upload command"""
            user_id = message.from_user.id
            
            # Check authorization with permission
            if not await db.has_permission(user_id, 'upload'):
                await message.reply_text(
                    "❌ You are not authorized to upload characters.\n\n"
                    "You need 'upload' permission. Contact the bot owner for access."
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
                    "`/upload \"Character Name\" \"Anime Name\" Rarity`\n\n"
                    "**Examples:**\n"
                    "• `/upload \"Ichigo Kurosaki\" Bleach 3`\n"
                    "• `/upload \"Goku\" \"Dragon Ball\" 10`\n\n"
                    "**Rarity Numbers (1-14):**\n"
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
                    "14. 🎤 Celebrity"
                )
                return
            
            # Parse arguments
            args = message.text.split()
            if len(args) < 4:
                await message.reply_text(
                    "❌ **Invalid syntax!**\n\n"
                    "**Usage:** `/upload \"Character Name\" \"Anime Name\" Rarity`\n\n"
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
            text = text.replace('/upload', '', 1).strip()
            
            # Parse character name (might be in quotes)
            if text.startswith('"'):
                end_quote = text.find('"', 1)
                if end_quote == -1:
                    await message.reply_text("❌ Invalid format. Missing closing quote for character name.")
                    return
                char_name = text[1:end_quote]
                text = text[end_quote + 1:].strip()
            else:
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
                parts = text.split()
                if not parts:
                    await message.reply_text("❌ Missing anime name.")
                    return
                anime_name = parts[0]
                text = ' '.join(parts[1:])
            
            # The rest is rarity
            rarity_input = text.strip()
            
            if not char_name or not anime_name or not rarity_input:
                await message.reply_text("❌ Missing required parameters.")
                return
            
            # Parse rarity
            rarity_name = helpers.parse_rarity(rarity_input)
            if not rarity_name:
                await message.reply_text(
                    "❌ Invalid rarity.\n\n"
                    "**Valid Rarity Numbers (1-14):**\n"
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
                    "14. 🎤 Celebrity"
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
        
        # ========== ADDSUDO COMMAND (Owner only) ==========
        @self.client.on_message(filters.command("addsudo"))
        async def addsudo_command(client: Client, message: Message):
            """Add sudo user (Owner only)"""
            user_id = message.from_user.id
            
            if not helpers.is_owner(user_id):
                await message.reply_text("❌ Only the bot owner can use this command.")
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "👑 **Add Sudo User**\n\n"
                    "**Usage:** `/addsudo @username`\n\n"
                    "**Example:** `/addsudo @username`\n\n"
                    "**Note:** This will give the user all permissions by default.\n"
                    "Use /setsudo to set specific permissions."
                )
                return
            
            target_username = args[1].replace('@', '')
            
            try:
                # Get user from username
                target_user = await client.get_users(target_username)
                
                # Check if already sudo
                existing_sudo = await db.get_sudo_user(target_user.id)
                if existing_sudo:
                    await message.reply_text(f"❌ @{target_username} is already a sudo user.")
                    return
                
                # Add with all permissions by default
                all_permissions = list(config.PERMISSIONS.keys())
                await db.add_sudo_user(target_user.id, all_permissions)
                
                await message.reply_text(
                    f"✅ **Sudo User Added!**\n\n"
                    f"👤 **User:** @{target_username} (ID: {target_user.id})\n"
                    f"🔑 **Permissions:** All permissions granted\n\n"
                    f"Use /setsudo to modify specific permissions."
                )
                
                logger.info(f"Sudo user added: @{target_username} ({target_user.id})")
                
            except Exception as e:
                logger.error(f"Error adding sudo user: {e}")
                await message.reply_text("❌ Error adding sudo user. Make sure the username is correct.")
        
        # ========== REMOVESUDO COMMAND (Owner only) ==========
        @self.client.on_message(filters.command(["removesudo", "delsudo"]))
        async def removesudo_command(client: Client, message: Message):
            """Remove sudo user (Owner only)"""
            user_id = message.from_user.id
            
            if not helpers.is_owner(user_id):
                await message.reply_text("❌ Only the bot owner can use this command.")
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "👑 **Remove Sudo User**\n\n"
                    "**Usage:** `/removesudo @username`\n\n"
                    "**Example:** `/removesudo @username`"
                )
                return
            
            target_username = args[1].replace('@', '')
            
            try:
                # Get user from username
                target_user = await client.get_users(target_username)
                
                # Remove sudo
                removed = await db.remove_sudo_user(target_user.id)
                
                if removed:
                    await message.reply_text(
                        f"✅ **Sudo User Removed!**\n\n"
                        f"👤 **User:** @{target_username} (ID: {target_user.id})\n"
                        f"🔓 **Status:** All permissions revoked"
                    )
                    
                    logger.info(f"Sudo user removed: @{target_username} ({target_user.id})")
                else:
                    await message.reply_text(f"❌ @{target_username} is not a sudo user.")
                    
            except Exception as e:
                logger.error(f"Error removing sudo user: {e}")
                await message.reply_text("❌ Error removing sudo user. Make sure the username is correct.")
        
        # ========== SUDOLIST COMMAND (Owner only) ==========
        @self.client.on_message(filters.command(["sudolist", "listsudo", "sudoers"]))
        async def sudolist_command(client: Client, message: Message):
            """List all sudo users (Owner only)"""
            user_id = message.from_user.id
            
            if not helpers.is_owner(user_id):
                await message.reply_text("❌ Only the bot owner can use this command.")
                return
            
            sudo_users = await db.get_all_sudo_users()
            
            if not sudo_users:
                await message.reply_text("👑 **No Sudo Users Found**\n\nNo sudo users have been added yet.")
                return
            
            message_text = "👑 **Sudo Users List**\n\n"
            
            for i, sudo in enumerate(sudo_users, 1):
                user_id = sudo.get('user_id')
                permissions = sudo.get('permissions', [])
                added_at = sudo.get('added_at', datetime.utcnow())
                
                # Try to get username
                try:
                    username = await helpers.get_username_from_id(client, user_id)
                except:
                    username = f"User {user_id}"
                
                # Format permissions
                perm_text = ', '.join(permissions[:3])
                if len(permissions) > 3:
                    perm_text += f" (+{len(permissions)-3} more)"
                
                # Format date
                if isinstance(added_at, datetime):
                    date_str = added_at.strftime('%Y-%m-%d')
                else:
                    date_str = "Unknown"
                
                message_text += f"{i}. {username}\n"
                message_text += f"   🆔: {user_id}\n"
                message_text += f"   🔑: {perm_text}\n"
                message_text += f"   📅: {date_str}\n\n"
            
            # Add buttons to manage sudo users
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Sudo User", callback_data="add_sudo_ui")],
                [InlineKeyboardButton("⚙️ Manage Permissions", callback_data="manage_perms_ui")]
            ])
            
            await message.reply_text(message_text, reply_markup=keyboard)
        
        # ========== SETSUDO COMMAND (Owner only) ==========
        @self.client.on_message(filters.command(["setsudo", "setpermissions"]))
        async def setsudo_command(client: Client, message: Message):
            """Set specific permissions for sudo user (Owner only)"""
            user_id = message.from_user.id
            
            if not helpers.is_owner(user_id):
                await message.reply_text("❌ Only the bot owner can use this command.")
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "👑 **Set Sudo Permissions**\n\n"
                    "**Usage:** `/setsudo @username`\n\n"
                    "**Example:** `/setsudo @username`\n\n"
                    "This will open an inline keyboard to select specific permissions."
                )
                return
            
            target_username = args[1].replace('@', '')
            
            try:
                # Get user from username
                target_user = await client.get_users(target_username)
                
                # Check if user exists in sudo
                sudo_user = await db.get_sudo_user(target_user.id)
                current_permissions = set(sudo_user.get('permissions', [])) if sudo_user else set()
                
                # Create permission selection keyboard
                keyboard = helpers.create_permission_keyboard(target_user.id, current_permissions)
                
                await message.reply_text(
                    f"⚙️ **Set Permissions for @{target_username}**\n\n"
                    f"**Current permissions:** {len(current_permissions)}\n"
                    f"Click on permissions to toggle them, then click 'Save Permissions'.\n\n"
                    f"**Available Permissions:**\n"
                    f"• upload - Upload characters\n"
                    f"• delete - Delete characters\n"
                    f"• edit - Edit characters\n"
                    f"• restore - Restore deleted characters\n"
                    f"• fill - Fill deleted slots\n"
                    f"• view_deleted - View recycle bin\n"
                    f"• add_sudo - Add sudo users\n"
                    f"• remove_sudo - Remove sudo users\n"
                    f"• reset_db - Reset database",
                    reply_markup=keyboard
                )
                
            except Exception as e:
                logger.error(f"Error setting sudo permissions: {e}")
                await message.reply_text("❌ Error setting permissions. Make sure the username is correct.")
        
        # ========== RESET COMMAND (Owner only with warnings) ==========
        @self.client.on_message(filters.command("reset"))
        async def reset_command(client: Client, message: Message):
            """Reset database with 3 warnings (Owner only)"""
            user_id = message.from_user.id
            
            if not helpers.is_owner(user_id):
                await message.reply_text("❌ Only the bot owner can reset the database.")
                return
            
            # Get current warnings
            warning_count, last_warning = await db.get_reset_warnings(user_id)
            
            # Check if warnings have expired (24 hours)
            warning_expired = False
            if last_warning:
                hours_since_warning = (datetime.utcnow() - last_warning).total_seconds() / 3600
                if hours_since_warning > 24:
                    warning_expired = True
                    await db.clear_reset_warnings(user_id)
                    warning_count = 0
            
            warnings_needed = 3 - warning_count
            
            if warnings_needed <= 0:
                # All warnings given, show final confirmation
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🚨 YES, RESET DATABASE", callback_data="confirm_reset"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset")
                    ]
                ])
                
                total_chars = await db.get_character_count()
                total_deleted = await db.get_deleted_characters_count()
                
                await message.reply_text(
                    f"⚠️ **FINAL WARNING - DATABASE RESET** ⚠️\n\n"
                    f"🚨 **This is your FINAL warning!**\n\n"
                    f"📊 **Current Database Stats:**\n"
                    f"• Active Characters: {total_chars}\n"
                    f"• Deleted Characters: {total_deleted}\n"
                    f"• Total: {total_chars + total_deleted}\n\n"
                    f"❌ **THIS ACTION WILL:**\n"
                    f"1. Delete ALL characters\n"
                    f"2. Delete ALL deleted characters\n"
                    f"3. Reset character ID counter to 0\n"
                    f"4. Clear ALL data\n\n"
                    f"🔥 **THIS ACTION IS IRREVERSIBLE!**\n\n"
                    f"Are you ABSOLUTELY sure you want to reset the database?",
                    reply_markup=keyboard
                )
                
            else:
                # Add warning
                new_warning_count, _ = await db.add_reset_warning(user_id)
                
                total_chars = await db.get_character_count()
                total_deleted = await db.get_deleted_characters_count()
                
                if new_warning_count == 1:
                    warning_text = "FIRST"
                elif new_warning_count == 2:
                    warning_text = "SECOND"
                else:
                    warning_text = "THIRD"
                
                await message.reply_text(
                    f"⚠️ **{warning_text} WARNING - DATABASE RESET** ⚠️\n\n"
                    f"🚨 **Warning {new_warning_count}/3**\n\n"
                    f"📊 **Current Database Stats:**\n"
                    f"• Active Characters: {total_chars}\n"
                    f"• Deleted Characters: {total_deleted}\n"
                    f"• Total: {total_chars + total_deleted}\n\n"
                    f"❌ **Resetting will delete ALL data!**\n\n"
                    f"⚠️ **You need {3 - new_warning_count} more warning(s) before you can reset.**\n"
                    f"Send `/reset` again to continue."
                )
        
        # ========== FILL COMMAND (with permission check) ==========
        @self.client.on_message(filters.command("fill"))
        async def fill_command(client: Client, message: Message):
            """Handle /fill command - add character in place of deleted character"""
            user_id = message.from_user.id
            
            # Check authorization with permission
            if not await db.has_permission(user_id, 'fill'):
                await message.reply_text(
                    "❌ You are not authorized to use the fill command.\n\n"
                    "You need 'fill' permission. Contact the bot owner for access."
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
                    "🔄 **Fill Deleted Character Slot**\n\n"
                    "**Usage:** Reply to a media file with:\n"
                    "`/fill character_id \"Character Name\" \"Anime Name\" Rarity`\n\n"
                    "**Examples:**\n"
                    "• `/fill 123 \"Ichigo Kurosaki\" Bleach 3`\n"
                    "• `/fill 456 \"Goku\" \"Dragon Ball\" 10`\n\n"
                    "**To fill oldest deleted slot:**\n"
                    "`/fill oldest \"Character Name\" \"Anime Name\" Rarity`\n\n"
                    "**To see available deleted IDs:**\n"
                    "Use `/deleted` to view recycle bin\n"
                    "Use `/searchdeleted` to search deleted characters"
                )
                return
            
            # Parse arguments
            args = message.text.split()
            if len(args) < 4:
                await message.reply_text(
                    "❌ **Invalid syntax!**\n\n"
                    "**Usage:** `/fill character_id \"Character Name\" \"Anime Name\" Rarity`\n\n"
                    "**Examples:**\n"
                    "• `/fill 123 \"Ichigo Kurosaki\" Bleach 3`\n"
                    "• `/fill oldest \"Naruto Uzumaki\" Naruto 4`\n\n"
                    "**Note:** Use quotes for names with spaces\n"
                    "Use `oldest` to fill the oldest deleted character slot."
                )
                return
            
            # Parse target ID (could be "oldest" or a number)
            target_id_input = args[1].lower()
            
            if target_id_input == "oldest":
                # Get the oldest deleted character
                oldest_deleted = await db.get_oldest_deleted_character()
                if not oldest_deleted:
                    await message.reply_text("❌ No deleted characters found in recycle bin!")
                    return
                character_id = oldest_deleted.get("character_id")
            else:
                try:
                    character_id = int(target_id_input)
                except ValueError:
                    await message.reply_text("❌ Invalid character ID. Must be a number or 'oldest'.")
                    return
                
                # Check if character exists in deleted collection
                deleted_char = await db.get_deleted_character_by_id(character_id)
                if not deleted_char:
                    # Check if ID is already in use
                    active_char = await db.get_character_by_id(character_id)
                    if active_char:
                        await message.reply_text(
                            f"❌ Character ID `{character_id}` is already in use!\n\n"
                            f"**Current Character:**\n"
                            f"• Name: {active_char.get('char_name')}\n"
                            f"• Anime: {active_char.get('anime_name')}\n\n"
                            f"Use a different ID or delete the character first."
                        )
                    else:
                        await message.reply_text(
                            f"❌ Character ID `{character_id}` not found in recycle bin!\n\n"
                            f"**Available options:**\n"
                            f"• Use `/deleted` to view deleted characters\n"
                            f"• Use `/fill oldest` to fill the oldest deleted slot\n"
                            f"• Use a different deleted character ID"
                        )
                    return
            
            # Parse character details
            text = message.text
            text = text.replace(f'/fill {args[1]}', '', 1).strip()
            
            # Parse character name
            char_name = ""
            if text.startswith('"'):
                end_quote = text.find('"', 1)
                if end_quote == -1:
                    await message.reply_text("❌ Invalid format. Missing closing quote for character name.")
                    return
                char_name = text[1:end_quote]
                text = text[end_quote + 1:].strip()
            else:
                parts = text.split()
                char_name = parts[0]
                text = ' '.join(parts[1:])
            
            # Parse anime name
            anime_name = ""
            if text.startswith('"'):
                end_quote = text.find('"', 1)
                if end_quote == -1:
                    await message.reply_text("❌ Invalid format. Missing closing quote for anime name.")
                    return
                anime_name = text[1:end_quote]
                text = text[end_quote + 1:].strip()
            else:
                parts = text.split()
                if not parts:
                    await message.reply_text("❌ Missing anime name.")
                    return
                anime_name = parts[0]
                text = ' '.join(parts[1:])
            
            # Parse rarity
            rarity_input = text.strip()
            rarity_name = helpers.parse_rarity(rarity_input)
            
            if not rarity_name:
                await message.reply_text(
                    "❌ Invalid rarity.\n\n"
                    "**Valid Rarity Numbers (1-14):**\n"
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
                    "14. 🎤 Celebrity"
                )
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
            
            # Start fill process
            status_msg = await message.reply_text(f"🔄 Filling character slot #{character_id}...")
            
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
            
            # Create character object
            character = Character(
                char_name=char_name,
                anime_name=anime_name,
                rarity=rarity_name,
                character_id=character_id,
                media_url=media_url,
                media_type=media_type,
                added_by=user_id
            )
            
            try:
                # Fill the deleted character slot
                filled = await db.fill_deleted_character(character_id, character)
                
                if filled:
                    # Send to log channel
                    username = message.from_user.username or message.from_user.first_name or "Unknown"
                    await helpers.send_to_log_channel(
                        client, character.to_dict(), username, user_id, "filled"
                    )
                    
                    # Get info about the replaced character
                    replaced_char = await db.get_deleted_character_by_id(character_id)
                    replaced_info = ""
                    if replaced_char:
                        replaced_info = (
                            f"\n🔄 **Replaced Deleted Character:**\n"
                            f"• Name: {replaced_char.get('char_name', 'Unknown')}\n"
                            f"• Anime: {replaced_char.get('anime_name', 'Unknown')}\n"
                            f"• Deleted on: {replaced_char.get('deleted_at', 'Unknown')}\n"
                        )
                    
                    # Success message
                    success_text = (
                        f"🔄 **Character Slot #{character_id} Filled Successfully!**\n\n"
                        f"👤 **New Character:** {char_name}\n"
                        f"🎞️ **Anime:** {anime_name}\n"
                        f"🏅 **Rarity:** {rarity_name}\n"
                        f"\n📸 **Media:** Uploaded to Catbox\n"
                        f"📢 **Posted to:** @capture_database\n"
                        f"🆔 **Character ID:** `{character_id}`\n"
                        f"{replaced_info}\n"
                        f"✅ **Slot has been successfully reused!**"
                    )
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("👁️ View Character", callback_data=f"info_{character_id}")],
                        [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
                        [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")]
                    ])
                    
                    await update_status(success_text)
                    await status_msg.edit_reply_markup(keyboard)
                    
                    logger.info(f"Character slot {character_id} filled by user {user_id}")
                else:
                    await update_status(f"❌ Failed to fill character slot #{character_id}. It may no longer exist in recycle bin.")
                    
            except Exception as e:
                logger.error(f"Error filling character: {e}")
                await update_status("❌ Error filling character slot. Please try again.")
        
        # ========== RESTORE COMMAND (with permission check) ==========
        @self.client.on_message(filters.command("restore"))
        async def restore_command(client: Client, message: Message):
            """Handle /restore command - restore deleted character"""
            user_id = message.from_user.id
            
            # Check authorization with permission
            if not await db.has_permission(user_id, 'restore'):
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
        
        # ========== DELETED COMMAND (with permission check) ==========
        @self.client.on_message(filters.command(["deleted", "recyclebin", "trash"]))
        async def deleted_command(client: Client, message: Message):
            """Show deleted characters (recycle bin)"""
            user_id = message.from_user.id
            
            # Check authorization with permission
            if not await db.has_permission(user_id, 'view_deleted'):
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
        
        # ========== SEARCHDELETED COMMAND (with permission check) ==========
        @self.client.on_message(filters.command(["searchdeleted", "finddeleted"]))
        async def searchdeleted_command(client: Client, message: Message):
            """Search deleted characters"""
            user_id = message.from_user.id
            
            # Check authorization with permission
            if not await db.has_permission(user_id, 'view_deleted'):
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
            
            # Add back button
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    "🔙 Back to Menu",
                    callback_data="menu_main"
                )
            ])
            
            await message.reply_text(message_text, reply_markup=keyboard)
        
        # ========== MENU COMMAND ==========
        @self.client.on_message(filters.command("menu"))
        async def menu_command(client: Client, message: Message):
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
            await message.reply_text(menu_text, reply_markup=keyboard)
        
        # ========== SEARCH COMMAND ==========
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
            for char in characters[:5]:
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
        
        # ========== STATS COMMAND ==========
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
            for rarity_num, rarity_name in config.RARITY_MAP.items():
                count = rarity_stats.get(rarity_name, 0)
                percentage = (count / total_chars * 100) if total_chars > 0 else 0
                emoji = helpers.get_rarity_emoji(rarity_name)
                stats_text += f"{emoji} **{rarity_name.split(' ', 1)[-1]}:** {count} ({percentage:.1f}%)\n"
            
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
        
        # ========== MYUPLOADS COMMAND ==========
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
            for char in characters[:5]:
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
        
        # ========== INFO COMMAND ==========
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
        
        # ========== EDIT COMMAND (with permission check) ==========
        @self.client.on_message(filters.command("edit"))
        async def edit_command(client: Client, message: Message):
            """Handle /edit command - edit character details"""
            user_id = message.from_user.id
            
            # Check authorization with permission
            if not await db.has_permission(user_id, 'edit'):
                await message.reply_text("❌ You are not authorized to edit characters.")
                return
            
            args = message.text.split()
            if len(args) < 5:
                await message.reply_text(
                    "✏️ **Edit Character**\n\n"
                    "**Usage:** `/edit ID \"New Name\" \"New Anime\" Rarity`\n\n"
                    "**Examples:**\n"
                    "• `/edit 123 \"Naruto Uzumaki\" Naruto 3`\n"
                    "• `/edit 123 \"Sakura\" Naruto 10`\n\n"
                    "**Note:** Use quotes for names with spaces"
                )
                return
            
            try:
                character_id = int(args[1])
                
                # Simple parsing similar to upload
                text = message.text
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
                new_rarity = helpers.parse_rarity(rarity_input)
                
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
                    rarity=new_rarity
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
        
        # ========== EDITMEDIA COMMAND (with permission check) ==========
        @self.client.on_message(filters.command("editmedia"))
        async def editmedia_command(client: Client, message: Message):
            """Handle /editmedia command - edit character media"""
            user_id = message.from_user.id
            
            # Check authorization with permission
            if not await db.has_permission(user_id, 'edit'):
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
        
        # ========== DELETE COMMAND (with permission check) ==========
        @self.client.on_message(filters.command(["delete", "remove", "del"]))
        async def delete_command(client: Client, message: Message):
            """Handle /delete command - move character to recycle bin"""
            user_id = message.from_user.id
            
            # Check authorization with permission
            if not await db.has_permission(user_id, 'delete'):
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
        
        # ========== CALLBACK QUERY HANDLER ==========
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
                        
                        # Show characters for this rarity
                        characters, total_count = await db.get_characters_by_rarity(
                            config.RARITY_MAP[rarity_num], 0
                        )
                        
                        if not characters:
                            await callback_query.answer(f"No characters found for rarity {rarity_num}", show_alert=True)
                            return
                        
                        total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
                        
                        message_text = helpers.format_character_list(
                            characters, 0, total_count,
                            f"{config.RARITY_MAP[rarity_num]} Characters"
                        )
                        
                        keyboard = helpers.create_pagination_keyboard(0, total_pages, "rarity", f"{rarity_num}_{current_view}")
                        
                        buttons = []
                        for char in characters[:3]:
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
                        
                        keyboard.inline_keyboard.append([
                            InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
                        ])
                        
                        await callback_query.message.edit_text(message_text, reply_markup=keyboard)
                        await callback_query.answer()
                
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
                
                # Pagination for search
                elif data.startswith("search_page_"):
                    parts = data.split("_")
                    page = int(parts[2])
                    query = '_'.join(parts[3:])
                    await self._show_search_results(client, callback_query, query, page)
                
                # Pagination for deleted search
                elif data.startswith("search_deleted_page_"):
                    parts = data.split("_")
                    page = int(parts[3])
                    query = '_'.join(parts[4:])
                    characters, total_count = await db.search_deleted_characters(query, page)
                    
                    if not characters:
                        await callback_query.answer("No more results", show_alert=True)
                        return
                    
                    total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
                    
                    message_text = helpers.format_deleted_character_list(characters, page, total_count)
                    message_text = f"🔍 **Search Results in Recycle Bin:**\n\n" + message_text
                    
                    keyboard = helpers.create_pagination_keyboard(page, total_pages, "search_deleted", query)
                    
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
                    
                    characters, total_count = await db.get_characters_by_rarity(
                        config.RARITY_MAP[rarity_num], page
                    )
                    
                    if not characters:
                        await callback_query.answer("No more characters", show_alert=True)
                        return
                    
                    total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
                    
                    message_text = helpers.format_character_list(
                        characters, page, total_count,
                        f"{config.RARITY_MAP[rarity_num]} Characters"
                    )
                    
                    keyboard = helpers.create_pagination_keyboard(page, total_pages, "rarity", f"{rarity_num}_{current_view}")
                    
                    buttons = []
                    for char in characters[:3]:
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
                    
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
                    ])
                    
                    await callback_query.message.edit_text(message_text, reply_markup=keyboard)
                    await callback_query.answer()
                
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
                    
                    # Check authorization with permission
                    if not await db.has_permission(user_id, 'delete'):
                        await callback_query.answer("You are not authorized to delete characters", show_alert=True)
                        return
                    
                    # Move to recycle bin
                    deleted = await db.soft_delete_character(character_id, user_id, "Deleted via button")
                    
                    if deleted:
                        character = await db.get_deleted_character_by_id(character_id)
                        if character:
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
                    
                    # Check authorization with permission
                    if not await db.has_permission(user_id, 'restore'):
                        await callback_query.answer("You are not authorized to restore characters", show_alert=True)
                        return
                    
                    # Restore character
                    restored = await db.restore_character(character_id)
                    
                    if restored:
                        character = await db.get_character_by_id(character_id)
                        if character:
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
                        "`/upload \"Character Name\" \"Anime Name\" Rarity`\n\n"
                        "**Example:**\n"
                        "`/upload \"Ichigo Kurosaki\" Bleach 3`\n"
                        "`/upload \"Goku\" \"Dragon Ball\" 10`\n\n"
                        "**Rarity Numbers (1-14):**\n"
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
                        "14. 🎤 Celebrity",
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
                        "`/upload \"Naruto Uzumaki\" Naruto 4`\n\n"
                        "**This would create:**\n"
                        "• Character: Naruto Uzumaki\n"
                        "• Anime: Naruto\n"
                        "• Rarity: 🟡 Legendary",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📤 Try Uploading", callback_data="upload_help")],
                            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                        ])
                    )
                    await callback_query.answer()
                
                # Fill example
                elif data == "fill_example":
                    await callback_query.message.edit_text(
                        "🔄 **Fill Deleted Character Slot Example:**\n\n"
                        "1. **Find a deleted character ID** using `/deleted`\n"
                        "2. **Send a photo** of a new character\n"
                        "3. **Reply to it with:**\n"
                        "`/fill 123 \"Sasuke Uchiha\" Naruto 4`\n\n"
                        "**This would:**\n"
                        "• Reuse deleted slot #123\n"
                        "• Create: Sasuke Uchiha (Naruto)\n"
                        "• Rarity: 🟡 Legendary\n\n"
                        "**Or use `oldest` to fill the oldest slot:**\n"
                        "`/fill oldest \"New Character\" Anime 3`\n\n"
                        "**Note:** You need 'fill' permission to use this command.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
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
                        "🔄 Fill deleted character slots\n"
                        "🔍 Search for characters\n"
                        "📊 View statistics\n\n"
                        "**Use buttons below to explore:**",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📤 Upload System", callback_data="upload_help")],
                            [InlineKeyboardButton("🔄 Fill System", callback_data="fill_example")],
                            [InlineKeyboardButton("📚 Viewing System", callback_data="menu_main")],
                            [InlineKeyboardButton("🗑️ Recycle Bin", callback_data="deleted_list_0_main")],
                            [InlineKeyboardButton("📊 Statistics", callback_data="stats_main")]
                        ])
                    )
                    await callback_query.answer()
                
                # Add sudo user UI
                elif data == "add_sudo_ui":
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Only owner can add sudo users", show_alert=True)
                        return
                    
                    await callback_query.message.edit_text(
                        "👑 **Add Sudo User**\n\n"
                        "Use the command:\n"
                        "`/addsudo @username`\n\n"
                        "This will give the user all permissions by default.\n"
                        "Use `/setsudo @username` to set specific permissions.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back to Sudo List", callback_data="sudo_list_back")],
                            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                        ])
                    )
                    await callback_query.answer()
                
                # Manage permissions UI
                elif data == "manage_perms_ui":
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Only owner can manage permissions", show_alert=True)
                        return
                    
                    await callback_query.message.edit_text(
                        "⚙️ **Manage Sudo Permissions**\n\n"
                        "Use the command:\n"
                        "`/setsudo @username`\n\n"
                        "This will open an inline keyboard to select specific permissions for the user.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back to Sudo List", callback_data="sudo_list_back")],
                            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                        ])
                    )
                    await callback_query.answer()
                
                # Back to sudo list
                elif data == "sudo_list_back":
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Unauthorized", show_alert=True)
                        return
                    
                    sudo_users = await db.get_all_sudo_users()
                    
                    if not sudo_users:
                        await callback_query.message.edit_text("👑 **No Sudo Users Found**\n\nNo sudo users have been added yet.")
                        await callback_query.answer()
                        return
                    
                    message_text = "👑 **Sudo Users List**\n\n"
                    
                    for i, sudo in enumerate(sudo_users, 1):
                        sudo_user_id = sudo.get('user_id')
                        permissions = sudo.get('permissions', [])
                        added_at = sudo.get('added_at', datetime.utcnow())
                        
                        # Try to get username
                        try:
                            username = await helpers.get_username_from_id(client, sudo_user_id)
                        except:
                            username = f"User {sudo_user_id}"
                        
                        # Format permissions
                        perm_text = ', '.join(permissions[:3])
                        if len(permissions) > 3:
                            perm_text += f" (+{len(permissions)-3} more)"
                        
                        # Format date
                        if isinstance(added_at, datetime):
                            date_str = added_at.strftime('%Y-%m-%d')
                        else:
                            date_str = "Unknown"
                        
                        message_text += f"{i}. {username}\n"
                        message_text += f"   🆔: {sudo_user_id}\n"
                        message_text += f"   🔑: {perm_text}\n"
                        message_text += f"   📅: {date_str}\n\n"
                    
                    # Add buttons to manage sudo users
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Add Sudo User", callback_data="add_sudo_ui")],
                        [InlineKeyboardButton("⚙️ Manage Permissions", callback_data="manage_perms_ui")],
                        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                    ])
                    
                    await callback_query.message.edit_text(message_text, reply_markup=keyboard)
                    await callback_query.answer()
                
                # Toggle permission
                elif data.startswith("toggle_perm_"):
                    parts = data.split("_")
                    if len(parts) != 4:
                        await callback_query.answer("Invalid permission data", show_alert=True)
                        return
                    
                    target_user_id = int(parts[2])
                    perm_key = parts[3]
                    
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Only owner can modify permissions", show_alert=True)
                        return
                    
                    # Get current permissions
                    sudo_user = await db.get_sudo_user(target_user_id)
                    if not sudo_user:
                        await callback_query.answer("User is not a sudo user", show_alert=True)
                        return
                    
                    current_permissions = set(sudo_user.get('permissions', []))
                    
                    # Toggle permission
                    if perm_key in current_permissions:
                        current_permissions.remove(perm_key)
                    else:
                        current_permissions.add(perm_key)
                    
                    # Update UI
                    keyboard = helpers.create_permission_keyboard(target_user_id, current_permissions)
                    
                    # Get username for display
                    try:
                        target_username = await helpers.get_username_from_id(client, target_user_id)
                    except:
                        target_username = f"User {target_user_id}"
                    
                    await callback_query.message.edit_reply_markup(keyboard)
                    await callback_query.answer(f"Toggled {perm_key} permission")
                
                # Save permissions
                elif data.startswith("save_perms_"):
                    target_user_id = int(data.split("_")[2])
                    
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Only owner can save permissions", show_alert=True)
                        return
                    
                    # Get current permissions from button states (we need to parse them from the message)
                    # For simplicity, we'll get them from the database and update
                    sudo_user = await db.get_sudo_user(target_user_id)
                    if not sudo_user:
                        await callback_query.answer("User is not a sudo user", show_alert=True)
                        return
                    
                    current_permissions = set(sudo_user.get('permissions', []))
                    
                    # Update in database
                    await db.update_sudo_permissions(target_user_id, list(current_permissions))
                    
                    # Get username for display
                    try:
                        target_username = await helpers.get_username_from_id(client, target_user_id)
                    except:
                        target_username = f"User {target_user_id}"
                    
                    await callback_query.message.edit_text(
                        f"✅ **Permissions Updated!**\n\n"
                        f"👤 **User:** {target_username}\n"
                        f"🔑 **Permissions:** {len(current_permissions)} permissions set\n\n"
                        f"Permissions have been saved successfully.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("👑 Back to Sudo Management", callback_data="sudo_list_back")]
                        ])
                    )
                    await callback_query.answer("Permissions saved successfully")
                
                # Cancel permission editing
                elif data == "cancel_perms":
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Unauthorized", show_alert=True)
                        return
                    
                    await callback_query.message.edit_text(
                        "❌ **Permission editing cancelled.**\n\n"
                        "No changes were made.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("👑 Back to Sudo Management", callback_data="sudo_list_back")]
                        ])
                    )
                    await callback_query.answer()
                
                # Confirm database reset
                elif data == "confirm_reset":
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Only owner can reset database", show_alert=True)
                        return
                    
                    # Check if user has permission to reset
                    if not await db.has_permission(user_id, 'reset_db'):
                        await callback_query.answer("You don't have permission to reset database", show_alert=True)
                        return
                    
                    # Get stats before reset
                    total_chars_before = await db.get_character_count()
                    total_deleted_before = await db.get_deleted_characters_count()
                    
                    # Reset database
                    reset_success = await db.reset_database()
                    
                    if reset_success:
                        # Clear warnings
                        await db.clear_reset_warnings(user_id)
                        
                        await callback_query.message.edit_text(
                            f"♻️ **DATABASE RESET COMPLETE!**\n\n"
                            f"✅ **All data has been cleared!**\n\n"
                            f"📊 **Before Reset:**\n"
                            f"• Active Characters: {total_chars_before}\n"
                            f"• Deleted Characters: {total_deleted_before}\n"
                            f"• Total: {total_chars_before + total_deleted_before}\n\n"
                            f"🆕 **After Reset:**\n"
                            f"• Active Characters: 0\n"
                            f"• Deleted Characters: 0\n"
                            f"• Character ID Counter: 0\n\n"
                            f"✨ **Database is now fresh and empty!**\n"
                            f"You can start uploading new characters from ID 1."
                        )
                        
                        logger.info(f"Database reset by owner {user_id}")
                    else:
                        await callback_query.message.edit_text(
                            "❌ **Database reset failed!**\n\n"
                            "An error occurred while resetting the database."
                        )
                    
                    await callback_query.answer()
                
                # Cancel reset
                elif data == "cancel_reset":
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("Unauthorized", show_alert=True)
                        return
                    
                    # Clear warnings
                    await db.clear_reset_warnings(user_id)
                    
                    await callback_query.message.edit_text(
                        "✅ **Database reset cancelled.**\n\n"
                        "No changes were made to the database."
                    )
                    await callback_query.answer()
                
                # Delete confirmation (old system)
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
    
    # ==================== VIEWING METHODS ====================
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
    
    async def _show_all_characters(self, client: Client, callback_query: CallbackQuery, page: int, current_view: str):
        """Show all active characters"""
        characters, total_count = await db.get_all_characters_paginated(page)
        
        if not characters:
            await callback_query.answer("No characters found", show_alert=True)
            return
        
        total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
        
        message_text = helpers.format_character_list(
            characters, page, total_count, 
            "All Active Characters"
        )
        
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "all", current_view)
        
        buttons = []
        for char in characters[:3]:
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
        
        message_text = helpers.format_deleted_character_list(characters, page, total_count)
        
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "deleted_list", current_view)
        
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
    
    async def _show_search_results(self, client: Client, callback_query: CallbackQuery, query: str, page: int):
        """Show search results"""
        characters, total_count = await db.search_characters_paginated(query, page)
        
        if not characters:
            await callback_query.answer("No more results", show_alert=True)
            return
        
        total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
        
        message_text = helpers.format_character_list(
            characters, page, total_count, 
            f"Search Results for: '{query}'"
        )
        
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "search", query)
        
        buttons = []
        for char in characters[:3]:
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
        
        message_text = helpers.format_character_list(
            characters, page, total_count, 
            "Your Uploaded Characters"
        )
        
        keyboard = helpers.create_pagination_keyboard(page, total_pages, "myuploads", "")
        
        buttons = []
        for char in characters[:3]:
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
        for rarity_num, rarity_name in config.RARITY_MAP.items():
            count = rarity_stats.get(rarity_name, 0)
            percentage = (count / total_chars * 100) if total_chars > 0 else 0
            emoji = helpers.get_rarity_emoji(rarity_name)
            stats_text += f"{emoji} **{rarity_name.split(' ', 1)[-1]}:** {count} ({percentage:.1f}%)\n"
        
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
    
    # ==================== BOT LIFECYCLE ====================
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
