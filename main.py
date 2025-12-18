#!/usr/bin/env python3
"""
COMPLETE TELEGRAM UPLOAD BOT WITH ALL FEATURES
Features: Rarity system, recycle bin, sudo permissions, database reset warnings, etc.
"""

import os
import logging
import asyncio
import json
import hashlib
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from io import BytesIO
from functools import wraps
import aiohttp

from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from bson import ObjectId
from bson.errors import InvalidId
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    User,
    Chat,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackContext
)
from telegram.error import BadRequest, NetworkError, RetryAfter

# ==================== LOAD ENVIRONMENT ====================
load_dotenv()

# ==================== CONFIGURATION ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "upload_bot")
    OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
    LOG_CHANNEL = os.getenv("LOG_CHANNEL", "")
    UPLOAD_TIMEOUT = int(os.getenv("UPLOAD_TIMEOUT", 60))
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB
    
    # Rarity system (1-14) for categorization
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
        'upload': 'Upload files',
        'delete': 'Delete files',
        'edit': 'Edit files',
        'restore': 'Restore deleted files',
        'fill': 'Fill deleted slots',
        'view_deleted': 'View recycle bin',
        'add_sudo': 'Add sudo users',
        'remove_sudo': 'Remove sudo users',
        'reset_db': 'Reset database'
    }

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== DATA MODELS ====================
class FileMetadata:
    """Data model for file documents"""
    
    def __init__(
        self,
        file_name: str,
        description: str,
        rarity: str,
        file_id: int,
        telegram_file_id: str = None,
        file_type: str = None,
        file_size: int = 0,
        added_by: int = None,
        timestamp: Optional[datetime] = None,
        deleted_at: Optional[datetime] = None,
        deleted_by: Optional[int] = None,
        deleted_reason: Optional[str] = None,
        tags: List[str] = None,
        privacy: str = "public",
        views: int = 0,
        downloads: int = 0,
        favorites: int = 0
    ):
        self.file_name = file_name
        self.description = description
        self.rarity = rarity
        self.file_id = file_id
        self.telegram_file_id = telegram_file_id
        self.file_type = file_type
        self.file_size = file_size
        self.added_by = added_by
        self.timestamp = timestamp or datetime.utcnow()
        self.deleted_at = deleted_at
        self.deleted_by = deleted_by
        self.deleted_reason = deleted_reason
        self.tags = tags or []
        self.privacy = privacy
        self.views = views
        self.downloads = downloads
        self.favorites = favorites
    
    def to_dict(self) -> Dict:
        """Convert file object to dictionary for MongoDB"""
        data = {
            "file_name": self.file_name,
            "description": self.description,
            "rarity": self.rarity,
            "file_id": self.file_id,
            "telegram_file_id": self.telegram_file_id,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "added_by": self.added_by,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "privacy": self.privacy,
            "views": self.views,
            "downloads": self.downloads,
            "favorites": self.favorites
        }
        
        if self.deleted_at:
            data["deleted_at"] = self.deleted_at
        if self.deleted_by:
            data["deleted_by"] = self.deleted_by
        if self.deleted_reason:
            data["deleted_reason"] = self.deleted_reason
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FileMetadata':
        """Create FileMetadata object from dictionary"""
        return cls(
            file_name=data.get("file_name"),
            description=data.get("description"),
            rarity=data.get("rarity"),
            file_id=data.get("file_id"),
            telegram_file_id=data.get("telegram_file_id"),
            file_type=data.get("file_type"),
            file_size=data.get("file_size", 0),
            added_by=data.get("added_by"),
            timestamp=data.get("timestamp"),
            deleted_at=data.get("deleted_at"),
            deleted_by=data.get("deleted_by"),
            deleted_reason=data.get("deleted_reason"),
            tags=data.get("tags", []),
            privacy=data.get("privacy", "public"),
            views=data.get("views", 0),
            downloads=data.get("downloads", 0),
            favorites=data.get("favorites", 0)
        )

# ==================== DATABASE CLASS ====================
class MongoDB:
    """MongoDB database operations handler"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.files = None
        self.deleted_files = None
        self.counters = None
        self.sudo_users = None
        self.db_warnings = None
        self.users = None
        self.analytics = None
    
    def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.client.server_info()
            
            self.db = self.client[Config.DATABASE_NAME]
            self.files = self.db.files
            self.deleted_files = self.db.deleted_files
            self.counters = self.db.counters
            self.sudo_users = self.db.sudo_users
            self.db_warnings = self.db.db_warnings
            self.users = self.db.users
            self.analytics = self.db.analytics
            
            # Create indexes
            self._create_indexes()
            
            # Initialize counter
            self._initialize_counter()
            
            # Initialize warnings
            self._initialize_warnings()
            
            logger.info("✅ Connected to MongoDB successfully")
            
        except ConnectionFailure as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Create all necessary indexes"""
        # Files collection indexes
        self.files.create_index([("telegram_file_id", 1)], unique=True, sparse=True)
        self.files.create_index([("added_by", 1)])
        self.files.create_index([("file_id", 1)], unique=True)
        self.files.create_index([("rarity", 1)])
        self.files.create_index([("timestamp", DESCENDING)])
        self.files.create_index([("tags", 1)])
        self.files.create_index([("privacy", 1)])
        
        # Deleted files indexes
        self.deleted_files.create_index([("file_id", 1)])
        self.deleted_files.create_index([("deleted_at", DESCENDING)])
        self.deleted_files.create_index([("deleted_by", 1)])
        
        # Users indexes
        self.users.create_index([("user_id", 1)], unique=True)
        self.sudo_users.create_index([("user_id", 1)], unique=True)
        
        logger.info("✅ Database indexes created")
    
    def _initialize_counter(self):
        """Initialize counter if not exists"""
        if not self.counters.find_one({"_id": "file_id"}):
            self.counters.insert_one({"_id": "file_id", "seq": 0})
    
    def _initialize_warnings(self):
        """Initialize reset warnings collection"""
        if not self.db_warnings.find_one({"_id": "reset_warnings"}):
            self.db_warnings.insert_one({
                "_id": "reset_warnings",
                "warnings": {},
                "last_warning": None
            })
    
    # ==================== ID MANAGEMENT ====================
    def get_next_file_id(self) -> int:
        """Get next sequential file ID"""
        result = self.counters.find_one_and_update(
            {"_id": "file_id"},
            {"$inc": {"seq": 1}},
            return_document=True
        )
        return result["seq"]
    
    # ==================== FILE OPERATIONS ====================
    def insert_file(self, file_data: FileMetadata) -> str:
        """Insert a new file into database"""
        result = self.files.insert_one(file_data.to_dict())
        return str(result.inserted_id)
    
    def get_file_count(self) -> int:
        """Get total number of active files"""
        return self.files.count_documents({})
    
    def get_file_by_id(self, file_id: int) -> Optional[Dict]:
        """Get active file by file ID"""
        return self.files.find_one({"file_id": file_id})
    
    def update_file(
        self, 
        file_id: int, 
        file_name: str, 
        description: str, 
        rarity: str,
        tags: List[str] = None
    ) -> bool:
        """Update file details"""
        update_data = {
            "file_name": file_name,
            "description": description,
            "rarity": rarity
        }
        if tags is not None:
            update_data["tags"] = tags
            
        result = self.files.update_one(
            {"file_id": file_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    def update_file_metadata(self, file_id: int, metadata: Dict) -> bool:
        """Update file metadata"""
        result = self.files.update_one(
            {"file_id": file_id},
            {"$set": metadata}
        )
        return result.modified_count > 0
    
    def increment_views(self, file_id: int) -> bool:
        """Increment file views"""
        result = self.files.update_one(
            {"file_id": file_id},
            {"$inc": {"views": 1}}
        )
        return result.modified_count > 0
    
    def increment_downloads(self, file_id: int) -> bool:
        """Increment file downloads"""
        result = self.files.update_one(
            {"file_id": file_id},
            {"$inc": {"downloads": 1}}
        )
        return result.modified_count > 0
    
    def increment_favorites(self, file_id: int) -> bool:
        """Increment file favorites"""
        result = self.files.update_one(
            {"file_id": file_id},
            {"$inc": {"favorites": 1}}
        )
        return result.modified_count > 0
    
    # ==================== RECYCLE BIN OPERATIONS ====================
    def soft_delete_file(self, file_id: int, deleted_by: int, reason: str = None) -> bool:
        """Move file to recycle bin (soft delete)"""
        # Get file from active collection
        file_data = self.files.find_one({"file_id": file_id})
        
        if not file_data:
            return False
        
        # Add deletion metadata
        file_data["deleted_at"] = datetime.utcnow()
        file_data["deleted_by"] = deleted_by
        if reason:
            file_data["deleted_reason"] = reason
        
        # Insert into deleted collection
        self.deleted_files.insert_one(file_data)
        
        # Remove from active collection
        result = self.files.delete_one({"file_id": file_id})
        
        return result.deleted_count > 0
    
    def restore_file(self, file_id: int) -> bool:
        """Restore file from recycle bin"""
        # Get file from deleted collection
        file_data = self.deleted_files.find_one({"file_id": file_id})
        
        if not file_data:
            return False
        
        # Remove deletion metadata
        file_data.pop("deleted_at", None)
        file_data.pop("deleted_by", None)
        file_data.pop("deleted_reason", None)
        
        # Insert back into active collection
        self.files.insert_one(file_data)
        
        # Remove from deleted collection
        result = self.deleted_files.delete_one({"file_id": file_id})
        
        return result.deleted_count > 0
    
    def permanent_delete_file(self, file_id: int) -> bool:
        """Permanently delete file from recycle bin"""
        result = self.deleted_files.delete_one({"file_id": file_id})
        return result.deleted_count > 0
    
    def fill_deleted_file(self, file_id: int, file_data: FileMetadata) -> bool:
        """Replace a deleted file with new file data"""
        # Check if file exists in deleted collection
        deleted_file = self.deleted_files.find_one({"file_id": file_id})
        
        if not deleted_file:
            return False
        
        # Remove from deleted collection
        self.deleted_files.delete_one({"file_id": file_id})
        
        # Insert new file with the same ID
        file_dict = file_data.to_dict()
        file_dict["file_id"] = file_id
        
        self.files.insert_one(file_dict)
        
        return True
    
    def get_deleted_file_by_id(self, file_id: int) -> Optional[Dict]:
        """Get deleted file by file ID"""
        return self.deleted_files.find_one({"file_id": file_id})
    
    def get_deleted_files_count(self) -> int:
        """Get total number of deleted files"""
        return self.deleted_files.count_documents({})
    
    def get_oldest_deleted_file(self) -> Optional[Dict]:
        """Get the oldest deleted file (first to be deleted)"""
        return self.deleted_files.find_one({}, sort=[("deleted_at", ASCENDING)])
    
    def cleanup_old_deleted(self) -> int:
        """Clean up old deleted files (older than RECYCLE_BIN_MAX_DAYS)"""
        cutoff_date = datetime.utcnow() - timedelta(days=Config.RECYCLE_BIN_MAX_DAYS)
        result = self.deleted_files.delete_many({"deleted_at": {"$lt": cutoff_date}})
        return result.deleted_count
    
    # ==================== SEARCH AND LIST OPERATIONS ====================
    def search_files(self, query: str, limit: int = 20) -> List[Dict]:
        """Search active files by name or description"""
        search_filter = {
            "$or": [
                {"file_name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"tags": {"$in": [query]}}
            ]
        }
        
        return list(self.files.find(search_filter).limit(limit))
    
    def search_deleted_files(self, query: str, page: int = 0) -> Tuple[List[Dict], int]:
        """Search deleted files with pagination"""
        skip = page * Config.ITEMS_PER_PAGE
        
        search_filter = {
            "$or": [
                {"file_name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"tags": {"$in": [query]}}
            ]
        }
        
        files = list(self.deleted_files.find(search_filter)
                     .sort("deleted_at", DESCENDING)
                     .skip(skip)
                     .limit(Config.ITEMS_PER_PAGE))
        
        total_count = self.deleted_files.count_documents(search_filter)
        
        return files, total_count
    
    def get_files_by_rarity(self, rarity_name: str, page: int = 0) -> Tuple[List[Dict], int]:
        """Get active files by rarity with pagination"""
        skip = page * Config.ITEMS_PER_PAGE
        
        files = list(self.files.find({"rarity": rarity_name})
                     .skip(skip)
                     .limit(Config.ITEMS_PER_PAGE))
        
        total_count = self.files.count_documents({"rarity": rarity_name})
        
        return files, total_count
    
    def get_all_files_paginated(self, page: int = 0) -> Tuple[List[Dict], int]:
        """Get all active files with pagination"""
        skip = page * Config.ITEMS_PER_PAGE
        
        files = list(self.files.find({})
                     .sort("file_id", ASCENDING)
                     .skip(skip)
                     .limit(Config.ITEMS_PER_PAGE))
        
        total_count = self.get_file_count()
        
        return files, total_count
    
    def get_deleted_files(self, page: int = 0) -> Tuple[List[Dict], int]:
        """Get deleted files with pagination"""
        skip = page * Config.ITEMS_PER_PAGE
        
        files = list(self.deleted_files.find({})
                     .sort("deleted_at", DESCENDING)
                     .skip(skip)
                     .limit(Config.ITEMS_PER_PAGE))
        
        total_count = self.get_deleted_files_count()
        
        return files, total_count
    
    def get_user_files_paginated(self, user_id: int, page: int = 0) -> Tuple[List[Dict], int]:
        """Get all active files uploaded by a user with pagination"""
        skip = page * Config.ITEMS_PER_PAGE
        
        files = list(self.files.find({"added_by": user_id})
                     .sort("timestamp", DESCENDING)
                     .skip(skip)
                     .limit(Config.ITEMS_PER_PAGE))
        
        total_count = self.files.count_documents({"added_by": user_id})
        
        return files, total_count
    
    def get_user_deleted_files(self, user_id: int, page: int = 0) -> Tuple[List[Dict], int]:
        """Get deleted files uploaded by a user with pagination"""
        skip = page * Config.ITEMS_PER_PAGE
        
        files = list(self.deleted_files.find({"added_by": user_id})
                     .sort("deleted_at", DESCENDING)
                     .skip(skip)
                     .limit(Config.ITEMS_PER_PAGE))
        
        total_count = self.deleted_files.count_documents({"added_by": user_id})
        
        return files, total_count
    
    def search_files_paginated(self, query: str, page: int = 0) -> Tuple[List[Dict], int]:
        """Search active files with pagination"""
        skip = page * Config.ITEMS_PER_PAGE
        
        search_filter = {
            "$or": [
                {"file_name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"tags": {"$in": [query]}}
            ]
        }
        
        files = list(self.files.find(search_filter)
                     .skip(skip)
                     .limit(Config.ITEMS_PER_PAGE))
        
        total_count = self.files.count_documents(search_filter)
        
        return files, total_count
    
    # ==================== STATISTICS ====================
    def get_rarity_stats(self) -> Dict[str, int]:
        """Get count of active files per rarity"""
        pipeline = [
            {"$group": {
                "_id": "$rarity",
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        results = list(self.files.aggregate(pipeline))
        
        stats = {}
        for result in results:
            stats[result["_id"]] = result["count"]
        
        return stats
    
    def get_top_uploaders(self, limit: int = 10) -> List[Dict]:
        """Get top uploaders by file count"""
        pipeline = [
            {"$group": {
                "_id": "$added_by",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": DESCENDING}},
            {"$limit": limit}
        ]
        
        return list(self.files.aggregate(pipeline))
    
    # ==================== DATABASE RESET FUNCTIONS ====================
    def add_reset_warning(self, user_id: int) -> Tuple[int, datetime]:
        """Add a reset warning for a user"""
        result = self.db_warnings.find_one_and_update(
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
        
        warnings = result.get("warnings", {})
        user_warnings = warnings.get(str(user_id), {})
        warning_count = user_warnings.get("count", 1)
        
        return warning_count, datetime.utcnow()
    
    def get_reset_warnings(self, user_id: int) -> Tuple[int, Optional[datetime]]:
        """Get reset warnings for a user"""
        result = self.db_warnings.find_one({"_id": "reset_warnings"})
        
        if result and "warnings" in result:
            warnings = result["warnings"]
            user_warnings = warnings.get(str(user_id), {})
            warning_count = user_warnings.get("count", 0)
            last_warning = user_warnings.get("last_warning")
            if last_warning and isinstance(last_warning, str):
                last_warning = datetime.fromisoformat(last_warning.replace('Z', '+00:00'))
            return warning_count, last_warning
        
        return 0, None
    
    def clear_reset_warnings(self, user_id: int) -> bool:
        """Clear reset warnings for a user"""
        result = self.db_warnings.update_one(
            {"_id": "reset_warnings"},
            {"$unset": {f"warnings.{user_id}": ""}}
        )
        return result.modified_count > 0
    
    def reset_database(self) -> bool:
        """Reset the entire database (clear all collections)"""
        try:
            # Drop all collections
            self.files.drop()
            self.deleted_files.drop()
            
            # Reset counter
            self.counters.delete_one({"_id": "file_id"})
            
            # Reinitialize counter
            self.counters.insert_one({"_id": "file_id", "seq": 0})
            
            # Clear all warnings
            self.db_warnings.delete_one({"_id": "reset_warnings"})
            
            # Reinitialize warnings
            self.db_warnings.insert_one({
                "_id": "reset_warnings",
                "warnings": {},
                "last_warning": None
            })
            
            logger.info("Database reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return False
    
    # ==================== SUDO USER OPERATIONS ====================
    def add_sudo_user(self, user_id: int, permissions: List[str]) -> bool:
        """Add a sudo user with specific permissions"""
        sudo_doc = {
            "user_id": user_id,
            "permissions": permissions,
            "added_at": datetime.utcnow(),
            "added_by": Config.OWNER_ID
        }
        
        result = self.sudo_users.update_one(
            {"user_id": user_id},
            {"$set": sudo_doc},
            upsert=True
        )
        return True
    
    def remove_sudo_user(self, user_id: int) -> bool:
        """Remove a sudo user"""
        result = self.sudo_users.delete_one({"user_id": user_id})
        return result.deleted_count > 0
    
    def get_sudo_user(self, user_id: int) -> Optional[Dict]:
        """Get sudo user details"""
        return self.sudo_users.find_one({"user_id": user_id})
    
    def get_all_sudo_users(self) -> List[Dict]:
        """Get all sudo users"""
        return list(self.sudo_users.find({}))
    
    def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has specific permission"""
        if user_id == Config.OWNER_ID:
            return True
        
        sudo_user = self.sudo_users.find_one({"user_id": user_id})
        
        if not sudo_user:
            return False
        
        permissions = sudo_user.get("permissions", [])
        return permission in permissions
    
    def update_sudo_permissions(self, user_id: int, permissions: List[str]) -> bool:
        """Update sudo user permissions"""
        result = self.sudo_users.update_one(
            {"user_id": user_id},
            {"$set": {"permissions": permissions}}
        )
        return result.modified_count > 0
    
    # ==================== USER MANAGEMENT ====================
    def ensure_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """Ensure user exists in database"""
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "join_date": datetime.utcnow(),
            "last_seen": datetime.utcnow(),
            "uploads_count": 0,
            "total_downloads": 0,
            "total_views": 0
        }
        
        self.users.update_one(
            {"user_id": user_id},
            {"$setOnInsert": user_data, "$set": {"last_seen": datetime.utcnow()}},
            upsert=True
        )
        
        return user_data
    
    def increment_user_uploads(self, user_id: int) -> bool:
        """Increment user's upload count"""
        result = self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"uploads_count": 1}}
        )
        return result.modified_count > 0
    
    def increment_user_downloads(self, user_id: int) -> bool:
        """Increment user's download count"""
        result = self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"total_downloads": 1}}
        )
        return result.modified_count > 0

# Initialize database
db = MongoDB()
db.connect()

# ==================== HELPER CLASSES ====================
class UploadService:
    """Handles media uploads"""
    
    @staticmethod
    async def upload_to_catbox(file_bytes: bytes, filename: str) -> Optional[str]:
        """Upload file to Catbox.moe"""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                form_data = aiohttp.FormData()
                form_data.add_field('reqtype', 'fileupload')
                form_data.add_field('fileToUpload', file_bytes, filename=filename)
                
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
    def format_size(size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.2f} {units[i]}"
    
    @staticmethod
    def format_file_info(file_data: Dict) -> str:
        """Format file data for display"""
        info = f"📁 **Name:** {file_data.get('file_name', 'N/A')}\n"
        info += f"📝 **Description:** {file_data.get('description', 'N/A')}\n"
        info += f"🏷️ **Rarity:** {file_data.get('rarity', 'N/A')}\n"
        info += f"🆔 **ID:** `{file_data.get('file_id', 'N/A')}`\n"
        info += f"📏 **Size:** {Helpers.format_size(file_data.get('file_size', 0))}\n"
        
        if file_data.get('timestamp'):
            timestamp = file_data['timestamp']
            if isinstance(timestamp, datetime):
                info += f"📅 **Added:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if file_data.get('added_by'):
            info += f"👤 **Uploaded by:** {file_data['added_by']}\n"
        
        if file_data.get('tags'):
            info += f"🏷️ **Tags:** {', '.join(file_data['tags'])}\n"
        
        if file_data.get('views') is not None:
            info += f"👁️ **Views:** {file_data['views']}\n"
        
        if file_data.get('downloads') is not None:
            info += f"📥 **Downloads:** {file_data['downloads']}\n"
        
        return info
    
    @staticmethod
    def format_deleted_file_info(file_data: Dict) -> str:
        """Format deleted file data for display"""
        info = f"🗑️ **Deleted File**\n\n"
        info += f"📁 **Name:** {file_data.get('file_name', 'N/A')}\n"
        info += f"📝 **Description:** {file_data.get('description', 'N/A')}\n"
        info += f"🏷️ **Rarity:** {file_data.get('rarity', 'N/A')}\n"
        info += f"🆔 **ID:** `{file_data.get('file_id', 'N/A')}`\n"
        
        if file_data.get('timestamp'):
            timestamp = file_data['timestamp']
            if isinstance(timestamp, datetime):
                info += f"📅 **Originally Added:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if file_data.get('deleted_at'):
            deleted_at = file_data['deleted_at']
            if isinstance(deleted_at, datetime):
                info += f"🗑️ **Deleted On:** {deleted_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                days_ago = (datetime.utcnow() - deleted_at).days
                info += f"⏳ **Deleted {days_ago} days ago**\n"
        
        if file_data.get('deleted_by'):
            info += f"👤 **Deleted by:** {file_data['deleted_by']}\n"
        
        if file_data.get('deleted_reason'):
            info += f"📝 **Reason:** {file_data['deleted_reason']}\n"
        
        return info
    
    @staticmethod
    def get_rarity_emoji(rarity_name: str) -> str:
        """Get emoji for rarity name"""
        if rarity_name and len(rarity_name) > 0:
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
        for rarity_num, rarity_name in Config.RARITY_MAP.items():
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
        
        # Add all files option
        keyboard.append([
            InlineKeyboardButton(
                "📊 All Files",
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
                "🔍 Search Files",
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
        for perm_key, perm_desc in Config.PERMISSIONS.items():
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
    def format_file_list(files: List[Dict], page: int, total_count: int, title: str = "Files") -> str:
        """Format a list of files for display"""
        if not files:
            return f"❌ No {title.lower()} found."
        
        start_num = page * Config.ITEMS_PER_PAGE + 1
        end_num = min(start_num + len(files) - 1, total_count)
        
        message = f"**{title}**\n"
        message += f"📊 **Showing {start_num}-{end_num} of {total_count}**\n\n"
        
        for i, file in enumerate(files, start=start_num):
            emoji = Helpers.get_rarity_emoji(file.get('rarity', ''))
            message += f"{i}. **{file.get('file_name', 'Unknown')}**\n"
            message += f"   {emoji} {file.get('rarity', 'Unknown')} | ID: `{file.get('file_id', 'N/A')}`\n\n"
        
        return message
    
    @staticmethod
    def format_deleted_file_list(files: List[Dict], page: int, total_count: int) -> str:
        """Format a list of deleted files for display"""
        if not files:
            return "🗑️ **Recycle Bin is empty!**\n\nNo deleted files found."
        
        start_num = page * Config.ITEMS_PER_PAGE + 1
        end_num = min(start_num + len(files) - 1, total_count)
        
        message = f"🗑️ **Recycle Bin (Deleted Files)**\n"
        message += f"📊 **Showing {start_num}-{end_num} of {total_count}**\n\n"
        
        for i, file in enumerate(files, start=start_num):
            emoji = Helpers.get_rarity_emoji(file.get('rarity', ''))
            
            # Calculate days since deletion
            days_ago = 0
            if file.get('deleted_at') and isinstance(file['deleted_at'], datetime):
                days_ago = (datetime.utcnow() - file['deleted_at']).days
            
            message += f"{i}. **{file.get('file_name', 'Unknown')}**\n"
            message += f"   {emoji} {file.get('rarity', 'Unknown')}\n"
            message += f"   🆔 `{file.get('file_id', 'N/A')}` | 🗑️ {days_ago}d ago\n\n"
        
        return message
    
    @staticmethod
    def parse_rarity(rarity_input: str) -> Optional[str]:
        """Parse rarity input for new rarity system (1-14)"""
        try:
            rarity_num = int(rarity_input.strip())
            if 1 <= rarity_num <= 14:
                return Config.RARITY_MAP[rarity_num]
            return None
        except (ValueError, KeyError):
            return None

helpers = Helpers()

# ==================== DECORATORS ====================
def admin_only(func):
    """Decorator to restrict access to bot owner only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != Config.OWNER_ID:
            await update.message.reply_text("⛔ This command is for bot owner only.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def sudo_only(permission: str):
    """Decorator to restrict access to sudo users with specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            
            # Owner always has permission
            if user_id == Config.OWNER_ID:
                return await func(update, context, *args, **kwargs)
            
            # Check sudo permission
            if not db.has_permission(user_id, permission):
                await update.message.reply_text(
                    f"❌ You are not authorized to use this command.\n\n"
                    f"You need '{permission}' permission. Contact the bot owner."
                )
                return
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with complete feature overview"""
    user = update.effective_user
    db.ensure_user(user.id, user.username, user.first_name)
    
    welcome_text = f"""
🌟 **Welcome to Complete Upload Bot** 🌟

**Complete Bot with All Features:**

📤 **UPLOAD SYSTEM:**
• Upload files with rarity system (1-14)
• Supports photos, videos, audio, documents
• Automatic metadata extraction
• Custom tags and descriptions

🏷️ **RARITY SYSTEM (1-14):**
1. ⚪ Common
2. 🟢 Uncommon
3. 🔴 Rare
4. 🟡 Legendary
5. 🎐 Limited Edition
6. 💎 Premium
7. 🥵 Exotic
8. 🎬 Animated
9. 🌩️ Thundra
10. ☄️ Galvoria
11. 🌈 Neon
12. 🛡️ Supreme
13. 🔮 Crystal
14. 🎤 Celebrity

🗑️ **RECYCLE BIN SYSTEM:**
• Deleted files go to recycle bin
• Restore deleted files anytime
• Auto-cleanup after 30 days
• View deleted file history

🔄 **FILL SYSTEM:**
• Fill deleted file slots with new files
• Reuse deleted file IDs
• Maintains ID continuity

👑 **SUDO SYSTEM:**
• Granular permission control
• Different access levels
• Inline permission management

📚 **VIEWING SYSTEM:**
• Browse files by rarity
• Search files by name or description
• View file details and statistics
• Paginated browsing

**Main Commands:**
• /menu - Browse file database
• /upload - Upload new file
• /fill - Fill deleted slot
• /restore - Restore deleted file
• /deleted - View recycle bin
• /search - Search files
• /stats - View statistics
• /help - Show detailed help
• /sudolist - View sudo users (Owner only)
• /addsudo - Add sudo user (Owner only)
• /removesudo - Remove sudo user (Owner only)
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")],
        [InlineKeyboardButton("📤 Upload File", callback_data="upload_help")],
        [InlineKeyboardButton("🔄 Fill Deleted Slot", callback_data="fill_example")],
        [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
        [InlineKeyboardButton("ℹ️ Help Guide", callback_data="help_main")]
    ])
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed help message"""
    help_text = """
ℹ️ **Complete Bot Help Guide**

📤 **UPLOADING FILES:**
1. Send a photo/video/audio/document
2. Reply to it with: `/upload "File Name" "Description" Rarity`

**Examples:**
• `/upload "Project Report" "Q4 Financial Analysis" 3`
• `/upload "Vacation Photos" "Summer 2024 Album" 10`

**Rarity Numbers (1-14):**
1. ⚪ Common
2. 🟢 Uncommon
3. 🔴 Rare
4. 🟡 Legendary
5. 🎐 Limited Edition
6. 💎 Premium
7. 🥵 Exotic
8. 🎬 Animated
9. 🌩️ Thundra
10. ☄️ Galvoria
11. 🌈 Neon
12. 🛡️ Supreme
13. 🔮 Crystal
14. 🎤 Celebrity

🔄 **FILLING DELETED SLOTS:**
• `/fill ID "File Name" "Description" Rarity`
• `/fill oldest "File Name" "Description" Rarity`
• Reuses deleted file IDs from recycle bin

🗑️ **RECYCLE BIN SYSTEM:**
• /deleted - View deleted files
• /restore ID - Restore a deleted file
• /searchdeleted query - Search deleted files
• /delete ID - Move file to recycle bin
• Deleted files auto-clean after 30 days

📚 **BROWSING FILES:**
• /menu - Browse by rarity
• /search query - Search files
• /info ID - View file details
• /myuploads - View your uploads
• /stats - View database statistics

⚙️ **EDITING FILES:**
• /edit ID "New Name" "New Description" Rarity
• /editmedia ID - Edit media (reply to new media)

👑 **SUDO MANAGEMENT (Owner only):**
• /addsudo @username - Add sudo user
• /removesudo @username - Remove sudo user
• /sudolist - List all sudo users
• /setsudo @username - Set specific permissions

⚠️ **DATABASE RESET (Owner only):**
• /reset - Reset database (requires 3 confirmations)

**Note:** Commands require appropriate sudo permissions.
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")],
        [InlineKeyboardButton("📤 Upload Example", callback_data="upload_example")],
        [InlineKeyboardButton("🔄 Fill Example", callback_data="fill_example")],
        [InlineKeyboardButton("🗑️ Recycle Bin", callback_data="deleted_list_0_main")],
        [InlineKeyboardButton("📊 View Stats", callback_data="stats_main")]
    ])
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@sudo_only('upload')
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /upload command with rarity system"""
    user = update.effective_user
    
    # Check if message is a reply to media
    if not update.message.reply_to_message or not (
        update.message.reply_to_message.document or 
        update.message.reply_to_message.photo or 
        update.message.reply_to_message.video or 
        update.message.reply_to_message.audio
    ):
        await update.message.reply_text(
            "❌ **Please reply to a media file with this command!**\n\n"
            "**Usage:** Reply to a photo/video/audio/document with:\n"
            "`/upload \"File Name\" \"Description\" Rarity`\n\n"
            "**Examples:**\n"
            "• `/upload \"Project Report\" \"Q4 Financial Analysis\" 3`\n"
            "• `/upload \"Vacation Photos\" \"Summer 2024 Album\" 10`\n\n"
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
    args = update.message.text.split()
    if len(args) < 4:
        await update.message.reply_text(
            "❌ **Invalid syntax!**\n\n"
            "**Usage:** `/upload \"File Name\" \"Description\" Rarity`\n\n"
            "**Note:** Use quotes for names with spaces\n"
            "**Example:** `/upload \"Project Report\" \"Financial Analysis\" 3`"
        )
        return
    
    # Parse file name (support quotes)
    file_name = ""
    description = ""
    rarity_input = ""
    
    text = update.message.text
    text = text.replace('/upload', '', 1).strip()
    
    # Parse file name (might be in quotes)
    if text.startswith('"'):
        end_quote = text.find('"', 1)
        if end_quote == -1:
            await update.message.reply_text("❌ Invalid format. Missing closing quote for file name.")
            return
        file_name = text[1:end_quote]
        text = text[end_quote + 1:].strip()
    else:
        parts = text.split()
        file_name = parts[0]
        text = ' '.join(parts[1:])
    
    # Parse description (might be in quotes)
    if text.startswith('"'):
        end_quote = text.find('"', 1)
        if end_quote == -1:
            await update.message.reply_text("❌ Invalid format. Missing closing quote for description.")
            return
        description = text[1:end_quote]
        text = text[end_quote + 1:].strip()
    else:
        parts = text.split()
        if not parts:
            await update.message.reply_text("❌ Missing description.")
            return
        description = parts[0]
        text = ' '.join(parts[1:])
    
    # The rest is rarity
    rarity_input = text.strip()
    
    if not file_name or not description or not rarity_input:
        await update.message.reply_text("❌ Missing required parameters.")
        return
    
    # Parse rarity
    rarity_name = helpers.parse_rarity(rarity_input)
    if not rarity_name:
        await update.message.reply_text(
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
    
    # Get file from replied message
    message = update.message.reply_to_message
    file_obj = None
    file_type = None
    
    if message.document:
        file_obj = message.document
        file_type = "document"
    elif message.photo:
        file_obj = message.photo[-1]
        file_type = "photo"
    elif message.video:
        file_obj = message.video
        file_type = "video"
    elif message.audio:
        file_obj = message.audio
        file_type = "audio"
    else:
        await update.message.reply_text("❌ Unsupported file type.")
        return
    
    # Check file size
    if file_obj.file_size > Config.MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ File too large! Maximum size is {helpers.format_size(Config.MAX_FILE_SIZE)}."
        )
        return
    
    # Send processing message
    status_msg = await update.message.reply_text("🔄 Starting upload process...")
    
    try:
        # Get next file ID
        file_id = db.get_next_file_id()
        
        # Create file metadata
        file_metadata = FileMetadata(
            file_name=file_name,
            description=description,
            rarity=rarity_name,
            file_id=file_id,
            telegram_file_id=file_obj.file_id,
            file_type=file_type,
            file_size=file_obj.file_size,
            added_by=user.id,
            tags=[],  # Can be extended to parse tags from description
            privacy="public"
        )
        
        # Save to database
        inserted_id = db.insert_file(file_metadata)
        
        # Update user stats
        db.increment_user_uploads(user.id)
        
        # Send success message
        success_text = (
            f"✅ **File #{file_id} Uploaded Successfully!**\n\n"
            f"📁 **Name:** {file_name}\n"
            f"📝 **Description:** {description}\n"
            f"🏷️ **Rarity:** {rarity_name}\n"
            f"📏 **Size:** {helpers.format_size(file_obj.file_size)}\n"
            f"🆔 **File ID:** `{file_id}`\n\n"
            f"**Use this ID to edit or delete the file.**"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👁️ View File", callback_data=f"info_{file_id}")],
            [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")]
        ])
        
        await status_msg.edit_text(success_text, reply_markup=keyboard)
        
        # Log to channel if configured
        if Config.LOG_CHANNEL:
            try:
                log_message = (
                    f"🆕 **New File Uploaded!**\n\n"
                    f"📁 **Name:** {file_name}\n"
                    f"📝 **Description:** {description}\n"
                    f"🏷️ **Rarity:** {rarity_name}\n"
                    f"👤 **Uploaded by:** @{user.username or user.first_name}\n"
                    f"🆔 **File ID:** {file_id}"
                )
                await context.bot.send_message(Config.LOG_CHANNEL, log_message)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        await status_msg.edit_text("❌ Failed to upload file. Please try again.")

@admin_only
async def addsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add sudo user (Owner only)"""
    args = update.message.text.split()
    if len(args) != 2:
        await update.message.reply_text(
            "👑 **Add Sudo User**\n\n"
            "**Usage:** `/addsudo @username`\n\n"
            "**Example:** `/addsudo @username`\n\n"
            "**Note:** This will give the user all permissions by default.\n"
            "Use /setsudo to set specific permissions."
        )
        return
    
    target_username = args[1].replace('@', '')
    
    try:
        # Get user from mention or username
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        else:
            # Try to get user by username (limited in Telegram Bot API)
            await update.message.reply_text(
                "Please reply to a user's message with `/addsudo` or use their numeric ID.\n\n"
                "To get a user's ID, forward a message from them to @userinfobot"
            )
            return
        
        # Check if already sudo
        existing_sudo = db.get_sudo_user(target_user.id)
        if existing_sudo:
            await update.message.reply_text(f"❌ @{target_user.username} is already a sudo user.")
            return
        
        # Add with all permissions by default
        all_permissions = list(Config.PERMISSIONS.keys())
        db.add_sudo_user(target_user.id, all_permissions)
        
        await update.message.reply_text(
            f"✅ **Sudo User Added!**\n\n"
            f"👤 **User:** @{target_user.username or target_user.first_name} (ID: {target_user.id})\n"
            f"🔑 **Permissions:** All permissions granted\n\n"
            f"Use /setsudo to modify specific permissions."
        )
        
        logger.info(f"Sudo user added: @{target_user.username} ({target_user.id})")
        
    except Exception as e:
        logger.error(f"Error adding sudo user: {e}")
        await update.message.reply_text("❌ Error adding sudo user.")

@admin_only
async def removesudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove sudo user (Owner only)"""
    args = update.message.text.split()
    if len(args) != 2:
        await update.message.reply_text(
            "👑 **Remove Sudo User**\n\n"
            "**Usage:** `/removesudo @username`\n\n"
            "**Example:** `/removesudo @username`"
        )
        return
    
    target_username = args[1].replace('@', '')
    
    try:
        # Get user from mention
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        else:
            await update.message.reply_text("Please reply to the user's message.")
            return
        
        # Remove sudo
        removed = db.remove_sudo_user(target_user.id)
        
        if removed:
            await update.message.reply_text(
                f"✅ **Sudo User Removed!**\n\n"
                f"👤 **User:** @{target_user.username or target_user.first_name} (ID: {target_user.id})\n"
                f"🔓 **Status:** All permissions revoked"
            )
            
            logger.info(f"Sudo user removed: @{target_user.username} ({target_user.id})")
        else:
            await update.message.reply_text(f"❌ @{target_user.username} is not a sudo user.")
            
    except Exception as e:
        logger.error(f"Error removing sudo user: {e}")
        await update.message.reply_text("❌ Error removing sudo user.")

@admin_only
async def sudolist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all sudo users (Owner only)"""
    sudo_users = db.get_all_sudo_users()
    
    if not sudo_users:
        await update.message.reply_text("👑 **No Sudo Users Found**\n\nNo sudo users have been added yet.")
        return
    
    message_text = "👑 **Sudo Users List**\n\n"
    
    for i, sudo in enumerate(sudo_users, 1):
        user_id = sudo.get('user_id')
        permissions = sudo.get('permissions', [])
        added_at = sudo.get('added_at', datetime.utcnow())
        
        # Try to get username from database
        user_data = db.users.find_one({"user_id": user_id})
        username = user_data.get('username', f"User {user_id}") if user_data else f"User {user_id}"
        
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
    
    await update.message.reply_text(message_text, reply_markup=keyboard)

@admin_only
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset database with 3 warnings (Owner only)"""
    user_id = update.effective_user.id
    
    # Get current warnings
    warning_count, last_warning = db.get_reset_warnings(user_id)
    
    # Check if warnings have expired (24 hours)
    warning_expired = False
    if last_warning:
        hours_since_warning = (datetime.utcnow() - last_warning).total_seconds() / 3600
        if hours_since_warning > 24:
            warning_expired = True
            db.clear_reset_warnings(user_id)
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
        
        total_files = db.get_file_count()
        total_deleted = db.get_deleted_files_count()
        
        await update.message.reply_text(
            f"⚠️ **FINAL WARNING - DATABASE RESET** ⚠️\n\n"
            f"🚨 **This is your FINAL warning!**\n\n"
            f"📊 **Current Database Stats:**\n"
            f"• Active Files: {total_files}\n"
            f"• Deleted Files: {total_deleted}\n"
            f"• Total: {total_files + total_deleted}\n\n"
            f"❌ **THIS ACTION WILL:**\n"
            f"1. Delete ALL files\n"
            f"2. Delete ALL deleted files\n"
            f"3. Reset file ID counter to 0\n"
            f"4. Clear ALL data\n\n"
            f"🔥 **THIS ACTION IS IRREVERSIBLE!**\n\n"
            f"Are you ABSOLUTELY sure you want to reset the database?",
            reply_markup=keyboard
        )
        
    else:
        # Add warning
        new_warning_count, _ = db.add_reset_warning(user_id)
        
        total_files = db.get_file_count()
        total_deleted = db.get_deleted_files_count()
        
        if new_warning_count == 1:
            warning_text = "FIRST"
        elif new_warning_count == 2:
            warning_text = "SECOND"
        else:
            warning_text = "THIRD"
        
        await update.message.reply_text(
            f"⚠️ **{warning_text} WARNING - DATABASE RESET** ⚠️\n\n"
            f"🚨 **Warning {new_warning_count}/3**\n\n"
            f"📊 **Current Database Stats:**\n"
            f"• Active Files: {total_files}\n"
            f"• Deleted Files: {total_deleted}\n"
            f"• Total: {total_files + total_deleted}\n\n"
            f"❌ **Resetting will delete ALL data!**\n\n"
            f"⚠️ **You need {3 - new_warning_count} more warning(s) before you can reset.**\n"
            f"Send `/reset` again to continue."
        )

@sudo_only('fill')
async def fill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /fill command - add file in place of deleted file"""
    user = update.effective_user
    
    # Check if message is a reply to media
    if not update.message.reply_to_message or not (
        update.message.reply_to_message.document or 
        update.message.reply_to_message.photo or 
        update.message.reply_to_message.video or 
        update.message.reply_to_message.audio
    ):
        await update.message.reply_text(
            "🔄 **Fill Deleted File Slot**\n\n"
            "**Usage:** Reply to a media file with:\n"
            "`/fill file_id \"File Name\" \"Description\" Rarity`\n\n"
            "**Examples:**\n"
            "• `/fill 123 \"Project Report\" \"Financial Analysis\" 3`\n"
            "• `/fill 456 \"Vacation Photos\" \"Summer Album\" 10`\n\n"
            "**To fill oldest deleted slot:**\n"
            "`/fill oldest \"File Name\" \"Description\" Rarity`\n\n"
            "**To see available deleted IDs:**\n"
            "Use `/deleted` to view recycle bin\n"
            "Use `/searchdeleted` to search deleted files"
        )
        return
    
    # Parse arguments
    args = update.message.text.split()
    if len(args) < 4:
        await update.message.reply_text(
            "❌ **Invalid syntax!**\n\n"
            "**Usage:** `/fill file_id \"File Name\" \"Description\" Rarity`\n\n"
            "**Examples:**\n"
            "• `/fill 123 \"Project Report\" \"Financial Analysis\" 3`\n"
            "• `/fill oldest \"New File\" \"Description\" 4`\n\n"
            "**Note:** Use quotes for names with spaces\n"
            "Use `oldest` to fill the oldest deleted file slot."
        )
        return
    
    # Parse target ID (could be "oldest" or a number)
    target_id_input = args[1].lower()
    
    if target_id_input == "oldest":
        # Get the oldest deleted file
        oldest_deleted = db.get_oldest_deleted_file()
        if not oldest_deleted:
            await update.message.reply_text("❌ No deleted files found in recycle bin!")
            return
        file_id = oldest_deleted.get("file_id")
    else:
        try:
            file_id = int(target_id_input)
        except ValueError:
            await update.message.reply_text("❌ Invalid file ID. Must be a number or 'oldest'.")
            return
        
        # Check if file exists in deleted collection
        deleted_file = db.get_deleted_file_by_id(file_id)
        if not deleted_file:
            # Check if ID is already in use
            active_file = db.get_file_by_id(file_id)
            if active_file:
                await update.message.reply_text(
                    f"❌ File ID `{file_id}` is already in use!\n\n"
                    f"**Current File:**\n"
                    f"• Name: {active_file.get('file_name')}\n"
                    f"• Description: {active_file.get('description')}\n\n"
                    f"Use a different ID or delete the file first."
                )
            else:
                await update.message.reply_text(
                    f"❌ File ID `{file_id}` not found in recycle bin!\n\n"
                    f"**Available options:**\n"
                    f"• Use `/deleted` to view deleted files\n"
                    f"• Use `/fill oldest` to fill the oldest deleted slot\n"
                    f"• Use a different deleted file ID"
                )
            return
    
    # Parse file details
    text = update.message.text
    text = text.replace(f'/fill {args[1]}', '', 1).strip()
    
    # Parse file name
    file_name = ""
    if text.startswith('"'):
        end_quote = text.find('"', 1)
        if end_quote == -1:
            await update.message.reply_text("❌ Invalid format. Missing closing quote for file name.")
            return
        file_name = text[1:end_quote]
        text = text[end_quote + 1:].strip()
    else:
        parts = text.split()
        file_name = parts[0]
        text = ' '.join(parts[1:])
    
    # Parse description
    description = ""
    if text.startswith('"'):
        end_quote = text.find('"', 1)
        if end_quote == -1:
            await update.message.reply_text("❌ Invalid format. Missing closing quote for description.")
            return
        description = text[1:end_quote]
        text = text[end_quote + 1:].strip()
    else:
        parts = text.split()
        if not parts:
            await update.message.reply_text("❌ Missing description.")
            return
        description = parts[0]
        text = ' '.join(parts[1:])
    
    # Parse rarity
    rarity_input = text.strip()
    rarity_name = helpers.parse_rarity(rarity_input)
    
    if not rarity_name:
        await update.message.reply_text(
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
    
    # Get file from replied message
    message = update.message.reply_to_message
    file_obj = None
    file_type = None
    
    if message.document:
        file_obj = message.document
        file_type = "document"
    elif message.photo:
        file_obj = message.photo[-1]
        file_type = "photo"
    elif message.video:
        file_obj = message.video
        file_type = "video"
    elif message.audio:
        file_obj = message.audio
        file_type = "audio"
    else:
        await update.message.reply_text("❌ Unsupported file type.")
        return
    
    # Check file size
    if file_obj.file_size > Config.MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ File too large! Maximum size is {helpers.format_size(Config.MAX_FILE_SIZE)}."
        )
        return
    
    # Send processing message
    status_msg = await update.message.reply_text(f"🔄 Filling file slot #{file_id}...")
    
    try:
        # Create file metadata
        file_metadata = FileMetadata(
            file_name=file_name,
            description=description,
            rarity=rarity_name,
            file_id=file_id,
            telegram_file_id=file_obj.file_id,
            file_type=file_type,
            file_size=file_obj.file_size,
            added_by=user.id
        )
        
        # Fill the deleted file slot
        filled = db.fill_deleted_file(file_id, file_metadata)
        
        if filled:
            # Update user stats
            db.increment_user_uploads(user.id)
            
            # Get info about the replaced file
            replaced_file = db.get_deleted_file_by_id(file_id)
            replaced_info = ""
            if replaced_file:
                replaced_info = (
                    f"\n🔄 **Replaced Deleted File:**\n"
                    f"• Name: {replaced_file.get('file_name', 'Unknown')}\n"
                    f"• Description: {replaced_file.get('description', 'Unknown')}\n"
                    f"• Deleted on: {replaced_file.get('deleted_at', 'Unknown')}\n"
                )
            
            # Success message
            success_text = (
                f"🔄 **File Slot #{file_id} Filled Successfully!**\n\n"
                f"📁 **New File:** {file_name}\n"
                f"📝 **Description:** {description}\n"
                f"🏷️ **Rarity:** {rarity_name}\n"
                f"📏 **Size:** {helpers.format_size(file_obj.file_size)}\n"
                f"🆔 **File ID:** `{file_id}`\n"
                f"{replaced_info}\n"
                f"✅ **Slot has been successfully reused!**"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👁️ View File", callback_data=f"info_{file_id}")],
                [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
                [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")]
            ])
            
            await status_msg.edit_text(success_text, reply_markup=keyboard)
            
            logger.info(f"File slot {file_id} filled by user {user.id}")
        else:
            await status_msg.edit_text(f"❌ Failed to fill file slot #{file_id}. It may no longer exist in recycle bin.")
            
    except Exception as e:
        logger.error(f"Error filling file: {e}")
        await status_msg.edit_text("❌ Error filling file slot. Please try again.")

@sudo_only('restore')
async def restore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /restore command - restore deleted file"""
    args = update.message.text.split()
    if len(args) != 2:
        await update.message.reply_text(
            "♻️ **Restore Deleted File**\n\n"
            "**Usage:** `/restore file_id`\n\n"
            "**Example:** `/restore 123`\n\n"
            "You can find file IDs in the recycle bin using /deleted command."
        )
        return
    
    try:
        file_id = int(args[1])
        
        # Check if file exists in deleted collection
        file_data = db.get_deleted_file_by_id(file_id)
        if not file_data:
            await update.message.reply_text(f"❌ File with ID `{file_id}` not found in recycle bin!")
            return
        
        # Restore file
        restored = db.restore_file(file_id)
        
        if restored:
            await update.message.reply_text(
                f"♻️ **File #{file_id} Restored Successfully!**\n\n"
                f"📁 **Name:** {file_data.get('file_name', 'Unknown')}\n"
                f"📝 **Description:** {file_data.get('description', 'Unknown')}\n"
                f"🏷️ **Rarity:** {file_data.get('rarity', 'Unknown')}\n\n"
                f"The file has been moved back to the active database."
            )
            
            logger.info(f"File {file_id} restored by user {update.effective_user.id}")
        else:
            await update.message.reply_text("❌ Failed to restore file.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid file ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error in restore command: {e}")
        await update.message.reply_text("❌ Error restoring file.")

@sudo_only('view_deleted')
async def deleted_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show deleted files (recycle bin)"""
    await update.message.reply_text("🗑️ Loading recycle bin...")
    
    # Get deleted files
    files, total_count = db.get_deleted_files(page=0)
    
    if not files:
        await update.message.reply_text(
            "🗑️ **Recycle Bin is Empty!**\n\n"
            "No deleted files found.\n"
            "Deleted files are automatically cleaned up after 30 days."
        )
        return
    
    total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
    
    # Format message
    message_text = helpers.format_deleted_file_list(files, 0, total_count)
    
    # Create keyboard
    keyboard = helpers.create_pagination_keyboard(0, total_pages, "deleted_list", "main")
    
    # Add action buttons for each file
    buttons = []
    for file in files[:3]:
        file_id = file.get('file_id')
        if file_id:
            buttons.append([
                InlineKeyboardButton(
                    f"♻️ Restore {file.get('file_name', 'Unknown')[:10]}...",
                    callback_data=f"restore_{file_id}"
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    f"👁️ View {file.get('file_name', 'Unknown')[:10]}...",
                    callback_data=f"deleted_info_{file_id}"
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
    keyboard.inline_keyroom=keyboard
        await update.message.reply_text(message_text, reply_markup=keyboard)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu"""
    total_files = db.get_file_count()
    total_deleted = db.get_deleted_files_count()
    
    menu_text = (
        f"📚 **File Database Menu**\n"
        f"📊 **Active Files:** {total_files}\n"
        f"🗑️ **Deleted Files:** {total_deleted}\n\n"
        "Select a rarity to browse files:"
    )
    
    keyboard = helpers.create_rarity_keyboard("main")
    await update.message.reply_text(menu_text, reply_markup=keyboard)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command"""
    args = update.message.text.split()
    if len(args) < 2:
        await update.message.reply_text(
            "🔍 **Search Files**\n\n"
            "**Usage:** `/search query`\n\n"
            "**Examples:**\n"
            "• `/search project`\n"
            "• `/search report`\n"
            "• `/search vacation photos`\n\n"
            "You can search by file name or description."
        )
        return
    
    query = ' '.join(args[1:])
    await update.message.reply_text(f"🔍 Searching for: `{query}`...")
    
    # Perform search
    files, total_count = db.search_files_paginated(query, page=0)
    
    if not files:
        await update.message.reply_text(f"❌ No results found for: `{query}`")
        return
    
    total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
    
    # Format message
    message_text = helpers.format_file_list(
        files, 0, total_count, 
        f"Search Results for: '{query}'"
    )
    
    # Create keyboard
    keyboard = helpers.create_pagination_keyboard(0, total_pages, "search", query)
    
    # Add view buttons for each file
    buttons = []
    for file in files[:5]:
        file_id = file.get('file_id')
        if file_id:
            buttons.append([
                InlineKeyboardButton(
                    f"👁️ {file.get('file_name', 'Unknown')[:15]}...",
                    callback_data=f"info_{file_id}"
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
    
    await update.message.reply_text(message_text, reply_markup=keyboard)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show database statistics"""
    # Get various stats
    total_files = db.get_file_count()
    total_deleted = db.get_deleted_files_count()
    rarity_stats = db.get_rarity_stats()
    top_uploaders = db.get_top_uploaders(10)
    
    # Clean up old deleted files
    cleaned_count = db.cleanup_old_deleted()
    
    # Format stats message
    stats_text = f"📈 **Database Statistics**\n\n"
    stats_text += f"📊 **Active Files:** {total_files}\n"
    stats_text += f"🗑️ **Deleted Files:** {total_deleted}\n"
    if cleaned_count > 0:
        stats_text += f"🧹 **Recently Cleaned:** {cleaned_count} (older than {Config.RECYCLE_BIN_MAX_DAYS} days)\n"
    stats_text += f"📈 **Total (All Time):** {total_files + total_deleted}\n\n"
    
    stats_text += "**Files by Rarity:**\n"
    for rarity_num, rarity_name in Config.RARITY_MAP.items():
        count = rarity_stats.get(rarity_name, 0)
        percentage = (count / total_files * 100) if total_files > 0 else 0
        emoji = helpers.get_rarity_emoji(rarity_name)
        stats_text += f"{emoji} **{rarity_name.split(' ', 1)[-1]}:** {count} ({percentage:.1f}%)\n"
    
    stats_text += f"\n**Top Uploaders:**\n"
    for i, uploader in enumerate(top_uploaders, 1):
        user_id = uploader["_id"]
        count = uploader["count"]
        
        # Try to get username from database
        user_data = db.users.find_one({"user_id": user_id})
        username = user_data.get('username', f"User {user_id}") if user_data else f"User {user_id}"
        
        stats_text += f"{i}. {username}: {count} files\n"
    
    # Add keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="stats_refresh")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
    ])
    
    await update.message.reply_text(stats_text, reply_markup=keyboard)

async def myuploads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's uploaded files"""
    user_id = update.effective_user.id
    
    await update.message.reply_text("📂 Loading your uploaded files...")
    
    # Get user's files
    files, total_count = db.get_user_files_paginated(user_id, page=0)
    
    if not files:
        await update.message.reply_text("📭 You haven't uploaded any files yet.")
        return
    
    total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
    
    # Format message
    message_text = helpers.format_file_list(
        files, 0, total_count, 
        "Your Uploaded Files"
    )
    
    # Create keyboard
    keyboard = helpers.create_pagination_keyboard(0, total_pages, "myuploads", "")
    
    # Add view buttons for each file
    buttons = []
    for file in files[:5]:
        file_id = file.get('file_id')
        if file_id:
            buttons.append([
                InlineKeyboardButton(
                    f"👁️ {file.get('file_name', 'Unknown')[:15]}...",
                    callback_data=f"info_{file_id}"
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
    
    await update.message.reply_text(message_text, reply_markup=keyboard)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show file information by ID"""
    args = update.message.text.split()
    if len(args) != 2:
        await update.message.reply_text(
            "ℹ️ **File Information**\n\n"
            "**Usage:** `/info file_id`\n\n"
            "**Example:** `/info 123`\n\n"
            "You can find file IDs by browsing the database or searching."
        )
        return
    
    try:
        file_id = int(args[1])
        await _show_file_info(update, context, file_id)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid file ID. Please enter a number.")
    except Exception as e:
        logger.error(f"Error in info command: {e}")
        await update.message.reply_text("❌ Error fetching file information.")

@sudo_only('edit')
async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /edit command - edit file details"""
    args = update.message.text.split()
    if len(args) < 5:
        await update.message.reply_text(
            "✏️ **Edit File**\n\n"
            "**Usage:** `/edit ID \"New Name\" \"New Description\" Rarity`\n\n"
            "**Examples:**\n"
            "• `/edit 123 \"Updated Report\" \"Revised Analysis\" 3`\n"
            "• `/edit 456 \"New Name\" \"New Description\" 10`\n\n"
            "**Note:** Use quotes for names with spaces"
        )
        return
    
    try:
        file_id = int(args[1])
        
        # Simple parsing similar to upload
        text = update.message.text
        text = text.replace(f'/edit {args[1]}', '', 1).strip()
        
        # Parse new file name
        new_file_name = ""
        if text.startswith('"'):
            end_quote = text.find('"', 1)
            if end_quote == -1:
                await update.message.reply_text("❌ Missing closing quote for file name.")
                return
            new_file_name = text[1:end_quote]
            text = text[end_quote + 1:].strip()
        else:
            parts = text.split()
            new_file_name = parts[0]
            text = ' '.join(parts[1:])
        
        # Parse new description
        new_description = ""
        if text.startswith('"'):
            end_quote = text.find('"', 1)
            if end_quote == -1:
                await update.message.reply_text("❌ Missing closing quote for description.")
                return
            new_description = text[1:end_quote]
            text = text[end_quote + 1:].strip()
        else:
            parts = text.split()
            if not parts:
                await update.message.reply_text("❌ Missing description.")
                return
            new_description = parts[0]
            text = ' '.join(parts[1:])
        
        # Parse rarity
        rarity_input = text.strip()
        new_rarity = helpers.parse_rarity(rarity_input)
        
        if not new_rarity:
            await update.message.reply_text("❌ Invalid rarity. Must be 1-14.")
            return
        
        # Check if file exists
        file_data = db.get_file_by_id(file_id)
        if not file_data:
            await update.message.reply_text("❌ File not found!")
            return
        
        # Update file
        updated = db.update_file(
            file_id=file_id,
            file_name=new_file_name,
            description=new_description,
            rarity=new_rarity
        )
        
        if updated:
            await update.message.reply_text(f"✅ File `{file_id}` updated successfully!")
            logger.info(f"File {file_id} edited by user {update.effective_user.id}")
        else:
            await update.message.reply_text("❌ Failed to update file.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid file ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error in edit command: {e}")
        await update.message.reply_text("❌ Error updating file. Please check the format.")

@sudo_only('delete')
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delete command - move file to recycle bin"""
    args = update.message.text.split()
    if len(args) != 2:
        await update.message.reply_text(
            "🗑️ **Delete File**\n\n"
            "**Usage:** `/delete ID`\n\n"
            "**Example:** `/delete 123`\n\n"
            "**Note:** This moves the file to the recycle bin where it can be restored later."
        )
        return
    
    try:
        file_id = int(args[1])
        file_data = db.get_file_by_id(file_id)
        
        if not file_data:
            await update.message.reply_text("❌ File not found!")
            return
        
        # Show confirmation
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, Move to Recycle Bin", callback_data=f"soft_delete_{file_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")
            ]
        ])
        
        await update.message.reply_text(
            f"⚠️ **Are you sure you want to move this file to the recycle bin?**\n\n"
            f"**Name:** {file_data['file_name']}\n"
            f"**Description:** {file_data.get('description', 'No description')}\n"
            f"**ID:** `{file_id}`\n\n"
            f"**Note:** The file can be restored from the recycle bin later.",
            reply_markup=keyboard
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid file ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error in delete command: {e}")
        await update.message.reply_text("❌ Error processing delete request.")

# ==================== CALLBACK QUERY HANDLER ====================
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    try:
        # Handle noop (do nothing)
        if data == "noop":
            return
        
        # Handle menu
        elif data == "menu_main":
            await _show_main_menu(query)
        
        # Handle rarity selection
        elif data.startswith("rarity_"):
            parts = data.split("_")
            if len(parts) >= 3:
                rarity_num = int(parts[1])
                current_view = parts[2] if len(parts) > 2 else "main"
                
                # Show files for this rarity
                files, total_count = db.get_files_by_rarity(
                    Config.RARITY_MAP[rarity_num], 0
                )
                
                if not files:
                    await query.answer(f"No files found for rarity {rarity_num}", show_alert=True)
                    return
                
                total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
                
                message_text = helpers.format_file_list(
                    files, 0, total_count,
                    f"{Config.RARITY_MAP[rarity_num]} Files"
                )
                
                keyboard = helpers.create_pagination_keyboard(0, total_pages, "rarity", f"{rarity_num}_{current_view}")
                
                buttons = []
                for file in files[:3]:
                    file_id = file.get('file_id')
                    if file_id:
                        buttons.append([
                            InlineKeyboardButton(
                                f"👁️ {file.get('file_name', 'Unknown')[:15]}...",
                                callback_data=f"info_{file_id}"
                            )
                        ])
                
                if buttons:
                    keyboard.inline_keyboard.extend(buttons)
                
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
                ])
                
                await query.message.edit_text(message_text, reply_markup=keyboard)
        
        # View all files
        elif data.startswith("view_all_"):
            parts = data.split("_")
            current_view = parts[2] if len(parts) > 2 else "main"
            await _show_all_files(query, 0, current_view)
        
        # View deleted files
        elif data.startswith("deleted_list_"):
            parts = data.split("_")
            page = int(parts[2])
            current_view = parts[3] if len(parts) > 3 else "main"
            await _show_deleted_files(query, page, current_view)
        
        # Pagination for search
        elif data.startswith("search_page_"):
            parts = data.split("_")
            page = int(parts[2])
            query_text = '_'.join(parts[3:])
            await _show_search_results(query, query_text, page)
        
        # File info
        elif data.startswith("info_"):
            file_id = int(data.split("_")[1])
            await _show_file_info_callback(query, context, file_id)
        
        # Deleted file info
        elif data.startswith("deleted_info_"):
            file_id = int(data.split("_")[2])
            file_data = db.get_deleted_file_by_id(file_id)
            
            if not file_data:
                await query.answer("File not found in recycle bin", show_alert=True)
                return
            
            file_info = helpers.format_deleted_file_info(file_data)
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("♻️ Restore File", callback_data=f"restore_{file_id}"),
                    InlineKeyboardButton("🗑️ Delete Permanently", callback_data=f"perm_delete_{file_id}")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Recycle Bin", callback_data="deleted_list_0_main")
                ]
            ])
            
            await query.message.reply_text(f"**🗑️ Deleted File Information**\n\n{file_info}", reply_markup=keyboard)
        
        # Soft delete (move to recycle bin)
        elif data.startswith("soft_delete_"):
            file_id = int(data.split("_")[2])
            
            # Check authorization with permission
            if not db.has_permission(user_id, 'delete'):
                await query.answer("You are not authorized to delete files", show_alert=True)
                return
            
            # Move to recycle bin
            deleted = db.soft_delete_file(file_id, user_id, "Deleted via button")
            
            if deleted:
                await query.message.edit_text(
                    f"🗑️ **File `{file_id}` moved to recycle bin!**\n\n"
                    f"The file has been moved to the recycle bin and can be restored later.\n\n"
                    f"Use `/restore {file_id}` or the recycle bin menu to restore it."
                )
                logger.info(f"File {file_id} moved to recycle bin by user {user_id}")
            else:
                await query.answer("Failed to delete file", show_alert=True)
        
        # Restore file
        elif data.startswith("restore_"):
            file_id = int(data.split("_")[1])
            
            # Check authorization with permission
            if not db.has_permission(user_id, 'restore'):
                await query.answer("You are not authorized to restore files", show_alert=True)
                return
            
            # Restore file
            restored = db.restore_file(file_id)
            
            if restored:
                await query.message.edit_text(
                    f"♻️ **File `{file_id}` restored successfully!**\n\n"
                    f"The file has been moved back to the active database.\n\n"
                    f"Use `/info {file_id}` to view the file."
                )
                logger.info(f"File {file_id} restored by user {user_id}")
            else:
                await query.answer("Failed to restore file", show_alert=True)
        
        # Permanent delete
        elif data.startswith("perm_delete_"):
            file_id = int(data.split("_")[2])
            
            # Only owner can permanently delete
            if user_id != Config.OWNER_ID:
                await query.answer("Only the bot owner can permanently delete files", show_alert=True)
                return
            
            # Show confirmation
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⚠️ Yes, Delete Permanently", callback_data=f"confirm_perm_delete_{file_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_perm_delete")
                ]
            ])
            
            await query.message.edit_text(
                f"🚨 **Permanent Deletion Warning!**\n\n"
                f"Are you sure you want to **PERMANENTLY DELETE** file `{file_id}`?\n\n"
                f"**This action cannot be undone!**\n"
                f"The file will be removed from the recycle bin forever.\n\n"
                f"⚠️ **This is irreversible!**",
                reply_markup=keyboard
            )
        
        # Confirm permanent delete
        elif data.startswith("confirm_perm_delete_"):
            file_id = int(data.split("_")[3])
            
            # Only owner can permanently delete
            if user_id != Config.OWNER_ID:
                await query.answer("Unauthorized", show_alert=True)
                return
            
            # Get file info before deleting
            file_data = db.get_deleted_file_by_id(file_id)
            
            # Permanently delete
            deleted = db.permanent_delete_file(file_id)
            
            if deleted:
                await query.message.edit_text(
                    f"💀 **File `{file_id}` permanently deleted!**\n\n"
                    f"The file has been permanently removed from the database.\n\n"
                    f"**Name:** {file_data.get('file_name', 'Unknown') if file_data else 'Unknown'}\n"
                    f"**This action cannot be undone.**"
                )
                logger.info(f"File {file_id} permanently deleted by owner {user_id}")
            else:
                await query.message.edit_text(f"❌ Failed to permanently delete file `{file_id}`")
        
        # Cancel permanent delete
        elif data == "cancel_perm_delete":
            await query.message.edit_text("✅ Permanent deletion cancelled.")
        
        # Cleanup old deleted files
        elif data == "cleanup_deleted":
            # Only owner can cleanup
            if user_id != Config.OWNER_ID:
                await query.answer("Only the bot owner can cleanup old deleted files", show_alert=True)
                return
            
            cleaned_count = db.cleanup_old_deleted()
            
            if cleaned_count > 0:
                await query.message.edit_text(
                    f"🧹 **Cleanup Complete!**\n\n"
                    f"Removed {cleaned_count} old deleted files (older than {Config.RECYCLE_BIN_MAX_DAYS} days).\n\n"
                    f"The recycle bin has been cleaned up."
                )
                logger.info(f"Cleaned up {cleaned_count} old deleted files by owner {user_id}")
            else:
                await query.message.edit_text(
                    "🧹 **No old files to clean up.**\n\n"
                    "All deleted files are within the retention period."
                )
        
        # Search from menu
        elif data == "search_main":
            await query.message.edit_text(
                "🔍 **Search Files**\n\n"
                "Please use the /search command followed by your search query.\n\n"
                "**Example:** `/search project report`\n\n"
                "You can search by file name or description.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                ])
            )
        
        # Stats from menu
        elif data == "stats_main" or data == "stats_refresh":
            await _show_stats(query)
        
        # Upload help
        elif data == "upload_help":
            await query.message.edit_text(
                "📤 **Upload File**\n\n"
                "1. Send a photo/video/audio/document\n"
                "2. Reply to it with:\n"
                "`/upload \"File Name\" \"Description\" Rarity`\n\n"
                "**Example:**\n"
                "`/upload \"Project Report\" \"Q4 Financial Analysis\" 3`\n"
                "`/upload \"Vacation Photos\" \"Summer Album\" 10`\n\n"
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
        
        # Upload example
        elif data == "upload_example":
            await query.message.edit_text(
                "📤 **Upload Example:**\n\n"
                "1. **Send a photo** of a document\n"
                "2. **Reply to it with:**\n"
                "`/upload \"Project Report\" \"Q4 Financial Analysis\" 3`\n\n"
                "**This would create:**\n"
                "• File: Project Report\n"
                "• Description: Q4 Financial Analysis\n"
                "• Rarity: 🔴 Rare",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Try Uploading", callback_data="upload_help")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                ])
            )
        
        # Fill example
        elif data == "fill_example":
            await query.message.edit_text(
                "🔄 **Fill Deleted File Slot Example:**\n\n"
                "1. **Find a deleted file ID** using `/deleted`\n"
                "2. **Send a photo** of a new file\n"
                "3. **Reply to it with:**\n"
                "`/fill 123 \"New Report\" \"Updated Analysis\" 3`\n\n"
                "**This would:**\n"
                "• Reuse deleted slot #123\n"
                "• Create: New Report (Updated Analysis)\n"
                "• Rarity: 🔴 Rare\n\n"
                "**Or use `oldest` to fill the oldest slot:**\n"
                "`/fill oldest \"New File\" \"Description\" 3`\n\n"
                "**Note:** You need 'fill' permission to use this command.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
                    [InlineKeyboardButton("📤 Try Uploading", callback_data="upload_help")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
                ])
            )
        
        # Help from callback
        elif data == "help_main":
            await query.message.edit_text(
                "ℹ️ **File Bot Help**\n\n"
                "**Main Functions:**\n"
                "📤 Upload files with rarity system\n"
                "📚 Browse file database\n"
                "🗑️ Recycle bin system (restore deleted)\n"
                "🔄 Fill deleted file slots\n"
                "🔍 Search for files\n"
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
        
        # Confirm database reset
        elif data == "confirm_reset":
            if user_id != Config.OWNER_ID:
                await query.answer("Only owner can reset database", show_alert=True)
                return
            
            # Check if user has permission to reset
            if not db.has_permission(user_id, 'reset_db'):
                await query.answer("You don't have permission to reset database", show_alert=True)
                return
            
            # Get stats before reset
            total_files_before = db.get_file_count()
            total_deleted_before = db.get_deleted_files_count()
            
            # Reset database
            reset_success = db.reset_database()
            
            if reset_success:
                # Clear warnings
                db.clear_reset_warnings(user_id)
                
                await query.message.edit_text(
                    f"♻️ **DATABASE RESET COMPLETE!**\n\n"
                    f"✅ **All data has been cleared!**\n\n"
                    f"📊 **Before Reset:**\n"
                    f"• Active Files: {total_files_before}\n"
                    f"• Deleted Files: {total_deleted_before}\n"
                    f"• Total: {total_files_before + total_deleted_before}\n\n"
                    f"🆕 **After Reset:**\n"
                    f"• Active Files: 0\n"
                    f"• Deleted Files: 0\n"
                    f"• File ID Counter: 0\n\n"
                    f"✨ **Database is now fresh and empty!**\n"
                    f"You can start uploading new files from ID 1."
                )
                
                logger.info(f"Database reset by owner {user_id}")
            else:
                await query.message.edit_text(
                    "❌ **Database reset failed!**\n\n"
                    "An error occurred while resetting the database."
                )
        
        # Cancel reset
        elif data == "cancel_reset":
            if user_id != Config.OWNER_ID:
                await query.answer("Unauthorized", show_alert=True)
                return
            
            # Clear warnings
            db.clear_reset_warnings(user_id)
            
            await query.message.edit_text(
                "✅ **Database reset cancelled.**\n\n"
                "No changes were made to the database."
            )
        
        # Delete confirmation (old system)
        elif data.startswith("confirm_delete_"):
            file_id = int(data.split("_")[2])
            
            # Only owner can permanently delete (old system)
            if user_id != Config.OWNER_ID:
                await query.answer("Unauthorized", show_alert=True)
                return
            
            # For backward compatibility, use soft delete
            deleted = db.soft_delete_file(file_id, user_id, "Deleted via old delete command")
            
            if deleted:
                await query.message.edit_text(f"🗑️ File `{file_id}` moved to recycle bin!")
                logger.info(f"File {file_id} moved to recycle bin by user {user_id}")
            else:
                await query.message.edit_text(f"❌ Failed to delete file `{file_id}`")
        
        elif data == "cancel_delete":
            await query.message.edit_text("✅ Delete cancelled.")
        
        # Unknown callback
        else:
            await query.answer("Unknown action", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await query.answer("An error occurred", show_alert=True)

# ==================== VIEWING METHODS ====================
async def _show_main_menu(query):
    """Show main menu"""
    total_files = db.get_file_count()
    total_deleted = db.get_deleted_files_count()
    
    menu_text = (
        f"📚 **File Database Menu**\n"
        f"📊 **Active Files:** {total_files}\n"
        f"🗑️ **Deleted Files:** {total_deleted}\n\n"
        "Select a rarity to browse files:"
    )
    
    keyboard = helpers.create_rarity_keyboard("main")
    await query.message.edit_text(menu_text, reply_markup=keyboard)

async def _show_all_files(query, page: int, current_view: str):
    """Show all active files"""
    files, total_count = db.get_all_files_paginated(page)
    
    if not files:
        await query.answer("No files found", show_alert=True)
        return
    
    total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
    
    message_text = helpers.format_file_list(
        files, page, total_count, 
        "All Active Files"
    )
    
    keyboard = helpers.create_pagination_keyboard(page, total_pages, "all", current_view)
    
    buttons = []
    for file in files[:3]:
        file_id = file.get('file_id')
        if file_id:
            buttons.append([
                InlineKeyboardButton(
                    f"👁️ {file.get('file_name', 'Unknown')[:15]}...",
                    callback_data=f"info_{file_id}"
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
    
    await query.message.edit_text(message_text, reply_markup=keyboard)

async def _show_deleted_files(query, page: int, current_view: str):
    """Show deleted files (recycle bin)"""
    files, total_count = db.get_deleted_files(page)
    
    if not files:
        await query.answer("Recycle bin is empty", show_alert=True)
        return
    
    total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
    
    message_text = helpers.format_deleted_file_list(files, page, total_count)
    
    keyboard = helpers.create_pagination_keyboard(page, total_pages, "deleted_list", current_view)
    
    buttons = []
    for file in files[:3]:
        file_id = file.get('file_id')
        if file_id:
            buttons.append([
                InlineKeyboardButton(
                    f"♻️ Restore {file.get('file_name', 'Unknown')[:10]}...",
                    callback_data=f"restore_{file_id}"
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    f"👁️ View {file.get('file_name', 'Unknown')[:10]}...",
                    callback_data=f"deleted_info_{file_id}"
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
    
    await query.message.edit_text(message_text, reply_markup=keyboard)

async def _show_search_results(query, search_query: str, page: int):
    """Show search results"""
    files, total_count = db.search_files_paginated(search_query, page)
    
    if not files:
        await query.answer("No more results", show_alert=True)
        return
    
    total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
    
    message_text = helpers.format_file_list(
        files, page, total_count, 
        f"Search Results for: '{search_query}'"
    )
    
    keyboard = helpers.create_pagination_keyboard(page, total_pages, "search", search_query)
    
    buttons = []
    for file in files[:3]:
        file_id = file.get('file_id')
        if file_id:
            buttons.append([
                InlineKeyboardButton(
                    f"👁️ {file.get('file_name', 'Unknown')[:15]}...",
                    callback_data=f"info_{file_id}"
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
    
    await query.message.edit_text(message_text, reply_markup=keyboard)

async def _show_file_info(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: int):
    """Show file information"""
    # First check active files
    file_data = db.get_file_by_id(file_id)
    is_deleted = False
    
    # If not found in active, check deleted
    if not file_data:
        file_data = db.get_deleted_file_by_id(file_id)
        is_deleted = True
    
    if not file_data:
        await update.message.reply_text(f"❌ File with ID `{file_id}` not found!")
        return
    
    # Format file info
    if is_deleted:
        file_info = helpers.format_deleted_file_info(file_data)
        title = "🗑️ Deleted File Information"
    else:
        file_info = helpers.format_file_info(file_data)
        title = "File Information"
    
    # Create keyboard based on status
    if is_deleted:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("♻️ Restore File", callback_data=f"restore_{file_id}"),
                InlineKeyboardButton("🗑️ Delete Permanently", callback_data=f"perm_delete_{file_id}")
            ],
            [
                InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
            ]
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ Move to Recycle Bin", callback_data=f"soft_delete_{file_id}")
            ],
            [
                InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
            ]
        ])
    
    await update.message.reply_text(f"**{title}**\n\n{file_info}", reply_markup=keyboard)

async def _show_file_info_callback(query, context: ContextTypes.DEFAULT_TYPE, file_id: int):
    """Show file information from callback"""
    # First check active files
    file_data = db.get_file_by_id(file_id)
    is_deleted = False
    
    # If not found in active, check deleted
    if not file_data:
        file_data = db.get_deleted_file_by_id(file_id)
        is_deleted = True
    
    if not file_data:
        await query.answer(f"File with ID {file_id} not found", show_alert=True)
        return
    
    # Format file info
    if is_deleted:
        file_info = helpers.format_deleted_file_info(file_data)
        title = "🗑️ Deleted File Information"
    else:
        file_info = helpers.format_file_info(file_data)
        title = "File Information"
    
    # Create keyboard based on status
    if is_deleted:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("♻️ Restore File", callback_data=f"restore_{file_id}"),
                InlineKeyboardButton("🗑️ Delete Permanently", callback_data=f"perm_delete_{file_id}")
            ],
            [
                InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
            ]
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ Move to Recycle Bin", callback_data=f"soft_delete_{file_id}")
            ],
            [
                InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")
            ]
        ])
    
    await query.message.reply_text(f"**{title}**\n\n{file_info}", reply_markup=keyboard)

async def _show_stats(query):
    """Show database statistics"""
    # Get various stats
    total_files = db.get_file_count()
    total_deleted = db.get_deleted_files_count()
    rarity_stats = db.get_rarity_stats()
    top_uploaders = db.get_top_uploaders(10)
    
    # Clean up old deleted files
    cleaned_count = db.cleanup_old_deleted()
    
    # Format stats message
    stats_text = f"📈 **Database Statistics**\n\n"
    stats_text += f"📊 **Active Files:** {total_files}\n"
    stats_text += f"🗑️ **Deleted Files:** {total_deleted}\n"
    if cleaned_count > 0:
        stats_text += f"🧹 **Recently Cleaned:** {cleaned_count} (older than {Config.RECYCLE_BIN_MAX_DAYS} days)\n"
    stats_text += f"📈 **Total (All Time):** {total_files + total_deleted}\n\n"
    
    stats_text += "**Files by Rarity:**\n"
    for rarity_num, rarity_name in Config.RARITY_MAP.items():
        count = rarity_stats.get(rarity_name, 0)
        percentage = (count / total_files * 100) if total_files > 0 else 0
        emoji = helpers.get_rarity_emoji(rarity_name)
        stats_text += f"{emoji} **{rarity_name.split(' ', 1)[-1]}:** {count} ({percentage:.1f}%)\n"
    
    stats_text += f"\n**Top Uploaders:**\n"
    for i, uploader in enumerate(top_uploaders, 1):
        user_id = uploader["_id"]
        count = uploader["count"]
        
        # Try to get username from database
        user_data = db.users.find_one({"user_id": user_id})
        username = user_data.get('username', f"User {user_id}") if user_data else f"User {user_id}"
        
        stats_text += f"{i}. {username}: {count} files\n"
    
    # Add keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")],
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="stats_refresh")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
    ])
    
    await query.message.edit_text(stats_text, reply_markup=keyboard)

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    
    # Notify user
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later.\n"
                "If the problem persists, contact support."
            )
        except:
            pass

# ==================== BACKGROUND TASKS ====================
async def daily_cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Daily cleanup task"""
    logger.info("Running daily cleanup...")
    
    # Clean up old deleted files
    cleaned_count = db.cleanup_old_deleted()
    if cleaned_count > 0:
        logger.info(f"Cleaned up {cleaned_count} old deleted files")
    
    logger.info("Daily cleanup completed.")

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    if not Config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable is required!")
        exit(1)
    
    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("myuploads", myuploads_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("restore", restore_command))
    application.add_handler(CommandHandler("deleted", deleted_command))
    application.add_handler(CommandHandler("fill", fill_command))
    application.add_handler(CommandHandler("addsudo", addsudo_command))
    application.add_handler(CommandHandler("removesudo", removesudo_command))
    application.add_handler(CommandHandler("sudolist", sudolist_command))
    application.add_handler(CommandHandler("reset", reset_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(handle_callbacks))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Add job queue for background tasks
    job_queue = application.job_queue
    if job_queue:
        # Daily cleanup at 3 AM
        job_queue.run_daily(daily_cleanup, time=datetime.time(hour=3, minute=0))
    
    # Start the bot
    logger.info("🤖 Bot is starting...")
    print("=" * 50)
    print("     COMPLETE UPLOAD BOT")
    print("     with ALL FEATURES")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
