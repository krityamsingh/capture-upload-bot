from pyrogram import Client
from pyrogram.types import User
from config import config
import asyncio

async def check_channel_membership(client: Client, user_id: int) -> bool:
    """Check if user has joined all required channels"""
    try:
        for channel_id in config.CHANNEL_IDS:
            try:
                member = await client.get_chat_member(channel_id, user_id)
                if member.status in ["left", "kicked", "banned"]:
                    return False
            except Exception as e:
                print(f"Error checking membership: {e}")
                return False
        return True
    except Exception as e:
        print(f"Error in check_channel_membership: {e}")
        return False

async def delete_user_message_with_warning(client: Client, message, warning_text: str):
    """Delete user message and send warning"""
    try:
        # Delete user's message
        await message.delete()
        
        # Send warning
        warning = await message.reply_text(
            warning_text,
            reply_to_message_id=message.id
        )
        
        # Delete warning after 10 seconds
        await asyncio.sleep(10)
        await warning.delete()
        
    except Exception as e:
        print(f"Error in delete warning: {e}")

def format_task_message(task: dict, user: User) -> str:
    """Format task message with emojis"""
    posts_count = len(task.get("posts", []))
    
    message = f"""
🎯 **DAILY TASK ASSIGNED**

**👤 User:** @{user.username or user.id}
**📝 Task ID:** `{task.get('task_code', 'N/A')}`
**📊 Posts to complete:** {posts_count}
**⏰ Assigned:** {task.get('assigned_at').strftime('%Y-%m-%d %H:%M')}

📋 **INSTRUCTIONS:**
1. Click on **"Visit Post X"** buttons to open each post
2. Click on **ALL links** inside each post
3. After visiting ALL posts, click **"✅ Mark Complete"**
4. Tag @{config.ADMIN_USERNAME} for your reward

⚠️ **IMPORTANT:**
• You must join both channels first
• Click ALL links in each post for verification
• Task expires in 24 hours
• Fraud detection is active

💰 **Earnings per task:** ${posts_count * 0.50} (estimated)
"""
    return message

async def notify_admin(client: Client, user: User, task: dict):
    """Send notification to admin about completed task"""
    try:
        admin_message = f"""
🎉 **TASK COMPLETED - PAYMENT REQUIRED**

**👤 User:** @{user.username or 'N/A'}
**🆔 User ID:** `{user.id}`
**📝 Task ID:** `{task.get('task_code', 'N/A')}`
**📊 Posts completed:** {len(task.get('posts', []))}
**⏰ Completed at:** {task.get('completed_at', 'N/A')}
**💰 Estimated earnings:** ${len(task.get('posts', [])) * 0.50}

**📋 Task Details:**
"""
        
        # Add post details
        for i, post in enumerate(task.get("posts", []), 1):
            admin_message += f"\n**Post {i}:**"
            admin_message += f"\n• Clicks: {post.get('clicks', 0)}"
            admin_message += f"\n• Links: {len(post.get('links', []))}"
        
        admin_message += f"\n\n**Action Required:**"
        admin_message += f"\nPlease send reward to: @{config.ADMIN_USERNAME}"
        admin_message += f"\n\n**User Contact:** @{user.username or 'No username'}"
        
        # Send to first channel (as admin notification)
        await client.send_message(
            chat_id=config.CHANNEL_IDS[0],
            text=admin_message
        )
        
    except Exception as e:
        print(f"Error notifying admin: {e}")
