import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
API_ID = int(os.getenv("API_ID", 26676741))
API_HASH = os.getenv("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8400868432:AAELK0oQXqxXlZJbusLn2QsgIwYkG6-cqss")
TOKEN = BOT_TOKEN

# Database Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0")

# Catbox.moe Configuration
CATBOX_API_KEY = os.getenv("CATBOX_API_KEY", "")

# Owner Configuration
OWNER_ID = int(os.getenv("OWNER_ID", 8301883098))

# Permanent Broadcast Channels (These will always be used)
PERMANENT_BROADCAST_CHANNELS = [-1003364380308, -1003663151888]

# Upload Settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.webp', '.webm']

# Catbox Settings
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"
CATBOX_TIMEOUT = 30  # seconds
CATBOX_MAX_RETRIES = 3

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

