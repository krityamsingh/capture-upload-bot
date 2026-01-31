import os
import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
import random

# ==================== CONFIGURATION ====================
API_ID = 26676741
API_HASH = "6fbc29f23c15bdb0c7fbbefe65c9193a"
BOT_TOKEN = "8552100143:AAGMjxMfkvoXGTe-PHeRAPYGy-RvHonm7vk"
MONGO_URI = "mongodb+srv://Capture:capture@cluster0.7jqepnf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Channel and Group IDs
CHANNEL_IDS = [-1003430763556, -1002769749639]
CHANNEL_USERNAMES = ["Capture_Talks", "BLACKCLV"]  # For user-friendly display
CHANNEL_LINKS = ["https://t.me/Capture_Talks", "https://t.me/BLACKCLV"]
GROUP_ID = -1002313549356  # ⚠️ Add your group ID here

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
verification_col = db["verification"]

# ==================== ENHANCED JOIN VERIFICATION ====================
async def check_channel_membership(client, user_id):
    """Enhanced check if user joined both channels with caching"""
    try:
        # Check cache first
        cache_key = f"member_{user_id}"
        cached = await verification_col.find_one({"key": cache_key})
        
        if cached and (datetime.now() - cached["checked_at"]).seconds < 300:  # 5 min cache
            return cached["is_member"]
        
        member_status = []
        
        for i, channel_id in enumerate(CHANNEL_IDS):
            try:
                member = await client.get_chat_member(channel_id, user_id)
                status = member.status
                member_status.append({
                    "channel": CHANNEL_USERNAMES[i],
                    "joined": status not in ["left", "kicked", "banned"],
                    "status": status
                })
            except Exception as e:
                member_status.append({
                    "channel": CHANNEL_USERNAMES[i],
                    "joined": False,
                    "status": "error"
                })
        
        all_joined = all(status["joined"] for status in member_status)
        
        # Cache result
        await verification_col.update_one(
            {"key": cache_key},
            {"$set": {
                "user_id": user_id,
                "is_member": all_joined,
                "member_status": member_status,
                "checked_at": datetime.now()
            }},
            upsert=True
        )
        
        return all_joined
        
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

async def get_channel_join_status(client, user_id):
    """Get detailed join status for each channel"""
    status_text = "📊 **YOUR CHANNEL JOIN STATUS**\n\n"
    not_joined = []
    
    for i, channel_id in enumerate(CHANNEL_IDS):
        try:
            member = await client.get_chat_member(channel_id, user_id)
            status = member.status
            
            if status in ["left", "kicked", "banned"]:
                status_text += f"❌ **{CHANNEL_USERNAMES[i]}**: NOT JOINED\n"
                not_joined.append(CHANNEL_LINKS[i])
            else:
                status_text += f"✅ **{CHANNEL_USERNAMES[i]}**: JOINED\n"
                
        except Exception as e:
            status_text += f"❓ **{CHANNEL_USERNAMES[i]}**: CHECK FAILED\n"
            not_joined.append(CHANNEL_LINKS[i])
    
    return status_text, not_joined

async def verify_user_join(client, user_id):
    """Force verify user's channel membership"""
    # Clear cache
    cache_key = f"member_{user_id}"
    await verification_col.delete_one({"key": cache_key})
    
    # Re-check
    return await check_channel_membership(client, user_id)

# ==================== BOT SETUP ====================
app = Client(
    "ad_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ==================== MESSAGE HANDLERS ====================
@app.on_message(filters.command("start"))
async def start_command(client, message):
    """Handle /start command"""
    user = message.from_user
    
    # Register/update user
    await users_col.update_one(
        {"user_id": user.id},
        {"$set": {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "joined_at": datetime.now(),
            "last_active": datetime.now(),
            "language_code": user.language_code,
            "is_bot": user.is_bot
        }},
        upsert=True
    )
    
    # Check if user joined channels
    is_member = await check_channel_membership(client, user.id)
    
    if is_member:
        keyboard = [
            [InlineKeyboardButton("🎯 Get Daily Task", callback_data="get_task")],
            [InlineKeyboardButton("📊 My Statistics", callback_data="my_stats")],
            [InlineKeyboardButton("👥 Check Channel Status", callback_data="check_join")],
            [
                InlineKeyboardButton("📢 Channel 1", url=CHANNEL_LINKS[0]),
                InlineKeyboardButton("📢 Channel 2", url=CHANNEL_LINKS[1])
            ]
        ]
        
        await message.reply_text(
            f"🤖 **Welcome to Ad Task Bot!**\n\n"
            f"👤 **Hello {user.first_name}!**\n"
            f"✅ **Status:** Verified Member\n\n"
            "💰 **Earn money by completing tasks:**\n"
            "• Click posts from @InsideAds_bot\n"
            "• Earn per click\n"
            "• Daily payments\n\n"
            "🎯 **Click below to get your daily task!**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [
            [
                InlineKeyboardButton("✅ Join Channel 1", url=CHANNEL_LINKS[0]),
                InlineKeyboardButton("✅ Join Channel 2", url=CHANNEL_LINKS[1])
            ],
            [InlineKeyboardButton("🔄 Verify My Join", callback_data="force_verify")],
            [InlineKeyboardButton("📊 Check Status", callback_data="check_join_detail")]
        ]
        
        await message.reply_text(
            f"👋 **Welcome {user.first_name}!**\n\n"
            "⚠️ **You must join our channels first!**\n\n"
            "**Required Channels:**\n"
            f"1. **{CHANNEL_USERNAMES[0]}** - {CHANNEL_LINKS[0]}\n"
            f"2. **{CHANNEL_USERNAMES[1]}** - {CHANNEL_LINKS[1]}\n\n"
            "**After joining:**\n"
            "1. Click both join buttons\n"
            "2. Click 'Verify My Join'\n"
            "3. Start earning money!\n\n"
            "💰 **Earnings:** $0.50 - $1.50 per task",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

@app.on_message(filters.command("verify"))
async def verify_command(client, message):
    """Manual verification command"""
    user = message.from_user
    
    # Clear cache and verify
    await verify_user_join(client, user.id)
    is_member = await check_channel_membership(client, user.id)
    
    if is_member:
        await message.reply_text(
            "✅ **VERIFICATION SUCCESSFUL!**\n\n"
            "You have joined both channels!\n"
            "Now use /task to get your first earning task."
        )
    else:
        status_text, not_joined = await get_channel_join_status(client, user.id)
        
        keyboard = []
        for link in not_joined:
            channel_name = CHANNEL_USERNAMES[CHANNEL_LINKS.index(link)]
            keyboard.append([InlineKeyboardButton(f"Join {channel_name}", url=link)])
        
        keyboard.append([InlineKeyboardButton("🔄 Verify Again", callback_data="force_verify")])
        
        await message.reply_text(
            f"{status_text}\n\n"
            "❌ **You haven't joined all channels!**\n"
            "Please join the missing channels above and try again.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

@app.on_message(filters.command("task"))
async def task_command(client, message):
    """Handle /task command"""
    user = message.from_user
    
    # Enhanced verification
    is_member = await check_channel_membership(client, user.id)
    
    if not is_member:
        # Get detailed status
        status_text, not_joined = await get_channel_join_status(client, user.id)
        
        keyboard = []
        for link in not_joined:
            channel_name = CHANNEL_USERNAMES[CHANNEL_LINKS.index(link)]
            keyboard.append([InlineKeyboardButton(f"Join {channel_name}", url=link)])
        
        keyboard.append([InlineKeyboardButton("🔄 Verify My Join", callback_data="force_verify")])
        
        await message.reply_text(
            f"{status_text}\n\n"
            "❌ **ACCESS DENIED**\n"
            "You must join ALL channels to get tasks!\n\n"
            "**Why join?**\n"
            "• Earn money daily\n"
            "• Simple tasks\n"
            "• Instant payments\n\n"
            "**Steps:**\n"
            "1. Join missing channels above\n"
            "2. Click 'Verify My Join'\n"
            "3. Use /task again",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # User is verified - proceed with task
    await process_task_assignment(client, message, user)

async def process_task_assignment(client, message, user):
    """Process task assignment for verified users"""
    # Get recent posts
    recent_posts = await posts_col.find({
        "date": {"$gte": datetime.now() - timedelta(days=1)}
    }).limit(20).to_list(length=20)
    
    if not recent_posts or len(recent_posts) < 2:
        await message.reply_text(
            "📭 **No posts available right now!**\n\n"
            "We're waiting for new ads from @InsideAds_bot\n"
            "Please check back in a few hours.\n\n"
            "⏰ **Next check:** 2 hours\n"
            "📢 **Channel:** @Capture_Talks"
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
            "completed": False,
            "clicks": 0
        }
        task_posts.append(task_post)
    
    task_data = {
        "user_id": user.id,
        "username": user.username,
        "posts": task_posts,
        "assigned_at": datetime.now(),
        "status": "active",
        "completed_at": None,
        "task_code": f"TASK{datetime.now().strftime('%Y%m%d%H%M%S')}_{user.id}",
        "verified_at": datetime.now()
    }
    
    result = await tasks_col.insert_one(task_data)
    task_id = str(result.inserted_id)
    
    # Create interactive keyboard
    keyboard = []
    
    for i, post in enumerate(selected_posts, 1):
        # Get channel info
        channel_idx = CHANNEL_IDS.index(post["channel_id"]) if post["channel_id"] in CHANNEL_IDS else 0
        channel_name = CHANNEL_USERNAMES[channel_idx]
        
        # Create post URL
        if str(post["channel_id"]).startswith("-100"):
            chat_id = str(post["channel_id"]).replace("-100", "")
            post_url = f"https://t.me/c/{chat_id}/{post['message_id']}"
        else:
            post_url = f"https://t.me/{post['channel_id']}/{post['message_id']}"
        
        # Post button
        keyboard.append([
            InlineKeyboardButton(
                f"📰 Post {i} - {channel_name}",
                url=post_url
            )
        ])
        
        # Link buttons (max 3 per post)
        links = post.get("links", [])
        for j, link in enumerate(links[:3], 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"🔗 Link {j} (Post {i})",
                    url=link
                )
            ])
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton("✅ Mark Complete", callback_data=f"complete_{task_id}"),
        InlineKeyboardButton("🔄 Check Progress", callback_data=f"progress_{task_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("📊 Task Stats", callback_data=f"stats_{task_id}"),
        InlineKeyboardButton("❌ Cancel Task", callback_data=f"cancel_{task_id}")
    ])
    
    await message.reply_text(
        f"🎯 **DAILY TASK ASSIGNED**\n\n"
        f"**👤 User:** @{user.username or user.id}\n"
        f"**📝 Task ID:** `{task_data['task_code']}`\n"
        f"**📊 Posts:** {len(selected_posts)}\n"
        f"**⏰ Time:** {datetime.now().strftime('%I:%M %p')}\n"
        f"**💰 Earnings:** ${len(selected_posts) * 0.50}\n\n"
        "**📋 INSTRUCTIONS:**\n"
        "1. Click ALL post buttons (open each post)\n"
        "2. Click ALL link buttons (visit each ad)\n"
        "3. Click '✅ Mark Complete' when done\n\n"
        "**⚠️ IMPORTANT:**\n"
        "• You must click ALL links\n"
        "• Task expires in 24 hours\n"
        "• Fraud detection is active\n\n"
        "**🎁 REWARD:** Tag @rajputanaxironman after completion!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex(r"^force_verify$"))
async def force_verify_handler(client, callback_query):
    """Force verify channel join"""
    user = callback_query.from_user
    
    await callback_query.answer("🔍 Checking your joins...")
    
    # Force verification
    is_member = await verify_user_join(client, user.id)
    
    if is_member:
        await callback_query.message.edit_text(
            "✅ **VERIFICATION SUCCESSFUL!**\n\n"
            "You have joined both channels!\n"
            "Now you can:\n"
            "• Use /task to earn money\n"
            "• Chat in our group\n"
            "• Get daily rewards\n\n"
            "💰 **Click /task to start earning!**"
        )
    else:
        status_text, not_joined = await get_channel_join_status(client, user.id)
        
        keyboard = []
        for link in not_joined:
            channel_name = CHANNEL_USERNAMES[CHANNEL_LINKS.index(link)]
            keyboard.append([InlineKeyboardButton(f"Join {channel_name}", url=link)])
        
        keyboard.append([InlineKeyboardButton("🔄 Verify Again", callback_data="force_verify")])
        
        await callback_query.message.edit_text(
            f"{status_text}\n\n"
            "❌ **VERIFICATION FAILED!**\n"
            "Please join ALL channels and verify again.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

@app.on_callback_query(filters.regex(r"^check_join$"))
async def check_join_handler(client, callback_query):
    """Check join status"""
    user = callback_query.from_user
    
    status_text, not_joined = await get_channel_join_status(client, user.id)
    is_member = await check_channel_membership(client, user.id)
    
    if is_member:
        await callback_query.answer("✅ You have joined both channels!", show_alert=True)
    else:
        await callback_query.answer(f"❌ Missing {len(not_joined)} channel(s)", show_alert=True)

@app.on_callback_query(filters.regex(r"^check_join_detail$"))
async def check_join_detail_handler(client, callback_query):
    """Show detailed join status"""
    user = callback_query.from_user
    
    status_text, not_joined = await get_channel_join_status(client, user.id)
    
    keyboard = []
    if not_joined:
        for link in not_joined:
            channel_name = CHANNEL_USERNAMES[CHANNEL_LINKS.index(link)]
            keyboard.append([InlineKeyboardButton(f"Join {channel_name}", url=link)])
    
    keyboard.append([InlineKeyboardButton("🔄 Verify Now", callback_data="force_verify")])
    
    await callback_query.message.edit_text(
        f"{status_text}\n\n"
        f"**Status:** {'✅ VERIFIED' if len(not_joined) == 0 else '❌ NOT VERIFIED'}\n"
        f"**Missing:** {len(not_joined)} channel(s)\n\n"
        "**Action Required:**\n"
        "Join missing channels and verify again.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== OTHER HANDLERS ====================
@app.on_message(filters.group & filters.incoming)
async def group_message_handler(client, message):
    """Handle group messages - delete if not joined channels"""
    if GROUP_ID and message.chat.id == GROUP_ID:
        if message.from_user and not message.from_user.is_bot:
            is_member = await check_channel_membership(client, message.from_user.id)
            
            if not is_member:
                # Delete message
                await message.delete()
                
                # Get which channels are missing
                status_text, not_joined = await get_channel_join_status(client, message.from_user.id)
                
                # Send warning
                warning = await message.reply_text(
                    f"⚠️ **@{message.from_user.username or message.from_user.id}**\n\n"
                    "Your message was deleted!\n"
                    "You must join our channels first:\n\n"
                    f"{status_text}\n\n"
                    "Join then you can chat here!"
                )
                
                # Delete warning after 15 seconds
                await asyncio.sleep(15)
                await warning.delete()

@app.on_message(filters.chat(CHANNEL_IDS))
async def channel_post_handler(client, message):
    """Monitor and save posts from InsideAds bot"""
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

# ==================== TASK COMPLETION HANDLERS ====================
@app.on_callback_query(filters.regex(r"^complete_"))
async def complete_task_handler(client, callback_query):
    """Handle task completion"""
    task_id = callback_query.data.replace("complete_", "")
    user = callback_query.from_user
    
    task = await tasks_col.find_one({"_id": task_id, "user_id": user.id})
    
    if not task:
        await callback_query.answer("Task not found!", show_alert=True)
        return
    
    # Check if all posts completed
    all_completed = all(post.get("completed", False) for post in task.get("posts", []))
    
    if not all_completed:
        completed = sum(1 for post in task.get("posts", []) if post.get("completed", False))
        total = len(task.get("posts", []))
        
        await callback_query.answer(
            f"❌ Only {completed}/{total} posts completed!",
            show_alert=True
        )
        return
    
    # Mark task as completed
    await tasks_col.update_one(
        {"_id": task_id},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.now()
        }}
    )
    
    # Update user stats
    await users_col.update_one(
        {"user_id": user.id},
        {
            "$inc": {"completed_tasks": 1, "total_earnings": len(task.get("posts", [])) * 0.5},
            "$set": {"last_completed": datetime.now()}
        },
        upsert=True
    )
    
    # Notify admin
    try:
        admin_msg = (
            f"🎉 **TASK COMPLETED - PAYMENT REQUEST**\n\n"
            f"**User:** @{user.username or user.id}\n"
            f"**Task:** {task.get('task_code', 'N/A')}\n"
            f"**Posts:** {len(task.get('posts', []))}\n"
            f"**Earnings:** ${len(task.get('posts', [])) * 0.5}\n"
            f"**Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"**Payment to:** @{ADMIN_USERNAME}"
        )
        
        await client.send_message(
            chat_id=CHANNEL_IDS[0],
            text=admin_msg
        )
    except Exception as e:
        print(f"Failed to notify admin: {e}")
    
    # Success message
    await callback_query.message.edit_text(
        f"✅ **TASK COMPLETED SUCCESSFULLY!**\n\n"
        f"**👤 User:** @{user.username or user.id}\n"
        f"**📝 Task:** {task.get('task_code', 'N/A')}\n"
        f"**📊 Posts:** {len(task.get('posts', []))}\n"
        f"**💰 Earnings:** ${len(task.get('posts', [])) * 0.5}\n"
        f"**⏰ Completed:** {datetime.now().strftime('%I:%M %p')}\n\n"
        f"🏆 **CONGRATULATIONS!**\n\n"
        f"**Next Steps:**\n"
        f"1. Tag @{ADMIN_USERNAME} in the group\n"
        f"2. Send your payment details\n"
        f"3. Wait for confirmation\n\n"
        f"💳 **Payment:** Processed within 24 hours\n"
        f"🔄 **New task:** Available in 24 hours\n\n"
        f"Thank you for your work! 👏"
    )

@app.on_callback_query(filters.regex(r"^progress_"))
async def progress_handler(client, callback_query):
    """Check task progress"""
    task_id = callback_query.data.replace("progress_", "")
    user = callback_query.from_user
    
    task = await tasks_col.find_one({"_id": task_id, "user_id": user.id})
    
    if not task:
        await callback_query.answer("Task not found!", show_alert=True)
        return
    
    completed = sum(1 for post in task.get("posts", []) if post.get("completed", False))
    total = len(task.get("posts", []))
    
    progress_text = f"📊 **Task Progress:** {completed}/{total} posts\n\n"
    
    for i, post in enumerate(task.get("posts", []), 1):
        status = "✅" if post.get("completed") else "❌"
        clicks = post.get("clicks", 0)
        links = len(post.get("links", []))
        progress_text += f"{status} Post {i}: {clicks}/{links} clicks\n"
    
    if completed == total:
        progress_text += "\n🎉 **Ready to complete!**"
    else:
        progress_text += f"\n📝 **Remaining:** {total - completed} posts"
    
    await callback_query.answer(progress_text, show_alert=True)

# ==================== BOT STARTUP ====================
async def main():
    await app.start()
    
    me = await app.get_me()
    print("=" * 50)
    print(f"🤖 Bot started: @{me.username}")
    print(f"📊 Monitoring {len(CHANNEL_IDS)} channels")
    print(f"🔗 Channels: {', '.join(CHANNEL_USERNAMES)}")
    
    if GROUP_ID:
        print(f"👥 Group monitoring: ENABLED")
    else:
        print(f"👥 Group monitoring: DISABLED (set GROUP_ID to enable)")
    
    print("=" * 50)
    
    # Keep bot running
    await idle()

if __name__ == "__main__":
    # Fix for Heroku event loop
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
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        print("🔄 Restarting in 5 seconds...")
        import time
        time.sleep(5)
        # Restart
        loop.run_until_complete(main())

