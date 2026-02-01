# start.py - Simple starter
import subprocess
import sys
import os
import time

print("=" * 50)
print("Terabox DM Bot - Starting...")
print("=" * 50)

# Check environment variables
required_vars = ["API_ID", "API_HASH", "BOT_TOKEN"]
for var in required_vars:
    if not os.environ.get(var):
        print(f"❌ Missing environment variable: {var}")
        sys.exit(1)

print("✅ Environment variables check passed")

# Start the bot
print("🚀 Starting Telegram bot...")
subprocess.run([sys.executable, "bot.py"])
