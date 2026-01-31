import os
import asyncio
import logging
from datetime import datetime
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
CHANNEL_IDS = [-1003430763556, -1002769749639]  # Your channels
GROUP_ID = None  # ⚠️ Add your group ID here

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

# ==================== HELPER FUNCTIONS ====================
async def check_channel_membership(client, user_id):
    """Check if user joined both channels"""
    try:
        for channel_id in CHANNEL_IDS:
            try:
                member = await client.get_chat_member(channel_id, user_id)
                if member.status in ["left", "kicked"]:
                    return False
            except:
                return False
        return True
    except:
        return False

async def save_insideads_post(message):
    """Save posts from InsideAds bot"""
    if not message.from_user:
        return
    
    if message.from_user.username and message.from_user.username.lower() == INSIDE_ADS_BOT.lower():
        post_data = {
            "message_id": message.id,
            "channel_id": message.chat.id,
            "date": datetime.now(),
            "text": message.text or message.caption or "",
            "links": [],
            "saved_at": datetime.now()
        }
        
        # Extract links
        import re
        if message.text:
            urls = re.findall(r'https?://[^\s]+', message.text)
            post_data["links"] = urls
        
        # Check buttons
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
        
        print(f"📥 Saved post from InsideAds: {message.id}")

async def get_task_posts_for_user(user_id):
    """Get 2-3 random posts for user task"""
    # Get recent posts
    recent_posts = await posts_col.find().sort("date", -1).limit(20).to_list(length=20)
    
    if not recent_posts:
        return []
    
    # Get 2-3 random posts
    num_posts = random.randint(2, 3)
    selected_posts = random.sample(recent_posts, min(num_posts, len(recent_posts)))
    
    return selected_posts

# ==================== BOT SETUP ====================
app = Client(
    "ad_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

# ==================== MESSAGE HANDLERS ====================
@app.on_message(filters.command("start"))
async def start_command(client, message):
    """Handle /start command"""
    user = message.from_user
    await users_col.update_one(
        {"user_id": user.id},
        {"$set": {
            "username": user.username,
            "first_name": user.first_name,
            "joined_at": datetime.now()
        }},
        upsert=True
    )
    
    keyboard = [
        [InlineKeyboardButton("🎯 Get Daily Task", callback_data="get_task")],
        [InlineKeyboardButton("📢 Join Channels", callback_data="join_channels")],
        [InlineKeyboardButton("💰 Earnings", callback_data="earnings")],
        [
            InlineKeyboardButton("Channel 1", url="https://t.me/Capture_Talks"),
            InlineKeyboardButton("Channel 2", url="https://t.me/BLACKCLV")
        ]
    ]
    
    await message.reply_text(
        f"🤖 **Welcome to Ad Task Bot!**\n\n"
        f"👤 **Hello {user.first_name}!**\n\n"
        "💰 **Earn money by:**\n"
        "1. Joining our channels\n"
        "2. Completing daily tasks\n"
        "3. Clicking ad links\n\n"
        "🎯 **Daily Tasks:** 2-3 posts/day\n"
        "💵 **Earnings:** Pay per click\n\n"
        "👇 **Click 'Get Daily Task' to start!**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_message(filters.command("task"))
async def task_command(client, message):
    """Handle /task command with inline interface"""
    user = message.from_user
    
    # Check if user joined channels
    is_member = await check_channel_membership(client, user.id)
    
    if not is_member:
        keyboard = [
            [
                InlineKeyboardButton("✅ Join Channel 1", url="https://t.me/Capture_Talks"),
                InlineKeyboardButton("✅ Join Channel 2", url="https://t.me/BLACKCLV")
            ],
            [InlineKeyboardButton("🔄 I Joined", callback_data="check_join")]
        ]
        
        await message.reply_text(
            "❌ **You must join both channels first!**\n\n"
            "**Required Channels:**\n"
            "1. https://t.me/Capture_Talks\n"
            "2. https://t.me/BLACKCLV\n\n"
            "👇 **Click buttons to join:**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Get task posts
    posts = await get_task_posts_for_user(user.id)
    
    if not posts:
        await message.reply_text(
            "📭 **No posts available right now!**\n\n"
            "Please wait for @InsideAds_bot to post in our channels.\n"
            "Check back in a few hours!"
        )
        return
    
    # Create task
    task_posts = []
    for post in posts:
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
        "task_code": f"TASK{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    result = await tasks_col.insert_one(task_data)
    task_id = str(result.inserted_id)
    
    # Create interactive keyboard
    keyboard = []
    for i, post in enumerate(posts, 1):
        # Create post URL
        channel_id = post["channel_id"]
        message_id = post["message_id"]
        
        if str(channel_id).startswith("-100"):
            chat_id = str(channel_id).replace("-100", "")
            post_url = f"https://t.me/c/{chat_id}/{message_id}"
        else:
            post_url = f"https://t.me/{channel_id}/{message_id}"
        
        # Button for each post
        keyboard.append([
            InlineKeyboardButton(
                f"📰 Post {i} - Click Here",
                url=post_url
            )
        ])
        
        # Buttons for links in post (max 2)
        links = post.get("links", [])
        for j, link in enumerate(links[:2], 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"🔗 Link {j} (Post {i})",
                    url=link
                )
            ])
    
    # Completion buttons
    keyboard.append([
        InlineKeyboardButton("✅ Mark Complete", callback_data=f"complete_{task_id}"),
        InlineKeyboardButton("🔄 Check Progress", callback_data=f"progress_{task_id}")
    ])
    
    await message.reply_text(
        f"🎯 **DAILY TASK ASSIGNED**\n\n"
        f"**User:** @{user.username or user.id}\n"
        f"**Task ID:** `{task_data['task_code']}`\n"
        f"**Posts:** {len(posts)}\n"
        f"**Time:** {datetime.now().strftime('%H:%M')}\n\n"
        "**Instructions:**\n"
        "1. Click ALL post buttons below\n"
        "2. Click ALL link buttons in each post\n"
        "3. Click '✅ Mark Complete' when done\n\n"
        "⚠️ **You MUST click all links for verification**\n"
        "💰 **Earnings:** ${len(posts) * 0.50} (estimated)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_message(filters.group & filters.incoming)
async def group_message_handler(client, message):
    """Handle group messages - delete if not joined channels"""
    if GROUP_ID and message.chat.id == GROUP_ID:
        # Skip bots
        if message.from_user and message.from_user.is_bot:
            return
        
        # Check if user joined channels
        is_member = await check_channel_membership(client, message.from_user.id)
        
        if not is_member:
            # Delete message
            await message.delete()
            
            # Send warning
            warning = await message.reply_text(
                f"⚠️ **@{message.from_user.username or message.from_user.id}**\n\n"
                "Your message was deleted!\n"
                "You must join our channels first:\n\n"
                "1. https://t.me/Capture_Talks\n"
                "2. https://t.me/BLACKCLV\n\n"
                "Join both channels to chat here!"
            )
            
            # Delete warning after 10 seconds
            await asyncio.sleep(10)
            await warning.delete()

@app.on_message(filters.chat(CHANNEL_IDS))
async def channel_post_handler(client, message):
    """Monitor and save posts from InsideAds bot"""
    await save_insideads_post(message)

@app.on_callback_query()
async def callback_handler(client, callback_query):
    """Handle inline button clicks"""
    data = callback_query.data
    user = callback_query.from_user
    
    await callback_query.answer()
    
    if data == "get_task":
        # Simulate /task command
        message = Message(
            id=callback_query.message.id,
            chat=callback_query.message.chat,
            from_user=user,
            text="/task"
        )
        await task_command(client, message)
    
    elif data == "join_channels":
        keyboard = [
            [
                InlineKeyboardButton("Join Channel 1", url="https://t.me/Capture_Talks"),
                InlineKeyboardButton("Join Channel 2", url="https://t.me/BLACKCLV")
            ],
            [InlineKeyboardButton("✅ I Joined Both", callback_data="check_join")]
        ]
        
        await callback_query.message.edit_text(
            "📢 **JOIN OUR CHANNELS**\n\n"
            "To use this bot and earn money, you MUST join:\n\n"
            "1. **Capture Talks** - https://t.me/Capture_Talks\n"
            "2. **BLACKCLV** - https://t.me/BLACKCLV\n\n"
            "👇 Click buttons to join, then click 'I Joined Both'",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "check_join":
        is_member = await check_channel_membership(client, user.id)
        
        if is_member:
            await callback_query.answer("✅ Great! You joined both channels!", show_alert=True)
            
            # Go back to start
            await start_command(client, callback_query.message)
        else:
            await callback_query.answer("❌ You haven't joined both channels!", show_alert=True)
    
    elif data.startswith("complete_"):
        task_id = data.replace("complete_", "")
        
        # Get task
        task = await tasks_col.find_one({"_id": task_id})
        
        if not task or task["user_id"] != user.id:
            await callback_query.answer("Task not found!", show_alert=True)
            return
        
        # Check if all posts completed
        all_completed = all(post.get("completed", False) for post in task["posts"])
        
        if all_completed:
            # Mark as completed
            await tasks_col.update_one(
                {"_id": task_id},
                {"$set": {"status": "completed", "completed_at": datetime.now()}}
            )
            
            # Update user stats
            await users_col.update_one(
                {"user_id": user.id},
                {"$inc": {"completed_tasks": 1}},
                upsert=True
            )
            
            # Notify admin
            try:
                admin_msg = (
                    f"🎉 **TASK COMPLETED**\n\n"
                    f"**User:** @{user.username or user.id}\n"
                    f"**Task ID:** {task['task_code']}\n"
                    f"**Posts:** {len(task['posts'])}\n"
                    f"**Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"**Reward to:** @{ADMIN_USERNAME}"
                )
                
                await client.send_message(
                    chat_id=CHANNEL_IDS[0],
                    text=admin_msg
                )
            except:
                pass
            
            # Success message
            await callback_query.message.edit_text(
                f"✅ **TASK COMPLETED!**\n\n"
                f"**User:** @{user.username or user.id}\n"
                f"**Task:** {task['task_code']}\n"
                f"**Posts:** {len(task['posts'])}\n"
                f"**Earnings:** ${len(task['posts']) * 0.50}\n\n"
                f"🏆 **Congratulations!**\n\n"
                f"**Next Steps:**\n"
                f"1. Tag @{ADMIN_USERNAME} in the group\n"
                f"2. Send your payment details\n"
                f"3. Wait for confirmation\n\n"
                f"💰 **Payment:** Processed within 24 hours\n"
                f"🔄 **New task:** Available tomorrow"
            )
        else:
            await callback_query.answer("❌ Not all posts completed!", show_alert=True)
    
    elif data.startswith("progress_"):
        task_id = data.replace("progress_", "")
        task = await tasks_col.find_one({"_id": task_id})
        
        if task and task["user_id"] == user.id:
            completed = sum(1 for post in task["posts"] if post.get("completed", False))
            total = len(task["posts"])
            
            progress_msg = f"📊 Progress: {completed}/{total} posts\n"
            
            for i, post in enumerate(task["posts"], 1):
                status = "✅" if post.get("completed") else "❌"
                progress_msg += f"{status} Post {i}: {len(post.get('links', []))} links\n"
            
            await callback_query.answer(progress_msg, show_alert=True)
        else:
            await callback_query.answer("Task not found!", show_alert=True)

# ==================== BOT STARTUP ====================
async def main():
    await app.start()
    
    me = await app.get_me()
    print(f"🤖 Bot started: @{me.username}")
    print(f"📊 Monitoring channels: {len(CHANNEL_IDS)}")
    
    if not GROUP_ID:
        print("⚠️ GROUP_ID not set - Group monitoring disabled")
    
    # Keep running
    await idle()
    await app.stop()

if __name__ == "__main__":
    # Heroku requires this
    port = int(os.environ.get("PORT", 5000))
    
    print("=" * 50)
    print("🚀 Bot Starting...")
    print("=" * 50)
    
    try:
        # Create event loop for async
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
