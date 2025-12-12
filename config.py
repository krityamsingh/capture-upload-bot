# config.py - UNCHANGED
import os
from typing import Dict, Any

class Config:
    """Configuration class for bot settings"""
    
    # Telegram API credentials
    API_ID = int(os.getenv("API_ID", 26676741))
    API_HASH = os.getenv("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8496337458:AAF7ORldWpN-C6hpzSDt1bPCOeGVxfbU4qg")
    
    # MongoDB configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://erenxironman09:erenxironman09@catcherbot.koejwre.mongodb.net/?appName=catcherbot")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "telegram_upload_bot")
    
    # Bot owner ID (for admin commands)
    OWNER_ID = int(os.getenv("OWNER_ID", 8496760733))
    
    # Upload service configuration
    UPLOAD_TIMEOUT = 60  # Reduced from 300 to 60 seconds for faster timeout
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max file size
    
    # Mass upload configuration
    MAX_BATCH_SIZE = 50  # Maximum characters per batch
    BATCH_PROCESSING_TIMEOUT = 300  # 5 minutes per batch
    
    # Rarity mappings
    RARITY_MAP = {
        1: "⚪️ Common",
        2: "🟠 Rare", 
        3: "🟡 Legendary",
        4: "💮 Exclusive",
        5: "🔮 Limited Edition",
        6: "✨ Celestial",
        7: "👑 Eternal",
        8: "🎥 Cinematic",
        9: "🪔 Diwali",
    }
    
    LIMITED_SUBTYPES = {
        "valentine": "💝 Valentine",
        "christmas": "🎄 Christmas", 
        "halloween": "🎃 Halloween",
        "summer": "🏖️ Summer",
        "winter": "❄️ Winter",
        "basketball": "🏀 Basketball",
        "police": "👮‍♀️ Police",
        "newyear": "🎆 New Year",
        "easter": "🐰 Easter",
        "wedding": "💒 Wedding",
        "karate": "🥋 Karate",
    }
    
    CELESTIAL_SUBTYPES = {
        "dragonic": "🐉 Dragonic",
        "egypt": "🏜 Egypt",
        "special": "🎗 Special",
        "nun": "🌑 Nun",
        "viking": "🛡 Viking",
        "demon": "🃏 Demon",
        "nurse": "💊 Nurse",
        "cake": "🍰 Cake",
        "monster": "🍾 Monster",
    }
    
    # Subrarity to emoji mapping for auto-emoji system
    SUBRARITY_EMOJI_MAP = {
        "valentine": "💝",
        "christmas": "🎄", 
        "halloween": "🎃",
        "summer": "🏖️",
        "winter": "❄️",
        "basketball": "🏀",
        "police": "👮‍♀️",
        "newyear": "🎆",
        "easter": "🐰",
        "wedding": "💒",
        "karate": "🥋",
        "dragonic": "🐉",
        "egypt": "🏜",
        "special": "🎗",
        "nun": "🌑",
        "viking": "🛡",
        "demon": "🃏",
        "nurse": "💊",
        "cake": "🍰",
        "monster": "🍾",
    }
    
    # Rarities that have sub-types
    RARITIES_WITH_SUBTYPES = [5, 6]  # Limited Edition and Celestial


config = Config()

