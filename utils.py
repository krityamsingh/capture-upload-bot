import re
import random
import string
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from bson import ObjectId
from database import collection, upload_team_collection, database_channel_collection
import os
import mimetypes
from io import BytesIO

# Emoji to text mapping for [emoji] format - Used for special cases only
EMOJI_MAPPING = {
    "🔴": "[red_circle]",
    "🔵": "[blue_circle]", 
    "🟠": "[orange_circle]",
    "⚪️": "[white_circle]",
    "🟡": "[yellow_circle]",
    "🔮": "[crystal_ball]",
    "🫧": "[bubbles]",
    "🏵️": "[rosette]",
    "⚜️": "[fleur_de_lis]",
    "🌼": "[blossom]",
    "🎐": "[wind_chime]",
    "🍹": "[tropical_drink]",
    "🧿": "[nazar_amulet]",
    "⚡️": "[high_voltage]",
    "🛸": "[flying_saucer]",
    "🤖": "[robot]",
    "✅": "[white_check_mark]",
    "🔍": "[magnifying_glass]",
    "📡": "[satellite_antenna]",
    "🚀": "[rocket]",
    "⚡": "[high_voltage]",
    "📸": "[camera]",
    "🎞": "[film_frames]",
    "👤": "[bust_in_silhouette]",
    "🎬": "[clapper_board]",
    "🌟": "[glowing_star]",
    "📁": "[file_folder]",
    "🎀": "[ribbon]",
    "🌐": "[globe_with_meridians]",
    "⚠️": "[warning]",
    "❌": "[cross_mark]",
    "📊": "[bar_chart]",
    "👥": "[busts_in_silhouette]",
    "📈": "[chart_increasing]",
    "📢": "[loudspeaker]",
    "💾": "[floppy_disk]",
    "🔗": "[link]",
    "⏱": "[stopwatch]",
    "📋": "[clipboard]",
    "🆔": "[id_button]",
    "📛": "[name_badge]",
    "📺": "[television]",
    "💎": "[gem_stone]",
    "🔧": "[wrench]",
    "📱": "[mobile_phone]",
    "⏰": "[alarm_clock]",
    "💡": "[light_bulb]",
    "🛑": "[stop_sign]",
    "💥": "[collision]",
    "✏️": "[pencil]",
    "🍰": "[shortcake]",
    "🌸": "[cherry_blossom]",
    "❄️": "[snowflake]",
    "🔥": "[fire]",
    "💝": "[heart_with_ribbon]",
    "🎃": "[jack_o_lantern]",
    "🎄": "[christmas_tree]",
    "🎂": "[birthday_cake]",
    "👑": "[crown]",
    "⚔️": "[crossed_swords]",
    "🧚": "[fairy]",
    "🐉": "[dragon]",
    "🎉": "[party_popper]",
    "⏳": "[hourglass]",
    "📤": "[outbox_tray]",
    "📏": "[straight_ruler]",
    "🎁": "[wrapped_gift]",
    "🌞": "[sun]",
    "🍂": "[fallen_leaf]",
    "⭐": "[star]",
}

class UploadUtils:
    @staticmethod
    def format_character_name(name: str) -> str:
        """Format character name with auto-capitalization"""
        words = name.replace("-", " ").split()
        formatted_words = [word.capitalize() for word in words]
        return " ".join(formatted_words)
    
    @staticmethod
    def auto_capitalize(text: str) -> str:
        """Auto-capitalize text: hyphens to spaces, capitalize each word"""
        words = text.replace("-", " ").split()
        formatted_words = [word.capitalize() for word in words]
        return " ".join(formatted_words)
    
    @staticmethod
    async def generate_character_id() -> str:
        """Generate next character ID without leading zeros"""
        characters = await collection.find({"deleted": False}).to_list(None)
        
        if not characters:
            return "1"
        
        ids = []
        for char in characters:
            try:
                if char.get('id'):
                    # Convert to integer to remove leading zeros
                    char_id = str(char['id']).lstrip('0')
                    if not char_id:  # Handle case where ID is "0" or all zeros
                        char_id = "0"
                    ids.append(int(char_id))
            except (ValueError, TypeError):
                continue
        
        if not ids:
            return "1"
        
        max_id = max(ids)
        all_ids = set(range(1, max_id + 1))
        existing_ids = set(ids)
        available_ids = sorted(list(all_ids - existing_ids))
        
        if available_ids:
            return str(available_ids[0])
        else:
            next_id = max_id + 1
            return str(next_id)
    
    @staticmethod
    def parse_upload_command(text: str) -> Optional[Tuple[str, str]]:
        """Parse /upload command arguments"""
        parts = text.split()
        
        if len(parts) < 3:
            return None
        
        parts = parts[1:]
        
        if '"' in text or "'" in text:
            import shlex
            try:
                parsed = shlex.split(text)
                if len(parsed) >= 3:
                    parsed = parsed[1:]
                    character_name = parsed[0]
                    anime_name = " ".join(parsed[1:])
                    
                    character_name = UploadUtils.auto_capitalize(character_name)
                    anime_name = UploadUtils.auto_capitalize(anime_name)
                    return character_name, anime_name
            except:
                pass
        
        character_name = parts[0]
        anime_name = " ".join(parts[1:])
        
        character_name = UploadUtils.auto_capitalize(character_name)
        anime_name = UploadUtils.auto_capitalize(anime_name)
        
        return character_name, anime_name
    
    @staticmethod
    def get_media_type(message) -> Optional[str]:
        """Get media type from message"""
        if message.photo:
            return "photo"
        elif message.video:
            return "video"
        elif message.animation:
            return "animation"
        elif message.document:
            mime_type = message.document.mime_type
            if mime_type and mime_type.startswith("image/"):
                return "photo"
            elif mime_type and mime_type.startswith("video/"):
                return "video"
            elif mime_type and "gif" in mime_type:
                return "animation"
        return None
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension from filename"""
        return "." + filename.split(".")[-1] if "." in filename else ""
    
    @staticmethod
    async def is_uploader(user_id: int) -> bool:
        """Check if user is an uploader"""
        team_member = await upload_team_collection.find_one({"user_id": user_id})
        return team_member is not None
    
    @staticmethod
    async def is_owner(user_id: int) -> bool:
        """Check if user is an owner"""
        team_member = await upload_team_collection.find_one(
            {"user_id": user_id, "role": "owner"}
        )
        return team_member is not None
    
    @staticmethod
    def convert_emojis_to_text(text: str) -> str:
        """Convert emojis in text to [emoji_name] format"""
        for emoji, replacement in EMOJI_MAPPING.items():
            text = text.replace(emoji, replacement)
        return text
    
    @staticmethod
    def convert_text_to_emojis(text: str) -> str:
        """Convert [emoji_name] format back to emojis"""
        for emoji, replacement in EMOJI_MAPPING.items():
            text = text.replace(replacement, emoji)
        return text
    
    @staticmethod
    async def format_preview_text(session_data: Dict[str, Any], user: Dict[str, Any]) -> str:
        """Format preview text for confirmation"""
        from keyboards import UploadKeyboards
        
        username = user.get("username", "Unknown")
        
        # Get rarity emoji from the RARITIES dictionary
        rarity_emoji = UploadKeyboards.RARITIES.get(session_data.get('rarity', ''), "")
        
        # Format text with emojis
        text = f"""🆔 ID: {session_data['temp_id']}
👤 Character: {session_data['character_name']}
🎬 Anime: {session_data['anime_name']}
🌟 Rarity: {rarity_emoji} {session_data['rarity']}
📁 Type: {'📸 Photo' if session_data['img_type'] == 'photo' else '🎞 Video'}
👤 Added by: @{username}
🌐 Host: Catbox.moe"""
        
        return text.strip()
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate unique session ID"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    @staticmethod
    def format_caption_for_character(character: Dict[str, Any], user_info: Dict[str, Any]) -> str:
        """Format caption for character display with proper emojis"""
        from keyboards import UploadKeyboards
        
        username = user_info.get("username", "Unknown")
        
        # Get rarity emoji from the RARITIES dictionary
        rarity = character.get('rarity', '')
        rarity_emoji = UploadKeyboards.RARITIES.get(rarity, "")
        
        # Get character name with edition emoji if available
        character_name = character.get('name', 'Unknown')
        edition = character.get('edition', '')
        
        # Add edition emoji to character name if edition exists
        if edition:
            edition_lower = edition.lower()
            if 'birthday' in edition_lower:
                character_name += " 🎂"
            elif 'christmas' in edition_lower:
                character_name += " 🎄"
            elif 'halloween' in edition_lower:
                character_name += " 🎃"
            elif 'valentine' in edition_lower or 'love' in edition_lower:
                character_name += " 💝"
            elif 'new year' in edition_lower or 'newyear' in edition_lower:
                character_name += " 🎉"
            elif 'summer' in edition_lower:
                character_name += " 🌞"
            elif 'winter' in edition_lower:
                character_name += " ❄️"
            elif 'spring' in edition_lower:
                character_name += " 🌸"
            elif 'autumn' in edition_lower or 'fall' in edition_lower:
                character_name += " 🍂"
            elif 'anniversary' in edition_lower:
                character_name += " 🎁"
            elif 'limited' in edition_lower:
                character_name += " ⭐"
            elif 'exclusive' in edition_lower:
                character_name += " 💎"
        
        # Get type emoji
        type_emoji = "📸" if character.get('img_type') == 'photo' else '🎞'
        
        # Format caption with emojis
        caption = f"""🆔 ID: {character.get('id', 'N/A')}
👤 Character: {character_name}
🎬 Anime: {character.get('anime', 'Unknown')}
🌟 Rarity: {rarity_emoji} {character.get('rarity', 'Unknown')}
📁 Type: {type_emoji} {'Photo' if character.get('img_type') == 'photo' else 'Video'}
👤 Added by: @{username}"""
        
        # Add edition if available
        if edition:
            caption += f"\n🎀 Edition: {edition}"
        
        caption += "\n🌐 Host: Catbox.moe"
        
        return caption
    
    @staticmethod
    async def get_database_channel() -> Optional[int]:
        """Get database channel ID"""
        channel = await database_channel_collection.find_one({})
        return channel.get('channel_id') if channel else None
    
    @staticmethod
    async def set_database_channel(channel_id: int) -> bool:
        """Set database channel ID"""
        try:
            await database_channel_collection.update_one(
                {},
                {"$set": {"channel_id": channel_id}},
                upsert=True
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    async def find_character_by_id(char_id: str) -> Optional[Dict[str, Any]]:
        """Find character by ID, handling multiple formats"""
        # Try exact match first
        character = await collection.find_one({
            "id": char_id,
            "deleted": False
        })
        
        if character:
            return character
        
        # Try without leading zeros if it's a number
        if char_id.isdigit():
            # Try removing leading zeros
            char_id_no_zeros = str(int(char_id))
            if char_id_no_zeros != char_id:
                character = await collection.find_one({
                    "id": char_id_no_zeros,
                    "deleted": False
                })
                if character:
                    return character
            
            # Try with 4-digit format
            char_id_4digit = char_id.zfill(4)
            if char_id_4digit != char_id:
                character = await collection.find_one({
                    "id": char_id_4digit,
                    "deleted": False
                })
                if character:
                    return character
        

        return None
