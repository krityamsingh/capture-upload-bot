# Bot Configuration
BOT_TOKEN=your_bot_token_here

# Database Configuration
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=upload_bot
REDIS_URL=redis://localhost:6379

# Security & Administration
ADMIN_IDS=123456789,987654321
LOG_CHAT_ID=-1001234567890
CHANNEL_ID=-1001234567890

# Upload Limits
MAX_FILE_SIZE=209715200  # 200MB in bytes
API_RATE_LIMIT=30
SESSION_TIMEOUT=300

# Features
ALLOWED_TYPES=["document", "photo", "video", "audio", "voice", "video_note", "sticker", "animation"]
THUMBNAIL_SIZE=320,240

# Performance
BACKUP_INTERVAL=3600
CACHE_TTL=300
MAX_CONNECTIONS=100
