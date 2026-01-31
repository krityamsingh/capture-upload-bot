import os
import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
import random

# ==================== CONFIGURATION ====================
API_ID = 26676741
API_HASH = "6fbc29f23c15bdb0c7fbbefe65c9193a"
BOT_TOKEN = "8552100143:AAGMjxMfkvoXGTe-PHeRAPYGy-RvHonm7vk"
MONGO_URI = "mongodb+srv://Capture:capture@cluster0.7jqepnf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Channel Configuration
CHANNEL_IDS = [-1003430763556, -1002769749639]
CHANNEL_USERNAMES = ["Capture_Talks", "BLACKCLV"]
CHANNEL_LINKS = ["https://t.me/Capture_Talks", "https://t.me/BLACKCLV"]

# Group Configuration (MUST SET THIS - get from @RawDataBot)
GROUP_ID = None  # ⚠️ SET THIS: Example -1001234567890

# Bot settings
INSIDE_ADS_BOT = "InsideAds_bot"
ADMIN_USERNAME = "rajputanaxironman"

# ==================== DATABASE SETUP ====================
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["ad_tracking_bot"]

# Collections
users_col = db["users"]
posts_col = db["posts"]
tasks_col = db["user_tasks"]
clicks_col = db["clicks"]
verifications_col = db["verifications"]

# ==================== PERMANENT VERIFICATION SYSTEM ====================
class PermanentVerification:
    def __init__(self, client):
        self.client = client
        self.user_checks = {}  # Cache for user verification status
    
    async def check_user_channels(self, user_id: int) -> dict:
        """Check which channels user has joined/left"""
        channel_status = {}
        all_joined = True
        
        for i, channel_id in enumerate(CHANNEL_IDS):
            try:
                member = await self.client.get_chat_member(channel_id, user_id)
                is_member = member.status not in ["left", "kicked", "banned", None]
                
                channel_status[CHANNEL_USERNAMES[i]] = {
                    "joined": is_member,
                    "status": member.status,
                    "link": CHANNEL_LINKS[i]
                }
                
                if not is_member:
                    all_joined = False
                    
            except Exception as e:
                channel_status[CHANNEL_USERNAMES[i]] = {
                    "joined": False,
                    "status": "error",
                    "link": CHANNEL_LINKS[i]
                }
                all_joined = False
        
        return {
            "user_id": user_id,
            "all_joined": all_joined,
            "channels": channel_status,
            "checked_at": datetime.now()
        }
    
    async def is_user_verified(self, user_id: int) -> bool:
        """Check if user is currently verified (has joined both channels)"""
        # Check cache first
        cache_key = f"verify_{user_id}"
        if cache_key in self.user_checks:
            cached = self.user_checks[cache_key]
            if (datetime.now() - cached["checked_at"]).seconds < 300:  # 5 min cache
                return cached["all_joined"]
        
        # Check in database
        db_verification = await verifications_col.find_one({"user_id": user_id})
        if db_verification and db_verification.get("permanent", False):
            # Still need to check if user hasn't left channels
            status = await self.check_user_channels(user_id)
            
            # Update cache
            self.user_checks[cache_key] = status
            
            # Update database if user left channels
            if not status["all_joined"]:
                await verifications_col.update_one(
                    {"user_id": user_id},
                    {"$set": {"permanent": False, "left_at": datetime.now()}}
                )
            
            return status["all_joined"]
        
        # Check channels directly
        status = await self.check_user_channels(user_id)
        
        # Update cache
        self.user_checks[cache_key] = status
        
        # Update database
        await verifications_col.update_one(
            {"user_id": user_id},
            {"$set": {
                "username": await self.get_username(user_id),
                "all_joined": status["all_joined"],
                "channels": status["channels"],
                "last_checked": datetime.now(),
                "permanent": status["all_joined"],
                "verified_at": datetime.now() if status["all_joined"] else None
            }},
            upsert=True
        )
        
        return status["all_joined"]
    
    async def get_username(self, user_id: int) -> str:
        """Get username from user ID"""
        try:
            user = await self.client.get_users(user_id)
            return user.username or f"user_{user_id}"
        except:
            return f"user_{user_id}"
    
    async def send_verification_message(self, chat_id: int, user_id: int, message_id: int = None):
        """Send verification message with inline buttons"""
        user_info = await self.get_username(user_id)
        
        # Check current status
        status = await self.check_user_channels(user_id)
        
        # Create message based on status
        if status["all_joined"]:
            message_text = (
                f"✅ **VERIFICATION COMPLETE**\n\n"
                f"👤 **User:** @{user_info}\n\n"
                "🎉 **You have joined both channels!**\n\n"
                "You can now:\n"
                "• Send messages in this group\n"
                "• Use /task to earn money\n"
                "• Get daily rewards\n\n"
                "💰 **Start earning now!**"
            )
            
            keyboard = [
                [InlineKeyboardButton("🎯 Get Daily Task", callback_data=f"get_task_{user_id}")],
                [InlineKeyboardButton("📊 Check Status", callback_data=f"status_{user_id}")]
            ]
            
        else:
            # Find which channels are missing
            missing_channels = []
            for channel_name, info in status["channels"].items():
                if not info["joined"]:
                    missing_channels.append(channel_name)
            
            message_text = (
                f"⚠️ **CHANNEL JOIN REQUIRED**\n\n"
                f"👤 **User:** @{user_info}\n\n"
                "❌ **You cannot send messages yet!**\n\n"
            )
            
            if missing_channels:
                message_text += f"**Missing Channels ({len(missing_channels)}):**\n"
                for channel in missing_channels:
                    message_text += f"• {channel}\n"
                message_text += "\n"
            
            message_text += (
                "**You must join BOTH channels:**\n"
                f"1. **{CHANNEL_USERNAMES[0]}** - {CHANNEL_LINKS[0]}\n"
                f"2. **{CHANNEL_USERNAMES[1]}** - {CHANNEL_LINKS[1]}\n\n"
                "**Steps:**\n"
                "1. Click 'Join Channel' buttons below\n"
                "2. Join both channels\n"
                "3. Return to this chat\n"
                "4. Click '✅ I Have Joined'\n\n"
                "✅ **After joining you can chat & earn money!**"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(f"📢 Join {CHANNEL_USERNAMES[0]}", url=CHANNEL_LINKS[0]),
                    InlineKeyboardButton(f"📢 Join {CHANNEL_USERNAMES[1]}", url=CHANNEL_LINKS[1])
                ],
                [InlineKeyboardButton("✅ I Have Joined Both", callback_data=f"verify_{user_id}")],
                [InlineKeyboardButton("🔄 Check My Status", callback_data=f"status_{user_id}")]
            ]
        
        try:
            if message_id:
                # Edit existing message
                await self.client.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=message_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    disable_web_page_preview=True
                )
                return message_id
            else:
                # Send new message
                msg = await self.client.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    disable_web_page_preview=True
                )
                return msg.id
                
        except Exception as e:
            print(f"Error sending verification message: {e}")
            return None
    
    async def verify_user(self, user_id: int) -> dict:
        """Verify user and mark as permanent if joined all channels"""
        status = await self.check_user_channels(user_id)
        
        if status["all_joined"]:
            # Mark as permanently verified
            await verifications_col.update_one(
                {"user_id": user_id},
                {"$set": {
                    "permanent": True,
                    "verified_at": datetime.now(),
                    "channels": status["channels"],
                    "last_verified": datetime.now()
                }},
                upsert=True
            )
            
            # Update cache
            cache_key = f"verify_{user_id}"
            self.user_checks[cache_key] = status
            
            return {
                "success": True,
                "message": "✅ **PERMANENT VERIFICATION GRANTED!**\n\nYou have joined both channels. You can now chat freely and use /task to earn money!"
            }
        else:
            # Find which channels are missing
            missing = []
            for channel_name, info in status["channels"].items():
                if not info["joined"]:
                    missing.append(channel_name)
            
            return {
                "success": False,
                "message": f"❌ **VERIFICATION FAILED!**\n\nYou haven't joined all channels.\nMissing: {', '.join(missing)}\n\nPlease join both channels and try again.",
                "missing_channels": missing
            }
    
    async def get_user_status_message(self, user_id: int) -> str:
        """Get detailed status message for user"""
        status = await self.check_user_channels(user_id)
        user_info = await self.get_username(user_id)
        
        message = f"📊 **VERIFICATION STATUS**\n\n"
        message += f"👤 **User:** @{user_info}\n\n"
        
        # Channel status
        message += "**Channel Status:**\n"
        for channel_name, info in status["channels"].items():
            if info["joined"]:
                message += f"✅ **{channel_name}:** Joined\n"
            else:
                message += f"❌ **{channel_name}:** Not Joined\n"
        
        message += "\n"
        
        # Overall status
        if status["all_joined"]:
            db_status = await verifications_col.find_one({"user_id": user_id})
            if db_status and db_status.get("permanent"):
                message += "✅ **Permanent Verification:** ACTIVE\n"
                if db_status.get("verified_at"):
                    verified_time = db_status["verified_at"]
                    message += f"📅 **Verified since:** {verified_time.strftime('%Y-%m-%d %H:%M')}\n"
            else:
                message += "⚠️ **Verification:** TEMPORARY (Click 'Verify' to make permanent)\n"
        else:
            message += "❌ **Verification:** NOT VERIFIED\n"
            message += "Join both channels and click 'Verify' button\n"
        
        return message

# ==================== BOT SETUP ====================
app = Client(
    "ad_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize verification system
verification = PermanentVerification(app)

# ==================== GROUP MESSAGE HANDLER ====================
@app.on_message(filters.group & filters.incoming)
async def group_message_handler(client, message: Message):
    """Handle all group messages - check verification before allowing"""
    if not GROUP_ID or message.chat.id != GROUP_ID:
        return
    
    # Skip messages from bots
    if message.from_user and message.from_user.is_bot:
        return
    
    user_id = message.from_user.id
    
    # Check if user is verified
    is_verified = await verification.is_user_verified(user_id)
    
    if not is_verified:
        # Delete user's message
        try:
            await message.delete()
        except:
            pass
        
        # Send verification message (with rate limiting)
        user_key = f"verify_msg_{user_id}"
        existing_msg = await verifications_col.find_one({"key": user_key})
        
        if existing_msg and (datetime.now() - existing_msg["sent_at"]).seconds < 30:
            # Don't spam - wait at least 30 seconds between messages
            return
        
        # Send verification message
        msg_id = await verification.send_verification_message(
            chat_id=message.chat.id,
            user_id=user_id
        )
        
        if msg_id:
            # Store message info
            await verifications_col.update_one(
                {"key": user_key},
                {"$set": {
                    "message_id": msg_id,
                    "user_id": user_id,
                    "sent_at": datetime.now(),
                    "chat_id": message.chat.id
                }},
                upsert=True
            )

# ==================== CALLBACK QUERY HANDLERS ====================
@app.on_callback_query(filters.regex(r"^verify_"))
async def verify_callback_handler(client, callback_query: CallbackQuery):
    """Handle 'I Have Joined' button click"""
    try:
        user_id = int(callback_query.data.replace("verify_", ""))
        clicking_user = callback_query.from_user
        
        # Verify it's the right user
        if clicking_user.id != user_id:
            await callback_query.answer(
                "❌ This verification is for another user!",
                show_alert=True
            )
            return
        
        await callback_query.answer("🔍 Checking your channel joins...")
        
        # Verify user
        result = await verification.verify_user(user_id)
        
        if result["success"]:
            # Success - user verified
            await callback_query.edit_message_text(
                text=result["message"],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Get Daily Task", callback_data=f"get_task_{user_id}")],
                    [InlineKeyboardButton("💬 Start Chatting", callback_data="start_chatting")]
                ])
            )
            
            # Send welcome message
            await callback_query.message.reply_text(
                f"👋 Welcome @{clicking_user.username or clicking_user.first_name}! "
                f"You're now permanently verified! 🎉\n\n"
                f"You can now send messages in this group. "
                f"Use /task to start earning money! 💰"
            )
        else:
            # Failed - show which channels are missing
            keyboard = []
            for channel_name in result.get("missing_channels", []):
                idx = CHANNEL_USERNAMES.index(channel_name)
                keyboard.append([
                    InlineKeyboardButton(f"📢 Join {channel_name}", url=CHANNEL_LINKS[idx])
                ])
            
            keyboard.append([
                InlineKeyboardButton("🔄 Check Again", callback_data=f"verify_{user_id}")
            ])
            
            await callback_query.edit_message_text(
                text=result["message"],
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        print(f"Error in verify_callback: {e}")
        await callback_query.answer("Error during verification!", show_alert=True)

@app.on_callback_query(filters.regex(r"^status_"))
async def status_callback_handler(client, callback_query: CallbackQuery):
    """Handle 'Check My Status' button click"""
    try:
        user_id = int(callback_query.data.replace("status_", ""))
        clicking_user = callback_query.from_user
        
        # Verify it's the right user
        if clicking_user.id != user_id:
            await callback_query.answer(
                "❌ This status check is for another user!",
                show_alert=True
            )
            return
        
        await callback_query.answer("📊 Checking your status...")
        
        # Get status message
        status_message = await verification.get_user_status_message(user_id)
        
        # Create buttons based on status
        keyboard = []
        
        # Check current status
        current_status = await verification.check_user_channels(user_id)
        
        if current_status["all_joined"]:
            # Already joined all channels
            keyboard.append([
                InlineKeyboardButton("✅ Make Verification Permanent", callback_data=f"verify_{user_id}")
            ])
        else:
            # Missing some channels
            for channel_name, info in current_status["channels"].items():
                if not info["joined"]:
                    idx = CHANNEL_USERNAMES.index(channel_name)
                    keyboard.append([
                        InlineKeyboardButton(f"📢 Join {channel_name}", url=CHANNEL_LINKS[idx])
                    ])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh Status", callback_data=f"status_{user_id}"),
            InlineKeyboardButton("📢 Join All Channels", callback_data="join_all")
        ])
        
        await callback_query.edit_message_text(
            text=status_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        print(f"Error in status_callback: {e}")
        await callback_query.answer("Error checking status!", show_alert=True)

@app.on_callback_query(filters.regex(r"^join_all$"))
async def join_all_callback_handler(client, callback_query: CallbackQuery):
    """Show all channel join buttons"""
    keyboard = []
    
    for i, channel_name in enumerate(CHANNEL_USERNAMES):
        keyboard.append([
            InlineKeyboardButton(f"📢 Join {channel_name}", url=CHANNEL_LINKS[i])
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ I Have Joined Both", callback_data=f"verify_{callback_query.from_user.id}"),
        InlineKeyboardButton("🔄 Check Status", callback_data=f"status_{callback_query.from_user.id}")
    ])
    
    await callback_query.edit_message_text(
        text="📢 **JOIN ALL CHANNELS**\n\n"
             "Click the buttons below to join our channels.\n"
             "After joining BOTH channels, click '✅ I Have Joined Both' to verify.\n\n"
             "**Channels to join:**\n"
             f"1. {CHANNEL_USERNAMES[0]}\n"
             f"2. {CHANNEL_USERNAMES[1]}\n\n"
             "✅ **Verification is permanent until you leave channels!**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex(r"^get_task_"))
async def get_task_callback_handler(client, callback_query: CallbackQuery):
    """Handle 'Get Daily Task' button"""
    user_id = int(callback_query.data.replace("get_task_", ""))
    user = callback_query.from_user
    
    # Verify it's the right user
    if user.id != user_id:
        await callback_query.answer("This task is for another user!", show_alert=True)
        return
    
    # Check if user is verified
    is_verified = await verification.is_user_verified(user_id)
    
    if not is_verified:
        await callback_query.answer("❌ You must verify first!", show_alert=True)
        await verification.send_verification_message(
            chat_id=callback_query.message.chat.id,
            user_id=user_id,
            message_id=callback_query.message.id
        )
        return
    
    # User is verified - assign task
    await assign_daily_task(client, callback_query.message, user)

# ==================== COMMAND HANDLERS ====================
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    """Handle /start command"""
    user = message.from_user
    
    # Register user
    await users_col.update_one(
        {"user_id": user.id},
        {"$set": {
            "username": user.username,
            "first_name": user.first_name,
            "joined_at": datetime.now(),
            "last_seen": datetime.now()
        }},
        upsert=True
    )
    
    # Check verification status
    is_verified = await verification.is_user_verified(user.id)
    
    if is_verified:
        keyboard = [
            [InlineKeyboardButton("🎯 Get Daily Task", callback_data=f"get_task_{user.id}")],
            [InlineKeyboardButton("📊 My Statistics", callback_data=f"stats_{user.id}")],
            [InlineKeyboardButton("👥 Check Status", callback_data=f"status_{user.id}")]
        ]
        
        await message.reply_text(
            f"🤖 **Welcome back, {user.first_name}!**\n\n"
            f"✅ **Status:** Permanently Verified\n"
            f"💰 **Ready to earn money!**\n\n"
            "Use the buttons below to get started.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Not verified - show join channels
        await verification.send_verification_message(
            chat_id=message.chat.id,
            user_id=user.id
        )

@app.on_message(filters.command("verify"))
async def verify_command(client, message: Message):
    """Manual verification command"""
    user = message.from_user
    
    # Send verification message
    await verification.send_verification_message(
        chat_id=message.chat.id,
        user_id=user.id
    )

@app.on_message(filters.command("status"))
async def status_command(client, message: Message):
    """Check verification status"""
    user = message.from_user
    
    status_message = await verification.get_user_status_message(user.id)
    
    keyboard = []
    current_status = await verification.check_user_channels(user.id)
    
    if current_status["all_joined"]:
        keyboard.append([
            InlineKeyboardButton("✅ Make Permanent", callback_data=f"verify_{user.id}")
        ])
    else:
        for channel_name, info in current_status["channels"].items():
            if not info["joined"]:
                idx = CHANNEL_USERNAMES.index(channel_name)
                keyboard.append([
                    InlineKeyboardButton(f"Join {channel_name}", url=CHANNEL_LINKS[idx])
                ])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh", callback_data=f"status_{user.id}")
    ])
    
    await message.reply_text(
        status_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

@app.on_message(filters.command("task"))
async def task_command(client, message: Message):
    """Handle /task command - only for verified users"""
    user = message.from_user
    
    # Check if user is verified
    is_verified = await verification.is_user_verified(user.id)
    
    if not is_verified:
        await message.reply_text(
            "❌ **ACCESS DENIED**\n\n"
            "You must join and verify with our channels first!\n\n"
            "**Use /verify to start verification**\n"
            "or click below to join channels:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"📢 {CHANNEL_USERNAMES[0]}", url=CHANNEL_LINKS[0]),
                    InlineKeyboardButton(f"📢 {CHANNEL_USERNAMES[1]}", url=CHANNEL_LINKS[1])
                ],
                [InlineKeyboardButton("✅ I Have Joined", callback_data=f"verify_{user.id}")]
            ])
        )
        return
    
    # User is verified - assign task
    await assign_daily_task(client, message, user)

async def assign_daily_task(client, message, user):
    """Assign daily task to verified user"""
    # Get recent posts from InsideAds bot
    recent_posts = await posts_col.find({
        "date": {"$gte": datetime.now() - timedelta(days=1)}
    }).limit(20).to_list(length=20)
    
    if not recent_posts or len(recent_posts) < 2:
        await message.reply_text(
            "📭 **No tasks available yet!**\n\n"
            "Waiting for new posts from @InsideAds_bot\n"
            "Please check back in a few hours.\n\n"
            "⏰ **Next check:** 2 hours\n"
            "📢 **Channels:** @Capture_Talks & @BLACKCLV"
        )
        return
    
    # Select 2-3 random posts
    num_posts = random.randint(2, 3)
    selected_posts = random.sample(recent_posts, min(num_posts, len(recent_posts)))
    
    # Create task
    task_posts = []
    for post in selected_posts:
        task_post = {
            "post_id": str(post["_id"]),
            "message_id": post["message_id"],
            "channel_id": post["channel_id"],
            "links": post.get("links", []),
            "completed": False
        }
        task_posts.append(task_post)
    
    task_data = {
        "user_id": user.id,
        "username": user.username,
        "posts": task_posts,
        "assigned_at": datetime.now(),
        "status": "active",
        "task_code": f"TASK{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "verified": True
    }
    
    await tasks_col.insert_one(task_data)
    
    # Create task interface
    keyboard = []
    for i, post in enumerate(selected_posts, 1):
        # Create post URL
        channel_id = str(post["channel_id"]).replace("-100", "")
        post_url = f"https://t.me/c/{channel_id}/{post['message_id']}"
        
        keyboard.append([
            InlineKeyboardButton(f"📰 Visit Post {i}", url=post_url)
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Mark Complete", callback_data="complete_task"),
        InlineKeyboardButton("🔄 Check Progress", callback_data="check_progress")
    ])
    
    await message.reply_text(
        f"🎯 **DAILY TASK ASSIGNED**\n\n"
        f"**User:** @{user.username or user.id}\n"
        f"**Posts:** {len(selected_posts)}\n"
        f"**Earnings:** ${len(selected_posts) * 0.50}\n\n"
        "**Instructions:**\n"
        "1. Click ALL post links above\n"
        "2. Visit each link in the posts\n"
        "3. Click 'Mark Complete' when done\n\n"
        "✅ **You're verified - start earning!**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== CHANNEL MONITORING ====================
@app.on_message(filters.chat(CHANNEL_IDS))
async def channel_post_handler(client, message: Message):
    """Save posts from InsideAds bot"""
    if message.from_user and message.from_user.username:
        if message.from_user.username.lower() == INSIDE_ADS_BOT.lower():
            post_data = {
                "message_id": message.id,
                "channel_id": message.chat.id,
                "date": datetime.now(),
                "text": message.text or message.caption or "",
                "links": [],
                "saved_at": datetime.now()
            }
            
            import re
            if message.text:
                urls = re.findall(r'https?://[^\s]+', message.text)
                post_data["links"] = urls
            
            if message.reply_markup:
                for row in message.reply_markup.inline_keyboard:
                    for button in row:
                        if hasattr(button, 'url') and button.url:
                            post_data["links"].append(button.url)
            
            await posts_col.update_one(
                {"message_id": message.id, "channel_id": message.chat.id},
                {"$set": post_data},
                upsert=True
            )

# ==================== PERIODIC VERIFICATION CHECK ====================
async def periodic_verification_check():
    """Periodically check if verified users have left channels"""
    while True:
        try:
            # Get all permanently verified users
            verified_users = await verifications_col.find({
                "permanent": True
            }).to_list(length=1000)
            
            for user in verified_users:
                user_id = user["user_id"]
                
                # Check current status
                status = await verification.check_user_channels(user_id)
                
                if not status["all_joined"]:
                    # User left a channel - remove permanent verification
                    await verifications_col.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "permanent": False,
                            "left_at": datetime.now(),
                            "channels": status["channels"]
                        }}
                    )
                    
                    # Clear cache
                    cache_key = f"verify_{user_id}"
                    if cache_key in verification.user_checks:
                        del verification.user_checks[cache_key]
                    
                    print(f"⚠️ User {user_id} left channels - verification removed")
            
            # Wait 5 minutes before next check
            await asyncio.sleep(300)
            
        except Exception as e:
            print(f"Error in periodic verification check: {e}")
            await asyncio.sleep(60)

# ==================== BOT STARTUP ====================
async def main():
    await app.start()
    
    me = await app.get_me()
    print("=" * 60)
    print(f"🤖 Bot: @{me.username}")
    print(f"📊 Channels: {', '.join(CHANNEL_USERNAMES)}")
    
    if GROUP_ID:
        print(f"👥 Group Monitoring: ENABLED")
        print(f"✅ Permanent Verification System: ACTIVE")
        print(f"🔍 Periodic checks every 5 minutes")
    else:
        print(f"⚠️ Group Monitoring: DISABLED (set GROUP_ID)")
    
    print("=" * 60)
    print("✅ Bot is running...")
    
    # Start periodic verification check
    asyncio.create_task(periodic_verification_check())
    
    await idle()

if __name__ == "__main__":
    # Set event loop for Heroku
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔄 Restarting in 10 seconds...")
        import time
        time.sleep(10)
        loop.run_until_complete(main())
