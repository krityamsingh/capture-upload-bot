# states.py - UNCHANGED
from enum import Enum

class CharacterStates(Enum):
    """State management for character upload flow - NEW FLOW"""
    WAITING_CHAR_NAME = "waiting_char_name"
    WAITING_ANIME_NAME = "waiting_anime_name" 
    WAITING_RARITY = "waiting_rarity"
    WAITING_SUBRARITY = "waiting_subrarity"
    WAITING_MEDIA = "waiting_media"
    WAITING_CONFIRMATION = "waiting_confirmation"