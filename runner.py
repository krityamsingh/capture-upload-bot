# runner.py - Simple runner
import os
import sys
import time

print("=" * 50)
print("Terabox Downloader Bot")
print("With Cookies Support")
print("=" * 50)

# Check environment
print(f"API_ID: {os.environ.get('API_ID', 'Not set')}")
print(f"BOT_TOKEN: {os.environ.get('BOT_TOKEN', 'Not set')[:10]}...")

# Create cookies directory
os.makedirs("cookies", exist_ok=True)

# Start the bot
print("\nStarting bot...")
os.execv(sys.executable, [sys.executable, "bot.py"])
