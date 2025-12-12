# ==================== UTILS/KEYBOARDS.PY ====================
# utils/keyboards.py - UNCHANGED
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import config

class Keyboards:
    """Inline keyboard generators for the bot"""
    
    @staticmethod
    def get_rarity_keyboard() -> InlineKeyboardMarkup:
        """Generate rarity selection keyboard"""
        buttons = []
        row = []
        
        for rarity_id, rarity_name in config.RARITY_MAP.items():
            row.append(InlineKeyboardButton(
                rarity_name, 
                callback_data=f"rarity_{rarity_id}"
            ))
            if len(row) == 2:  # 2 buttons per row
                buttons.append(row)
                row = []
        
        if row:  # Add remaining buttons
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_start")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def get_limited_subtypes_keyboard() -> InlineKeyboardMarkup:
        """Generate Limited Edition subtypes keyboard"""
        buttons = []
        row = []
        
        for subtype_key, subtype_name in config.LIMITED_SUBTYPES.items():
            row.append(InlineKeyboardButton(
                subtype_name,
                callback_data=f"subrarity_limited_{subtype_key}"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_rarity")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def get_celestial_subtypes_keyboard() -> InlineKeyboardMarkup:
        """Generate Celestial subtypes keyboard"""
        buttons = []
        row = []
        
        for subtype_key, subtype_name in config.CELESTIAL_SUBTYPES.items():
            row.append(InlineKeyboardButton(
                subtype_name,
                callback_data=f"subrarity_celestial_{subtype_key}"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_rarity")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def get_confirmation_keyboard() -> InlineKeyboardMarkup:
        """Generate confirmation keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data="confirm_upload"),
                InlineKeyboardButton("❌ Reject", callback_data="reject_upload")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="back_subrarity")]
        ])
    
    @staticmethod
    def get_main_menu_keyboard() -> InlineKeyboardMarkup:
        """Generate main menu keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Add Character", callback_data="add_char"),
                InlineKeyboardButton("📊 Status", callback_data="status")
            ],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ])

keyboards = Keyboards()