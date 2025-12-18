#!/usr/bin/env python3
"""
Advanced Telegram Upload Bot with MongoDB
Features: Multi-user support, advanced search, file management, admin panel, statistics, and more.
"""

import os
import logging
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
from io import BytesIO
from functools import wraps
import mimetypes

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from pymongo.collection import Collection
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    InputFile,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAudio,
    Chat,
    User
)
from telegram.constants import ChatAction, ChatType
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackContext
)
from telegram.error import BadRequest, NetworkError, RetryAfter
import aiohttp
from PIL import Image
import magic

# ==================== LOAD ENVIRONMENT ====================
load_dotenv()

# ==================== CONFIGURATION ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "upload_bot")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 200 * 1024 * 1024))  # 200MB
    ALLOWED_TYPES = json.loads(os.getenv("ALLOWED_TYPES", '["document", "photo", "video", "audio"]'))
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(','))) if os.getenv("ADMIN_IDS") else []
    CHANNEL_ID = os.getenv("CHANNEL_ID", "")
    LOG_CHAT_ID = os.getenv("LOG_CHAT_ID", "")
    API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", 30))
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", 300))
    BACKUP_INTERVAL = int(os.getenv("BACKUP_INTERVAL", 3600))
    THUMBNAIL_SIZE = tuple(map(int, os.getenv("THUMBNAIL_SIZE", "320,240").split(',')))

# ==================== ENUMS ====================
class FileType(Enum):
    DOCUMENT = "document"
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"
    STICKER = "sticker"
    ANIMATION = "animation"

class PrivacyLevel(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PROTECTED = "protected"

class UploadStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"

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

# ==================== DATABASE MODELS ====================
class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        try:
            # Sync client for operations that don't need async
            self.sync_client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.sync_client.server_info()
            
            # Async client for async operations
            self.async_client = AsyncIOMotorClient(Config.MONGODB_URI)
            
            self.db = self.sync_client[Config.DATABASE_NAME]
            self.async_db = self.async_client[Config.DATABASE_NAME]
            
            # Collections
            self.files = self.db.files
            self.users = self.db.users
            self.stats = self.db.stats
            self.sessions = self.db.sessions
            self.analytics = self.db.analytics
            self.backups = self.db.backups
            
            # Create indexes
            self._create_indexes()
            logger.info("✅ Database initialized successfully")
            
        except ConnectionFailure as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        # Files collection indexes
        self.files.create_index([("file_id", 1)], unique=True, sparse=True)
        self.files.create_index([("user_id", 1)])
        self.files.create_index([("upload_date", DESCENDING)])
        self.files.create_index([("tags", 1)])
        self.files.create_index([("file_type", 1)])
        self.files.create_index([("privacy", 1)])
        self.files.create_index([("hash_md5", 1)])
        self.files.create_index([("size", DESCENDING)])
        self.files.create_index([("views", DESCENDING)])
        self.files.create_index([("downloads", DESCENDING)])
        
        # Users collection indexes
        self.users.create_index([("user_id", 1)], unique=True)
        self.users.create_index([("username", 1)], sparse=True)
        self.users.create_index([("is_premium", 1)])
        self.users.create_index([("storage_used", DESCENDING)])
        
        # Analytics indexes
        self.analytics.create_index([("date", DESCENDING)])
        self.analytics.create_index([("user_id", 1)])
        
        # Sessions indexes
        self.sessions.create_index([("expires_at", 1)], expireAfterSeconds=0)
        
        logger.info("✅ Database indexes created")
    
    def get_async_collection(self, collection_name: str):
        """Get async collection"""
        return self.async_db[collection_name]

# Initialize database
db = Database()

# ==================== CACHE SYSTEM ====================
class Cache:
    def __init__(self):
        self._cache = {}
        self._ttl = {}
    
    def set(self, key: str, value, ttl: int = 300):
        """Set cache with TTL"""
        self._cache[key] = value
        self._ttl[key] = datetime.now() + timedelta(seconds=ttl)
    
    def get(self, key: str):
        """Get cached value"""
        if key in self._cache:
            if datetime.now() < self._ttl.get(key, datetime.now()):
                return self._cache[key]
            else:
                del self._cache[key]
                del self._ttl[key]
        return None
    
    def delete(self, key: str):
        """Delete from cache"""
        if key in self._cache:
            del self._cache[key]
        if key in self._ttl:
            del self._ttl[key]
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self._ttl.clear()

cache = Cache()

# ==================== DECORATORS ====================
def admin_only(func):
    """Decorator to restrict access to admins only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ This command is for administrators only.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def premium_only(func):
    """Decorator for premium users only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        user_data = db.users.find_one({"user_id": user_id})
        if not user_data or not user_data.get("is_premium", False):
            await update.message.reply_text(
                "⭐ This feature requires Premium subscription.\n"
                "Use /premium to learn more."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def rate_limit(limit: int = 5, per: int = 60):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            key = f"rate_limit:{user_id}:{func.__name__}"
            current = cache.get(key) or 0
            
            if current >= limit:
                await update.message.reply_text(
                    "⏳ Too many requests. Please wait a moment before trying again."
                )
                return
            
            cache.set(key, current + 1, per)
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

# ==================== HELPER FUNCTIONS ====================
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

def format_duration(seconds: int) -> str:
    """Format seconds to HH:MM:SS"""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def extract_metadata(file_obj, file_type: FileType) -> Dict:
    """Extract metadata from Telegram file object"""
    metadata = {
        "file_type": file_type.value,
        "mime_type": getattr(file_obj, 'mime_type', ''),
        "size": file_obj.file_size,
        "file_name": getattr(file_obj, 'file_name', ''),
        "duration": getattr(file_obj, 'duration', 0),
        "width": getattr(file_obj, 'width', 0),
        "height": getattr(file_obj, 'height', 0),
        "title": getattr(file_obj, 'title', ''),
        "performer": getattr(file_obj, 'performer', ''),
        "thumbnail": getattr(file_obj, 'thumbnail', None),
    }
    return {k: v for k, v in metadata.items() if v}

def parse_tags(text: str) -> List[str]:
    """Parse hashtags from text"""
    import re
    tags = re.findall(r'#(\w+)', text)
    return [tag.lower() for tag in tags]

def calculate_hash(file_data: bytes) -> Dict:
    """Calculate file hashes"""
    return {
        "md5": hashlib.md5(file_data).hexdigest(),
        "sha1": hashlib.sha1(file_data).hexdigest(),
        "sha256": hashlib.sha256(file_data).hexdigest(),
    }

def generate_thumbnail(image_data: bytes) -> Optional[bytes]:
    """Generate thumbnail from image"""
    try:
        img = Image.open(BytesIO(image_data))
        img.thumbnail(Config.THUMBNAIL_SIZE)
        thumb_io = BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)
        return thumb_io.getvalue()
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}")
        return None

def get_file_type_from_mime(mime_type: str) -> FileType:
    """Determine file type from MIME type"""
    if mime_type.startswith('image/'):
        return FileType.PHOTO
    elif mime_type.startswith('video/'):
        return FileType.VIDEO
    elif mime_type.startswith('audio/'):
        return FileType.AUDIO
    else:
        return FileType.DOCUMENT

# ==================== USER MANAGEMENT ====================
async def ensure_user(user: User):
    """Ensure user exists in database"""
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,
        "is_bot": user.is_bot,
        "is_premium": getattr(user, 'is_premium', False),
        "storage_used": 0,
        "storage_limit": 10 * 1024 * 1024 * 1024,  # 10GB default
        "max_file_size": 50 * 1024 * 1024,  # 50MB default
        "daily_upload_limit": 100,
        "uploads_today": 0,
        "total_uploads": 0,
        "total_downloads": 0,
        "join_date": datetime.now(),
        "last_seen": datetime.now(),
        "settings": {
            "privacy_default": "public",
            "auto_delete_days": 0,
            "notify_on_download": True,
            "compress_images": False,
            "watermark_enabled": False,
        }
    }
    
    db.users.update_one(
        {"user_id": user.id},
        {"$setOnInsert": user_data, "$set": {"last_seen": datetime.now()}},
        upsert=True
    )
    
    # Update analytics
    db.analytics.update_one(
        {"date": datetime.now().date(), "user_id": user.id},
        {"$inc": {"visits": 1}},
        upsert=True
    )
    
    return user_data

# ==================== COMMAND HANDLERS ====================
@rate_limit(limit=3, per=60)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with user registration"""
    user = update.effective_user
    await ensure_user(user)
    
    welcome_text = """
🌟 *Welcome to Advanced Upload Bot* 🌟

I'm your powerful file management assistant with these features:

📤 *Upload Features:*
• Multiple file types (documents, photos, videos, audio)
• Batch upload support
• Automatic metadata extraction
• Custom tags and descriptions
• Privacy settings (public/private/unlisted)

🔍 *Search & Discovery:*
• Advanced search by tags, type, date
• Full-text search in descriptions
• Similar files recommendation
• Trending files

📊 *Management:*
• File statistics and analytics
• Storage usage monitoring
• File organization with folders
• Duplicate detection

⚡ *Premium Features:*
• Increased storage (up to 100GB)
• Larger file uploads (up to 2GB)
• No ads
• Priority support
• Advanced search filters

*Quick Commands:*
/upload - Upload files
/myfiles - View your files
/search - Search files
/folders - Manage folders
/stats - Your statistics
/help - Detailed help
/premium - Premium features

*Need help?* Use /help for detailed instructions.
    """
    
    keyboard = [
        [InlineKeyboardButton("📤 Upload File", callback_data="upload_start")],
        [InlineKeyboardButton("📁 My Files", callback_data="my_files")],
        [InlineKeyboardButton("🔍 Search", callback_data="search_start")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
    ]
    
    if user.id in Config.ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detailed help command"""
    help_text = """
📚 *Complete Bot Guide*

*Basic Commands:*
/start - Start the bot
/help - This help message
/upload - Upload files (or just send them)
/myfiles - List your uploaded files
/search <query> - Search files
/delete <file_id> - Delete a file
/info <file_id> - Get file info

*Advanced Commands:*
/folders - Manage file folders
/tags - Manage tags
/duplicates - Find duplicate files
/stats - View your statistics
/settings - Configure bot settings
/backup - Backup your files
/restore - Restore from backup

*Admin Commands:*
/admin - Admin panel
/broadcast - Send message to all users
/stats_all - Global statistics
/cleanup - Clean up old files
/ban <user_id> - Ban user
/unban <user_id> - Unban user

*Upload Instructions:*
1. Send any file (document, photo, video, audio)
2. Add caption with tags (e.g., #work #important)
3. Set privacy: Add !private, !unlisted, or !public
4. Add description after tags

*Examples:*
• Send a photo with caption: "#vacation !private Beach sunset"
• Search: /search #vacation type:photo
• Create folder: /folders create vacation_photos

*Privacy Levels:*
• Public: Anyone can view
• Private: Only you can view
• Unlisted: Anyone with link can view
• Protected: Password protected

Need more help? Contact support.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

@rate_limit(limit=5, per=60)
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiate upload process"""
    user = update.effective_user
    await ensure_user(user)
    
    # Check storage limit
    user_data = db.users.find_one({"user_id": user.id})
    if user_data["storage_used"] >= user_data["storage_limit"]:
        await update.message.reply_text(
            "❌ Storage limit reached!\n"
            "Please delete some files or upgrade to premium."
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("📄 Document", callback_data="upload_type:document"),
         InlineKeyboardButton("🖼️ Photo", callback_data="upload_type:photo")],
        [InlineKeyboardButton("🎥 Video", callback_data="upload_type:video"),
         InlineKeyboardButton("🎵 Audio", callback_data="upload_type:audio")],
        [InlineKeyboardButton("🎤 Voice", callback_data="upload_type:voice"),
         InlineKeyboardButton("📹 Video Note", callback_data="upload_type:video_note")],
        [InlineKeyboardButton("📦 Batch Upload", callback_data="upload_batch")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📤 *Select upload type:*\n\n"
        "You can also just send me any file directly.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def my_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List user's files with pagination"""
    user = update.effective_user
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 1
    per_page = 10
    
    # Get files
    skip = (page - 1) * per_page
    files = list(db.files.find(
        {"user_id": user.id, "status": "completed"}
    ).sort("upload_date", DESCENDING).skip(skip).limit(per_page))
    
    if not files:
        await update.message.reply_text("📭 You haven't uploaded any files yet.")
        return
    
    # Calculate statistics
    total_files = db.files.count_documents({"user_id": user.id, "status": "completed"})
    total_pages = (total_files + per_page - 1) // per_page
    
    # Build response
    response = f"📁 *Your Files* (Page {page}/{total_pages})\n\n"
    
    for idx, file in enumerate(files, 1):
        file_date = file['upload_date'].strftime("%Y-%m-%d")
        file_size = format_size(file['size'])
        file_type_emoji = {
            'document': '📄',
            'photo': '🖼️',
            'video': '🎥',
            'audio': '🎵',
            'voice': '🎤',
            'video_note': '📹'
        }.get(file['file_type'], '📁')
        
        response += (
            f"*{idx + skip}.* {file_type_emoji} `{file['file_name']}`\n"
            f"   📏 {file_size} | 📅 {file_date} | 👁️ {file.get('views', 0)}\n"
            f"   🔗 ID: `{file['_id']}`\n"
            f"   🏷️ {', '.join(file.get('tags', ['No tags']))[:30]}\n\n"
        )
    
    # Add navigation buttons
    keyboard = []
    if page > 1:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"myfiles:{page-1}"))
    if page < total_pages:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"myfiles:{page+1}"))
    
    if keyboard:
        reply_markup = InlineKeyboardMarkup([keyboard])
    else:
        reply_markup = None
    
    await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)

@rate_limit(limit=10, per=60)
async def search_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Advanced file search"""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Search Usage:*\n\n"
            "• `/search #tag1 #tag2` - Search by tags\n"
            "• `/search type:photo` - Search by file type\n"
            "• `/search size>10MB` - Search by size\n"
            "• `/search date>2024-01-01` - Search by date\n"
            "• `/search \"exact phrase\"` - Full-text search\n"
            "• Combine: `/search #work type:document size<1MB`",
            parse_mode='Markdown'
        )
        return
    
    query = ' '.join(context.args)
    user = update.effective_user
    
    # Parse search query
    search_criteria = parse_search_query(query)
    
    # Build MongoDB query
    mongo_query = build_mongo_search_query(search_criteria, user.id)
    
    # Execute search
    files = list(db.files.find(mongo_query).limit(20))
    
    if not files:
        await update.message.reply_text("🔍 No files found matching your criteria.")
        return
    
    # Display results
    response = f"🔍 *Search Results* ({len(files)} files)\n\n"
    
    for idx, file in enumerate(files, 1):
        privacy_icon = {
            'public': '🌐',
            'private': '🔒',
            'unlisted': '🔗'
        }.get(file.get('privacy', 'public'), '❓')
        
        response += (
            f"*{idx}.* {privacy_icon} `{file['file_name']}`\n"
            f"   📏 {format_size(file['size'])} | 👤 {file.get('username', 'Unknown')}\n"
            f"   🔗 ID: `{file['_id']}`\n\n"
        )
    
    keyboard = []
    for file in files[:5]:
        keyboard.append([InlineKeyboardButton(
            f"📄 {file['file_name'][:20]}",
            callback_data=f"file_info:{file['_id']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)

def parse_search_query(query: str) -> Dict:
    """Parse advanced search query"""
    criteria = {
        'tags': [],
        'text': [],
        'filters': {}
    }
    
    # Split by space but keep quoted strings together
    import shlex
    parts = shlex.split(query)
    
    for part in parts:
        if part.startswith('#'):
            criteria['tags'].append(part[1:].lower())
        elif ':' in part:
            key, value = part.split(':', 1)
            criteria['filters'][key.lower()] = value.lower()
        elif part.startswith('size'):
            # Parse size filter (size>10MB, size<1GB)
            criteria['filters']['size'] = part
        elif part.startswith('date'):
            # Parse date filter
            criteria['filters']['date'] = part
        else:
            criteria['text'].append(part)
    
    return criteria

def build_mongo_search_query(criteria: Dict, user_id: int) -> Dict:
    """Build MongoDB query from search criteria"""
    query_parts = []
    
    # Privacy filter - user can see their own private files and public/unlisted files
    privacy_filter = {
        "$or": [
            {"privacy": "public"},
            {"privacy": "unlisted"},
            {"user_id": user_id}
        ]
    }
    query_parts.append(privacy_filter)
    
    # Tags filter
    if criteria['tags']:
        query_parts.append({"tags": {"$all": criteria['tags']}})
    
    # Text search
    if criteria['text']:
        query_parts.append({
            "$or": [
                {"file_name": {"$regex": ' '.join(criteria['text']), "$options": "i"}},
                {"description": {"$regex": ' '.join(criteria['text']), "$options": "i"}},
                {"tags": {"$in": criteria['text']}}
            ]
        })
    
    # Apply filters
    for key, value in criteria['filters'].items():
        if key == 'type':
            query_parts.append({"file_type": value})
        elif key == 'size':
            # Parse size filter (size>10MB, size<1GB)
            import re
            match = re.match(r'size([<>]=?)(\d+)(MB|GB|KB)', value, re.IGNORECASE)
            if match:
                operator, amount, unit = match.groups()
                multiplier = {
                    'KB': 1024,
                    'MB': 1024 * 1024,
                    'GB': 1024 * 1024 * 1024
                }[unit.upper()]
                size_bytes = int(amount) * multiplier
                
                mongo_operator = {
                    '>': '$gt',
                    '>=': '$gte',
                    '<': '$lt',
                    '<=': '$lte'
                }.get(operator, '$eq')
                
                query_parts.append({"size": {mongo_operator: size_bytes}})
    
    # Combine all parts with AND
    if len(query_parts) == 1:
        return query_parts[0]
    elif query_parts:
        return {"$and": query_parts}
    else:
        return {}

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user = update.effective_user
    user_data = db.users.find_one({"user_id": user.id})
    
    if not user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    # Calculate statistics
    total_files = db.files.count_documents({"user_id": user.id, "status": "completed"})
    total_size = db.files.aggregate([
        {"$match": {"user_id": user.id, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$size"}}}
    ])
    total_size_result = next(total_size, {"total": 0})
    
    # Recent activity
    last_week = datetime.now() - timedelta(days=7)
    recent_uploads = db.files.count_documents({
        "user_id": user.id,
        "upload_date": {"$gte": last_week}
    })
    
    # Popular tags
    tag_pipeline = [
        {"$match": {"user_id": user.id}},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": DESCENDING}},
        {"$limit": 5}
    ]
    popular_tags = list(db.files.aggregate(tag_pipeline))
    
    stats_text = f"""
📊 *Your Statistics*

👤 *User Info:*
• Username: @{user.username or 'N/A'}
• User ID: `{user.id}`
• Premium: {'⭐ Yes' if user_data.get('is_premium') else 'No'}
• Joined: {user_data['join_date'].strftime('%Y-%m-%d')}

📁 *Storage:*
• Used: {format_size(user_data['storage_used'])}
• Limit: {format_size(user_data['storage_limit'])}
• Available: {format_size(user_data['storage_limit'] - user_data['storage_used'])}
• Usage: {(user_data['storage_used'] / user_data['storage_limit'] * 100):.1f}%

📈 *Activity:*
• Total Files: {total_files}
• Total Size: {format_size(total_size_result['total'])}
• Recent (7 days): {recent_uploads} files
• Today's Uploads: {user_data.get('uploads_today', 0)}

🏷️ *Popular Tags:*
{chr(10).join(f'• #{tag["_id"]}: {tag["count"]} files' for tag in popular_tags) or '• No tags yet'}

🎯 *Limits:*
• Max File Size: {format_size(user_data['max_file_size'])}
• Daily Uploads: {user_data.get('uploads_today', 0)}/{user_data['daily_upload_limit']}
    """
    
    keyboard = [
        [InlineKeyboardButton("📈 Detailed Analytics", callback_data="analytics")],
        [InlineKeyboardButton("⚙️ Storage Settings", callback_data="storage_settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
         InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("📁 Files", callback_data="admin_files"),
         InlineKeyboardButton("🔍 Search", callback_data="admin_search")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🧹 Cleanup", callback_data="admin_cleanup"),
         InlineKeyboardButton("📝 Logs", callback_data="admin_logs")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👑 *Admin Panel*\n\n"
        "Select an option below:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def file_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get detailed file information"""
    if not context.args:
        await update.message.reply_text("Usage: /info <file_id>")
        return
    
    file_id = context.args[0]
    user = update.effective_user
    
    try:
        file_data = db.files.find_one({"_id": ObjectId(file_id)})
    except InvalidId:
        await update.message.reply_text("❌ Invalid file ID format.")
        return
    
    if not file_data:
        await update.message.reply_text("❌ File not found.")
        return
    
    # Check permissions
    if file_data.get('privacy') == 'private' and file_data['user_id'] != user.id:
        await update.message.reply_text("⛔ You don't have permission to view this file.")
        return
    
    # Format file info
    info_text = f"""
📄 *File Information*

📛 *Name:* `{file_data['file_name']}`
🆔 *ID:* `{file_data['_id']}`
📁 *Type:* {file_data['file_type']}
📏 *Size:* {format_size(file_data['size'])}
📅 *Uploaded:* {file_data['upload_date'].strftime('%Y-%m-%d %H:%M:%S')}
👤 *Uploader:* @{file_data.get('username', 'Unknown')}
🔒 *Privacy:* {file_data.get('privacy', 'public')}
🏷️ *Tags:* {', '.join(file_data.get('tags', [])) or 'None'}

📊 *Statistics:*
👁️ Views: {file_data.get('views', 0)}
📥 Downloads: {file_data.get('downloads', 0)}
⭐ Favorites: {file_data.get('favorites', 0)}

🔗 *Telegram File IDs:*
• File ID: `{file_data['file_id']}`
• Unique ID: `{file_data.get('file_unique_id', 'N/A')}`
• MIME Type: {file_data.get('mime_type', 'N/A')}

📝 *Description:*
{file_data.get('description', 'No description')}
    """
    
    keyboard = []
    
    # Action buttons
    actions = [
        ("📥 Download", f"download:{file_data['_id']}"),
        ("📋 Copy Info", f"copy_info:{file_data['_id']}"),
        ("✏️ Edit", f"edit_file:{file_data['_id']}")
    ]
    
    if user.id == file_data['user_id'] or user.id in Config.ADMIN_IDS:
        actions.append(("🗑️ Delete", f"delete_confirm:{file_data['_id']}"))
    
    for i in range(0, len(actions), 2):
        row = actions[i:i+2]
        keyboard.append([InlineKeyboardButton(text, callback_data=data) for text, data in row])
    
    # Additional buttons
    if file_data.get('thumbnail'):
        keyboard.append([InlineKeyboardButton("🖼️ View Thumbnail", callback_data=f"thumbnail:{file_data['_id']}")])
    
    keyboard.append([InlineKeyboardButton("🔗 Share Link", callback_data=f"share:{file_data['_id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(info_text, parse_mode='Markdown', reply_markup=reply_markup)

# ==================== FILE UPLOAD HANDLER ====================
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming files"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Send typing action
    await update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    
    # Ensure user exists
    user_data = await ensure_user(user)
    
    # Check daily upload limit
    if user_data.get('uploads_today', 0) >= user_data.get('daily_upload_limit', 100):
        await update.message.reply_text(
            "⚠️ Daily upload limit reached!\n"
            "Try again tomorrow or upgrade to premium."
        )
        return
    
    # Get file object based on type
    file_obj, file_type, media_group_id = await get_file_object(update)
    
    if not file_obj:
        await update.message.reply_text("❌ Unsupported file type.")
        return
    
    # Check file size limit
    if file_obj.file_size > user_data.get('max_file_size', 50 * 1024 * 1024):
        await update.message.reply_text(
            f"❌ File too large! Max size: {format_size(user_data['max_file_size'])}\n"
            "Upgrade to premium for larger uploads."
        )
        return
    
    if file_obj.file_size > Config.MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ File exceeds bot limit of {format_size(Config.MAX_FILE_SIZE)}."
        )
        return
    
    # Parse caption for metadata
    caption = update.message.caption or ""
    tags = parse_tags(caption)
    description = caption.strip()
    
    # Remove tags from description
    for tag in tags:
        description = description.replace(f"#{tag}", "").strip()
    
    # Parse privacy settings
    privacy = "public"
    if "!private" in description.lower():
        privacy = "private"
        description = description.replace("!private", "").strip()
    elif "!unlisted" in description.lower():
        privacy = "unlisted"
        description = description.replace("!unlisted", "").strip()
    elif "!public" in description.lower():
        description = description.replace("!public", "").strip()
    
    try:
        # Prepare file metadata
        file_metadata = {
            "file_id": file_obj.file_id,
            "file_unique_id": file_obj.file_unique_id,
            "file_name": getattr(file_obj, 'file_name', f"{file_type.value}_{file_obj.file_id}"),
            "file_type": file_type.value,
            "size": file_obj.file_size,
            "user_id": user.id,
            "username": user.username or user.first_name,
            "chat_id": chat.id,
            "upload_date": datetime.now(),
            "caption": caption,
            "description": description,
            "tags": tags,
            "privacy": privacy,
            "status": "completed",
            "views": 0,
            "downloads": 0,
            "favorites": 0,
            "media_group_id": media_group_id,
            "hashes": {},
            "metadata": extract_metadata(file_obj, file_type),
            "settings": {
                "auto_delete_days": 0,
                "password_protected": False,
                "watermark": False,
                "compressed": False
            }
        }
        
        # For media groups, check if this is first in group
        if media_group_id:
            existing = db.files.find_one({"media_group_id": media_group_id})
            if existing:
                # Add to existing group
                db.files.update_one(
                    {"_id": existing["_id"]},
                    {"$push": {"group_files": file_metadata}}
                )
                await update.message.reply_text(f"✅ Added to media group ({existing['file_name']})")
                return
        
        # Save to database
        result = db.files.insert_one(file_metadata)
        
        # Update user statistics
        db.users.update_one(
            {"user_id": user.id},
            {
                "$inc": {
                    "storage_used": file_obj.file_size,
                    "uploads_today": 1,
                    "total_uploads": 1
                }
            }
        )
        
        # Update analytics
        db.analytics.update_one(
            {"date": datetime.now().date()},
            {
                "$inc": {
                    "uploads": 1,
                    "total_size": file_obj.file_size,
                    f"uploads_{file_type.value}": 1
                }
            },
            upsert=True
        )
        
        # Send confirmation
        keyboard = [
            [InlineKeyboardButton("📄 View Details", callback_data=f"file_info:{result.inserted_id}"),
             InlineKeyboardButton("🔗 Share", callback_data=f"share:{result.inserted_id}")],
            [InlineKeyboardButton("📁 Add to Folder", callback_data=f"add_to_folder:{result.inserted_id}"),
             InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{result.inserted_id}")]
        ]
        
        if privacy != "private":
            keyboard.append([InlineKeyboardButton("🌐 Public Link", callback_data=f"public_link:{result.inserted_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"✅ *File Uploaded Successfully!*\n\n"
            f"📛 *Name:* `{file_metadata['file_name']}`\n"
            f"📁 *Type:* {file_metadata['file_type']}\n"
            f"📏 *Size:* {format_size(file_metadata['size'])}\n"
            f"🔒 *Privacy:* {privacy}\n"
            f"🏷️ *Tags:* {', '.join(tags) if tags else 'None'}\n"
            f"🆔 *ID:* `{result.inserted_id}`\n\n"
            f"Use /info `{result.inserted_id}` for details."
        )
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Log to admin channel if configured
        if Config.LOG_CHAT_ID and user.id not in Config.ADMIN_IDS:
            log_message = (
                f"📥 New Upload\n"
                f"👤 User: @{user.username} ({user.id})\n"
                f"📁 File: {file_metadata['file_name']}\n"
                f"📏 Size: {format_size(file_metadata['size'])}\n"
                f"🆔 ID: {result.inserted_id}"
            )
            try:
                await context.bot.send_message(Config.LOG_CHAT_ID, log_message)
            except:
                pass
        
    except DuplicateKeyError:
        await update.message.reply_text("⚠️ This file has already been uploaded.")
    except Exception as e:
        logger.error(f"Error saving file: {e}", exc_info=True)
        await update.message.reply_text("❌ Failed to save file. Please try again.")

async def get_file_object(update: Update) -> Tuple[Optional[object], Optional[FileType], Optional[str]]:
    """Extract file object from update"""
    media_group_id = getattr(update.message, 'media_group_id', None)
    
    if update.message.document:
        return update.message.document, FileType.DOCUMENT, media_group_id
    elif update.message.photo:
        return update.message.photo[-1], FileType.PHOTO, media_group_id
    elif update.message.video:
        return update.message.video, FileType.VIDEO, media_group_id
    elif update.message.audio:
        return update.message.audio, FileType.AUDIO, media_group_id
    elif update.message.voice:
        return update.message.voice, FileType.VOICE, media_group_id
    elif update.message.video_note:
        return update.message.video_note, FileType.VIDEO_NOTE, media_group_id
    elif update.message.sticker:
        return update.message.sticker, FileType.STICKER, media_group_id
    elif update.message.animation:
        return update.message.animation, FileType.ANIMATION, media_group_id
    
    return None, None, media_group_id

# ==================== CALLBACK QUERY HANDLER ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("file_info:"):
        file_id = data.split(":")[1]
        # Simulate /info command
        context.args = [file_id]
        await file_info(update, context)
        
    elif data.startswith("download:"):
        file_id = data.split(":")[1]
        await download_file(update, context, file_id)
        
    elif data.startswith("delete_confirm:"):
        file_id = data.split(":")[1]
        await confirm_delete(update, context, file_id)
        
    elif data.startswith("share:"):
        file_id = data.split(":")[1]
        await share_file(update, context, file_id)
        
    elif data == "admin_panel":
        await admin_panel(update, context)
        
    elif data == "upload_start":
        await upload_command(update, context)
        
    elif data == "my_files":
        await my_files(update, context)
        
    elif data.startswith("myfiles:"):
        page = int(data.split(":")[1])
        context.args = [str(page)]
        await my_files(update, context)
        
    elif data == "search_start":
        await update.callback_query.message.reply_text(
            "🔍 Enter search query:\n"
            "Examples:\n"
            "#vacation type:photo\n"
            "size<10MB date>2024-01-01\n"
            "\"work document\""
        )
        
    else:
        await query.edit_message_text(f"Button: {data}")

async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    """Download and send file"""
    query = update.callback_query
    
    try:
        file_data = db.files.find_one({"_id": ObjectId(file_id)})
    except InvalidId:
        await query.edit_message_text("❌ Invalid file ID.")
        return
    
    if not file_data:
        await query.edit_message_text("❌ File not found.")
        return
    
    # Check permissions
    if file_data.get('privacy') == 'private' and file_data['user_id'] != update.effective_user.id:
        await query.edit_message_text("⛔ You don't have permission to download this file.")
        return
    
    # Send typing action
    await query.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    
    try:
        # Send file based on type
        if file_data['file_type'] == 'document':
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_data['file_id'],
                caption=f"📄 {file_data['file_name']}",
                filename=file_data['file_name']
            )
        elif file_data['file_type'] == 'photo':
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=file_data['file_id'],
                caption=f"🖼️ {file_data['file_name']}"
            )
        elif file_data['file_type'] == 'video':
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=file_data['file_id'],
                caption=f"🎥 {file_data['file_name']}"
            )
        elif file_data['file_type'] == 'audio':
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=file_data['file_id'],
                caption=f"🎵 {file_data['file_name']}"
            )
        
        # Update download count
        db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$inc": {"downloads": 1}}
        )
        
        # Update user stats
        db.users.update_one(
            {"user_id": update.effective_user.id},
            {"$inc": {"total_downloads": 1}}
        )
        
    except BadRequest as e:
        logger.error(f"Error sending file: {e}")
        await query.edit_message_text("❌ Failed to send file. It may have been deleted from Telegram servers.")

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    """Confirm file deletion"""
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"delete_yes:{file_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"delete_no:{file_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "⚠️ *Are you sure you want to delete this file?*\n\n"
        "This action cannot be undone!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def share_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    """Generate share link for file"""
    query = update.callback_query
    
    try:
        file_data = db.files.find_one({"_id": ObjectId(file_id)})
    except InvalidId:
        await query.edit_message_text("❌ Invalid file ID.")
        return
    
    if not file_data:
        await query.edit_message_text("❌ File not found.")
        return
    
    # Check if file is shareable
    if file_data.get('privacy') == 'private':
        await query.edit_message_text("🔒 This file is private and cannot be shared.")
        return
    
    # Generate share link
    base_url = "https://t.me/your_bot_username"  # Replace with your bot username
    share_link = f"{base_url}?start=file_{file_id}"
    
    # Create keyboard with share options
    keyboard = [
        [InlineKeyboardButton("📤 Share via Telegram", 
         url=f"https://t.me/share/url?url={share_link}&text=Check%20out%20this%20file")],
        [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_link:{file_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔗 *Share Link*\n\n"
        f"*File:* `{file_data['file_name']}`\n"
        f"*Link:* {share_link}\n\n"
        f"Click the button below to share:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ==================== ADMIN COMMANDS ====================
@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin statistics"""
    # Total statistics
    total_users = db.users.count_documents({})
    total_files = db.files.count_documents({"status": "completed"})
    total_size = db.files.aggregate([
        {"$match": {"status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$size"}}}
    ])
    total_size_result = next(total_size, {"total": 0})
    
    # Today's statistics
    today = datetime.now().date()
    today_uploads = db.files.count_documents({
        "upload_date": {"$gte": datetime.combine(today, datetime.min.time())}
    })
    
    # User growth (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    new_users = db.users.count_documents({"join_date": {"$gte": week_ago}})
    
    # File type distribution
    type_distribution = list(db.files.aggregate([
        {"$group": {"_id": "$file_type", "count": {"$sum": 1}, "size": {"$sum": "$size"}}},
        {"$sort": {"count": DESCENDING}}
    ]))
    
    stats_text = f"""
📊 *Admin Statistics*

👥 *Users:*
• Total Users: {total_users}
• New Users (7 days): {new_users}
• Premium Users: {db.users.count_documents({'is_premium': True})}

📁 *Files:*
• Total Files: {total_files}
• Total Size: {format_size(total_size_result['total'])}
• Today's Uploads: {today_uploads}

📈 *File Types:*
"""
    for dist in type_distribution:
        stats_text += f"• {dist['_id']}: {dist['count']} files ({format_size(dist['size'])})\n"
    
    # Storage usage by user
    top_users = list(db.users.find().sort("storage_used", DESCENDING).limit(5))
    stats_text += f"\n🏆 *Top Users by Storage:*\n"
    for user in top_users:
        stats_text += f"• @{user.get('username', 'N/A')}: {format_size(user['storage_used'])}\n"
    
    # Recent activity
    recent_activity = list(db.files.find().sort("upload_date", DESCENDING).limit(5))
    stats_text += f"\n⏰ *Recent Activity:*\n"
    for file in recent_activity:
        time_ago = datetime.now() - file['upload_date']
        hours = int(time_ago.total_seconds() // 3600)
        stats_text += f"• {file['file_name'][:20]} ({hours}h ago)\n"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

@admin_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = ' '.join(context.args)
    users = db.users.find({}, {"user_id": 1})
    
    await update.message.reply_text(f"📢 Broadcasting to {users.count()} users...")
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(user['user_id'], message)
            success += 1
            await asyncio.sleep(0.05)  # Rate limiting
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {user['user_id']}: {e}")
    
    await update.message.reply_text(
        f"✅ Broadcast completed!\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}"
    )

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
    
    # Notify admin
    if Config.LOG_CHAT_ID:
        error_msg = f"🚨 Error: {context.error}\nUpdate: {update}"
        try:
            await context.bot.send_message(Config.LOG_CHAT_ID, error_msg[:4000])
        except:
            pass

# ==================== BACKGROUND TASKS ====================
async def daily_cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Daily cleanup task"""
    logger.info("Running daily cleanup...")
    
    # Reset daily upload counters
    db.users.update_many({}, {"$set": {"uploads_today": 0}})
    
    # Delete expired files
    expired_files = db.files.find({"settings.auto_delete_days": {"$gt": 0}})
    for file in expired_files:
        expire_date = file['upload_date'] + timedelta(days=file['settings']['auto_delete_days'])
        if datetime.now() > expire_date:
            # Delete file from Telegram (if possible)
            try:
                await context.bot.delete_message(file['chat_id'], file.get('message_id', 0))
            except:
                pass
            
            # Delete from database
            db.files.delete_one({"_id": file['_id']})
            logger.info(f"Deleted expired file: {file['_id']}")
    
    logger.info("Daily cleanup completed.")

async def backup_database(context: ContextTypes.DEFAULT_TYPE):
    """Backup database task"""
    logger.info("Running database backup...")
    
    backup_data = {
        "timestamp": datetime.now(),
        "files_count": db.files.count_documents({}),
        "users_count": db.users.count_documents({}),
        "total_size": db.files.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$size"}}}
        ]).next()['total']
    }
    
    db.backups.insert_one(backup_data)
    logger.info(f"Backup created: {backup_data}")

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    # Verify configuration
    if not Config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable is required!")
        exit(1)
    
    # Create application
    application = ApplicationBuilder() \
        .token(Config.BOT_TOKEN) \
        .concurrent_updates(True) \
        .post_init(post_init) \
        .post_stop(post_stop) \
        .build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CommandHandler("myfiles", my_files))
    application.add_handler(CommandHandler("search", search_files))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("info", file_info))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Add message handlers - FIXED: Use correct filter classes
    application.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO | 
        filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE |
        filters.Sticker.ALL | filters.Animation.ALL,  # FIXED HERE
        handle_file
    ))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Add job queue for background tasks
    job_queue = application.job_queue
    
    if job_queue:
        # Daily cleanup at 3 AM
        job_queue.run_daily(daily_cleanup, time=datetime.time(hour=3, minute=0))
        
        # Database backup every 6 hours
        job_queue.run_repeating(backup_database, interval=6*3600, first=10)
        
        # Update analytics every hour
        job_queue.run_repeating(update_analytics, interval=3600, first=5)
    
    # Start the bot
    logger.info("🤖 Bot is starting...")
    print_banner()
    
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False
    )

async def post_init(application: Application):
    """Post initialization tasks"""
    logger.info("✅ Bot initialized successfully")
    
    # Send startup notification to admin
    if Config.LOG_CHAT_ID:
        try:
            await application.bot.send_message(
                Config.LOG_CHAT_ID,
                "🚀 Bot started successfully!\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")

async def post_stop(application: Application):
    """Post stop tasks"""
    logger.info("🛑 Bot is stopping...")
    
    if Config.LOG_CHAT_ID:
        try:
            await application.bot.send_message(
                Config.LOG_CHAT_ID,
                "🛑 Bot stopped!\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except:
            pass

async def update_analytics(context: ContextTypes.DEFAULT_TYPE):
    """Update analytics data"""
    today = datetime.now().date()
    
    analytics_data = {
        "date": today,
        "hour": datetime.now().hour,
        "active_users": db.users.count_documents({"last_seen": {"$gte": datetime.now() - timedelta(hours=1)}}),
        "total_uploads": db.files.count_documents({"upload_date": {"$gte": datetime.combine(today, datetime.min.time())}}),
        "total_downloads": db.files.aggregate([
            {"$match": {"upload_date": {"$gte": datetime.combine(today, datetime.min.time())}}},
            {"$group": {"_id": None, "total": {"$sum": "$downloads"}}}
        ]).next().get('total', 0)
    }
    
    db.analytics.update_one(
        {"date": today, "hour": datetime.now().hour},
        {"$set": analytics_data},
        upsert=True
    )

def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════╗
    ║     ADVANCED TELEGRAM UPLOAD BOT         ║
    ║           WITH MONGODB                   ║
    ╠══════════════════════════════════════════╣
    ║ Status:      ✅ Running                  ║
    ║ Database:    ✅ Connected                ║
    ║ Cache:       ✅ Ready                    ║
    ║ Admin IDs:   {} ║
    ║ Storage:     {}         ║
    ╚══════════════════════════════════════════╝
    """.format(
        str(Config.ADMIN_IDS)[:20].ljust(20),
        format_size(db.files.aggregate([{"$group": {"_id": None, "total": {"$sum": "$size"}}}]).next()['total']).ljust(20)
    )
    print(banner)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
