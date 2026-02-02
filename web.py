# web.py - Simple web server
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Terabox Public Downloader Bot",
        "message": "Free Terabox video downloader for everyone!",
        "features": [
            "No registration required",
            "Works with public links",
            "Direct DM delivery",
            "Free forever"
        ]
    })

@app.route('/ping')
def ping():
    return "pong"

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
