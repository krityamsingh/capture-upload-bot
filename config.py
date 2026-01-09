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

# PixelDrain Configuration (Required)
# Get your API key from: https://pixeldrain.com/user/api_keys
# Format: empty username, API key as password in Basic Auth
PIXELDRAIN_API_KEY = os.getenv("PIXELDRAIN_API_KEY", "571c4355-220d-4695-8863-97d927e37571")

# Owner Configuration (Initial owner will be set on first run)
OWNER_ID = int(os.getenv("OWNER_ID", 8496760733))

# Upload Settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi']

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")