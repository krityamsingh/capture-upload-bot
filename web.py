#!/usr/bin/env python3
from flask import Flask, jsonify
import threading
import time
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Terabox Downloader Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                padding: 30px;
                border-radius: 10px;
                backdrop-filter: blur(10px);
            }
            h1 {
                color: white;
                text-align: center;
            }
            .status {
                background: rgba(0, 255, 0, 0.2);
                padding: 10px;
                border-radius: 5px;
                margin: 20px 0;
            }
            code {
                background: rgba(0, 0, 0, 0.3);
                padding: 2px 5px;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Terabox Downloader Bot</h1>
            <div class="status">
                ✅ <strong>Status: Online</strong>
            </div>
            <p>This bot is running on Heroku and ready to download videos from:</p>
            <ul>
                <li>terabox.com</li>
                <li>1024tera.com</li>
                <li>terafileshare.com</li>
            </ul>
            <p>To use the bot, search for it on Telegram and send a Terabox link.</p>
            <p><strong>Bot will auto-restart if it crashes.</strong></p>
            <hr>
            <p><small>Last checked: <span id="time"></span></small></p>
        </div>
        <script>
            document.getElementById('time').textContent = new Date().toLocaleString();
            // Auto-refresh every 5 minutes to keep dyno awake
            setInterval(() => {
                fetch('/ping');
            }, 300000);
        </script>
    </body>
    </html>
    """

@app.route('/ping')
def ping():
    return jsonify({"status": "ok", "time": time.time()})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": time.time()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
