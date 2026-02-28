import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
API_ID = 26676741
API_HASH = "6fbc29f23c15bdb0c7fbbefe65c9193a"
BOT_TOKEN = "8400868432:AAELK0oQXqxXlZJbusLn2QsgIwYkG6-cqss"
TOKEN = BOT_TOKEN

# Database Configuration
MONGO_URL = "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0"

# Catbox.moe Configuration
CATBOX_API_KEY = ""

# Owner Configuration
OWNER_IDS = [6118760915, 7738726467, 7416365439, 8389069484, 8301883098, 7251602666, 8485415780]
OWNER_ID = OWNER_IDS[0]

# Upload Settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.webp', '.webm']

# Catbox Settings
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"
CATBOX_TIMEOUT = 30  # seconds
CATBOX_MAX_RETRIES = 3

# Logging Configuration
LOG_LEVEL = "INFO"

# Fixed database channel (no longer set via command)
DATABASE_CHANNEL = -1003869604435
