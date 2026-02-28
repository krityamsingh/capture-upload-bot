from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class Character(BaseModel):
    name: str
    anime: str
    rarity: str
    id: str
    subtype: Optional[str] = ""
    img_url: str
    file_extension: str
    img_type: str
    upload_site: str = "pixeldrain"
    added_by: Dict[str, Any]
    edition: Optional[str] = ""
    date_added: datetime = Field(default_factory=datetime.utcnow)
    deleted: bool = False

class UploadSession(BaseModel):
    user_id: int
    chat_id: int
    message_id: int
    step: str
    character_name: str
    anime_name: str
    media_url: str
    file_extension: str
    img_type: str
    rarity: Optional[str] = None
    subtype: Optional[str] = None
    temp_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TeamMember(BaseModel):
    user_id: int
    username: Optional[str] = None
    role: str = "team_member"
    added_by: int
    added_at: datetime = Field(default_factory=datetime.utcnow)
