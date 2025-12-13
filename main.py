# ==================== SIMPLE CHARACTER UPLOAD BOT ====================
import os
import logging
import asyncio
import aiohttp
import uuid
import json
import zipfile
import io
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
    
    # Bot owner IDs (for admin commands) - multiple owners
    OWNER_IDS = [1653814030, 7976292835, 8496760733, 7878477646]
    
    # Default log channel - @capture_database
    LOG_CHANNEL = "@capture_database"
    
    # Upload service configuration
    UPLOAD_TIMEOUT = 60
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max file size
    
    # Updated rarity mappings
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
        self.harem = None  # New collection for harem data
        self.user_backups = None  # New collection for user backup metadata
    
    async def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(config.MONGO_URI)
            self.db = self.client[config.DATABASE_NAME]
            self.characters = self.db.characters
            self.counters = self.db.counters
            self.sudo_users = self.db.sudo_users
            self.harem = self.db.harem  # Initialize harem collection
            self.user_backups = self.db.user_backups  # Initialize backup metadata
            
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
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.harem.create_index([("user_id", 1), ("character_id", 1)], unique=True)
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.user_backups.create_index([("user_id", 1), ("backup_id", 1)], unique=True)
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
    async def add_sudo_user(self, user_id: int, added_by: int) -> bool:
        """Add a sudo user"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.insert_one({
                    "user_id": user_id,
                    "added_by": added_by,
                    "added_at": datetime.utcnow()
                })
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
            if user_id in config.OWNER_IDS:
                return True
            sudo_user = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sudo_users.find_one({"user_id": user_id})
            )
            return sudo_user is not None
        except PyMongoError as e:
            logger.error(f"Error checking sudo user: {e}")
            return False
    
    async def get_sudo_users(self) -> List[Dict[str, Any]]:
        """Get all sudo user IDs with metadata"""
        try:
            sudo_users = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.sudo_users.find({}))
            )
            return sudo_users
        except PyMongoError as e:
            logger.error(f"Error fetching sudo users: {e}")
            return []
    
    # Backup operations
    async def create_backup_data(self) -> Dict[str, Any]:
        """Create backup of entire database"""
        try:
            backup_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "characters": [],
                "sudo_users": [],
                "harem_data": [],
                "metadata": {
                    "total_characters": 0,
                    "total_sudo_users": 0,
                    "total_harem_entries": 0
                }
            }
            
            # Get all characters
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({}))
            )
            # Convert ObjectId to string for JSON serialization
            for char in characters:
                char['_id'] = str(char['_id'])
                if 'timestamp' in char and isinstance(char['timestamp'], datetime):
                    char['timestamp'] = char['timestamp'].isoformat()
            
            backup_data["characters"] = characters
            backup_data["metadata"]["total_characters"] = len(characters)
            
            # Get all sudo users
            sudo_users = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.sudo_users.find({}))
            )
            for user in sudo_users:
                user['_id'] = str(user['_id'])
                if 'added_at' in user and isinstance(user['added_at'], datetime):
                    user['added_at'] = user['added_at'].isoformat()
            
            backup_data["sudo_users"] = sudo_users
            backup_data["metadata"]["total_sudo_users"] = len(sudo_users)
            
            # Get all harem data
            harem_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.harem.find({}))
            )
            for entry in harem_data:
                entry['_id'] = str(entry['_id'])
                if 'timestamp' in entry and isinstance(entry['timestamp'], datetime):
                    entry['timestamp'] = entry['timestamp'].isoformat()
            
            backup_data["harem_data"] = harem_data
            backup_data["metadata"]["total_harem_entries"] = len(harem_data)
            
            return backup_data
            
        except PyMongoError as e:
            logger.error(f"Error creating backup data: {e}")
            return None
    
    # Harem operations
    async def add_to_harem(self, user_id: int, character_id: int) -> bool:
        """Add character to user's harem"""
        try:
            # Check if character exists
            character = await self.get_character_by_id(character_id)
            if not character:
                return False
            
            # Check if already in harem
            existing = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.harem.find_one({
                    "user_id": user_id,
                    "character_id": character_id
                })
            )
            
            if existing:
                return True  # Already in harem
            
            # Add to harem
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.harem.insert_one({
                    "user_id": user_id,
                    "character_id": character_id,
                    "character_data": character,
                    "added_at": datetime.utcnow()
                })
            )
            
            return result.inserted_id is not None
            
        except PyMongoError as e:
            logger.error(f"Error adding to harem: {e}")
            return False
    
    async def get_user_harem(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user's harem data"""
        try:
            harem = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.harem.find({"user_id": user_id}))
            )
            return harem
        except PyMongoError as e:
            logger.error(f"Error getting user harem: {e}")
            return []
    
    async def remove_from_harem(self, user_id: int, character_id: int) -> bool:
        """Remove character from user's harem"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.harem.delete_one({
                    "user_id": user_id,
                    "character_id": character_id
                })
            )
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error removing from harem: {e}")
            return False
    
    async def clear_user_harem(self, user_id: int) -> bool:
        """Clear all harem entries for user"""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.harem.delete_many({"user_id": user_id})
            )
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Error clearing harem: {e}")
            return False
    
    async def backup_user_harem(self, user_id: int) -> Dict[str, Any]:
        """Create backup of user's harem"""
        try:
            harem_data = await self.get_user_harem(user_id)
            backup = {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "total_characters": len(harem_data),
                "harem_entries": []
            }
            
            for entry in harem_data:
                # Clean up the entry for JSON serialization
                clean_entry = {
                    "character_id": entry.get("character_id"),
                    "character_name": entry.get("character_data", {}).get("char_name", "Unknown"),
                    "anime": entry.get("character_data", {}).get("anime_name", "Unknown"),
                    "rarity": entry.get("character_data", {}).get("rarity", "Unknown"),
                    "added_at": entry.get("added_at", datetime.utcnow()).isoformat() if isinstance(entry.get("added_at"), datetime) else datetime.utcnow().isoformat()
                }
                backup["harem_entries"].append(clean_entry)
            
            return backup
            
        except Exception as e:
            logger.error(f"Error backing up user harem: {e}")
            return None
    
    async def restore_user_harem(self, user_id: int, harem_data: List[Dict[str, Any]]) -> tuple[bool, int, int]:
        """Restore user's harem from backup data"""
        try:
            # Clear existing harem
            cleared = await self.clear_user_harem(user_id)
            if not cleared:
                logger.warning(f"Could not clear existing harem for user {user_id}")
            
            added_count = 0
            failed_count = 0
            
            for entry in harem_data:
                character_id = entry.get("character_id")
                if character_id:
                    success = await self.add_to_harem(user_id, character_id)
                    if success:
                        added_count += 1
                    else:
                        failed_count += 1
            
            return True, added_count, failed_count
            
        except Exception as e:
            logger.error(f"Error restoring user harem: {e}")
            return False, 0, 0
    
    async def get_all_harem_users(self) -> List[int]:
        """Get all user IDs with harem data"""
        try:
            user_ids = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.harem.distinct("user_id"))
            )
            return user_ids
        except PyMongoError as e:
            logger.error(f"Error getting all harem users: {e}")
            return []
    
    # Get character by various fields
    async def get_characters_by_name(self, char_name: str) -> List[Dict[str, Any]]:
        """Get characters by name"""
        try:
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({"char_name": {"$regex": f"^{char_name}$", "$options": "i"}}))
            )
            return characters
        except PyMongoError as e:
            logger.error(f"Error getting characters by name: {e}")
            return []
    
    async def get_characters_by_anime(self, anime_name: str) -> List[Dict[str, Any]]:
        """Get characters by anime"""
        try:
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({"anime_name": {"$regex": f"^{anime_name}$", "$options": "i"}}))
            )
            return characters
        except PyMongoError as e:
            logger.error(f"Error getting characters by anime: {e}")
            return []
    
    async def get_characters_by_rarity(self, rarity: str) -> List[Dict[str, Any]]:
        """Get characters by rarity"""
        try:
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({"rarity": rarity}))
            )
            return characters
        except PyMongoError as e:
            logger.error(f"Error getting characters by rarity: {e}")
            return []
    
    async def get_deleted_characters(self) -> List[int]:
        """Get list of deleted character IDs (gaps in sequence)"""
        try:
            # Get all existing character IDs
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({}, {"character_id": 1}))
            )
            
            existing_ids = {char['character_id'] for char in characters}
            
            # Get max ID
            max_id = await self.get_next_character_id() - 1
            
            # Find gaps
            deleted_ids = []
            for i in range(1, max_id + 1):
                if i not in existing_ids:
                    deleted_ids.append(i)
            
            return deleted_ids
            
        except PyMongoError as e:
            logger.error(f"Error getting deleted characters: {e}")
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
    
    @staticmethod
    async def upload_json_to_catbox(data: Dict[str, Any], filename: str) -> Optional[str]:
        """Upload JSON data to Catbox"""
        try:
            # Create JSON string
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Create a temporary file
            temp_file = f"/tmp/{filename}"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            # Upload to Catbox
            url = await UploadService.upload_to_catbox(temp_file, filename)
            
            # Clean up
            try:
                os.remove(temp_file)
            except:
                pass
            
            return url
        except Exception as e:
            logger.error(f"Error uploading JSON to Catbox: {e}")
            return None

class BackupSystem:
    """Handles backup creation and restoration"""
    
    @staticmethod
    async def create_full_backup() -> tuple[Optional[bytes], Optional[str]]:
        """Create a zip backup of entire database"""
        try:
            # Get backup data
            backup_data = await db.create_backup_data()
            if not backup_data:
                return None, "Failed to create backup data"
            
            # Create zip in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add characters backup
                characters_json = json.dumps(backup_data["characters"], indent=2, ensure_ascii=False)
                zip_file.writestr("characters.json", characters_json)
                
                # Add sudo users backup
                sudo_json = json.dumps(backup_data["sudo_users"], indent=2, ensure_ascii=False)
                zip_file.writestr("sudo_users.json", sudo_json)
                
                # Add harem backup
                harem_json = json.dumps(backup_data["harem_data"], indent=2, ensure_ascii=False)
                zip_file.writestr("harem_data.json", harem_json)
                
                # Add metadata
                metadata = {
                    "backup_timestamp": backup_data["timestamp"],
                    "total_characters": backup_data["metadata"]["total_characters"],
                    "total_sudo_users": backup_data["metadata"]["total_sudo_users"],
                    "total_harem_entries": backup_data["metadata"]["total_harem_entries"],
                    "backup_version": "1.0"
                }
                metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
                zip_file.writestr("metadata.json", metadata_json)
            
            # Reset buffer position
            zip_buffer.seek(0)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"catcherbot_backup_{timestamp}.zip"
            
            return zip_buffer.getvalue(), filename
            
        except Exception as e:
            logger.error(f"Error creating backup zip: {e}")
            return None, str(e)
    
    @staticmethod
    async def create_all_harem_backup() -> tuple[Optional[bytes], Optional[str]]:
        """Create backup of all users' harem data in a zip"""
        try:
            # Get all users with harem data
            user_ids = await db.get_all_harem_users()
            
            if not user_ids:
                return None, "No harem data found"
            
            # Create zip in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                backup_count = 0
                
                for user_id in user_ids:
                    try:
                        # Create backup for each user
                        backup = await db.backup_user_harem(user_id)
                        if backup:
                            # Convert to JSON
                            json_str = json.dumps(backup, indent=2, ensure_ascii=False)
                            filename = f"harem_backup_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            zip_file.writestr(filename, json_str)
                            backup_count += 1
                    except Exception as e:
                        logger.error(f"Error backing up harem for user {user_id}: {e}")
                        continue
            
            if backup_count == 0:
                return None, "Failed to create any harem backups"
            
            # Reset buffer position
            zip_buffer.seek(0)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"all_harem_backups_{timestamp}.zip"
            
            return zip_buffer.getvalue(), filename
            
        except Exception as e:
            logger.error(f"Error creating all harem backup: {e}")
            return None, str(e)
    
    @staticmethod
    async def create_specific_harem_backup(user_id: int) -> tuple[Optional[bytes], Optional[str]]:
        """Create backup of specific user's harem"""
        try:
            backup = await db.backup_user_harem(user_id)
            if not backup:
                return None, "Failed to create harem backup"
            
            # Convert to JSON
            json_str = json.dumps(backup, indent=2, ensure_ascii=False)
            json_bytes = json_str.encode('utf-8')
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"harem_backup_{user_id}_{timestamp}.json"
            
            return json_bytes, filename
            
        except Exception as e:
            logger.error(f"Error creating specific harem backup: {e}")
            return None, str(e)
    
    @staticmethod
    async def parse_harem_backup_file(file_content: bytes) -> Optional[List[Dict[str, Any]]]:
        """Parse harem backup file"""
        try:
            # Try to parse as JSON
            json_str = file_content.decode('utf-8')
            data = json.loads(json_str)
            
            # Validate structure
            if not isinstance(data, dict):
                return None
            
            if "harem_entries" in data and isinstance(data["harem_entries"], list):
                return data["harem_entries"]
            elif isinstance(data, list):
                # Direct list of entries
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing harem backup: {e}")
            return None

class Helpers:
    """Utility functions for the bot"""
    
    def __init__(self):
        self.upload_service = UploadService()
        self.backup_system = BackupSystem()
    
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
        return user_id in config.OWNER_IDS
    
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
    
    @staticmethod
    def parse_reupload_arguments(text: str) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Parse reupload arguments (can be partial updates)"""
        try:
            parts = text.strip().split()
            if not parts:
                return None, None, None, None
            
            # Check if first part is a command keyword
            char_name = None
            anime_name = None
            rarity_input = None
            subrarity = None
            
            i = 0
            while i < len(parts):
                if parts[i] in ["name", "char", "character"]:
                    # Next part(s) is character name
                    if i + 1 < len(parts):
                        char_name = parts[i + 1]
                        i += 2
                    else:
                        return None, None, None, None
                
                elif parts[i] in ["anime", "series"]:
                    # Next part(s) is anime name
                    if i + 1 < len(parts):
                        anime_name = parts[i + 1]
                        i += 2
                    else:
                        return None, None, None, None
                
                elif parts[i] in ["rarity", "rank", "level"]:
                    # Next part(s) is rarity
                    if i + 1 < len(parts):
                        rarity_input = parts[i + 1]
                        if i + 2 < len(parts) and parts[i + 2] in config.LIMITED_SUBTYPES:
                            subrarity = parts[i + 2]
                            i += 3
                        else:
                            i += 2
                    else:
                        return None, None, None, None
                
                else:
                    # If no keyword, assume it's full format: name anime rarity
                    if len(parts) >= 3:
                        char_name = parts[0]
                        anime_name = parts[1]
                        rarity_input = parts[2]
                        if len(parts) > 3:
                            subrarity = parts[3]
                        break
                    else:
                        return None, None, None, None
            
            return char_name, anime_name, rarity_input, subrarity
            
        except Exception as e:
            logger.error(f"Error parsing reupload arguments: {e}")
            return None, None, None, None

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
                "2. 🟢 Uncommon\n"
                "3. 🔴 Rare\n"
                "4. 🟡 Legendary\n"
                "5. 🎐 Limited Edition (with subtypes)\n"
                "6. 💎 Premium\n"
                "7. 🥵 Exotic\n"
                "8. 🎬 Animated\n"
                "9. 🌩️ Thundra\n"
                "10. ☄️ Galvoria\n"
                "11. 🌈 Neon\n"
                "12. 🛡️ Supreme\n"
                "13. 🔮 Crystal\n"
                "14. 🎤 Celebrity\n\n"
                "**Limited Edition Subtypes:**\n"
                "valentine, christmas, halloween, summer, winter, basketball, police, newyear, easter, wedding, karate\n\n"
                "**All uploads are posted to:** @capture_database\n\n"
                "**🔧 Admin Commands (Owner/Sudo):**\n"
                "• `/add user_id` - Add sudo user (owner only)\n"
                "• `/remove user_id` - Remove sudo user (owner only)\n"
                "• `/sudos` - List all sudo users\n"
                "• `/backup` - Backup entire database (owner only)\n"
                "• `/backupharem [user_id]` - Backup all/specific user harem (owner only)\n\n"
                "**📝 Character Commands:**\n"
                "• `/edit ID new_name new_anime rarity` - Edit character\n"
                "• `/editmedia ID` - Edit character media (reply to media)\n"
                "• `/reupload ID [args]` - Reupload/update character (reply to media)\n"
                "• `/search query` - Search characters\n"
                "• `/info ID` - View character details\n"
                "• `/delete ID` - Delete character (owner only)\n\n"
                "**💾 Harem Commands:**\n"
                "• `/harembackup` - Backup your harem data\n"
                "• `/haremupload` - Restore harem data (reply to JSON file)\n"
                "• `/addharem ID` - Add character to your harem\n"
                "• `/myharem` - View your harem\n\n"
                "**📊 Utility Commands:**\n"
                "• `/stats` - View bot statistics\n"
                "• `/help` - Show this help message\n\n"
                "**Note:** Uploading a character does NOT automatically add it to your harem.\n"
                "You must use `/addharem ID` to add characters to your harem."
            )
            
            await message.reply_text(welcome_text)
        
        @self.client.on_message(filters.command("backup"))
        async def backup_command(client: Client, message: Message):
            """Handle /backup command - create database backup (owner only)"""
            user_id = message.from_user.id
            
            # Check if owner
            if not helpers.is_owner(user_id):
                await message.reply_text("❌ Only bot owners can create backups.")
                return
            
            status_msg = await message.reply_text("🔄 Creating database backup...")
            
            try:
                # Create backup
                backup_data, filename = await helpers.backup_system.create_full_backup()
                
                if not backup_data:
                    await status_msg.edit_text("❌ Failed to create backup. Please check logs.")
                    logger.error("Backup data creation failed")
                    return
                
                await status_msg.edit_text("✅ Backup created! Sending to your DM...")
                
                # Get file size
                file_size = len(backup_data)
                file_size_mb = file_size / (1024 * 1024)
                
                # Send backup to owner's DM
                try:
                    await client.send_document(
                        chat_id=user_id,
                        document=backup_data,
                        file_name=filename,
                        caption=f"📦 **Database Backup**\n\n"
                               f"🗓️ **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                               f"📊 **File Size:** {file_size_mb:.2f} MB\n"
                               f"👤 **Requested by:** {message.from_user.mention}\n\n"
                               f"**Instructions:**\n"
                               f"• Save this file securely\n"
                               f"• Contains all characters, sudo users, and harem data"
                    )
                    await status_msg.edit_text("✅ Backup sent to your DM!")
                    logger.info(f"Backup created and sent to owner {user_id} (Size: {file_size_mb:.2f} MB)")
                    
                except Exception as e:
                    logger.error(f"Failed to send backup to DM: {e}")
                    # Try sending in chat if DM fails
                    try:
                        await client.send_document(
                            chat_id=message.chat.id,
                            document=backup_data,
                            file_name=filename,
                            caption=f"📦 **Database Backup**\n\nSize: {file_size_mb:.2f} MB"
                        )
                        await status_msg.edit_text("✅ Backup created! (Sent in chat because DM failed)")
                    except Exception as e2:
                        logger.error(f"Failed to send backup in chat: {e2}")
                        await status_msg.edit_text("❌ Failed to send backup. File might be too large.")
                    
            except Exception as e:
                logger.error(f"Error in backup command: {e}")
                await status_msg.edit_text("❌ Error creating backup.")
        
        @self.client.on_message(filters.command("backupharem"))
        async def backup_harem_command(client: Client, message: Message):
            """Handle /backupharem command - backup all or specific user harem"""
            user_id = message.from_user.id
            
            # Check if owner
            if not helpers.is_owner(user_id):
                await message.reply_text("❌ Only bot owners can backup harem data.")
                return
            
            args = message.text.split()
            status_msg = await message.reply_text("🔄 Preparing harem backup...")
            
            try:
                # If no argument, backup all users
                if len(args) == 1:
                    backup_data, filename = await helpers.backup_system.create_all_harem_backup()
                    backup_type = "All Users"
                else:
                    # Try to parse user ID or username
                    target = args[1]
                    target_user_id = None
                    
                    # Check if it's a user ID (numeric)
                    if target.isdigit():
                        target_user_id = int(target)
                    else:
                        # Check if it's a username (with or without @)
                        if target.startswith('@'):
                            target = target[1:]
                        
                        try:
                            # Try to get user by username
                            user = await client.get_users(target)
                            target_user_id = user.id
                        except Exception as e:
                            await status_msg.edit_text(f"❌ Invalid user: {target}")
                            return
                    
                    if not target_user_id:
                        await status_msg.edit_text("❌ Could not find user.")
                        return
                    
                    # Check if user exists in harem
                    user_harem = await db.get_user_harem(target_user_id)
                    if not user_harem:
                        await status_msg.edit_text(f"❌ User {target_user_id} has no harem data.")
                        return
                    
                    backup_data, filename = await helpers.backup_system.create_specific_harem_backup(target_user_id)
                    backup_type = f"User {target_user_id}"
                
                if not backup_data:
                    await status_msg.edit_text("❌ Failed to create harem backup.")
                    return
                
                await status_msg.edit_text(f"✅ {backup_type} harem backup created! Sending to your DM...")
                
                # Get file size
                file_size = len(backup_data)
                file_size_mb = file_size / (1024 * 1024)
                
                # Send backup to owner's DM
                try:
                    await client.send_document(
                        chat_id=user_id,
                        document=backup_data,
                        file_name=filename,
                        caption=f"💾 **Harem Backup - {backup_type}**\n\n"
                               f"🗓️ **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                               f"📊 **File Size:** {file_size_mb:.2f} MB\n"
                               f"👤 **Requested by:** {message.from_user.mention}\n\n"
                               f"**Instructions:**\n"
                               f"• Save this file securely\n"
                               f"• Use `/haremupload` to restore data"
                    )
                    await status_msg.edit_text(f"✅ {backup_type} harem backup sent to your DM!")
                    logger.info(f"Harem backup created for {backup_type} by owner {user_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to send harem backup to DM: {e}")
                    # Try sending in chat
                    try:
                        await client.send_document(
                            chat_id=message.chat.id,
                            document=backup_data,
                            file_name=filename,
                            caption=f"💾 **Harem Backup - {backup_type}**\n\nSize: {file_size_mb:.2f} MB"
                        )
                        await status_msg.edit_text(f"✅ {backup_type} harem backup created! (Sent in chat)")
                    except Exception as e2:
                        logger.error(f"Failed to send harem backup in chat: {e2}")
                        await status_msg.edit_text("❌ Failed to send backup. File might be too large.")
                    
            except Exception as e:
                logger.error(f"Error in backupharem command: {e}")
                await status_msg.edit_text("❌ Error creating harem backup.")
        
        @self.client.on_message(filters.command("reupload"))
        async def reupload_command(client: Client, message: Message):
            """Handle /reupload command - update character with new media/details"""
            user_id = message.from_user.id
            
            # Check authorization
            if not await helpers.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to reupload characters.")
                return
            
            # Check if message is a reply to media
            if not message.reply_to_message or not (
                message.reply_to_message.photo or 
                message.reply_to_message.video or 
                message.reply_to_message.audio or 
                message.reply_to_message.document
            ):
                await message.reply_text(
                    "🔄 **Reupload Character**\n\n"
                    "**Usage:** Reply to a media file with:\n"
                    "`/reupload character_id` - Update media only\n"
                    "`/reupload character_id name \"New Name\"` - Update name only\n"
                    "`/reupload character_id anime \"New Anime\"` - Update anime only\n"
                    "`/reupload character_id rarity 5` - Update rarity only\n"
                    "`/reupload character_id \"New Name\" \"New Anime\" 5 valentine` - Update everything\n\n"
                    "**Examples:**\n"
                    "• `/reupload 123` (reply to media) - Update media\n"
                    "• `/reupload 123 name \"New Character Name\"` - Update name\n"
                    "• `/reupload 123 anime \"New Anime\" rarity 5` - Update anime and rarity\n"
                    "• `/reupload 123 \"Full Name\" \"Full Anime\" 5 valentine` (reply to media) - Full update"
                )
                return
            
            args = message.text.split()
            if len(args) < 2:
                await message.reply_text("❌ Usage: Reply to media with `/reupload character_id [args]`")
                return
            
            try:
                character_id = int(args[1])
                
                # Check if character exists
                character = await db.get_character_by_id(character_id)
                if not character:
                    await message.reply_text("❌ Character not found!")
                    return
                
                # Parse additional arguments if provided
                new_char_name = character['char_name']
                new_anime_name = character['anime_name']
                new_rarity = character['rarity']
                new_subrarity = character.get('subrarity')
                
                update_type = "media"  # Default is media update
                
                if len(args) > 2:
                    # Parse arguments
                    text_args = ' '.join(args[2:])
                    parsed_name, parsed_anime, parsed_rarity, parsed_subrarity = helpers.parse_reupload_arguments(text_args)
                    
                    if parsed_name:
                        new_char_name = parsed_name
                        update_type = "media and name"
                    
                    if parsed_anime:
                        new_anime_name = parsed_anime
                        update_type = "media and anime" if update_type == "media" else f"{update_type} and anime"
                    
                    if parsed_rarity:
                        rarity_name, subrarity = helpers.parse_rarity(parsed_rarity)
                        if rarity_name:
                            new_rarity = rarity_name
                            if subrarity:
                                new_subrarity = subrarity
                            update_type = "media and rarity" if update_type == "media" else f"{update_type} and rarity"
                        else:
                            await message.reply_text("❌ Invalid rarity.")
                            return
                
                # Start upload process
                status_msg = await message.reply_text("🔄 Starting reupload process...")
                
                async def update_status(text: str):
                    try:
                        await status_msg.edit_text(text)
                    except Exception as e:
                        logger.warning(f"Failed to update status: {e}")
                
                # Upload new media
                await update_status("📥 Uploading new media to Catbox...")
                
                media_url, media_type = await helpers.upload_media(
                    client, 
                    message.reply_to_message,
                    status_callback=update_status
                )
                
                if not media_url:
                    await update_status("❌ Failed to upload media. Please try again.")
                    return
                
                # Update character in database
                updated = False
                
                if len(args) > 2:
                    # Update character details
                    await update_status("🔄 Updating character details...")
                    updated = await db.update_character(
                        character_id=character_id,
                        char_name=new_char_name,
                        anime_name=new_anime_name,
                        rarity=new_rarity,
                        subrarity=new_subrarity
                    )
                    
                    if not updated:
                        await update_status("❌ Failed to update character details.")
                        return
                
                # Update character media
                await update_status("🔄 Updating character media...")
                media_updated = await db.update_character_media(character_id, media_url, media_type)
                
                if not media_updated:
                    await update_status("❌ Failed to update character media.")
                    return
                
                # Send to log channel
                username = message.from_user.username or message.from_user.first_name or "Unknown"
                updated_character = await db.get_character_by_id(character_id)
                
                if updated_character:
                    await helpers.send_to_log_channel(
                        client, updated_character, username, user_id
                    )
                
                # Success message
                success_text = (
                    f"✅ **Character #{character_id} Reuploaded Successfully!**\n\n"
                    f"👤 **Name:** {new_char_name}\n"
                    f"🎞️ **Anime:** {new_anime_name}\n"
                    f"🏅 **Rarity:** {new_rarity}\n"
                )
                
                if new_subrarity:
                    success_text += f"💠 **Sub-Rarity:** {new_subrarity}\n"
                
                success_text += (
                    f"\n📸 **Media:** Updated on Catbox\n"
                    f"📢 **Posted to:** @capture_database\n"
                    f"🆔 **Character ID:** `{character_id}`\n"
                    f"🔄 **Updated:** {update_type}\n\n"
                    f"**Character has been successfully updated!**"
                )
                
                await update_status(success_text)
                logger.info(f"Character {character_id} reuploaded by user {user_id}")
                
            except ValueError:
                await message.reply_text("❌ Invalid character ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in reupload command: {e}")
                await message.reply_text("❌ Error reuploading character.")
        
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
                    f"**Note:** This character was **NOT** automatically added to your harem.\n"
                    f"Use `/addharem {character_id}` to add it to your collection.\n\n"
                    f"**Use this ID to edit or delete the character.**"
                )
                
                await update_status(success_text)
                
            except Exception as e:
                logger.error(f"Error saving character: {e}")
                await update_status("❌ Error saving character to database. Please try again.")
        
        @self.client.on_message(filters.command("add"))
        async def add_sudo_command(client: Client, message: Message):
            """Handle /add command - add sudo user (owner only)"""
            user_id = message.from_user.id
            
            # Check if owner
            if not helpers.is_owner(user_id):
                await message.reply_text("❌ Only bot owners can add sudo users.")
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "👥 **Add Sudo User**\n\n"
                    "**Usage:** `/add user_id`\n\n"
                    "**Example:** `/add 1234567890`\n\n"
                    "**Note:** User ID must be a number."
                )
                return
            
            try:
                target_user_id = int(args[1])
                
                # Check if user is already sudo
                if await helpers.is_sudo_user(target_user_id):
                    await message.reply_text("❌ This user is already a sudo user.")
                    return
                
                # Check if user is an owner
                if target_user_id in config.OWNER_IDS:
                    await message.reply_text("❌ This user is already an owner.")
                    return
                
                # Add sudo user
                success = await db.add_sudo_user(target_user_id, user_id)
                
                if success:
                    try:
                        target_user = await client.get_users(target_user_id)
                        username = f"@{target_user.username}" if target_user.username else target_user.first_name
                    except:
                        username = f"User ({target_user_id})"
                    
                    await message.reply_text(
                        f"✅ **Sudo User Added Successfully!**\n\n"
                        f"👤 **User:** {username}\n"
                        f"🆔 **User ID:** `{target_user_id}`\n"
                        f"👑 **Added by:** {message.from_user.mention}\n\n"
                        f"**This user can now upload and edit characters.**"
                    )
                    logger.info(f"Sudo user {target_user_id} added by {user_id}")
                else:
                    await message.reply_text("❌ Failed to add sudo user.")
                    
            except ValueError:
                await message.reply_text("❌ Invalid user ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in add command: {e}")
                await message.reply_text("❌ Error adding sudo user.")
        
        @self.client.on_message(filters.command(["remove", "removesudo"]))
        async def remove_sudo_command(client: Client, message: Message):
            """Handle /remove command - remove sudo user (owner only)"""
            user_id = message.from_user.id
            
            # Check if owner
            if not helpers.is_owner(user_id):
                await message.reply_text("❌ Only bot owners can remove sudo users.")
                return
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "👥 **Remove Sudo User**\n\n"
                    "**Usage:** `/remove user_id`\n\n"
                    "**Example:** `/remove 1234567890`"
                )
                return
            
            try:
                target_user_id = int(args[1])
                
                # Check if user is an owner
                if target_user_id in config.OWNER_IDS:
                    await message.reply_text("❌ Cannot remove an owner.")
                    return
                
                # Check if user is sudo
                if not await helpers.is_sudo_user(target_user_id):
                    await message.reply_text("❌ This user is not a sudo user.")
                    return
                
                # Remove sudo user
                success = await db.remove_sudo_user(target_user_id)
                
                if success:
                    try:
                        target_user = await client.get_users(target_user_id)
                        username = f"@{target_user.username}" if target_user.username else target_user.first_name
                    except:
                        username = f"User ({target_user_id})"
                    
                    await message.reply_text(
                        f"✅ **Sudo User Removed Successfully!**\n\n"
                        f"👤 **User:** {username}\n"
                        f"🆔 **User ID:** `{target_user_id}`\n\n"
                        f"**This user can no longer upload or edit characters.**"
                    )
                    logger.info(f"Sudo user {target_user_id} removed by {user_id}")
                else:
                    await message.reply_text("❌ Failed to remove sudo user.")
                    
            except ValueError:
                await message.reply_text("❌ Invalid user ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in remove command: {e}")
                await message.reply_text("❌ Error removing sudo user.")
        
        @self.client.on_message(filters.command("sudos"))
        async def list_sudos_command(client: Client, message: Message):
            """Handle /sudos command - list all sudo users"""
            user_id = message.from_user.id
            
            # Check if owner or sudo
            if not helpers.is_owner(user_id) and not await helpers.is_sudo_user(user_id):
                await message.reply_text("❌ You are not authorized to view sudo users.")
                return
            
            try:
                sudo_users = await db.get_sudo_users()
                
                if not sudo_users:
                    await message.reply_text("📋 **Sudo Users List:**\n\nNo sudo users found (only owners).")
                    return
                
                # List owners
                owners_text = "👑 **Bot Owners:**\n"
                for owner_id in config.OWNER_IDS:
                    try:
                        owner = await client.get_users(owner_id)
                        owners_text += f"• {owner.mention} (`{owner_id}`)\n"
                    except:
                        owners_text += f"• User (`{owner_id}`)\n"
                
                # List sudo users
                sudo_text = "\n👥 **Sudo Users:**\n"
                for sudo in sudo_users:
                    sudo_id = sudo.get("user_id")
                    added_by = sudo.get("added_by", "Unknown")
                    added_at = sudo.get("added_at", datetime.utcnow())
                    
                    if isinstance(added_at, str):
                        try:
                            added_at = datetime.fromisoformat(added_at)
                        except:
                            added_at = datetime.utcnow()
                    
                    try:
                        sudo_user = await client.get_users(sudo_id)
                        sudo_name = f"@{sudo_user.username}" if sudo_user.username else sudo_user.first_name
                        sudo_text += f"• {sudo_name} (`{sudo_id}`)\n"
                    except:
                        sudo_text += f"• User (`{sudo_id}`)\n"
                    
                    # Try to get added by username
                    try:
                        adder = await client.get_users(added_by)
                        adder_name = f"@{adder.username}" if adder.username else adder.first_name
                        sudo_text += f"  └─ Added by: {adder_name} on {added_at.strftime('%Y-%m-%d')}\n"
                    except:
                        sudo_text += f"  └─ Added by: User (`{added_by}`) on {added_at.strftime('%Y-%m-%d')}\n"
                
                full_text = owners_text + sudo_text
                await message.reply_text(full_text)
                
            except Exception as e:
                logger.error(f"Error listing sudo users: {e}")
                await message.reply_text("❌ Error fetching sudo users list.")
        
        @self.client.on_message(filters.command("harembackup"))
        async def harem_backup_command(client: Client, message: Message):
            """Handle /harembackup command - backup user's harem"""
            user_id = message.from_user.id
            
            status_msg = await message.reply_text("🔄 Creating your harem backup...")
            
            try:
                # Create harem backup
                backup_data, filename = await helpers.backup_system.create_specific_harem_backup(user_id)
                
                if not backup_data:
                    await status_msg.edit_text("❌ Failed to create harem backup.")
                    return
                
                # Get harem stats
                harem = await db.get_user_harem(user_id)
                total_chars = len(harem)
                
                if total_chars == 0:
                    await status_msg.edit_text("❌ Your harem is empty!")
                    return
                
                # Count characters by rarity
                rarity_count = {}
                for entry in harem:
                    rarity = entry.get("character_data", {}).get("rarity", "Unknown")
                    rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
                
                rarity_stats = "\n".join([f"• {rarity}: {count}" for rarity, count in rarity_count.items()])
                
                # Get file size
                file_size = len(backup_data)
                file_size_kb = file_size / 1024
                
                # Send backup to user
                await client.send_document(
                    chat_id=user_id,
                    document=backup_data,
                    file_name=filename,
                    caption=f"💾 **Your Harem Backup**\n\n"
                           f"👤 **User:** {message.from_user.mention}\n"
                           f"📅 **Backup Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                           f"📊 **File Size:** {file_size_kb:.1f} KB\n"
                           f"👥 **Total Characters:** {total_chars}\n\n"
                           f"**Rarity Distribution:**\n{rarity_stats}\n\n"
                           f"**Instructions:**\n"
                           f"• Save this file to restore your harem later\n"
                           f"• Use `/haremupload` (reply to this file) to restore"
                )
                await status_msg.edit_text("✅ Your harem backup has been sent to your DM!")
                logger.info(f"Harem backup created for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error in harem backup: {e}")
                await status_msg.edit_text("❌ Error creating harem backup.")
        
        @self.client.on_message(filters.command("haremupload"))
        async def harem_upload_command(client: Client, message: Message):
            """Handle /haremupload command - restore harem from backup"""
            user_id = message.from_user.id
            
            # Check if message is a reply to a document
            if not message.reply_to_message or not message.reply_to_message.document:
                await message.reply_text(
                    "❌ **Please reply to a harem backup file with this command!**\n\n"
                    "**Usage:**\n"
                    "1. Create backup with `/harembackup`\n"
                    "2. Reply to the backup file with `/haremupload`\n\n"
                    "**Note:** This will replace your current harem!"
                )
                return
            
            status_msg = await message.reply_text("📥 Downloading backup file...")
            
            try:
                # Download the backup file
                file_path = await client.download_media(
                    message.reply_to_message.document.file_id,
                    file_name=f"harem_backup_{user_id}.json"
                )
                
                if not file_path:
                    await status_msg.edit_text("❌ Failed to download backup file.")
                    return
                
                await status_msg.edit_text("🔍 Parsing backup data...")
                
                # Read and parse the backup file
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read().encode('utf-8')
                
                # Parse backup data
                harem_data = await helpers.backup_system.parse_harem_backup_file(file_content)
                
                if not harem_data:
                    await status_msg.edit_text("❌ Invalid backup file format.")
                    # Clean up
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    return
                
                await status_msg.edit_text("🔄 Restoring your harem...")
                
                # Restore harem
                success, added_count, failed_count = await db.restore_user_harem(user_id, harem_data)
                
                # Clean up downloaded file
                try:
                    os.remove(file_path)
                except:
                    pass
                
                if success:
                    await status_msg.edit_text(
                        f"✅ **Harem Restored Successfully!**\n\n"
                        f"👤 **User:** {message.from_user.mention}\n"
                        f"✅ **Characters Added:** {added_count}\n"
                        f"❌ **Failed to Add:** {failed_count}\n"
                        f"📊 **Total in Harem:** {added_count}\n\n"
                        f"**Note:** Characters that no longer exist in the database were skipped."
                    )
                    logger.info(f"Harem restored for user {user_id}: {added_count} added, {failed_count} failed")
                else:
                    await status_msg.edit_text("❌ Failed to restore harem.")
                    
            except Exception as e:
                logger.error(f"Error in harem upload: {e}")
                await status_msg.edit_text("❌ Error restoring harem.")
        
        @self.client.on_message(filters.command("addharem"))
        async def add_harem_command(client: Client, message: Message):
            """Handle /addharem command - add character to user's harem"""
            user_id = message.from_user.id
            
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "💝 **Add to Harem**\n\n"
                    "**Usage:** `/addharem character_id`\n\n"
                    "**Example:** `/addharem 123`\n\n"
                    "**Note:** You can only add characters that exist in the database."
                )
                return
            
            try:
                character_id = int(args[1])
                
                # Check if character exists
                character = await db.get_character_by_id(character_id)
                if not character:
                    await message.reply_text("❌ Character not found!")
                    return
                
                # Add to harem
                success = await db.add_to_harem(user_id, character_id)
                
                if success:
                    await message.reply_text(
                        f"✅ **Character Added to Your Harem!**\n\n"
                        f"👤 **Name:** {character['char_name']}\n"
                        f"🎞️ **Anime:** {character['anime_name']}\n"
                        f"🏅 **Rarity:** {character['rarity']}\n"
                        f"🆔 **ID:** `{character_id}`\n\n"
                        f"**View your harem with** `/myharem`"
                    )
                else:
                    await message.reply_text("❌ Character is already in your harem!")
                    
            except ValueError:
                await message.reply_text("❌ Invalid character ID. Must be a number.")
            except Exception as e:
                logger.error(f"Error in addharem command: {e}")
                await message.reply_text("❌ Error adding character to harem.")
        
        @self.client.on_message(filters.command("myharem"))
        async def my_harem_command(client: Client, message: Message):
            """Handle /myharem command - view user's harem"""
            user_id = message.from_user.id
            
            try:
                harem = await db.get_user_harem(user_id)
                
                if not harem:
                    await message.reply_text(
                        "💔 **Your Harem is Empty!**\n\n"
                        "**To add characters to your harem:**\n"
                        "1. Find characters using `/search`\n"
                        "2. Add characters with `/addharem ID`\n"
                        "3. Restore from backup with `/haremupload`\n\n"
                        "**View character details with** `/info ID`"
                    )
                    return
                
                total_chars = len(harem)
                
                # Paginate results if too many
                page = 0
                args = message.text.split()
                if len(args) > 1:
                    try:
                        page = int(args[1]) - 1
                        if page < 0:
                            page = 0
                    except:
                        pass
                
                chars_per_page = 10
                total_pages = (total_chars + chars_per_page - 1) // chars_per_page
                if page >= total_pages:
                    page = total_pages - 1
                
                start_idx = page * chars_per_page
                end_idx = min(start_idx + chars_per_page, total_chars)
                
                # Create harem list
                harem_text = f"💝 **Your Harem** - Page {page + 1}/{total_pages}\n\n"
                harem_text += f"📊 **Total Characters:** {total_chars}\n\n"
                
                # Count by rarity
                rarity_count = {}
                for i in range(start_idx, end_idx):
                    entry = harem[i]
                    character = entry.get("character_data", {})
                    char_name = character.get("char_name", "Unknown")
                    anime = character.get("anime_name", "Unknown")
                    rarity = character.get("rarity", "Unknown")
                    char_id = entry.get("character_id", "?")
                    
                    harem_text += f"{i+1}. **{char_name}**\n"
                    harem_text += f"   ├─ 🎞️ {anime}\n"
                    harem_text += f"   ├─ 🏅 {rarity}\n"
                    harem_text += f"   └─ 🆔 `{char_id}`\n\n"
                    
                    # Count rarity
                    rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
                
                # Add rarity stats
                if rarity_count:
                    harem_text += "**📈 Rarity Distribution:**\n"
                    for rarity, count in sorted(rarity_count.items()):
                        percentage = (count / total_chars) * 100
                        harem_text += f"• {rarity}: {count} ({percentage:.1f}%)\n"
                
                # Add navigation buttons if multiple pages
                keyboard = None
                if total_pages > 1:
                    buttons = []
                    if page > 0:
                        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"harem_page_{page-1}_{user_id}"))
                    if page < total_pages - 1:
                        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"harem_page_{page+1}_{user_id}"))
                    
                    if buttons:
                        keyboard = InlineKeyboardMarkup([buttons])
                
                await message.reply_text(harem_text, reply_markup=keyboard)
                
            except Exception as e:
                logger.error(f"Error in myharem command: {e}")
                await message.reply_text("❌ Error fetching your harem.")
        
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
                
                # Check if in user's harem
                user_harem = await db.get_user_harem(message.from_user.id)
                in_harem = any(entry.get("character_id") == character_id for entry in user_harem)
                if in_harem:
                    char_info += "\n💝 **Status:** In your harem!"
                
                # Add edit buttons if user is sudo
                if await helpers.is_sudo_user(message.from_user.id):
                    buttons = []
                    buttons.append(InlineKeyboardButton("✏️ Edit Details", callback_data=f"edit_{character_id}"))
                    buttons.append(InlineKeyboardButton("🖼️ Edit Media", callback_data=f"editmedia_{character_id}"))
                    buttons.append(InlineKeyboardButton("🔄 Reupload", callback_data=f"reupload_{character_id}"))
                    
                    if not in_harem:
                        buttons.append(InlineKeyboardButton("💝 Add to Harem", callback_data=f"addharem_{character_id}"))
                    
                    keyboard = InlineKeyboardMarkup([buttons])
                else:
                    if not in_harem:
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("💝 Add to Harem", callback_data=f"addharem_{character_id}")]
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
                    f"**This will also remove it from all users' harems!**\n"
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
                user_harem = await db.get_user_harem(message.from_user.id)
                is_sudo = await helpers.is_sudo_user(message.from_user.id)
                is_owner_user = helpers.is_owner(message.from_user.id)
                
                # Get sudo users count
                sudo_users = await db.get_sudo_users()
                sudo_count = len(sudo_users)
                
                # Get deleted characters count
                deleted_ids = await db.get_deleted_characters()
                deleted_count = len(deleted_ids)
                
                stats_text = (
                    "📊 **Bot Statistics**\n\n"
                    f"• **Total Characters:** {total_chars}\n"
                    f"• **Deleted Characters:** {deleted_count}\n"
                    f"• **Sudo Users:** {sudo_count}\n"
                    f"• **Your Uploads:** {len(user_chars)}\n"
                    f"• **Your Harem Size:** {len(user_harem)}\n"
                    f"• **Your Status:** {'👑 Owner' if is_owner_user else ('✅ Sudo User' if is_sudo else '👤 Regular User')}\n"
                    f"• **Log Channel:** {config.LOG_CHANNEL}\n"
                    f"• **Max File Size:** {config.MAX_FILE_SIZE // (1024*1024)}MB\n\n"
                    "**Commands:**\n"
                    "• `/upload` - Upload character\n"
                    "• `/reupload` - Reupload/update character\n"
                    "• `/edit` - Edit character\n"
                    "• `/search` - Search characters\n"
                    "• `/info` - View character info\n"
                    "• `/addharem` - Add character to harem\n"
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
                "**🔄 REUPLOAD COMMAND:**\n"
                "Reply to media with `/reupload ID` to update media\n"
                "Add arguments to update details:\n"
                "• `/reupload ID name \"New Name\"`\n"
                "• `/reupload ID anime \"New Anime\" rarity 5`\n"
                "• `/reupload ID \"Full Name\" \"Full Anime\" 5 valentine`\n\n"
                "**🔄 EDIT COMMANDS:**\n"
                "• `/edit ID \"New Name\" \"New Anime\" Rarity [subrarity]`\n"
                "• `/editmedia ID` (reply to new media)\n\n"
                "**🔍 SEARCH COMMANDS:**\n"
                "• `/search query` - Search by name or anime\n"
                "• `/info ID` - View character details\n\n"
                "**💾 HAREM COMMANDS:**\n"
                "• `/harembackup` - Backup your harem data\n"
                "• `/haremupload` - Restore harem (reply to backup)\n"
                "• `/addharem ID` - Add character to harem\n"
                "• `/myharem` - View your harem\n\n"
                "**👑 ADMIN COMMANDS (Owner/Sudo):**\n"
                "• `/add user_id` - Add sudo user (owner only)\n"
                "• `/remove user_id` - Remove sudo user (owner only)\n"
                "• `/sudos` - List all sudo users\n"
                "• `/backup` - Backup database (owner only)\n"
                "• `/backupharem [user_id]` - Backup all/specific harem (owner only)\n"
                "• `/delete ID` - Delete character (owner only)\n\n"
                "**🎯 RARITIES (1-14):**\n"
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
                "**Important:** Uploading a character does **NOT** automatically add it to your harem.\n"
                "You must use `/addharem ID` to add characters to your collection.\n\n"
                "**All uploads are automatically posted to:** @capture_database"
            )
            
            await message.reply_text(help_text)
        
        # Callback query handler for inline buttons
        @self.client.on_callback_query()
        async def handle_callbacks(client: Client, callback_query):
            data = callback_query.data
            user_id = callback_query.from_user.id
            
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
                
                elif data.startswith("reupload_"):
                    character_id = int(data.split("_")[1])
                    await callback_query.message.edit_text(
                        f"🔄 **Reupload Character #{character_id}**\n\n"
                        "Please reply to a media file with:\n"
                        f"`/reupload {character_id}`\n\n"
                        "**Optional arguments:**\n"
                        f"• `/reupload {character_id} name \"New Name\"`\n"
                        f"• `/reupload {character_id} anime \"New Anime\"`\n"
                        f"• `/reupload {character_id} rarity 5`\n"
                        f"• `/reupload {character_id} \"Full Name\" \"Full Anime\" 5 valentine`"
                    )
                    await callback_query.answer()
                
                elif data.startswith("addharem_"):
                    character_id = int(data.split("_")[1])
                    
                    # Add to harem
                    success = await db.add_to_harem(user_id, character_id)
                    
                    if success:
                        await callback_query.answer("✅ Added to your harem!", show_alert=True)
                        
                        # Update message to show it's in harem
                        try:
                            message_text = callback_query.message.caption or callback_query.message.text
                            if "💝 **Status:** In your harem!" not in message_text:
                                new_text = message_text + "\n💝 **Status:** In your harem!"
                                
                                # Remove the add button
                                keyboard = callback_query.message.reply_markup
                                if keyboard:
                                    new_keyboard = InlineKeyboardMarkup([])
                                    for row in keyboard.inline_keyboard:
                                        new_row = []
                                        for button in row:
                                            if button.callback_data != data:
                                                new_row.append(button)
                                        if new_row:
                                            new_keyboard.inline_keyboard.append(new_row)
                                    
                                    await callback_query.message.edit_caption(
                                        caption=new_text,
                                        reply_markup=new_keyboard if new_keyboard.inline_keyboard else None
                                    )
                        except Exception as e:
                            logger.warning(f"Error updating message: {e}")
                    else:
                        await callback_query.answer("❌ Already in your harem!", show_alert=True)
                
                elif data.startswith("harem_page_"):
                    # Handle harem pagination
                    parts = data.split("_")
                    page = int(parts[2])
                    target_user_id = int(parts[3])
                    
                    # Only allow user to navigate their own harem
                    if user_id != target_user_id:
                        await callback_query.answer("❌ You can only view your own harem!", show_alert=True)
                        return
                    
                    # Fetch harem for the requested page
                    harem = await db.get_user_harem(user_id)
                    total_chars = len(harem)
                    chars_per_page = 10
                    total_pages = (total_chars + chars_per_page - 1) // chars_per_page
                    
                    if page >= total_pages:
                        page = total_pages - 1
                    if page < 0:
                        page = 0
                    
                    start_idx = page * chars_per_page
                    end_idx = min(start_idx + chars_per_page, total_chars)
                    
                    # Create harem list for this page
                    harem_text = f"💝 **Your Harem** - Page {page + 1}/{total_pages}\n\n"
                    harem_text += f"📊 **Total Characters:** {total_chars}\n\n"
                    
                    rarity_count = {}
                    for i in range(start_idx, end_idx):
                        entry = harem[i]
                        character = entry.get("character_data", {})
                        char_name = character.get("char_name", "Unknown")
                        anime = character.get("anime_name", "Unknown")
                        rarity = character.get("rarity", "Unknown")
                        char_id = entry.get("character_id", "?")
                        
                        harem_text += f"{i+1}. **{char_name}**\n"
                        harem_text += f"   ├─ 🎞️ {anime}\n"
                        harem_text += f"   ├─ 🏅 {rarity}\n"
                        harem_text += f"   └─ 🆔 `{char_id}`\n\n"
                        
                        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
                    
                    # Add rarity stats
                    if rarity_count:
                        harem_text += "**📈 Rarity Distribution:**\n"
                        for rarity, count in sorted(rarity_count.items()):
                            percentage = (count / total_chars) * 100
                            harem_text += f"• {rarity}: {count} ({percentage:.1f}%)\n"
                    
                    # Update navigation buttons
                    buttons = []
                    if page > 0:
                        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"harem_page_{page-1}_{user_id}"))
                    if page < total_pages - 1:
                        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"harem_page_{page+1}_{user_id}"))
                    
                    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None
                    
                    await callback_query.message.edit_text(harem_text, reply_markup=keyboard)
                    await callback_query.answer()
                
                elif data.startswith("confirm_delete_"):
                    character_id = int(data.split("_")[2])
                    
                    # Only owner can delete
                    if not helpers.is_owner(user_id):
                        await callback_query.answer("❌ Only owners can delete characters!", show_alert=True)
                        return
                    
                    deleted = await db.delete_character(character_id)
                    if deleted:
                        await callback_query.message.edit_text(f"✅ Character `{character_id}` deleted successfully!")
                        logger.info(f"Character {character_id} deleted by user {user_id}")
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
            logger.info(f"Owner IDs: {config.OWNER_IDS}")
            
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
