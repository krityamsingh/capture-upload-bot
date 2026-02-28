import re
import random
import string
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from database import collection, upload_team_collection, database_channel_collection, counters_collection

class UploadUtils:
    @staticmethod
    def format_character_name(name: str) -> str:
        words = name.replace("-", " ").split()
        return " ".join(word.capitalize() for word in words)

    @staticmethod
    def auto_capitalize(text: str) -> str:
        words = text.replace("-", " ").split()
        return " ".join(word.capitalize() for word in words)

    @staticmethod
    async def generate_character_id() -> str:
        """Generate next character ID using MongoDB counter."""
        counter = await counters_collection.find_one_and_update(
            {"_id": "character_id"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )
        return str(counter["seq"])

    @staticmethod
    def parse_upload_command(text: str) -> Optional[Tuple[str, str]]:
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
                    char = UploadUtils.auto_capitalize(parsed[0])
                    anime = UploadUtils.auto_capitalize(" ".join(parsed[1:]))
                    return char, anime
            except:
                pass

        char = UploadUtils.auto_capitalize(parts[0])
        anime = UploadUtils.auto_capitalize(" ".join(parts[1:]))
        return char, anime

    @staticmethod
    def get_media_type(message) -> Optional[str]:
        if message.photo:
            return "photo"
        elif message.video:
            return "video"
        elif message.animation:
            return "animation"
        elif message.document:
            mime = message.document.mime_type
            if mime and mime.startswith("image/"):
                return "photo"
            elif mime and mime.startswith("video/"):
                return "video"
            elif mime and "gif" in mime:
                return "animation"
        return None

    @staticmethod
    def get_file_extension(filename: str) -> str:
        return "." + filename.split(".")[-1] if "." in filename else ""

    @staticmethod
    async def is_uploader(user_id: int) -> bool:
        return await upload_team_collection.find_one({"user_id": user_id}) is not None

    @staticmethod
    async def is_owner(user_id: int) -> bool:
        return await upload_team_collection.find_one({"user_id": user_id, "role": "owner"}) is not None

    @staticmethod
    async def format_preview_text(session_data: Dict[str, Any], user: Dict[str, Any]) -> str:
        from keyboards import UploadKeyboards
        rarity_emoji = UploadKeyboards.RARITIES.get(session_data.get('rarity', ''), "")
        return f"""🆔 ID: {session_data['temp_id']}
👤 Character: {session_data['character_name']}
🎬 Anime: {session_data['anime_name']}
🌟 Rarity: {rarity_emoji} {session_data['rarity']}
📁 Type: {'📸 Photo' if session_data['img_type'] == 'photo' else '🎞 Video'}
👤 Added by: @{user['username']}
🌐 Host: Catbox.moe"""

    @staticmethod
    def generate_session_id() -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    @staticmethod
    def format_caption_for_character(character: Dict[str, Any], user_info: Dict[str, Any]) -> str:
        from keyboards import UploadKeyboards
        rarity_emoji = UploadKeyboards.RARITIES.get(character.get('rarity', ''), "")
        type_emoji = "📸" if character.get('img_type') == 'photo' else '🎞'

        caption = f"""🆔 ID: {character.get('id', 'N/A')}
👤 Character: {character.get('name', 'Unknown')}
🎬 Anime: {character.get('anime', 'Unknown')}
🌟 Rarity: {rarity_emoji} {character.get('rarity', 'Unknown')}
📁 Type: {type_emoji} {'Photo' if character.get('img_type') == 'photo' else 'Video'}
👤 Added by: @{user_info['username']}"""

        edition = character.get('edition', '')
        if edition:
            caption += f"\n🎀 Edition: {edition}"
        caption += "\n🌐 Host: Catbox.moe"
        return caption

    @staticmethod
    async def get_database_channel() -> Optional[int]:
        channel = await database_channel_collection.find_one({})
        return channel.get('channel_id') if channel else None

    @staticmethod
    async def set_database_channel(channel_id: int) -> bool:
        try:
            await database_channel_collection.update_one({}, {"$set": {"channel_id": channel_id}}, upsert=True)
            return True
        except Exception:
            return False

    @staticmethod
    async def find_character_by_id(char_id: str) -> Optional[Dict[str, Any]]:
        char = await collection.find_one({"id": char_id, "deleted": False})
        if char:
            return char
        if char_id.isdigit():
            no_zeros = str(int(char_id))
            if no_zeros != char_id:
                char = await collection.find_one({"id": no_zeros, "deleted": False})
                if char:
                    return char
            four_digit = char_id.zfill(4)
            if four_digit != char_id:
                char = await collection.find_one({"id": four_digit, "deleted": False})
                if char:
                    return char
        return None
