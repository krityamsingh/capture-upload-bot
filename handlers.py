from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from config import config
from database import db
from keyboards import get_task_keyboard, get_main_menu, get_verification_keyboard
from utils import (
    check_channel_membership, 
    delete_user_message_with_warning,
    format_task_message,
    notify_admin
)
import re

async def handle_start(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user
    await db.save_user(user.id, user.username)
    
    welcome_text = f"""
🤖 **Welcome to Ad Tracker Bot!** 

**👤 Hello,** @{user.username or user.first_name}

💰 **Earn money by completing simple tasks:**
1. Join our channels
2. Visit posts from @{config.INSIDE_ADS_BOT}
3. Click on ad links
4. Get paid!

📊 **Your Benefits:**
• Earn per click
• Daily tasks available
• Instant payments
• Simple process

👇 **Get started with the buttons below!**
"""
    
    await message.reply_text(
        welcome_text,
        reply_markup=get_main_menu()
    )

async def handle_task_command(client: Client, message: Message):
    """Handle /task command"""
    user = message.from_user
    
    # Check channel membership
    is_member = await check_channel_membership(client, user.id)
    
    if not is_member:
        warning_text = f"""
❌ **CHANNEL JOIN REQUIRED**

👤 @{user.username or user.id}

You must join both channels before getting tasks:

1. **Channel 1:** https://t.me/Capture_Talks
2. **Channel 2:** https://t.me/BLACKCLV

👇 **Click the buttons below to join:**
"""
        await message.reply_text(
            warning_text,
            reply_markup=get_verification_keyboard()
        )
        return
    
    # Create task for user
    task = await db.create_user_task(user.id)
    
    if not task:
        await message.reply_text(
            "📭 **No posts available at the moment.**\n\n"
            "Please check back in a few hours when new ads are posted."
        )
        return
    
    # Send task with interactive keyboard
    await message.reply_text(
        format_task_message(task, user),
        reply_markup=get_task_keyboard(str(task["_id"]), task["posts"]),
        disable_web_page_preview=True
    )

async def handle_group_message(client: Client, message: Message):
    """Handle group messages - enforce channel joining"""
    if not config.GROUP_ID or message.chat.id != config.GROUP_ID:
        return
    
    # Skip if message is from bot or admin
    if message.from_user.is_bot:
        return
    
    # Check channel membership
    is_member = await check_channel_membership(client, message.from_user.id)
    
    if not is_member:
        warning_text = f"""
⚠️ **CHANNEL JOIN REQUIRED**

👤 **@{message.from_user.username or message.from_user.id}**

Your message was deleted because you haven't joined our channels.

**Join these channels first:**
1. https://t.me/Capture_Talks
2. https://t.me/BLACKCLV

After joining, you can:
• Send messages in this group
• Use /task to earn money
• Get daily rewards
"""
        
        await delete_user_message_with_warning(client, message, warning_text)

async def handle_channel_post(client: Client, message: Message):
    """Monitor and save posts from InsideAds bot"""
    if message.chat.id not in config.CHANNEL_IDS:
        return
    
    saved_post = await db.save_post(message)
    if saved_post:
        print(f"✅ Saved post from {config.INSIDE_ADS_BOT}: {message.id}")

async def handle_callback_query(client: Client, callback_query: CallbackQuery):
    """Handle inline keyboard button clicks"""
    user = callback_query.from_user
    data = callback_query.data
    
    await callback_query.answer()
    
    if data == "get_task":
        # Simulate /task command
        message = Message(
            id=callback_query.message.id,
            chat=callback_query.message.chat,
            from_user=user,
            text="/task"
        )
        await handle_task_command(client, message)
        await callback_query.message.delete()
    
    elif data == "my_stats":
        # Get user statistics
        user_data = await db.users.find_one({"user_id": user.id})
        
        if user_data:
            stats_text = f"""
📊 **YOUR STATISTICS**

👤 **User:** @{user.username or user.id}
🆔 **ID:** `{user.id}`
📅 **Joined:** {user_data.get('joined_at', 'N/A').strftime('%Y-%m-%d')}

💰 **Earnings Summary:**
• Total Tasks: {user_data.get('total_tasks', 0)}
• Total Clicks: {user_data.get('total_clicks', 0)}
• Estimated Earnings: ${user_data.get('total_clicks', 0) * 0.01}

🏆 **Rank:** #{user_data.get('rank', 'N/A')}
⭐ **Level:** {min(user_data.get('total_tasks', 0) // 10 + 1, 10)}

📈 **Today's Progress:**
• Tasks: 0/3 (Daily limit)
• Clicks: {user_data.get('today_clicks', 0)}/50
"""
        else:
            stats_text = "No data found. Please use /start first."
        
        await callback_query.message.edit_text(
            stats_text,
            reply_markup=get_main_menu()
        )
    
    elif data.startswith("progress_"):
        # Check task progress
        task_id = data.replace("progress_", "")
        task = await db.user_tasks.find_one({"_id": task_id})
        
        if task and task["user_id"] == user.id:
            completed = sum(1 for post in task["posts"] if post.get("completed", False))
            total = len(task["posts"])
            
            progress_text = f"""
📊 **TASK PROGRESS**

**Task ID:** `{task.get('task_code', 'N/A')}`
**Status:** {task.get('status', 'active').upper()}
**Progress:** {completed}/{total} posts

"""
            
            for i, post in enumerate(task["posts"], 1):
                status = "✅" if post.get("completed") else "❌"
                progress_text += f"\n{status} **Post {i}:**"
                progress_text += f" {post.get('clicks', 0)}/{len(post.get('links', []))} clicks"
            
            if completed == total:
                progress_text += "\n\n🎉 **All posts completed!**\nClick '✅ Mark Complete' to finish."
            else:
                progress_text += f"\n\n📝 **Remaining:** {total - completed} posts"
            
            await callback_query.answer(progress_text, show_alert=True)
    
    elif data.startswith("complete_"):
        # Mark task as complete
        task_id = data.replace("complete_", "")
        
        # Check if all posts are completed
        is_complete = await db.check_task_completion(task_id)
        
        if is_complete:
            task = await db.user_tasks.find_one({"_id": task_id})
            
            # Notify admin
            await notify_admin(client, user, task)
            
            completion_text = f"""
✅ **TASK COMPLETED SUCCESSFULLY!**

**👤 User:** @{user.username or user.id}
**📝 Task ID:** `{task.get('task_code', 'N/A')}`
**📊 Posts Completed:** {len(task.get('posts', []))}
**💰 Estimated Earnings:** ${len(task.get('posts', [])) * 0.50}

🏆 **CONGRATULATIONS!**

**Next Steps:**
1. Tag @{config.ADMIN_USERNAME} in this group
2. Send your wallet address
3. Wait for payment confirmation
4. Come back tomorrow for more tasks!

**📢 Important:** Payments are processed within 24 hours.
"""
            
            await callback_query.message.edit_text(
                completion_text,
                reply_markup=get_main_menu()
            )
        else:
            await callback_query.answer(
                "❌ Not all posts are completed yet!",
                show_alert=True
            )
    
    elif data == "check_joins":
        # Check channel membership
        is_member = await check_channel_membership(client, user.id)
        
        if is_member:
            await callback_query.answer(
                "✅ You have joined both channels!",
                show_alert=True
            )
        else:
            await callback_query.answer(
                "❌ You haven't joined all channels!",
                show_alert=True
            )
    
    elif data == "leaderboard":
        # Show top users
        top_users = await db.users.find(
            {"total_tasks": {"$gt": 0}}
        ).sort("total_tasks", -1).limit(10).to_list(length=10)
        
        leaderboard_text = "🏆 **TOP EARNERS LEADERBOARD**\n\n"
        
        for i, user_data in enumerate(top_users, 1):
            username = user_data.get("username", f"User{user_data['user_id']}")
            tasks = user_data.get("total_tasks", 0)
            clicks = user_data.get("total_clicks", 0)
            earnings = clicks * 0.01
            
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            
            leaderboard_text += f"{medal} **@{username}**\n"
            leaderboard_text += f"   Tasks: {tasks} | Clicks: {clicks} | Earned: ${earnings:.2f}\n\n"
        
        leaderboard_text += "\n💰 **Earn more by completing daily tasks!**"
        
        await callback_query.message.edit_text(
            leaderboard_text,
            reply_markup=get_main_menu()
        )
