from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, List, Tuple, Optional

class UploadKeyboards:
    # New rarity system with emojis
    RARITIES = {
        "Common": "🔴",
        "Uncommon": "🔵", 
        "Rare": "🟠",
        "Epic": "⚪️",
        "Legendary": "🟡",
        "Limited": "🔮",
        "Premium": "🫧",
        "Exotic": "🏵️",
        "Animated": "⚜️",
        "Celebrity": "🌼",
        "Crystal": "🎐",
        "Neon": "🍹",
        "Supreme": "🧿",
        "Thundra": "⚡️",
        "Galvoria": "🛸"
    }
    
    @staticmethod
    def get_rarity_keyboard(session_id: str) -> InlineKeyboardMarkup:
        """Get rarity selection keyboard with 3 columns"""
        buttons = []
        
        # Create rows of 3 buttons each
        rarities_list = list(UploadKeyboards.RARITIES.items())
        
        # First 5 rows (15 buttons in total)
        for i in range(0, len(rarities_list), 3):
            row = []
            for rarity, emoji in rarities_list[i:i+3]:
                row.append(InlineKeyboardButton(
                    f"{emoji} {rarity}",
                    callback_data=f"rarity:{session_id}:{rarity}"
                ))
            buttons.append(row)
            
        # Cancel button
        buttons.append([
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{session_id}")
        ])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def get_confirmation_keyboard(session_id: str) -> InlineKeyboardMarkup:
        """Get confirmation keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm Upload", callback_data=f"confirm:{session_id}")
            ],
            [
                InlineKeyboardButton("✏️ Edit Rarity", callback_data=f"back:{session_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{session_id}")
            ]
        ])
