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

# Group Configuration (REQUIRED - get from @RawDataBot)
GROUP_ID = None  # ⚠️ CHANGE THIS: Example: -1001234567890

# Bot settings
INSIDE_ADS_BOT = "InsideAds_bot"
ADMIN_USERNAME = "rajputanaxironman"

# Verification settings
VERIFICATION_TIMEOUT = 300  # 5 minutes cache
MAX_VERIFICATION_ATTEMPTS = 3

# ==================== DATABASE SETUP ====================
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["ad_tracking_bot"]

# Collections
users_col = db["users"]
posts_col = db["posts"]
tasks_col = db["user_tasks"]
clicks_col = db["clicks"]
verification_col = db["verification"]
allowed_users_col = db["allowed_users"]

# ==================== JOIN VERIFICATION SYSTEM ====================
class JoinVerification:
    def __init__(self, client):
        self.client = client
        self.verification_messages = {}  # Store verification message IDs
    
    async def check_user_joined_all_channels(self, user_id: int) -> bool:
        """Check if user has joined ALL required channels"""
        try:
            for channel_id in CHANNEL_IDS:
                try:
                    member = await self.client.get_chat_member(channel_id, user_id)
                    if member.status in ["left", "kicked", "banned"]:
                        # Cache failure
                        await verification_col.update_one(
                            {"user_id": user_id, "type": "status"},
                            {"$set": {
                                "joined": False,
                                "failed_channel": channel_id,
                                "checked_at": datetime.now(),
                                "attempts": 1
                            }},
                            upsert=True
                        )
                        return False
                except Exception as e:
                    print(f"Error checking channel {channel_id}: {e}")
                    return False
            
            # User joined all channels
            await verification_col.update_one(
                {"user_id": user_id, "type": "status"},
                {"$set": {
                    "joined": True,
                    "checked_at": datetime.now(),
                    "verified_at": datetime.now(),
                    "attempts": 0
                }},
                upsert=True
            )
            
            # Add to allowed users
            await allowed_users_col.update_one(
                {"user_id": user_id},
                {"$set": {
                    "username": await self.get_username(user_id),
                    "allowed_at": datetime.now(),
                    "verified": True
                }},
                upsert=True
            )
            
            return True
            
        except Exception as e:
            print(f"Error in check_user_joined_all_channels: {e}")
            return False
    
    async def get_username(self, user_id: int) -> str:
        """Get username from user_id"""
        try:
            user = await self.client.get_users(user_id)
            return user.username or f"user_{user_id}"
        except:
            return f"user_{user_id}"
    
    async def send_join_required_message(self, chat_id: int, user_id: int, message_id: int = None):
        """Send join required message with verification button"""
        user_info = await self.get_username(user_id)
        
        # Create interactive message
        keyboard = [
            [
                InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_LINKS[0]),
                InlineKeyboardButton("📢 Join Channel 2", url=CHANNEL_LINKS[1])
            ],
            [InlineKeyboardButton("✅ I Have Joined Both", callback_data=f"verify_join_{user_id}")],
            [InlineKeyboardButton("🔄 Check My Status", callback_data=f"check_status_{user_id}")]
        ]
        
        message_text = (
            f"⚠️ **JOIN REQUIRED**\n\n"
            f"👤 **User:** @{user_info}\n\n"
            "❌ **You cannot send messages here!**\n\n"
            "**To participate in this group, you MUST join:**\n"
            f"1. **{CHANNEL_USERNAMES[0]}** - {CHANNEL_LINKS[0]}\n"
            f"2. **{CHANNEL_USERNAMES[1]}** - {CHANNEL_LINKS[1]}\n\n"
            "**Steps to join:**\n"
            "1. Click both 'Join Channel' buttons above\n"
            "2. Wait 5 seconds after joining\n"
            "3. Click '✅ I Have Joined Both'\n"
            "4. You'll be verified automatically\n\n"
            "✅ **After verification you can:**\n"
            "• Send messages in this group\n"
            "• Use /task to earn money\n"
            "• Get daily rewards\n\n"
            "💰 **Earnings:** $0.50 - $1.50 per task"
        )
        
        try:
            if message_id:
                # Edit existing message
                await self.client.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=message_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return message_id
            else:
                # Send new message
                msg = await self.client.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                # Store message ID for later editing
                self.verification_messages[user_id] = msg.id
                return msg.id
        except Exception as e:
            print(f"Error sending join message: {e}")
            return None
    
    async def verify_user_callback(self, callback_query: CallbackQuery, user_id: int):
        """Handle verification callback"""
        # Get user who clicked (should be the same as user_id in callback_data)
        clicking_user = callback_query.from_user
        
        if clicking_user.id != user_id:
            await callback_query.answer(
                "❌ This verification is for another user!",
                show_alert=True
            )
            return
        
        await callback_query.answer("🔍 Checking your channel joins...")
        
        # Check if user joined all channels
        has_joined = await self.check_user_joined_all_channels(user_id)
        
        if has_joined:
            # User verified successfully
            success_text = (
                f"✅ **VERIFICATION SUCCESSFUL!**\n\n"
                f"👤 **User:** @{clicking_user.username or clicking_user.first_name}\n\n"
                "🎉 **Welcome to the group!**\n\n"
                "You can now:\n"
                "• Send messages freely\n"
                "• Use /task to earn money\n"
                "• Participate in discussions\n\n"
                "💰 **Start earning:** Use /task in this group or PM\n\n"
                "⚠️ **Note:** Verification lasts 24 hours"
            )
            
            # Update verification message
            await callback_query.edit_message_text(
                text=success_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Get Daily Task", callback_data="get_task")]
                ])
            )
            
            # Send welcome message
            await callback_query.message.reply_text(
                f"👋 Welcome @{clicking_user.username or clicking_user.first_name}! "
                f"You're now verified and can chat freely. "
                f"Use /task to start earning money!"
            )
            
        else:
            # User hasn't joined all channels
            await callback_query.answer(
                "❌ You haven't joined all channels! Please join both and try again.",
                show_alert=True
            )
            
            # Update message to show still not joined
            await self.send_join_required_message(
                chat_id=callback_query.message.chat.id,
                user_id=user_id,
                message_id=callback_query.message.id
            )
    
    async def check_user_status(self, user_id: int) -> dict:
        """Check detailed status of user's channel joins"""
        status = {
            "verified": False,
            "channels": {},
            "allowed_until": None
        }
        
        # Check if user is in allowed list
        allowed = await allowed_users_col.find_one({"user_id": user_id, "verified": True})
        if allowed:
            status["verified"] = True
            status["allowed_until"] = allowed.get("allowed_at", datetime.now()) + timedelta(days=1)
        
        # Check each channel
        for i, channel_id in enumerate(CHANNEL_IDS):
            try:
                member = await self.client.get_chat_member(channel_id, user_id)
                status["channels"][CHANNEL_USERNAMES[i]] = {
                    "joined": member.status not in ["left", "kicked", "banned"],
                    "status": member.status
                }
            except:
                status["channels"][CHANNEL_USERNAMES[i]] = {
                    "joined": False,
                    "status": "error"
                }
        
        return status
    
    async def is_user_allowed_to_message(self, user_id: int) -> bool:
        """Check if user is allowed to send messages (cached check)"""
        # Check cache first
        cache = await verification_col.find_one({
            "user_id": user_id, 
            "type": "allowed_cache"
        })
        
        if cache and (datetime.now() - cache["checked_at"]).seconds < VERIFICATION_TIMEOUT:
            return cache.get("allowed", False)
        
        # Check if user is in allowed list
        allowed = await allowed_users_col.find_one({"user_id": user_id, "verified": True})
        
        if allowed:
            # Check if verification is still valid (24 hours)
            allowed_at = allowed.get("allowed_at", datetime.now())
            if datetime.now() - allowed_at < timedelta(days=1):
                # Update cache
                await verification_col.update_one(
                    {"user_id": user_id, "type": "allowed_cache"},
                    {"$set": {
                        "allowed": True,
                        "checked_at": datetime.now(),
                        "expires_at": allowed_at + timedelta(days=1)
                    }},
                    upsert=True
                )
                return True
        
        # Verify by checking channels
        has_joined = await self.check_user_joined_all_channels(user_id)
        
        # Update cache
        await verification_col.update_one(
            {"user_id": user_id, "type": "allowed_cache"},
            {"$set": {
                "allowed": has_joined,
                "checked_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(seconds=VERIFICATION_TIMEOUT)
            }},
            upsert=True
        )
        
        return has_joined

# ==================== BOT SETUP ====================
app = Client(
    "ad_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize verification system
verification = JoinVerification(app)

# ==================== GROUP MESSAGE HANDLER ====================
@app.on_message(filters.group & filters.incoming)
async def group_message_handler(client, message: Message):
    """Handle all group messages - verify user before allowing"""
    if not GROUP_ID or message.chat.id != GROUP_ID:
        return
    
    # Skip messages from bots
    if message.from_user and message.from_user.is_bot:
        return
    
    user_id = message.from_user.id
    
    # Check if user is allowed to message
    is_allowed = await verification.is_user_allowed_to_message(user_id)
    
    if not is_allowed:
        # Delete user's message
        try:
            await message.delete()
        except:
            pass
        
        # Send or update verification message
        user_key = f"verify_msg_{user_id}"
        existing_msg = await verification_col.find_one({"key": user_key})
        
        if existing_msg and (datetime.now() - existing_msg["sent_at"]).seconds < 30:
            # Don't spam, use existing message
            return
        
        # Send verification requirement message
        msg_id = await verification.send_join_required_message(
            chat_id=message.chat.id,
            user_id=user_id
        )
        
        if msg_id:
            # Store message info
            await verification_col.update_one(
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
@app.on_callback_query(filters.regex(r"^verify_join_"))
async def verify_join_callback(client, callback_query: CallbackQuery):
    """Handle 'I Have Joined' button click"""
    try:
        # Extract user_id from callback data
        user_id = int(callback_query.data.replace("verify_join_", ""))
        await verification.verify_user_callback(callback_query, user_id)
    except Exception as e:
        print(f"Error in verify_join_callback: {e}")
        await callback_query.answer("Error processing verification!", show_alert=True)

@app.on_callback_query(filters.regex(r"^check_status_"))
async def check_status_callback(client, callback_query: CallbackQuery):
    """Handle 'Check My Status' button click"""
    try:
        user_id = int(callback_query.data.replace("check_status_", ""))
        
        # Only the user themselves can check
        if callback_query.from_user.id != user_id:
            await callback_query.answer("This is not your status!", show_alert=True)
            return
        
        await callback_query.answer("🔍 Checking your status...")
        
        # Get detailed status
        status = await verification.check_user_status(user_id)
        
        # Build status message
        status_text = "📊 **YOUR VERIFICATION STATUS**\n\n"
        
        # Channel status
        for channel_name, info in status["channels"].items():
            if info["joined"]:
                status_text += f"✅ **{channel_name}:** JOINED\n"
            else:
                status_text += f"❌ **{channel_name}:** NOT JOINED\n"
        
        # Overall status
        if status["verified"]:
            status_text += f"\n✅ **VERIFIED:** YES\n"
            if status["allowed_until"]:
                remaining = status["allowed_until"] - datetime.now()
                hours = remaining.seconds // 3600
                status_text += f"⏰ **Expires in:** {hours} hours\n"
        else:
            status_text += f"\n❌ **VERIFIED:** NO\n"
            status_text += "You must join ALL channels above!\n"
        
        # Action buttons
        keyboard = []
        if not status["verified"]:
            keyboard.append([
                InlineKeyboardButton("✅ Verify Now", callback_data=f"verify_join_{user_id}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data=f"check_status_{user_id}"),
            InlineKeyboardButton("📢 Join Channels", callback_data="show_channels")
        ])
        
        await callback_query.edit_message_text(
            text=status_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        print(f"Error in check_status_callback: {e}")
        await callback_query.answer("Error checking status!", show_alert=True)

@app.on_callback_query(filters.regex(r"^show_channels$"))
async def show_channels_callback(client, callback_query: CallbackQuery):
    """Show channel join buttons"""
    keyboard = [
        [
            InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_LINKS[0]),
            InlineKeyboardButton("📢 Join Channel 2", url=CHANNEL_LINKS[1])
        ],
        [InlineKeyboardButton("✅ I Have Joined", callback_data=f"verify_join_{callback_query.from_user.id}")]
    ]
    
    await callback_query.edit_message_text(
        text="📢 **JOIN OUR CHANNELS**\n\n"
             "Click the buttons below to join our channels.\n"
             "After joining, click '✅ I Have Joined' to verify.\n\n"
             "**Channels to join:**\n"
             f"1. {CHANNEL_USERNAMES[0]}\n"
             f"2. {CHANNEL_USERNAMES[1]}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
    
    # Check if user is verified
    is_verified = await verification.is_user_allowed_to_message(user.id)
    
    if is_verified:
        keyboard = [
            [InlineKeyboardButton("🎯 Get Daily Task", callback_data="get_task")],
            [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
            [InlineKeyboardButton("👥 Check Status", callback_data=f"check_status_{user.id}")]
        ]
        
        await message.reply_text(
            f"🤖 **Welcome back, {user.first_name}!**\n\n"
            f"✅ **Status:** Verified Member\n"
            f"💰 **Ready to earn money!**\n\n"
            "Use the buttons below to get started.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Not verified - show join channels
        await verification.send_join_required_message(
            chat_id=message.chat.id,
            user_id=user.id
        )

@app.on_message(filters.command("verify"))
async def verify_command(client, message: Message):
    """Manual verification command"""
    user = message.from_user
    
    # Force verification check
    is_verified = await verification.check_user_joined_all_channels(user.id)
    
    if is_verified:
        await message.reply_text(
            "✅ **VERIFICATION SUCCESSFUL!**\n\n"
            "You are now verified and can:\n"
            "• Send messages in the group\n"
            "• Use /task to earn money\n"
            "• Get daily rewards\n\n"
            "🎯 Use /task to start earning!"
        )
    else:
        await verification.send_join_required_message(
            chat_id=message.chat.id,
            user_id=user.id
        )

@app.on_message(filters.command("task"))
async def task_command(client, message: Message):
    """Handle /task command - only for verified users"""
    user = message.from_user
    
    # Check if user is verified
    is_verified = await verification.is_user_allowed_to_message(user.id)
    
    if not is_verified:
        await message.reply_text(
            "❌ **ACCESS DENIED**\n\n"
            "You must join our channels first to get tasks!\n\n"
            "**Use /verify to check your status**\n"
            "or click the buttons below to join:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_LINKS[0]),
                    InlineKeyboardButton("📢 Join Channel 2", url=CHANNEL_LINKS[1])
                ],
                [InlineKeyboardButton("✅ I Have Joined", callback_data=f"verify_join_{user.id}")]
            ])
        )
        return
    
    # User is verified - proceed with task assignment
    await assign_task_to_user(client, message, user)

async def assign_task_to_user(client, message, user):
    """Assign task to verified user"""
    # Get recent posts
    recent_posts = await posts_col.find({
        "date": {"$gte": datetime.now() - timedelta(days=1)}
    }).limit(10).to_list(length=10)
    
    if not recent_posts:
        await message.reply_text(
            "📭 **No tasks available yet!**\n\n"
            "Waiting for new posts from @InsideAds_bot\n"
            "Please check back later."
        )
        return
    
    # Select 2-3 posts
    num_posts = random.randint(2, 3)
    selected_posts = random.sample(recent_posts, min(num_posts, len(recent_posts)))
    
    # Create task
    task_data = {
        "user_id": user.id,
        "username": user.username,
        "posts": selected_posts,
        "assigned_at": datetime.now(),
        "status": "active",
        "task_code": f"TASK{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    await tasks_col.insert_one(task_data)
    
    # Create task message with buttons
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
        f"🎯 **TASK ASSIGNED**\n\n"
        f"**User:** @{user.username or user.id}\n"
        f"**Posts:** {len(selected_posts)}\n"
        f"**Earnings:** ${len(selected_posts) * 0.50}\n\n"
        "Click all post links above, then mark complete.",
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

# ==================== BOT STARTUP ====================
async def main():
    await app.start()
    
    me = await app.get_me()
    print("=" * 60)
    print(f"🤖 Bot: @{me.username}")
    print(f"📊 Channels: {', '.join(CHANNEL_USERNAMES)}")
    
    if GROUP_ID:
        print(f"👥 Group Monitoring: ENABLED")
        print(f"✅ Users must join channels to message")
    else:
        print(f"⚠️ Group Monitoring: DISABLED (set GROUP_ID)")
    
    print("=" * 60)
    print("✅ Bot is running...")
    
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
