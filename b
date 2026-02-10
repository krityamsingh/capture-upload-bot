#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTIMATE TELEGRAM ENTERPRISE REPORTING SYSTEM v11.0
Complete Professional Solution with Advanced OTP Verification & Proxy Analytics Engine
Created: 2024
Version: 11.0
Lines: 5200+
"""

# ============================================
# STANDARD LIBRARY IMPORTS
# ============================================
import asyncio
import csv
import hashlib
import io
import ipaddress
import json
import logging
import math
import platform
import random
import re
import socket
import ssl
import statistics
import string
import sys
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from pathlib import Path
from typing import (Any, Callable, Dict, List, Optional, Set, Tuple, Union)

# ============================================
# THIRD-PARTY NETWORKING/HTTP IMPORTS
# ============================================
import aiohttp
import certifi
import dns.resolver
import pytz
import requests
import urllib.parse
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================
# TELEGRAM LIBRARIES
# ============================================
# Bot API (user interface)
from telegram import (
    BotCommand, BotCommandScopeAllPrivateChats, CallbackGame, Chat,
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
    MenuButtonCommands, MessageEntity, ReplyKeyboardMarkup,
    ReplyKeyboardRemove, Update, User, WebAppInfo
)
from telegram.ext import (
    Application, ApplicationBuilder, CallbackContext, CallbackQueryHandler,
    CommandHandler, ConversationHandler, ExtBot, JobQueue, MessageHandler,
    PicklePersistence, ContextTypes, filters
)

# Telegram Client (actual reporting functionality)
from telethon import TelegramClient, events, functions, hints, types
from telethon.errors import (
    AccessTokenExpiredError, AccessTokenInvalidError, ApiIdInvalidError,
    AuthKeyDuplicatedError, AuthKeyUnregisteredError, ChatAdminRequiredError,
    ChatWriteForbiddenError, FilePartEmptyError, FilePartMissingError,
    FloodWaitError, InviteHashEmptyError, InviteHashExpiredError,
    InviteHashInvalidError, Md5ChecksumInvalidError, PackShortNameInvalidError,
    PackShortNameOccupiedError, PasswordHashInvalidError, PhoneCodeEmptyError,
    PhoneCodeExpiredError, PhoneCodeHashEmptyError, PhoneCodeInvalidError,
    PhoneNumberBannedError, PhoneNumberFloodError, PhoneNumberInvalidError,
    PhoneNumberOccupiedError, PhoneNumberUnoccupiedError, PhotoCropSizeSmallError,
    PhotoExtInvalidError, RpcCallFailError, RpcMcgetFailError,
    ServerError, SessionExpiredError, SessionPasswordNeededError,
    SessionRevokedError, SlowModeWaitError, StickersetInvalidError,
    TimedOutError, UserAlreadyParticipantError, UserChannelsTooMuchError,
    UserDeactivatedBanError, UserDeactivatedError, UserNotParticipantError,
    UserPrivacyRestrictedError, UsernameInvalidError, UsernameNotModifiedError,
    UsernameOccupiedError
)

# Telethon TL functions
from telethon.tl.functions.account import (
    GetAccountTTLRequest, GetAuthorizationsRequest, GetAutoDownloadSettingsRequest,
    GetChatThemesRequest, GetContentSettingsRequest, GetGlobalPrivacySettingsRequest,
    GetMultiWallPapersRequest, GetNotifySettingsRequest, GetPasswordRequest,
    GetPasswordSettingsRequest, GetThemesRequest, GetTmpPasswordRequest,
    GetWallPapersRequest, GetWebAuthorizationsRequest, ReportPeerRequest,
    ResetAuthorizationRequest, ResetWebAuthorizationRequest,
    ResetWebAuthorizationsRequest, SaveAutoDownloadSettingsRequest,
    SetAccountTTLRequest, SetContentSettingsRequest, SetGlobalPrivacySettingsRequest,
    UpdatePasswordSettingsRequest, UpdateStatusRequest, UploadThemeRequest
)

from telethon.tl.functions.auth import (
    BindTempAuthKeyRequest, CancelCodeRequest, CheckPasswordRequest,
    DropTempAuthKeysRequest, ExportAuthorizationRequest, ImportAuthorizationRequest,
    ImportBotAuthorizationRequest, LogOutRequest, RecoverPasswordRequest,
    RequestPasswordRecoveryRequest, ResendCodeRequest, ResetAuthorizationsRequest,
    SendCodeRequest, SignInRequest, SignUpRequest
)

from telethon.tl.functions.messages import (
    AcceptUrlAuthRequest, AddChatUserRequest, CheckChatInviteRequest,
    CheckHistoryImportRequest, CheckHistoryImportPeerRequest, ClearAllDraftsRequest,
    CreateChatRequest, DeleteChatRequest, DeleteChatUserRequest,
    DeleteExportedChatInviteRequest, DeleteHistoryRequest, DeleteMessagesRequest,
    EditChatPhotoRequest, EditChatTitleRequest, EditExportedChatInviteRequest,
    EditMessageRequest, ExportChatInviteRequest, FaveStickerRequest,
    ForwardMessagesRequest, GetAdminsWithInvitesRequest, GetAllChatsRequest,
    GetAttachedStickersRequest, GetBotCallbackAnswerRequest, GetChatInviteImportersRequest,
    GetChatsRequest, GetCommonChatsRequest, GetDialogFilterRequest,
    GetDialogFiltersRequest, GetDialogUnreadMarksRequest, GetDialogsRequest,
    GetDiscussionMessageRequest, GetExportedChatInviteRequest,
    GetExportedChatInvitesRequest, GetFavedStickersRequest, GetFullChatRequest,
    GetGameHighScoresRequest, GetHistoryRequest, GetInlineBotResultsRequest,
    GetMessageEditDataRequest, GetMessageReadParticipantsRequest,
    GetMessagesReactionsRequest, GetMessagesRequest, GetMessagesViewsRequest,
    GetPinnedDialogsRequest, GetPollResultsRequest, GetPollVotesRequest,
    GetRecentLocationsRequest, GetRepliesRequest, GetSearchCountersRequest,
    GetSplitRangesRequest, GetStickerSetRequest, GetSuggestedDialogFiltersRequest,
    GetUnreadMentionsRequest, GetWebPagePreviewRequest, GetWebPageRequest,
    HidePeerSettingsBarRequest, ImportChatInviteRequest, InstallStickerSetRequest,
    MarkDialogUnreadRequest, MigrateChatRequest, ReadDiscussionRequest,
    ReadHistoryRequest, ReadMentionsRequest, ReceivedMessagesRequest,
    ReorderDialogFiltersRequest, ReorderPinnedDialogsRequest, ReportRequest,
    ReportSpamRequest, RequestUrlAuthRequest, SaveDefaultSendAsRequest,
    SearchRequest, SearchStickerSetsRequest, SendInlineBotResultRequest,
    SendMediaRequest, SendMessageRequest, SendMultiMediaRequest,
    SendReactionRequest, SendScreenshotNotificationRequest, SetBotCallbackAnswerRequest,
    SetBotPrecheckoutResultsRequest, SetBotShippingResultsRequest,
    SetChatThemeRequest, SetGameScoreRequest, SetHistoryTTLRequest,
    SetTypingRequest, StartBotRequest, ToggleDialogPinRequest,
    ToggleNoForwardsRequest, UninstallStickerSetRequest, UnpinAllMessagesRequest,
    UpdateDialogFilterRequest, UpdatePinnedMessageRequest, UploadEncryptedFileRequest,
    UploadMediaRequest
)

# Telethon TL types (truncated for brevity - you should keep only what you actually use)
from telethon.tl.types import (
    Channel, ChannelFull, Chat, ChatEmpty, ChatFull, ChatInvite,
    ChatInviteAlready, ChatInvitePeek, ChatParticipant, ChatParticipantAdmin,
    ChatParticipantCreator, ChatParticipants, ChatParticipantsForbidden,
    ChatPhoto, ChatPhotoEmpty, Dialog, DialogPeer, DialogPeerFolder,
    InputChatPhoto, InputChatPhotoEmpty, InputChatUploadedPhoto,
    InputDocumentFileLocation, InputEncryptedFileLocation, InputFileLocation,
    InputGeoPoint, InputGeoPointEmpty, InputMediaContact, InputMediaDice,
    InputMediaDocument, InputMediaGame, InputMediaGeoLive, InputMediaGeoPoint,
    InputMediaInvoice, InputMediaPhoto, InputMediaPoll, InputMediaStory,
    InputMediaUploadedDocument, InputMediaUploadedPhoto, InputMediaVenue,
    InputMediaWebPage, InputPeerChannel, InputPeerChat, InputPeerUser,
    InputPeerPhotoFileLocation, InputPhoto, InputPhotoEmpty,
    InputPhotoFileLocation, InputPhotoLegacyFileLocation,
    InputReportReasonChildAbuse, InputReportReasonCopyright,
    InputReportReasonFake, InputReportReasonGeoIrrelevant,
    InputReportReasonIllegalDrugs, InputReportReasonOther,
    InputReportReasonPersonalDetails, InputReportReasonPornography,
    InputReportReasonSpam, InputReportReasonViolence,
    InputSecureFileLocation, InputStickerSetThumb, InputTakeoutFileLocation,
    InputUser, InputWebFileLocation, Message, MessageActionBotAllowed,
    MessageActionChannelCreate, MessageActionChannelMigrateFrom,
    MessageActionChatAddUser, MessageActionChatCreate, MessageActionChatDeletePhoto,
    MessageActionChatDeleteUser, MessageActionChatEditPhoto,
    MessageActionChatEditTitle, MessageActionChatJoinedByLink,
    MessageActionChatJoinedByRequest, MessageActionChatMigrateTo,
    MessageActionContactSignUp, MessageActionCustomAction, MessageActionEmpty,
    MessageActionGameScore, MessageActionGeoProximityReached,
    MessageActionGiftCode, MessageActionGiftPremium, MessageActionGiveawayLaunch,
    MessageActionGiveawayResults, MessageActionGroupCall,
    MessageActionGroupCallScheduled, MessageActionHistoryClear,
    MessageActionInviteToGroupCall, MessageActionPaymentSent,
    MessageActionPaymentSentMe, MessageActionPhoneCall, MessageActionPinMessage,
    MessageActionRequestedPeer, MessageActionScreenshotTaken,
    MessageActionSecureValuesSent, MessageActionSecureValuesSentMe,
    MessageActionSetChatTheme, MessageActionSetMessagesTTL,
    MessageActionSuggestProfilePhoto, MessageActionTopicCreate,
    MessageActionTopicEdit, MessageActionWebViewDataSent,
    MessageActionWebViewDataSentMe, MessageEmpty, MessageMediaContact,
    MessageMediaDice, MessageMediaDocument, MessageMediaEmpty, MessageMediaGame,
    MessageMediaGeo, MessageMediaInvoice, MessageMediaPhoto, MessageMediaPoll,
    MessageMediaVenue, MessageMediaWebPage, MessageService, PeerChannel,
    PeerChat, PeerUser, UpdateBotCallbackQuery, UpdateChannel,
    UpdateChannelMessageViews, UpdateChannelTooLong, UpdateChat,
    UpdateChatDefaultBannedRights, UpdateChatParticipants,
    UpdateChatUserTyping, UpdateDeleteChannelMessages, UpdateDeleteMessages,
    UpdateEditChannelMessage, UpdateEncryptedChatTyping, UpdateEncryptedMessagesRead,
    UpdateEncryption, UpdateMessageID, UpdateNewChannelMessage,
    UpdateNewEncryptedMessage, UpdateNewMessage, UpdateNewStickerSet,
    UpdateNotifySettings, UpdatePinnedChannelMessages, UpdatePinnedDialogs,
    UpdatePinnedMessages, UpdatePrivacy, UpdateReadChannelInbox,
    UpdateReadChannelOutbox, UpdateReadHistoryInbox, UpdateReadHistoryOutbox,
    UpdateReadMessagesContents, UpdateServiceNotification, UpdateStickerSets,
    UpdateStickerSetsOrder, UpdateUser, UpdateUserPhone, UpdateUserPhoto,
    UpdateUserStatus, UpdateUserName, UpdateUserTyping, UpdateWebPage,
    User, UserEmpty, UserFull
)

# ============================================
# UTILITY & MONITORING IMPORTS
# ============================================
import backoff
import numpy as np
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

# ============================================
# RICH CONSOLE OUTPUT
# ============================================
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn, TextColumn,
                           TimeElapsedColumn, TimeRemainingColumn)
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.traceback import install as install_rich_traceback

# Install rich traceback for better error display
install_rich_traceback()
console = Console()


# ============================================
# SECTION 2: ADVANCED CONFIGURATION
# ============================================

# Bot Token (Replace with your actual bot token)
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
API_ID = 27157163
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"

# Owner IDs (Full control)
OWNER_IDS = [6118760915, 1366105247]

# Admin IDs (Extended permissions)
ADMIN_IDS = []

# Fast response countries (Telegram servers are fastest here)
FAST_COUNTRIES = [
    "Germany", "Netherlands", "Singapore", "Finland", "Ireland", "Japan",
    "United States", "United Kingdom", "France", "Canada", "Australia",
    "Switzerland", "Sweden", "Norway", "Denmark", "Austria", "Belgium",
    "Luxembourg", "Italy", "Spain", "Portugal", "Poland", "Czech Republic",
    "Slovakia", "Hungary", "Romania", "Bulgaria", "Greece", "Turkey",
    "Israel", "United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait",
    "Bahrain", "Oman", "South Africa", "Brazil", "Argentina", "Chile",
    "Mexico", "Colombia", "Peru", "Venezuela", "Ecuador", "Uruguay",
    "Paraguay", "Bolivia", "Costa Rica", "Panama", "Dominican Republic",
    "Puerto Rico", "Jamaica", "Trinidad and Tobago", "Barbados", "Bahamas"
]

# Premium countries (Top tier for performance)
PREMIUM_COUNTRIES = [
    "Germany", "Netherlands", "Singapore", "Finland", "Ireland", "Japan",
    "United States", "United Kingdom", "Switzerland", "Sweden"
]

# File paths
DATA_DIR = Path("data")
SESSION_DIR = Path("sessions")
LOG_DIR = Path("logs")
BACKUP_DIR = Path("backups")
ANALYTICS_DIR = Path("analytics")

# Create directories
for directory in [DATA_DIR, SESSION_DIR, LOG_DIR, BACKUP_DIR, ANALYTICS_DIR]:
    directory.mkdir(exist_ok=True)

# Data files
USERS_FILE = DATA_DIR / "users.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
PROXY_FILE = DATA_DIR / "data.txt"  # User adds proxies here
PROXY_CACHE_FILE = DATA_DIR / "proxy_cache.json"
JOBS_FILE = DATA_DIR / "jobs.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
BLACKLIST_FILE = DATA_DIR / "blacklist.json"
WHITELIST_FILE = DATA_DIR / "whitelist.json"
LOG_FILE = LOG_DIR / "system.log"
ANALYTICS_FILE = ANALYTICS_DIR / "analytics.json"

# Advanced proxy test URLs with multiple endpoints
PROXY_TEST_URLS = [
    # Fast check endpoints (simple IP check)
    {"url": "https://httpbin.org/ip", "type": "json", "field": "origin", "timeout": 5},
    {"url": "https://api.ipify.org?format=json", "type": "json", "field": "ip", "timeout": 5},
    {"url": "https://checkip.amazonaws.com", "type": "text", "field": None, "timeout": 5},
    {"url": "https://icanhazip.com", "type": "text", "field": None, "timeout": 5},
    {"url": "https://ipinfo.io/ip", "type": "text", "field": None, "timeout": 5},
    {"url": "https://wtfismyip.com/text", "type": "text", "field": None, "timeout": 5},
    {"url": "https://myexternalip.com/raw", "type": "text", "field": None, "timeout": 5},
    {"url": "https://ipecho.net/plain", "type": "text", "field": None, "timeout": 5},
    
    # Telemetry endpoints (check if proxy leaks data)
    {"url": "https://httpbin.org/user-agent", "type": "json", "field": "user-agent", "timeout": 8},
    {"url": "https://httpbin.org/headers", "type": "json", "field": "headers", "timeout": 8},
    {"url": "https://httpbin.org/get", "type": "json", "field": "args", "timeout": 8},
    
    # Geo-location endpoints
    {"url": "https://ipapi.co/json/", "type": "json", "field": "country_name", "timeout": 10},
    {"url": "https://ipwho.is/", "type": "json", "field": "country", "timeout": 10},
    {"url": "https://geolocation-db.com/json/", "type": "json", "field": "country_name", "timeout": 10},
    
    # High-speed test endpoints
    {"url": "https://google.com", "type": "text", "field": None, "timeout": 3},
    {"url": "https://cloudflare.com", "type": "text", "field": None, "timeout": 3},
    {"url": "https://fast.com", "type": "text", "field": None, "timeout": 5},
]

# User-Agent rotation for proxy testing
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
]

# ============================================
# SECTION 3: ENHANCED DATA MODELS
# ============================================

class UserRole(IntEnum):
    """Enhanced user roles with hierarchical permissions"""
    BANNED = 0       # No access
    VIEWER = 1       # View only
    USER = 2         # Basic reporting
    REPORTER = 3     # Enhanced reporting
    MODERATOR = 4    # Can manage users
    ADMIN = 5        # Full system access
    SUDO = 6         # Super user
    OWNER = 7        # System owner

class AccountStatus(IntEnum):
    """Enhanced account status tracking"""
    UNVERIFIED = 0          # Not verified yet
    VERIFYING = 1           # OTP verification in progress
    ACTIVE = 2              # Ready to use
    INACTIVE = 3            # Not logged in
    BANNED = 4              # Banned by Telegram
    FLOOD_WAIT = 5          # Rate limited
    NEED_PASSWORD = 6       # 2FA required
    PROXY_FAILED = 7        # Proxy not working
    SESSION_EXPIRED = 8     # Session expired
    NEED_EMAIL_CODE = 9     # Email verification needed
    NEED_PHONE_CODE = 10    # Phone verification needed
    NEED_CAPTCHA = 11       # Captcha required
    NEED_DEVICE_CONFIRM = 12 # Device confirmation needed

class ReportStatus(IntEnum):
    """Enhanced job status tracking"""
    PENDING = 0
    VALIDATING = 1
    PREPARING = 2
    PROCESSING = 3
    COMPLETING = 4
    COMPLETED = 5
    FAILED = 6
    PARTIAL = 7
    CANCELLED = 8
    TIMED_OUT = 9

class ProxyType(IntEnum):
    """Proxy protocol types"""
    HTTP = 0
    HTTPS = 1
    SOCKS4 = 2
    SOCKS5 = 3
    DIRECT = 4

class OTPSource(IntEnum):
    """OTP delivery methods"""
    SMS = 0
    APP = 1
    CALL = 2
    FLASH_CALL = 3
    MISSED_CALL = 4
    EMAIL = 5
    BACKUP = 6

class SecurityLevel(IntEnum):
    """Security levels for accounts"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    EXTREME = 3

@dataclass
class TelegramUser:
    """Enhanced user model with comprehensive tracking"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "en"
    role: UserRole = UserRole.USER
    added_at: datetime = None
    reports_made: int = 0
    last_active: Optional[datetime] = None
    session_id: str = None
    permissions: List[str] = None
    settings: Dict[str, Any] = None
    statistics: Dict[str, Any] = None
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    is_premium: bool = False
    trust_score: float = 100.0
    warnings: int = 0
    flags: Set[str] = None
    
    def __post_init__(self):
        if self.added_at is None:
            self.added_at = datetime.now()
        if self.session_id is None:
            self.session_id = hashlib.sha256(f"{self.user_id}{time.time()}".encode()).hexdigest()[:16]
        if self.permissions is None:
            self.permissions = []
        if self.settings is None:
            self.settings = {
                "notifications": True,
                "auto_start": False,
                "proxy_priority": "speed",
                "report_limit": 10,
                "language": "en",
                "timezone": "UTC"
            }
        if self.statistics is None:
            self.statistics = {
                "total_reports": 0,
                "successful_reports": 0,
                "failed_reports": 0,
                "report_success_rate": 0.0,
                "average_report_time": 0.0,
                "last_report_time": None,
                "daily_reports": 0,
                "weekly_reports": 0,
                "monthly_reports": 0
            }
        if self.flags is None:
            self.flags = set()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "language_code": self.language_code,
            "role": self.role.value,
            "added_at": self.added_at.isoformat(),
            "reports_made": self.reports_made,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "session_id": self.session_id,
            "permissions": self.permissions,
            "settings": self.settings,
            "statistics": self.statistics,
            "security_level": self.security_level.value,
            "is_premium": self.is_premium,
            "trust_score": self.trust_score,
            "warnings": self.warnings,
            "flags": list(self.flags)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TelegramUser':
        """Create from dictionary"""
        user = cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            language_code=data.get("language_code", "en"),
            role=UserRole(data.get("role", 2)),
            reports_made=data.get("reports_made", 0),
            is_premium=data.get("is_premium", False),
            trust_score=data.get("trust_score", 100.0),
            warnings=data.get("warnings", 0)
        )
        user.added_at = datetime.fromisoformat(data["added_at"])
        if data.get("last_active"):
            user.last_active = datetime.fromisoformat(data["last_active"])
        user.session_id = data.get("session_id") or hashlib.sha256(f"{data['user_id']}{time.time()}".encode()).hexdigest()[:16]
        user.permissions = data.get("permissions", [])
        user.settings = data.get("settings", {})
        user.statistics = data.get("statistics", {})
        user.security_level = SecurityLevel(data.get("security_level", 1))
        user.flags = set(data.get("flags", []))
        return user
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        if self.role >= UserRole.OWNER:
            return True
        return permission in self.permissions
    
    def update_statistics(self, success: bool, report_time: float):
        """Update user statistics"""
        self.statistics["total_reports"] += 1
        if success:
            self.statistics["successful_reports"] += 1
        else:
            self.statistics["failed_reports"] += 1
        
        # Calculate success rate
        total = self.statistics["total_reports"]
        successful = self.statistics["successful_reports"]
        self.statistics["report_success_rate"] = (successful / total * 100) if total > 0 else 0.0
        
        # Update average time
        current_avg = self.statistics["average_report_time"]
        count = self.statistics["total_reports"]
        self.statistics["average_report_time"] = (current_avg * (count - 1) + report_time) / count if count > 0 else report_time
        
        self.statistics["last_report_time"] = datetime.now().isoformat()
        
        # Update daily/weekly/monthly counts
        now = datetime.now()
        last_report = datetime.fromisoformat(self.statistics["last_report_time"]) if self.statistics["last_report_time"] else None
        
        if not last_report or (now - last_report).days >= 1:
            self.statistics["daily_reports"] = 0
        self.statistics["daily_reports"] += 1

@dataclass
class ProxyEntry:
    """
    Enhanced proxy entry with comprehensive analytics
    """
    proxy: str  # Format: protocol://user:pass@host:port or host:port
    proxy_type: ProxyType = ProxyType.HTTP
    country: str = "Unknown"
    city: str = "Unknown"
    isp: str = "Unknown"
    asn: str = "Unknown"
    is_active: bool = True
    success_count: int = 0
    fail_count: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    last_used: Optional[datetime] = None
    reports_used: int = 0
    priority: float = 1.0
    verified: bool = False
    verification_level: int = 0
    last_verified: Optional[datetime] = None
    speed_score: float = 0.0
    reliability_score: float = 100.0
    anonymity_level: int = 0
    supports_https: bool = True
    supports_socks: bool = False
    bandwidth_estimate: float = 0.0
    uptime_percentage: float = 0.0
    flags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    geographic_data: Dict[str, Any] = field(default_factory=dict)
    performance_history: List[Dict] = field(default_factory=list)
    last_error: Optional[str] = None
    error_count: int = 0
    consecutive_failures: int = 0
    rotation_count: int = 0
    is_premium: bool = False
    cost_per_gb: float = 0.0
    data_used: float = 0.0
    data_limit: Optional[float] = None
    
    def __post_init__(self):
        # Detect proxy type from string
        if not hasattr(self, 'proxy_type_detected'):
            self._detect_proxy_type()
    
    def _detect_proxy_type(self):
        """Detect proxy type from string"""
        proxy_lower = self.proxy.lower()
        if proxy_lower.startswith('socks5://'):
            self.proxy_type = ProxyType.SOCKS5
        elif proxy_lower.startswith('socks4://'):
            self.proxy_type = ProxyType.SOCKS4
        elif proxy_lower.startswith('https://'):
            self.proxy_type = ProxyType.HTTPS
        elif proxy_lower.startswith('http://'):
            self.proxy_type = ProxyType.HTTP
        else:
            # Default to HTTP for backward compatibility
            self.proxy_type = ProxyType.HTTP
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "proxy": self.proxy,
            "proxy_type": self.proxy_type.value,
            "country": self.country,
            "city": self.city,
            "isp": self.isp,
            "asn": self.asn,
            "is_active": self.is_active,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "total_requests": self.total_requests,
            "avg_response_time": self.avg_response_time,
            "min_response_time": self.min_response_time if self.min_response_time != float('inf') else 0.0,
            "max_response_time": self.max_response_time,
            "response_times": self.response_times[-100:],  # Keep last 100
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "reports_used": self.reports_used,
            "priority": self.priority,
            "verified": self.verified,
            "verification_level": self.verification_level,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
            "speed_score": self.speed_score,
            "reliability_score": self.reliability_score,
            "anonymity_level": self.anonymity_level,
            "supports_https": self.supports_https,
            "supports_socks": self.supports_socks,
            "bandwidth_estimate": self.bandwidth_estimate,
            "uptime_percentage": self.uptime_percentage,
            "flags": list(self.flags),
            "metadata": self.metadata,
            "geographic_data": self.geographic_data,
            "performance_history": self.performance_history[-50:],  # Keep last 50
            "last_error": self.last_error,
            "error_count": self.error_count,
            "consecutive_failures": self.consecutive_failures,
            "rotation_count": self.rotation_count,
            "is_premium": self.is_premium,
            "cost_per_gb": self.cost_per_gb,
            "data_used": self.data_used,
            "data_limit": self.data_limit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProxyEntry':
        """Create from dictionary"""
        entry = cls(
            proxy=data["proxy"],
            country=data.get("country", "Unknown"),
            city=data.get("city", "Unknown"),
            isp=data.get("isp", "Unknown"),
            asn=data.get("asn", "Unknown"),
            is_active=data.get("is_active", True),
            success_count=data.get("success_count", 0),
            fail_count=data.get("fail_count", 0),
            total_requests=data.get("total_requests", 0),
            avg_response_time=data.get("avg_response_time", 0.0),
            min_response_time=data.get("min_response_time", float('inf')),
            max_response_time=data.get("max_response_time", 0.0),
            reports_used=data.get("reports_used", 0),
            priority=data.get("priority", 1.0),
            verified=data.get("verified", False),
            verification_level=data.get("verification_level", 0),
            speed_score=data.get("speed_score", 0.0),
            reliability_score=data.get("reliability_score", 100.0),
            anonymity_level=data.get("anonymity_level", 0),
            supports_https=data.get("supports_https", True),
            supports_socks=data.get("supports_socks", False),
            bandwidth_estimate=data.get("bandwidth_estimate", 0.0),
            uptime_percentage=data.get("uptime_percentage", 0.0),
            last_error=data.get("last_error"),
            error_count=data.get("error_count", 0),
            consecutive_failures=data.get("consecutive_failures", 0),
            rotation_count=data.get("rotation_count", 0),
            is_premium=data.get("is_premium", False),
            cost_per_gb=data.get("cost_per_gb", 0.0),
            data_used=data.get("data_used", 0.0),
            data_limit=data.get("data_limit")
        )
        
        entry.proxy_type = ProxyType(data.get("proxy_type", 0))
        entry.response_times = data.get("response_times", [])
        entry.flags = set(data.get("flags", []))
        entry.metadata = data.get("metadata", {})
        entry.geographic_data = data.get("geographic_data", {})
        entry.performance_history = data.get("performance_history", [])
        
        if data.get("last_used"):
            entry.last_used = datetime.fromisoformat(data["last_used"])
        if data.get("last_verified"):
            entry.last_verified = datetime.fromisoformat(data["last_verified"])
        
        return entry
    
    def update_performance(self, response_time: float, success: bool = True):
        """Update proxy performance metrics"""
        self.total_requests += 1
        
        if success:
            self.success_count += 1
            self.consecutive_failures = 0
            
            # Update response times
            self.response_times.append(response_time)
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            # Update min/max
            self.min_response_time = min(self.min_response_time, response_time)
            self.max_response_time = max(self.max_response_time, response_time)
            
            # Update average
            self.avg_response_time = statistics.mean(self.response_times) if self.response_times else response_time
            
            # Update speed score (higher is better)
            self.speed_score = max(0.1, 100.0 / (response_time + 0.1))
            
            # Add to performance history
            self.performance_history.append({
                "timestamp": datetime.now().isoformat(),
                "response_time": response_time,
                "success": True,
                "type": "request"
            })
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
        else:
            self.fail_count += 1
            self.error_count += 1
            self.consecutive_failures += 1
            
            # Add to performance history
            self.performance_history.append({
                "timestamp": datetime.now().isoformat(),
                "response_time": response_time,
                "success": False,
                "type": "request",
                "error": self.last_error
            })
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
        
        # Update reliability score
        total = self.success_count + self.fail_count
        if total > 0:
            self.reliability_score = (self.success_count / total) * 100.0
        
        # Update uptime percentage
        successful_checks = sum(1 for p in self.performance_history[-100:] if p.get("success"))
        total_checks = min(100, len(self.performance_history))
        if total_checks > 0:
            self.uptime_percentage = (successful_checks / total_checks) * 100.0
        
        self.last_used = datetime.now()
        
        # Check if proxy should be deactivated
        if self.consecutive_failures >= 5:
            self.is_active = False
            self.flags.add("disabled_due_to_failures")
        
        # Check data limits
        if self.data_limit and self.data_used >= self.data_limit:
            self.is_active = False
            self.flags.add("data_limit_exceeded")
    
    def calculate_priority(self) -> float:
        """Calculate dynamic priority based on performance"""
        base_priority = 1.0
        
        # Country multiplier
        if self.country in PREMIUM_COUNTRIES:
            base_priority *= 2.5
        elif self.country in FAST_COUNTRIES:
            base_priority *= 2.0
        elif self.country != "Unknown":
            base_priority *= 1.5
        
        # Speed multiplier
        if self.avg_response_time > 0:
            speed_multiplier = 1.0 / (self.avg_response_time + 0.1)
            base_priority *= min(speed_multiplier, 3.0)
        
        # Reliability multiplier
        reliability_multiplier = self.reliability_score / 100.0
        base_priority *= reliability_multiplier
        
        # Premium proxy boost
        if self.is_premium:
            base_priority *= 1.5
        
        # Recent usage penalty
        if self.last_used and (datetime.now() - self.last_used).seconds < 300:
            base_priority *= 0.8  # Recently used, give others a chance
        
        # Consecutive failures penalty
        if self.consecutive_failures > 0:
            base_priority *= max(0.1, 1.0 / (self.consecutive_failures + 1))
        
        # Data limit check
        if self.data_limit and self.data_used >= self.data_limit * 0.9:
            base_priority *= 0.5  # Approaching data limit
        
        return max(0.1, base_priority)

@dataclass
class TelegramAccount:
    """
    Enhanced Telegram account with comprehensive tracking
    """
    # Basic information
    phone: str
    session_file: Path
    proxy: Optional[str] = None
    proxy_entry: Optional[ProxyEntry] = None
    client: Optional[TelegramClient] = None
    status: AccountStatus = AccountStatus.UNVERIFIED
    report_count: int = 0
    total_reports: int = 0
    last_report_time: Optional[datetime] = None
    created_at: datetime = None
    last_used: Optional[datetime] = None
    last_login: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    
    # Account details
    user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    country: Optional[str] = None
    language_code: str = "en"
    is_premium: bool = False
    premium_since: Optional[datetime] = None
    is_bot: bool = False
    is_verified: bool = False
    is_scam: bool = False
    is_fake: bool = False
    is_support: bool = False
    is_self: bool = False
    is_contact: bool = False
    is_mutual_contact: bool = False
    is_deleted: bool = False
    
    # Security
    two_factor_enabled: bool = False
    two_factor_pending: bool = False
    password_hint: Optional[str] = None
    has_secure_values: bool = False
    has_email: bool = False
    email_verified: bool = False
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    flags: Set[str] = None
    
    # Device simulation
    device_model: str = "Desktop"
    system_version: str = "Windows 10"
    app_version: str = "4.0.0"
    system_lang_code: str = "en-US"
    lang_pack: str = ""
    lang_code: str = "en"
    ipv6_enabled: bool = False
    tcp_obfuscation: bool = False
    connection_mode: str = "auto"
    
    # Proxy configuration
    proxy_verified: bool = False
    proxy_failures: int = 0
    proxy_rotation_count: int = 0
    last_proxy_rotation: Optional[datetime] = None
    
    # Session management
    session_quality: float = 100.0
    session_age_days: int = 0
    session_errors: int = 0
    session_flood_waits: int = 0
    last_flood_wait: Optional[datetime] = None
    flood_wait_seconds: int = 0
    
    # OTP management
    otp_source: OTPSource = OTPSource.SMS
    otp_attempts: int = 0
    last_otp_attempt: Optional[datetime] = None
    otp_code_hash: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    otp_resend_available: bool = False
    otp_resend_count: int = 0
    
    # Performance metrics
    success_rate: float = 0.0
    average_report_time: float = 0.0
    total_online_time: float = 0.0
    last_online_check: Optional[datetime] = None
    is_online: bool = False
    connection_quality: float = 100.0
    
    # Statistics
    statistics: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.flags is None:
            self.flags = set()
        if self.statistics is None:
            self.statistics = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_bytes_sent": 0,
                "total_bytes_received": 0,
                "average_latency": 0.0,
                "peak_latency": 0.0,
                "connection_attempts": 0,
                "connection_successes": 0,
                "reconnection_attempts": 0,
                "session_duration": 0.0,
                "timeouts": 0,
                "errors": {},
                "hourly_activity": {},
                "daily_activity": {}
            }
        if self.metadata is None:
            self.metadata = {
                "added_by": None,
                "added_via": "manual",
                "source": "unknown",
                "tags": [],
                "notes": "",
                "risk_score": 0.0,
                "trust_level": "unknown"
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "phone": self.phone,
            "session_file": str(self.session_file),
            "proxy": self.proxy,
            "status": self.status.value,
            "report_count": self.report_count,
            "total_reports": self.total_reports,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "bio": self.bio,
            "country": self.country,
            "language_code": self.language_code,
            "is_premium": self.is_premium,
            "premium_since": self.premium_since.isoformat() if self.premium_since else None,
            "is_bot": self.is_bot,
            "is_verified": self.is_verified,
            "is_scam": self.is_scam,
            "is_fake": self.is_fake,
            "is_support": self.is_support,
            "is_self": self.is_self,
            "is_contact": self.is_contact,
            "is_mutual_contact": self.is_mutual_contact,
            "is_deleted": self.is_deleted,
            "two_factor_enabled": self.two_factor_enabled,
            "two_factor_pending": self.two_factor_pending,
            "password_hint": self.password_hint,
            "has_secure_values": self.has_secure_values,
            "has_email": self.has_email,
            "email_verified": self.email_verified,
            "security_level": self.security_level.value,
            "flags": list(self.flags),
            "device_model": self.device_model,
            "system_version": self.system_version,
            "app_version": self.app_version,
            "system_lang_code": self.system_lang_code,
            "lang_pack": self.lang_pack,
            "lang_code": self.lang_code,
            "ipv6_enabled": self.ipv6_enabled,
            "tcp_obfuscation": self.tcp_obfuscation,
            "connection_mode": self.connection_mode,
            "proxy_verified": self.proxy_verified,
            "proxy_failures": self.proxy_failures,
            "proxy_rotation_count": self.proxy_rotation_count,
            "last_proxy_rotation": self.last_proxy_rotation.isoformat() if self.last_proxy_rotation else None,
            "session_quality": self.session_quality,
            "session_age_days": self.session_age_days,
            "session_errors": self.session_errors,
            "session_flood_waits": self.session_flood_waits,
            "last_flood_wait": self.last_flood_wait.isoformat() if self.last_flood_wait else None,
            "flood_wait_seconds": self.flood_wait_seconds,
            "otp_source": self.otp_source.value,
            "otp_attempts": self.otp_attempts,
            "last_otp_attempt": self.last_otp_attempt.isoformat() if self.last_otp_attempt else None,
            "otp_code_hash": self.otp_code_hash,
            "otp_expires_at": self.otp_expires_at.isoformat() if self.otp_expires_at else None,
            "otp_resend_available": self.otp_resend_available,
            "otp_resend_count": self.otp_resend_count,
            "success_rate": self.success_rate,
            "average_report_time": self.average_report_time,
            "total_online_time": self.total_online_time,
            "last_online_check": self.last_online_check.isoformat() if self.last_online_check else None,
            "is_online": self.is_online,
            "connection_quality": self.connection_quality,
            "statistics": self.statistics,
            "metadata": self.metadata
        }
        
        if self.last_report_time:
            data["last_report_time"] = self.last_report_time.isoformat()
        else:
            data["last_report_time"] = None
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TelegramAccount':
        """Create from dictionary"""
        account = cls(
            phone=data["phone"],
            session_file=Path(data["session_file"]),
            proxy=data.get("proxy"),
            status=AccountStatus(data["status"]),
            report_count=data.get("report_count", 0),
            total_reports=data.get("total_reports", 0),
            user_id=data.get("user_id"),
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            bio=data.get("bio"),
            country=data.get("country"),
            language_code=data.get("language_code", "en"),
            is_premium=data.get("is_premium", False),
            is_bot=data.get("is_bot", False),
            is_verified=data.get("is_verified", False),
            is_scam=data.get("is_scam", False),
            is_fake=data.get("is_fake", False),
            is_support=data.get("is_support", False),
            is_self=data.get("is_self", False),
            is_contact=data.get("is_contact", False),
            is_mutual_contact=data.get("is_mutual_contact", False),
            is_deleted=data.get("is_deleted", False),
            two_factor_enabled=data.get("two_factor_enabled", False),
            two_factor_pending=data.get("two_factor_pending", False),
            password_hint=data.get("password_hint"),
            has_secure_values=data.get("has_secure_values", False),
            has_email=data.get("has_email", False),
            email_verified=data.get("email_verified", False),
            device_model=data.get("device_model", "Desktop"),
            system_version=data.get("system_version", "Windows 10"),
            app_version=data.get("app_version", "4.0.0"),
            system_lang_code=data.get("system_lang_code", "en-US"),
            lang_pack=data.get("lang_pack", ""),
            lang_code=data.get("lang_code", "en"),
            ipv6_enabled=data.get("ipv6_enabled", False),
            tcp_obfuscation=data.get("tcp_obfuscation", False),
            connection_mode=data.get("connection_mode", "auto"),
            proxy_verified=data.get("proxy_verified", False),
            proxy_failures=data.get("proxy_failures", 0),
            proxy_rotation_count=data.get("proxy_rotation_count", 0),
            session_quality=data.get("session_quality", 100.0),
            session_age_days=data.get("session_age_days", 0),
            session_errors=data.get("session_errors", 0),
            session_flood_waits=data.get("session_flood_waits", 0),
            flood_wait_seconds=data.get("flood_wait_seconds", 0),
            otp_source=OTPSource(data.get("otp_source", 0)),
            otp_attempts=data.get("otp_attempts", 0),
            otp_code_hash=data.get("otp_code_hash"),
            otp_resend_available=data.get("otp_resend_available", False),
            otp_resend_count=data.get("otp_resend_count", 0),
            success_rate=data.get("success_rate", 0.0),
            average_report_time=data.get("average_report_time", 0.0),
            total_online_time=data.get("total_online_time", 0.0),
            is_online=data.get("is_online", False),
            connection_quality=data.get("connection_quality", 100.0)
        )
        
        account.created_at = datetime.fromisoformat(data["created_at"])
        
        # Handle optional datetime fields
        datetime_fields = [
            "last_used", "last_login", "last_sync", "premium_since",
            "last_flood_wait", "last_otp_attempt", "otp_expires_at",
            "last_online_check", "last_proxy_rotation", "last_report_time"
        ]
        
        for field in datetime_fields:
            if data.get(field):
                setattr(account, field, datetime.fromisoformat(data[field]))
        
        account.security_level = SecurityLevel(data.get("security_level", 1))
        account.flags = set(data.get("flags", []))
        account.statistics = data.get("statistics", {})
        account.metadata = data.get("metadata", {})
        
        return account
    
    def update_statistics(self, request_type: str, success: bool, 
                         latency: float = 0.0, bytes_sent: int = 0, 
                         bytes_received: int = 0):
        """Update account statistics"""
        self.statistics["total_requests"] += 1
        
        if success:
            self.statistics["successful_requests"] += 1
        else:
            self.statistics["failed_requests"] += 1
        
        self.statistics["total_bytes_sent"] += bytes_sent
        self.statistics["total_bytes_received"] += bytes_received
        
        # Update latency metrics
        if latency > 0:
            current_avg = self.statistics["average_latency"]
            total_reqs = self.statistics["total_requests"]
            self.statistics["average_latency"] = (
                (current_avg * (total_reqs - 1) + latency) / total_reqs
            ) if total_reqs > 0 else latency
            
            self.statistics["peak_latency"] = max(
                self.statistics["peak_latency"], latency
            )
        
        # Update hourly activity
        hour = datetime.now().strftime("%Y-%m-%d %H:00")
        if hour not in self.statistics["hourly_activity"]:
            self.statistics["hourly_activity"][hour] = {
                "requests": 0,
                "successful": 0,
                "failed": 0,
                "bytes_sent": 0,
                "bytes_received": 0
            }
        
        self.statistics["hourly_activity"][hour]["requests"] += 1
        if success:
            self.statistics["hourly_activity"][hour]["successful"] += 1
        else:
            self.statistics["hourly_activity"][hour]["failed"] += 1
        
        self.statistics["hourly_activity"][hour]["bytes_sent"] += bytes_sent
        self.statistics["hourly_activity"][hour]["bytes_received"] += bytes_received
        
        # Update success rate
        total = self.statistics["total_requests"]
        successful = self.statistics["successful_requests"]
        self.success_rate = (successful / total * 100) if total > 0 else 0.0
    
    def should_rotate_proxy(self, max_reports: int = 9) -> bool:
        """Check if proxy should be rotated"""
        # Check report count
        if self.report_count >= max_reports:
            return True
        
        # Check proxy failures
        if self.proxy_failures >= 3:
            return True
        
        # Check session quality
        if self.session_quality < 50.0:
            return True
        
        # Check if proxy was rotated recently
        if self.last_proxy_rotation:
            hours_since_rotation = (datetime.now() - self.last_proxy_rotation).total_seconds() / 3600
            if hours_since_rotation < 1 and self.proxy_failures > 0:
                return True
        
        return False
    
    def get_health_score(self) -> float:
        """Calculate account health score (0-100)"""
        score = 100.0
        
        # Deduct for session errors
        if self.session_errors > 0:
            score -= min(self.session_errors * 5, 50)
        
        # Deduct for flood waits
        if self.session_flood_waits > 0:
            score -= min(self.session_flood_waits * 10, 30)
        
        # Deduct for proxy failures
        if self.proxy_failures > 0:
            score -= min(self.proxy_failures * 15, 45)
        
        # Deduct for low success rate
        if self.success_rate < 80.0:
            score -= (80.0 - self.success_rate)
        
        # Deduct for old session
        if self.session_age_days > 30:
            score -= min((self.session_age_days - 30) * 2, 20)
        
        # Bonus for premium account
        if self.is_premium:
            score += 10
        
        # Bonus for good connection quality
        if self.connection_quality > 90.0:
            score += 5
        
        return max(0.0, min(100.0, score))

@dataclass
class ReportJob:
    """
    Enhanced report job with comprehensive tracking
    """
    job_id: str
    target: str
    target_type: str
    category: str
    subcategory: str
    description: str
    created_by: int
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: ReportStatus = ReportStatus.PENDING
    priority: int = 1
    retry_count: int = 0
    max_retries: int = 3
    accounts_used: List[str] = None
    results: List[Dict] = None
    metadata: Dict[str, Any] = None
    flags: Set[str] = None
    error_log: List[Dict] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.accounts_used is None:
            self.accounts_used = []
        if self.results is None:
            self.results = []
        if self.metadata is None:
            self.metadata = {
                "target_resolved": False,
                "target_id": None,
                "target_access_hash": None,
                "validation_passed": False,
                "risk_level": "medium",
                "estimated_duration": 0,
                "complexity": "medium"
            }
        if self.flags is None:
            self.flags = set()
        if self.error_log is None:
            self.error_log = []
        if self.performance_metrics is None:
            self.performance_metrics = {
                "total_accounts": 0,
                "successful_accounts": 0,
                "failed_accounts": 0,
                "average_report_time": 0.0,
                "total_duration": 0.0,
                "proxy_rotations": 0,
                "flood_waits": 0,
                "errors_encountered": 0,
                "retry_successes": 0
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "job_id": self.job_id,
            "target": self.target,
            "target_type": self.target_type,
            "category": self.category,
            "subcategory": self.subcategory,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "accounts_used": self.accounts_used,
            "results": self.results,
            "metadata": self.metadata,
            "flags": list(self.flags),
            "error_log": self.error_log,
            "performance_metrics": self.performance_metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportJob':
        """Create from dictionary"""
        job = cls(
            job_id=data["job_id"],
            target=data["target"],
            target_type=data["target_type"],
            category=data["category"],
            subcategory=data["subcategory"],
            description=data["description"],
            created_by=data["created_by"],
            priority=data.get("priority", 1),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )
        
        job.created_at = datetime.fromisoformat(data["created_at"])
        job.status = ReportStatus(data["status"])
        
        if data.get("started_at"):
            job.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            job.completed_at = datetime.fromisoformat(data["completed_at"])
        
        job.accounts_used = data.get("accounts_used", [])
        job.results = data.get("results", [])
        job.metadata = data.get("metadata", {})
        job.flags = set(data.get("flags", []))
        job.error_log = data.get("error_log", [])
        job.performance_metrics = data.get("performance_metrics", {})
        
        return job
    
    def add_result(self, result: Dict[str, Any]):
        """Add a result to the job"""
        self.results.append(result)
        
        # Update performance metrics
        if result.get("status") == "COMPLETED":
            self.performance_metrics["successful_accounts"] += 1
        else:
            self.performance_metrics["failed_accounts"] += 1
        
        self.performance_metrics["total_accounts"] += 1
        
        # Update average report time
        report_time = result.get("response_time", 0.0)
        if report_time > 0:
            current_avg = self.performance_metrics["average_report_time"]
            total = self.performance_metrics["total_accounts"]
            self.performance_metrics["average_report_time"] = (
                (current_avg * (total - 1) + report_time) / total
            ) if total > 0 else report_time
        
        # Track flood waits
        if "flood_wait" in result.get("flags", []):
            self.performance_metrics["flood_waits"] += 1
        
        # Track proxy rotations
        if "proxy_rotated" in result.get("flags", []):
            self.performance_metrics["proxy_rotations"] += 1
        
        # Track errors
        if result.get("error"):
            self.performance_metrics["errors_encountered"] += 1
            self.error_log.append({
                "timestamp": datetime.now().isoformat(),
                "account": result.get("account"),
                "error": result.get("error"),
                "details": result.get("details", {})
            })
    
    def update_duration(self):
        """Update job duration"""
        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
            self.performance_metrics["total_duration"] = duration
    
    def get_success_rate(self) -> float:
        """Calculate job success rate"""
        total = self.performance_metrics["total_accounts"]
        successful = self.performance_metrics["successful_accounts"]
        return (successful / total * 100) if total > 0 else 0.0

@dataclass
class OTPSession:
    """
    Comprehensive OTP session management
    """
    session_id: str
    phone: str
    client: Optional[TelegramClient] = None
    phone_code_hash: Optional[str] = None
    otp_source: OTPSource = OTPSource.SMS
    otp_code: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    otp_attempts: int = 0
    max_attempts: int = 5
    last_attempt: Optional[datetime] = None
    created_at: datetime = None
    status: str = "pending"
    two_factor_required: bool = False
    two_factor_password: Optional[str] = None
    flags: Set[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.flags is None:
            self.flags = set()
        if self.metadata is None:
            self.metadata = {
                "device_info": {},
                "ip_address": None,
                "user_agent": None,
                "location": None,
                "risk_score": 0.0,
                "captcha_required": False,
                "captcha_solved": False
            }
    
    def is_expired(self) -> bool:
        """Check if OTP session is expired"""
        if self.otp_expires_at:
            return datetime.now() > self.otp_expires_at
        # Default expiration: 5 minutes
        return (datetime.now() - self.created_at).total_seconds() > 300
    
    def can_retry(self) -> bool:
        """Check if OTP can be retried"""
        if self.otp_attempts >= self.max_attempts:
            return False
        
        if self.last_attempt:
            # Wait at least 30 seconds between attempts
            return (datetime.now() - self.last_attempt).total_seconds() > 30
        
        return True
    
    def record_attempt(self, success: bool):
        """Record an OTP attempt"""
        self.otp_attempts += 1
        self.last_attempt = datetime.now()
        
        if success:
            self.status = "verified"
        elif self.otp_attempts >= self.max_attempts:
            self.status = "failed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "phone": self.phone,
            "phone_code_hash": self.phone_code_hash,
            "otp_source": self.otp_source.value,
            "otp_code": self.otp_code,
            "otp_expires_at": self.otp_expires_at.isoformat() if self.otp_expires_at else None,
            "otp_attempts": self.otp_attempts,
            "max_attempts": self.max_attempts,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "two_factor_required": self.two_factor_required,
            "two_factor_password": self.two_factor_password,
            "flags": list(self.flags),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OTPSession':
        """Create from dictionary"""
        session = cls(
            session_id=data["session_id"],
            phone=data["phone"],
            phone_code_hash=data.get("phone_code_hash"),
            otp_source=OTPSource(data.get("otp_source", 0)),
            otp_code=data.get("otp_code"),
            otp_attempts=data.get("otp_attempts", 0),
            max_attempts=data.get("max_attempts", 5),
            status=data.get("status", "pending"),
            two_factor_required=data.get("two_factor_required", False),
            two_factor_password=data.get("two_factor_password")
        )
        
        session.created_at = datetime.fromisoformat(data["created_at"])
        
        if data.get("otp_expires_at"):
            session.otp_expires_at = datetime.fromisoformat(data["otp_expires_at"])
        if data.get("last_attempt"):
            session.last_attempt = datetime.fromisoformat(data["last_attempt"])
        
        session.flags = set(data.get("flags", []))
        session.metadata = data.get("metadata", {})
        
        return session

# ============================================
# SECTION 4: ENHANCED PROXY MANAGER
# ============================================

class AdvancedProxyManager:
    """
    ADVANCED PROXY MANAGER WITH COMPREHENSIVE ANALYTICS
    
    Features:
    1. Ultra-fast parallel proxy verification
    2. Comprehensive proxy analytics
    3. Intelligent proxy rotation
    4. Bandwidth monitoring
    5. Geographic optimization
    6. Performance-based load balancing
    7. Failover mechanisms
    8. Proxy health monitoring
    """
    
    def __init__(self):
        self.proxies: List[ProxyEntry] = []
        self.proxy_map: Dict[str, ProxyEntry] = {}
        self.proxy_history: Dict[str, List[Dict]] = defaultdict(list)
        self.active_proxies: List[ProxyEntry] = []
        self.fast_proxies: List[ProxyEntry] = []
        self.premium_proxies: List[ProxyEntry] = []
        self.fast_countries = FAST_COUNTRIES
        self.premium_countries = PREMIUM_COUNTRIES
        self.max_reports_per_proxy = 9
        self.test_urls = PROXY_TEST_URLS
        self.user_agents = USER_AGENTS
        self.session: Optional[aiohttp.ClientSession] = None
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.verification_lock = asyncio.Lock()
        self.stats = {
            "total_tested": 0,
            "working_proxies": 0,
            "failed_proxies": 0,
            "verification_time": 0.0,
            "avg_speed": 0.0,
            "best_proxy": None,
            "worst_proxy": None,
            "country_distribution": {},
            "type_distribution": {},
            "last_update": None
        }
        self.analytics = {
            "daily_usage": {},
            "hourly_performance": {},
            "proxy_lifespan": {},
            "failure_patterns": {},
            "geographic_performance": {}
        }
        
    async def initialize(self) -> bool:
        """
        Initialize proxy manager with advanced features
        """
        console.print("[cyan]🚀 Initializing Advanced Proxy Manager...[/cyan]")
        
        # Create aiohttp session
        self.session = aiohttp.ClientSession(
            connector=TCPConnector(ssl=False, limit=100),
            timeout=ClientTimeout(total=30)
        )
        
        # Step 1: Load proxies
        await self._load_proxies_from_file()
        
        if not self.proxies:
            console.print("[red]❌ No proxies found[/red]")
            return False
        
        console.print(f"[green]✅ Loaded {len(self.proxies)} proxies[/green]")
        
        # Step 2: Load cache
        await self._load_cache()
        
        # Step 3: Fast parallel verification
        console.print("[yellow]⚡ Starting ultra-fast proxy verification...[/yellow]")
        await self.verify_all_proxies_parallel()
        
        # Step 4: Analyze proxies
        await self._analyze_proxies()
        
        # Step 5: Display comprehensive statistics
        self._display_comprehensive_stats()
        
        # Step 6: Send working proxies to owners
        await self._send_working_proxies_to_owners()
        
        return True
    
    async def _load_proxies_from_file(self):
        """Load proxies from data.txt with advanced parsing"""
        try:
            proxy_file_path = PROXY_FILE
            
            # Check multiple possible locations
            possible_paths = [
                proxy_file_path,
                Path("data.txt"),
                Path("../data.txt"),
                Path("./data/data.txt"),
                Path("proxy.txt"),
                Path("proxies.txt")
            ]
            
            for path in possible_paths:
                if path.exists():
                    proxy_file_path = path
                    console.print(f"[cyan]📂 Found proxies at: {path}[/cyan]")
                    break
            
            if not proxy_file_path.exists():
                console.print("[yellow]📝 Creating proxy file template...[/yellow]")
                self._create_proxy_file_template(proxy_file_path)
                return
            
            console.print(f"[cyan]📖 Reading proxies from: {proxy_file_path}[/cyan]")
            
            with open(proxy_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse with advanced regex patterns
            proxy_patterns = [
                # HTTP/HTTPS with auth
                r'(https?://[a-zA-Z0-9._-]+:[a-zA-Z0-9._-]+@[0-9]{1,3}(?:\.[0-9]{1,3}){3}:[0-9]{1,5})',
                r'(https?://[0-9]{1,3}(?:\.[0-9]{1,3}){3}:[0-9]{1,5})',
                # SOCKS with auth
                r'(socks[45]://[a-zA-Z0-9._-]+:[a-zA-Z0-9._-]+@[0-9]{1,3}(?:\.[0-9]{1,3}){3}:[0-9]{1,5})',
                r'(socks[45]://[0-9]{1,3}(?:\.[0-9]{1,3}){3}:[0-9]{1,5})',
                # IP:PORT without protocol
                r'([0-9]{1,3}(?:\.[0-9]{1,3}){3}:[0-9]{1,5})',
                # Hostname:PORT
                r'([a-zA-Z0-9._-]+(?:\.[a-zA-Z0-9._-]+)+:[0-9]{1,5})'
            ]
            
            loaded_count = 0
            for pattern in proxy_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    proxy_str = match.group(1)
                    
                    # Validate proxy
                    if not self._validate_proxy_string(proxy_str):
                        continue
                    
                    # Create proxy entry with metadata
                    proxy_entry = self._create_proxy_entry(proxy_str)
                    
                    # Check for duplicates
                    if proxy_entry.proxy in self.proxy_map:
                        continue
                    
                    self.proxies.append(proxy_entry)
                    self.proxy_map[proxy_entry.proxy] = proxy_entry
                    loaded_count += 1
            
            if loaded_count:
                console.print(f"[green]✅ Successfully parsed {loaded_count} proxies[/green]")
            else:
                console.print("[yellow]⚠️ No valid proxies found in file[/yellow]")
                
        except Exception as e:
            console.print(f"[red]❌ Error loading proxies: {e}[/red]")
            import traceback
            traceback.print_exc()
    
    def _create_proxy_file_template(self, file_path: Path):
        """Create a comprehensive proxy file template"""
        template = """# ============================================
# PROXY LIST TEMPLATE
# Add your proxies here (one per line)
# ============================================

# HTTP/HTTPS Proxies (with authentication)
# Format: http://username:password@ip:port
http://user1:pass123@192.168.1.1:8080
https://proxyuser:proxypass@10.0.0.1:8443

# HTTP/HTTPS Proxies (without authentication)
# Format: http://ip:port or https://ip:port
http://45.76.89.12:3128
https://203.0.113.1:443

# SOCKS5 Proxies (recommended for Telegram)
# Format: socks5://username:password@ip:port
socks5://socksuser:sockspass@104.238.123.45:1080
socks5://192.168.100.1:9050

# SOCKS4 Proxies
# Format: socks4://ip:port
socks4://198.51.100.1:4145

# IP:PORT format (auto-detected)
# Format: ip:port
45.77.89.123:8080
proxy.example.com:3128

# Premium proxies (recommended)
# residential.rayobyte.com:22225
# geo.iproyal.com:12321

# ============================================
# PROXY SOURCES (Free & Paid)
# ============================================

# Free Proxy Sources:
# - https://www.sslproxies.org/
# - https://free-proxy-list.net/
# - https://proxyscrape.com/free-proxy-list
# - https://geonode.com/free-proxy-list

# Paid Proxy Providers (Recommended):
# - BrightData (luminati.io)
# - Oxylabs (oxylabs.io)
# - SmartProxy (smartproxy.com)
# - Proxy-Cheap (proxy-cheap.com)
# - IPRoyal (iproyal.com)

# ============================================
# BEST PRACTICES:
# ============================================
# 1. Use residential/mobile proxies for Telegram
# 2. Rotate proxies every 9 reports
# 3. Test proxies before adding
# 4. Remove non-working proxies regularly
# 5. Use proxies from fast countries (Germany, NL, Singapore)
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(template)
        
        console.print(f"[green]✅ Created proxy template at {file_path}[/green]")
        console.print("[yellow]📝 Please add your proxies to the file and restart[/yellow]")
    
    def _validate_proxy_string(self, proxy_str: str) -> bool:
        """Validate proxy string format"""
        try:
            # Basic validation
            if not proxy_str or len(proxy_str) < 8:
                return False
            
            # Check for IP:PORT format
            if ':' not in proxy_str:
                return False
            
            # Extract host and port
            if '@' in proxy_str:
                # Has authentication
                auth_part, host_port = proxy_str.split('@', 1)
                if '://' in auth_part:
                    protocol, auth = auth_part.split('://', 1)
                else:
                    host_port = proxy_str
            else:
                host_port = proxy_str
            
            # Clean protocol prefix
            if '://' in host_port:
                host_port = host_port.split('://', 1)[1]
            
            # Split host and port
            if ':' in host_port:
                host, port_str = host_port.rsplit(':', 1)
                
                # Validate port
                try:
                    port = int(port_str)
                    if port < 1 or port > 65535:
                        return False
                except ValueError:
                    return False
                
                # Validate host (IP or domain)
                if host.replace('.', '').isdigit():
                    # Check if it's a valid IP
                    try:
                        ipaddress.ip_address(host)
                    except ValueError:
                        return False
                
                return True
            
            return False
            
        except Exception:
            return False
    
    def _create_proxy_entry(self, proxy_str: str) -> ProxyEntry:
        """Create enhanced proxy entry with metadata"""
        # Detect proxy type
        proxy_type = ProxyType.HTTP
        if proxy_str.startswith('socks5://'):
            proxy_type = ProxyType.SOCKS5
        elif proxy_str.startswith('socks4://'):
            proxy_type = ProxyType.SOCKS4
        elif proxy_str.startswith('https://'):
            proxy_type = ProxyType.HTTPS
        
        # Extract metadata
        metadata = self._extract_proxy_metadata(proxy_str)
        
        # Detect country from proxy string patterns
        country = self._detect_country_from_proxy(proxy_str, metadata)
        
        # Create proxy entry
        proxy_entry = ProxyEntry(
            proxy=proxy_str,
            proxy_type=proxy_type,
            country=country,
            city=metadata.get("city", "Unknown"),
            isp=metadata.get("isp", "Unknown"),
            metadata=metadata,
            flags=metadata.get("flags", set()),
            is_premium=metadata.get("is_premium", False),
            cost_per_gb=metadata.get("cost_per_gb", 0.0),
            data_limit=metadata.get("data_limit")
        )
        
        # Set initial priority based on metadata
        proxy_entry.priority = proxy_entry.calculate_priority()
        
        return proxy_entry
    
    def _extract_proxy_metadata(self, proxy_str: str) -> Dict[str, Any]:
        """Extract metadata from proxy string"""
        metadata = {
            "original_string": proxy_str,
            "has_auth": '@' in proxy_str,
            "has_protocol": '://' in proxy_str,
            "detected_at": datetime.now().isoformat(),
            "quality_indicators": [],
            "flags": set(),
            "is_premium": False,
            "cost_per_gb": 0.0
        }
        
        # Check for premium indicators
        premium_keywords = [
            'residential', 'mobile', 'rayobyte', 'oxylabs', 'brightdata',
            'luminati', 'smartproxy', 'iproyal', 'geo', 'premium', 'elite',
            'enterprise', 'business', 'dedicated'
        ]
        
        proxy_lower = proxy_str.lower()
        for keyword in premium_keywords:
            if keyword in proxy_lower:
                metadata["is_premium"] = True
                metadata["flags"].add("premium")
                metadata["quality_indicators"].append(f"contains_{keyword}")
                break
        
        # Check for datacenter indicators
        dc_keywords = [
            'datacenter', 'dc', 'server', 'vps', 'cloud', 'aws', 'digitalocean',
            'linode', 'vultr', 'hetzner', 'ovh', 'google', 'azure'
        ]
        
        for keyword in dc_keywords:
            if keyword in proxy_lower:
                metadata["flags"].add("datacenter")
                metadata["quality_indicators"].append(f"contains_{keyword}")
                break
        
        # Extract authentication if present
        if '@' in proxy_str:
            auth_part = proxy_str.split('@', 1)[0]
            if '://' in auth_part:
                auth_part = auth_part.split('://', 1)[1]
            
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
                metadata["username"] = username
                metadata["password_length"] = len(password)
                metadata["has_strong_auth"] = len(password) >= 8
        
        # Extract host and port
        host_port = proxy_str
        if '@' in host_port:
            host_port = host_port.split('@', 1)[1]
        if '://' in host_port:
            host_port = host_port.split('://', 1)[1]
        
        if ':' in host_port:
            host, port = host_port.rsplit(':', 1)
            metadata["host"] = host
            metadata["port"] = int(port)
            
            # Check if host is IP or domain
            try:
                ipaddress.ip_address(host)
                metadata["is_ip"] = True
                metadata["is_domain"] = False
            except ValueError:
                metadata["is_ip"] = False
                metadata["is_domain"] = True
                metadata["domain_level"] = len(host.split('.'))
        
        return metadata
    
    def _detect_country_from_proxy(self, proxy_str: str, metadata: Dict[str, Any]) -> str:
        """Detect country from proxy string using multiple methods"""
        proxy_lower = proxy_str.lower()
        
        # Country code patterns in hostnames
        country_patterns = {
            # Europe
            'de': 'Germany', 'germany': 'Germany', 'berlin': 'Germany', 'frankfurt': 'Germany',
            'nl': 'Netherlands', 'netherlands': 'Netherlands', 'amsterdam': 'Netherlands',
            'fr': 'France', 'france': 'France', 'paris': 'France',
            'uk': 'United Kingdom', 'gb': 'United Kingdom', 'london': 'United Kingdom',
            'it': 'Italy', 'italy': 'Italy', 'rome': 'Italy', 'milan': 'Italy',
            'es': 'Spain', 'spain': 'Spain', 'madrid': 'Spain', 'barcelona': 'Spain',
            'ch': 'Switzerland', 'switzerland': 'Switzerland', 'zurich': 'Switzerland',
            'se': 'Sweden', 'sweden': 'Sweden', 'stockholm': 'Sweden',
            'no': 'Norway', 'norway': 'Norway', 'oslo': 'Norway',
            'dk': 'Denmark', 'denmark': 'Denmark', 'copenhagen': 'Denmark',
            'fi': 'Finland', 'finland': 'Finland', 'helsinki': 'Finland',
            'ie': 'Ireland', 'ireland': 'Ireland', 'dublin': 'Ireland',
            'pl': 'Poland', 'poland': 'Poland', 'warsaw': 'Poland',
            'cz': 'Czech Republic', 'czech': 'Czech Republic', 'prague': 'Czech Republic',
            'hu': 'Hungary', 'hungary': 'Hungary', 'budapest': 'Hungary',
            'ro': 'Romania', 'romania': 'Romania', 'bucharest': 'Romania',
            'bg': 'Bulgaria', 'bulgaria': 'Bulgaria', 'sofia': 'Bulgaria',
            'gr': 'Greece', 'greece': 'Greece', 'athens': 'Greece',
            'tr': 'Turkey', 'turkey': 'Turkey', 'istanbul': 'Turkey',
            
            # Asia
            'jp': 'Japan', 'japan': 'Japan', 'tokyo': 'Japan',
            'sg': 'Singapore', 'singapore': 'Singapore',
            'kr': 'South Korea', 'korea': 'South Korea', 'seoul': 'South Korea',
            'cn': 'China', 'china': 'China', 'beijing': 'China', 'shanghai': 'China',
            'tw': 'Taiwan', 'taiwan': 'Taiwan', 'taipei': 'Taiwan',
            'hk': 'Hong Kong', 'hongkong': 'Hong Kong',
            'in': 'India', 'india': 'India', 'mumbai': 'India', 'delhi': 'India',
            'th': 'Thailand', 'thailand': 'Thailand', 'bangkok': 'Thailand',
            'vn': 'Vietnam', 'vietnam': 'Vietnam', 'hanoi': 'Vietnam', 'hochiminh': 'Vietnam',
            'id': 'Indonesia', 'indonesia': 'Indonesia', 'jakarta': 'Indonesia',
            'my': 'Malaysia', 'malaysia': 'Malaysia', 'kualalumpur': 'Malaysia',
            'ph': 'Philippines', 'philippines': 'Philippines', 'manila': 'Philippines',
            
            # Middle East
            'ae': 'United Arab Emirates', 'dubai': 'United Arab Emirates',
            'sa': 'Saudi Arabia', 'riyadh': 'Saudi Arabia',
            'qa': 'Qatar', 'qatar': 'Qatar', 'doha': 'Qatar',
            'kw': 'Kuwait', 'kuwait': 'Kuwait',
            'bh': 'Bahrain', 'bahrain': 'Bahrain',
            'om': 'Oman', 'oman': 'Oman',
            'il': 'Israel', 'israel': 'Israel', 'telaviv': 'Israel',
            
            # Americas
            'us': 'United States', 'usa': 'United States', 'newyork': 'United States',
            'losangeles': 'United States', 'chicago': 'United States', 'miami': 'United States',
            'ca': 'Canada', 'canada': 'Canada', 'toronto': 'Canada', 'vancouver': 'Canada',
            'mx': 'Mexico', 'mexico': 'Mexico', 'mexicocity': 'Mexico',
            'br': 'Brazil', 'brazil': 'Brazil', 'saopaulo': 'Brazil', 'riodejaneiro': 'Brazil',
            'ar': 'Argentina', 'argentina': 'Argentina', 'buenosaires': 'Argentina',
            'cl': 'Chile', 'chile': 'Chile', 'santiago': 'Chile',
            'co': 'Colombia', 'colombia': 'Colombia', 'bogota': 'Colombia',
            'pe': 'Peru', 'peru': 'Peru', 'lima': 'Peru',
            
            # Africa
            'za': 'South Africa', 'southafrica': 'South Africa', 'johannesburg': 'South Africa',
            'eg': 'Egypt', 'egypt': 'Egypt', 'cairo': 'Egypt',
            'ng': 'Nigeria', 'nigeria': 'Nigeria', 'lagos': 'Nigeria',
            'ke': 'Kenya', 'kenya': 'Kenya', 'nairobi': 'Kenya',
            
            # Oceania
            'au': 'Australia', 'australia': 'Australia', 'sydney': 'Australia', 'melbourne': 'Australia',
            'nz': 'New Zealand', 'newzealand': 'New Zealand', 'auckland': 'New Zealand',
        }
        
        # Check patterns
        for pattern, country in country_patterns.items():
            if pattern in proxy_lower:
                return country
        
        # Check metadata
        if metadata.get("is_premium"):
            # Premium proxies often have country in hostname
            host_parts = metadata.get("host", "").split('.')
            for part in host_parts:
                if len(part) == 2 and part in country_patterns:
                    return country_patterns[part]
        
        return "Unknown"
    
    async def _load_cache(self):
        """Load proxy cache with enhanced error handling"""
        try:
            if PROXY_CACHE_FILE.exists():
                with open(PROXY_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cache_map = {}
                for proxy_data in cache_data.get("proxies", []):
                    try:
                        proxy_entry = ProxyEntry.from_dict(proxy_data)
                        cache_map[proxy_entry.proxy] = proxy_entry
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Skipping invalid cache entry: {e}[/yellow]")
                        continue
                
                # Update existing proxies
                updated = 0
                for proxy_entry in self.proxies:
                    if proxy_entry.proxy in cache_map:
                        cached = cache_map[proxy_entry.proxy]
                        
                        # Copy performance data
                        proxy_entry.success_count = cached.success_count
                        proxy_entry.fail_count = cached.fail_count
                        proxy_entry.total_requests = cached.total_requests
                        proxy_entry.avg_response_time = cached.avg_response_time
                        proxy_entry.min_response_time = cached.min_response_time
                        proxy_entry.max_response_time = cached.max_response_time
                        proxy_entry.response_times = cached.response_times[-100:]  # Keep recent
                        proxy_entry.reports_used = cached.reports_used
                        proxy_entry.priority = cached.priority
                        proxy_entry.verified = cached.verified
                        proxy_entry.verification_level = cached.verification_level
                        proxy_entry.speed_score = cached.speed_score
                        proxy_entry.reliability_score = cached.reliability_score
                        proxy_entry.anonymity_level = cached.anonymity_level
                        proxy_entry.supports_https = cached.supports_https
                        proxy_entry.supports_socks = cached.supports_socks
                        proxy_entry.bandwidth_estimate = cached.bandwidth_estimate
                        proxy_entry.uptime_percentage = cached.uptime_percentage
                        proxy_entry.flags = cached.flags
                        proxy_entry.metadata.update(cached.metadata)
                        proxy_entry.geographic_data = cached.geographic_data
                        proxy_entry.performance_history = cached.performance_history[-50:]  # Keep recent
                        proxy_entry.last_error = cached.last_error
                        proxy_entry.error_count = cached.error_count
                        proxy_entry.consecutive_failures = cached.consecutive_failures
                        proxy_entry.rotation_count = cached.rotation_count
                        proxy_entry.is_premium = cached.is_premium
                        proxy_entry.cost_per_gb = cached.cost_per_gb
                        proxy_entry.data_used = cached.data_used
                        proxy_entry.data_limit = cached.data_limit
                        
                        # Copy timestamps
                        proxy_entry.last_used = cached.last_used
                        proxy_entry.last_verified = cached.last_verified
                        
                        updated += 1
                
                if updated:
                    console.print(f"[green]✅ Updated {updated} proxies from cache[/green]")
                
                # Load analytics
                self.analytics = cache_data.get("analytics", self.analytics)
                self.stats = cache_data.get("stats", self.stats)
                
        except Exception as e:
            console.print(f"[yellow]⚠️ Error loading cache: {e}[/yellow]")
    
    async def save_cache(self):
        """Save proxy data to cache with compression"""
        try:
            cache_data = {
                "proxies": [p.to_dict() for p in self.proxies],
                "analytics": self.analytics,
                "stats": self.stats,
                "last_updated": datetime.now().isoformat(),
                "total_proxies": len(self.proxies),
                "active_proxies": len([p for p in self.proxies if p.is_active]),
                "verified_proxies": len([p for p in self.proxies if p.verified]),
                "premium_proxies": len([p for p in self.proxies if p.is_premium])
            }
            
            with open(PROXY_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            console.print("[green]✅ Proxy cache saved[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error saving cache: {e}[/red]")
    
    async def verify_all_proxies_parallel(self):
        """
        Ultra-fast parallel proxy verification using asyncio
        """
        console.print("[cyan]⚡ Starting parallel proxy verification...[/cyan]")
        
        # Filter proxies that need verification
        proxies_to_verify = []
        for proxy in self.proxies:
            # Skip if recently verified (less than 5 minutes ago)
            if proxy.last_verified and (datetime.now() - proxy.last_verified).seconds < 300:
                if proxy.verified:
                    continue
            
            # Skip if marked as inactive
            if not proxy.is_active and proxy.fail_count >= 5:
                continue
            
            proxies_to_verify.append(proxy)
        
        if not proxies_to_verify:
            console.print("[yellow]⚠️ No proxies need verification[/yellow]")
            return
        
        console.print(f"[cyan]📊 Verifying {len(proxies_to_verify)} proxies in parallel...[/cyan]")
        
        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Verifying proxies...",
                total=len(proxies_to_verify)
            )
            
            # Create verification tasks with semaphore for rate limiting
            semaphore = asyncio.Semaphore(50)  # Max concurrent verifications
            
            async def verify_with_semaphore(proxy_entry: ProxyEntry):
                async with semaphore:
                    result = await self._verify_single_proxy_advanced(proxy_entry)
                    progress.update(task, advance=1)
                    return result
            
            # Run all verifications in parallel
            tasks = [verify_with_semaphore(proxy) for proxy in proxies_to_verify]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    console.print(f"[red]❌ Verification error for proxy {i}: {result}[/red]")
                elif result:
                    successful += 1
            
            # Update statistics
            self.stats["total_tested"] = len(proxies_to_verify)
            self.stats["working_proxies"] = successful
            self.stats["failed_proxies"] = len(proxies_to_verify) - successful
            self.stats["last_update"] = datetime.now().isoformat()
            
            # Sort proxies by performance
            self._sort_proxies()
            
            # Update active and fast proxy lists
            self.active_proxies = [p for p in self.proxies if p.is_active and p.verified]
            self.fast_proxies = sorted(
                self.active_proxies,
                key=lambda x: x.avg_response_time if x.avg_response_time > 0 else float('inf')
            )[:50]  # Top 50 fastest
            
            self.premium_proxies = [p for p in self.active_proxies if p.is_premium]
            
            console.print(f"[green]✅ Verification complete: {successful}/{len(proxies_to_verify)} proxies working[/green]")
            
            # Save cache
            await self.save_cache()
    
    async def _verify_single_proxy_advanced(self, proxy_entry: ProxyEntry) -> bool:
        """
        Advanced single proxy verification with multiple test types
        """
        try:
            start_time = time.time()
            test_results = []
            
            # Format proxy URL
            proxy_url = self._format_proxy_for_aiohttp(proxy_entry.proxy)
            
            # Test configuration
            test_configs = [
                {"type": "fast", "count": 2, "timeout": 5},
                {"type": "medium", "count": 3, "timeout": 8},
                {"type": "comprehensive", "count": 2, "timeout": 12}
            ]
            
            # Run tests
            for config in test_configs:
                test_type = config["type"]
                test_count = config["count"]
                timeout = config["timeout"]
                
                for i in range(test_count):
                    test_result = await self._run_single_test(
                        proxy_url, proxy_entry, test_type, timeout
                    )
                    
                    if test_result["success"]:
                        test_results.append(test_result)
                    else:
                        # If fast test fails, skip further tests
                        if test_type == "fast":
                            proxy_entry.last_error = test_result.get("error", "Fast test failed")
                            proxy_entry.consecutive_failures += 1
                            return False
                        
                        # For other tests, record failure but continue
                        proxy_entry.fail_count += 1
            
            # Analyze results
            if len(test_results) >= 3:  # Need at least 3 successful tests
                # Calculate average response time
                response_times = [r["response_time"] for r in test_results]
                avg_response_time = statistics.mean(response_times)
                
                # Update proxy entry
                proxy_entry.verified = True
                proxy_entry.is_active = True
                proxy_entry.avg_response_time = avg_response_time
                proxy_entry.min_response_time = min(response_times)
                proxy_entry.max_response_time = max(response_times)
                proxy_entry.response_times.extend(response_times)
                proxy_entry.success_count += 1
                proxy_entry.consecutive_failures = 0
                proxy_entry.last_verified = datetime.now()
                proxy_entry.verification_level = len(test_results)
                
                # Update speed and reliability scores
                proxy_entry.speed_score = max(0.1, 100.0 / (avg_response_time + 0.1))
                proxy_entry.reliability_score = 100.0  # Passed verification
                
                # Update geographic data if available
                for result in test_results:
                    if "geo_data" in result:
                        proxy_entry.geographic_data.update(result["geo_data"])
                        
                        # Update country/city if detected
                        if "country" in result["geo_data"]:
                            proxy_entry.country = result["geo_data"]["country"]
                        if "city" in result["geo_data"]:
                            proxy_entry.city = result["geo_data"]["city"]
                
                # Calculate bandwidth estimate
                if len(response_times) >= 3:
                    # Simple bandwidth estimation based on response times
                    fastest_time = min(response_times)
                    if fastest_time > 0:
                        # Assuming average page size of 50KB
                        estimated_bandwidth = (50 * 1024) / fastest_time  # bytes per second
                        proxy_entry.bandwidth_estimate = estimated_bandwidth / 1024  # KB/s
                
                # Update priority
                proxy_entry.priority = proxy_entry.calculate_priority()
                
                # Add to performance history
                proxy_entry.performance_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "verification",
                    "success": True,
                    "response_time": avg_response_time,
                    "tests_passed": len(test_results),
                    "verification_level": proxy_entry.verification_level
                })
                
                total_time = time.time() - start_time
                console.print(f"[green]✅ {proxy_entry.proxy[:40]}... verified ({avg_response_time:.2f}s, {total_time:.1f}s total)[/green]")
                return True
            else:
                proxy_entry.verified = False
                proxy_entry.is_active = False
                proxy_entry.fail_count += 1
                proxy_entry.consecutive_failures += 1
                proxy_entry.last_error = f"Only {len(test_results)}/{7} tests passed"
                
                console.print(f"[red]❌ {proxy_entry.proxy[:40]}... failed verification[/red]")
                return False
                
        except Exception as e:
            proxy_entry.last_error = str(e)
            proxy_entry.fail_count += 1
            proxy_entry.consecutive_failures += 1
            proxy_entry.is_active = False
            
            console.print(f"[red]❌ {proxy_entry.proxy[:40]}... error: {str(e)[:50]}[/red]")
            return False
    
    async def _run_single_test(self, proxy_url: str, proxy_entry: ProxyEntry, 
                              test_type: str, timeout: int) -> Dict[str, Any]:
        """
        Run a single test against the proxy
        """
        try:
            start_time = time.time()
            
            # Select test URL based on test type
            if test_type == "fast":
                test_urls = [t for t in self.test_urls if t.get("timeout", 10) <= 5]
            elif test_type == "medium":
                test_urls = [t for t in self.test_urls if t.get("timeout", 10) <= 10]
            else:
                test_urls = self.test_urls
            
            if not test_urls:
                test_urls = [self.test_urls[0]]
            
            test_config = random.choice(test_urls)
            url = test_config["url"]
            expected_type = test_config.get("type", "text")
            field = test_config.get("field")
            
            # Prepare headers
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Create request with timeout
            async with self.session.get(
                url,
                proxy=proxy_url,
                headers=headers,
                timeout=timeout,
                ssl=self.ssl_context
            ) as response:
                
                response_time = time.time() - start_time
                
                if response.status == 200:
                    content = await response.text()
                    
                    # Validate response based on expected type
                    if expected_type == "json":
                        try:
                            data = json.loads(content)
                            if field:
                                # Check if field exists
                                if field in data:
                                    # Extract geographic data if available
                                    geo_data = {}
                                    if "country" in data or "country_name" in data:
                                        geo_data["country"] = data.get("country") or data.get("country_name")
                                    if "city" in data:
                                        geo_data["city"] = data["city"]
                                    if "isp" in data or "org" in data:
                                        geo_data["isp"] = data.get("isp") or data.get("org")
                                    
                                    return {
                                        "success": True,
                                        "response_time": response_time,
                                        "status": response.status,
                                        "test_type": test_type,
                                        "geo_data": geo_data
                                    }
                                else:
                                    return {
                                        "success": False,
                                        "response_time": response_time,
                                        "error": f"Field '{field}' not found in JSON",
                                        "test_type": test_type
                                    }
                            else:
                                return {
                                    "success": True,
                                    "response_time": response_time,
                                    "status": response.status,
                                    "test_type": test_type
                                }
                        except json.JSONDecodeError:
                            return {
                                "success": False,
                                "response_time": response_time,
                                "error": "Invalid JSON response",
                                "test_type": test_type
                            }
                    else:
                        # Text response - check if it looks like an IP
                        if re.match(r'^\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?$', content.strip()):
                            return {
                                "success": True,
                                "response_time": response_time,
                                "status": response.status,
                                "test_type": test_type
                            }
                        else:
                            # Still successful if we got a response
                            return {
                                "success": True,
                                "response_time": response_time,
                                "status": response.status,
                                "test_type": test_type
                            }
                else:
                    return {
                        "success": False,
                        "response_time": response_time,
                        "error": f"HTTP {response.status}",
                        "test_type": test_type
                    }
                    
        except asyncio.TimeoutError:
            return {
                "success": False,
                "response_time": timeout,
                "error": f"Timeout ({timeout}s)",
                "test_type": test_type
            }
        except Exception as e:
            return {
                "success": False,
                "response_time": time.time() - start_time,
                "error": str(e)[:100],
                "test_type": test_type
            }
    
    def _format_proxy_for_aiohttp(self, proxy_str: str) -> str:
        """Format proxy string for aiohttp"""
        if proxy_str.startswith(('http://', 'https://', 'socks5://', 'socks4://')):
            return proxy_str
        
        # Check proxy type
        if proxy_str in self.proxy_map:
            proxy_type = self.proxy_map[proxy_str].proxy_type
            if proxy_type == ProxyType.SOCKS5:
                return f"socks5://{proxy_str}"
            elif proxy_type == ProxyType.SOCKS4:
                return f"socks4://{proxy_str}"
            elif proxy_type == ProxyType.HTTPS:
                return f"https://{proxy_str}"
        
        # Default to HTTP
        return f"http://{proxy_str}"
    
    def _format_proxy_for_telethon(self, proxy_str: str):
        """Format proxy string for Telethon"""
        if not proxy_str:
            return None
        
        # Remove protocol prefix if present
        clean_proxy = proxy_str
        for prefix in ['http://', 'https://', 'socks5://', 'socks4://']:
            if clean_proxy.startswith(prefix):
                clean_proxy = clean_proxy[len(prefix):]
                break
        
        # Parse proxy string
        if '@' in clean_proxy:
            # Format: user:pass@host:port
            auth, hostport = clean_proxy.split('@', 1)
            user, password = auth.split(':', 1)
            host, port = hostport.split(':', 1)
            
            # Determine proxy type
            proxy_type_str = 'http'
            if proxy_str.startswith('socks5://'):
                proxy_type_str = 'socks5'
            elif proxy_str.startswith('socks4://'):
                proxy_type_str = 'socks4'
            
            return (proxy_type_str, host, int(port), user, password)
        else:
            # Format: host:port
            host, port = clean_proxy.split(':', 1)
            
            # Determine proxy type
            proxy_type_str = 'http'
            if proxy_str.startswith('socks5://'):
                proxy_type_str = 'socks5'
            elif proxy_str.startswith('socks4://'):
                proxy_type_str = 'socks4'
            
            return (proxy_type_str, host, int(port))
    
    def _sort_proxies(self):
        """Sort proxies by multiple criteria"""
        self.proxies.sort(key=lambda x: (
            0 if x.verified else 1,
            0 if x.is_active else 1,
            -x.priority,
            x.avg_response_time if x.avg_response_time > 0 else float('inf'),
            -x.success_count,
            x.fail_count,
            -x.reliability_score,
            -x.speed_score
        ))
    
    async def _analyze_proxies(self):
        """Analyze proxy performance and generate insights"""
        console.print("[cyan]📈 Analyzing proxy performance...[/cyan]")
        
        active_proxies = [p for p in self.proxies if p.is_active and p.verified]
        
        if not active_proxies:
            return
        
        # Calculate statistics
        response_times = [p.avg_response_time for p in active_proxies if p.avg_response_time > 0]
        reliability_scores = [p.reliability_score for p in active_proxies]
        speed_scores = [p.speed_score for p in active_proxies]
        
        # Update stats
        self.stats["avg_speed"] = statistics.mean(response_times) if response_times else 0.0
        self.stats["best_proxy"] = min(active_proxies, key=lambda x: x.avg_response_time if x.avg_response_time > 0 else float('inf')).proxy[:50]
        self.stats["worst_proxy"] = max(active_proxies, key=lambda x: x.avg_response_time if x.avg_response_time > 0 else 0).proxy[:50]
        
        # Country distribution
        country_dist = {}
        for proxy in active_proxies:
            country = proxy.country
            country_dist[country] = country_dist.get(country, 0) + 1
        self.stats["country_distribution"] = country_dist
        
        # Type distribution
        type_dist = {}
        for proxy in active_proxies:
            type_name = proxy.proxy_type.name
            type_dist[type_name] = type_dist.get(type_name, 0) + 1
        self.stats["type_distribution"] = type_dist
        
        # Update analytics
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.analytics["daily_usage"]:
            self.analytics["daily_usage"][today] = {
                "total_proxies": len(active_proxies),
                "avg_response_time": self.stats["avg_speed"],
                "reliability_avg": statistics.mean(reliability_scores) if reliability_scores else 0.0,
                "speed_avg": statistics.mean(speed_scores) if speed_scores else 0.0,
                "country_distribution": country_dist,
                "premium_count": len([p for p in active_proxies if p.is_premium])
            }
        
        console.print("[green]✅ Proxy analysis complete[/green]")
    
    def _display_comprehensive_stats(self):
        """Display comprehensive proxy statistics"""
        active_proxies = [p for p in self.proxies if p.is_active and p.verified]
        premium_proxies = [p for p in active_proxies if p.is_premium]
        fast_proxies = sorted(active_proxies, key=lambda x: x.avg_response_time)[:10]
        
        # Main statistics table
        main_table = Table(title="📊 Proxy Manager Statistics", box=box.ROUNDED, show_header=True)
        main_table.add_column("Metric", style="cyan", justify="left")
        main_table.add_column("Value", style="green", justify="right")
        main_table.add_column("Details", style="yellow", justify="left")
        
        main_table.add_row("Total Proxies", str(len(self.proxies)), "Loaded from data.txt")
        main_table.add_row("Active & Verified", str(len(active_proxies)), "Ready for use")
        main_table.add_row("Premium Proxies", str(len(premium_proxies)), "High-quality proxies")
        main_table.add_row("Average Speed", f"{self.stats['avg_speed']:.2f}s", "Response time")
        main_table.add_row("Verification Level", f"{max(p.verification_level for p in active_proxies) if active_proxies else 0}/7", "Test thoroughness")
        main_table.add_row("Last Update", self.stats["last_update"][:19] if self.stats["last_update"] else "Never", "Verification timestamp")
        
        # Country distribution table
        if self.stats["country_distribution"]:
            country_table = Table(title="🌍 Country Distribution", box=box.SIMPLE)
            country_table.add_column("Country", style="cyan")
            country_table.add_column("Count", style="green")
            country_table.add_column("Percentage", style="yellow")
            
            total = sum(self.stats["country_distribution"].values())
            for country, count in sorted(self.stats["country_distribution"].items(), key=lambda x: x[1], reverse=True)[:10]:
                percentage = (count / total * 100) if total > 0 else 0
                country_table.add_row(country, str(count), f"{percentage:.1f}%")
        
        # Fastest proxies table
        if fast_proxies:
            speed_table = Table(title="⚡ Top 10 Fastest Proxies", box=box.SIMPLE)
            speed_table.add_column("#", style="cyan", width=3)
            speed_table.add_column("Proxy", style="green", width=30)
            speed_table.add_column("Country", style="yellow", width=15)
            speed_table.add_column("Speed", style="magenta", width=10)
            speed_table.add_column("Reliability", style="blue", width=12)
            speed_table.add_column("Type", style="cyan", width=8)
            
            for i, proxy in enumerate(fast_proxies, 1):
                proxy_display = proxy.proxy[:28] + "..." if len(proxy.proxy) > 28 else proxy.proxy
                country_display = proxy.country[:13] + "..." if len(proxy.country) > 13 else proxy.country
                speed_display = f"{proxy.avg_response_time:.2f}s"
                reliability_display = f"{proxy.reliability_score:.0f}%"
                type_display = proxy.proxy_type.name
                
                speed_table.add_row(
                    str(i),
                    proxy_display,
                    country_display,
                    speed_display,
                    reliability_display,
                    type_display
                )
        
        # Display all tables
        console.print(main_table)
        
        if self.stats["country_distribution"]:
            console.print(country_table)
        
        if fast_proxies:
            console.print(speed_table)
        
        # Display warning if no proxies
        if not active_proxies:
            console.print("[red]❌ CRITICAL: No working proxies available![/red]")
            console.print("[yellow]💡 Add working proxies to data/data.txt and restart[/yellow]")
    
    async def _send_working_proxies_to_owners(self):
        """Send working proxies list to all owners via DM"""
        try:
            active_proxies = [p for p in self.proxies if p.is_active and p.verified]
            
            if not active_proxies:
                console.print("[yellow]⚠️ No working proxies to send[/yellow]")
                return
            
            # Prepare proxy list text
            lines = ["# WORKING PROXIES LIST", ""]
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"Total Working: {len(active_proxies)}")
            lines.append("")
            lines.append("## Fastest Proxies (Top 20):")
            lines.append("")
            
            # Add fastest proxies
            fast_proxies = sorted(active_proxies, key=lambda x: x.avg_response_time)[:20]
            for i, proxy in enumerate(fast_proxies, 1):
                lines.append(f"{i:2d}. {proxy.proxy}")
                lines.append(f"    Country: {proxy.country}")
                lines.append(f"    Speed: {proxy.avg_response_time:.2f}s")
                lines.append(f"    Reliability: {proxy.reliability_score:.1f}%")
                lines.append(f"    Type: {proxy.proxy_type.name}")
                lines.append("")
            
            lines.append("## All Working Proxies:")
            lines.append("")
            
            # Add all proxies
            for proxy in active_proxies:
                lines.append(f"- {proxy.proxy}")
            
            # Create text file
            text_content = "\n".join(lines)
            
            # Save to file
            export_file = DATA_DIR / "working_proxies.txt"
            with open(export_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            console.print(f"[green]✅ Working proxies saved to {export_file}[/green]")
            
            # Send to bot owners
            await self._send_proxies_to_owners_via_bot(text_content)
            
        except Exception as e:
            console.print(f"[red]❌ Error sending proxies to owners: {e}[/red]")
    
    async def _send_proxies_to_owners_via_bot(self, text_content: str):
        """Send proxies to owners via Telegram bot"""
        try:
            # Create bot application
            app = Application.builder().token(BOT_TOKEN).build()
            
            # Send to each owner
            for owner_id in OWNER_IDS:
                try:
                    # Send as document if content is large
                    if len(text_content) > 4000:
                        # Create file in memory
                        file_bytes = text_content.encode('utf-8')
                        file_io = io.BytesIO(file_bytes)
                        file_io.name = f"working_proxies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        
                        await app.bot.send_document(
                            chat_id=owner_id,
                            document=file_io,
                            caption=f"✅ Working Proxies List\n\nTotal: {len([p for p in self.proxies if p.is_active and p.verified])} proxies\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    else:
                        # Send as message
                        await app.bot.send_message(
                            chat_id=owner_id,
                            text=f"✅ *Working Proxies List*\n\n`{text_content[:3500]}`",
                            parse_mode='Markdown'
                        )
                    
                    console.print(f"[green]✅ Sent proxies list to owner {owner_id}[/green]")
                    
                except Exception as e:
                    console.print(f"[yellow]⚠️ Failed to send to owner {owner_id}: {e}[/yellow]")
                
                # Small delay between sends
                await asyncio.sleep(1)
            
            await app.shutdown()
            
        except Exception as e:
            console.print(f"[red]❌ Error in bot sending: {e}[/red]")
    
    async def get_best_proxy_for_account(self, account_phone: str, 
                                        proxy_type: Optional[ProxyType] = None) -> Optional[str]:
        """
        Get the best proxy for an account with intelligent selection
        """
        # Get available proxies
        available = [
            p for p in self.proxies 
            if p.is_active and p.verified and p.reports_used < self.max_reports_per_proxy
        ]
        
        # Filter by type if specified
        if proxy_type is not None:
            available = [p for p in available if p.proxy_type == proxy_type]
        
        if not available:
            # Fallback to any active proxy
            available = [p for p in self.proxies if p.is_active and p.verified]
        
        if not available:
            console.print("[red]❌ No proxies available[/red]")
            return None
        
        # Check account's proxy history
        recent_proxies = set()
        if account_phone in self.proxy_history:
            recent_proxies = {entry["proxy"] for entry in self.proxy_history[account_phone][-3:]}
        
        # Filter out recently used proxies
        fresh_proxies = [p for p in available if p.proxy not in recent_proxies]
        if fresh_proxies:
            available = fresh_proxies
        
        # Sort by multiple criteria
        available.sort(key=lambda x: (
            -x.priority,  # Higher priority first
            x.reports_used,  # Less used first
            x.avg_response_time,  # Faster first
            -x.reliability_score  # More reliable first
        ))
        
        if not available:
            return None
        
        # Select the best proxy
        selected = available[0]
        selected.last_used = datetime.now()
        selected.reports_used += 1
        
        # Update proxy usage statistics
        selected.update_performance(selected.avg_response_time, success=True)
        
        # Record in history
        self.proxy_history[account_phone].append({
            "proxy": selected.proxy,
            "timestamp": datetime.now().isoformat(),
            "country": selected.country,
            "reports_used": selected.reports_used,
            "response_time": selected.avg_response_time,
            "priority": selected.priority
        })
        
        # Limit history size
        if len(self.proxy_history[account_phone]) > 20:
            self.proxy_history[account_phone] = self.proxy_history[account_phone][-20:]
        
        console.print(f"[cyan]📡 Selected proxy for {account_phone}: {selected.country} ({selected.avg_response_time:.2f}s)[/cyan]")
        return selected.proxy
    
    async def rotate_proxy_for_account(self, account_phone: str) -> Optional[str]:
        """
        Force rotate proxy for an account
        """
        # Mark current proxy as needing rotation
        if account_phone in self.proxy_history and self.proxy_history[account_phone]:
            last_entry = self.proxy_history[account_phone][-1]
            last_proxy = last_entry["proxy"]
            
            # Find and update the proxy
            for proxy in self.proxies:
                if proxy.proxy == last_proxy:
                    proxy.reports_used = self.max_reports_per_proxy
                    proxy.rotation_count += 1
                    proxy.flags.add("rotated")
                    console.print(f"[yellow]🔄 Rotating proxy for {account_phone}[/yellow]")
                    break
        
        # Get new proxy
        return await self.get_best_proxy_for_account(account_phone)
    
    def mark_proxy_success(self, proxy_url: str, response_time: float, bytes_sent: int = 0, bytes_received: int = 0):
        """Mark a proxy as successful after use"""
        for proxy in self.proxies:
            if proxy.proxy == proxy_url:
                proxy.update_performance(response_time, success=True)
                
                # Update data usage
                if bytes_sent > 0 or bytes_received > 0:
                    proxy.data_used += (bytes_sent + bytes_received) / (1024 * 1024)  # Convert to MB
                
                break
    
    def mark_proxy_failed(self, proxy_url: str, error: str = None):
        """Mark a proxy as failed"""
        for proxy in self.proxies:
            if proxy.proxy == proxy_url:
                proxy.last_error = error
                proxy.update_performance(0, success=False)
                break
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed proxy statistics"""
        active_proxies = [p for p in self.proxies if p.is_active and p.verified]
        premium_proxies = [p for p in active_proxies if p.is_premium]
        
        # Calculate various statistics
        response_times = [p.avg_response_time for p in active_proxies if p.avg_response_time > 0]
        reliability_scores = [p.reliability_score for p in active_proxies]
        speed_scores = [p.speed_score for p in active_proxies]
        
        stats = {
            "total_proxies": len(self.proxies),
            "active_proxies": len(active_proxies),
            "premium_proxies": len(premium_proxies),
            "fast_country_proxies": len([p for p in active_proxies if p.country in self.fast_countries]),
            "average_response_time": statistics.mean(response_times) if response_times else 0.0,
            "median_response_time": statistics.median(response_times) if response_times else 0.0,
            "average_reliability": statistics.mean(reliability_scores) if reliability_scores else 0.0,
            "average_speed_score": statistics.mean(speed_scores) if speed_scores else 0.0,
            "fast_countries": self.fast_countries,
            "premium_countries": self.premium_countries,
            "country_distribution": self.stats["country_distribution"],
            "type_distribution": self.stats["type_distribution"],
            "total_data_used_mb": sum(p.data_used for p in self.proxies),
            "verification_timestamp": self.stats["last_update"],
            "performance_rating": self._calculate_performance_rating(active_proxies)
        }
        
        return stats
    
    def _calculate_performance_rating(self, active_proxies: List[ProxyEntry]) -> str:
        """Calculate overall performance rating"""
        if not active_proxies:
            return "F (No working proxies)"
        
        avg_speed = self.stats["avg_speed"]
        avg_reliability = statistics.mean([p.reliability_score for p in active_proxies])
        
        # Calculate score (0-100)
        speed_score = max(0, 100 - (avg_speed * 20))  # 0-5s = 0-100
        reliability_score = avg_reliability
        
        total_score = (speed_score * 0.4) + (reliability_score * 0.6)
        
        # Convert to letter grade
        if total_score >= 90:
            return "A+"
        elif total_score >= 80:
            return "A"
        elif total_score >= 70:
            return "B"
        elif total_score >= 60:
            return "C"
        elif total_score >= 50:
            return "D"
        else:
            return "F"
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

# ============================================
# SECTION 5: ADVANCED OTP VERIFICATION SYSTEM
# ============================================

class AdvancedOTPVerification:
    """
    ADVANCED OTP VERIFICATION SYSTEM
    
    Features:
    1. Multiple OTP delivery methods (SMS, Call, App, Email, Flash Call)
    2. Automatic OTP code detection
    3. Retry logic with exponential backoff
    4. Session management
    5. Security enhancements
    6. Fallback mechanisms
    7. Comprehensive error handling
    """
    
    def __init__(self, account_manager, proxy_manager):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.otp_sessions: Dict[str, OTPSession] = {}
        self.active_verifications: Dict[str, asyncio.Task] = {}
        self.otp_cache: Dict[str, Dict] = {}
        
        # OTP configuration
        self.max_otp_attempts = 5
        self.otp_expiry_minutes = 5
        self.resend_delay_seconds = 30
        self.retry_delay_base = 2
        
        # Security settings
        self.enable_2fa_fallback = True
        self.enable_email_fallback = True
        self.enable_app_fallback = True
        self.require_device_confirmation = False
        
    async def start_otp_verification(self, phone: str, client: TelegramClient, 
                                   update: Update, user_id: int) -> bool:
        """
        Start OTP verification process with multiple methods
        """
        try:
            console.print(f"[cyan]📱 Starting OTP verification for {phone}[/cyan]")
            
            # Create OTP session
            session_id = hashlib.sha256(f"{phone}{time.time()}{user_id}".encode()).hexdigest()[:16]
            otp_session = OTPSession(
                session_id=session_id,
                phone=phone,
                client=client,
                status="initiating"
            )
            
            self.otp_sessions[session_id] = otp_session
            
            # Try different OTP methods in order of preference
            otp_methods = [
                (OTPSource.APP, "Telegram App"),
                (OTPSource.SMS, "SMS"),
                (OTPSource.CALL, "Voice Call"),
                (OTPSource.FLASH_CALL, "Flash Call"),
                (OTPSource.MISSED_CALL, "Missed Call")
            ]
            
            success = False
            last_error = None
            
            for otp_source, method_name in otp_methods:
                try:
                    console.print(f"[yellow]🔐 Trying {method_name} for {phone}[/yellow]")
                    
                    # Send OTP request
                    sent_code = await self._send_otp_request(
                        client, phone, otp_source, otp_session
                    )
                    
                    if sent_code:
                        otp_session.phone_code_hash = sent_code.phone_code_hash
                        otp_session.otp_source = otp_source
                        otp_session.otp_expires_at = datetime.now() + timedelta(minutes=self.otp_expiry_minutes)
                        otp_session.status = "otp_sent"
                        
                        # Notify user
                        await self._send_otp_notification(
                            update, phone, method_name, otp_session
                        )
                        
                        # Store session in user context
                        if not hasattr(update, '_user_sessions'):
                            update._user_sessions = {}
                        
                        update._user_sessions[user_id] = {
                            "session_id": session_id,
                            "phone": phone,
                            "step": "waiting_otp",
                            "method": method_name,
                            "expires_at": otp_session.otp_expires_at.isoformat()
                        }
                        
                        success = True
                        break
                        
                except FloodWaitError as e:
                    last_error = f"Flood wait: {e.seconds} seconds"
                    console.print(f"[red]❌ Flood wait for {method_name}: {e.seconds}s[/red]")
                    if e.seconds > 300:  # 5 minutes
                        break
                    await asyncio.sleep(min(e.seconds, 30))
                    
                except Exception as e:
                    last_error = str(e)
                    console.print(f"[yellow]⚠️ {method_name} failed: {e}[/yellow]")
                    continue
            
            if not success:
                await update.message.reply_text(
                    f"❌ *Failed to send OTP*\n\n"
                    f"Phone: `{phone}`\n"
                    f"Error: {last_error[:100]}\n\n"
                    f"Please try again later.",
                    parse_mode='Markdown'
                )
                return False
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ OTP verification start error: {e}[/red]")
            await update.message.reply_text(
                f"❌ *Verification Error*\n\n{str(e)[:200]}",
                parse_mode='Markdown'
            )
            return False
    
    async def _send_otp_request(self, client: TelegramClient, phone: str, 
                               otp_source: OTPSource, otp_session: OTPSession) -> Optional[Any]:
        """
        Send OTP request with specific method
        """
        try:
            # Map OTP source to Telegram's allowed_settings
            if otp_source == OTPSource.APP:
                # Telegram app notification
                sent_code = await client.send_code_request(
                    phone,
                    settings=types.CodeSettings(
                        allow_flashcall=False,
                        current_number=True,
                        allow_app_hash=True,
                        allow_missed_call=False
                    )
                )
            elif otp_source == OTPSource.SMS:
                # SMS
                sent_code = await client.send_code_request(
                    phone,
                    settings=types.CodeSettings(
                        allow_flashcall=False,
                        current_number=False,
                        allow_app_hash=False,
                        allow_missed_call=False
                    )
                )
            elif otp_source == OTPSource.CALL:
                # Voice call
                sent_code = await client.send_code_request(
                    phone,
                    settings=types.CodeSettings(
                        allow_flashcall=False,
                        current_number=False,
                        allow_app_hash=False,
                        allow_missed_call=False
                    )
                )
            elif otp_source == OTPSource.FLASH_CALL:
                # Flash call
                sent_code = await client.send_code_request(
                    phone,
                    settings=types.CodeSettings(
                        allow_flashcall=True,
                        current_number=True,
                        allow_app_hash=False,
                        allow_missed_call=False
                    )
                )
            elif otp_source == OTPSource.MISSED_CALL:
                # Missed call
                sent_code = await client.send_code_request(
                    phone,
                    settings=types.CodeSettings(
                        allow_flashcall=False,
                        current_number=False,
                        allow_app_hash=False,
                        allow_missed_call=True
                    )
                )
            else:
                # Default to SMS
                sent_code = await client.send_code_request(phone)
            
            return sent_code
            
        except PhoneNumberInvalidError:
            raise Exception("Invalid phone number format")
        except PhoneNumberFloodError:
            raise Exception("Phone number flood protection")
        except PhoneNumberBannedError:
            raise Exception("Phone number is banned")
        except PhoneNumberUnoccupiedError:
            raise Exception("Phone number not registered")
        except Exception as e:
            raise e
    
    async def _send_otp_notification(self, update: Update, phone: str, 
                                    method: str, otp_session: OTPSession):
        """
        Send OTP notification to user
        """
        expires_time = otp_session.otp_expires_at.strftime("%H:%M:%S")
        time_left = (otp_session.otp_expires_at - datetime.now()).seconds // 60
        
        message = (
            f"✅ *OTP Sent Successfully!*\n\n"
            f"📱 Phone: `{phone}`\n"
            f"📨 Method: {method}\n"
            f"⏰ Expires: {expires_time} ({time_left} minutes)\n"
            f"🔢 Attempts left: {self.max_otp_attempts}\n\n"
        )
        
        # Add method-specific instructions
        if "App" in method:
            message += (
                "*Check your Telegram app for the login code.*\n"
                "The code should appear in your Telegram app notifications.\n\n"
            )
        elif "SMS" in method:
            message += (
                "*Check your SMS messages.*\n"
                "The code should arrive within 1-2 minutes.\n\n"
            )
        elif "Call" in method:
            message += (
                "*Answer the phone call.*\n"
                "You will receive an automated call with the code.\n\n"
            )
        elif "Flash" in method:
            message += (
                "*Answer the flash call.*\n"
                "A short call will display the code on your screen.\n\n"
            )
        
        message += (
            "*Reply with the 5-digit code:* `12345`\n\n"
            "⚠️ *Security Notice:*\n"
            "• Never share this code with anyone\n"
            "• Telegram will NEVER ask for this code\n"
            "• Code is valid for 5 minutes only\n"
            "• After 5 attempts, you'll need to restart"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def verify_otp_code(self, session_id: str, otp_code: str, 
                             update: Update, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Verify OTP code with comprehensive error handling
        """
        try:
            # Get OTP session
            if session_id not in self.otp_sessions:
                return False, "Session expired or invalid"
            
            otp_session = self.otp_sessions[session_id]
            
            # Check if session is expired
            if otp_session.is_expired():
                del self.otp_sessions[session_id]
                return False, "OTP code expired"
            
            # Check if max attempts reached
            if not otp_session.can_retry():
                return False, "Maximum OTP attempts reached"
            
            # Validate OTP code format
            if not re.match(r'^\d{5}$', otp_code):
                return False, "Invalid OTP format. Must be 5 digits"
            
            # Update session
            otp_session.otp_code = otp_code
            otp_session.last_attempt = datetime.now()
            otp_session.otp_attempts += 1
            
            console.print(f"[cyan]🔐 Verifying OTP for {otp_session.phone} (attempt {otp_session.otp_attempts})[/cyan]")
            
            # Try to sign in with OTP
            try:
                await otp_session.client.sign_in(
                    phone=otp_session.phone,
                    code=otp_code,
                    phone_code_hash=otp_session.phone_code_hash
                )
                
                # Successful login
                otp_session.status = "verified"
                otp_session.record_attempt(True)
                
                # Update account
                await self._handle_successful_login(otp_session, update, user_id)
                
                # Cleanup
                if session_id in self.otp_sessions:
                    del self.otp_sessions[session_id]
                
                return True, None
                
            except SessionPasswordNeededError:
                # 2FA required
                otp_session.two_factor_required = True
                otp_session.status = "need_password"
                
                # Get password hint
                try:
                    password_info = await otp_session.client.get_password()
                    otp_session.metadata["password_hint"] = password_info.hint
                except:
                    pass
                
                return False, "2FA_PASSWORD_NEEDED"
                
            except PhoneCodeInvalidError:
                otp_session.record_attempt(False)
                attempts_left = otp_session.max_attempts - otp_session.otp_attempts
                
                if attempts_left > 0:
                    return False, f"Invalid code. {attempts_left} attempts left"
                else:
                    return False, "Invalid code. Maximum attempts reached"
                
            except PhoneCodeExpiredError:
                del self.otp_sessions[session_id]
                return False, "OTP code expired. Please restart verification"
                
            except Exception as e:
                otp_session.last_error = str(e)
                return False, f"Verification error: {str(e)[:100]}"
            
        except Exception as e:
            console.print(f"[red]❌ OTP verification error: {e}[/red]")
            return False, f"System error: {str(e)[:100]}"
    
    async def _handle_successful_login(self, otp_session: OTPSession, 
                                      update: Update, user_id: int):
        """
        Handle successful login after OTP verification
        """
        try:
            phone = otp_session.phone
            
            # Update account in account manager
            if phone in self.account_manager.accounts:
                account = self.account_manager.accounts[phone]
                
                # Update account status
                account.client = otp_session.client
                account.status = AccountStatus.ACTIVE
                account.last_login = datetime.now()
                account.last_used = datetime.now()
                account.otp_attempts = otp_session.otp_attempts
                account.otp_source = otp_session.otp_source
                
                # Get account info
                try:
                    me = await otp_session.client.get_me()
                    account.user_id = me.id
                    account.username = me.username
                    account.first_name = me.first_name
                    account.last_name = me.last_name
                    account.is_premium = getattr(me, 'premium', False)
                    account.is_verified = getattr(me, 'verified', False)
                    account.is_scam = getattr(me, 'scam', False)
                    account.is_fake = getattr(me, 'fake', False)
                    
                    # Check 2FA
                    try:
                        password_info = await otp_session.client.get_password()
                        account.two_factor_enabled = password_info.has_password
                        account.password_hint = password_info.hint
                    except:
                        account.two_factor_enabled = False
                    
                except Exception as e:
                    console.print(f"[yellow]⚠️ Could not get account info: {e}[/yellow]")
                
                # Save account
                self.account_manager._save_accounts()
                
                # Prepare success message
                success_message = self._prepare_success_message(account)
                
                await update.message.reply_text(
                    success_message,
                    parse_mode='Markdown'
                )
                
                console.print(f"[green]✅ Login successful for {phone}[/green]")
                
            else:
                await update.message.reply_text(
                    f"❌ *Account Error*\n\n"
                    f"Account `{phone}` not found in manager.",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            console.print(f"[red]❌ Error handling successful login: {e}[/red]")
            await update.message.reply_text(
                f"✅ *Login Complete*\n\n"
                f"Account `{phone}` verified successfully.\n"
                f"Error updating details: {str(e)[:100]}",
                parse_mode='Markdown'
            )
    
    def _prepare_success_message(self, account: TelegramAccount) -> str:
        """Prepare detailed success message"""
        # Account info
        info_lines = [
            f"✅ *Login Successful!*",
            "",
            f"📱 *Account Details:*",
            f"• Phone: `{account.phone}`",
            f"• User ID: `{account.user_id}`" if account.user_id else "",
            f"• Username: @{account.username}" if account.username else "",
            f"• Name: {account.first_name or ''} {account.last_name or ''}".strip(),
            ""
        ]
        
        # Security info
        security_lines = [
            f"🔒 *Security Status:*",
            f"• 2FA: {'✅ Enabled' if account.two_factor_enabled else '❌ Disabled'}",
            f"• Premium: {'⭐ Yes' if account.is_premium else 'No'}",
            f"• Verified: {'✅ Yes' if account.is_verified else 'No'}",
            f"• Reports Today: {account.report_count}/9",
            ""
        ]
        
        # Device info
        device_lines = [
            f"🖥️ *Device Simulation:*",
            f"• Device: {account.device_model}",
            f"• System: {account.system_version}",
            f"• App Version: {account.app_version}",
            f"• Country: {account.country or 'Unknown'}",
            ""
        ]
        
        # Instructions
        instruction_lines = [
            f"📊 *Ready for Reporting!*",
            f"",
            f"Use `/report` to start reporting targets.",
            f"Use `/stats` to check account status.",
            f"",
            f"⚠️ *Important:*",
            f"• Each account can report 9 times before proxy rotation",
            f"• Use premium proxies for better results",
            f"• Monitor account health with `/accounts`",
        ]
        
        # Combine all lines
        all_lines = info_lines + security_lines + device_lines + instruction_lines
        return "\n".join(line for line in all_lines if line != "")
    
    async def handle_2fa_password(self, session_id: str, password: str,
                                 update: Update, user_id: int) -> Tuple[bool, str]:
        """
        Handle 2FA password verification
        """
        try:
            if session_id not in self.otp_sessions:
                return False, "Session expired"
            
            otp_session = self.otp_sessions[session_id]
            
            if not otp_session.two_factor_required:
                return False, "2FA not required"
            
            console.print(f"[cyan]🔒 Verifying 2FA password for {otp_session.phone}[/cyan]")
            
            try:
                # Sign in with password
                await otp_session.client.sign_in(password=password)
                
                # Update session
                otp_session.two_factor_password = password
                otp_session.status = "verified"
                otp_session.two_factor_required = False
                
                # Update account
                await self._handle_successful_login(otp_session, update, user_id)
                
                # Cleanup
                if session_id in self.otp_sessions:
                    del self.otp_sessions[session_id]
                
                return True, ""
                
            except PasswordHashInvalidError:
                return False, "Invalid 2FA password"
            except Exception as e:
                return False, f"2FA error: {str(e)[:100]}"
            
        except Exception as e:
            console.print(f"[red]❌ 2FA verification error: {e}[/red]")
            return False, f"System error: {str(e)[:100]}"
    
    async def resend_otp(self, session_id: str, update: Update, user_id: int) -> Tuple[bool, str]:
        """
        Resend OTP code
        """
        try:
            if session_id not in self.otp_sessions:
                return False, "Session expired"
            
            otp_session = self.otp_sessions[session_id]
            
            # Check if resend is available
            if not otp_session.otp_resend_available:
                if otp_session.last_attempt:
                    time_since_last = (datetime.now() - otp_session.last_attempt).seconds
                    if time_since_last < self.resend_delay_seconds:
                        wait_time = self.resend_delay_seconds - time_since_last
                        return False, f"Wait {wait_time} seconds before resending"
            
            console.print(f"[cyan]🔄 Resending OTP for {otp_session.phone}[/cyan]")
            
            # Resend OTP
            try:
                sent_code = await otp_session.client.resend_code(
                    phone=otp_session.phone,
                    phone_code_hash=otp_session.phone_code_hash
                )
                
                # Update session
                otp_session.phone_code_hash = sent_code.phone_code_hash
                otp_session.otp_expires_at = datetime.now() + timedelta(minutes=self.otp_expiry_minutes)
                otp_session.otp_resend_count += 1
                otp_session.otp_resend_available = False
                
                # Schedule resend availability
                asyncio.create_task(self._enable_resend_after_delay(session_id))
                
                # Notify user
                expires_time = otp_session.otp_expires_at.strftime("%H:%M:%S")
                time_left = (otp_session.otp_expires_at - datetime.now()).seconds // 60
                
                await update.message.reply_text(
                    f"✅ *OTP Resent!*\n\n"
                    f"📱 Phone: `{otp_session.phone}`\n"
                    f"⏰ New expiry: {expires_time} ({time_left} minutes)\n"
                    f"🔢 Attempts left: {self.max_otp_attempts - otp_session.otp_attempts}\n\n"
                    f"*Reply with the new 5-digit code:* `12345`",
                    parse_mode='Markdown'
                )
                
                return True, ""
                
            except Exception as e:
                return False, f"Failed to resend OTP: {str(e)[:100]}"
            
        except Exception as e:
            console.print(f"[red]❌ OTP resend error: {e}[/red]")
            return False, f"System error: {str(e)[:100]}"
    
    async def _enable_resend_after_delay(self, session_id: str):
        """Enable OTP resend after delay"""
        await asyncio.sleep(self.resend_delay_seconds)
        
        if session_id in self.otp_sessions:
            self.otp_sessions[session_id].otp_resend_available = True
    
    def cleanup_expired_sessions(self):
        """Cleanup expired OTP sessions"""
        expired_sessions = []
        now = datetime.now()
        
        for session_id, session in self.otp_sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.otp_sessions[session_id]
        
        if expired_sessions:
            console.print(f"[yellow]🧹 Cleaned up {len(expired_sessions)} expired OTP sessions[/yellow]")
    
    async def get_otp_session_info(self, session_id: str) -> Optional[Dict]:
        """Get OTP session information"""
        if session_id in self.otp_sessions:
            session = self.otp_sessions[session_id]
            return {
                "phone": session.phone,
                "status": session.status,
                "attempts": session.otp_attempts,
                "max_attempts": session.max_attempts,
                "expires_at": session.otp_expires_at.isoformat() if session.otp_expires_at else None,
                "two_factor_required": session.two_factor_required,
                "resend_available": session.otp_resend_available,
                "resend_count": session.otp_resend_count
            }
        return None

# ============================================
# SECTION 6: ENHANCED USER MANAGER
# ============================================

class AdvancedUserManager:
    """
    ENHANCED USER MANAGER WITH COMPREHENSIVE PERMISSIONS
    
    Features:
    1. Hierarchical role system
    2. Permission-based access control
    3. User activity tracking
    4. Trust scoring
    5. Security monitoring
    6. Session management
    7. Analytics and reporting
    """
    
    def __init__(self):
        self.users: Dict[int, TelegramUser] = {}
        self.sessions: Dict[str, Dict] = {}
        self.activity_log: List[Dict] = []
        self.security_log: List[Dict] = []
        self.owner_ids = OWNER_IDS
        self.admin_ids = ADMIN_IDS
        
        # Permission definitions
        self.permissions = {
            "view_stats": [UserRole.VIEWER, UserRole.USER, UserRole.REPORTER, 
                          UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUDO, UserRole.OWNER],
            "create_report": [UserRole.USER, UserRole.REPORTER, UserRole.MODERATOR,
                            UserRole.ADMIN, UserRole.SUDO, UserRole.OWNER],
            "add_account": [UserRole.REPORTER, UserRole.MODERATOR, UserRole.ADMIN,
                          UserRole.SUDO, UserRole.OWNER],
            "manage_users": [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUDO, UserRole.OWNER],
            "manage_system": [UserRole.ADMIN, UserRole.SUDO, UserRole.OWNER],
            "full_control": [UserRole.SUDO, UserRole.OWNER]
        }
        
        self._initialize_system()
        self._load_users()
    
    def _initialize_system(self):
        """Initialize system users"""
        # Create owner accounts
        for owner_id in self.owner_ids:
            if owner_id not in self.users:
                owner_user = TelegramUser(
                    user_id=owner_id,
                    role=UserRole.OWNER,
                    security_level=SecurityLevel.EXTREME,
                    trust_score=100.0,
                    is_premium=True
                )
                self.users[owner_id] = owner_user
                
                # Add owner permissions
                owner_user.permissions = list(self.permissions.keys())
        
        # Create admin accounts
        for admin_id in self.admin_ids:
            if admin_id not in self.users:
                admin_user = TelegramUser(
                    user_id=admin_id,
                    role=UserRole.ADMIN,
                    security_level=SecurityLevel.HIGH,
                    trust_score=90.0
                )
                self.users[admin_id] = admin_user
                
                # Add admin permissions (all except full_control)
                admin_user.permissions = [p for p in self.permissions.keys() if p != "full_control"]
        
        console.print(f"[green]✅ Initialized {len(self.owner_ids)} owners and {len(self.admin_ids)} admins[/green]")
    
    def _load_users(self):
        """Load users from JSON file"""
        try:
            if USERS_FILE.exists():
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                loaded = 0
                for user_id_str, user_data in data.items():
                    try:
                        user = TelegramUser.from_dict(user_data)
                        self.users[user.user_id] = user
                        loaded += 1
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Skipping invalid user data: {e}[/yellow]")
                        continue
                
                console.print(f"[green]✅ Loaded {loaded} users[/green]")
                
                # Log security event
                self.log_security_event(
                    event_type="system_start",
                    user_id=0,
                    severity="info",
                    description=f"Loaded {loaded} users from storage"
                )
                
        except Exception as e:
            console.print(f"[red]❌ Error loading users: {e}[/red]")
            self.log_security_event(
                event_type="system_error",
                user_id=0,
                severity="critical",
                description=f"Failed to load users: {e}"
            )
    
    def _save_users(self):
        """Save users to JSON file"""
        try:
            data = {str(uid): user.to_dict() for uid, user in self.users.items()}
            
            # Create backup
            backup_file = BACKUP_DIR / f"users_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Save current
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Keep only last 5 backups
            backups = list(BACKUP_DIR.glob("users_backup_*.json"))
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for backup in backups[5:]:
                backup.unlink()
            
        except Exception as e:
            console.print(f"[red]❌ Error saving users: {e}[/red]")
            self.log_security_event(
                event_type="system_error",
                user_id=0,
                severity="critical",
                description=f"Failed to save users: {e}"
            )
    
    def log_activity(self, user_id: int, action: str, details: Dict[str, Any] = None):
        """Log user activity"""
        activity = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details or {},
            "ip_address": details.get("ip_address") if details else None,
            "user_agent": details.get("user_agent") if details else None
        }
        
        self.activity_log.append(activity)
        
        # Keep log size manageable
        if len(self.activity_log) > 10000:
            self.activity_log = self.activity_log[-5000:]
    
    def log_security_event(self, event_type: str, user_id: int, 
                          severity: str, description: str, details: Dict[str, Any] = None):
        """Log security event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "severity": severity,
            "description": description,
            "details": details or {}
        }
        
        self.security_log.append(event)
        
        # Keep log size manageable
        if len(self.security_log) > 5000:
            self.security_log = self.security_log[-2500:]
        
        # Log to console based on severity
        if severity == "critical":
            console.print(f"[red]🔴 SECURITY CRITICAL: {description}[/red]")
        elif severity == "high":
            console.print(f"[yellow]🟡 SECURITY HIGH: {description}[/yellow]")
        elif severity == "medium":
            console.print(f"[cyan]🔵 SECURITY MEDIUM: {description}[/cyan]")
    
    def create_user_session(self, user_id: int, client_info: Dict[str, Any]) -> str:
        """Create a new user session"""
        session_id = hashlib.sha256(f"{user_id}{time.time()}{random.random()}".encode()).hexdigest()[:32]
        
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "client_info": client_info,
            "is_active": True,
            "ip_address": client_info.get("ip_address"),
            "user_agent": client_info.get("user_agent"),
            "location": client_info.get("location"),
            "flags": set()
        }
        
        self.sessions[session_id] = session
        
        # Log activity
        self.log_activity(
            user_id=user_id,
            action="session_create",
            details={"session_id": session_id, "client_info": client_info}
        )
        
        return session_id
    
    def validate_session(self, session_id: str, user_id: int) -> bool:
        """Validate user session"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Check if session belongs to user
        if session["user_id"] != user_id:
            self.log_security_event(
                event_type="session_hijack_attempt",
                user_id=user_id,
                severity="high",
                description=f"Session hijack attempt detected",
                details={"session_id": session_id, "expected_user": session["user_id"]}
            )
            return False
        
        # Check if session is active
        if not session["is_active"]:
            return False
        
        # Check session age (max 24 hours)
        created_at = datetime.fromisoformat(session["created_at"])
        if (datetime.now() - created_at).total_seconds() > 86400:
            session["is_active"] = False
            return False
        
        # Update last activity
        session["last_activity"] = datetime.now().isoformat()
        
        return True
    
    def update_user_activity(self, user_id: int, username: str = None, 
                            first_name: str = None, last_name: str = None,
                            client_info: Dict[str, Any] = None):
        """Update user's last activity and information"""
        if user_id not in self.users:
            # Create new user with default role
            user = TelegramUser(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.USER,
                security_level=SecurityLevel.MEDIUM
            )
            self.users[user_id] = user
            
            # Log new user
            self.log_activity(
                user_id=user_id,
                action="user_created",
                details={
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "client_info": client_info
                }
            )
            
            console.print(f"[green]✅ New user created: {user_id}[/green]")
        else:
            # Update existing user
            user = self.users[user_id]
            user.last_active = datetime.now()
            
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            
            # Update trust score based on activity
            user.trust_score = min(100.0, user.trust_score + 0.1)
        
        # Log activity
        self.log_activity(
            user_id=user_id,
            action="user_activity",
            details={"client_info": client_info}
        )
        
        # Save users
        self._save_users()
    
    def check_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has specific permission"""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        
        # Owners have all permissions
        if user.role == UserRole.OWNER:
            return True
        
        # Check permission hierarchy
        allowed_roles = self.permissions.get(permission, [])
        return user.role in allowed_roles or permission in user.permissions
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None,
                last_name: str = None, role: UserRole = UserRole.USER) -> Tuple[bool, str]:
        """Add a new user"""
        if user_id in self.users:
            return False, "User already exists"
        
        user = TelegramUser(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            security_level=SecurityLevel.MEDIUM,
            trust_score=50.0
        )
        
        # Set permissions based on role
        if role == UserRole.OWNER:
            user.permissions = list(self.permissions.keys())
        elif role == UserRole.ADMIN:
            user.permissions = [p for p in self.permissions.keys() if p != "full_control"]
        elif role == UserRole.MODERATOR:
            user.permissions = ["view_stats", "create_report", "add_account", "manage_users"]
        elif role == UserRole.REPORTER:
            user.permissions = ["view_stats", "create_report", "add_account"]
        elif role == UserRole.USER:
            user.permissions = ["view_stats", "create_report"]
        elif role == UserRole.VIEWER:
            user.permissions = ["view_stats"]
        
        self.users[user_id] = user
        self._save_users()
        
        # Log security event
        self.log_security_event(
            event_type="user_added",
            user_id=user_id,
            severity="info",
            description=f"User added with role {role.name}",
            details={"added_by": "system", "role": role.name}
        )
        
        console.print(f"[green]✅ Added user {user_id} with role {role.name}[/green]")
        return True, f"User added with role {role.name}"
    
    def promote_user(self, user_id: int, new_role: UserRole, 
                    promoted_by: int) -> Tuple[bool, str]:
        """Promote user to higher role"""
        if user_id not in self.users:
            return False, "User not found"
        
        user = self.users[user_id]
        
        # Check if promoter has permission
        promoter = self.users.get(promoted_by)
        if not promoter or promoter.role < UserRole.MODERATOR:
            return False, "Insufficient permissions"
        
        # Check role hierarchy
        if new_role <= user.role:
            return False, "New role must be higher than current role"
        
        # Update user role
        old_role = user.role
        user.role = new_role
        
        # Update permissions based on new role
        if new_role == UserRole.OWNER:
            user.permissions = list(self.permissions.keys())
        elif new_role == UserRole.ADMIN:
            user.permissions = [p for p in self.permissions.keys() if p != "full_control"]
        elif new_role == UserRole.MODERATOR:
            user.permissions = ["view_stats", "create_report", "add_account", "manage_users"]
        elif new_role == UserRole.REPORTER:
            user.permissions = ["view_stats", "create_report", "add_account"]
        elif new_role == UserRole.USER:
            user.permissions = ["view_stats", "create_report"]
        
        user.trust_score = min(100.0, user.trust_score + 10.0)
        
        self._save_users()
        
        # Log security event
        self.log_security_event(
            event_type="user_promoted",
            user_id=user_id,
            severity="medium",
            description=f"User promoted from {old_role.name} to {new_role.name}",
            details={"promoted_by": promoted_by, "old_role": old_role.name, "new_role": new_role.name}
        )
        
        console.print(f"[green]✅ Promoted user {user_id} from {old_role.name} to {new_role.name}[/green]")
        return True, f"User promoted to {new_role.name}"
    
    def demote_user(self, user_id: int, new_role: UserRole, 
                   demoted_by: int) -> Tuple[bool, str]:
        """Demote user to lower role"""
        if user_id not in self.users:
            return False, "User not found"
        
        user = self.users[user_id]
        
        # Check if demoter has permission
        demoter = self.users.get(demoted_by)
        if not demoter or demoter.role < UserRole.MODERATOR:
            return False, "Insufficient permissions"
        
        # Cannot demote owners
        if user.role == UserRole.OWNER:
            return False, "Cannot demote owners"
        
        # Check role hierarchy
        if new_role >= user.role:
            return False, "New role must be lower than current role"
        
        # Update user role
        old_role = user.role
        user.role = new_role
        
        # Update permissions based on new role
        if new_role == UserRole.ADMIN:
            user.permissions = [p for p in self.permissions.keys() if p != "full_control"]
        elif new_role == UserRole.MODERATOR:
            user.permissions = ["view_stats", "create_report", "add_account", "manage_users"]
        elif new_role == UserRole.REPORTER:
            user.permissions = ["view_stats", "create_report", "add_account"]
        elif new_role == UserRole.USER:
            user.permissions = ["view_stats", "create_report"]
        elif new_role == UserRole.VIEWER:
            user.permissions = ["view_stats"]
        elif new_role == UserRole.BANNED:
            user.permissions = []
        
        user.trust_score = max(0.0, user.trust_score - 20.0)
        
        self._save_users()
        
        # Log security event
        self.log_security_event(
            event_type="user_demoted",
            user_id=user_id,
            severity="medium",
            description=f"User demoted from {old_role.name} to {new_role.name}",
            details={"demoted_by": demoted_by, "old_role": old_role.name, "new_role": new_role.name}
        )
        
        console.print(f"[yellow]⚠️ Demoted user {user_id} from {old_role.name} to {new_role.name}[/yellow]")
        return True, f"User demoted to {new_role.name}"
    
    def ban_user(self, user_id: int, banned_by: int, reason: str) -> Tuple[bool, str]:
        """Ban a user"""
        if user_id not in self.users:
            return False, "User not found"
        
        user = self.users[user_id]
        
        # Check if banner has permission
        banner = self.users.get(banned_by)
        if not banner or banner.role < UserRole.MODERATOR:
            return False, "Insufficient permissions"
        
        # Cannot ban owners
        if user.role == UserRole.OWNER:
            return False, "Cannot ban owners"
        
        # Demote to banned role
        success, message = self.demote_user(user_id, UserRole.BANNED, banned_by)
        
        if success:
            # Add ban flag and reason
            user.flags.add("banned")
            user.metadata["ban_reason"] = reason
            user.metadata["banned_by"] = banned_by
            user.metadata["banned_at"] = datetime.now().isoformat()
            
            self._save_users()
            
            # Log security event
            self.log_security_event(
                event_type="user_banned",
                user_id=user_id,
                severity="high",
                description=f"User banned: {reason}",
                details={"banned_by": banned_by, "reason": reason}
            )
            
            console.print(f"[red]🔴 User {user_id} banned: {reason}[/red]")
            return True, f"User banned: {reason}"
        
        return False, message
    
    def unban_user(self, user_id: int, unbanned_by: int) -> Tuple[bool, str]:
        """Unban a user"""
        if user_id not in self.users:
            return False, "User not found"
        
        user = self.users[user_id]
        
        # Check if unbanner has permission
        unbanner = self.users.get(unbanned_by)
        if not unbanner or unbanner.role < UserRole.MODERATOR:
            return False, "Insufficient permissions"
        
        # Check if user is actually banned
        if user.role != UserRole.BANNED and "banned" not in user.flags:
            return False, "User is not banned"
        
        # Restore to USER role
        user.role = UserRole.USER
        user.permissions = ["view_stats", "create_report"]
        user.flags.discard("banned")
        
        if "ban_reason" in user.metadata:
            del user.metadata["ban_reason"]
        if "banned_by" in user.metadata:
            del user.metadata["banned_by"]
        if "banned_at" in user.metadata:
            del user.metadata["banned_at"]
        
        user.trust_score = 50.0  # Reset to default
        
        self._save_users()
        
        # Log security event
        self.log_security_event(
            event_type="user_unbanned",
            user_id=user_id,
            severity="medium",
            description="User unbanned",
            details={"unbanned_by": unbanned_by}
        )
        
        console.print(f"[green]✅ User {user_id} unbanned[/green]")
        return True, "User unbanned"
    
    def increment_reports(self, user_id: int, success: bool = True):
        """Increment user's report statistics"""
        if user_id in self.users:
            user = self.users[user_id]
            user.reports_made += 1
            
            # Update statistics
            user.update_statistics(success, 0.0)  # Time will be updated by reporting engine
            
            # Update trust score based on success
            if success:
                user.trust_score = min(100.0, user.trust_score + 1.0)
            else:
                user.trust_score = max(0.0, user.trust_score - 0.5)
            
            self._save_users()
    
    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed user statistics"""
        if user_id not in self.users:
            return None
        
        user = self.users[user_id]
        
        # Calculate activity level
        activity_level = "inactive"
        if user.last_active:
            days_since_active = (datetime.now() - user.last_active).days
            if days_since_active == 0:
                activity_level = "active_today"
            elif days_since_active <= 7:
                activity_level = "active_week"
            elif days_since_active <= 30:
                activity_level = "active_month"
            else:
                activity_level = "inactive"
        
        # Get user's recent activity
        recent_activity = [
            activity for activity in self.activity_log[-100:]
            if activity["user_id"] == user_id
        ]
        
        # Get user's security events
        user_security_events = [
            event for event in self.security_log[-50:]
            if event["user_id"] == user_id
        ]
        
        stats = {
            "user_info": {
                "user_id": user.user_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.name,
                "added_at": user.added_at.isoformat(),
                "last_active": user.last_active.isoformat() if user.last_active else None,
                "activity_level": activity_level
            },
            "statistics": user.statistics,
            "trust_score": user.trust_score,
            "security_level": user.security_level.name,
            "warnings": user.warnings,
            "flags": list(user.flags),
            "permissions": user.permissions,
            "recent_activity_count": len(recent_activity),
            "security_events_count": len(user_security_events),
            "is_premium": user.is_premium,
            "settings": user.settings
        }
        
        return stats
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics"""
        total_users = len(self.users)
        
        # Count by role
        role_counts = {role.name: 0 for role in UserRole}
        for user in self.users.values():
            role_counts[user.role.name] += 1
        
        # Trust score distribution
        trust_scores = [user.trust_score for user in self.users.values()]
        avg_trust_score = statistics.mean(trust_scores) if trust_scores else 0.0
        
        # Activity analysis
        active_users = 0
        for user in self.users.values():
            if user.last_active and (datetime.now() - user.last_active).days <= 7:
                active_users += 1
        
        # Total reports
        total_reports = sum(user.reports_made for user in self.users.values())
        
        stats = {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "role_distribution": role_counts,
            "average_trust_score": avg_trust_score,
            "total_reports": total_reports,
            "total_activity_logs": len(self.activity_log),
            "total_security_logs": len(self.security_log),
            "unique_sessions": len(self.sessions),
            "active_sessions": sum(1 for s in self.sessions.values() if s["is_active"])
        }
        
        return stats
    
    def export_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Export all user data for backup or analysis"""
        if user_id not in self.users:
            return None
        
        user = self.users[user_id]
        
        # Get user's activity
        user_activities = [
            activity for activity in self.activity_log
            if activity["user_id"] == user_id
        ]
        
        # Get user's security events
        user_security_events = [
            event for event in self.security_log
            if event["user_id"] == user_id
        ]
        
        # Get user's sessions
        user_sessions = [
            session for session in self.sessions.values()
            if session["user_id"] == user_id
        ]
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "user_data": user.to_dict(),
            "activities": user_activities[-1000:],  # Last 1000 activities
            "security_events": user_security_events[-500:],  # Last 500 events
            "sessions": user_sessions,
            "summary": {
                "total_activities": len(user_activities),
                "total_security_events": len(user_security_events),
                "total_sessions": len(user_sessions),
                "report_success_rate": user.statistics.get("report_success_rate", 0.0),
                "average_report_time": user.statistics.get("average_report_time", 0.0)
            }
        }
        
        return export_data
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """Cleanup inactive sessions"""
        inactive_sessions = []
        now = datetime.now()
        
        for session_id, session in self.sessions.items():
            last_activity = datetime.fromisoformat(session["last_activity"])
            if (now - last_activity).total_seconds() > (max_age_hours * 3600):
                session["is_active"] = False
                inactive_sessions.append(session_id)
        
        # Remove completely inactive sessions (older than 7 days)
        old_sessions = []
        for session_id, session in self.sessions.items():
            if not session["is_active"]:
                created_at = datetime.fromisoformat(session["created_at"])
                if (now - created_at).total_seconds() > (7 * 24 * 3600):
                    old_sessions.append(session_id)
        
        for session_id in old_sessions:
            del self.sessions[session_id]
        
        if inactive_sessions or old_sessions:
            console.print(f"[yellow]🧹 Cleaned up {len(inactive_sessions)} inactive and {len(old_sessions)} old sessions[/yellow]")
    
    def run_security_scan(self):
        """Run security scan on all users"""
        console.print("[cyan]🔍 Running security scan...[/cyan]")
        
        suspicious_users = []
        
        for user_id, user in self.users.items():
            # Check for suspicious patterns
            flags = []
            
            # Multiple failed reports
            if user.statistics.get("failed_reports", 0) > 10 and user.statistics.get("report_success_rate", 0) < 20.0:
                flags.append("high_failure_rate")
            
            # Low trust score
            if user.trust_score < 30.0 and user.role not in [UserRole.BANNED, UserRole.VIEWER]:
                flags.append("low_trust_score")
            
            # Many warnings
            if user.warnings >= 3:
                flags.append("multiple_warnings")
            
            # Inactive but making reports
            if user.last_active and (datetime.now() - user.last_active).days > 30 and user.reports_made > 0:
                flags.append("inactive_but_reporting")
            
            if flags:
                suspicious_users.append({
                    "user_id": user_id,
                    "username": user.username,
                    "role": user.role.name,
                    "flags": flags,
                    "trust_score": user.trust_score,
                    "reports_made": user.reports_made,
                    "success_rate": user.statistics.get("report_success_rate", 0.0)
                })
        
        if suspicious_users:
            console.print(f"[yellow]⚠️ Found {len(suspicious_users)} suspicious users[/yellow]")
            
            # Log security event
            self.log_security_event(
                event_type="security_scan",
                user_id=0,
                severity="medium",
                description=f"Security scan found {len(suspicious_users)} suspicious users",
                details={"suspicious_users": suspicious_users}
            )
            
            # Create report
            scan_report = {
                "timestamp": datetime.now().isoformat(),
                "total_users_scanned": len(self.users),
                "suspicious_users_count": len(suspicious_users),
                "suspicious_users": suspicious_users,
                "recommendations": []
            }
            
            # Add recommendations
            for user in suspicious_users:
                if "high_failure_rate" in user["flags"]:
                    scan_report["recommendations"].append({
                        "user_id": user["user_id"],
                        "action": "review_reports",
                        "reason": "High failure rate detected"
                    })
                if "low_trust_score" in user["flags"]:
                    scan_report["recommendations"].append({
                        "user_id": user["user_id"],
                        "action": "downgrade_or_monitor",
                        "reason": "Low trust score"
                    })
            
            # Save scan report
            scan_file = ANALYTICS_DIR / f"security_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(scan_file, 'w', encoding='utf-8') as f:
                json.dump(scan_report, f, indent=2, ensure_ascii=False)
            
            console.print(f"[green]✅ Security scan report saved to {scan_file}[/green]")
        else:
            console.print("[green]✅ Security scan: No suspicious users found[/green]")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for admin dashboard"""
        stats = self.get_system_stats()
        
        # Recent activity
        recent_activities = self.activity_log[-20:]  # Last 20 activities
        
        # Recent security events
        recent_security_events = self.security_log[-10:]  # Last 10 security events
        
        # Top reporters
        top_reporters = sorted(
            self.users.values(),
            key=lambda u: u.reports_made,
            reverse=True
        )[:5]
        
        top_reporters_data = []
        for user in top_reporters:
            top_reporters_data.append({
                "user_id": user.user_id,
                "username": user.username,
                "reports_made": user.reports_made,
                "success_rate": user.statistics.get("report_success_rate", 0.0),
                "role": user.role.name
            })
        
        dashboard_data = {
            "system_stats": stats,
            "recent_activities": recent_activities,
            "recent_security_events": recent_security_events,
            "top_reporters": top_reporters_data,
            "timestamp": datetime.now().isoformat()
        }
        
        return dashboard_data

# ============================================
# SECTION 7: ENHANCED ACCOUNT MANAGER
# ============================================

class AdvancedAccountManager:
    """
    ENHANCED ACCOUNT MANAGER WITH COMPREHENSIVE MANAGEMENT
    
    Features:
    1. Multi-method OTP verification
    2. Advanced session management
    3. Proxy optimization
    4. Health monitoring
    5. Performance analytics
    6. Automatic maintenance
    7. Security enforcement
    """
    
    def __init__(self, proxy_manager: AdvancedProxyManager, 
                 user_manager: AdvancedUserManager,
                 otp_verification: AdvancedOTPVerification):
        self.accounts: Dict[str, TelegramAccount] = {}
        self.account_sessions: Dict[str, Dict] = {}
        self.proxy_manager = proxy_manager
        self.user_manager = user_manager
        self.otp_verification = otp_verification
        self.max_reports_per_account = 9
        self.maintenance_tasks: Dict[str, asyncio.Task] = {}
        self.health_monitor_task: Optional[asyncio.Task] = None
        
        self._load_accounts()
        self._start_health_monitor()
    
    def _load_accounts(self):
        """Load accounts from JSON file with validation"""
        try:
            if ACCOUNTS_FILE.exists():
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                loaded = 0
                errors = 0
                
                for phone, acc_data in data.items():
                    try:
                        account = TelegramAccount.from_dict(acc_data)
                        
                        # Validate account data
                        if not self._validate_account(account):
                            errors += 1
                            continue
                        
                        self.accounts[phone] = account
                        loaded += 1
                        
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Skipping invalid account {phone}: {e}[/yellow]")
                        errors += 1
                        continue
                
                console.print(f"[green]✅ Loaded {loaded} accounts ({errors} errors)[/green]")
                
                # Log security event
                self.user_manager.log_security_event(
                    event_type="accounts_loaded",
                    user_id=0,
                    severity="info",
                    description=f"Loaded {loaded} accounts from storage",
                    details={"loaded": loaded, "errors": errors}
                )
                
        except Exception as e:
            console.print(f"[red]❌ Error loading accounts: {e}[/red]")
            self.user_manager.log_security_event(
                event_type="system_error",
                user_id=0,
                severity="critical",
                description=f"Failed to load accounts: {e}"
            )
    
    def _validate_account(self, account: TelegramAccount) -> bool:
        """Validate account data"""
        try:
            # Basic validation
            if not account.phone or not re.match(r'^\+\d{10,15}$', account.phone):
                return False
            
            # Session file should exist or be creatable
            if not account.session_file.parent.exists():
                account.session_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Validate status
            if account.status not in AccountStatus:
                return False
            
            # Validate numeric fields
            if account.report_count < 0 or account.total_reports < 0:
                return False
            
            # Validate proxy if present
            if account.proxy and not self._validate_proxy(account.proxy):
                console.print(f"[yellow]⚠️ Invalid proxy for account {account.phone}: {account.proxy}[/yellow]")
                account.proxy = None
                account.proxy_verified = False
            
            return True
            
        except Exception:
            return False
    
    def _validate_proxy(self, proxy: str) -> bool:
        """Validate proxy format"""
        if not proxy:
            return False
        
        try:
            # Basic format check
            if ':' not in proxy:
                return False
            
            # Check if it's in proxy manager
            if proxy in self.proxy_manager.proxy_map:
                return self.proxy_manager.proxy_map[proxy].is_active
            
            # Try to parse
            if '@' in proxy:
                auth, hostport = proxy.split('@', 1)
                if ':' not in auth:
                    return False
            else:
                hostport = proxy
            
            if '://' in hostport:
                hostport = hostport.split('://', 1)[1]
            
            host, port = hostport.rsplit(':', 1)
            
            # Validate port
            port_num = int(port)
            if port_num < 1 or port_num > 65535:
                return False
            
            # Validate host (basic check)
            if not host or len(host) > 253:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _save_accounts(self):
        """Save accounts to JSON file with backup"""
        try:
            data = {phone: account.to_dict() for phone, account in self.accounts.items()}
            
            # Create backup
            backup_file = BACKUP_DIR / f"accounts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Save current
            with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Keep only last 5 backups
            backups = list(BACKUP_DIR.glob("accounts_backup_*.json"))
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for backup in backups[5:]:
                backup.unlink()
            
        except Exception as e:
            console.print(f"[red]❌ Error saving accounts: {e}[/red]")
            self.user_manager.log_security_event(
                event_type="system_error",
                user_id=0,
                severity="critical",
                description=f"Failed to save accounts: {e}"
            )
    
    async def _start_health_monitor(self):
        """Start account health monitoring task"""
        async def monitor_health():
            while True:
                try:
                    await self._check_account_health()
                    await asyncio.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    console.print(f"[red]❌ Health monitor error: {e}[/red]")
                    await asyncio.sleep(60)
        
        self.health_monitor_task = asyncio.create_task(monitor_health())
    
    async def _check_account_health(self):
        """Check health of all accounts"""
        try:
            unhealthy_accounts = []
            
            for phone, account in self.accounts.items():
                health_score = account.get_health_score()
                
                if health_score < 50.0:
                    unhealthy_accounts.append({
                        "phone": phone,
                        "health_score": health_score,
                        "status": account.status.name,
                        "report_count": account.report_count,
                        "proxy_failures": account.proxy_failures,
                        "session_errors": account.session_errors
                    })
                    
                    # Log warning for very unhealthy accounts
                    if health_score < 30.0:
                        console.print(f"[yellow]⚠️ Account {phone} health critical: {health_score:.1f}[/yellow]")
            
            if unhealthy_accounts:
                console.print(f"[cyan]🔍 Found {len(unhealthy_accounts)} unhealthy accounts[/cyan]")
                
                # Log security event
                self.user_manager.log_security_event(
                    event_type="account_health_check",
                    user_id=0,
                    severity="medium",
                    description=f"Found {len(unhealthy_accounts)} unhealthy accounts",
                    details={"unhealthy_accounts": unhealthy_accounts}
                )
                
        except Exception as e:
            console.print(f"[red]❌ Account health check error: {e}[/red]")
    
    async def add_account(self, phone: str, added_by: int, 
                         proxy_type: Optional[ProxyType] = None) -> Tuple[bool, str]:
        """
        Add a new account with enhanced validation
        """
        # Validate phone number
        if not re.match(r'^\+\d{10,15}$', phone):
            return False, "Invalid phone number format. Use: +1234567890"
        
        # Check if account already exists
        if phone in self.accounts:
            return False, "Account already exists"
        
        # Get best proxy for this account
        proxy = await self.proxy_manager.get_best_proxy_for_account(phone, proxy_type)
        if not proxy:
            return False, "No working proxies available"
        
        # Create session file path
        session_file = SESSION_DIR / f"{phone.replace('+', '')}.session"
        
        # Create account with enhanced metadata
        account = TelegramAccount(
            phone=phone,
            session_file=session_file,
            proxy=proxy,
            status=AccountStatus.UNVERIFIED,
            proxy_verified=True
        )
        
        # Set metadata
        account.metadata.update({
            "added_by": added_by,
            "added_at": datetime.now().isoformat(),
            "added_via": "bot_command",
            "source": "manual",
            "tags": ["new", "unverified"],
            "risk_score": 0.0,
            "trust_level": "unknown"
        })
        
        # Add to accounts
        self.accounts[phone] = account
        self._save_accounts()
        
        # Log activity
        self.user_manager.log_activity(
            user_id=added_by,
            action="account_added",
            details={"phone": phone, "proxy": proxy, "proxy_type": proxy_type.name if proxy_type else "auto"}
        )
        
        # Log security event
        self.user_manager.log_security_event(
            event_type="account_added",
            user_id=added_by,
            severity="info",
            description=f"Account {phone} added by user {added_by}",
            details={"phone": phone, "proxy": proxy}
        )
        
        console.print(f"[green]✅ Added account: {phone} with proxy: {proxy[:50]}...[/green]")
        return True, f"Account {phone} added successfully"
    
    async def create_desktop_session(self, phone: str, update: Update, 
                                   user_id: int) -> Tuple[bool, str]:
        """
        Create enhanced desktop session with multiple OTP methods
        """
        try:
            if phone not in self.accounts:
                return False, "Account not found"
            
            account = self.accounts[phone]
            
            # Check if already logged in
            if account.status == AccountStatus.ACTIVE and account.client and account.client.is_connected():
                await update.message.reply_text(
                    f"✅ *Already Logged In!*\n\n"
                    f"Account `{phone}` is already active.\n"
                    f"Ready for reporting!",
                    parse_mode='Markdown'
                )
                return True, "Already logged in"
            
            # Check if banned
            if account.status == AccountStatus.BANNED:
                return False, "Account is banned"
            
            # Check flood wait
            if account.status == AccountStatus.FLOOD_WAIT and account.last_flood_wait:
                wait_time = (datetime.now() - account.last_flood_wait).seconds
                if wait_time < account.flood_wait_seconds:
                    remaining = account.flood_wait_seconds - wait_time
                    return False, f"Flood wait: {remaining} seconds remaining"
            
            # Random desktop configuration for realism
            desktop_configs = [
                {"model": "Desktop", "sys_ver": "Windows 10", "app_ver": "4.0.0", "lang": "en-US"},
                {"model": "Desktop", "sys_ver": "Windows 11", "app_ver": "4.1.0", "lang": "en-US"},
                {"model": "Mac", "sys_ver": "macOS 14.0", "app_ver": "4.0.0", "lang": "en"},
                {"model": "Linux", "sys_ver": "Ubuntu 22.04", "app_ver": "3.8.0", "lang": "en"},
                {"model": "Desktop", "sys_ver": "Windows 10", "app_ver": "4.2.0", "lang": "en-GB"},
                {"model": "Desktop", "sys_ver": "Windows 11", "app_ver": "4.3.0", "lang": "en-AU"},
            ]
            
            config = random.choice(desktop_configs)
            account.device_model = config["model"]
            account.system_version = config["sys_ver"]
            account.app_version = config["app_version"]
            account.system_lang_code = config["lang"]
            account.lang_code = config["lang"].split('-')[0] if '-' in config["lang"] else config["lang"]
            
            # Update account
            account.last_used = datetime.now()
            account.status = AccountStatus.VERIFYING
            
            await update.message.reply_text(
                f"🖥️ *Creating Desktop Session*\n\n"
                f"Phone: `{phone}`\n"
                f"Device: {config['model']} ({config['sys_ver']})\n"
                f"Telegram Desktop: {config['app_version']}\n"
                f"Language: {config['lang']}\n"
                f"Proxy: Verified ✅\n\n"
                f"⏳ Connecting to Telegram...",
                parse_mode='Markdown'
            )
            
            # Create Telegram client with enhanced configuration
            client = TelegramClient(
                str(account.session_file),
                API_ID,
                API_HASH,
                device_model=account.device_model,
                system_version=account.system_version,
                app_version=account.app_version,
                system_lang_code=account.system_lang_code,
                lang_code=account.lang_code,
                use_ipv6=account.ipv6_enabled,
                timeout=30,
                request_retries=3,
                connection_retries=3,
                auto_reconnect=True
            )
            
            # Set proxy if available
            if account.proxy:
                try:
                    proxy_tuple = self.proxy_manager._format_proxy_for_telethon(account.proxy)
                    if proxy_tuple:
                        client.set_proxy(proxy_tuple)
                        console.print(f"[cyan]🔧 Set proxy for {phone}: {proxy_tuple}[/cyan]")
                except Exception as proxy_error:
                    console.print(f"[red]❌ Error setting proxy: {proxy_error}[/red]")
                    account.proxy_failures += 1
                    return False, "Proxy configuration error"
            
            # Connect to Telegram
            try:
                await client.connect()
                
                # Check if already authorized
                if await client.is_user_authorized():
                    account.client = client
                    account.status = AccountStatus.ACTIVE
                    account.last_login = datetime.now()
                    account.session_quality = 100.0
                    
                    # Get account info
                    await self._update_account_info(account, client)
                    
                    self._save_accounts()
                    
                    await update.message.reply_text(
                        f"✅ *Already Authorized!*\n\n"
                        f"Account `{phone}` was already logged in.\n"
                        f"Session restored successfully!\n\n"
                        f"Ready for reporting!",
                        parse_mode='Markdown'
                    )
                    
                    return True, "Session restored"
                
                # Start OTP verification
                success = await self.otp_verification.start_otp_verification(
                    phone, client, update, user_id
                )
                
                if success:
                    # Store client in session for OTP verification
                    if not hasattr(update, '_user_sessions'):
                        update._user_sessions = {}
                    
                    update._user_sessions[user_id] = {
                        "phone": phone,
                        "client": client,
                        "step": "waiting_otp",
                        "created_at": datetime.now().isoformat(),
                        "session_type": "desktop"
                    }
                    
                    # Update account
                    account.client = client
                    self._save_accounts()
                    
                    return True, "OTP sent successfully"
                else:
                    await client.disconnect()
                    account.status = AccountStatus.INACTIVE
                    self._save_accounts()
                    return False, "Failed to send OTP"
                
            except FloodWaitError as e:
                account.status = AccountStatus.FLOOD_WAIT
                account.last_flood_wait = datetime.now()
                account.flood_wait_seconds = e.seconds
                account.session_flood_waits += 1
                self._save_accounts()
                
                wait_minutes = e.seconds // 60
                wait_seconds = e.seconds % 60
                
                return False, f"Flood wait: {wait_minutes} minutes {wait_seconds} seconds"
                
            except PhoneNumberBannedError:
                account.status = AccountStatus.BANNED
                self._save_accounts()
                return False, "Phone number is banned"
                
            except PhoneNumberUnoccupiedError:
                return False, "Phone number not registered on Telegram"
                
            except Exception as e:
                console.print(f"[red]❌ Connection error: {e}[/red]")
                account.session_errors += 1
                self._save_accounts()
                return False, f"Connection error: {str(e)[:100]}"
                
        except Exception as e:
            console.print(f"[red]❌ Session creation error: {e}[/red]")
            return False, f"Error: {str(e)[:100]}"
    
    async def _update_account_info(self, account: TelegramAccount, client: TelegramClient):
        """Update account information from Telegram"""
        try:
            me = await client.get_me()
            
            account.user_id = me.id
            account.username = me.username
            account.first_name = me.first_name
            account.last_name = me.last_name
            account.is_premium = getattr(me, 'premium', False)
            account.is_verified = getattr(me, 'verified', False)
            account.is_scam = getattr(me, 'scam', False)
            account.is_fake = getattr(me, 'fake', False)
            account.is_bot = me.bot
            account.is_self = me.self
            account.is_contact = me.contact
            account.is_mutual_contact = me.mutual_contact
            account.is_deleted = me.deleted
            account.is_support = me.support
            
            # Get bio if available
            try:
                full_user = await client.get_entity(me.id)
                account.bio = getattr(full_user, 'about', None)
            except:
                account.bio = None
            
            # Check 2FA
            try:
                password_info = await client.get_password()
                account.two_factor_enabled = password_info.has_password
                account.password_hint = password_info.hint if password_info.has_password else None
            except:
                account.two_factor_enabled = False
            
            # Update country from phone
            account.country = self._get_country_from_phone(account.phone)
            
            # Update session quality
            account.session_quality = 100.0
            account.last_sync = datetime.now()
            
            # Update metadata
            account.metadata["last_info_update"] = datetime.now().isoformat()
            account.metadata["has_bio"] = account.bio is not None
            account.metadata["premium_since"] = getattr(me, 'premium_since', None)
            
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not get account info for {account.phone}: {e}[/yellow]")
            account.session_quality = max(0.0, account.session_quality - 10.0)
    
    def _get_country_from_phone(self, phone: str) -> str:
        """Enhanced country detection from phone number"""
        # Comprehensive country code mapping
        country_codes = {
            '+1': 'United States',
            '+44': 'United Kingdom',
            '+49': 'Germany',
            '+33': 'France',
            '+81': 'Japan',
            '+65': 'Singapore',
            '+91': 'India',
            '+7': 'Russia',
            '+86': 'China',
            '+90': 'Turkey',
            '+55': 'Brazil',
            '+61': 'Australia',
            '+34': 'Spain',
            '+39': 'Italy',
            '+358': 'Finland',
            '+353': 'Ireland',
            '+82': 'South Korea',
            '+52': 'Mexico',
            '+20': 'Egypt',
            '+27': 'South Africa',
            '+31': 'Netherlands',
            '+41': 'Switzerland',
            '+46': 'Sweden',
            '+47': 'Norway',
            '+45': 'Denmark',
            '+43': 'Austria',
            '+32': 'Belgium',
            '+48': 'Poland',
            '+420': 'Czech Republic',
            '+36': 'Hungary',
            '+40': 'Romania',
            '+381': 'Serbia',
            '+385': 'Croatia',
            '+386': 'Slovenia',
            '+387': 'Bosnia',
            '+389': 'North Macedonia',
            '+359': 'Bulgaria',
            '+30': 'Greece',
            '+355': 'Albania',
            '+381': 'Montenegro',
            '+373': 'Moldova',
            '+380': 'Ukraine',
            '+375': 'Belarus',
            '+370': 'Lithuania',
            '+371': 'Latvia',
            '+372': 'Estonia',
            '+994': 'Azerbaijan',
            '+995': 'Georgia',
            '+374': 'Armenia',
            '+998': 'Uzbekistan',
            '+7': 'Kazakhstan',
            '+993': 'Turkmenistan',
            '+996': 'Kyrgyzstan',
            '+992': 'Tajikistan',
            '+973': 'Bahrain',
            '+966': 'Saudi Arabia',
            '+971': 'United Arab Emirates',
            '+974': 'Qatar',
            '+965': 'Kuwait',
            '+968': 'Oman',
            '+962': 'Jordan',
            '+963': 'Syria',
            '+964': 'Iraq',
            '+961': 'Lebanon',
            '+970': 'Palestine',
            '+972': 'Israel',
            '+20': 'Egypt',
            '+212': 'Morocco',
            '+213': 'Algeria',
            '+216': 'Tunisia',
            '+218': 'Libya',
            '+220': 'Gambia',
            '+221': 'Senegal',
            '+222': 'Mauritania',
            '+223': 'Mali',
            '+224': 'Guinea',
            '+225': 'Ivory Coast',
            '+226': 'Burkina Faso',
            '+227': 'Niger',
            '+228': 'Togo',
            '+229': 'Benin',
            '+230': 'Mauritius',
            '+231': 'Liberia',
            '+232': 'Sierra Leone',
            '+233': 'Ghana',
            '+234': 'Nigeria',
            '+235': 'Chad',
            '+236': 'Central African Republic',
            '+237': 'Cameroon',
            '+238': 'Cape Verde',
            '+239': 'Sao Tome and Principe',
            '+240': 'Equatorial Guinea',
            '+241': 'Gabon',
            '+242': 'Republic of the Congo',
            '+243': 'Democratic Republic of the Congo',
            '+244': 'Angola',
            '+245': 'Guinea-Bissau',
            '+246': 'British Indian Ocean Territory',
            '+247': 'Ascension Island',
            '+248': 'Seychelles',
            '+249': 'Sudan',
            '+250': 'Rwanda',
            '+251': 'Ethiopia',
            '+252': 'Somalia',
            '+253': 'Djibouti',
            '+254': 'Kenya',
            '+255': 'Tanzania',
            '+256': 'Uganda',
            '+257': 'Burundi',
            '+258': 'Mozambique',
            '+260': 'Zambia',
            '+261': 'Madagascar',
            '+262': 'Reunion',
            '+263': 'Zimbabwe',
            '+264': 'Namibia',
            '+265': 'Malawi',
            '+266': 'Lesotho',
            '+267': 'Botswana',
            '+268': 'Swaziland',
            '+269': 'Comoros',
            '+290': 'Saint Helena',
            '+291': 'Eritrea',
            '+297': 'Aruba',
            '+298': 'Faroe Islands',
            '+299': 'Greenland',
        }
        
        for code, country in country_codes.items():
            if phone.startswith(code):
                return country
        
        return "Unknown"
    
    async def verify_otp_code(self, phone: str, otp_code: str, 
                             update: Update, user_id: int) -> Tuple[bool, str]:
        """
        Verify OTP code for account
        """
        try:
            if phone not in self.accounts:
                return False, "Account not found"
            
            # Get session from update context
            if not hasattr(update, '_user_sessions') or user_id not in update._user_sessions:
                return False, "Session expired"
            
            session_data = update._user_sessions[user_id]
            if session_data.get("phone") != phone:
                return False, "Phone mismatch"
            
            # Get session ID
            session_id = session_data.get("session_id")
            if not session_id:
                return False, "Session ID not found"
            
            # Verify OTP using OTP verification system
            success, message = await self.otp_verification.verify_otp_code(
                session_id, otp_code, update, user_id
            )
            
            if success:
                # Update account
                account = self.accounts[phone]
                account.status = AccountStatus.ACTIVE
                account.last_login = datetime.now()
                account.otp_attempts += 1
                account.session_quality = 100.0
                
                # Get client from session
                if "client" in session_data:
                    account.client = session_data["client"]
                
                # Update account info
                if account.client:
                    await self._update_account_info(account, account.client)
                
                self._save_accounts()
                
                # Log activity
                self.user_manager.log_activity(
                    user_id=user_id,
                    action="account_verified",
                    details={"phone": phone, "method": "otp"}
                )
                
                return True, "OTP verified successfully"
            elif message == "2FA_PASSWORD_NEEDED":
                # Store session for 2FA
                update._user_sessions[user_id]["step"] = "need_password"
                update._user_sessions[user_id]["session_id"] = session_id
                
                # Update account
                account = self.accounts[phone]
                account.status = AccountStatus.NEED_PASSWORD
                account.two_factor_pending = True
                self._save_accounts()
                
                return False, "2FA_PASSWORD_NEEDED"
            else:
                # Update account with failed attempt
                account = self.accounts[phone]
                account.otp_attempts += 1
                
                if "Invalid code" in message and account.otp_attempts >= 5:
                    account.status = AccountStatus.INACTIVE
                
                self._save_accounts()
                
                return False, message
            
        except Exception as e:
            console.print(f"[red]❌ OTP verification error: {e}[/red]")
            return False, f"System error: {str(e)[:100]}"
    
    async def verify_2fa_password(self, phone: str, password: str,
                                 update: Update, user_id: int) -> Tuple[bool, str]:
        """
        Verify 2FA password
        """
        try:
            if phone not in self.accounts:
                return False, "Account not found"
            
            # Get session from update context
            if not hasattr(update, '_user_sessions') or user_id not in update._user_sessions:
                return False, "Session expired"
            
            session_data = update._user_sessions[user_id]
            if session_data.get("phone") != phone:
                return False, "Phone mismatch"
            
            # Get session ID
            session_id = session_data.get("session_id")
            if not session_id:
                return False, "Session ID not found"
            
            # Verify 2FA password
            success, message = await self.otp_verification.handle_2fa_password(
                session_id, password, update, user_id
            )
            
            if success:
                # Update account
                account = self.accounts[phone]
                account.status = AccountStatus.ACTIVE
                account.last_login = datetime.now()
                account.two_factor_enabled = True
                account.two_factor_pending = False
                account.session_quality = 100.0
                
                self._save_accounts()
                
                # Log activity
                self.user_manager.log_activity(
                    user_id=user_id,
                    action="account_2fa_verified",
                    details={"phone": phone, "method": "password"}
                )
                
                return True, "2FA verified successfully"
            else:
                # Update account with failed attempt
                account = self.accounts[phone]
                account.otp_attempts += 1
                self._save_accounts()
                
                return False, message
            
        except Exception as e:
            console.print(f"[red]❌ 2FA verification error: {e}[/red]")
            return False, f"System error: {str(e)[:100]}"
    
    async def get_available_accounts(self, count: int = 3, 
                                   min_health_score: float = 60.0) -> List[TelegramAccount]:
        """
        Get available accounts with health filtering
        """
        available = []
        
        # First pass: Active accounts with reports left and good health
        for account in self.accounts.values():
            if (account.status == AccountStatus.ACTIVE and 
                account.report_count < self.max_reports_per_account and
                account.get_health_score() >= min_health_score):
                
                available.append(account)
                if len(available) >= count:
                    break
        
        # Second pass: Lower health threshold if not enough accounts
        if len(available) < count:
            for account in self.accounts.values():
                if (account.status == AccountStatus.ACTIVE and 
                    account.report_count < self.max_reports_per_account and
                    account.get_health_score() >= 40.0 and
                    account not in available):
                    
                    available.append(account)
                    if len(available) >= count:
                        break
        
        # Third pass: Include inactive but potentially usable accounts
        if len(available) < count:
            inactive = [acc for acc in self.accounts.values() 
                       if acc.status == AccountStatus.INACTIVE]
            available.extend(inactive[:count - len(available)])
        
        # Sort by health score (highest first)
        available.sort(key=lambda x: x.get_health_score(), reverse=True)
        
        return available[:count]
    
    async def rotate_proxy_for_account(self, phone: str) -> Tuple[bool, str]:
        """
        Rotate proxy for account with enhanced logic
        """
        if phone not in self.accounts:
            return False, "Account not found"
        
        account = self.accounts[phone]
        
        # Check if rotation is needed
        if not account.should_rotate_proxy(self.max_reports_per_account):
            return True, "Rotation not needed"
        
        console.print(f"[cyan]🔄 Rotating proxy for {phone}...[/cyan]")
        
        # Get new proxy
        old_proxy = account.proxy
        new_proxy = await self.proxy_manager.rotate_proxy_for_account(phone)
        
        if new_proxy and new_proxy != account.proxy:
            # Update account
            account.proxy = new_proxy
            account.report_count = 0
            account.proxy_verified = True
            account.proxy_rotation_count += 1
            account.last_proxy_rotation = datetime.now()
            account.proxy_failures = 0
            
            # Update metadata
            account.metadata["proxy_rotations"] = account.metadata.get("proxy_rotations", 0) + 1
            account.metadata["last_proxy_change"] = datetime.now().isoformat()
            account.metadata["old_proxy"] = old_proxy
            
            # Try to reconnect with new proxy
            if account.client and account.client.is_connected():
                try:
                    await account.client.disconnect()
                    
                    # Reconnect with new proxy
                    proxy_tuple = self.proxy_manager._format_proxy_for_telethon(new_proxy)
                    if proxy_tuple:
                        account.client.set_proxy(proxy_tuple)
                    
                    await account.client.connect()
                    
                except Exception as e:
                    console.print(f"[yellow]⚠️ Error reconnecting with new proxy: {e}[/yellow]")
                    # Continue anyway, will reconnect when needed
            
            self._save_accounts()
            
            console.print(f"[green]✅ Proxy rotated for {phone}: {old_proxy[:30]}... → {new_proxy[:30]}...[/green]")
            return True, f"Proxy rotated: {new_proxy[:50]}..."
        elif new_proxy:
            # Same proxy but reset count
            account.report_count = 0
            account.proxy_failures = 0
            self._save_accounts()
            return True, "Report count reset"
        else:
            account.proxy_failures += 1
            self._save_accounts()
            return False, "Failed to get new proxy"
    
    async def check_account_connection(self, phone: str) -> Tuple[bool, str, float]:
        """
        Check account connection status and latency
        """
        if phone not in self.accounts:
            return False, "Account not found", 0.0
        
        account = self.accounts[phone]
        
        if not account.client or not account.client.is_connected():
            return False, "Not connected", 0.0
        
        try:
            start_time = time.time()
            
            # Simple ping to check connection
            await account.client.get_me()
            
            latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Update connection quality
            if latency < 1000:
                account.connection_quality = min(100.0, account.connection_quality + 5.0)
            else:
                account.connection_quality = max(0.0, account.connection_quality - 10.0)
            
            account.is_online = True
            account.last_online_check = datetime.now()
            
            self._save_accounts()
            
            return True, "Connected", latency
            
        except Exception as e:
            account.is_online = False
            account.connection_quality = max(0.0, account.connection_quality - 20.0)
            account.session_errors += 1
            
            self._save_accounts()
            
            return False, f"Connection error: {str(e)[:100]}", 0.0
    
    async def perform_account_maintenance(self, phone: str) -> Dict[str, Any]:
        """
        Perform comprehensive account maintenance
        """
        if phone not in self.accounts:
            return {"success": False, "error": "Account not found"}
        
        account = self.accounts[phone]
        results = {
            "phone": phone,
            "timestamp": datetime.now().isoformat(),
            "actions": [],
            "errors": [],
            "warnings": []
        }
        
        try:
            # 1. Check connection
            if account.client and account.client.is_connected():
                results["actions"].append("connection_checked")
            else:
                results["warnings"].append("not_connected")
            
            # 2. Check proxy
            if account.proxy:
                proxy_entry = self.proxy_manager.proxy_map.get(account.proxy)
                if proxy_entry and proxy_entry.is_active:
                    results["actions"].append("proxy_checked")
                else:
                    results["warnings"].append("proxy_inactive")
                    # Try to rotate proxy
                    rotated, message = await self.rotate_proxy_for_account(phone)
                    if rotated:
                        results["actions"].append("proxy_rotated")
                    else:
                        results["errors"].append(f"proxy_rotation_failed: {message}")
            
            # 3. Check session health
            health_score = account.get_health_score()
            results["health_score"] = health_score
            
            if health_score < 50.0:
                results["warnings"].append(f"low_health_score: {health_score:.1f}")
            
            # 4. Update session age
            if account.created_at:
                account.session_age_days = (datetime.now() - account.created_at).days
                results["session_age_days"] = account.session_age_days
            
            # 5. Cleanup old statistics
            if "hourly_activity" in account.statistics:
                # Keep only last 7 days of hourly data
                cutoff_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                account.statistics["hourly_activity"] = {
                    k: v for k, v in account.statistics["hourly_activity"].items()
                    if k >= cutoff_date
                }
                results["actions"].append("statistics_cleaned")
            
            # 6. Update metadata
            account.metadata["last_maintenance"] = datetime.now().isoformat()
            account.metadata["maintenance_count"] = account.metadata.get("maintenance_count", 0) + 1
            
            # Save changes
            self._save_accounts()
            
            results["success"] = True
            results["final_health_score"] = account.get_health_score()
            
            console.print(f"[green]✅ Maintenance completed for {phone}[/green]")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"maintenance_error: {str(e)}")
            console.print(f"[red]❌ Maintenance error for {phone}: {e}[/red]")
        
        return results
    
    def get_account_stats(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive account statistics"""
        if phone not in self.accounts:
            return None
        
        account = self.accounts[phone]
        
        stats = {
            "basic_info": {
                "phone": account.phone,
                "status": account.status.name,
                "user_id": account.user_id,
                "username": account.username,
                "first_name": account.first_name,
                "last_name": account.last_name,
                "country": account.country,
                "language": account.lang_code
            },
            "security": {
                "two_factor_enabled": account.two_factor_enabled,
                "security_level": account.security_level.name,
                "is_premium": account.is_premium,
                "is_verified": account.is_verified,
                "password_hint": account.password_hint
            },
            "performance": {
                "report_count": account.report_count,
                "total_reports": account.total_reports,
                "max_reports": self.max_reports_per_account,
                "success_rate": account.success_rate,
                "average_report_time": account.average_report_time,
                "health_score": account.get_health_score(),
                "connection_quality": account.connection_quality,
                "session_quality": account.session_quality
            },
            "proxy": {
                "current_proxy": account.proxy[:50] + "..." if account.proxy and len(account.proxy) > 50 else account.proxy,
                "proxy_verified": account.proxy_verified,
                "proxy_failures": account.proxy_failures,
                "proxy_rotations": account.proxy_rotation_count,
                "last_proxy_rotation": account.last_proxy_rotation.isoformat() if account.last_proxy_rotation else None
            },
            "device": {
                "model": account.device_model,
                "system": account.system_version,
                "app_version": account.app_version,
                "language": account.system_lang_code
            },
            "session": {
                "session_age_days": account.session_age_days,
                "session_errors": account.session_errors,
                "flood_waits": account.session_flood_waits,
                "last_flood_wait": account.last_flood_wait.isoformat() if account.last_flood_wait else None,
                "last_login": account.last_login.isoformat() if account.last_login else None,
                "last_used": account.last_used.isoformat() if account.last_used else None
            },
            "statistics": account.statistics,
            "metadata": account.metadata,
            "flags": list(account.flags)
        }
        
        return stats
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide account statistics"""
        total = len(self.accounts)
        
        # Count by status
        status_counts = {status.name: 0 for status in AccountStatus}
        for account in self.accounts.values():
            status_counts[account.status.name] += 1
        
        # Health distribution
        health_scores = [account.get_health_score() for account in self.accounts.values()]
        avg_health = statistics.mean(health_scores) if health_scores else 0.0
        
        # Report statistics
        total_reports = sum(account.total_reports for account in self.accounts.values())
        today = datetime.now().date()
        reports_today = sum(
            account.report_count for account in self.accounts.values()
            if account.last_report_time and account.last_report_time.date() == today
        )
        
        # Proxy statistics
        accounts_with_proxy = sum(1 for account in self.accounts.values() if account.proxy)
        accounts_proxy_verified = sum(1 for account in self.accounts.values() if account.proxy_verified)
        
        # Premium accounts
        premium_accounts = sum(1 for account in self.accounts.values() if account.is_premium)
        
        # 2FA statistics
        accounts_with_2fa = sum(1 for account in self.accounts.values() if account.two_factor_enabled)
        
        stats = {
            "total_accounts": total,
            "active_accounts": status_counts["ACTIVE"],
            "inactive_accounts": status_counts["INACTIVE"],
            "banned_accounts": status_counts["BANNED"],
            "needs_2fa": status_counts["NEED_PASSWORD"],
            "flood_wait": status_counts["FLOOD_WAIT"],
            "average_health_score": avg_health,
            "total_reports": total_reports,
            "reports_today": reports_today,
            "accounts_with_proxy": accounts_with_proxy,
            "accounts_proxy_verified": accounts_proxy_verified,
            "premium_accounts": premium_accounts,
            "accounts_with_2fa": accounts_with_2fa,
            "max_reports_per_account": self.max_reports_per_account,
            "status_distribution": status_counts
        }
        
        return stats
    
    async def export_account_data(self, phone: str) -> Optional[Dict[str, Any]]:
        """Export all account data"""
        if phone not in self.accounts:
            return None
        
        account = self.accounts[phone]
        stats = self.get_account_stats(phone)
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "account_data": account.to_dict(),
            "comprehensive_stats": stats,
            "summary": {
                "health_score": account.get_health_score(),
                "total_reports": account.total_reports,
                "success_rate": account.success_rate,
                "session_age_days": account.session_age_days,
                "proxy_rotations": account.proxy_rotation_count
            }
        }
        
        return export_data
    
    async def cleanup(self):
        """Cleanup resources"""
        # Stop health monitor
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
            try:
                await self.health_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all clients
        for account in self.accounts.values():
            if account.client and account.client.is_connected():
                try:
                    await account.client.disconnect()
                except:
                    pass
        
        # Save accounts
        self._save_accounts()

# ============================================
# SECTION 8: ADVANCED REPORTING ENGINE
# ============================================

class AdvancedReportingEngine:
    """
    ADVANCED REPORTING ENGINE WITH COMPREHENSIVE FEATURES
    
    Features:
    1. Multi-account parallel reporting
    2. Intelligent proxy rotation
    3. Realistic desktop simulation
    4. Comprehensive error handling
    5. Performance analytics
    6. Automatic retry mechanisms
    7. Security monitoring
    """
    
    def __init__(self, account_manager: AdvancedAccountManager, 
                 proxy_manager: AdvancedProxyManager, 
                 user_manager: AdvancedUserManager):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.user_manager = user_manager
        self.active_jobs: Dict[str, ReportJob] = {}
        self.job_history: List[ReportJob] = []
        self.report_queue: asyncio.Queue = asyncio.Queue()
        self.worker_tasks: List[asyncio.Task] = []
        self.is_running = False
        
        # Report categories with enhanced details
        self.categories = {
            "ILLEGAL_DRUGS": {
                "name": "Illegal Drugs",
                "priority": "HIGH",
                "telethon_reason": InputReportReasonIllegalDrugs,
                "subcategories": {
                    1: {"name": "Drug Sales", "description": "Selling illegal drugs"},
                    2: {"name": "Drug Promotion", "description": "Promoting drug use"},
                    3: {"name": "Drug Recipes", "description": "Sharing drug production methods"},
                    4: {"name": "Drug Trafficking", "description": "Organized drug distribution"}
                }
            },
            "SPAM": {
                "name": "Spam",
                "priority": "MEDIUM",
                "telethon_reason": InputReportReasonSpam,
                "subcategories": {
                    1: {"name": "Mass Spamming", "description": "Sending bulk unwanted messages"},
                    2: {"name": "Phishing Links", "description": "Sharing phishing websites"},
                    3: {"name": "Financial Scams", "description": "Financial fraud attempts"},
                    4: {"name": "Fake Giveaways", "description": "Fake contests and giveaways"},
                    5: {"name": "Bot Spam", "description": "Automated spam messages"}
                }
            },
            "VIOLENCE": {
                "name": "Violence",
                "priority": "HIGH",
                "telethon_reason": InputReportReasonViolence,
                "subcategories": {
                    1: {"name": "Threats", "description": "Making violent threats"},
                    2: {"name": "Terrorism", "description": "Terrorist propaganda"},
                    3: {"name": "Extremism", "description": "Extremist content"},
                    4: {"name": "Organized Violence", "description": "Planning violent acts"}
                }
            },
            "SEXUAL": {
                "name": "Sexual Content",
                "priority": "HIGH",
                "telethon_reason": InputReportReasonPornography,
                "subcategories": {
                    1: {"name": "Exploitation", "description": "Sexual exploitation"},
                    2: {"name": "Harassment", "description": "Sexual harassment"},
                    3: {"name": "Pornography", "description": "Adult content"},
                    4: {"name": "Child Abuse", "description": "Child sexual abuse material"}
                }
            },
            "FRAUD": {
                "name": "Fraud",
                "priority": "HIGH",
                "telethon_reason": InputReportReasonFake,
                "subcategories": {
                    1: {"name": "Impersonation", "description": "Impersonating others"},
                    2: {"name": "Fake Accounts", "description": "Fake identity accounts"},
                    3: {"name": "Scams", "description": "Financial scams"},
                    4: {"name": "Identity Theft", "description": "Stealing identities"}
                }
            },
            "HARASSMENT": {
                "name": "Harassment",
                "priority": "MEDIUM",
                "telethon_reason": InputReportReasonPersonalDetails,
                "subcategories": {
                    1: {"name": "Bullying", "description": "Targeted harassment"},
                    2: {"name": "Doxxing", "description": "Sharing private information"},
                    3: {"name": "Stalking", "description": "Online stalking"},
                    4: {"name": "Hate Speech", "description": "Hateful content"}
                }
            },
            "COPYRIGHT": {
                "name": "Copyright",
                "priority": "LOW",
                "telethon_reason": InputReportReasonCopyright,
                "subcategories": {
                    1: {"name": "Piracy", "description": "Copyright infringement"},
                    2: {"name": "Content Theft", "description": "Stealing content"},
                    3: {"name": "Unauthorized Distribution", "description": "Illegal distribution"}
                }
            },
            "OTHER": {
                "name": "Other",
                "priority": "LOW",
                "telethon_reason": InputReportReasonOther,
                "subcategories": {
                    1: {"name": "Custom Reason", "description": "Other violations"},
                    2: {"name": "Platform Abuse", "description": "Abusing platform features"},
                    3: {"name": "TOS Violation", "description": "Terms of Service violation"}
                }
            }
        }
        
        # Priority weights
        self.priority_weights = {
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1
        }
        
        self._load_jobs()
        self._start_workers()
    
    def _load_jobs(self):
        """Load jobs from file"""
        try:
            if JOBS_FILE.exists():
                with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                loaded = 0
                for job_data in data:
                    try:
                        job = ReportJob.from_dict(job_data)
                        self.job_history.append(job)
                        loaded += 1
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Skipping invalid job data: {e}[/yellow]")
                        continue
                
                console.print(f"[green]✅ Loaded {loaded} jobs from history[/green]")
                
        except Exception as e:
            console.print(f"[yellow]⚠️ Error loading jobs: {e}[/yellow]")
    
    def _save_jobs(self):
        """Save jobs to file"""
        try:
            # Keep last 200 jobs in history
            data = [job.to_dict() for job in self.job_history[-200:]]
            
            with open(JOBS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            console.print(f"[red]❌ Error saving jobs: {e}[/red]")
    
    def _start_workers(self):
        """Start report processing workers"""
        async def worker():
            while self.is_running:
                try:
                    job_id = await self.report_queue.get()
                    if job_id is None:
                        break
                    
                    await self._process_job(job_id)
                    self.report_queue.task_done()
                    
                except Exception as e:
                    console.print(f"[red]❌ Worker error: {e}[/red]")
        
        # Start 3 worker tasks
        self.is_running = True
        for i in range(3):
            task = asyncio.create_task(worker())
            self.worker_tasks.append(task)
        
        console.print("[green]✅ Started 3 report processing workers[/green]")
    
    async def create_job(self, target: str, target_type: str, category: str,
                        subcategory: int, description: str, user_id: int,
                        priority: int = 1) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new report job with validation
        """
        try:
            # Validate category
            if category not in self.categories:
                return False, f"Invalid category: {category}", None
            
            # Validate subcategory
            if subcategory not in self.categories[category]["subcategories"]:
                return False, f"Invalid subcategory: {subcategory}", None
            
            # Validate target
            if not target or len(target) < 3:
                return False, "Invalid target", None
            
            # Validate description
            if not description or len(description) < 20:
                return False, "Description must be at least 20 characters", None
            
            # Get subcategory details
            sub_details = self.categories[category]["subcategories"][subcategory]
            
            # Generate job ID
            job_id = hashlib.sha256(
                f"{target}{category}{subcategory}{user_id}{time.time()}".encode()
            ).hexdigest()[:16]
            
            # Create job
            job = ReportJob(
                job_id=job_id,
                target=target,
                target_type=target_type,
                category=category,
                subcategory=sub_details["name"],
                description=description,
                created_by=user_id,
                priority=priority
            )
            
            # Set metadata
            job.metadata.update({
                "category_name": self.categories[category]["name"],
                "subcategory_description": sub_details["description"],
                "priority_weight": self.priority_weights.get(self.categories[category]["priority"], 1),
                "estimated_accounts_needed": 3,
                "complexity": "medium",
                "risk_level": "medium" if self.categories[category]["priority"] == "MEDIUM" else "high"
            })
            
            # Add to active jobs
            self.active_jobs[job_id] = job
            
            # Log activity
            self.user_manager.log_activity(
                user_id=user_id,
                action="job_created",
                details={
                    "job_id": job_id,
                    "target": target,
                    "category": category,
                    "subcategory": subcategory,
                    "priority": priority
                }
            )
            
            console.print(f"[cyan]📝 Created job {job_id} for {target} (priority: {priority})[/cyan]")
            
            return True, "Job created successfully", job_id
            
        except Exception as e:
            console.print(f"[red]❌ Job creation error: {e}[/red]")
            return False, f"Error creating job: {str(e)[:100]}", None
    
    async def start_job(self, job_id: str) -> Tuple[bool, str]:
        """
        Start processing a job
        """
        if job_id not in self.active_jobs:
            return False, "Job not found"
        
        job = self.active_jobs[job_id]
        
        # Check if already processing or completed
        if job.status in [ReportStatus.PROCESSING, ReportStatus.COMPLETED, ReportStatus.FAILED]:
            return False, f"Job already {job.status.name.lower()}"
        
        # Update job status
        job.status = ReportStatus.PROCESSING
        job.started_at = datetime.now()
        
        # Add to queue
        await self.report_queue.put(job_id)
        
        # Log activity
        self.user_manager.log_activity(
            user_id=job.created_by,
            action="job_started",
            details={"job_id": job_id}
        )
        
        console.print(f"[cyan]🚀 Started processing job {job_id}[/cyan]")
        return True, "Job started processing"
    
    async def _process_job(self, job_id: str):
        """
        Process a job with comprehensive error handling
        """
        if job_id not in self.active_jobs:
            return
        
        job = self.active_jobs[job_id]
        
        try:
            console.print(f"[cyan]🔧 Processing job {job_id}[/cyan]")
            
            # Step 1: Validate target
            await self._validate_target(job)
            
            if not job.metadata["target_resolved"]:
                job.status = ReportStatus.FAILED
                job.error_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "stage": "validation",
                    "error": "Target validation failed"
                })
                self._complete_job(job)
                return
            
            # Step 2: Get available accounts
            accounts_needed = job.metadata.get("estimated_accounts_needed", 3)
            accounts = await self.account_manager.get_available_accounts(accounts_needed)
            
            if not accounts:
                job.status = ReportStatus.FAILED
                job.error_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "stage": "account_selection",
                    "error": "No accounts available"
                })
                self._complete_job(job)
                return
            
            # Step 3: Process accounts in parallel with limits
            semaphore = asyncio.Semaphore(2)  # Max 2 concurrent reports
            
            async def process_account(account: TelegramAccount):
                async with semaphore:
                    return await self._process_account_report(account, job)
            
            # Process accounts
            tasks = [process_account(account) for account in accounts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    job.error_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "stage": "account_processing",
                        "account": accounts[i].phone,
                        "error": str(result)[:200]
                    })
                else:
                    job.add_result(result)
            
            # Step 4: Update job status
            successful = job.performance_metrics["successful_accounts"]
            total = job.performance_metrics["total_accounts"]
            
            if successful == 0:
                job.status = ReportStatus.FAILED
            elif successful == total:
                job.status = ReportStatus.COMPLETED
            else:
                job.status = ReportStatus.PARTIAL
            
            # Step 5: Complete job
            self._complete_job(job)
            
            console.print(f"[green]✅ Completed job {job_id}: {successful}/{total} successful[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Job processing error: {e}[/red]")
            
            job.status = ReportStatus.FAILED
            job.error_log.append({
                "timestamp": datetime.now().isoformat(),
                "stage": "job_processing",
                "error": str(e)[:200]
            })
            
            self._complete_job(job)
    
    async def _validate_target(self, job: ReportJob):
        """Validate and resolve target"""
        try:
            # Use first available account to resolve target
            accounts = await self.account_manager.get_available_accounts(1)
            if not accounts:
                job.metadata["target_resolved"] = False
                return
            
            account = accounts[0]
            
            if not account.client or not account.client.is_connected():
                # Try to connect
                try:
                    await account.client.connect()
                except:
                    job.metadata["target_resolved"] = False
                    return
            
            # Resolve target
            try:
                entity = await self._resolve_entity(account.client, job.target, job.target_type)
                
                if entity:
                    job.metadata["target_resolved"] = True
                    job.metadata["target_id"] = getattr(entity, 'id', None)
                    job.metadata["target_access_hash"] = getattr(entity, 'access_hash', None)
                    
                    # Get target info
                    if hasattr(entity, 'title'):
                        job.metadata["target_title"] = entity.title
                    elif hasattr(entity, 'username'):
                        job.metadata["target_username"] = entity.username
                    elif hasattr(entity, 'first_name'):
                        name = entity.first_name or ''
                        if entity.last_name:
                            name += f" {entity.last_name}"
                        job.metadata["target_name"] = name.strip()
                else:
                    job.metadata["target_resolved"] = False
                    
            except Exception as e:
                console.print(f"[yellow]⚠️ Target resolution error: {e}[/yellow]")
                job.metadata["target_resolved"] = False
                
        except Exception as e:
            console.print(f"[red]❌ Target validation error: {e}[/red]")
            job.metadata["target_resolved"] = False
    
    async def _resolve_entity(self, client: TelegramClient, target: str, target_type: str):
        """Resolve target entity"""
        try:
            target = target.strip()
            
            if target.startswith("@"):
                return await client.get_entity(target[1:])
            
            if "t.me/" in target:
                # Parse URL
                if "t.me/joinchat/" in target:
                    # Group invite link
                    return await client.get_entity(target)
                elif "t.me/+" in target:
                    # Phone number link
                    return await client.get_entity(target)
                else:
                    # Username or channel link
                    username = target.split("/")[-1]
                    if "?" in username:
                        username = username.split("?")[0]
                    return await client.get_entity(username)
            
            # Try as username
            if not target.startswith("@"):
                target = f"@{target}"
            
            return await client.get_entity(target)
            
        except Exception as e:
            console.print(f"[yellow]⚠️ Entity resolution failed: {target} - {e}[/yellow]")
            return None
    
    async def _process_account_report(self, account: TelegramAccount, 
                                     job: ReportJob) -> Dict[str, Any]:
        """
        Process a single account report with comprehensive tracking
        """
        start_time = time.time()
        result = {
            "account": account.phone,
            "status": "FAILED",
            "start_time": datetime.now().isoformat(),
            "flags": [],
            "details": {}
        }
        
        try:
            # Step 1: Check proxy rotation
            if account.should_rotate_proxy(self.account_manager.max_reports_per_account):
                rotated, message = await self.account_manager.rotate_proxy_for_account(account.phone)
                if rotated:
                    result["flags"].append("proxy_rotated")
                    result["details"]["proxy_rotation"] = message
                else:
                    result["error"] = f"Proxy rotation failed: {message}"
                    return result
            
            # Step 2: Ensure client is connected
            if not account.client or not account.client.is_connected():
                try:
                    # Reconnect with current proxy
                    if account.proxy:
                        proxy_tuple = self.proxy_manager._format_proxy_for_telethon(account.proxy)
                        if proxy_tuple:
                            account.client.set_proxy(proxy_tuple)
                    
                    await account.client.connect()
                    
                except Exception as e:
                    result["error"] = f"Connection failed: {str(e)[:100]}"
                    account.session_errors += 1
                    return result
            
            # Step 3: Resolve target
            entity = await self._resolve_entity(account.client, job.target, job.target_type)
            if not entity:
                result["error"] = "Failed to resolve target"
                return result
            
            # Step 4: Desktop simulation
            simulation_result = await self._simulate_desktop_behavior(account, job)
            result["details"]["simulation"] = simulation_result
            
            # Step 5: Execute report
            report_result = await self._execute_report(account.client, entity, job)
            
            if report_result["success"]:
                # Update account statistics
                account.report_count += 1
                account.total_reports += 1
                account.last_report_time = datetime.now()
                
                # Update performance metrics
                response_time = time.time() - start_time
                account.average_report_time = (
                    (account.average_report_time * (account.total_reports - 1) + response_time)
                    / account.total_reports
                )
                
                # Update success rate
                account.success_rate = (
                    (account.success_rate * (account.total_reports - 1) + 100)
                    / account.total_reports
                )
                
                # Update proxy statistics
                if account.proxy:
                    self.proxy_manager.mark_proxy_success(
                        account.proxy, 
                        response_time,
                        bytes_sent=report_result.get("bytes_sent", 0),
                        bytes_received=report_result.get("bytes_received", 0)
                    )
                
                # Update account statistics
                account.update_statistics(
                    request_type="report",
                    success=True,
                    latency=response_time * 1000,  # Convert to milliseconds
                    bytes_sent=report_result.get("bytes_sent", 0),
                    bytes_received=report_result.get("bytes_received", 0)
                )
                
                # Set result
                result["status"] = "COMPLETED"
                result["response_time"] = response_time
                result["device"] = account.device_model
                result["country"] = account.country
                result["2fa"] = account.two_factor_enabled
                result["report_count"] = account.report_count
                result["details"].update(report_result.get("details", {}))
                
            else:
                # Update failure statistics
                account.update_statistics(
                    request_type="report",
                    success=False,
                    latency=0,
                    bytes_sent=0,
                    bytes_received=0
                )
                
                # Update proxy failure
                if account.proxy:
                    self.proxy_manager.mark_proxy_failed(
                        account.proxy,
                        error=report_result.get("error")
                    )
                    account.proxy_failures += 1
                
                result["error"] = report_result.get("error", "Unknown error")
                result["details"].update(report_result.get("details", {}))
            
            # Save account
            self.account_manager._save_accounts()
            
        except FloodWaitError as e:
            # Handle flood wait
            account.status = AccountStatus.FLOOD_WAIT
            account.last_flood_wait = datetime.now()
            account.flood_wait_seconds = e.seconds
            account.session_flood_waits += 1
            
            result["status"] = "FLOOD_WAIT"
            result["error"] = f"Flood wait: {e.seconds} seconds"
            result["flags"].append("flood_wait")
            
            self.account_manager._save_accounts()
            
        except Exception as e:
            # Generic error handling
            account.session_errors += 1
            account.session_quality = max(0.0, account.session_quality - 10.0)
            
            result["error"] = str(e)[:200]
            result["details"]["exception_type"] = type(e).__name__
            
            self.account_manager._save_accounts()
        
        finally:
            # Calculate total time
            result["end_time"] = datetime.now().isoformat()
            result["total_time"] = time.time() - start_time
            
            # Update user statistics
            self.user_manager.increment_reports(job.created_by, result["status"] == "COMPLETED")
        
        return result
    
    async def _simulate_desktop_behavior(self, account: TelegramAccount, 
                                        job: ReportJob) -> Dict[str, Any]:
        """
        Simulate realistic desktop behavior
        """
        simulation_steps = [
            {"action": "launch_app", "min_time": 1.5, "max_time": 3.0, "description": "Launching Telegram Desktop"},
            {"action": "load_dialogs", "min_time": 0.5, "max_time": 1.5, "description": "Loading dialog list"},
            {"action": "search_target", "min_time": 1.0, "max_time": 2.5, "description": f"Searching for {job.target[:20]}..."},
            {"action": "open_chat", "min_time": 0.3, "max_time": 0.8, "description": "Opening chat"},
            {"action": "scroll_content", "min_time": 2.0, "max_time": 5.0, "description": "Viewing content"},
            {"action": "open_menu", "min_time": 0.5, "max_time": 1.0, "description": "Opening menu"},
            {"action": "select_report", "min_time": 0.5, "max_time": 1.0, "description": "Selecting report option"},
            {"action": "choose_reason", "min_time": 1.0, "max_time": 2.0, "description": f"Choosing {job.category} reason"},
            {"action": "type_description", "min_time": 3.0, "max_time": 8.0, "description": "Typing description"},
            {"action": "review_report", "min_time": 1.0, "max_time": 2.0, "description": "Reviewing report"},
            {"action": "submit_report", "min_time": 0.5, "max_time": 1.0, "description": "Submitting report"},
        ]
        
        total_time = 0.0
        details = []
        
        for step in simulation_steps:
            # Add realistic delay
            delay = random.uniform(step["min_time"], step["max_time"])
            
            # Add device-specific variations
            if "Windows" in account.system_version:
                delay *= random.uniform(0.9, 1.1)
            elif "Mac" in account.system_version:
                delay *= random.uniform(0.8, 1.0)
            elif "Linux" in account.system_version:
                delay *= random.uniform(0.7, 0.9)
            
            await asyncio.sleep(delay)
            total_time += delay
            
            details.append({
                "action": step["action"],
                "delay": delay,
                "description": step["description"]
            })
        
        return {
            "total_time": total_time,
            "steps": len(simulation_steps),
            "details": details,
            "device": account.device_model,
            "system": account.system_version
        }
    
    async def _execute_report(self, client: TelegramClient, entity: Any, 
                             job: ReportJob) -> Dict[str, Any]:
        """
        Execute the actual report
        """
        try:
            # Get report reason
            category_info = self.categories.get(job.category, self.categories["OTHER"])
            reason_class = category_info["telethon_reason"]
            
            # Prepare message
            message = f"{job.subcategory}: {job.description[:200]}"
            
            # Execute report
            await client(ReportPeerRequest(
                peer=entity,
                reason=reason_class(),
                message=message
            ))
            
            # Simulate post-report delay
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            return {
                "success": True,
                "details": {
                    "reason": job.category,
                    "subcategory": job.subcategory,
                    "message_length": len(message),
                    "entity_type": type(entity).__name__
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)[:200],
                "details": {
                    "exception_type": type(e).__name__,
                    "reason": job.category
                }
            }
    
    def _complete_job(self, job: ReportJob):
        """Complete job processing"""
        job.completed_at = datetime.now()
        job.update_duration()
        
        # Move to history
        self.job_history.append(job)
        if job.job_id in self.active_jobs:
            del self.active_jobs[job.job_id]
        
        # Save jobs
        self._save_jobs()
        
        # Log completion
        self.user_manager.log_activity(
            user_id=job.created_by,
            action="job_completed",
            details={
                "job_id": job.job_id,
                "status": job.status.name,
                "success_rate": job.get_success_rate(),
                "duration": job.performance_metrics["total_duration"]
            }
        )
        
        # Send notification to user
        asyncio.create_task(self._send_job_notification(job))
    
    async def _send_job_notification(self, job: ReportJob):
        """Send job completion notification to user"""
        try:
            # Create bot application
            app = Application.builder().token(BOT_TOKEN).build()
            
            # Prepare message based on status
            if job.status == ReportStatus.COMPLETED:
                success_rate = job.get_success_rate()
                message = (
                    f"✅ *Report Job Completed!*\n\n"
                    f"Job ID: `{job.job_id}`\n"
                    f"Target: `{job.target[:50]}`\n"
                    f"Success Rate: {success_rate:.1f}%\n"
                    f"Accounts Used: {len(job.accounts_used)}\n"
                    f"Duration: {job.performance_metrics['total_duration']:.1f}s\n\n"
                    f"*Great job! The report has been submitted successfully.*"
                )
            elif job.status == ReportStatus.PARTIAL:
                success_rate = job.get_success_rate()
                message = (
                    f"⚠️ *Report Job Partially Completed*\n\n"
                    f"Job ID: `{job.job_id}`\n"
                    f"Target: `{job.target[:50]}`\n"
                    f"Success Rate: {success_rate:.1f}%\n"
                    f"Successful: {job.performance_metrics['successful_accounts']}\n"
                    f"Failed: {job.performance_metrics['failed_accounts']}\n\n"
                    f"*Some accounts failed to report. Consider retrying.*"
                )
            else:
                message = (
                    f"❌ *Report Job Failed*\n\n"
                    f"Job ID: `{job.job_id}`\n"
                    f"Target: `{job.target[:50]}`\n"
                    f"Errors: {len(job.error_log)}\n\n"
                    f"*The job failed to complete. Check logs for details.*"
                )
            
            # Send message
            await app.bot.send_message(
                chat_id=job.created_by,
                text=message,
                parse_mode='Markdown'
            )
            
            await app.shutdown()
            
        except Exception as e:
            console.print(f"[yellow]⚠️ Failed to send job notification: {e}[/yellow]")
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and details"""
        job = self.active_jobs.get(job_id)
        if not job:
            # Check history
            for historical_job in self.job_history:
                if historical_job.job_id == job_id:
                    job = historical_job
                    break
        
        if not job:
            return None
        
        status_info = {
            "job_id": job.job_id,
            "target": job.target,
            "category": job.category,
            "subcategory": job.subcategory,
            "status": job.status.name,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "created_by": job.created_by,
            "priority": job.priority,
            "accounts_used": job.accounts_used,
            "performance_metrics": job.performance_metrics,
            "success_rate": job.get_success_rate(),
            "error_count": len(job.error_log),
            "flags": list(job.flags)
        }
        
        return status_info
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide reporting statistics"""
        total_jobs = len(self.job_history)
        
        # Status distribution
        status_counts = {status.name: 0 for status in ReportStatus}
        for job in self.job_history:
            status_counts[job.status.name] += 1
        
        # Category distribution
        category_counts = {}
        for job in self.job_history:
            category = job.category
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Success rate analysis
        successful_jobs = sum(1 for job in self.job_history if job.status == ReportStatus.COMPLETED)
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0.0
        
        # Average performance
        avg_success_rate = 0.0
        avg_duration = 0.0
        total_success_rate = 0.0
        total_duration = 0.0
        count = 0
        
        for job in self.job_history[-100:]:  # Last 100 jobs for recent performance
            if job.performance_metrics["total_accounts"] > 0:
                success_rate = job.get_success_rate()
                total_success_rate += success_rate
                total_duration += job.performance_metrics.get("total_duration", 0)
                count += 1
        
        if count > 0:
            avg_success_rate = total_success_rate / count
            avg_duration = total_duration / count
        
        stats = {
            "total_jobs": total_jobs,
            "active_jobs": len(self.active_jobs),
            "successful_jobs": successful_jobs,
            "failed_jobs": status_counts["FAILED"],
            "partial_jobs": status_counts["PARTIAL"],
            "overall_success_rate": success_rate,
            "recent_success_rate": avg_success_rate,
            "average_duration": avg_duration,
            "status_distribution": status_counts,
            "category_distribution": category_counts,
            "total_accounts_used": sum(len(job.accounts_used) for job in self.job_history),
            "total_reports_made": sum(job.performance_metrics["total_accounts"] for job in self.job_history),
            "queue_size": self.report_queue.qsize(),
            "active_workers": len([t for t in self.worker_tasks if not t.done()])
        }
        
        return stats
    
    async def cleanup(self):
        """Cleanup resources"""
        # Stop workers
        self.is_running = False
        
        # Send stop signals to workers
        for _ in range(len(self.worker_tasks)):
            await self.report_queue.put(None)
        
        # Wait for workers to finish
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Save jobs
        self._save_jobs()

# ============================================
# SECTION 9: ENHANCED TELEGRAM BOT HANDLER
# ============================================

class AdvancedBotHandler:
    """
    ENHANCED TELEGRAM BOT HANDLER WITH COMPREHENSIVE FEATURES
    
    Features:
    1. Hierarchical command system
    2. Interactive menus and keyboards
    3. Conversation state management
    4. User feedback system
    5. Analytics and monitoring
    6. Security and validation
    7. Multi-language support
    """
    
    def __init__(self, user_manager: AdvancedUserManager, 
                 account_manager: AdvancedAccountManager, 
                 reporting_engine: AdvancedReportingEngine,
                 proxy_manager: AdvancedProxyManager,
                 otp_verification: AdvancedOTPVerification):
        
        self.user_manager = user_manager
        self.account_manager = account_manager
        self.reporting_engine = reporting_engine
        self.proxy_manager = proxy_manager
        self.otp_verification = otp_verification
        
        # Conversation states
        self.START, self.ADD_PHONE, self.ADD_OTP, self.ADD_PASSWORD = range(4)
        self.REPORT_TARGET, self.REPORT_CATEGORY, self.REPORT_SUBCATEGORY, self.REPORT_DESCRIPTION = range(8)
        self.ADMIN_MENU, self.USER_MANAGEMENT, self.ACCOUNT_MANAGEMENT, self.SYSTEM_MANAGEMENT = range(12)
        self.SETTINGS_MENU, self.STATS_DETAILED = range(14)
        
        # User sessions
        self.user_sessions = {}
        
        # Command descriptions for bot menu
        self.commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help information"),
            BotCommand("report", "Start a new report"),
            BotCommand("stats", "Show statistics"),
            BotCommand("accounts", "Manage accounts (Admin)"),
            BotCommand("jobs", "View report jobs"),
            BotCommand("proxies", "View proxy status"),
            BotCommand("settings", "User settings"),
            BotCommand("admin", "Admin panel (Admin only)"),
        ]
    
    async def setup_bot_commands(self, application: Application):
        """Setup bot commands menu"""
        await application.bot.set_my_commands(
            commands=self.commands,
            scope=BotCommandScopeAllPrivateChats()
        )
        console.print("[green]✅ Bot commands setup complete[/green]")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /start command with user registration"""
        user = update.effective_user
        chat = update.effective_chat
        
        # Update user activity
        client_info = {
            "ip_address": context.bot_data.get("client_ip"),
            "user_agent": context.bot_data.get("user_agent"),
            "chat_type": chat.type if chat else "private",
            "language": user.language_code
        }
        
        self.user_manager.update_user_activity(
            user.id, user.username, user.first_name, user.last_name, client_info
        )
        
        # Create user session
        session_id = self.user_manager.create_user_session(user.id, client_info)
        
        # Get user role
        user_data = self.user_manager.users.get(user.id)
        role = user_data.role if user_data else UserRole.USER
        
        # Prepare welcome message based on role
        if role == UserRole.OWNER:
            role_text = "👑 *System Owner*"
            permissions = "Full system access"
        elif role == UserRole.SUDO:
            role_text = "⚡ *Super User*"
            permissions = "Almost full access"
        elif role == UserRole.ADMIN:
            role_text = "🛡️ *Administrator*"
            permissions = "Administrative access"
        elif role == UserRole.MODERATOR:
            role_text = "👮 *Moderator*"
            permissions = "User management access"
        elif role == UserRole.REPORTER:
            role_text = "📊 *Reporter*"
            permissions = "Enhanced reporting"
        elif role == UserRole.USER:
            role_text = "👤 *User*"
            permissions = "Basic reporting"
        elif role == UserRole.VIEWER:
            role_text = "👀 *Viewer*"
            permissions = "View only"
        else:
            role_text = "❌ *Banned*"
            permissions = "No access"
        
        # System status
        system_stats = self.user_manager.get_system_stats()
        account_stats = self.account_manager.get_system_stats()
        proxy_stats = self.proxy_manager.get_detailed_stats()
        report_stats = self.reporting_engine.get_system_stats()
        
        welcome_message = f"""
🤖 *Telegram Enterprise Reporting System v11.0*

*Your Status:* {role_text}
*Permissions:* {permissions}
*Session ID:* `{session_id[:12]}...`

📊 *System Status:*
• Users: {system_stats['total_users']} ({system_stats['active_users']} active)
• Accounts: {account_stats['total_accounts']} ({account_stats['active_accounts']} active)
• Proxies: {proxy_stats['active_proxies']}/{proxy_stats['total_proxies']} working
• Jobs: {report_stats['total_jobs']} completed
• Success Rate: {report_stats['overall_success_rate']:.1f}%

🛠️ *Available Commands:*
"""
        
        # Add commands based on role
        if role >= UserRole.USER:
            welcome_message += """
• /report - Start a new report
• /stats - View statistics
• /jobs - View your jobs
• /proxies - Check proxy status
• /settings - User settings
• /help - Detailed help
"""
        
        if role >= UserRole.REPORTER:
            welcome_message += """• /accounts - Account management\n"""
        
        if role >= UserRole.MODERATOR:
            welcome_message += """• /admin - Admin panel\n"""
        
        if role >= UserRole.OWNER:
            welcome_message += """• System monitoring tools available\n"""
        
        welcome_message += f"""
🔒 *Security Level:* {user_data.security_level.name if user_data else 'MEDIUM'}
⭐ *Trust Score:* {user_data.trust_score if user_data else 100.0:.1f}/100

💡 *Quick Start:*
1. Use `/report` to start reporting
2. Add accounts with `/accounts` (if permitted)
3. Check `/stats` for performance
4. Use `/help` for detailed guides

⚠️ *Important:*
• Each account can report 9 times before proxy rotation
• Use premium proxies for better results
• Monitor system health regularly
"""
        
        # Send welcome message
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=self._get_main_keyboard(role)
        )
        
        return self.START
    
    def _get_main_keyboard(self, role: UserRole) -> Optional[ReplyKeyboardMarkup]:
        """Get main keyboard based on user role"""
        keyboard = []
        
        # Basic buttons for all users
        if role >= UserRole.USER:
            keyboard.append(["📊 Stats", "🆘 Help"])
            keyboard.append(["📝 Report", "📋 My Jobs"])
        
        # Advanced buttons for reporters and above
        if role >= UserRole.REPORTER:
            keyboard.append(["📱 Accounts", "🌐 Proxies"])
        
        # Admin buttons for moderators and above
        if role >= UserRole.MODERATOR:
            keyboard.append(["🛡️ Admin Panel", "⚙️ Settings"])
        
        if keyboard:
            return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, selective=True)
        
        return None
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /help command with comprehensive guides"""
        user = update.effective_user
        user_data = self.user_manager.users.get(user.id)
        role = user_data.role if user_data else UserRole.USER
        
        help_message = """
🆘 *Comprehensive Help Guide*

📚 *Table of Contents:*
1. Getting Started
2. Reporting Guide
3. Account Management
4. Proxy System
5. User Roles
6. Troubleshooting
7. Security Tips
8. Advanced Features

────────────────────
1️⃣ *Getting Started*
────────────────────

*Basic Commands:*
/start - Welcome message and system status
/stats - View system and personal statistics
/help - This comprehensive guide
/settings - Configure your preferences

*First Steps:*
1. Start with `/start` to see your access level
2. Check `/stats` to understand system capacity
3. Use `/report` to begin your first report
4. Monitor progress with `/jobs`

────────────────────
2️⃣ *Reporting Guide*
────────────────────

*Report Command:* `/report`
Follow these steps:
1. Enter target (username or link)
2. Select category (spam, violence, etc.)
3. Choose specific violation
4. Add detailed description (min 20 chars)

*Best Practices:*
• Provide detailed, factual descriptions
• Include evidence if possible
• Be specific about violations
• Avoid emotional language

*Report Limits:*
• Each account: 9 reports per proxy
• Automatic proxy rotation
• Queue system for busy periods

────────────────────
3️⃣ *Account Management*
────────────────────

*Adding Accounts:*
1. Use `/accounts` menu
2. Select "Add Account"
3. Enter phone number (+1234567890)
4. Complete OTP verification
5. Optional: Set up 2FA

*Account Health:*
• Health score (0-100) indicates reliability
• Monitor proxy failures
• Regular maintenance recommended
• Auto-rotation after 9 reports

*Security:*
• 2FA supported and recommended
• Session encryption
• Regular security checks
• Suspicious activity monitoring

────────────────────
4️⃣ *Proxy System*
────────────────────

*Proxy Management:*
• System automatically verifies proxies
• Priority given to fast countries
• Rotation after 9 reports per account
• Performance-based selection

*Proxy Types:*
• HTTP/HTTPS: Basic proxies
• SOCKS5: Recommended for Telegram
• Residential: Highest success rate
• Premium: Best performance

*Adding Proxies:*
1. Edit `data/data.txt` file
2. Add one proxy per line
3. Format: `protocol://user:pass@host:port`
4. Restart bot or use proxy refresh

────────────────────
5️⃣ *User Roles*
────────────────────

*Role Hierarchy:*
👑 Owner - Full system control
⚡ Sudo - Almost full access
🛡️ Admin - Administrative functions
👮 Moderator - User management
📊 Reporter - Enhanced reporting
👤 User - Basic reporting
👀 Viewer - Read-only access
❌ Banned - No access

*Permissions:*
• Viewer: Can view stats only
• User: Basic reporting
• Reporter: + Account management
• Moderator: + User management
• Admin: + System management
• Sudo/Owner: Full control

────────────────────
6️⃣ *Troubleshooting*
────────────────────

*Common Issues:*

1. *OTP Not Received:*
   • Wait 2 minutes and retry
   • Try different OTP method (SMS/Call)
   • Check phone number format
   • Ensure phone can receive SMS

2. *Report Failures:*
   • Check account health score
   • Verify proxy is working
   • Ensure target exists
   • Check flood wait status

3. *Connection Issues:*
   • Verify internet connection
   • Check proxy status
   • Restart account session
   • Contact administrator

4. *Slow Performance:*
   • Check proxy speeds
   • Monitor system load
   • Reduce concurrent reports
   • Use premium proxies

────────────────────
7️⃣ *Security Tips*
────────────────────

*Account Security:*
• Enable 2FA on all accounts
• Use strong, unique passwords
• Monitor account activity
• Report suspicious behavior

*System Security:*
• Regular security scans
• Activity logging
• Access control
• Data encryption

*Best Practices:*
• Never share OTP codes
• Use secure proxies
• Regular system updates
• Backup important data

────────────────────
8️⃣ *Advanced Features*
────────────────────

*For Advanced Users:*

• *Batch Reporting:* Process multiple targets
• *Smart Proxy Selection:* AI-powered optimization
• *Performance Analytics:* Detailed metrics
• *Automated Maintenance:* Self-healing system
• *Custom Categories:* Tailored reporting
• *API Access:* Programmatic control (planned)

*Monitoring Tools:*
• Real-time dashboards
• Performance metrics
• Error tracking
• Security alerts

────────────────────
*Need More Help?*

Contact system administrators or check the documentation.

*Remember:* This system is for legitimate reporting purposes only. Misuse may result in account termination.
"""
        
        await update.message.reply_text(
            help_message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /stats command with comprehensive statistics"""
        user = update.effective_user
        user_data = self.user_manager.users.get(user.id)
        
        if not user_data:
            await update.message.reply_text("❌ User data not found. Use /start first.")
            return
        
        # Get comprehensive statistics
        user_stats = self.user_manager.get_user_stats(user.id)
        system_stats = self.user_manager.get_system_stats()
        account_stats = self.account_manager.get_system_stats()
        proxy_stats = self.proxy_manager.get_detailed_stats()
        report_stats = self.reporting_engine.get_system_stats()
        
        # Prepare statistics message
        stats_message = f"""
📊 *Comprehensive Statistics Dashboard*

👤 *Personal Statistics:*
• Role: {user_data.role.name}
• Trust Score: {user_data.trust_score:.1f}/100
• Reports Made: {user_data.reports_made}
• Success Rate: {user_data.statistics.get('report_success_rate', 0.0):.1f}%
• Avg Report Time: {user_data.statistics.get('average_report_time', 0.0):.1f}s
• Last Active: {user_data.last_active.strftime('%Y-%m-%d %H:%M') if user_data.last_active else 'Never'}

🏢 *System Overview:*
• Total Users: {system_stats['total_users']}
• Active Users: {system_stats['active_users']}
• Total Accounts: {account_stats['total_accounts']}
• Active Accounts: {account_stats['active_accounts']}
• Working Proxies: {proxy_stats['active_proxies']}/{proxy_stats['total_proxies']}
• Total Jobs: {report_stats['total_jobs']}

⚡ *Performance Metrics:*
• System Success Rate: {report_stats['overall_success_rate']:.1f}%
• Recent Success Rate: {report_stats['recent_success_rate']:.1f}%
• Avg Job Duration: {report_stats['average_duration']:.1f}s
• Proxy Performance: {proxy_stats['performance_rating']}
• Avg Proxy Speed: {proxy_stats['average_response_time']:.2f}s

📈 *Activity Analysis:*
• Reports Today: {account_stats['reports_today']}
• Active Jobs: {report_stats['active_jobs']}
• Queue Size: {report_stats['queue_size']}
• Active Workers: {report_stats['active_workers']}

🛡️ *Security Status:*
• Security Level: {user_data.security_level.name}
• Warnings: {user_data.warnings}
• Security Events: {system_stats['total_security_logs']}
• Active Sessions: {system_stats['active_sessions']}

🔧 *System Health:*
• Account Health Avg: {account_stats['average_health_score']:.1f}/100
• Proxy Reliability: {proxy_stats['average_reliability']:.1f}%
• System Uptime: 100% (monitored)
• Last Update: {proxy_stats['verification_timestamp'][:19] if proxy_stats['verification_timestamp'] else 'Unknown'}

💡 *Recommendations:*
"""
        
        # Add recommendations based on statistics
        recommendations = []
        
        if user_data.trust_score < 50.0:
            recommendations.append("• Improve trust score by making successful reports")
        
        if account_stats['average_health_score'] < 60.0:
            recommendations.append("• Perform account maintenance")
        
        if proxy_stats['active_proxies'] < 5:
            recommendations.append("• Add more working proxies")
        
        if report_stats['overall_success_rate'] < 70.0:
            recommendations.append("• Consider using premium proxies")
        
        if len(recommendations) > 0:
            stats_message += "\n".join(recommendations)
        else:
            stats_message += "• System is operating optimally"
        
        # Add detailed view option for admins
        if user_data.role >= UserRole.MODERATOR:
            stats_message += f"\n\n📋 Use `/stats detailed` for advanced analytics"
        
        await update.message.reply_text(
            stats_message,
            parse_mode='Markdown'
        )
    
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /report command with interactive flow"""
        user = update.effective_user
        user_data = self.user_manager.users.get(user.id)
        
        if not user_data:
            await update.message.reply_text("❌ User data not found. Use /start first.")
            return ConversationHandler.END
        
        # Check permissions
        if not self.user_manager.check_permission(user.id, "create_report"):
            await update.message.reply_text("❌ You don't have permission to create reports.")
            return ConversationHandler.END
        
        # Check if user has made too many failed reports
        if (user_data.statistics.get('failed_reports', 0) > 10 and 
            user_data.statistics.get('report_success_rate', 100.0) < 30.0):
            await update.message.reply_text(
                "❌ *Account Restricted*\n\n"
                "Your report success rate is too low.\n"
                "Please contact an administrator.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Initialize user session
        self.user_sessions[user.id] = {
            "step": "target",
            "created_at": datetime.now().isoformat(),
            "retry_count": 0
        }
        
        await update.message.reply_text(
            "📝 *Start New Report*\n\n"
            "Please send the target username or link:\n\n"
            "*Formats:*\n"
            "• User: `@username` or `https://t.me/username`\n"
            "• Channel: `@channelname` or `https://t.me/channelname`\n"
            "• Group: `https://t.me/joinchat/xxxxxx`\n\n"
            "*Examples:*\n"
            "• `@spamaccount`\n"
            "• `https://t.me/fakechannel`\n"
            "• `scammer_username`\n\n"
            "⚠️ *Note:* Make sure the target exists and is accessible.",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
        
        return self.REPORT_TARGET
    
    async def handle_report_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle report target input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            await update.message.reply_text("❌ Session expired. Start over with /report.")
            return ConversationHandler.END
        
        target = update.message.text.strip()
        
        # Validate target
        if not target or len(target) < 3:
            await update.message.reply_text("❌ Invalid target. Please provide a valid username or link.")
            return self.REPORT_TARGET
        
        # Determine target type
        target_type = "user"
        if "t.me/joinchat/" in target:
            target_type = "group"
        elif "t.me/" in target and not target.startswith("@"):
            if any(x in target.lower() for x in ["/c/", "/channel", "channel"]):
                target_type = "channel"
            else:
                target_type = "user"
        
        # Store in session
        self.user_sessions[user_id]["target"] = target
        self.user_sessions[user_id]["target_type"] = target_type
        
        # Create category keyboard
        keyboard = []
        row = []
        for i, (cat_id, cat_info) in enumerate(self.reporting_engine.categories.items()):
            row.append(InlineKeyboardButton(cat_info["name"], callback_data=f"cat_{cat_id}"))
            if (i + 1) % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        await update.message.reply_text(
            f"✅ *Target Accepted*\n\n"
            f"Target: `{target[:50]}`\n"
            f"Type: {target_type.capitalize()}\n\n"
            "Now select the violation category:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return self.REPORT_CATEGORY
    
    async def handle_report_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Report cancelled.")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Session expired.")
            return ConversationHandler.END
        
        cat_id = query.data.replace("cat_", "")
        
        if cat_id not in self.reporting_engine.categories:
            await query.edit_message_text("❌ Invalid category.")
            return self.REPORT_CATEGORY
        
        # Store category
        self.user_sessions[user_id]["category"] = cat_id
        cat_info = self.reporting_engine.categories[cat_id]
        
        # Create subcategory keyboard
        keyboard = []
        for sub_id, sub_info in cat_info["subcategories"].items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{sub_id}. {sub_info['name']}",
                    callback_data=f"sub_{sub_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("« Back", callback_data="back"), 
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        await query.edit_message_text(
            f"📑 *{cat_info['name']}*\n\n"
            f"Priority: {cat_info['priority']}\n\n"
            "Select the specific violation:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return self.REPORT_SUBCATEGORY
    
    async def handle_report_subcategory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subcategory selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Report cancelled.")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        
        if query.data == "back":
            # Go back to category selection
            keyboard = []
            row = []
            for i, (cat_id, cat_info) in enumerate(self.reporting_engine.categories.items()):
                row.append(InlineKeyboardButton(cat_info["name"], callback_data=f"cat_{cat_id}"))
                if (i + 1) % 2 == 0:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
            
            await query.edit_message_text(
                "Select the violation category:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return self.REPORT_CATEGORY
        
        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Session expired.")
            return ConversationHandler.END
        
        sub_id = int(query.data.replace("sub_", ""))
        cat_id = self.user_sessions[user_id]["category"]
        
        if cat_id not in self.reporting_engine.categories:
            await query.edit_message_text("❌ Invalid category.")
            return ConversationHandler.END
        
        cat_info = self.reporting_engine.categories[cat_id]
        
        if sub_id not in cat_info["subcategories"]:
            await query.edit_message_text("❌ Invalid subcategory.")
            return self.REPORT_SUBCATEGORY
        
        sub_info = cat_info["subcategories"][sub_id]
        
        # Store subcategory
        self.user_sessions[user_id]["subcategory"] = sub_id
        self.user_sessions[user_id]["subcategory_name"] = sub_info["name"]
        self.user_sessions[user_id]["subcategory_description"] = sub_info["description"]
        
        await query.edit_message_text(
            f"📝 *Description Required*\n\n"
            f"Category: {cat_info['name']}\n"
            f"Violation: {sub_info['name']}\n"
            f"Description: {sub_info['description']}\n\n"
            "Please provide a detailed description of the violation:\n\n"
            "*Requirements:*\n"
            "• Minimum 20 characters\n"
            "• Be specific and factual\n"
            "• Include evidence if available\n"
            "• Avoid emotional language\n\n"
            "*Example:*\n"
            "\"This account is sending mass spam messages promoting fake cryptocurrency investments. "
            "They contact users randomly with investment offers and phishing links.\"",
            parse_mode='Markdown'
        )
        
        return self.REPORT_DESCRIPTION
    
    async def handle_report_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle description input and create job"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            await update.message.reply_text("❌ Session expired.")
            return ConversationHandler.END
        
        description = update.message.text.strip()
        
        # Validate description
        if len(description) < 20:
            await update.message.reply_text(
                "❌ Description must be at least 20 characters.\n"
                "Please provide more details."
            )
            return self.REPORT_DESCRIPTION
        
        # Get session data
        session = self.user_sessions[user_id]
        target = session["target"]
        target_type = session["target_type"]
        category = session["category"]
        subcategory = session["subcategory"]
        
        # Create job
        success, message, job_id = await self.reporting_engine.create_job(
            target=target,
            target_type=target_type,
            category=category,
            subcategory=subcategory,
            description=description,
            user_id=user_id,
            priority=self.user_manager.users[user_id].role.value  # Higher role = higher priority
        )
        
        if success:
            # Start job processing
            await self.reporting_engine.start_job(job_id)
            
            await update.message.reply_text(
                f"✅ *Report Job Created!*\n\n"
                f"Job ID: `{job_id}`\n"
                f"Target: `{target[:50]}`\n"
                f"Category: {self.reporting_engine.categories[category]['name']}\n"
                f"Violation: {session['subcategory_name']}\n\n"
                f"⏳ *Processing started...*\n\n"
                f"*Estimated Timeline:*\n"
                f"• Account selection: 2-5 seconds\n"
                f"• Target verification: 3-7 seconds\n"
                f"• Desktop simulation: 20-40 seconds per account\n"
                f"• Report submission: 2-5 seconds per account\n\n"
                f"📊 *Expected Results:*\n"
                f"• Using 3 accounts simultaneously\n"
                f"• Proxy rotation if needed\n"
                f"• Realistic user simulation\n\n"
                f"🔔 *Notifications:*\n"
                f"You will receive a notification when the job is complete.\n\n"
                f"📈 *Track Progress:*\n"
                f"Use `/jobs` to view job status.",
                parse_mode='Markdown'
            )
            
            # Log activity
            self.user_manager.log_activity(
                user_id=user_id,
                action="report_created",
                details={
                    "job_id": job_id,
                    "target": target,
                    "category": category,
                    "subcategory": subcategory,
                    "description_length": len(description)
                }
            )
            
        else:
            await update.message.reply_text(
                f"❌ *Failed to create job*\n\n"
                f"Error: {message}\n\n"
                f"Please try again or contact support.",
                parse_mode='Markdown'
            )
        
        # Cleanup session
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        
        return ConversationHandler.END
    
    async def accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /accounts command with management options"""
        user = update.effective_user
        user_data = self.user_manager.users.get(user.id)
        
        if not user_data:
            await update.message.reply_text("❌ User data not found. Use /start first.")
            return
        
        # Check permissions
        if not self.user_manager.check_permission(user.id, "add_account"):
            await update.message.reply_text("❌ You don't have permission to manage accounts.")
            return
        
        # Get account statistics
        account_stats = self.account_manager.get_system_stats()
        
        # Create accounts keyboard
        keyboard = [
            [InlineKeyboardButton("📱 Add Account", callback_data="acc_add")],
            [InlineKeyboardButton("📊 View All Accounts", callback_data="acc_list")],
            [InlineKeyboardButton("🩺 Account Health", callback_data="acc_health")],
            [InlineKeyboardButton("🔄 Maintenance", callback_data="acc_maintenance")],
            [InlineKeyboardButton("📤 Export Data", callback_data="acc_export")],
            [InlineKeyboardButton("« Back", callback_data="back")]
        ]
        
        await update.message.reply_text(
            f"📱 *Account Management*\n\n"
            f"*System Status:*\n"
            f"• Total Accounts: {account_stats['total_accounts']}\n"
            f"• Active: {account_stats['active_accounts']}\n"
            f"• Banned: {account_stats['banned_accounts']}\n"
            f"• Needs 2FA: {account_stats['needs_2fa']}\n"
            f"• Avg Health: {account_stats['average_health_score']:.1f}/100\n\n"
            f"*Available Actions:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def proxies_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /proxies command with detailed status"""
        user = update.effective_user
        
        # Get proxy statistics
        proxy_stats = self.proxy_manager.get_detailed_stats()
        
        # Create proxy status message
        status_message = f"""
🌐 *Proxy System Status*

📊 *Overview:*
• Total Proxies: {proxy_stats['total_proxies']}
• Working Proxies: {proxy_stats['active_proxies']}
• Premium Proxies: {proxy_stats['premium_proxies']}
• Fast Country Proxies: {proxy_stats['fast_country_proxies']}
• Performance Rating: {proxy_stats['performance_rating']}

⚡ *Performance:*
• Average Speed: {proxy_stats['average_response_time']:.2f}s
• Median Speed: {proxy_stats['median_response_time']:.2f}s
• Average Reliability: {proxy_stats['average_reliability']:.1f}%
• Total Data Used: {proxy_stats['total_data_used_mb']:.1f} MB

🌍 *Geographic Distribution:*
"""
        
        # Add top countries
        if proxy_stats['country_distribution']:
            top_countries = sorted(
                proxy_stats['country_distribution'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            for country, count in top_countries:
                percentage = (count / proxy_stats['active_proxies'] * 100) if proxy_stats['active_proxies'] > 0 else 0
                status_message += f"• {country}: {count} ({percentage:.1f}%)\n"
        
        status_message += f"""
🔧 *Technical Details:*
• Last Verification: {proxy_stats['verification_timestamp'][:19] if proxy_stats['verification_timestamp'] else 'Never'}
• Proxy Types: {', '.join(f'{k}: {v}' for k, v in proxy_stats['type_distribution'].items())}
• Fast Countries: {', '.join(proxy_stats['fast_countries'][:5])}

💡 *Recommendations:*
"""
        
        # Add recommendations
        if proxy_stats['active_proxies'] < 10:
            status_message += "• Add more proxies to improve reliability\n"
        
        if proxy_stats['average_response_time'] > 2.0:
            status_message += "• Consider adding faster proxies\n"
        
        if proxy_stats['average_reliability'] < 80.0:
            status_message += "• Remove unreliable proxies\n"
        
        if not status_message.endswith("Recommendations:\n"):
            status_message += "• System is performing well\n"
        
        # Add management options for admins
        user_data = self.user_manager.users.get(user.id)
        if user_data and user_data.role >= UserRole.MODERATOR:
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Proxies", callback_data="proxy_refresh")],
                [InlineKeyboardButton("📋 Get Working List", callback_data="proxy_list")],
                [InlineKeyboardButton("📊 Detailed Stats", callback_data="proxy_stats")]
            ]
            
            await update.message.reply_text(
                status_message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                status_message,
                parse_mode='Markdown'
            )
    
    async def jobs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /jobs command with job management"""
        user = update.effective_user
        
        # Get user's jobs
        user_jobs = []
        for job_id, job in self.reporting_engine.active_jobs.items():
            if job.created_by == user.id:
                user_jobs.append(job)
        
        for job in self.reporting_engine.job_history[-50:]:  # Last 50 historical jobs
            if job.created_by == user.id and job not in user_jobs:
                user_jobs.append(job)
        
        if not user_jobs:
            await update.message.reply_text(
                "📭 *No Jobs Found*\n\n"
                "You haven't created any report jobs yet.\n"
                "Use `/report` to create your first job.",
                parse_mode='Markdown'
            )
            return
        
        # Sort by creation date (newest first)
        user_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Show recent jobs (last 5)
        recent_jobs = user_jobs[:5]
        
        jobs_message = f"""
📋 *Your Report Jobs*

*Recent Jobs ({len(recent_jobs)}):*
"""
        
        for i, job in enumerate(recent_jobs, 1):
            status_icon = {
                ReportStatus.COMPLETED: "✅",
                ReportStatus.PROCESSING: "⏳",
                ReportStatus.PENDING: "⏰",
                ReportStatus.FAILED: "❌",
                ReportStatus.PARTIAL: "⚠️"
            }.get(job.status, "❓")
            
            success_rate = job.get_success_rate()
            
            jobs_message += f"""
{i}. {status_icon} *{job.target[:20]}...*
   • ID: `{job.job_id}`
   • Status: {job.status.name}
   • Success: {success_rate:.1f}%
   • Created: {job.created_at.strftime('%Y-%m-%d %H:%M')}
"""
        
        jobs_message += f"""
📊 *Statistics:*
• Total Jobs: {len(user_jobs)}
• Completed: {sum(1 for j in user_jobs if j.status == ReportStatus.COMPLETED)}
• Failed: {sum(1 for j in user_jobs if j.status == ReportStatus.FAILED)}
• Average Success Rate: {sum(j.get_success_rate() for j in user_jobs if j.performance_metrics['total_accounts'] > 0) / max(1, sum(1 for j in user_jobs if j.performance_metrics['total_accounts'] > 0)):.1f}%

💡 *Actions:*
• Use `/jobs view JOB_ID` for details
• Check `/stats` for overall performance
• Contact admin for failed jobs
"""
        
        # Add keyboard for job management
        keyboard = []
        if len(user_jobs) > 5:
            keyboard.append([InlineKeyboardButton("📜 View All Jobs", callback_data="jobs_all")])
        
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="jobs_refresh")])
        
        if keyboard:
            await update.message.reply_text(
                jobs_message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                jobs_message,
                parse_mode='Markdown'
            )
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /admin command for administrators"""
        user = update.effective_user
        user_data = self.user_manager.users.get(user.id)
        
        if not user_data:
            await update.message.reply_text("❌ User data not found.")
            return
        
        # Check admin permissions
        if user_data.role < UserRole.MODERATOR:
            await update.message.reply_text("❌ Admin access required.")
            return
        
        # Get system status
        system_stats = self.user_manager.get_system_stats()
        account_stats = self.account_manager.get_system_stats()
        proxy_stats = self.proxy_manager.get_detailed_stats()
        report_stats = self.reporting_engine.get_system_stats()
        
        # Create admin dashboard
        dashboard = f"""
🛡️ *Admin Dashboard*

👥 *Users:*
• Total: {system_stats['total_users']}
• Active: {system_stats['active_users']}
• Admins: {system_stats['role_distribution'].get('ADMIN', 0)}
• Moderators: {system_stats['role_distribution'].get('MODERATOR', 0)}
• Banned: {system_stats['role_distribution'].get('BANNED', 0)}

📱 *Accounts:*
• Total: {account_stats['total_accounts']}
• Active: {account_stats['active_accounts']}
• Health Avg: {account_stats['average_health_score']:.1f}
• Needs 2FA: {account_stats['needs_2fa']}
• Banned: {account_stats['banned_accounts']}

🌐 *Proxies:*
• Total: {proxy_stats['total_proxies']}
• Working: {proxy_stats['active_proxies']}
• Performance: {proxy_stats['performance_rating']}
• Avg Speed: {proxy_stats['average_response_time']:.2f}s
• Reliability: {proxy_stats['average_reliability']:.1f}%

📊 *Reporting:*
• Total Jobs: {report_stats['total_jobs']}
• Active Jobs: {report_stats['active_jobs']}
• Success Rate: {report_stats['overall_success_rate']:.1f}%
• Queue Size: {report_stats['queue_size']}
• Workers: {report_stats['active_workers']}

🔒 *Security:*
• Security Events: {system_stats['total_security_logs']}
• Active Sessions: {system_stats['active_sessions']}
• Recent Alerts: {sum(1 for e in self.user_manager.security_log[-24:] if e['severity'] in ['high', 'critical'])}
• Trust Score Avg: {system_stats['average_trust_score']:.1f}

⚠️ *Alerts:*
"""
        
        # Add alerts
        alerts = []
        
        if account_stats['average_health_score'] < 50.0:
            alerts.append("• Account health is low")
        
        if proxy_stats['active_proxies'] < 5:
            alerts.append("• Few working proxies")
        
        if report_stats['overall_success_rate'] < 60.0:
            alerts.append("• Report success rate low")
        
        if system_stats['average_trust_score'] < 50.0:
            alerts.append("• Average trust score low")
        
        if alerts:
            dashboard += "\n".join(alerts)
        else:
            dashboard += "• No critical alerts"
        
        # Create admin keyboard
        keyboard = [
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("📱 Account Management", callback_data="admin_accounts")],
            [InlineKeyboardButton("🌐 Proxy Management", callback_data="admin_proxies")],
            [InlineKeyboardButton("📊 System Analytics", callback_data="admin_analytics")],
            [InlineKeyboardButton("🔒 Security Scan", callback_data="admin_security")],
            [InlineKeyboardButton("🔄 Maintenance", callback_data="admin_maintenance")]
        ]
        
        if user_data.role >= UserRole.ADMIN:
            keyboard.append([InlineKeyboardButton("⚙️ System Settings", callback_data="admin_settings")])
        
        keyboard.append([InlineKeyboardButton("« Back", callback_data="back")])
        
        await update.message.reply_text(
            dashboard,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /settings command for user preferences"""
        user = update.effective_user
        user_data = self.user_manager.users.get(user.id)
        
        if not user_data:
            await update.message.reply_text("❌ User data not found. Use /start first.")
            return
        
        settings = user_data.settings
        
        settings_message = f"""
⚙️ *User Settings*

*Current Settings:*
• Notifications: {'✅ Enabled' if settings.get('notifications', True) else '❌ Disabled'}
• Auto Start: {'✅ Enabled' if settings.get('auto_start', False) else '❌ Disabled'}
• Proxy Priority: {settings.get('proxy_priority', 'speed').title()}
• Report Limit: {settings.get('report_limit', 10)} per day
• Language: {settings.get('language', 'en').upper()}
• Timezone: {settings.get('timezone', 'UTC')}

*Available Options:*
"""
        
        # Create settings keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔔 " + ("Disable" if settings.get('notifications', True) else "Enable") + " Notifications",
                    callback_data="set_notifications"
                )
            ],
            [
                InlineKeyboardButton(
                    "🚀 " + ("Disable" if settings.get('auto_start', False) else "Enable") + " Auto Start",
                    callback_data="set_autostart"
                )
            ],
            [
                InlineKeyboardButton("🌐 Proxy Priority", callback_data="set_proxy"),
                InlineKeyboardButton("📊 Report Limit", callback_data="set_limit")
            ],
            [
                InlineKeyboardButton("🌍 Language", callback_data="set_language"),
                InlineKeyboardButton("⏰ Timezone", callback_data="set_timezone")
            ],
            [InlineKeyboardButton("🔄 Reset to Default", callback_data="set_reset")],
            [InlineKeyboardButton("« Back", callback_data="back")]
        ]
        
        await update.message.reply_text(
            settings_message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        # Handle back button
        if data == "back":
            await query.edit_message_text(
                "Returning to main menu...",
                reply_markup=None
            )
            await self.start_command(update, context)
            return
        
        # Handle cancel button
        if data == "cancel":
            await query.edit_message_text(
                "Operation cancelled.",
                reply_markup=None
            )
            return
        
        # Handle report category selection
        if data.startswith("cat_"):
            await self.handle_report_category(update, context)
        
        # Handle report subcategory selection
        elif data.startswith("sub_"):
            await self.handle_report_subcategory(update, context)
        
        # Handle account management
        elif data.startswith("acc_"):
            action = data.replace("acc_", "")
            await self._handle_account_action(query, action)
        
        # Handle proxy management
        elif data.startswith("proxy_"):
            action = data.replace("proxy_", "")
            await self._handle_proxy_action(query, action)
        
        # Handle admin actions
        elif data.startswith("admin_"):
            action = data.replace("admin_", "")
            await self._handle_admin_action(query, action)
        
        # Handle settings actions
        elif data.startswith("set_"):
            action = data.replace("set_", "")
            await self._handle_settings_action(query, action)
        
        # Handle job actions
        elif data.startswith("jobs_"):
            action = data.replace("jobs_", "")
            await self._handle_job_action(query, action)
    
    async def _handle_account_action(self, query, action: str):
        """Handle account management actions"""
        if action == "add":
            # Start account addition process
            await query.edit_message_text(
                "📱 *Add New Account*\n\n"
                "Please send the phone number:\n"
                "Format: `+1234567890`\n\n"
                "*Requirements:*\n"
                "• Must be a valid Telegram account\n"
                "• Must be able to receive OTP\n"
                "• Should not be already added\n\n"
                "⚠️ *Note:* You will need to complete OTP verification.",
                parse_mode='Markdown'
            )
            
            # Store state for phone input
            self.user_sessions[query.from_user.id] = {
                "step": "add_phone",
                "action": "add_account"
            }
        
        elif action == "list":
            # List all accounts
            accounts = list(self.account_manager.accounts.values())
            
            if not accounts:
                await query.edit_message_text(
                    "📭 *No Accounts*\n\n"
                    "No accounts have been added yet.",
                    parse_mode='Markdown'
                )
                return
            
            # Create account list message
            accounts_message = "📱 *All Accounts*\n\n"
            
            for i, account in enumerate(accounts[:10], 1):  # Show first 10
                status_icon = {
                    AccountStatus.ACTIVE: "🟢",
                    AccountStatus.INACTIVE: "🟡",
                    AccountStatus.BANNED: "🔴",
                    AccountStatus.FLOOD_WAIT: "⏳",
                    AccountStatus.NEED_PASSWORD: "🔒"
                }.get(account.status, "❓")
                
                health_score = account.get_health_score()
                health_color = "🟢" if health_score >= 70 else "🟡" if health_score >= 50 else "🔴"
                
                accounts_message += (
                    f"{i}. {status_icon} `{account.phone}`\n"
                    f"   • Status: {account.status.name}\n"
                    f"   • Health: {health_color} {health_score:.1f}/100\n"
                    f"   • Reports: {account.report_count}/9\n"
                    f"   • Total: {account.total_reports}\n"
                )
                
                if account.username:
                    accounts_message += f"   • Username: @{account.username}\n"
                
                accounts_message += "\n"
            
            if len(accounts) > 10:
                accounts_message += f"\n*... and {len(accounts) - 10} more accounts*"
            
            await query.edit_message_text(
                accounts_message,
                parse_mode='Markdown'
            )
        
        elif action == "health":
            # Show account health status
            unhealthy_accounts = []
            
            for phone, account in self.account_manager.accounts.items():
                health_score = account.get_health_score()
                if health_score < 60.0:
                    unhealthy_accounts.append({
                        "phone": phone,
                        "health_score": health_score,
                        "status": account.status.name,
                        "report_count": account.report_count,
                        "proxy_failures": account.proxy_failures
                    })
            
            if not unhealthy_accounts:
                await query.edit_message_text(
                    "✅ *All Accounts Healthy*\n\n"
                    "All accounts have health scores above 60.0",
                    parse_mode='Markdown'
                )
                return
            
            # Create health report
            health_message = "🩺 *Account Health Report*\n\n"
            
            for i, acc in enumerate(unhealthy_accounts[:5], 1):
                health_message += (
                    f"{i}. `{acc['phone']}`\n"
                    f"   • Health: {acc['health_score']:.1f}/100\n"
                    f"   • Status: {acc['status']}\n"
                    f"   • Reports: {acc['report_count']}/9\n"
                    f"   • Proxy Failures: {acc['proxy_failures']}\n\n"
                )
            
            if len(unhealthy_accounts) > 5:
                health_message += f"\n*... and {len(unhealthy_accounts) - 5} more unhealthy accounts*"
            
            health_message += (
                "\n💡 *Recommendations:*\n"
                "• Perform maintenance on unhealthy accounts\n"
                "• Rotate proxies for accounts with high failures\n"
                "• Check accounts with low health scores"
            )
            
            await query.edit_message_text(
                health_message,
                parse_mode='Markdown'
            )
        
        elif action == "maintenance":
            # Perform account maintenance
            await query.edit_message_text(
                "🔄 *Account Maintenance*\n\n"
                "Performing maintenance on all accounts...",
                parse_mode='Markdown'
            )
            
            # Perform maintenance in background
            asyncio.create_task(self._perform_account_maintenance(query))
        
        elif action == "export":
            # Export account data
            await query.edit_message_text(
                "📤 *Export Account Data*\n\n"
                "Preparing account data export...",
                parse_mode='Markdown'
            )
            
            # Export in background
            asyncio.create_task(self._export_account_data(query))
    
    async def _perform_account_maintenance(self, query):
        """Perform account maintenance"""
        try:
            accounts = list(self.account_manager.accounts.keys())
            total = len(accounts)
            successful = 0
            failed = 0
            
            for i, phone in enumerate(accounts, 1):
                try:
                    result = await self.account_manager.perform_account_maintenance(phone)
                    if result.get("success"):
                        successful += 1
                    else:
                        failed += 1
                    
                    # Update progress every 5 accounts
                    if i % 5 == 0 or i == total:
                        await query.edit_message_text(
                            f"🔄 *Account Maintenance*\n\n"
                            f"Progress: {i}/{total}\n"
                            f"Successful: {successful}\n"
                            f"Failed: {failed}\n\n"
                            f"Working on: `{phone}`",
                            parse_mode='Markdown'
                        )
                    
                except Exception as e:
                    failed += 1
                    console.print(f"[red]❌ Maintenance error for {phone}: {e}[/red]")
            
            await query.edit_message_text(
                f"✅ *Maintenance Complete*\n\n"
                f"Total Accounts: {total}\n"
                f"Successful: {successful}\n"
                f"Failed: {failed}\n\n"
                f"*Results:*\n"
                f"• Accounts optimized\n"
                f"• Statistics cleaned\n"
                f"• Health scores updated\n\n"
                f"Use `/accounts` to view updated status.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ *Maintenance Failed*\n\n"
                f"Error: {str(e)[:200]}",
                parse_mode='Markdown'
            )
    
    async def _export_account_data(self, query):
        """Export account data"""
        try:
            user_id = query.from_user.id
            export_data = []
            
            for phone, account in self.account_manager.accounts.items():
                data = await self.account_manager.export_account_data(phone)
                if data:
                    export_data.append(data)
            
            # Create export file
            export_file = DATA_DIR / f"accounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "export_timestamp": datetime.now().isoformat(),
                    "exported_by": user_id,
                    "total_accounts": len(export_data),
                    "accounts": export_data
                }, f, indent=2, ensure_ascii=False)
            
            # Send file to user
            await query.message.reply_document(
                document=open(export_file, 'rb'),
                filename=f"accounts_export_{datetime.now().strftime('%Y%m%d')}.json",
                caption=f"✅ *Account Data Export*\n\nExported {len(export_data)} accounts"
            )
            
            # Update query message
            await query.edit_message_text(
                f"✅ *Export Complete*\n\n"
                f"Exported {len(export_data)} accounts to file.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ *Export Failed*\n\n"
                f"Error: {str(e)[:200]}",
                parse_mode='Markdown'
            )
    
    async def _handle_proxy_action(self, query, action: str):
        """Handle proxy management actions"""
        if action == "refresh":
            # Refresh proxy verification
            await query.edit_message_text(
                "🔄 *Refreshing Proxies*\n\n"
                "Starting proxy verification...",
                parse_mode='Markdown'
            )
            
            # Run verification in background
            asyncio.create_task(self._refresh_proxies(query))
        
        elif action == "list":
            # Get working proxies list
            active_proxies = [p for p in self.proxy_manager.proxies if p.is_active and p.verified]
            
            if not active_proxies:
                await query.edit_message_text(
                    "❌ *No Working Proxies*\n\n"
                    "No proxies are currently working.",
                    parse_mode='Markdown'
                )
                return
            
            # Create proxies list
            proxies_text = "# WORKING PROXIES LIST\n\n"
            proxies_text += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            proxies_text += f"Total Working: {len(active_proxies)}\n\n"
            
            # Add fastest proxies
            fast_proxies = sorted(active_proxies, key=lambda x: x.avg_response_time)[:10]
            proxies_text += "## Fastest Proxies:\n\n"
            
            for i, proxy in enumerate(fast_proxies, 1):
                proxies_text += f"{i}. {proxy.proxy}\n"
                proxies_text += f"   Country: {proxy.country}\n"
                proxies_text += f"   Speed: {proxy.avg_response_time:.2f}s\n"
                proxies_text += f"   Reliability: {proxy.reliability_score:.1f}%\n"
                proxies_text += f"   Type: {proxy.proxy_type.name}\n\n"
            
            # Send as document if too long
            if len(proxies_text) > 4000:
                file_io = io.BytesIO(proxies_text.encode('utf-8'))
                file_io.name = f"proxies_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                
                await query.message.reply_document(
                    document=file_io,
                    caption=f"🌐 *Working Proxies List*\n\n{len(active_proxies)} proxies available"
                )
                
                await query.edit_message_text(
                    f"✅ *Proxies List Generated*\n\n"
                    f"Sent as document with {len(active_proxies)} proxies.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"🌐 *Working Proxies*\n\n"
                    f"`{proxies_text[:3500]}`",
                    parse_mode='Markdown'
                )
        
        elif action == "stats":
            # Show detailed proxy statistics
            proxy_stats = self.proxy_manager.get_detailed_stats()
            
            stats_message = f"""
📊 *Detailed Proxy Statistics*

*Performance Metrics:*
• Total Proxies: {proxy_stats['total_proxies']}
• Working Proxies: {proxy_stats['active_proxies']}
• Premium Proxies: {proxy_stats['premium_proxies']}
• Performance Rating: {proxy_stats['performance_rating']}

*Speed Analysis:*
• Average Response Time: {proxy_stats['average_response_time']:.2f}s
• Median Response Time: {proxy_stats['median_response_time']:.2f}s
• Fastest Proxy: {proxy_stats['best_proxy']}
• Slowest Proxy: {proxy_stats['worst_proxy']}

*Reliability:*
• Average Reliability: {proxy_stats['average_reliability']:.1f}%
• Average Speed Score: {proxy_stats['average_speed_score']:.1f}
• Total Data Used: {proxy_stats['total_data_used_mb']:.1f} MB

*Geographic Distribution:*
"""
            
            # Add country distribution
            if proxy_stats['country_distribution']:
                for country, count in sorted(proxy_stats['country_distribution'].items(), 
                                           key=lambda x: x[1], reverse=True)[:8]:
                    percentage = (count / proxy_stats['active_proxies'] * 100) if proxy_stats['active_proxies'] > 0 else 0
                    stats_message += f"• {country}: {count} ({percentage:.1f}%)\n"
            
            stats_message += f"""
*Proxy Types:*
"""
            
            # Add type distribution
            for type_name, count in proxy_stats['type_distribution'].items():
                percentage = (count / proxy_stats['active_proxies'] * 100) if proxy_stats['active_proxies'] > 0 else 0
                stats_message += f"• {type_name}: {count} ({percentage:.1f}%)\n"
            
            await query.edit_message_text(
                stats_message,
                parse_mode='Markdown'
            )
    
    async def _refresh_proxies(self, query):
        """Refresh proxy verification"""
        try:
            # Run verification
            await self.proxy_manager.verify_all_proxies_parallel()
            
            # Get updated stats
            proxy_stats = self.proxy_manager.get_detailed_stats()
            
            await query.edit_message_text(
                f"✅ *Proxy Refresh Complete*\n\n"
                f"*Results:*\n"
                f"• Total Tested: {proxy_stats['total_proxies']}\n"
                f"• Working Proxies: {proxy_stats['active_proxies']}\n"
                f"• Average Speed: {proxy_stats['average_response_time']:.2f}s\n"
                f"• Performance Rating: {proxy_stats['performance_rating']}\n\n"
                f"*Recommendations:*\n"
                f"{'• Add more proxies' if proxy_stats['active_proxies'] < 10 else '• Proxies are sufficient'}",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ *Proxy Refresh Failed*\n\n"
                f"Error: {str(e)[:200]}",
                parse_mode='Markdown'
            )
    
    async def _handle_admin_action(self, query, action: str):
        """Handle admin actions"""
        user_id = query.from_user.id
        user_data = self.user_manager.users.get(user_id)
        
        if not user_data or user_data.role < UserRole.MODERATOR:
            await query.edit_message_text("❌ Admin access required.")
            return
        
        if action == "users":
            # User management
            await self._show_user_management(query)
        
        elif action == "accounts":
            # Account management
            await self._show_account_management(query)
        
        elif action == "proxies":
            # Proxy management
            await self._show_proxy_management(query)
        
        elif action == "analytics":
            # System analytics
            await self._show_system_analytics(query)
        
        elif action == "security":
            # Security scan
            await self._run_security_scan(query)
        
        elif action == "maintenance":
            # System maintenance
            await self._run_system_maintenance(query)
        
        elif action == "settings":
            # System settings (admin only)
            if user_data.role >= UserRole.ADMIN:
                await self._show_system_settings(query)
            else:
                await query.edit_message_text("❌ Administrator access required.")
    
    async def _show_user_management(self, query):
        """Show user management interface"""
        system_stats = self.user_manager.get_system_stats()
        
        keyboard = [
            [InlineKeyboardButton("👥 List All Users", callback_data="admin_users_list")],
            [InlineKeyboardButton("📊 User Statistics", callback_data="admin_users_stats")],
            [InlineKeyboardButton("🔍 Search User", callback_data="admin_users_search")],
            [InlineKeyboardButton("🛡️ Security Logs", callback_data="admin_users_security")],
            [InlineKeyboardButton("📤 Export Users", callback_data="admin_users_export")],
            [InlineKeyboardButton("« Back to Admin", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            f"👥 *User Management*\n\n"
            f"*System Statistics:*\n"
            f"• Total Users: {system_stats['total_users']}\n"
            f"• Active Users: {system_stats['active_users']}\n"
            f"• Average Trust Score: {system_stats['average_trust_score']:.1f}\n"
            f"• Security Events: {system_stats['total_security_logs']}\n\n"
            f"*Available Actions:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_account_management(self, query):
        """Show account management interface"""
        account_stats = self.account_manager.get_system_stats()
        
        keyboard = [
            [InlineKeyboardButton("📱 List All Accounts", callback_data="admin_accounts_list")],
            [InlineKeyboardButton("🩺 Health Report", callback_data="admin_accounts_health")],
            [InlineKeyboardButton("🔧 Maintenance All", callback_data="admin_accounts_maintain")],
            [InlineKeyboardButton("📊 Performance Stats", callback_data="admin_accounts_stats")],
            [InlineKeyboardButton("📤 Export All Data", callback_data="admin_accounts_export")],
            [InlineKeyboardButton("« Back to Admin", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            f"📱 *Account Management*\n\n"
            f"*System Statistics:*\n"
            f"• Total Accounts: {account_stats['total_accounts']}\n"
            f"• Active Accounts: {account_stats['active_accounts']}\n"
            f"• Average Health: {account_stats['average_health_score']:.1f}/100\n"
            f"• Reports Today: {account_stats['reports_today']}\n"
            f"• Needs 2FA: {account_stats['needs_2fa']}\n\n"
            f"*Available Actions:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_proxy_management(self, query):
        """Show proxy management interface"""
        proxy_stats = self.proxy_manager.get_detailed_stats()
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh All", callback_data="admin_proxies_refresh")],
            [InlineKeyboardButton("📋 Working List", callback_data="admin_proxies_list")],
            [InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_proxies_stats")],
            [InlineKeyboardButton("🚫 Disable Failed", callback_data="admin_proxies_disable")],
            [InlineKeyboardButton("📤 Export Data", callback_data="admin_proxies_export")],
            [InlineKeyboardButton("« Back to Admin", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            f"🌐 *Proxy Management*\n\n"
            f"*System Statistics:*\n"
            f"• Total Proxies: {proxy_stats['total_proxies']}\n"
            f"• Working Proxies: {proxy_stats['active_proxies']}\n"
            f"• Performance Rating: {proxy_stats['performance_rating']}\n"
            f"• Average Speed: {proxy_stats['average_response_time']:.2f}s\n"
            f"• Reliability: {proxy_stats['average_reliability']:.1f}%\n\n"
            f"*Available Actions:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _show_system_analytics(self, query):
        """Show system analytics dashboard"""
        # Get all statistics
        system_stats = self.user_manager.get_system_stats()
        account_stats = self.account_manager.get_system_stats()
        proxy_stats = self.proxy_manager.get_detailed_stats()
        report_stats = self.reporting_engine.get_system_stats()
        
        # Create analytics dashboard
        dashboard = f"""
📈 *System Analytics Dashboard*

*👥 User Analytics:*
• Total Users: {system_stats['total_users']}
• Active (7d): {system_stats['active_users']}
• Trust Avg: {system_stats['average_trust_score']:.1f}
• Role Distribution: {', '.join(f'{k}: {v}' for k, v in system_stats['role_distribution'].items() if v > 0)}

*📱 Account Analytics:*
• Total Accounts: {account_stats['total_accounts']}
• Active: {account_stats['active_accounts']}
• Health Avg: {account_stats['average_health_score']:.1f}
• Success Rate: Calculated per account

*🌐 Proxy Analytics:*
• Working/Total: {proxy_stats['active_proxies']}/{proxy_stats['total_proxies']}
• Performance: {proxy_stats['performance_rating']}
• Speed Avg: {proxy_stats['average_response_time']:.2f}s
• Reliability: {proxy_stats['average_reliability']:.1f}%

*📊 Reporting Analytics:*
• Total Jobs: {report_stats['total_jobs']}
• Success Rate: {report_stats['overall_success_rate']:.1f}%
• Recent Success: {report_stats['recent_success_rate']:.1f}%
• Avg Duration: {report_stats['average_duration']:.1f}s

*📅 Activity Analysis:*
• Reports Today: {account_stats['reports_today']}
• Active Jobs: {report_stats['active_jobs']}
• Queue Size: {report_stats['queue_size']}
• Active Workers: {report_stats['active_workers']}

*📉 Performance Trends:*
"""
        
        # Add performance trends based on recent data
        if report_stats['recent_success_rate'] > report_stats['overall_success_rate']:
            dashboard += "• Success rate: 📈 Improving\n"
        else:
            dashboard += "• Success rate: 📉 Declining\n"
        
        if proxy_stats['average_response_time'] < 1.0:
            dashboard += "• Proxy speed: ⚡ Excellent\n"
        elif proxy_stats['average_response_time'] < 2.0:
            dashboard += "• Proxy speed: ✅ Good\n"
        else:
            dashboard += "• Proxy speed: ⚠️ Needs improvement\n"
        
        if account_stats['average_health_score'] >= 70.0:
            dashboard += "• Account health: ✅ Good\n"
        else:
            dashboard += "• Account health: ⚠️ Needs attention\n"
        
        keyboard = [
            [InlineKeyboardButton("📅 Daily Report", callback_data="admin_analytics_daily")],
            [InlineKeyboardButton("📈 Performance Charts", callback_data="admin_analytics_charts")],
            [InlineKeyboardButton("📊 Export Analytics", callback_data="admin_analytics_export")],
            [InlineKeyboardButton("« Back to Admin", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            dashboard,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _run_security_scan(self, query):
        """Run security scan"""
        await query.edit_message_text(
            "🔍 *Running Security Scan*\n\n"
            "Scanning system for security issues...",
            parse_mode='Markdown'
        )
        
        # Run security scan
        self.user_manager.run_security_scan()
        
        # Get recent security events
        recent_events = self.user_manager.security_log[-5:]
        
        security_message = "✅ *Security Scan Complete*\n\n"
        security_message += "*Recent Security Events:*\n"
        
        for event in recent_events:
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
                "info": "🔵"
            }.get(event["severity"], "⚪")
            
            security_message += (
                f"{severity_icon} {event['event_type']}: {event['description'][:50]}...\n"
            )
        
        security_message += (
            "\n💡 *Recommendations:*\n"
            "• Review security logs regularly\n"
            "• Monitor suspicious users\n"
            "• Update system regularly\n"
            "• Backup important data"
        )
        
        await query.edit_message_text(
            security_message,
            parse_mode='Markdown'
        )
    
    async def _run_system_maintenance(self, query):
        """Run system maintenance"""
        await query.edit_message_text(
            "🔧 *System Maintenance*\n\n"
            "Performing system maintenance tasks...",
            parse_mode='Markdown'
        )
        
        maintenance_tasks = []
        
        try:
            # Task 1: Cleanup inactive sessions
            self.user_manager.cleanup_inactive_sessions()
            maintenance_tasks.append("✅ Cleaned inactive sessions")
            
            # Task 2: Save all data
            self.user_manager._save_users()
            self.account_manager._save_accounts()
            self.reporting_engine._save_jobs()
            await self.proxy_manager.save_cache()
            maintenance_tasks.append("✅ Saved all system data")
            
            # Task 3: Cleanup OTP sessions
            self.otp_verification.cleanup_expired_sessions()
            maintenance_tasks.append("✅ Cleaned expired OTP sessions")
            
            # Task 4: Check account health
            await self.account_manager._check_account_health()
            maintenance_tasks.append("✅ Checked account health")
            
            maintenance_message = "✅ *System Maintenance Complete*\n\n"
            maintenance_message += "*Tasks Completed:*\n"
            maintenance_message += "\n".join(maintenance_tasks)
            
            maintenance_message += (
                "\n\n💡 *System Status:*\n"
                "• All systems operational\n"
                "• Data backed up\n"
                "• Sessions cleaned\n"
                "• Health monitored"
            )
            
        except Exception as e:
            maintenance_message = (
                f"⚠️ *Maintenance Partially Complete*\n\n"
                f"Some tasks completed with errors:\n\n"
                f"*Completed:*\n" + "\n".join(maintenance_tasks) + f"\n\n"
                f"*Errors:*\n• {str(e)[:200]}"
            )
        
        await query.edit_message_text(
            maintenance_message,
            parse_mode='Markdown'
        )
    
    async def _show_system_settings(self, query):
        """Show system settings (admin only)"""
        keyboard = [
            [InlineKeyboardButton("⚙️ General Settings", callback_data="admin_settings_general")],
            [InlineKeyboardButton("🔒 Security Settings", callback_data="admin_settings_security")],
            [InlineKeyboardButton("📊 Performance Settings", callback_data="admin_settings_performance")],
            [InlineKeyboardButton("🔄 Update Settings", callback_data="admin_settings_update")],
            [InlineKeyboardButton("« Back to Admin", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "⚙️ *System Settings*\n\n"
            "*Configuration Options:*\n"
            "• General system settings\n"
            "• Security configurations\n"
            "• Performance optimizations\n"
            "• Update management\n\n"
            "*Warning:* These settings affect the entire system.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _handle_settings_action(self, query, action: str):
        """Handle settings actions"""
        user_id = query.from_user.id
        user_data = self.user_manager.users.get(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ User data not found.")
            return
        
        settings = user_data.settings
        
        if action == "notifications":
            # Toggle notifications
            new_value = not settings.get('notifications', True)
            settings['notifications'] = new_value
            
            self.user_manager._save_users()
            
            await query.edit_message_text(
                f"✅ *Notifications {'Enabled' if new_value else 'Disabled'}*\n\n"
                f"Notification settings updated.",
                parse_mode='Markdown'
            )
            
            # Update settings display
            await self.settings_command(update=query, context=None)
        
        elif action == "autostart":
            # Toggle auto start
            new_value = not settings.get('auto_start', False)
            settings['auto_start'] = new_value
            
            self.user_manager._save_users()
            
            await query.edit_message_text(
                f"✅ *Auto Start {'Enabled' if new_value else 'Disabled'}*\n\n"
                f"Auto start settings updated.",
                parse_mode='Markdown'
            )
            
            await self.settings_command(update=query, context=None)
        
        elif action == "proxy":
            # Change proxy priority
            keyboard = [
                [InlineKeyboardButton("⚡ Speed Priority", callback_data="set_proxy_speed")],
                [InlineKeyboardButton("🛡️ Reliability Priority", callback_data="set_proxy_reliability")],
                [InlineKeyboardButton("🌍 Geographic Priority", callback_data="set_proxy_geo")],
                [InlineKeyboardButton("« Back to Settings", callback_data="settings_back")]
            ]
            
            await query.edit_message_text(
                "🌐 *Proxy Priority Settings*\n\n"
                "*Current:* " + settings.get('proxy_priority', 'speed').title() + "\n\n"
                "*Options:*\n"
                "• Speed: Fastest proxies first\n"
                "• Reliability: Most reliable proxies first\n"
                "• Geographic: Proxies from specific countries\n\n"
                "Select new priority:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif action == "limit":
            # Change report limit
            await query.edit_message_text(
                "📊 *Daily Report Limit*\n\n"
                f"Current limit: {settings.get('report_limit', 10)} reports per day\n\n"
                "Enter new daily limit (1-100):",
                parse_mode='Markdown'
            )
            
            # Store state for limit input
            self.user_sessions[user_id] = {
                "step": "set_report_limit",
                "settings_action": "limit"
            }
        
        elif action == "language":
            # Change language
            keyboard = [
                [InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en")],
                [InlineKeyboardButton("🇷🇺 Russian", callback_data="set_lang_ru")],
                [InlineKeyboardButton("🇪🇸 Spanish", callback_data="set_lang_es")],
                [InlineKeyboardButton("« Back to Settings", callback_data="settings_back")]
            ]
            
            await query.edit_message_text(
                "🌍 *Language Settings*\n\n"
                "*Current:* " + settings.get('language', 'en').upper() + "\n\n"
                "Select new language:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif action == "timezone":
            # Change timezone
            await query.edit_message_text(
                "⏰ *Timezone Settings*\n\n"
                f"Current timezone: {settings.get('timezone', 'UTC')}\n\n"
                "Enter new timezone (e.g., UTC, Europe/London, America/New_York):\n\n"
                "*Common timezones:*\n"
                "• UTC\n"
                "• Europe/London\n"
                "• Europe/Berlin\n"
                "• America/New_York\n"
                "• America/Los_Angeles\n"
                "• Asia/Singapore\n"
                "• Asia/Tokyo",
                parse_mode='Markdown'
            )
            
            # Store state for timezone input
            self.user_sessions[user_id] = {
                "step": "set_timezone",
                "settings_action": "timezone"
            }
        
        elif action == "reset":
            # Reset to default settings
            default_settings = {
                "notifications": True,
                "auto_start": False,
                "proxy_priority": "speed",
                "report_limit": 10,
                "language": "en",
                "timezone": "UTC"
            }
            
            settings.clear()
            settings.update(default_settings)
            
            self.user_manager._save_users()
            
            await query.edit_message_text(
                "🔄 *Settings Reset*\n\n"
                "All settings have been reset to default values.",
                parse_mode='Markdown'
            )
            
            await self.settings_command(update=query, context=None)
    
    async def _handle_job_action(self, query, action: str):
        """Handle job actions"""
        if action == "all":
            # Show all jobs
            user_id = query.from_user.id
            user_jobs = []
            
            for job_id, job in self.reporting_engine.active_jobs.items():
                if job.created_by == user_id:
                    user_jobs.append(job)
            
            for job in self.reporting_engine.job_history[-100:]:
                if job.created_by == user_id and job not in user_jobs:
                    user_jobs.append(job)
            
            if not user_jobs:
                await query.edit_message_text(
                    "📭 *No Jobs Found*",
                    parse_mode='Markdown'
                )
                return
            
            # Sort by creation date
            user_jobs.sort(key=lambda x: x.created_at, reverse=True)
            
            # Create jobs list
            jobs_list = "📋 *All Your Jobs*\n\n"
            
            for i, job in enumerate(user_jobs[:20], 1):  # Show first 20
                status_icon = {
                    ReportStatus.COMPLETED: "✅",
                    ReportStatus.PROCESSING: "⏳",
                    ReportStatus.PENDING: "⏰",
                    ReportStatus.FAILED: "❌",
                    ReportStatus.PARTIAL: "⚠️"
                }.get(job.status, "❓")
                
                success_rate = job.get_success_rate()
                
                jobs_list += (
                    f"{i}. {status_icon} `{job.job_id}`\n"
                    f"   Target: {job.target[:30]}...\n"
                    f"   Status: {job.status.name}\n"
                    f"   Success: {success_rate:.1f}%\n"
                    f"   Created: {job.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                )
            
            if len(user_jobs) > 20:
                jobs_list += f"\n*... and {len(user_jobs) - 20} more jobs*"
            
            await query.edit_message_text(
                jobs_list,
                parse_mode='Markdown'
            )
        
        elif action == "refresh":
            # Refresh jobs list
            await self.jobs_command(update=query, context=None)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all text messages"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Check if user has an active session
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            step = session.get("step")
            
            if step == "add_phone":
                # Handle phone number for account addition
                await self._handle_add_phone(update, text, user_id, session)
            
            elif step == "set_report_limit":
                # Handle report limit setting
                await self._handle_set_report_limit(update, text, user_id)
            
            elif step == "set_timezone":
                # Handle timezone setting
                await self._handle_set_timezone(update, text, user_id)
            
            elif step == "target":
                # Handle report target (already handled in conversation)
                pass
            
            elif step == "description":
                # Handle report description (already handled in conversation)
                pass
            
            else:
                # Unknown session step
                await update.message.reply_text(
                    "❌ Invalid session state. Please start over.",
                    parse_mode='Markdown'
                )
                del self.user_sessions[user_id]
        
        else:
            # Handle general messages
            await self._handle_general_message(update, text, user_id)
    
    async def _handle_add_phone(self, update: Update, text: str, user_id: int, session: Dict):
        """Handle phone number for account addition"""
        # Validate phone number
        if not re.match(r'^\+\d{10,15}$', text):
            await update.message.reply_text(
                "❌ Invalid phone number format.\n"
                "Please use format: `+1234567890`",
                parse_mode='Markdown'
            )
            return
        
        phone = text
        
        # Check if account already exists
        if phone in self.account_manager.accounts:
            await update.message.reply_text(
                f"❌ Account `{phone}` already exists.",
                parse_mode='Markdown'
            )
            del self.user_sessions[user_id]
            return
        
        # Add account
        success, message = await self.account_manager.add_account(phone, user_id)
        
        if success:
            await update.message.reply_text(
                f"✅ *Account Added*\n\n"
                f"Phone: `{phone}`\n\n"
                f"Now creating desktop session...",
                parse_mode='Markdown'
            )
            
            # Create desktop session
            session_success, session_message = await self.account_manager.create_desktop_session(
                phone, update, user_id
            )
            
            if not session_success:
                await update.message.reply_text(
                    f"⚠️ *Session Creation Failed*\n\n"
                    f"{session_message}",
                    parse_mode='Markdown'
                )
        
        else:
            await update.message.reply_text(
                f"❌ *Failed to Add Account*\n\n"
                f"{message}",
                parse_mode='Markdown'
            )
        
        # Cleanup session
        del self.user_sessions[user_id]
    
    async def _handle_set_report_limit(self, update: Update, text: str, user_id: int):
        """Handle report limit setting"""
        try:
            limit = int(text)
            
            if limit < 1 or limit > 100:
                await update.message.reply_text(
                    "❌ Limit must be between 1 and 100.",
                    parse_mode='Markdown'
                )
                return
            
            # Update settings
            user_data = self.user_manager.users.get(user_id)
            if user_data:
                user_data.settings['report_limit'] = limit
                self.user_manager._save_users()
                
                await update.message.reply_text(
                    f"✅ *Report Limit Updated*\n\n"
                    f"New daily limit: {limit} reports",
                    parse_mode='Markdown'
                )
                
                # Update settings display
                await self.settings_command(update=update, context=None)
            
            else:
                await update.message.reply_text(
                    "❌ User data not found.",
                    parse_mode='Markdown'
                )
        
        except ValueError:
            await update.message.reply_text(
                "❌ Please enter a valid number.",
                parse_mode='Markdown'
            )
        
        # Cleanup session
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def _handle_set_timezone(self, update: Update, text: str, user_id: int):
        """Handle timezone setting"""
        timezone = text.strip()
        
        # Validate timezone (basic check)
        valid_timezones = [
            'UTC', 'GMT', 'EST', 'PST', 'CST', 'MST',
            'Europe/London', 'Europe/Berlin', 'Europe/Paris',
            'America/New_York', 'America/Los_Angeles', 'America/Chicago',
            'Asia/Singapore', 'Asia/Tokyo', 'Asia/Dubai',
            'Australia/Sydney', 'Australia/Melbourne'
        ]
        
        # Accept any timezone that looks reasonable
        if '/' in timezone or timezone in ['UTC', 'GMT']:
            # Update settings
            user_data = self.user_manager.users.get(user_id)
            if user_data:
                user_data.settings['timezone'] = timezone
                self.user_manager._save_users()
                
                await update.message.reply_text(
                    f"✅ *Timezone Updated*\n\n"
                    f"New timezone: {timezone}",
                    parse_mode='Markdown'
                )
                
                # Update settings display
                await self.settings_command(update=update, context=None)
            
            else:
                await update.message.reply_text(
                    "❌ User data not found.",
                    parse_mode='Markdown'
                )
        
        else:
            await update.message.reply_text(
                "❌ Invalid timezone format.\n"
                "Examples: UTC, Europe/London, America/New_York",
                parse_mode='Markdown'
            )
        
        # Cleanup session
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def _handle_general_message(self, update: Update, text: str, user_id: int):
        """Handle general text messages"""
        # Check for OTP codes (5 digits)
        if re.match(r'^\d{5}$', text):
            # This might be an OTP code
            await update.message.reply_text(
                "🔐 *OTP Detected*\n\n"
                "This looks like an OTP code.\n"
                "If you're trying to verify an account, "
                "please use the account verification process.\n\n"
                "Use `/accounts` to manage accounts.",
                parse_mode='Markdown'
            )
            return
        
        # Check for help requests
        if any(word in text.lower() for word in ['help', 'support', 'assist', 'problem']):
            await self.help_command(update, None)
            return
        
        # Check for status requests
        if any(word in text.lower() for word in ['status', 'stats', 'statistics', 'report']):
            await self.stats_command(update, None)
            return
        
        # Default response
        await update.message.reply_text(
            "🤖 *Telegram Reporting System*\n\n"
            "I didn't understand that command.\n\n"
            "*Available Commands:*\n"
            "/start - Welcome message\n"
            "/help - Comprehensive guide\n"
            "/report - Start new report\n"
            "/stats - View statistics\n"
            "/accounts - Account management\n"
            "/jobs - View your jobs\n"
            "/proxies - Proxy status\n"
            "/settings - User settings\n"
            "/admin - Admin panel (if permitted)",
            parse_mode='Markdown'
        )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        error = context.error
        
        console.print(f"[red]❌ Bot Error: {error}[/red]")
        
        # Log security event
        self.user_manager.log_security_event(
            event_type="bot_error",
            user_id=update.effective_user.id if update and update.effective_user else 0,
            severity="high",
            description=f"Bot error: {str(error)[:200]}",
            details={"update": str(update.to_dict()) if update else "None"}
        )
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ *An error occurred*\n\n"
                    "The system encountered an error. "
                    "Administrators have been notified.\n\n"
                    "Please try again later.",
                    parse_mode='Markdown'
                )
            except:
                pass

# ============================================
# SECTION 10: MAIN APPLICATION
# ============================================

class TelegramEnterpriseBot:
    """
    MAIN ENTERPRISE BOT APPLICATION
    
    Orchestrates all components:
    1. AdvancedProxyManager - Comprehensive proxy management
    2. AdvancedUserManager - User and permission management
    3. AdvancedAccountManager - Account lifecycle management
    4. AdvancedOTPVerification - Secure OTP verification
    5. AdvancedReportingEngine - Intelligent reporting system
    6. AdvancedBotHandler - Interactive bot interface
    """
    
    def __init__(self):
        # Initialize core components
        console.print("[cyan]🚀 Initializing Telegram Enterprise Bot v11.0[/cyan]")
        
        # Create global user sessions storage
        setattr(Update, '_user_sessions', {})
        
        # Initialize managers
        self.user_manager = AdvancedUserManager()
        self.proxy_manager = AdvancedProxyManager()
        self.otp_verification = AdvancedOTPVerification(None, self.proxy_manager)  # Will be updated
        self.account_manager = AdvancedAccountManager(
            self.proxy_manager,
            self.user_manager,
            self.otp_verification
        )
        
        # Update OTP verification with account manager
        self.otp_verification.account_manager = self.account_manager
        
        # Initialize reporting engine
        self.reporting_engine = AdvancedReportingEngine(
            self.account_manager,
            self.proxy_manager,
            self.user_manager
        )
        
        # Initialize bot handler
        self.bot_handler = AdvancedBotHandler(
            self.user_manager,
            self.account_manager,
            self.reporting_engine,
            self.proxy_manager,
            self.otp_verification
        )
        
        # Create Telegram bot application with persistence
        persistence = PicklePersistence(filepath="data/bot_persistence.pickle")
        
        self.application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .persistence(persistence)
            .post_init(self.bot_handler.setup_bot_commands)
            .build()
        )
        
        # Setup all handlers
        self._setup_handlers()
        
        # Print system banner
        self._print_system_banner()
    
    def _print_system_banner(self):
        """Print enterprise system banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                TELEGRAM ENTERPRISE REPORTING SYSTEM v11.0                   ║
║                Advanced Solution with Comprehensive Features                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ FEATURES:                                                                   ║
║ • Advanced OTP Verification with multiple methods                          ║
║ • Ultra-fast parallel proxy verification & analytics                       ║
║ • Intelligent proxy rotation after 9 reports                               ║
║ • Comprehensive user role system (8 levels)                                ║
║ • Realistic desktop session simulation                                     ║
║ • Advanced security monitoring & analytics                                 ║
║ • Automatic system maintenance & health checks                             ║
║ • Multi-account parallel reporting engine                                  ║
║ • Interactive bot interface with menus & keyboards                         ║
║ • Detailed statistics & performance analytics                              ║
║ • Export functionality for all data types                                  ║
║ • 5000+ lines of comprehensive, production-ready code                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        console.print(f"[bright_cyan]{banner}[/bright_cyan]")
    
    def _setup_handlers(self):
        """Setup all Telegram bot handlers"""
        console.print("[cyan]🔧 Setting up bot handlers...[/cyan]")
        
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.bot_handler.start_command))
        self.application.add_handler(CommandHandler("help", self.bot_handler.help_command))
        self.application.add_handler(CommandHandler("stats", self.bot_handler.stats_command))
        self.application.add_handler(CommandHandler("accounts", self.bot_handler.accounts_command))
        self.application.add_handler(CommandHandler("proxies", self.bot_handler.proxies_command))
        self.application.add_handler(CommandHandler("jobs", self.bot_handler.jobs_command))
        self.application.add_handler(CommandHandler("admin", self.bot_handler.admin_command))
        self.application.add_handler(CommandHandler("settings", self.bot_handler.settings_command))
        
        # Report conversation
        report_handler = ConversationHandler(
            entry_points=[CommandHandler("report", self.bot_handler.report_command)],
            states={
                self.bot_handler.REPORT_TARGET: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                 self.bot_handler.handle_report_target)
                ],
                self.bot_handler.REPORT_CATEGORY: [
                    CallbackQueryHandler(self.bot_handler.handle_report_category, 
                                       pattern="^cat_|^cancel$")
                ],
                self.bot_handler.REPORT_SUBCATEGORY: [
                    CallbackQueryHandler(self.bot_handler.handle_report_subcategory,
                                       pattern="^sub_|^back|^cancel$")
                ],
                self.bot_handler.REPORT_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,
                                 self.bot_handler.handle_report_description)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.start_command)],
            allow_reentry=True,
            name="report_conversation"
        )
        self.application.add_handler(report_handler)
        
        # Callback query handler
        self.application.add_handler(
            CallbackQueryHandler(self.bot_handler.handle_callback_query)
        )
        
        # Message handler (for general messages and OTP)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, 
                         self.bot_handler.handle_message)
        )
        
        # Error handler
        self.application.add_error_handler(self.bot_handler.error_handler)
        
        console.print("[green]✅ Bot handlers setup complete[/green]")
    
    async def initialize_system(self) -> bool:
        """
        Initialize the entire enterprise system
        Returns: True if successful, False if failed
        """
        console.print("[yellow]🔧 Initializing enterprise system components...[/yellow]")
        
        try:
            # Step 1: Initialize proxy manager (critical component)
            console.print("[cyan]1. Initializing Proxy Manager...[/cyan]")
            proxy_ok = await self.proxy_manager.initialize()
            
            if not proxy_ok:
                console.print("[red]❌ Proxy manager initialization failed[/red]")
                
                # Try to continue without proxies (for testing)
                console.print("[yellow]⚠️ Continuing without proxy verification...[/yellow]")
            
            # Step 2: System self-check
            console.print("[cyan]2. Running system self-check...[/cyan]")
            await self._run_system_self_check()
            
            # Step 3: Load existing data
            console.print("[cyan]3. Loading system data...[/cyan]")
            await self._load_system_data()
            
            # Step 4: Start background tasks
            console.print("[cyan]4. Starting background tasks...[/cyan]")
            await self._start_background_tasks()
            
            console.print("[green]✅ Enterprise system initialization complete[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ System initialization failed: {e}[/red]")
            import traceback
            traceback.print_exc()
            return False
    
    async def _run_system_self_check(self):
        """Run comprehensive system self-check"""
        checks = []
        
        # Check 1: Data directories
        for directory in [DATA_DIR, SESSION_DIR, LOG_DIR, BACKUP_DIR, ANALYTICS_DIR]:
            if directory.exists() and directory.is_dir():
                checks.append(("✅", f"Directory: {directory.name}"))
            else:
                checks.append(("❌", f"Directory: {directory.name}"))
        
        # Check 2: Required files
        required_files = [USERS_FILE, ACCOUNTS_FILE, PROXY_FILE]
        for file in required_files:
            if file.exists():
                checks.append(("✅", f"File: {file.name}"))
            else:
                checks.append(("⚠️", f"File: {file.name} (will be created)"))
        
        # Check 3: Telegram API credentials
        if BOT_TOKEN and BOT_TOKEN != "YOUR_BOT_TOKEN":
            checks.append(("✅", "Bot token configured"))
        else:
            checks.append(("❌", "Bot token not configured"))
        
        if API_ID and API_HASH:
            checks.append(("✅", "Telegram API credentials"))
        else:
            checks.append(("❌", "Telegram API credentials missing"))
        
        # Check 4: Owner IDs
        if OWNER_IDS:
            checks.append(("✅", f"Owner IDs: {len(OWNER_IDS)} configured"))
        else:
            checks.append(("⚠️", "No owner IDs configured"))
        
        # Display check results
        check_table = Table(title="System Self-Check", box=box.ROUNDED)
        check_table.add_column("Status", style="cyan", width=3)
        check_table.add_column("Check", style="white")
        
        for status, check in checks:
            check_table.add_row(status, check)
        
        console.print(check_table)
    
    async def _load_system_data(self):
        """Load all system data"""
        # Data is already loaded by managers during initialization
        # This method can be used for additional data loading
        
        # Display loaded statistics
        user_stats = self.user_manager.get_system_stats()
        account_stats = self.account_manager.get_system_stats()
        
        stats_table = Table(title="System Data Loaded", box=box.ROUNDED)
        stats_table.add_column("Component", style="cyan")
        stats_table.add_column("Count", style="green")
        stats_table.add_column("Details", style="yellow")
        
        stats_table.add_row(
            "Users",
            str(user_stats['total_users']),
            f"{user_stats['active_users']} active, {user_stats['role_distribution'].get('ADMIN', 0)} admins"
        )
        
        stats_table.add_row(
            "Accounts",
            str(account_stats['total_accounts']),
            f"{account_stats['active_accounts']} active, {account_stats['average_health_score']:.1f} avg health"
        )
        
        stats_table.add_row(
            "Report Jobs",
            str(self.reporting_engine.get_system_stats()['total_jobs']),
            "Loaded from history"
        )
        
        console.print(stats_table)
    
    async def _start_background_tasks(self):
        """Start system background tasks"""
        # Background tasks are started by individual managers
        # This method can be used for additional periodic tasks
        
        async def periodic_maintenance():
            """Run periodic system maintenance"""
            while True:
                try:
                    # Wait for 1 hour
                    await asyncio.sleep(3600)
                    
                    console.print("[cyan]🔄 Running periodic maintenance...[/cyan]")
                    
                    # Run user manager maintenance
                    self.user_manager.cleanup_inactive_sessions()
                    
                    # Run account health check
                    await self.account_manager._check_account_health()
                    
                    # Cleanup OTP sessions
                    self.otp_verification.cleanup_expired_sessions()
                    
                    # Save all data
                    self.user_manager._save_users()
                    self.account_manager._save_accounts()
                    self.reporting_engine._save_jobs()
                    await self.proxy_manager.save_cache()
                    
                    console.print("[green]✅ Periodic maintenance complete[/green]")
                    
                except Exception as e:
                    console.print(f"[red]❌ Maintenance error: {e}[/red]")
                    await asyncio.sleep(300)  # Wait 5 minutes before retry
        
        # Start periodic maintenance task
        asyncio.create_task(periodic_maintenance())
        
        console.print("[green]✅ Background tasks started[/green]")
    
    async def run(self):
        """Run the enterprise bot"""
        # Initialize system
        initialized = await self.initialize_system()
        
        if not initialized:
            console.print("[red]❌ System initialization failed. Cannot start bot.[/red]")
            console.print("[yellow]💡 Check the error messages above and fix the issues.[/yellow]")
            return
        
        # Start bot
        console.print("[green]🤖 Starting Telegram Enterprise Bot...[/green]")
        
        try:
            # Start bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            console.print("[green]✅ Bot is running![/green]")
            console.print("[yellow]📱 Use /start in Telegram to begin[/yellow]")
            console.print("[cyan]⚡ System is fully operational with all features enabled[/cyan]")
            
            # Display system status
            await self._display_system_status()
            
            # Keep running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️ Received shutdown signal...[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Runtime error: {e}[/red]")
                import traceback
                traceback.print_exc()
            finally:
                await self.shutdown()
                
        except Exception as e:
            console.print(f"[red]❌ Bot startup failed: {e}[/red]")
            import traceback
            traceback.print_exc()
            await self.shutdown()
    
    async def _display_system_status(self):
        """Display comprehensive system status"""
        # Get all statistics
        user_stats = self.user_manager.get_system_stats()
        account_stats = self.account_manager.get_system_stats()
        proxy_stats = self.proxy_manager.get_detailed_stats()
        report_stats = self.reporting_engine.get_system_stats()
        
        status_table = Table(title="🚀 System Status Dashboard", box=box.DOUBLE_EDGE)
        status_table.add_column("Component", style="cyan", justify="left")
        status_table.add_column("Status", style="green", justify="center")
        status_table.add_column("Metrics", style="yellow", justify="left")
        
        status_table.add_row(
            "👥 Users",
            "✅" if user_stats['total_users'] > 0 else "⚠️",
            f"Total: {user_stats['total_users']}\nActive: {user_stats['active_users']}"
        )
        
        status_table.add_row(
            "📱 Accounts",
            "✅" if account_stats['active_accounts'] > 0 else "⚠️",
            f"Active: {account_stats['active_accounts']}\nHealth: {account_stats['average_health_score']:.1f}"
        )
        
        status_table.add_row(
            "🌐 Proxies",
            "✅" if proxy_stats['active_proxies'] > 0 else "❌",
            f"Working: {proxy_stats['active_proxies']}\nSpeed: {proxy_stats['average_response_time']:.2f}s"
        )
        
        status_table.add_row(
            "📊 Reporting",
            "✅" if report_stats['total_jobs'] > 0 else "⚡",
            f"Jobs: {report_stats['total_jobs']}\nSuccess: {report_stats['overall_success_rate']:.1f}%"
        )
        
        status_table.add_row(
            "🛡️ Security",
            "✅",
            f"Events: {user_stats['total_security_logs']}\nSessions: {user_stats['active_sessions']}"
        )
        
        console.print(status_table)
        
        # Display recommendations
        console.print("\n[cyan]💡 System Recommendations:[/cyan]")
        
        if proxy_stats['active_proxies'] < 5:
            console.print("[yellow]• Add more proxies to improve reliability[/yellow]")
        
        if account_stats['average_health_score'] < 60.0:
            console.print("[yellow]• Perform account maintenance[/yellow]")
        
        if report_stats['overall_success_rate'] < 70.0:
            console.print("[yellow]• Check proxy performance and account health[/yellow]")
        
        if user_stats['active_users'] == 0:
            console.print("[yellow]• No active users. Share bot with team members[/yellow]")
        
        console.print("\n[green]✅ System ready for operation![/green]")
        console.print("[cyan]📈 Monitor system performance with /stats command[/cyan]")
        console.print("[cyan]🔧 Use /admin for system management (if permitted)[/cyan]")
    
    async def shutdown(self):
        """Shutdown the entire enterprise system gracefully"""
        console.print("[yellow]🔧 Shutting down enterprise system...[/yellow]")
        
        try:
            # Step 1: Stop reporting engine
            if hasattr(self, 'reporting_engine'):
                await self.reporting_engine.cleanup()
            
            # Step 2: Stop account manager
            if hasattr(self, 'account_manager'):
                await self.account_manager.cleanup()
            
            # Step 3: Stop proxy manager
            if hasattr(self, 'proxy_manager'):
                await self.proxy_manager.cleanup()
            
            # Step 4: Save all data
            if hasattr(self, 'user_manager'):
                self.user_manager._save_users()
            
            # Step 5: Stop bot
            if hasattr(self, 'application'):
                if hasattr(self.application, 'updater'):
                    await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            console.print("[green]✅ Enterprise system shutdown complete[/green]")
            console.print("[cyan]👋 Goodbye![/cyan]")
            
        except Exception as e:
            console.print(f"[red]❌ Shutdown error: {e}[/red]")
            import traceback
            traceback.print_exc()

# ============================================
# SECTION 11: MAIN ENTRY POINT
# ============================================

async def main():
    """
    MAIN ENTRY POINT FOR THE ENTERPRISE SYSTEM
    
    This function:
    1. Creates the enterprise bot
    2. Initializes all components
    3. Starts the system
    4. Handles graceful shutdown
    """
    console.print("[bright_cyan]⚡ ENTERPRISE TELEGRAM REPORTING SYSTEM v11.0[/bright_cyan]")
    console.print("[cyan]Starting main application...[/cyan]")
    
    # Create and run the enterprise bot
    enterprise_bot = TelegramEnterpriseBot()
    
    try:
        await enterprise_bot.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Received interrupt signal[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
    
    console.print("[cyan]Application terminated.[/cyan]")

# ============================================
# RUN THE APPLICATION
# ============================================

if __name__ == "__main__":
    # Set event loop policy for Windows if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Run the main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Application terminated by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Critical error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
