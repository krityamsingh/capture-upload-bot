from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client['Character_catcher']

# Main character collection
collection = db['anime_characters']

# Upload team collection
upload_team_collection = db["upload_team"]

# Database channel collection (single channel)
database_channel_collection = db["database_channel"]

# Counter for character IDs
counters_collection = db["counters"]

# Keep other collections if needed by other parts, but for upload bot we only need above.
# If you still need others for compatibility, you can add them, but they are not used.
