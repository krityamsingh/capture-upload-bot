from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import random
from config import config

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(config.MONGO_URI)
        self.db = self.client[config.DB_NAME]
        
        # Collections
        self.users = self.db.users
        self.posts = self.db.posts
        self.tasks = self.db.tasks
        self.clicks = self.db.clicks
        self.user_tasks = self.db.user_tasks
    
    async def save_user(self, user_id: int, username: str = None):
        """Save or update user in database"""
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "username": username,
                "joined_at": datetime.now(),
                "last_seen": datetime.now(),
                "total_tasks": 0,
                "total_clicks": 0,
                "is_banned": False
            }},
            upsert=True
        )
    
    async def save_post(self, message):
        """Save posts from InsideAds bot"""
        if not message.from_user or not message.from_user.username:
            return
        
        if message.from_user.username.lower() == config.INSIDE_ADS_BOT.lower():
            post_data = {
                "message_id": message.id,
                "channel_id": message.chat.id,
                "date": message.date,
                "text": message.text or message.caption or "",
                "has_button": bool(message.reply_markup),
                "links": [],
                "saved_at": datetime.now(),
                "is_active": True
            }
            
            # Extract URLs from message
            import re
            if message.text:
                urls = re.findall(r'https?://[^\s]+', message.text)
                post_data["links"] = urls
            
            # Extract URLs from buttons
            if message.reply_markup:
                for row in message.reply_markup.inline_keyboard:
                    for button in row:
                        if hasattr(button, 'url') and button.url:
                            post_data["links"].append(button.url)
            
            await self.posts.update_one(
                {"message_id": message.id, "channel_id": message.chat.id},
                {"$set": post_data},
                upsert=True
            )
            
            return post_data
    
    async def get_random_posts(self, count: int = 3):
        """Get random active posts from last 24 hours"""
        yesterday = datetime.now() - timedelta(days=1)
        
        pipeline = [
            {"$match": {
                "date": {"$gte": yesterday},
                "is_active": True,
                "links": {"$ne": []}
            }},
            {"$sample": {"size": count}}
        ]
        
        posts = await self.posts.aggregate(pipeline).to_list(length=count)
        return posts
    
    async def create_user_task(self, user_id: int):
        """Create a new task for user"""
        # Check if user already has active task
        active_task = await self.user_tasks.find_one({
            "user_id": user_id,
            "status": "active"
        })
        
        if active_task:
            return active_task
        
        # Get random posts
        post_count = random.randint(
            config.MIN_POSTS_PER_TASK,
            config.MAX_POSTS_PER_TASK
        )
        posts = await self.get_random_posts(post_count)
        
        if not posts:
            return None
        
        task_posts = []
        for post in posts:
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
            "user_id": user_id,
            "posts": task_posts,
            "assigned_at": datetime.now(),
            "completed_at": None,
            "status": "active",
            "total_posts": len(task_posts),
            "completed_posts": 0,
            "task_code": f"TASK{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id}"
        }
        
        result = await self.user_tasks.insert_one(task_data)
        task_data["_id"] = result.inserted_id
        
        return task_data
    
    async def record_click(self, user_id: int, url: str, task_id: str, post_id: str):
        """Record a click from user"""
        click_data = {
            "user_id": user_id,
            "url": url,
            "task_id": task_id,
            "post_id": post_id,
            "clicked_at": datetime.now(),
            "ip_address": None,  # Would need web server for this
            "user_agent": None   # Would need web server for this
        }
        
        await self.clicks.insert_one(click_data)
        
        # Update task progress
        await self.user_tasks.update_one(
            {"_id": task_id, "posts.post_id": post_id},
            {
                "$inc": {"posts.$.clicks": 1},
                "$set": {"posts.$.completed": True}
            }
        )
        
        # Update user stats
        await self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"total_clicks": 1}}
        )
        
        return click_data
    
    async def check_task_completion(self, task_id: str):
        """Check if all posts in task are completed"""
        task = await self.user_tasks.find_one({"_id": task_id})
        if not task:
            return False
        
        all_completed = all(post.get("completed", False) for post in task["posts"])
        
        if all_completed:
            await self.user_tasks.update_one(
                {"_id": task_id},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.now()
                }}
            )
            
            # Update user stats
            await self.users.update_one(
                {"user_id": task["user_id"]},
                {"$inc": {"total_tasks": 1}}
            )
        
        return all_completed

db = Database()
