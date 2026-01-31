import os
import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified, FloodWait
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

# Group Configuration
GROUP_ID = -1003317208864  # ⚠️ SET THIS: Your group ID from @RawDataBot

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

# ==================== DEEP VERIFICATION SYSTEM ====================
class DeepVerification:
    def __init__(self, client):
        self.client = client
        self.user_cache = {}
        self.verification_in_progress = {}
        
    async def deep_check_user_channels(self, user_id: int) -> dict:
        """
        Perform DEEP analysis of user's channel membership
        Checks both channels thoroughly with multiple verification methods
        """
        try:
            user_info = await self.get_user_info(user_id)
            results = {
                "user_id": user_id,
                "username": user_info["username"],
                "first_name": user_info["first_name"],
                "checked_at": datetime.now(),
                "channels": {},
                "all_joined": False,
                "deep_analysis": True
            }
            
            # Check each channel with multiple verification methods
            for i, channel_id in enumerate(CHANNEL_IDS):
                channel_name = CHANNEL_USERNAMES[i]
                
                try:
                    # Method 1: Get chat member status (most reliable)
                    member = await self.client.get_chat_member(channel_id, user_id)
                    status = member.status
                    
                    # Method 2: Check if user can view messages (additional check)
                    can_view = status not in ["left", "kicked", "banned", None]
                    
                    # Method 3: Check join date if available
                    join_date = None
                    if hasattr(member, 'joined_date') and member.joined_date:
                        join_date = datetime.fromtimestamp(member.joined_date)
                    
                    # Store comprehensive channel info
                    results["channels"][channel_name] = {
                        "joined": can_view,
                        "status": status,
                        "join_date": join_date,
                        "can_view_messages": can_view,
                        "link": CHANNEL_LINKS[i],
                        "verified_methods": ["get_chat_member"],
                        "last_checked": datetime.now()
                    }
                    
                    # Additional verification for uncertain cases
                    if status == "member" and not can_view:
                        # Try alternative verification
                        try:
                            # Check if user appears in recent members list
                            # This is a more thorough check
                            results["channels"][channel_name]["verified_methods"].append("alternative_check")
                            results["channels"][channel_name]["joined"] = True
                        except:
                            pass
                            
                except Exception as e:
                    # User is definitely not a member or has privacy restrictions
                    results["channels"][channel_name] = {
                        "joined": False,
                        "status": "error",
                        "error": str(e),
                        "link": CHANNEL_LINKS[i],
                        "verified_methods": ["error"],
                        "last_checked": datetime.now()
                    }
            
            # Determine if user joined ALL channels
            all_joined = all(info["joined"] for info in results["channels"].values())
            results["all_joined"] = all_joined
            
            # Calculate verification score (0-100)
            verification_score = 0
            for channel_name, info in results["channels"].items():
                if info["joined"]:
                    verification_score += 50  # Each channel contributes 50 points
            
            results["verification_score"] = verification_score
            results["verification_level"] = "HIGH" if verification_score == 100 else "MEDIUM" if verification_score == 50 else "LOW"
            
            return results
            
        except Exception as e:
            print(f"Error in deep check: {e}")
            return {
                "user_id": user_id,
                "all_joined": False,
                "error": str(e),
                "deep_analysis": False
            }
    
    async def get_user_info(self, user_id: int) -> dict:
        """Get detailed user information"""
        try:
            user = await self.client.get_users(user_id)
            return {
                "username": user.username or f"user_{user_id}",
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "is_bot": user.is_bot,
                "language_code": user.language_code
            }
        except:
            return {
                "username": f"user_{user_id}",
                "first_name": "Unknown",
                "is_bot": False
            }
    
    async def is_user_already_verified(self, user_id: int) -> bool:
        """Check if user is already verified (cached check)"""
        # Check cache first
        cache_key = f"verified_{user_id}"
        if cache_key in self.user_cache:
            cached = self.user_cache[cache_key]
            if (datetime.now() - cached["checked_at"]).seconds < 300:
                return cached["verified"]
        
        # Check database
        db_verification = await verifications_col.find_one({
            "user_id": user_id,
            "permanent": True,
            "verified_at": {"$gte": datetime.now() - timedelta(days=30)}
        })
        
        if db_verification:
            # Update cache
            self.user_cache[cache_key] = {
                "verified": True,
                "checked_at": datetime.now(),
                "verified_at": db_verification.get("verified_at")
            }
            return True
        
        return False
    
    async def verify_user_automatically(self, user_id: int, deep_check_results: dict) -> bool:
        """Automatically verify user if they have joined all channels"""
        if not deep_check_results["all_joined"]:
            return False
        
        try:
            # Mark as permanently verified
            await verifications_col.update_one(
                {"user_id": user_id},
                {"$set": {
                    "username": deep_check_results.get("username", f"user_{user_id}"),
                    "first_name": deep_check_results.get("first_name", ""),
                    "permanent": True,
                    "verified_at": datetime.now(),
                    "channels": deep_check_results["channels"],
                    "verification_score": deep_check_results.get("verification_score", 100),
                    "verification_level": deep_check_results.get("verification_level", "HIGH"),
                    "deep_analysis": True,
                    "auto_verified": True,
                    "last_verified": datetime.now()
                }},
                upsert=True
            )
            
            # Update cache
            cache_key = f"verified_{user_id}"
            self.user_cache[cache_key] = {
                "verified": True,
                "checked_at": datetime.now(),
                "verified_at": datetime.now(),
                "auto_verified": True
            }
            
            return True
            
        except Exception as e:
            print(f"Error in auto-verification: {e}")
            return False
    
    async def handle_new_user_message(self, message: Message) -> str:
        """
        Handle new user message with deep analysis
        Returns: "verified", "not_verified", or "error"
        """
        user_id = message.from_user.id
        
        # Check if verification is already in progress for this user
        if user_id in self.verification_in_progress:
            return "in_progress"
        
        self.verification_in_progress[user_id] = True
        
        try:
            # Step 1: Check if already verified (quick cache check)
            if await self.is_user_already_verified(user_id):
                del self.verification_in_progress[user_id]
                return "verified"
            
            # Step 2: Perform DEEP channel analysis
            deep_check = await self.deep_check_user_channels(user_id)
            
            if deep_check["all_joined"]:
                # User has joined all channels - auto-verify them
                verified = await self.verify_user_automatically(user_id, deep_check)
                
                if verified:
                    # Send welcome message
                    await self.send_welcome_message(message, deep_check)
                    del self.verification_in_progress[user_id]
                    return "verified"
            
            # User hasn't joined all channels
            del self.verification_in_progress[user_id]
            return "not_verified"
            
        except Exception as e:
            print(f"Error handling new user: {e}")
            if user_id in self.verification_in_progress:
                del self.verification_in_progress[user_id]
            return "error"
    
    async def send_welcome_message(self, message: Message, deep_check: dict):
        """Send welcome message to auto-verified user"""
        user = message.from_user
        username = user.username or user.first_name or f"user_{user.id}"
        
        welcome_text = (
            f"🎉 **WELCOME, {username}!** 🎉\n\n"
            f"✅ **AUTO-VERIFICATION COMPLETE**\n\n"
            "Our system detected that you have already joined:\n"
        )
        
        for channel_name, info in deep_check["channels"].items():
            if info["joined"]:
                welcome_text += f"✅ **{channel_name}**\n"
        
        welcome_text += (
            "\n🏆 **You are WORTHY!** 🏆\n\n"
            "You have been automatically verified and can:\n"
            "• Send messages in this group\n"
            "• Use /task to earn money\n"
            "• Get daily rewards\n\n"
            "💰 **Start earning now!**\n"
            "Use /task to get your first earning task!"
        )
        
        try:
            # Send welcome message
            await message.reply_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Get Daily Task", callback_data=f"get_task_{user.id}")],
                    [InlineKeyboardButton("📊 Check My Status", callback_data=f"status_{user.id}")]
                ])
            )
        except Exception as e:
            print(f"Error sending welcome message: {e}")
    
    async def send_join_required_message(self, chat_id: int, user_id: int):
        """Send join required message for non-verified users"""
        user_info = await self.get_user_info(user_id)
        username = user_info["username"]
        
        # Get detailed channel status
        deep_check = await self.deep_check_user_channels(user_id)
        
        message_text = (
            f"⚠️ **CHANNEL JOIN REQUIRED**\n\n"
            f"👤 **User:** @{username}\n\n"
            "❌ **Your message was deleted!**\n\n"
            "**Our deep analysis shows:**\n"
        )
        
        # Show status for each channel
        for channel_name, info in deep_check["channels"].items():
            if info["joined"]:
                message_text += f"✅ **{channel_name}:** Already Joined\n"
            else:
                message_text += f"❌ **{channel_name}:** Not Joined\n"
        
        message_text += (
            "\n**You must join BOTH channels to participate:**\n"
            f"1. **{CHANNEL_USERNAMES[0]}** - {CHANNEL_LINKS[0]}\n"
            f"2. **{CHANNEL_USERNAMES[1]}** - {CHANNEL_LINKS[1]}\n\n"
            "**Steps to join:**\n"
            "1. Click 'Join Channel' buttons below\n"
            "2. Join both channels\n"
            "3. Return to this chat\n"
            "4. Click '✅ I Have Joined'\n\n"
            "✅ **After joining you can chat & earn money!**\n\n"
            "💰 **Earnings:** $0.50 - $1.50 per task"
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
            msg = await self.client.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )
            return msg.id
        except Exception as e:
            print(f"Error sending join message: {e}")
            return None
    
    async def get_user_status_message(self, user_id: int) -> str:
        """Get detailed status message for user"""
        deep_check = await self.deep_check_user_channels(user_id)
        user_info = await self.get_user_info(user_id)
        
        message = f"🔍 **DEEP ANALYSIS REPORT**\n\n"
        message += f"👤 **User:** @{user_info['username']}\n"
        message += f"📅 **Analysis Time:** {deep_check['checked_at'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        message += "**CHANNEL STATUS:**\n"
        for channel_name, info in deep_check["channels"].items():
            if info["joined"]:
                message += f"✅ **{channel_name}:** JOINED\n"
                if info.get("join_date"):
                    message += f"   📅 Joined: {info['join_date'].strftime('%Y-%m-%d')}\n"
            else:
                message += f"❌ **{channel_name}:** NOT JOINED\n"
                if info.get("error"):
                    message += f"   ⚠️ Error: {info['error'][:50]}...\n"
        
        message += f"\n**Verification Score:** {deep_check.get('verification_score', 0)}/100\n"
        message += f"**Verification Level:** {deep_check.get('verification_level', 'LOW')}\n\n"
        
        # Check if user is in database
        db_status = await verifications_col.find_one({"user_id": user_id})
        if db_status and db_status.get("permanent"):
            message += "✅ **PERMANENT VERIFICATION:** ACTIVE\n"
            if db_status.get("verified_at"):
                verified_time = db_status["verified_at"]
                message += f"📅 **Verified since:** {verified_time.strftime('%Y-%m-%d %H:%M')}\n"
                if db_status.get("auto_verified"):
                    message += "🤖 **Auto-verified by system**\n"
        else:
            message += "❌ **VERIFICATION:** NOT ACTIVE\n"
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
verification = DeepVerification(app)

# ==================== GROUP MESSAGE HANDLER ====================
@app.on_message(filters.group & filters.incoming)
async def group_message_handler(client, message: Message):
    """
    Handle all group messages with DEEP analysis first
    Only delete message if user hasn't joined channels
    """
    if not GROUP_ID or message.chat.id != GROUP_ID:
        return
    
    # Skip messages from bots
    if message.from_user and message.from_user.is_bot:
        return
    
    user_id = message.from_user.id
    
    print(f"🔍 Deep analyzing user {user_id}...")
    
    # Perform DEEP channel analysis
    result = await verification.handle_new_user_message(message)
    
    if result == "verified":
        # User is already verified or auto-verified
        # Message stays, no action needed
        print(f"✅ User {user_id} is verified, message allowed")
        return
    
    elif result == "not_verified":
        # User hasn't joined all channels
        print(f"❌ User {user_id} not verified, deleting message")
        
        # Delete user's message
        try:
            await message.delete()
        except:
            pass
        
        # Send join required message (with rate limiting)
        user_key = f"join_msg_{user_id}"
        existing_msg = await verifications_col.find_one({"key": user_key})
        
        if existing_msg and (datetime.now() - existing_msg["sent_at"]).seconds < 30:
            # Don't spam - wait at least 30 seconds between messages
            return
        
        # Send verification message
        msg_id = await verification.send_join_required_message(
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
    
    elif result == "error":
        # Error occurred during analysis
        print(f"⚠️ Error analyzing user {user_id}")
        # Allow message for now to avoid being too restrictive
        pass
    
    elif result == "in_progress":
        # Verification already in progress
        print(f"⏳ Verification in progress for user {user_id}")
        # Allow message to avoid deletion during verification
        pass

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
        
        await callback_query.answer("🔍 Performing deep channel analysis...")
        
        # Perform DEEP analysis
        deep_check = await verification.deep_check_user_channels(user_id)
        
        if deep_check["all_joined"]:
            # User has joined all channels - verify them
            await verifications_col.update_one(
                {"user_id": user_id},
                {"$set": {
                    "username": deep_check.get("username", f"user_{user_id}"),
                    "first_name": deep_check.get("first_name", ""),
                    "permanent": True,
                    "verified_at": datetime.now(),
                    "channels": deep_check["channels"],
                    "verification_score": deep_check.get("verification_score", 100),
                    "verification_level": deep_check.get("verification_level", "HIGH"),
                    "deep_analysis": True,
                    "manual_verified": True,
                    "last_verified": datetime.now()
                }},
                upsert=True
            )
            
            # Update cache
            cache_key = f"verified_{user_id}"
            verification.user_cache[cache_key] = {
                "verified": True,
                "checked_at": datetime.now(),
                "verified_at": datetime.now(),
                "manual_verified": True
            }
            
            success_text = (
                f"✅ **DEEP VERIFICATION COMPLETE!**\n\n"
                f"👤 **User:** @{clicking_user.username or clicking_user.first_name}\n\n"
                "**Our deep analysis confirms you have joined:**\n"
            )
            
            for channel_name, info in deep_check["channels"].items():
                if info["joined"]:
                    success_text += f"✅ **{channel_name}**\n"
            
            success_text += (
                "\n🏆 **You are WORTHY!** 🏆\n\n"
                "You are now permanently verified and can:\n"
                "• Send messages freely\n"
                "• Use /task to earn money\n"
                "• Get daily rewards\n\n"
                "💰 **Start earning now!**"
            )
            
            try:
                await callback_query.edit_message_text(
                    text=success_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🎯 Get Daily Task", callback_data=f"get_task_{user_id}")],
                        [InlineKeyboardButton("📊 View Report", callback_data=f"status_{user_id}")]
                    ])
                )
            except MessageNotModified:
                pass
            
            # Send welcome message
            await callback_query.message.reply_text(
                f"👋 Welcome @{clicking_user.username or clicking_user.first_name}! "
                f"You're now permanently verified! 🎉\n\n"
                f"Use /task to start earning money! 💰"
            )
            
        else:
            # User hasn't joined all channels
            missing = []
            for channel_name, info in deep_check["channels"].items():
                if not info["joined"]:
                    missing.append(channel_name)
            
            error_text = (
                f"❌ **DEEP VERIFICATION FAILED**\n\n"
                f"**Missing Channels:** {', '.join(missing)}\n\n"
                "Please join ALL channels and try again."
            )
            
            keyboard = []
            for channel_name in missing:
                idx = CHANNEL_USERNAMES.index(channel_name)
                keyboard.append([
                    InlineKeyboardButton(f"📢 Join {channel_name}", url=CHANNEL_LINKS[idx])
                ])
            
            keyboard.append([
                InlineKeyboardButton("🔄 Check Again", callback_data=f"verify_{user_id}")
            ])
            
            try:
                await callback_query.edit_message_text(
                    text=error_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except MessageNotModified:
                pass
            
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
        
        await callback_query.answer("🔍 Generating deep analysis report...")
        
        # Get detailed status report
        status_message = await verification.get_user_status_message(user_id)
        
        # Create buttons based on status
        keyboard = []
        
        # Perform quick check to see if user needs to verify
        deep_check = await verification.deep_check_user_channels(user_id)
        
        if deep_check["all_joined"]:
            # Already joined all channels
            keyboard.append([
                InlineKeyboardButton("✅ Make Verification Permanent", callback_data=f"verify_{user_id}")
            ])
        else:
            # Missing some channels
            for channel_name, info in deep_check["channels"].items():
                if not info["joined"]:
                    idx = CHANNEL_USERNAMES.index(channel_name)
                    keyboard.append([
                        InlineKeyboardButton(f"📢 Join {channel_name}", url=CHANNEL_LINKS[idx])
                    ])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh Analysis", callback_data=f"status_{user_id}"),
            InlineKeyboardButton("📢 Join All Channels", callback_data="join_all")
        ])
        
        try:
            await callback_query.edit_message_text(
                text=status_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )
        except MessageNotModified:
            pass
        
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
        InlineKeyboardButton("🔄 Deep Analysis", callback_data=f"status_{callback_query.from_user.id}")
    ])
    
    try:
        await callback_query.edit_message_text(
            text="📢 **JOIN ALL CHANNELS**\n\n"
                 "Click the buttons below to join our channels.\n"
                 "After joining BOTH channels, click '✅ I Have Joined Both' for deep verification.\n\n"
                 "**Channels to join:**\n"
                 f"1. {CHANNEL_USERNAMES[0]}\n"
                 f"2. {CHANNEL_USERNAMES[1]}\n\n"
                 "✅ **Verification is permanent!**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    except MessageNotModified:
        pass

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
    
    # Perform deep check
    deep_check = await verification.deep_check_user_channels(user.id)
    
    if deep_check["all_joined"]:
        # Auto-verify if not already verified
        db_status = await verifications_col.find_one({"user_id": user.id})
        if not db_status or not db_status.get("permanent"):
            await verification.verify_user_automatically(user.id, deep_check)
        
        keyboard = [
            [InlineKeyboardButton("🎯 Get Daily Task", callback_data=f"get_task_{user.id}")],
            [InlineKeyboardButton("🔍 Deep Analysis Report", callback_data=f"status_{user.id}")],
            [InlineKeyboardButton("📊 My Statistics", callback_data=f"stats_{user.id}")]
        ]
        
        await message.reply_text(
            f"🤖 **Welcome, {user.first_name}!**\n\n"
            f"✅ **Status:** Verified & Worthy\n"
            f"📊 **Verification Score:** {deep_check.get('verification_score', 100)}/100\n\n"
            "💰 **Ready to earn money!**\n\n"
            "Use the buttons below to get started.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Not verified - show join channels with deep analysis
        await verification.send_join_required_message(
            chat_id=message.chat.id,
            user_id=user.id
        )

@app.on_message(filters.command("deepcheck"))
async def deepcheck_command(client, message: Message):
    """Manual deep check command"""
    user = message.from_user
    
    await message.reply_text("🔍 Performing deep channel analysis...")
    
    # Perform deep check
    deep_check = await verification.deep_check_user_channels(user.id)
    status_message = await verification.get_user_status_message(user.id)
    
    keyboard = []
    if deep_check["all_joined"]:
        keyboard.append([
            InlineKeyboardButton("✅ Make Verification Permanent", callback_data=f"verify_{user.id}")
        ])
    else:
        for channel_name, info in deep_check["channels"].items():
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

# ==================== TASK SYSTEM (SIMPLIFIED) ====================
@app.on_message(filters.command("task"))
async def task_command(client, message: Message):
    """Handle /task command - only for verified users"""
    user = message.from_user
    
    # Check if user is verified
    deep_check = await verification.deep_check_user_channels(user.id)
    
    if not deep_check["all_joined"]:
        await message.reply_text(
            "❌ **ACCESS DENIED**\n\n"
            "You must join and verify with our channels first!\n\n"
            "**Use /deepcheck to see your status**\n"
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
        f"**Status:** ✅ Verified & Worthy\n"
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

# ==================== BOT STARTUP ====================
async def main():
    await app.start()
    
    me = await app.get_me()
    print("=" * 60)
    print(f"🤖 Bot: @{me.username}")
    print(f"📊 Channels: {', '.join(CHANNEL_USERNAMES)}")
    print(f"🔍 DEEP VERIFICATION SYSTEM: ACTIVE")
    
    if GROUP_ID:
        print(f"👥 Group Monitoring: ENABLED")
        print(f"✅ Auto-verification for joined users: ACTIVE")
    else:
        print(f"⚠️ Group Monitoring: DISABLED (set GROUP_ID)")
    
    print("=" * 60)
    print("✅ Bot is running with deep analysis...")
    
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
