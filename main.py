#!/usr/bin/env python3
"""
Telegram Upload Bot with MongoDB - Heroku Compatible
Simplified working version
"""

import os
import logging
import json
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from io import BytesIO
from functools import wraps

from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from bson import ObjectId
from bson.errors import InvalidId
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import BadRequest

# ==================== LOAD ENVIRONMENT ====================
load_dotenv()

# ==================== CONFIGURATION ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    MONGODB_URI = os.getenv("MONGODB_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    DATABASE_NAME = os.getenv("DATABASE_NAME", "upload_bot")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(','))) if os.getenv("ADMIN_IDS") else []
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 200 * 1024 * 1024))  # 200MB

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        try:
            self.client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.client.server_info()
            self.db = self.client[Config.DATABASE_NAME]
            
            # Collections
            self.files = self.db.files
            self.users = self.db.users
            
            # Create indexes
            self._create_indexes()
            logger.info("✅ Database initialized successfully")
            
        except ConnectionFailure as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def _create_indexes(self):
        """Create database indexes"""
        self.files.create_index([("file_id", 1)], unique=True, sparse=True)
        self.files.create_index([("user_id", 1)])
        self.files.create_index([("upload_date", DESCENDING)])
        self.files.create_index([("tags", 1)])
        self.users.create_index([("user_id", 1)], unique=True)
        logger.info("✅ Database indexes created")

# Initialize database
try:
    db = Database()
except:
    logger.error("Failed to initialize database")
    # Continue without database for now

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

def parse_tags(text: str) -> List[str]:
    """Parse hashtags from text"""
    tags = re.findall(r'#(\w+)', text)
    return [tag.lower() for tag in tags]

# ==================== USER MANAGEMENT ====================
async def ensure_user(user: User):
    """Ensure user exists in database"""
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "join_date": datetime.now(),
        "last_seen": datetime.now(),
        "storage_used": 0,
        "total_uploads": 0,
    }
    
    try:
        db.users.update_one(
            {"user_id": user.id},
            {"$setOnInsert": user_data, "$set": {"last_seen": datetime.now()}},
            upsert=True
        )
    except:
        pass  # Silently fail if database is not available
    
    return user_data

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    await ensure_user(user)
    
    welcome_text = """
🌟 *Welcome to Upload Bot* 🌟

I can help you store and organize your files!

*Available Commands:*
/start - Start the bot
/help - Show help message
/myfiles - List your uploaded files
/search - Search files by tags
/stats - Your statistics

*How to use:*
1. Send me any file (document, photo, video, audio)
2. Add tags in caption: #work #important
3. Set privacy: Add !private or !public

*Examples:*
• Send a photo with caption: "#vacation !private Beach sunset"
• Search: /search #vacation
"""
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """
*Bot Commands:*

/start - Start the bot
/help - Show this help
/myfiles - List your files
/search <tags> - Search files
/stats - Your statistics
/info <file_id> - Get file info

*Upload Instructions:*
Just send me any file! You can add:
• Tags: #work #project #important
• Privacy: !private (only you) or !public (everyone)

*Search Examples:*
/search #work
/search #vacation #beach
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def my_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List user's files"""
    user = update.effective_user
    
    try:
        files = list(db.files.find(
            {"user_id": user.id}
        ).sort("upload_date", DESCENDING).limit(10))
        
        if not files:
            await update.message.reply_text("📭 You haven't uploaded any files yet.")
            return
        
        response = "📁 *Your Files*\n\n"
        
        for idx, file in enumerate(files, 1):
            file_date = file['upload_date'].strftime("%Y-%m-%d")
            file_size = format_size(file['size'])
            
            response += (
                f"*{idx}.* `{file['file_name']}`\n"
                f"   📏 {file_size} | 📅 {file_date}\n"
                f"   🏷️ {', '.join(file.get('tags', ['No tags']))}\n"
                f"   🔗 ID: `{file['_id']}`\n\n"
            )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error fetching files: {e}")
        await update.message.reply_text("❌ Failed to fetch your files.")

async def search_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search files by tags"""
    if not context.args:
        await update.message.reply_text("Usage: /search #tag1 #tag2")
        return
    
    user = update.effective_user
    tags = parse_tags(' '.join(context.args))
    
    if not tags:
        await update.message.reply_text("Please use hashtags like: /search #work #important")
        return
    
    try:
        # Search in user's files and public files
        query = {
            "$or": [
                {"user_id": user.id},  # User's own files
                {"privacy": "public"}   # Public files
            ],
            "tags": {"$all": tags}
        }
        
        files = list(db.files.find(query).limit(10))
        
        if not files:
            await update.message.reply_text("🔍 No files found with these tags.")
            return
        
        response = f"🔍 *Found {len(files)} files*\n\n"
        
        for idx, file in enumerate(files, 1):
            privacy_icon = "🔒" if file.get('privacy') == 'private' else "🌐"
            response += (
                f"*{idx}.* {privacy_icon} `{file['file_name']}`\n"
                f"   👤 {file.get('username', 'Unknown')}\n"
                f"   🔗 ID: `{file['_id']}`\n\n"
            )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        await update.message.reply_text("❌ Search failed.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    user = update.effective_user
    
    try:
        user_data = db.users.find_one({"user_id": user.id}) or {}
        total_files = db.files.count_documents({"user_id": user.id})
        
        stats_text = f"""
📊 *Your Statistics*

👤 *User Info:*
• Username: @{user.username or 'N/A'}
• User ID: `{user.id}`
• Joined: {user_data.get('join_date', datetime.now()).strftime('%Y-%m-%d')}

📁 *Files:*
• Total Files: {total_files}
• Storage Used: {format_size(user_data.get('storage_used', 0))}

📈 *Activity:*
• Total Uploads: {user_data.get('total_uploads', 0)}
• Last Seen: {user_data.get('last_seen', datetime.now()).strftime('%Y-%m-%d %H:%M')}
"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text("❌ Failed to get statistics.")

async def file_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get file information"""
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
📁 *Type:* {file_data['file_type']}
📏 *Size:* {format_size(file_data['size'])}
📅 *Uploaded:* {file_data['upload_date'].strftime('%Y-%m-%d %H:%M:%S')}
👤 *Uploader:* @{file_data.get('username', 'Unknown')}
🔒 *Privacy:* {file_data.get('privacy', 'public')}
🏷️ *Tags:* {', '.join(file_data.get('tags', [])) or 'None'}

📊 *Statistics:*
👁️ Views: {file_data.get('views', 0)}
📥 Downloads: {file_data.get('downloads', 0)}
"""
    
    keyboard = [
        [InlineKeyboardButton("📥 Download", callback_data=f"download:{file_data['_id']}")],
    ]
    
    if user.id == file_data['user_id']:
        keyboard[0].append(InlineKeyboardButton("🗑️ Delete", callback_data=f"delete:{file_data['_id']}"))
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(info_text, parse_mode='Markdown', reply_markup=reply_markup)

# ==================== FILE UPLOAD HANDLER ====================
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming files"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Send typing action
    await update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    
    await ensure_user(user)
    
    # Determine file type
    if update.message.document:
        file_obj = update.message.document
        file_type = "document"
    elif update.message.photo:
        file_obj = update.message.photo[-1]
        file_type = "photo"
    elif update.message.video:
        file_obj = update.message.video
        file_type = "video"
    elif update.message.audio:
        file_obj = update.message.audio
        file_type = "audio"
    elif update.message.voice:
        file_obj = update.message.voice
        file_type = "voice"
    elif update.message.video_note:
        file_obj = update.message.video_note
        file_type = "video_note"
    else:
        await update.message.reply_text("❌ Unsupported file type.")
        return
    
    # Check file size
    if file_obj.file_size > Config.MAX_FILE_SIZE:
        await update.message.reply_text(f"❌ File too large! Max size: {format_size(Config.MAX_FILE_SIZE)}")
        return
    
    # Parse caption
    caption = update.message.caption or ""
    tags = parse_tags(caption)
    
    # Parse privacy
    privacy = "public"
    if "!private" in caption.lower():
        privacy = "private"
    
    try:
        # Prepare file metadata
        file_metadata = {
            "file_id": file_obj.file_id,
            "file_unique_id": file_obj.file_unique_id,
            "file_name": getattr(file_obj, 'file_name', f"{file_type}_{file_obj.file_id}"),
            "file_type": file_type,
            "size": file_obj.file_size,
            "user_id": user.id,
            "username": user.username or user.first_name,
            "chat_id": chat.id,
            "upload_date": datetime.now(),
            "caption": caption,
            "tags": tags,
            "privacy": privacy,
            "views": 0,
            "downloads": 0,
        }
        
        # Save to database
        result = db.files.insert_one(file_metadata)
        
        # Update user stats
        db.users.update_one(
            {"user_id": user.id},
            {
                "$inc": {
                    "storage_used": file_obj.file_size,
                    "total_uploads": 1
                },
                "$set": {"last_seen": datetime.now()}
            }
        )
        
        # Send confirmation
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
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except DuplicateKeyError:
        await update.message.reply_text("⚠️ This file has already been uploaded.")
    except Exception as e:
        logger.error(f"Error saving file: {e}", exc_info=True)
        await update.message.reply_text("❌ Failed to save file. Please try again.")

# ==================== CALLBACK HANDLER ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("download:"):
        file_id = data.split(":")[1]
        await download_file(update, context, file_id)
    elif data.startswith("delete:"):
        file_id = data.split(":")[1]
        await delete_file(update, context, file_id)

async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    """Download file"""
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
        
    except BadRequest as e:
        logger.error(f"Error sending file: {e}")
        await query.edit_message_text("❌ Failed to send file.")

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str):
    """Delete file"""
    query = update.callback_query
    
    try:
        file_data = db.files.find_one({"_id": ObjectId(file_id)})
    except InvalidId:
        await query.edit_message_text("❌ Invalid file ID.")
        return
    
    if not file_data:
        await query.edit_message_text("❌ File not found.")
        return
    
    # Check ownership
    if file_data['user_id'] != update.effective_user.id:
        await query.edit_message_text("⛔ You can only delete your own files.")
        return
    
    try:
        # Delete from database
        result = db.files.delete_one({"_id": ObjectId(file_id)})
        
        if result.deleted_count > 0:
            # Update user storage
            db.users.update_one(
                {"user_id": update.effective_user.id},
                {"$inc": {"storage_used": -file_data['size']}}
            )
            
            await query.edit_message_text(f"✅ File `{file_id}` deleted.")
        else:
            await query.edit_message_text("❌ Failed to delete file.")
            
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        await query.edit_message_text("❌ Failed to delete file.")

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
    application.add_handler(CommandHandler("myfiles", my_files))
    application.add_handler(CommandHandler("search", search_files))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("info", file_info))
    
    # Add message handler for files - SIMPLIFIED FILTER
    application.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO | 
        filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE,
        handle_file
    ))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("🤖 Bot is starting...")
    print("=" * 50)
    print("     TELEGRAM UPLOAD BOT")
    print("     Heroku Compatible Version")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
