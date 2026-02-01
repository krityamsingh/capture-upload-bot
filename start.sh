#!/bin/bash

echo "Starting Terabox Downloader Bot..."

# Create necessary directories
mkdir -p downloads
mkdir -p logs

# Check if required environment variables are set
if [ -z "$API_ID" ] || [ -z "$API_HASH" ] || [ -z "$BOT_TOKEN" ]; then
    echo "Error: Missing required environment variables!"
    echo "Please set API_ID, API_HASH, and BOT_TOKEN"
    exit 1
fi

echo "Environment variables check passed."

# Start the bot in background
python bot.py &
BOT_PID=$!

# Start the web server
python web.py &
WEB_PID=$!

echo "Bot PID: $BOT_PID"
echo "Web PID: $WEB_PID"

# Keep script running
wait $BOT_PID $WEB_PID
