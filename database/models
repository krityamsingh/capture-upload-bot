# ==================== DATABASE/MODELS.PY ====================
# database/models.py - UNCHANGED
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

class Character:
    """Data model for character documents"""
    
    def __init__(
        self,
        char_name: str,
        anime_name: str,
        rarity: str,
        character_id: int,
        media_url: Optional[str] = None,
        subrarity: Optional[str] = None,
        media_type: Optional[str] = None,
        added_by: int = None,
        timestamp: Optional[datetime] = None
    ):
        self.char_name = char_name
        self.anime_name = anime_name
        self.rarity = rarity
        self.character_id = character_id
        self.media_url = media_url
        self.subrarity = subrarity
        self.media_type = media_type
        self.added_by = added_by
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character object to dictionary for MongoDB"""
        return {
            "char_name": self.char_name,
            "anime_name": self.anime_name,
            "rarity": self.rarity,
            "character_id": self.character_id,
            "media_url": self.media_url,
            "subrarity": self.subrarity,
            "media_type": self.media_type,
            "added_by": self.added_by,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """Create Character object from dictionary"""
        return cls(
            char_name=data.get("char_name"),
            anime_name=data.get("anime_name"),
            rarity=data.get("rarity"),
            character_id=data.get("character_id"),
            media_url=data.get("media_url"),
            subrarity=data.get("subrarity"),
            media_type=data.get("media_type"),
            added_by=data.get("added_by"),
            timestamp=data.get("timestamp")
        )

class UserSession:
    """Temporary session data for character upload flow - SIMPLIFIED"""
    
    def __init__(
        self,
        user_id: int,
        state: str,
        char_name: Optional[str] = None,
        anime_name: Optional[str] = None,
        rarity: Optional[str] = None,
        subrarity: Optional[str] = None,
        media_file_id: Optional[str] = None,
        media_type: Optional[str] = None,
        media_url: Optional[str] = None
    ):
        self.user_id = user_id
        self.state = state
        self.char_name = char_name
        self.anime_name = anime_name
        self.rarity = rarity
        self.subrarity = subrarity
        self.media_file_id = media_file_id
        self.media_type = media_type
        self.media_url = media_url
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "user_id": self.user_id,
            "state": self.state,
            "char_name": self.char_name,
            "anime_name": self.anime_name,
            "rarity": self.rarity,
            "subrarity": self.subrarity,
            "media_file_id": self.media_file_id,
            "media_type": self.media_type,
            "media_url": self.media_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create UserSession from dictionary"""
        return cls(
            user_id=data.get("user_id"),
            state=data.get("state"),
            char_name=data.get("char_name"),
            anime_name=data.get("anime_name"),
            rarity=data.get("rarity"),
            subrarity=data.get("subrarity"),
            media_file_id=data.get("media_file_id"),
            media_type=data.get("media_type"),
            media_url=data.get("media_url")
        )

@dataclass
class MassUploadSession:
    """Mass upload session for batch character processing"""
    user_id: int
    char_name: str
    anime_name: str
    uploaded_characters: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mass upload session to dictionary"""
        return {
            "user_id": self.user_id,
            "char_name": self.char_name,
            "anime_name": self.anime_name,
            "uploaded_characters": self.uploaded_characters,
            "created_at": self.created_at,
            "last_activity": self.last_activity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MassUploadSession':
        """Create MassUploadSession from dictionary"""
        session = cls(
            user_id=data.get("user_id"),
            char_name=data.get("char_name"),
            anime_name=data.get("anime_name"),
            uploaded_characters=data.get("uploaded_characters", []),
            created_at=data.get("created_at", datetime.utcnow())
        )
        session.last_activity = data.get("last_activity", session.created_at)
        return session
    
    def add_character(self, character_data: Dict[str, Any]):
        """Add a character to the session"""
        self.uploaded_characters.append(character_data)
        self.last_activity = datetime.utcnow()
    
    def remove_last_character(self) -> Optional[Dict[str, Any]]:
        """Remove and return the last uploaded character"""
        if self.uploaded_characters:
            return self.uploaded_characters.pop()
        return None
    
    def get_character_count(self) -> int:
        """Get total characters uploaded in this session"""
        return len(self.uploaded_characters)
    
    def get_session_summary(self) -> str:
        """Get formatted session summary"""
        return (
            f"📋 **Current Session**\n\n"
            f"👤 **Character:** {self.char_name}\n"
            f"🎞️ **Anime:** {self.anime_name}\n"
            f"📊 **Uploaded:** {self.get_character_count()} characters\n"
            f"🕐 **Started:** {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
