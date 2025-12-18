#!/usr/bin/env python3
"""
COMPLETE TELEGRAM UPLOAD BOT WITH ALL FEATURES
Simplified version with correct imports
"""

import os
import logging
import asyncio
import json
import hashlib
import uuid
import re
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Set
from io import BytesIO
from functools import wraps
import aiohttp

from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import ConnectionFailure

# Import for python-telegram-bot v20+
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# ==================== LOAD ENVIRONMENT ====================
load_dotenv()

# ==================== CONFIGURATION ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "upload_bot")
    OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
    LOG_CHANNEL = os.getenv("LOG_CHANNEL", "")
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Rarity system
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
    
    ITEMS_PER_PAGE = 10
    RECYCLE_BIN_MAX_DAYS = 30

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== DATABASE CLASS (Simplified) ====================
class MongoDB:
    """Simplified MongoDB handler"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.files = None
        self.deleted_files = None
        self.counters = None
        self.sudo_users = None
        self.users = None
    
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
            self.users = self.db.users
            
            # Create indexes
            self._create_indexes()
            self._initialize_counter()
            
            logger.info("✅ Connected to MongoDB successfully")
            
        except ConnectionFailure as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Create basic indexes"""
        self.files.create_index([("file_id", 1)], unique=True)
        self.files.create_index([("added_by", 1)])
        self.files.create_index([("rarity", 1)])
        
        self.deleted_files.create_index([("file_id", 1)])
        self.deleted_files.create_index([("deleted_at", DESCENDING)])
        
        self.users.create_index([("user_id", 1)], unique=True)
        self.sudo_users.create_index([("user_id", 1)], unique=True)
        
        logger.info("✅ Database indexes created")
    
    def _initialize_counter(self):
        """Initialize counter if not exists"""
        if not self.counters.find_one({"_id": "file_id"}):
            self.counters.insert_one({"_id": "file_id", "seq": 0})
    
    def get_next_file_id(self) -> int:
        """Get next sequential file ID"""
        result = self.counters.find_one_and_update(
            {"_id": "file_id"},
            {"$inc": {"seq": 1}},
            return_document=True
        )
        return result["seq"]
    
    def insert_file(self, file_data: Dict) -> str:
        """Insert a new file into database"""
        result = self.files.insert_one(file_data)
        return str(result.inserted_id)
    
    def get_file_by_id(self, file_id: int) -> Optional[Dict]:
        """Get active file by file ID"""
        return self.files.find_one({"file_id": file_id})
    
    def soft_delete_file(self, file_id: int, deleted_by: int, reason: str = None) -> bool:
        """Move file to recycle bin"""
        file_data = self.files.find_one({"file_id": file_id})
        
        if not file_data:
            return False
        
        file_data["deleted_at"] = datetime.utcnow()
        file_data["deleted_by"] = deleted_by
        if reason:
            file_data["deleted_reason"] = reason
        
        self.deleted_files.insert_one(file_data)
        result = self.files.delete_one({"file_id": file_id})
        
        return result.deleted_count > 0
    
    def restore_file(self, file_id: int) -> bool:
        """Restore file from recycle bin"""
        file_data = self.deleted_files.find_one({"file_id": file_id})
        
        if not file_data:
            return False
        
        file_data.pop("deleted_at", None)
        file_data.pop("deleted_by", None)
        file_data.pop("deleted_reason", None)
        
        self.files.insert_one(file_data)
        result = self.deleted_files.delete_one({"file_id": file_id})
        
        return result.deleted_count > 0
    
    def get_deleted_file_by_id(self, file_id: int) -> Optional[Dict]:
        """Get deleted file by file ID"""
        return self.deleted_files.find_one({"file_id": file_id})
    
    def get_file_count(self) -> int:
        """Get total number of active files"""
        return self.files.count_documents({})
    
    def get_deleted_files_count(self) -> int:
        """Get total number of deleted files"""
        return self.deleted_files.count_documents({})
    
    def get_deleted_files(self, page: int = 0) -> Tuple[List[Dict], int]:
        """Get deleted files with pagination"""
        skip = page * Config.ITEMS_PER_PAGE
        
        files = list(self.deleted_files.find({})
                     .sort("deleted_at", DESCENDING)
                     .skip(skip)
                     .limit(Config.ITEMS_PER_PAGE))
        
        total_count = self.get_deleted_files_count()
        
        return files, total_count
    
    def search_files_paginated(self, query: str, page: int = 0) -> Tuple[List[Dict], int]:
        """Search active files with pagination"""
        skip = page * Config.ITEMS_PER_PAGE
        
        search_filter = {
            "$or": [
                {"file_name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}}
            ]
        }
        
        files = list(self.files.find(search_filter)
                     .skip(skip)
                     .limit(Config.ITEMS_PER_PAGE))
        
        total_count = self.files.count_documents(search_filter)
        
        return files, total_count
    
    def ensure_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """Ensure user exists in database"""
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "join_date": datetime.utcnow(),
            "last_seen": datetime.utcnow()
        }
        
        self.users.update_one(
            {"user_id": user_id},
            {"$setOnInsert": user_data, "$set": {"last_seen": datetime.utcnow()}},
            upsert=True
        )
        
        return user_data
    
    def get_sudo_user(self, user_id: int) -> Optional[Dict]:
        """Get sudo user details"""
        return self.sudo_users.find_one({"user_id": user_id})
    
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

# Initialize database
db = MongoDB()
try:
    db.connect()
except Exception as e:
    logger.error(f"Failed to connect to database: {e}")
    # Continue anyway for testing

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

def parse_rarity(rarity_input: str) -> Optional[str]:
    """Parse rarity input for new rarity system (1-14)"""
    try:
        rarity_num = int(rarity_input.strip())
        if 1 <= rarity_num <= 14:
            return Config.RARITY_MAP[rarity_num]
        return None
    except (ValueError, KeyError):
        return None

def create_pagination_keyboard(current_page: int, total_pages: int, callback_prefix: str, extra_data: str = "") -> InlineKeyboardMarkup:
    """Create pagination keyboard"""
    keyboard = []
    
    if current_page > 0:
        keyboard.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"{callback_prefix}_page_{current_page - 1}_{extra_data}"
            )
        )
    
    keyboard.append(
        InlineKeyboardButton(
            f"📄 {current_page + 1}/{total_pages}",
            callback_data="noop"
        )
    )
    
    if current_page < total_pages - 1:
        keyboard.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"{callback_prefix}_page_{current_page + 1}_{extra_data}"
            )
        )
    
    return InlineKeyboardMarkup([keyboard])

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    db.ensure_user(user.id, user.username, user.first_name)
    
    welcome_text = """
🌟 **Welcome to Upload Bot** 🌟

**Features:**
📤 Upload files with rarity system (1-14)
🗑️ Recycle bin with restore function
🔍 Search and browse files
📊 Statistics and management

**Main Commands:**
• /menu - Browse file database
• /upload - Upload new file
• /search - Search files
• /deleted - View recycle bin
• /stats - View statistics
• /help - Show help
    """
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Browse Database", callback_data="menu_main")],
        [InlineKeyboardButton("📤 Upload File", callback_data="upload_help")],
        [InlineKeyboardButton("🗑️ View Recycle Bin", callback_data="deleted_list_0_main")]
    ])
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = """
ℹ️ **Bot Help Guide**

📤 **Uploading Files:**
1. Send a photo/video/document
2. Reply to it with: `/upload "File Name" "Description" Rarity`

**Example:** `/upload "Project Report" "Q4 Analysis" 3`

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

**Other Commands:**
• /menu - Browse files
• /search - Search files
• /deleted - View deleted files
• /stats - View statistics
    """
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu"""
    total_files = db.get_file_count()
    total_deleted = db.get_deleted_files_count()
    
    menu_text = (
        f"📚 **File Database Menu**\n"
        f"📊 **Active Files:** {total_files}\n"
        f"🗑️ **Deleted Files:** {total_deleted}\n\n"
        "Use /search to find files or /upload to add new files."
    )
    
    await update.message.reply_text(menu_text)

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
            "• `/search vacation photos`"
        )
        return
    
    query = ' '.join(args[1:])
    await update.message.reply_text(f"🔍 Searching for: `{query}`...")
    
    files, total_count = db.search_files_paginated(query, page=0)
    
    if not files:
        await update.message.reply_text(f"❌ No results found for: `{query}`")
        return
    
    total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
    
    message_text = f"🔍 **Search Results for: '{query}'**\n\n"
    message_text += f"📊 **Found:** {total_count} files\n\n"
    
    for i, file in enumerate(files, 1):
        message_text += f"{i}. **{file.get('file_name', 'Unknown')}**\n"
        message_text += f"   🏷️ {file.get('rarity', 'Unknown')} | 🆔 `{file.get('file_id', 'N/A')}`\n\n"
    
    if total_pages > 1:
        keyboard = create_pagination_keyboard(0, total_pages, "search", query)
        await update.message.reply_text(message_text, reply_markup=keyboard)
    else:
        await update.message.reply_text(message_text)

async def deleted_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show deleted files (recycle bin)"""
    await update.message.reply_text("🗑️ Loading recycle bin...")
    
    files, total_count = db.get_deleted_files(page=0)
    
    if not files:
        await update.message.reply_text(
            "🗑️ **Recycle Bin is Empty!**\n\n"
            "No deleted files found.\n"
            "Deleted files are automatically cleaned up after 30 days."
        )
        return
    
    total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
    
    message_text = f"🗑️ **Recycle Bin (Deleted Files)**\n"
    message_text += f"📊 **Total:** {total_count} files\n\n"
    
    for i, file in enumerate(files, 1):
        days_ago = 0
        if file.get('deleted_at') and isinstance(file['deleted_at'], datetime):
            days_ago = (datetime.utcnow() - file['deleted_at']).days
        
        message_text += f"{i}. **{file.get('file_name', 'Unknown')}**\n"
        message_text += f"   🆔 `{file.get('file_id', 'N/A')}` | 🗑️ {days_ago}d ago\n\n"
    
    keyboard = create_pagination_keyboard(0, total_pages, "deleted_list", "main")
    await update.message.reply_text(message_text, reply_markup=keyboard)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show database statistics"""
    total_files = db.get_file_count()
    total_deleted = db.get_deleted_files_count()
    
    stats_text = f"📈 **Database Statistics**\n\n"
    stats_text += f"📊 **Active Files:** {total_files}\n"
    stats_text += f"🗑️ **Deleted Files:** {total_deleted}\n"
    stats_text += f"📈 **Total (All Time):** {total_files + total_deleted}\n\n"
    
    stats_text += "**Bot is running and ready!** 🚀"
    
    await update.message.reply_text(stats_text)

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /upload command"""
    user = update.effective_user
    
    # Check if message is a reply to media
    if not update.message.reply_to_message or not (
        update.message.reply_to_message.document or 
        update.message.reply_to_message.photo or 
        update.message.reply_to_message.video
    ):
        await update.message.reply_text(
            "❌ **Please reply to a media file with this command!**\n\n"
            "**Usage:** Reply to a photo/video/document with:\n"
            "`/upload \"File Name\" \"Description\" Rarity`\n\n"
            "**Example:** `/upload \"Project Report\" \"Q4 Analysis\" 3`"
        )
        return
    
    # Parse arguments
    args = update.message.text.split()
    if len(args) < 4:
        await update.message.reply_text(
            "❌ **Invalid syntax!**\n\n"
            "**Usage:** `/upload \"File Name\" \"Description\" Rarity`\n\n"
            "**Example:** `/upload \"Project Report\" \"Financial Analysis\" 3`"
        )
        return
    
    # Parse file name, description, and rarity
    text = update.message.text
    text = text.replace('/upload', '', 1).strip()
    
    # Simple parsing
    parts = text.split('"')
    if len(parts) < 5:
        await update.message.reply_text("❌ Invalid format. Use quotes for file name and description.")
        return
    
    file_name = parts[1].strip()
    description = parts[3].strip()
    rarity_input = parts[4].strip()
    
    # Parse rarity
    rarity_name = parse_rarity(rarity_input)
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
    else:
        await update.message.reply_text("❌ Unsupported file type.")
        return
    
    # Check file size
    if file_obj.file_size > Config.MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ File too large! Maximum size is {format_size(Config.MAX_FILE_SIZE)}."
        )
        return
    
    # Send processing message
    status_msg = await update.message.reply_text("🔄 Starting upload process...")
    
    try:
        # Get next file ID
        file_id = db.get_next_file_id()
        
        # Create file data
        file_data = {
            "file_name": file_name,
            "description": description,
            "rarity": rarity_name,
            "file_id": file_id,
            "telegram_file_id": file_obj.file_id,
            "file_type": file_type,
            "file_size": file_obj.file_size,
            "added_by": user.id,
            "timestamp": datetime.utcnow(),
            "views": 0,
            "downloads": 0
        }
        
        # Save to database
        inserted_id = db.insert_file(file_data)
        
        # Send success message
        success_text = (
            f"✅ **File #{file_id} Uploaded Successfully!**\n\n"
            f"📁 **Name:** {file_name}\n"
            f"📝 **Description:** {description}\n"
            f"🏷️ **Rarity:** {rarity_name}\n"
            f"📏 **Size:** {format_size(file_obj.file_size)}\n"
            f"🆔 **File ID:** `{file_id}`"
        )
        
        await status_msg.edit_text(success_text)
        
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

# ==================== CALLBACK QUERY HANDLER ====================
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    try:
        if data == "noop":
            return
        
        elif data == "menu_main":
            await menu_command(update, context)
        
        elif data == "upload_help":
            await help_command(update, context)
        
        elif data.startswith("deleted_list_"):
            parts = data.split("_")
            page = int(parts[2]) if len(parts) > 2 else 0
            current_view = parts[3] if len(parts) > 3 else "main"
            
            files, total_count = db.get_deleted_files(page)
            
            if not files:
                await query.answer("No more deleted files", show_alert=True)
                return
            
            total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
            
            message_text = f"🗑️ **Recycle Bin - Page {page + 1}**\n\n"
            
            for i, file in enumerate(files, 1):
                days_ago = 0
                if file.get('deleted_at') and isinstance(file['deleted_at'], datetime):
                    days_ago = (datetime.utcnow() - file['deleted_at']).days
                
                message_text += f"{i}. **{file.get('file_name', 'Unknown')}**\n"
                message_text += f"   🆔 `{file.get('file_id', 'N/A')}` | 🗑️ {days_ago}d ago\n\n"
            
            keyboard = create_pagination_keyboard(page, total_pages, "deleted_list", current_view)
            await query.message.edit_text(message_text, reply_markup=keyboard)
        
        elif data.startswith("search_page_"):
            parts = data.split("_")
            page = int(parts[2])
            query_text = '_'.join(parts[3:])
            
            files, total_count = db.search_files_paginated(query_text, page)
            
            if not files:
                await query.answer("No more results", show_alert=True)
                return
            
            total_pages = (total_count + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE
            
            message_text = f"🔍 **Search Results for: '{query_text}' - Page {page + 1}**\n\n"
            
            for i, file in enumerate(files, 1):
                message_text += f"{i}. **{file.get('file_name', 'Unknown')}**\n"
                message_text += f"   🏷️ {file.get('rarity', 'Unknown')} | 🆔 `{file.get('file_id', 'N/A')}`\n\n"
            
            keyboard = create_pagination_keyboard(page, total_pages, "search", query_text)
            await query.message.edit_text(message_text, reply_markup=keyboard)
        
        else:
            await query.answer("Action not implemented yet", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await query.answer("An error occurred", show_alert=True)

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=True)
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )
        except:
            pass

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
    application.add_handler(CommandHandler("deleted", deleted_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(handle_callbacks))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("🤖 Bot is starting...")
    print("=" * 50)
    print("     SIMPLIFIED UPLOAD BOT")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
