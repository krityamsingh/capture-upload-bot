# main.py - RUN BOTH BOT AND WEB SERVER
import subprocess
import sys
import os
import time
from threading import Thread

def run_bot():
    """Run the Telegram bot"""
    print("Starting Telegram bot...")
    subprocess.run([sys.executable, "bot.py"])

def run_web():
    """Run the web server"""
    print("Starting web server...")
    subprocess.run([sys.executable, "web.py"])

if __name__ == "__main__":
    print("=== Terabox Downloader Bot ===")
    print(f"API_ID: {os.environ.get('API_ID', 'Not set')}")
    print(f"BOT_TOKEN: {os.environ.get('BOT_TOKEN', 'Not set')[:10]}...")
    
    # Run web server in background
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()
    
    # Give web server time to start
    time.sleep(2)
    
    # Run bot in foreground
    run_bot()
