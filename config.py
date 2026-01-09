import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
API_ID = int(os.getenv("API_ID", 26676741))
API_HASH = os.getenv("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8440461627:AAFgko_wvAT-jK1lq2UBMtsnJejfcm-8ugo")
TOKEN = BOT_TOKEN

# Database Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0")

# Catbox.moe Configuration (Required for fast uploads)
# Optional API key for account uploads (get from: https://catbox.moe/user/api.php)
CATBOX_API_KEY = os.getenv("CATBOX_API_KEY", "")
# For anonymous uploads, leave empty

# Owner Configuration (Initial owner will be set on first run)
OWNER_ID = int(os.getenv("OWNER_ID", 8496760733))

# Upload Settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.webp', '.webm']

# Catbox Settings
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"
CATBOX_TIMEOUT = 30  # seconds
CATBOX_MAX_RETRIES = 3

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
