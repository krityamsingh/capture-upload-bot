from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class UploadKeyboards:
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
        buttons = []
        rarities_list = list(UploadKeyboards.RARITIES.items())

        for i in range(0, len(rarities_list), 3):
            row = []
            for rarity, emoji in rarities_list[i:i+3]:
                row.append(InlineKeyboardButton(
                    f"{emoji} {rarity}",
                    callback_data=f"rarity:{session_id}:{rarity}"
                ))
            buttons.append(row)

        buttons.append([
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{session_id}")
        ])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_confirmation_keyboard(session_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm Upload", callback_data=f"confirm:{session_id}")
            ],
            [
                InlineKeyboardButton("✏️ Edit Rarity", callback_data=f"back:{session_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{session_id}")
            ]
        ])
