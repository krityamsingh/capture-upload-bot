import asyncio
import os
from datetime import datetime
from typing import Optional

from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    User,
    ChatJoinRequest
)
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# ==================== CONFIGURATION ====================
load_dotenv()

API_ID =  # GET FROM my.telegram.org
API_HASH = ""  # GET FROM my.telegram.org
BOT_TOKEN = "8552100143:AAGMjxMfkvoXGTe-PHeRAPYGy-RvHonm7vk"

# Your channels (Bot must be admin)
CHANNEL_IDS = [-1003430763556, -1002769749639]
# Your group where bot will enforce rules
GROUP_ID = -1002313549356 # ADD YOUR GROUP ID HERE

# MongoDB Configuration (USE A .env FILE IN PRODUCTION!)
MONGO_URI = "mongodb+srv://Capture:capture@cluster0.7jqepnf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "telegram_task_bot"

# InsideAds bot username (without @)
INSIDE_ADS_BOT = "InsideAds_bot"

# Admin to tag for rewards
ADMIN_USERNAME = "rajputanaxironman"

# ==================== DATABASE SETUP ====================
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]

# Collections
users_col = db["users"]
posts_col = db["posts"]
tasks_col = db["tasks"]
clicks_col = db["clicks"]

# ==================== BOT INITIALIZATION ====================
app = Client(
    "task_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# ==================== HELPER FUNCTIONS ====================
async def is_user_joined(user_id: int) -> bool:
    """Check if user has joined both channels"""
    try:
        for channel_id in CHANNEL_IDS:
            member = await app.get_chat_member(channel_id, user_id)
            if member.status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]:
                return False
        return True
    except:
        return False

async def save_new_post(post_message: Message):
    """Save posts from InsideAds bot to database"""
    if not post_message.from_user:
        return
    
    if post_message.from_user.username == INSIDE_ADS_BOT:
        post_data = {
            "message_id": post_message.id,
            "channel_id": post_message.chat.id,
            "date": post_message.date,
            "text": post_message.text or post_message.caption or "",
            "links": [],
            "has_button": False
        }
        
        # Extract links from text
        if post_message.text:
            import re
            links = re.findall(r'https?://[^\s]+', post_message.text)
            post_data["links"] = links
        
        # Check for inline buttons
        if post_message.reply_markup:
            post_data["has_button"] = True
            # Extract button links
            for row in post_message.reply_markup.inline_keyboard:
                for button in row:
                    if button.url:
                        post_data["links"].append(button.url)
        
        await posts_col.update_one(
            {"message_id": post_message.id, "channel_id": post_message.chat.id},
            {"$set": post_data},
            upsert=True
        )
        print(f"📥 Saved post {post_message.id} from {INSIDE_ADS_BOT}")

async def assign_task_to_user(user_id: int):
    """Assign 2-3 random posts as task to user"""
    # Get recent active posts (last 24 hours)
    yesterday = datetime.now().timestamp() - 86400
    recent_posts = await posts_col.find({
        "date": {"$gte": yesterday}
    }).to_list(length=10)
    
    if not recent_posts:
        return None
    
    import random
    num_posts = random.randint(2, 3)
    selected_posts = random.sample(recent_posts, min(num_posts, len(recent_posts)))
    
    # Create task record
    task_posts = []
    for post in selected_posts:
        task_post = {
            "post_id": post["_id"],
            "message_id": post["message_id"],
            "channel_id": post["channel_id"],
            "completed": False,
            "clicked_at": None
        }
        task_posts.append(task_post)
    
    task_data = {
        "user_id": user_id,
        "posts": task_posts,
        "assigned_at": datetime.now(),
        "completed_at": None,
        "status": "assigned"
    }
    
    result = await tasks_col.insert_one(task_data)
    return str(result.inserted_id), selected_posts

async def track_click(user_id: int, url: str):
    """Track when a user clicks a link"""
    click_data = {
        "user_id": user_id,
        "url": url,
        "clicked_at": datetime.now(),
        "credited": False
    }
    await clicks_col.insert_one(click_data)
    
    # Find and mark task post as completed
    post = await posts_col.find_one({"links": url})
    if post:
        await tasks_col.update_one(
            {"user_id": user_id, "posts.post_id": post["_id"]},
            {"$set": {
                "posts.$.completed": True,
                "posts.$.clicked_at": datetime.now()
            }}
        )

# ==================== MESSAGE HANDLERS ====================
@app.on_message(filters.chat(CHANNEL_IDS))
async def handle_channel_post(client: Client, message: Message):
    """Monitor posts in channels"""
    await save_new_post(message)

@app.on_message(filters.group & filters.incoming)
async def handle_group_message(client: Client, message: Message):
    """Enforce channel join in group"""
    if message.chat.id != GROUP_ID:
        return
    
    user_id = message.from_user.id
    
    # Ignore messages from admins/bots
    if message.from_user.is_bot:
        return
    
    # Check if user has joined channels
    joined = await is_user_joined(user_id)
    
    if not joined:
        # Delete user's message
        await message.delete()
        
        # Send warning
        warning_msg = await message.reply_text(
            f"👤 **@{message.from_user.username or message.from_user.id}**\n\n"
            "⚠️ **You must join both channels first!**\n\n"
            f"🔗 {CHANNEL_IDS[0]}\n"
            f"🔗 {CHANNEL_IDS[1]}\n\n"
            "Join both channels and try again.",
            reply_to_message_id=message.id
        )
        
        # Delete warning after 10 seconds
        await asyncio.sleep(10)
        await warning_msg.delete()

@app.on_message(filters.command("task"))
async def handle_task_command(client: Client, message: Message):
    """Handle /task command with inline interface"""
    user_id = message.from_user.id
    
    # Check channel membership
    if not await is_user_joined(user_id):
        channels_text = "\n".join([f"• Channel {i+1}" for i in range(len(CHANNEL_IDS))])
        await message.reply_text(
            f"❌ **You must join all channels first!**\n\n"
            f"{channels_text}\n\n"
            "Join them and try /task again."
        )
        return
    
    # Assign new task
    task_id, posts = await assign_task_to_user(user_id)
    
    if not posts:
        await message.reply_text("📭 No posts available for tasks yet. Check back later!")
        return
    
    # Create inline buttons for each post
    keyboard = []
    for i, post in enumerate(posts, 1):
        # Get channel info for the post
        try:
            chat = await client.get_chat(post["channel_id"])
            channel_name = chat.title
        except:
            channel_name = f"Channel {i}"
        
        # Create button that links directly to the post
        post_link = f"https://t.me/c/{str(post['channel_id']).replace('-100', '')}/{post['message_id']}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"📰 Post {i} - {channel_name[:15]}",
                url=post_link
            )
        ])
    
    # Add completion button
    keyboard.append([
        InlineKeyboardButton(
            "✅ I Visited All Posts",
            callback_data=f"complete_task_{task_id}"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            "🔄 Check Progress",
            callback_data=f"check_progress_{task_id}"
        )
    ])
    
    await message.reply_text(
        f"🎯 **DAILY TASK ASSIGNED**\n\n"
        f"**Posts to visit:** {len(posts)}\n"
        f"**User:** @{message.from_user.username or message.from_user.id}\n\n"
        "**Instructions:**\n"
        "1. Click each post button below\n"
        "2. Click ALL links in each post\n"
        "3. Click '✅ I Visited All Posts' when done\n\n"
        "⚠️ **You MUST click all links for verification**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_callback_query(filters.regex(r"^complete_task_"))
async def handle_completion(client: Client, callback_query: CallbackQuery):
    """Handle task completion"""
    task_id = callback_query.data.split("_")[-1]
    user_id = callback_query.from_user.id
    
    # Get task
    task = await tasks_col.find_one({"_id": task_id})
    if not task:
        await callback_query.answer("Task not found!", show_alert=True)
        return
    
    # Check if all posts are completed
    all_completed = all(post.get("completed", False) for post in task["posts"])
    
    if all_completed:
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
            {"user_id": user_id},
            {"$inc": {"completed_tasks": 1}},
            upsert=True
        )
        
        # Notify admin
        try:
            admin_message = (
                f"🎉 **TASK COMPLETED!**\n\n"
                f"**User:** @{callback_query.from_user.username or user_id}\n"
                f"**Task ID:** {task_id[:8]}...\n"
                f"**Posts clicked:** {len(task['posts'])}\n\n"
                f"Please send reward to @{ADMIN_USERNAME}"
            )
            
            # Send to first channel admin
            await client.send_message(
                chat_id=CHANNEL_IDS[0],
                text=admin_message
            )
        except Exception as e:
            print(f"Failed to notify admin: {e}")
        
        await callback_query.edit_message_text(
            f"✅ **TASK COMPLETED SUCCESSFULLY!**\n\n"
            f"**User:** @{callback_query.from_user.username or user_id}\n"
            f"**Posts visited:** {len(task['posts'])}\n"
            f"**Completed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🏆 **Admin @{ADMIN_USERNAME} has been notified!**\n"
            f"Wait for your reward.\n\n"
            "Thank you for participating! 🎊"
        )
    else:
        # Show which posts are pending
        pending = [i+1 for i, post in enumerate(task["posts"]) if not post.get("completed", False)]
        await callback_query.answer(
            f"❌ Still pending: Posts {', '.join(map(str, pending))}",
            show_alert=True
        )

@app.on_callback_query(filters.regex(r"^check_progress_"))
async def check_progress(client: Client, callback_query: CallbackQuery):
    """Check task progress"""
    task_id = callback_query.data.split("_")[-1]
    task = await tasks_col.find_one({"_id": task_id})
    
    if not task:
        await callback_query.answer("Task not found!", show_alert=True)
        return
    
    progress_text = "📊 **TASK PROGRESS**\n\n"
    for i, post in enumerate(task["posts"], 1):
        status = "✅" if post.get("completed") else "❌"
        progress_text += f"{status} Post {i}: {'Completed' if post.get('completed') else 'Pending'}\n"
    
    completed_count = sum(1 for post in task["posts"] if post.get("completed"))
    progress_text += f"\n**Progress:** {completed_count}/{len(task['posts'])} posts\n"
    
    if completed_count == len(task["posts"]):
        progress_text += "\n🎉 **Ready to submit!**"
    
    await callback_query.answer(progress_text, show_alert=True)

# ==================== CLICK TRACKING (Basic) ====================
# Note: Direct click tracking requires a custom URL shortener
# This is a simplified version

@app.on_message(filters.text & filters.private)
async def handle_private_links(client: Client, message: Message):
    """Detect when users send links (simulating click tracking)"""
    import re
    links = re.findall(r'https?://[^\s]+', message.text)
    
    if links and message.from_user:
        for link in links:
            await track_click(message.from_user.id, link)
            
            # Optional: Auto-check if this completes a task
            user_tasks = await tasks_col.find({
                "user_id": message.from_user.id,
                "status": "assigned"
            }).to_list(length=5)
            
            for task in user_tasks:
                all_completed = all(
                    post.get("completed", False) 
                    for post in task["posts"]
                )
                
                if all_completed:
                    await message.reply_text(
                        "🎉 **You've completed all posts!**\n\n"
                        "Go back to your task message and click "
                        "'✅ I Visited All Posts' to claim your reward."
                    )

# ==================== BOT STARTUP ====================
@app.on_chat_join_request()
async def handle_join_request(client: Client, join_request: ChatJoinRequest):
    """Auto-approve join requests if from your channels"""
    if join_request.chat.id in CHANNEL_IDS:
        await join_request.approve()

print("=" * 50)
print("🤖 TASK BOT STARTING...")
print(f"📊 Database: {DATABASE_NAME}")
print(f"📢 Monitoring {len(CHANNEL_IDS)} channels")
print(f"👤 Admin: @{ADMIN_USERNAME}")
print("=" * 50)

app.run()

