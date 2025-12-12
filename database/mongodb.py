# ==================== DATABASE/MONGODB.PY ====================
# database/mongodb.py - UPDATED
import logging
import asyncio
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config import config
from .models import Character, UserSession, MassUploadSession

logger = logging.getLogger(__name__)

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
            # Use sync MongoClient but run in thread pool
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
    
    async def bulk_insert_characters(self, characters: List[Character]) -> List[str]:
        """Bulk insert multiple characters (optimized for mass upload)"""
        try:
            character_dicts = [char.to_dict() for char in characters]
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.insert_many(character_dicts)
            )
            return [str(id) for id in result.inserted_ids]
        except PyMongoError as e:
            logger.error(f"Error bulk inserting characters: {e}")
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
        """Update character details - FIXED VERSION"""
        try:
            # Build update document properly
            update_doc = {
                "char_name": char_name,
                "anime_name": anime_name,
                "rarity": rarity
            }
            
            if subrarity:
                update_doc["subrarity"] = subrarity
            else:
                # Use $unset operator properly
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
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.update_one(
                    {"character_id": character_id},
                    {"$set": update_doc}
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
            return {"log_chat_1": None, "log_chat_2": None}
        except PyMongoError as e:
            logger.error(f"Error fetching log config: {e}")
            return {"log_chat_1": None, "log_chat_2": None}
    
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