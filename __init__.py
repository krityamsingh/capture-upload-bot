from pyrogram import Client as PyrogramClient
from telegram.ext import Application
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Import from config
try:
    from config import API_ID as api_id, API_HASH as api_hash, BOT_TOKEN as TOKEN, MONGO_URL, PERMANENT_BROADCAST_CHANNELS
except ImportError:
    # Fallback values
    api_id = 26676741
    api_hash = "6fbc29f23c15bdb0c7fbbefe65c9193a"
    TOKEN = "8400868432:AAELK0oQXqxXlZJbusLn2QsgIwYkG6-cqss"
    MONGO_URL = "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0"
    PERMANENT_BROADCAST_CHANNELS = [-1003364380308, -1003663151888]

bot_start_time = datetime.now()

class Client(PyrogramClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def resolve_peer(self, id):
        return await super().resolve_peer(id)


application = Application.builder().token(TOKEN).build()
Grabberu = Client(
    "Grabber",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=TOKEN)
app = Grabberu
client = AsyncIOMotorClient(MONGO_URL)
db = client['Character_catcher']

# Permanent broadcast channels collection (stores which channels are working)
permanent_channels_collection = db["permanent_channels"]

# Other existing collections
collection = db['anime_characters']
user_totals_collection = db['user_totals']
user_collection = db["user_collection"]
joke_collection = db["joke_collection"]
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
like_dislike_collection = db["like_dislike_data"]
user_votes_collection = db["user_votes"]
add_coins = db["add_coins"]
add_character = db["add_character"]
get_user_data = db["get_user_data"]
add = db["add"]
store_items = db["store_items"]
check_vip_status = db["check_vip_status"]
auction = db["auction"]
global_mute_users_collection = db["global_mute_users_collection"]
monster_collection = db["monster_collection"]
action_history_collection = db["action_history_collection"]
gang_collection = db["gang_collection"]
mission_collection = db["mission_collection"]
chain_collection = db["chain_collection"]
word_collection = db["words"]
fsub_collection = db["fsub_collection"]
chat_auctions = db["chat_auctions"]
active_auctions = db["active_auctions"]
backup_collection = db["backup_collection"]
clan_war_collection = db["clan_war_collection"]
giveaway_collection = db["giveaway_collection"]

# New collection for upload team
upload_team_collection = db["upload_team"]

# Database channel collections
database_channel_collection = db["database_channel"]
