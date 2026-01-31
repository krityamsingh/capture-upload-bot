import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram API
    API_ID = 26676741
    API_HASH = "6fbc29f23c15bdb0c7fbbefe65c9193a"
    BOT_TOKEN = "8552100143:AAGMjxMfkvoXGTe-PHeRAPYGy-RvHonm7vk"
    
    # MongoDB - CHANGE PASSWORD IMMEDIATELY!
    MONGO_URI = "mongodb+srv://Capture:capture@cluster0.7jqepnf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    DB_NAME = "ad_tracking_bot"
    
    # Channel and Group IDs
    CHANNEL_IDS = [-1003430763556, -1002769749639]  # Your channels
    GROUP_ID = None  # ⚠️ SET YOUR GROUP ID HERE (e.g., -1001234567890)
    
    # Bot Settings
    INSIDE_ADS_BOT = "InsideAds_bot"
    ADMIN_USERNAME = "rajputanaxironman"
    
    # Task Settings
    MIN_POSTS_PER_TASK = 2
    MAX_POSTS_PER_TASK = 3
    
    # Security
    MAX_ATTEMPTS = 3
    
config = Config()
