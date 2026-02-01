# runner.py - SIMPLE RUNNER THAT WORKS
import os
import sys
import subprocess
import time
import signal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bot():
    """Run the bot directly"""
    logger.info("Starting bot process...")
    
    # Run bot in current process
    try:
        import bot
        import asyncio
        
        # Run the bot
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        # Try alternative approach
        os.execv(sys.executable, [sys.executable, "bot.py"])

def run_web():
    """Run web server"""
    logger.info("Starting web server...")
    subprocess.Popen([sys.executable, "web.py"])

if __name__ == "__main__":
    print("=" * 50)
    print("Terabox DM Bot Runner")
    print("=" * 50)
    
    # Start web server
    run_web()
    
    # Wait a bit for web server to start
    time.sleep(2)
    
    # Start bot
    run_bot()
