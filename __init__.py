from pyrogram import Client as PyrogramClient
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

# Import from config
try:
    from config import API_ID as api_id, API_HASH as api_hash, BOT_TOKEN as TOKEN, MONGO_URL
except ImportError:
    api_id = 26676741
    api_hash = "6fbc29f23c15bdb0c7fbbefe65c9193a"
    TOKEN = "8400868432:AAELK0oQXqxXlZJbusLn2QsgIwYkG6-cqss"
    MONGO_URL = "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0"

bot_start_time = datetime.now(timezone.utc)

class Client(PyrogramClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def resolve_peer(self, id):
        return await super().resolve_peer(id)


Grabberu = Client(
    "Grabber",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=TOKEN
)
app = Grabberu

# Database connection
client = AsyncIOMotorClient(MONGO_URL)
db = client['Character_catcher']

# Collections – only those needed for upload bot
collection = db['anime_characters']
upload_team_collection = db["upload_team"]
database_channel_collection = db["database_channel"]
counters_collection = db["counters"]

# For backward compatibility you can add aliases, but they are not used.
user_totals_collection = db['user_totals']
user_collection = db["user_collection"]
# ... etc (if needed)
