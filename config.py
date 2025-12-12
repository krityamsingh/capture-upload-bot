import os
from typing import Dict, Any


class Config:
    """Central configuration for the Telegram bot"""

    # ───────────────────────────
    # Telegram API Credentials
    # ───────────────────────────
    API_ID = int(os.getenv("API_ID", 26676741))
    API_HASH = os.getenv("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
    BOT_TOKEN = os.getenv(
        "BOT_TOKEN",
        "8496337458:AAF7ORldWpN-C6hpzSDt1bPCOeGVxfbU4qg"
    )

    # ───────────────────────────
    # MongoDB Configuration
    # ───────────────────────────
    MONGO_URI = os.getenv(
        "MONGO_URI",
        "mongodb+srv://erenxironman09:erenxironman09@catcherbot.koejwre.mongodb.net/?appName=catcherbot"
    )
    DATABASE_NAME = os.getenv("DATABASE_NAME", "telegram_upload_bot")

    # ───────────────────────────
    # Bot Owner / Admin
    # ───────────────────────────
    OWNER_ID = int(os.getenv("OWNER_ID", 7878477646))

    # ───────────────────────────
    # Upload & Performance Limits
    # ───────────────────────────
    UPLOAD_TIMEOUT = 60                  # seconds
    MAX_FILE_SIZE = 50 * 1024 * 1024     # 50 MB

    # Mass / Batch Processing
    MAX_BATCH_SIZE = 50
    BATCH_PROCESSING_TIMEOUT = 300       # seconds

    # ───────────────────────────
    # RARITY SYSTEM (UPDATED)
    # ───────────────────────────
    RARITY_MAP = {
        1: "⚪ Common",
        2: "🟢 Uncommon",
        3: "🔴 Rare",
        4: "🟡 Legendary",
        5: "🎐 Limited Edition",
        6: "💎 Premium",
        7: "🥵 Exotic",
        8: "🎬 Animated",
        9: "🌩️ Thundra",
        10: "☄️ Galvoria",
        11: "🌈 Neon",
        12: "🛡️ Supreme",
        13: "🔮 Crystal",
        14: "🎤 Celebrity",
    }

    # ───────────────────────────
    # Rarities that support sub-types
    # ───────────────────────────
    RARITIES_WITH_SUBTYPES = [5, 6, 7, 12, 13, 14]

    # ───────────────────────────
    # Subtype Groups
    # ───────────────────────────
    LIMITED_SUBTYPES = {
        "valentine": "💝 Valentine",
        "christmas": "🎄 Christmas",
        "halloween": "🎃 Halloween",
        "summer": "🏖️ Summer",
        "winter": "❄️ Winter",
        "newyear": "🎆 New Year",
        "wedding": "💒 Wedding",
    }

    PREMIUM_SUBTYPES = {
        "gold": "🥇 Gold",
        "diamond": "💠 Diamond",
        "royal": "👑 Royal",
        "dark": "🌑 Dark",
    }

    SUPREME_SUBTYPES = {
        "mythic": "🛡️ Mythic",
        "ancient": "📜 Ancient",
        "celestial": "✨ Celestial",
    }

    CELEBRITY_SUBTYPES = {
        "phyco": "🎭 phyco",
        "singer": "🎤 Singer",
        "power": "🏆 power",
        "influencer": "📸 Influencer",
    }

    # ───────────────────────────
    # Auto Emoji Mapping (for captions)
    # ───────────────────────────
    SUBRARITY_EMOJI_MAP = {
        # Limited
        "valentine": "💝",
        "christmas": "🎄",
        "halloween": "🎃",
        "summer": "🏖️",
        "winter": "❄️",
        "newyear": "🎆",
        "wedding": "💒",

        # Premium / Exotic
        "gold": "🥇",
        "diamond": "💠",
        "royal": "👑",
        "dark": "🌑",

        # Supreme / Crystal
        "mythic": "🛡️",
        "ancient": "📜",
        "celestial": "✨",

        # Celebrity
        "actor": "🎭",
        "singer": "🎤",
        "athlete": "🏆",
        "influencer": "📸",
    }


# Export config instance
config = Config()
