# start.sh
#!/bin/bash

echo "=== Terabox Bot Startup ==="
echo "Checking environment variables..."

# Check required variables
if [ -z "$API_ID" ] || [ -z "$API_HASH" ] || [ -z "$BOT_TOKEN" ]; then
    echo "ERROR: Missing required environment variables!"
    echo "Please set: API_ID, API_HASH, BOT_TOKEN"
    exit 1
fi

echo "Environment check passed."
echo "Starting bot..."

# Start the bot
python bot.py
