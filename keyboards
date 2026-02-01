from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import config

def get_task_keyboard(task_id: str, posts: list):
    """Create interactive task keyboard"""
    keyboard = []
    
    for i, post in enumerate(posts, 1):
        # Create direct link to post
        channel_id = post.get("channel_id", "")
        message_id = post.get("message_id", "")
        
        # Convert channel ID for URL
        if str(channel_id).startswith("-100"):
            chat_id = str(channel_id).replace("-100", "")
            post_url = f"https://t.me/c/{chat_id}/{message_id}"
        else:
            post_url = f"https://t.me/{channel_id}/{message_id}"
        
        # Button to view post
        keyboard.append([
            InlineKeyboardButton(
                f"📰 Visit Post {i}",
                url=post_url
            )
        ])
        
        # Buttons for each link in post
        links = post.get("links", [])
        for j, link in enumerate(links[:2], 1):  # Show max 2 links per post
            keyboard.append([
                InlineKeyboardButton(
                    f"🔗 Link {j} (Post {i})",
                    url=link
                )
            ])
    
    # Progress and completion buttons
    keyboard.append([
        InlineKeyboardButton("🔄 Check Progress", callback_data=f"progress_{task_id}"),
        InlineKeyboardButton("✅ Mark Complete", callback_data=f"complete_{task_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
        InlineKeyboardButton("❌ Cancel Task", callback_data="cancel_task")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_main_menu():
    """Main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎯 Get Daily Task", callback_data="get_task")],
        [InlineKeyboardButton("📊 My Statistics", callback_data="my_stats")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [
            InlineKeyboardButton("📢 Our Channels", url="https://t.me/Capture_Talks"),
            InlineKeyboardButton("📢 Our Channel 2", url="https://t.me/BLACKCLV")
        ],
        [InlineKeyboardButton("👨‍💻 Contact Admin", url=f"https://t.me/{config.ADMIN_USERNAME}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_verification_keyboard():
    """Channel verification keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ I Joined Channel 1", url="https://t.me/Capture_Talks"),
            InlineKeyboardButton("✅ I Joined Channel 2", url="https://t.me/BLACKCLV")
        ],
        [InlineKeyboardButton("🔄 Check My Joins", callback_data="check_joins")]
    ]
    return InlineKeyboardMarkup(keyboard)
