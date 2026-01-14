from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

# Create database connection and collections
client = AsyncIOMotorClient(MONGO_URL)
db = client['Character_catcher']

# Permanent channels collection
permanent_channels_collection = db["permanent_channels"]

# Other existing collections
collection = db['anime_characters']
user_totals_collection = db['user_totals']
user_collection = db["user_collection"]
safari_cooldown_collection = db['safari_cooldown_collection']
safari_users_collection = db['safari_users_collection']
group_user_totals_collection = db['group_user_total']
top_global_groups_collection = db['top_global_groups']
guild = db["guild_team"]
gban = db["gban"]
clan_collection = db['clans']
join_requests_collection = db['join_requests']
global_ban_users_collection = db['global_ban_users']
users_collection = db['user']
videos_collection = db['videos']
sales_collection = db['sales']
blocked_users_collection = db["blocked_users"]

# New collection for upload team
upload_team_collection = db["upload_team"]

# Database channel collection
database_channel_collection = db["database_channel"]

__all__ = [
    'collection', 'user_collection', 'user_totals_collection',
    'safari_cooldown_collection', 'safari_users_collection',
    'group_user_totals_collection', 'top_global_groups_collection',
    'guild', 'gban', 'clan_collection', 'join_requests_collection',
    'global_ban_users_collection', 'users_collection', 'videos_collection',
    'sales_collection', 'blocked_users_collection', 'db',
    'upload_team_collection', 'database_channel_collection',
    'permanent_channels_collection'  # Added
]
