# ==================== CHARACTER DATABASE VIEWER BOT ====================
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardButton, 
    InlineKeyboardMarkup, CallbackQuery
)
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId

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
    
    # Updated rarity mappings based on your new system
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

config = Config()

# ==================== DATABASE ====================
class MongoDB:
    """MongoDB database operations handler"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.characters = None
        self.sudo_users = None
    
    async def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(config.MONGO_URI)
            self.db = self.client[config.DATABASE_NAME]
            self.characters = self.db.characters
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
                lambda: self.characters.create_index("rarity")
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
    
    # Character operations
    async def get_character_count(self) -> int:
        """Get total number of characters in database"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.characters.count_documents({})
        )
    
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
    
    async def get_characters_by_rarity(self, rarity_name: str, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get characters by rarity with pagination"""
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
    
    async def get_characters_by_subrarity(self, rarity_name: str, subrarity: str, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get characters by sub-rarity with pagination"""
        try:
            skip = page * config.ITEMS_PER_PAGE
            
            # Get characters for current page
            characters = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: list(self.characters.find({
                    "rarity": rarity_name,
                    "subrarity": subrarity
                }).skip(skip).limit(config.ITEMS_PER_PAGE))
            )
            
            # Get total count
            total_count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.characters.count_documents({
                    "rarity": rarity_name,
                    "subrarity": subrarity
                })
            )
            
            return characters, total_count
            
        except PyMongoError as e:
            logger.error(f"Error fetching characters by sub-rarity: {e}")
            return [], 0
    
    async def get_all_characters_paginated(self, page: int = 0, sort_by: str = "character_id") -> tuple[List[Dict[str, Any]], int]:
        """Get all characters with pagination"""
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
    
    async def search_characters(self, query: str, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Search characters by name or anime with pagination"""
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
        """Get count of characters per rarity"""
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
    
    async def get_user_characters(self, user_id: int, page: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """Get all characters uploaded by a user with pagination"""
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

# Global database instance
db = MongoDB()

# ==================== HELPERS ====================
class Helpers:
    """Utility functions for the bot"""
    
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
            # Get count from database (placeholder - we'll need to fetch actual counts)
            count_text = ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{rarity_data['emoji']} {rarity_data['name']} {count_text}",
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
                keyboard.append([
                    InlineKeyboardButton(
                        f"   {sub}",
                        callback_data=f"view_sub_{rarity_num}_{sub.replace(' ', '_')}_page_0_{current_view}"
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
    async def get_username_from_id(client: Client, user_id: int) -> str:
        """Get username from user ID"""
        try:
            user = await client.get_users(user_id)
            return f"@{user.username}" if user.username else user.first_name
        except:
            return f"User ({user_id})"

helpers = Helpers()

# ==================== MAIN BOT ====================
class CharacterViewerBot:
    """Main bot class for viewing character database"""
    
    def __init__(self):
        self.client = Client(
            "character_viewer_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )
        self.user_states = {}  # Store user states for conversations
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all message and callback handlers"""
        
        @self.client.on_message(filters.command("start"))
        async def start_command(client: Client, message: Message):
            """Handle /start command"""
            welcome_text = (
                "👋 **Welcome to Character Database Viewer!**\n\n"
                "This bot allows you to browse all uploaded characters from the database.\n\n"
                "**Main Commands:**\n"
                "• /menu - Show character database menu\n"
                "• /search - Search for characters\n"
                "• /stats - View database statistics\n"
                "• /myuploads - View your uploaded characters\n"
                "• /info - View character details\n\n"
                "**Browse characters by rarity:**\n"
                "Use the /menu command to see all available rarities and sub-rarities."
            )
            
            await message.reply_text(welcome_text)
        
        @self.client.on_message(filters.command("menu"))
        async def menu_command(client: Client, message: Message):
            """Show main menu with rarity options"""
            total_chars = await db.get_character_count()
            
            menu_text = (
                f"📚 **Character Database Menu**\n"
                f"📊 **Total Characters:** {total_chars}\n\n"
                "**Browse by Rarity:**\n"
                "Select a rarity below to view all characters in that category:\n\n"
                "**Rarity System:**\n"
                "1. 🌸 Blossom\n"
                "2. ✨ Starlit\n"
                "3. 🩸 Crimson (🩸 Bloodline, 🕯️ Cursed, 🌑 Shadowborn)\n"
                "4. 🌘 Eclipse (🌘 Lunar, ☀️ Solar, 🌓 Twilight, 🕳️ Void)\n"
                "5. 🌌 Celestia (🌌 Astral, 👼 Seraph, 🔮 Arcane, 🧿 Divine Relic)\n"
                "6. 🪽 Ascended (🪽 Mythborn, 👑 Sovereign, 👁️ Omniscient)\n"
                "7. 🧬 One-of-One\n"
            )
            
            keyboard = helpers.create_rarity_keyboard("main")
            await message.reply_text(menu_text, reply_markup=keyboard)
        
        @self.client.on_message(filters.command("search"))
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
            user_id = message.from_user.id
            
            # Store search state
            self.user_states[user_id] = {
                "action": "search",
                "query": query,
                "page": 0
            }
            
            await message.reply_text(f"🔍 Searching for: `{query}`...")
            
            # Perform search
            characters, total_count = await db.search_characters(query, page=0)
            
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
                            f"👁️ {char.get('char_name', 'Unknown')}",
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
            await message.reply_text("📊 Gathering statistics...")
            
            # Get various stats
            total_chars = await db.get_character_count()
            rarity_stats = await db.get_rarity_stats()
            top_uploaders = await db.get_top_uploaders(10)
            
            # Format stats message
            stats_text = f"📈 **Database Statistics**\n\n"
            stats_text += f"📊 **Total Characters:** {total_chars}\n\n"
            
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
                [InlineKeyboardButton("🔄 Refresh Stats", callback_data="stats_refresh")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
            ])
            
            await message.reply_text(stats_text, reply_markup=keyboard)
        
        @self.client.on_message(filters.command("myuploads"))
        async def myuploads_command(client: Client, message: Message):
            """Show user's uploaded characters"""
            user_id = message.from_user.id
            
            # Store state
            self.user_states[user_id] = {
                "action": "myuploads",
                "page": 0
            }
            
            await message.reply_text("📂 Loading your uploaded characters...")
            
            # Get user's characters
            characters, total_count = await db.get_user_characters(user_id, page=0)
            
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
                            f"👁️ {char.get('char_name', 'Unknown')}",
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
                    subrarity = ' '.join(parts[3:-2])  # Handle spaces in subrarity names
                    page = int(parts[-2])
                    current_view = parts[-1]
                    await self._show_subrarity_characters(client, callback_query, rarity_num, subrarity, page, current_view)
                
                # Pagination for search
                elif data.startswith("search_page_"):
                    parts = data.split("_")
                    page = int(parts[2])
                    query = '_'.join(parts[3:])  # Reconstruct query
                    await self._show_search_results(client, callback_query, query, page)
                
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
                    subrarity = ' '.join(parts[4:-1])  # Handle spaces in subrarity names
                    current_view = parts[-1]
                    await self._show_subrarity_characters(client, callback_query, rarity_num, subrarity, page, current_view)
                
                # Character info
                elif data.startswith("info_"):
                    character_id = int(data.split("_")[1])
                    await self._show_character_info_callback(client, callback_query, character_id)
                
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
                
                # Stats from menu
                elif data == "stats_main" or data == "stats_refresh":
                    await self._show_stats(client, callback_query)
                
                # Unknown callback
                else:
                    await callback_query.answer("Unknown action", show_alert=True)
                
            except Exception as e:
                logger.error(f"Error handling callback: {e}")
                await callback_query.answer("An error occurred", show_alert=True)
        
        # Helper methods
        async def _show_main_menu(self, client: Client, callback_query: CallbackQuery):
            """Show main menu"""
            total_chars = await db.get_character_count()
            
            menu_text = (
                f"📚 **Character Database Menu**\n"
                f"📊 **Total Characters:** {total_chars}\n\n"
                "Select a rarity to browse characters:"
            )
            
            keyboard = helpers.create_rarity_keyboard("main")
            await callback_query.message.edit_text(menu_text, reply_markup=keyboard)
            await callback_query.answer()
        
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
            """Show all characters"""
            characters, total_count = await db.get_all_characters_paginated(page)
            
            if not characters:
                await callback_query.answer("No characters found", show_alert=True)
                return
            
            total_pages = (total_count + config.ITEMS_PER_PAGE - 1) // config.ITEMS_PER_PAGE
            
            # Format message
            message_text = helpers.format_character_list(
                characters, page, total_count, 
                "All Characters"
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
                            f"👁️ {char.get('char_name', 'Unknown')}",
                            callback_data=f"info_{char_id}"
                        )
                    ])
            
            if buttons:
                keyboard.inline_keyboard.extend(buttons)
            
            # Add back button
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    "🔙 Back to Menu" if current_view == "main" else "🔙 Back",
                    callback_data="menu_main" if current_view == "main" else f"rarity_{helpers.get_rarity_number(characters[0].get('rarity', ''))}_{current_view}"
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
                            f"👁️ {char.get('char_name', 'Unknown')}",
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
                            f"👁️ {char.get('char_name', 'Unknown')}",
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
            characters, total_count = await db.search_characters(query, page)
            
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
                            f"👁️ {char.get('char_name', 'Unknown')}",
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
        
        async def _show_myuploads(self, client: Client, callback_query: CallbackQuery, page: int):
            """Show user's uploaded characters"""
            user_id = callback_query.from_user.id
            characters, total_count = await db.get_user_characters(user_id, page)
            
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
                            f"👁️ {char.get('char_name', 'Unknown')}",
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
            character = await db.get_character_by_id(character_id)
            
            if not character:
                await message.reply_text(f"❌ Character with ID `{character_id}` not found!")
                return
            
            # Format character info
            char_info = helpers.format_character_info(character)
            
            # Create keyboard
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back to Menu",
                        callback_data="menu_main"
                    )
                ]
            ])
            
            # Check if character has media
            if character.get('media_url') and character.get('media_type'):
                try:
                    if character.get('media_type') == 'photo':
                        await client.send_photo(
                            chat_id=message.chat.id,
                            photo=character['media_url'],
                            caption=f"**Character Information**\n\n{char_info}",
                            reply_markup=keyboard
                        )
                    elif character.get('media_type') == 'video':
                        await client.send_video(
                            chat_id=message.chat.id,
                            video=character['media_url'],
                            caption=f"**Character Information**\n\n{char_info}",
                            reply_markup=keyboard
                        )
                    elif character.get('media_type') == 'audio':
                        await client.send_audio(
                            chat_id=message.chat.id,
                            audio=character['media_url'],
                            caption=f"**Character Information**\n\n{char_info}",
                            reply_markup=keyboard
                        )
                    else:
                        await client.send_document(
                            chat_id=message.chat.id,
                            document=character['media_url'],
                            caption=f"**Character Information**\n\n{char_info}",
                            reply_markup=keyboard
                        )
                except Exception as e:
                    logger.warning(f"Failed to send media: {e}")
                    char_info += f"\n\n📸 **Media URL:** {character['media_url']}"
                    await message.reply_text(f"**Character Information**\n\n{char_info}", reply_markup=keyboard)
            else:
                await message.reply_text(f"**Character Information**\n\n{char_info}", reply_markup=keyboard)
        
        async def _show_character_info_callback(self, client: Client, callback_query: CallbackQuery, character_id: int):
            """Show character information from callback"""
            character = await db.get_character_by_id(character_id)
            
            if not character:
                await callback_query.answer(f"Character with ID {character_id} not found", show_alert=True)
                return
            
            # Format character info
            char_info = helpers.format_character_info(character)
            
            # Create keyboard
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back to Menu",
                        callback_data="menu_main"
                    )
                ]
            ])
            
            # Since we can't edit message to media, send a new message
            await callback_query.message.reply_text(f"**Character Information**\n\n{char_info}", reply_markup=keyboard)
            await callback_query.answer()
        
        async def _show_stats(self, client: Client, callback_query: CallbackQuery):
            """Show database statistics"""
            # Get various stats
            total_chars = await db.get_character_count()
            rarity_stats = await db.get_rarity_stats()
            top_uploaders = await db.get_top_uploaders(10)
            
            # Format stats message
            stats_text = f"📈 **Database Statistics**\n\n"
            stats_text += f"📊 **Total Characters:** {total_chars}\n\n"
            
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
                [InlineKeyboardButton("🔄 Refresh Stats", callback_data="stats_refresh")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]
            ])
            
            await callback_query.message.edit_text(stats_text, reply_markup=keyboard)
            await callback_query.answer()
    
    async def start(self):
        """Start the bot"""
        try:
            await db.connect()
            logger.info("Database connection established")
            
            await self.client.start()
            logger.info("Bot started successfully")
            
            me = await self.client.get_me()
            logger.info(f"Logged in as @{me.username} (ID: {me.id})")
            
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
    bot = CharacterViewerBot()
    
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
