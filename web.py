# web.py - SIMPLE WEB SERVER
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Terabox Bot is running!"

@app.route('/ping')
def ping():
    return "pong"

@app.route('/health')
def health():
    return "healthy"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
