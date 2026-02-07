#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM ENTERPRISE REPORTING SYSTEM v6.0
Enhanced with owner/sudo system, tg:// links support, and realistic delays
"""

import asyncio
import time
import re
import json
import logging
import random
import string
import hashlib
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import aiofiles
import aiohttp
import sys
import os
import shutil
from collections import defaultdict, deque
import csv
import math
import uuid
from dataclasses import dataclass, field
import pickle
import base64
from io import BytesIO
import urllib.parse

# Telegram Bot API
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

# Telethon for Telegram Client
from telethon import TelegramClient, events, Button
from telethon.errors import (
    FloodWaitError, SessionPasswordNeededError, PhoneCodeInvalidError,
    PhoneCodeExpiredError, AuthKeyDuplicatedError, UserNotParticipantError
)
from telethon.tl.functions.messages import ReportRequest, SendReactionRequest, GetMessagesRequest
from telethon.tl.functions.channels import JoinChannelRequest, GetParticipantsRequest, GetFullChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.account import ReportPeerRequest, UpdateProfileRequest
from telethon.tl.types import (
    InputReportReasonSpam, InputReportReasonViolence, InputReportReasonPornography,
    InputReportReasonChildAbuse, InputReportReasonCopyright, InputReportReasonGeoIrrelevant,
    InputReportReasonFake, InputReportReasonIllegalDrugs, InputReportReasonPersonalDetails,
    InputReportReasonOther, PeerUser, PeerChannel, PeerChat,
    InputPeerUser, InputPeerChannel, InputPeerChat,
    User, Channel, Chat, UserProfilePhoto, ChannelFull,
    ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRow,
    ReactionEmoji, MessageEntityTextUrl, MessageEntityMention,
    InputMessageEntityMentionName
)

# Rich for console output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.columns import Columns
from rich.live import Live
from rich.text import Text
from rich import box
from rich.syntax import Syntax

console = Console()

# ===== CONFIGURATION =====
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
API_ID = 27157163
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"

# Owners (full access)
OWNER_IDS = [6118760915, 1366105247]

# Proxy configuration
PROXY_FILE = "proxy.txt"
PROXY_GITHUB_URLS = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt"
]

# Fast response countries (prioritize these proxies)
FAST_COUNTRIES = ["Germany", "Netherlands", "Singapore", "United States", "Japan", "South Korea"]

# Session and data directories
SESSION_DIR = Path("sessions")
DATA_DIR = Path("data")
LOGS_DIR = Path("logs")
EXPORTS_DIR = Path("exports")
USERS_FILE = DATA_DIR / "users.json"
PROXY_CACHE_FILE = DATA_DIR / "proxy_cache.json"

# Create directories
for dir_path in [SESSION_DIR, DATA_DIR, LOGS_DIR, EXPORTS_DIR]:
    dir_path.mkdir(exist_ok=True)

# ===== ENHANCED DATA MODELS =====

class UserRole(Enum):
    OWNER = "OWNER"
    SUDO = "SUDO"
    USER = "USER"

class ReportPriority(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class ReportStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FLOOD_WAIT = "FLOOD_WAIT"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"

class AccountStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BANNED = "BANNED"
    FLOOD_WAIT = "FLOOD_WAIT"
    VERIFICATION_NEEDED = "VERIFICATION_NEEDED"

@dataclass
class TelegramUser:
    """Telegram user with role management"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    role: UserRole = UserRole.USER
    added_at: datetime = field(default_factory=datetime.now)
    reports_made: int = 0
    last_active: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "role": self.role.value,
            "added_at": self.added_at.isoformat(),
            "reports_made": self.reports_made,
            "last_active": self.last_active.isoformat() if self.last_active else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TelegramUser':
        user = cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            role=UserRole(data.get("role", "USER")),
            reports_made=data.get("reports_made", 0)
        )
        if data.get("added_at"):
            user.added_at = datetime.fromisoformat(data["added_at"])
        if data.get("last_active"):
            user.last_active = datetime.fromisoformat(data["last_active"])
        return user

@dataclass
class TelegramAccount:
    """Telegram account with enhanced session management"""
    phone: str
    session_file: Path
    proxy: Optional[str] = None
    client: Optional[TelegramClient] = None
    status: AccountStatus = AccountStatus.INACTIVE
    report_count: int = 0
    last_report_time: Optional[datetime] = None
    total_reports: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    country: Optional[str] = None
    is_premium: bool = False
    last_proxy_rotation: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "phone": self.phone,
            "session_file": str(self.session_file),
            "proxy": self.proxy,
            "status": self.status.value,
            "report_count": self.report_count,
            "total_reports": self.total_reports,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "tags": self.tags,
            "country": self.country,
            "is_premium": self.is_premium,
            "last_proxy_rotation": self.last_proxy_rotation.isoformat() if self.last_proxy_rotation else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TelegramAccount':
        account = cls(
            phone=data["phone"],
            session_file=Path(data["session_file"]),
            proxy=data.get("proxy"),
            status=AccountStatus(data["status"]),
            report_count=data.get("report_count", 0),
            total_reports=data.get("total_reports", 0),
            country=data.get("country"),
            is_premium=data.get("is_premium", False)
        )
        if data.get("created_at"):
            account.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_used"):
            account.last_used = datetime.fromisoformat(data["last_used"])
        if data.get("last_proxy_rotation"):
            account.last_proxy_rotation = datetime.fromisoformat(data["last_proxy_rotation"])
        account.tags = data.get("tags", [])
        return account

@dataclass
class ReportJob:
    """Enhanced reporting job with realistic delays"""
    target: str
    target_type: str  # "user", "channel", "group"
    reason_category: str
    reason_subcategory: str
    description: str
    accounts_needed: int = 1
    priority: ReportPriority = ReportPriority.MEDIUM
    schedule_time: Optional[datetime] = None
    created_by: int = None
    created_at: datetime = field(default_factory=datetime.now)
    status: ReportStatus = ReportStatus.PENDING
    assigned_accounts: List[str] = field(default_factory=list)
    completed_accounts: List[str] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    random_delay_enabled: bool = True
    delay_min: float = 2.0
    delay_max: float = 8.0
    
    def to_dict(self) -> Dict:
        return {
            "target": self.target,
            "target_type": self.target_type,
            "reason_category": self.reason_category,
            "reason_subcategory": self.reason_subcategory,
            "description": self.description,
            "accounts_needed": self.accounts_needed,
            "priority": self.priority.value,
            "schedule_time": self.schedule_time.isoformat() if self.schedule_time else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "assigned_accounts": self.assigned_accounts,
            "completed_accounts": self.completed_accounts,
            "results": self.results,
            "user_agent": self.user_agent,
            "random_delay_enabled": self.random_delay_enabled,
            "delay_min": self.delay_min,
            "delay_max": self.delay_max
        }

# ===== ENHANCED RANDOM DELAY SYSTEM =====

class RandomDelaySystem:
    """Intelligent random delay system for realistic behavior"""
    
    def __init__(self):
        self.delay_patterns = {
            "fast": {"min": 1.5, "max": 3.5, "weight": 0.3},
            "normal": {"min": 3.0, "max": 7.0, "weight": 0.5},
            "slow": {"min": 6.0, "max": 12.0, "weight": 0.2}
        }
        
        self.action_delays = {
            "typing": {"min": 0.05, "max": 0.2},  # per character
            "thinking": {"min": 1.0, "max": 4.0},
            "scrolling": {"min": 0.5, "max": 2.0},
            "loading": {"min": 0.3, "max": 1.5},
            "network": {"min": 0.1, "max": 0.8}
        }
        
        self.human_error_chance = 0.05  # 5% chance of human-like error
    
    async def get_random_delay(self, pattern: str = "normal") -> float:
        """Get random delay based on pattern"""
        if pattern not in self.delay_patterns:
            pattern = "normal"
        
        config = self.delay_patterns[pattern]
        delay = random.uniform(config["min"], config["max"])
        
        # Add small random variation
        variation = random.uniform(-0.3, 0.3)
        return max(0.5, delay + variation)
    
    async def simulate_typing(self, text: str) -> float:
        """Simulate realistic typing with errors"""
        total_delay = 0
        words = text.split()
        
        for word in words:
            # Type each character
            for char in word:
                char_delay = random.uniform(
                    self.action_delays["typing"]["min"],
                    self.action_delays["typing"]["max"]
                )
                await asyncio.sleep(char_delay)
                total_delay += char_delay
                
                # Simulate occasional backspace (human error)
                if random.random() < self.human_error_chance:
                    await asyncio.sleep(char_delay * 0.8)  # Backspace delay
                    total_delay += char_delay * 0.8
                    await asyncio.sleep(char_delay)  # Re-type
                    total_delay += char_delay
            
            # Space between words
            await asyncio.sleep(0.1)
            total_delay += 0.1
            
            # Occasional pause between words
            if random.random() < 0.1:  # 10% chance
                pause = random.uniform(0.3, 1.0)
                await asyncio.sleep(pause)
                total_delay += pause
        
        return total_delay
    
    async def simulate_thinking(self) -> float:
        """Simulate thinking before action"""
        thinking_time = random.uniform(
            self.action_delays["thinking"]["min"],
            self.action_delays["thinking"]["max"]
        )
        
        # Add micro-pauses
        for _ in range(random.randint(1, 3)):
            micro_pause = random.uniform(0.1, 0.3)
            await asyncio.sleep(micro_pause)
            thinking_time += micro_pause
        
        return thinking_time
    
    async def simulate_page_load(self) -> float:
        """Simulate page loading delay"""
        load_time = random.uniform(
            self.action_delays["loading"]["min"],
            self.action_delays["loading"]["max"]
        )
        await asyncio.sleep(load_time)
        return load_time
    
    async def simulate_scrolling(self, pages: int = 1) -> float:
        """Simulate scrolling through content"""
        total_scroll_time = 0
        for _ in range(pages):
            scroll_time = random.uniform(
                self.action_delays["scrolling"]["min"],
                self.action_delays["scrolling"]["max"]
            )
            await asyncio.sleep(scroll_time)
            total_scroll_time += scroll_time
            
            # Small pause after scroll
            if random.random() < 0.5:
                await asyncio.sleep(0.2)
                total_scroll_time += 0.2
        
        return total_scroll_time

# ===== ENHANCED PROXY MANAGER WITH COUNTRY PRIORITIZATION =====

class EnhancedProxyManager:
    """Proxy manager with country prioritization and rotation"""
    
    def __init__(self):
        self.proxies: List[Dict] = []
        self.proxy_history: Dict[str, List] = defaultdict(list)
        self.country_stats: Dict[str, Dict] = defaultdict(lambda: {"success": 0, "fail": 0, "speed": [], "last_used": None})
        self.banned_proxies: set = set()
        self.fast_countries = FAST_COUNTRIES
        self.proxy_refresh_interval = 3600  # Refresh every hour
        self.last_refresh = None
        
    async def load_proxies(self):
        """Load and prioritize proxies"""
        console.print("[cyan]Loading and prioritizing proxies...[/cyan]")
        
        # Load from all sources
        await self._load_from_file()
        await self._load_from_github()
        await self._load_from_cache()
        
        # Prioritize by country speed
        self._prioritize_proxies()
        
        console.print(f"[green]Loaded {len(self.proxies)} proxies[/green]")
        
        # Show country distribution
        country_dist = defaultdict(int)
        for proxy in self.proxies:
            if not proxy["banned"]:
                country_dist[proxy["country"]] += 1
        
        table = Table(title="Proxy Distribution by Country", box=box.ROUNDED)
        table.add_column("Country", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Status", style="yellow")
        
        for country, count in sorted(country_dist.items(), key=lambda x: x[1], reverse=True):
            status = "⚡ FAST" if country in self.fast_countries else "✓ OK"
            table.add_row(country, str(count), status)
        
        console.print(table)
    
    def _prioritize_proxies(self):
        """Prioritize proxies from fast countries"""
        # Sort proxies: fast countries first, then success rate, then speed
        self.proxies.sort(key=lambda x: (
            0 if x["country"] in self.fast_countries else 1,
            -x["success_count"],  # Negative for descending
            -x["avg_speed"]
        ))
    
    async def get_fast_proxy(self, account_phone: str = None) -> Optional[str]:
        """Get proxy from fast response country"""
        available = [p for p in self.proxies if not p["banned"]]
        
        if not available:
            console.print("[yellow]No proxies available, trying banned ones[/yellow]")
            available = self.proxies
        
        # Try to get from fast country first
        fast_proxies = [p for p in available if p["country"] in self.fast_countries]
        
        if fast_proxies:
            # Sort fast proxies by success rate
            fast_proxies.sort(key=lambda x: (-x["success_count"], -x["avg_speed"]))
            selected = fast_proxies[0]
        else:
            # Fallback to any proxy
            available.sort(key=lambda x: (-x["success_count"], -x["avg_speed"]))
            selected = available[0] if available else None
        
        if not selected:
            return None
        
        selected["last_used"] = datetime.now()
        
        # Update history
        if account_phone:
            self.proxy_history[account_phone].append({
                "proxy": selected["proxy"],
                "time": datetime.now().isoformat(),
                "country": selected["country"]
            })
        
        return selected["proxy"]
    
    async def rotate_proxy_for_account(self, account_phone: str) -> Optional[str]:
        """Rotate to a different country proxy"""
        current_proxy = None
        
        # Find current proxy
        for proxy in self.proxies:
            if proxy["proxy"] == self._get_current_proxy(account_phone):
                current_proxy = proxy
                break
        
        # Get proxies from different countries
        different_country_proxies = []
        same_country_proxies = []
        
        for proxy in self.proxies:
            if proxy["banned"]:
                continue
            if current_proxy and proxy["country"] != current_proxy["country"]:
                different_country_proxies.append(proxy)
            else:
                same_country_proxies.append(proxy)
        
        # Prefer different country
        if different_country_proxies:
            different_country_proxies.sort(key=lambda x: (-x["success_count"], -x["avg_speed"]))
            new_proxy = different_country_proxies[0]["proxy"]
        elif same_country_proxies:
            same_country_proxies.sort(key=lambda x: (-x["success_count"], -x["avg_speed"]))
            new_proxy = same_country_proxies[0]["proxy"]
        else:
            return None
        
        # Update account's proxy history
        if account_phone in self.proxy_history:
            self.proxy_history[account_phone].append({
                "proxy": new_proxy,
                "time": datetime.now().isoformat(),
                "action": "rotated"
            })
        
        console.print(f"[cyan]Rotated proxy for {account_phone} to {new_proxy[:30]}...[/cyan]")
        return new_proxy
    
    def _get_current_proxy(self, account_phone: str) -> Optional[str]:
        """Get current proxy for account"""
        if account_phone in self.proxy_history and self.proxy_history[account_phone]:
            return self.proxy_history[account_phone][-1]["proxy"]
        return None

# ===== USER MANAGEMENT SYSTEM =====

class UserManager:
    """Manage bot users with roles"""
    
    def __init__(self):
        self.users: Dict[int, TelegramUser] = {}
        self.users_file = USERS_FILE
        self.owner_ids = OWNER_IDS
        
        # Initialize with owners
        self._initialize_owners()
        self._load_users()
    
    def _initialize_owners(self):
        """Initialize owner accounts"""
        for owner_id in self.owner_ids:
            if owner_id not in self.users:
                self.users[owner_id] = TelegramUser(
                    user_id=owner_id,
                    role=UserRole.OWNER,
                    added_at=datetime.now()
                )
    
    def _load_users(self):
        """Load users from file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    for user_data in data.values():
                        user = TelegramUser.from_dict(user_data)
                        self.users[user.user_id] = user
                console.print(f"[green]Loaded {len(self.users)} users[/green]")
        except Exception as e:
            console.print(f"[red]Error loading users: {e}[/red]")
    
    def _save_users(self):
        """Save users to file"""
        try:
            data = {str(uid): user.to_dict() for uid, user in self.users.items()}
            with open(self.users_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving users: {e}[/red]")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                role: UserRole = UserRole.USER) -> bool:
        """Add a new user"""
        if user_id in self.users:
            return False
        
        user = TelegramUser(
            user_id=user_id,
            username=username,
            first_name=first_name,
            role=role,
            added_at=datetime.now()
        )
        
        self.users[user_id] = user
        self._save_users()
        
        console.print(f"[green]Added user {user_id} with role {role.value}[/green]")
        return True
    
    def promote_to_sudo(self, user_id: int) -> bool:
        """Promote user to sudo"""
        if user_id not in self.users:
            return False
        
        self.users[user_id].role = UserRole.SUDO
        self._save_users()
        
        console.print(f"[green]Promoted user {user_id} to SUDO[/green]")
        return True
    
    def demote_from_sudo(self, user_id: int) -> bool:
        """Demote user from sudo"""
        if user_id not in self.users or user_id in self.owner_ids:
            return False
        
        self.users[user_id].role = UserRole.USER
        self._save_users()
        
        console.print(f"[yellow]Demoted user {user_id} to USER[/yellow]")
        return True
    
    def get_user_role(self, user_id: int) -> Optional[UserRole]:
        """Get user role"""
        if user_id in self.users:
            return self.users[user_id].role
        return None
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is owner"""
        return user_id in self.owner_ids
    
    def is_sudo(self, user_id: int) -> bool:
        """Check if user is sudo or owner"""
        if user_id in self.owner_ids:
            return True
        return user_id in self.users and self.users[user_id].role == UserRole.SUDO
    
    def update_user_activity(self, user_id: int, username: str = None, first_name: str = None):
        """Update user last activity"""
        if user_id not in self.users:
            self.add_user(user_id, username, first_name)
        else:
            self.users[user_id].last_active = datetime.now()
            if username:
                self.users[user_id].username = username
            if first_name:
                self.users[user_id].first_name = first_name
            self._save_users()
    
    def increment_reports(self, user_id: int):
        """Increment reports made by user"""
        if user_id in self.users:
            self.users[user_id].reports_made += 1
            self._save_users()
    
    def get_stats(self) -> Dict:
        """Get user statistics"""
        total = len(self.users)
        owners = sum(1 for u in self.users.values() if u.role == UserRole.OWNER)
        sudo_users = sum(1 for u in self.users.values() if u.role == UserRole.SUDO)
        regular_users = total - owners - sudo_users
        
        total_reports = sum(u.reports_made for u in self.users.values())
        
        return {
            "total_users": total,
            "owners": owners,
            "sudo_users": sudo_users,
            "regular_users": regular_users,
            "total_reports": total_reports
        }

# ===== ENHANCED REPORTING ENGINE WITH TG:// SUPPORT =====

class EnhancedReportingEngine:
    """Enhanced reporting engine with tg:// link support"""
    
    def __init__(self, account_manager, proxy_manager, user_manager):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.user_manager = user_manager
        self.delay_system = RandomDelaySystem()
        self.active_jobs: Dict[str, ReportJob] = {}
        self.job_history: List[ReportJob] = []
        
        self._load_history()
    
    def _parse_tg_link(self, link: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse tg:// link to extract user_id"""
        try:
            if link.startswith("tg://openmessage?user_id="):
                # Extract user_id from tg:// link
                parsed = urllib.parse.urlparse(link)
                params = urllib.parse.parse_qs(parsed.query)
                
                if 'user_id' in params:
                    user_id = params['user_id'][0]
                    return user_id, "user"
            
            elif link.startswith("tg://resolve?domain="):
                # Extract username from resolve link
                parsed = urllib.parse.urlparse(link)
                params = urllib.parse.parse_qs(parsed.query)
                
                if 'domain' in params:
                    username = params['domain'][0]
                    if username.startswith('+'):
                        # Invite link
                        return f"https://t.me/joinchat/{username[1:]}", "channel"
                    else:
                        return f"@{username}", "user"
            
            elif link.startswith("tg://join?invite="):
                # Group invite link
                parsed = urllib.parse.urlparse(link)
                params = urllib.parse.parse_qs(parsed.query)
                
                if 'invite' in params:
                    invite_hash = params['invite'][0]
                    return f"https://t.me/joinchat/{invite_hash}", "group"
        
        except Exception as e:
            console.print(f"[red]Error parsing tg:// link: {e}[/red]")
        
        return None, None
    
    async def _simulate_desktop_report_flow(self, client, target_entity, reason_text: str) -> float:
        """Simulate desktop client report flow with realistic delays"""
        total_delay = 0
        
        # Simulate opening profile/channel
        console.print("[dim]Opening target profile...[/dim]")
        open_delay = await self.delay_system.simulate_page_load()
        total_delay += open_delay
        
        # Simulate scrolling through content
        console.print("[dim]Reviewing content...[/dim]")
        scroll_delay = await self.delay_system.simulate_scrolling(random.randint(1, 3))
        total_delay += scroll_delay
        
        # Simulate finding report button
        console.print("[dim]Looking for report option...[/dim]")
        think_delay = await self.delay_system.simulate_thinking()
        total_delay += think_delay
        
        # Simulate clicking report button
        console.print("[dim]Clicking report...[/dim]")
        await asyncio.sleep(random.uniform(0.3, 0.8))
        total_delay += 0.5
        
        # Simulate loading report dialog
        console.print("[dim]Loading report dialog...[/dim]")
        dialog_delay = await self.delay_system.simulate_page_load()
        total_delay += dialog_delay
        
        # Simulate selecting reason
        console.print("[dim]Selecting report reason...[/dim]")
        await asyncio.sleep(random.uniform(0.5, 1.2))
        total_delay += 0.8
        
        # Simulate typing description (if provided)
        if reason_text:
            console.print("[dim]Typing description...[/dim]")
            type_delay = await self.delay_system.simulate_typing(reason_text[:200])
            total_delay += type_delay
        
        # Simulate final review before submitting
        console.print("[dim]Reviewing report...[/dim]")
        review_delay = random.uniform(1.0, 2.5)
        await asyncio.sleep(review_delay)
        total_delay += review_delay
        
        return total_delay
    
    async def _report_user_profile_desktop_style(self, client, user_entity, reason, description: str) -> bool:
        """Report user profile in desktop style"""
        try:
            # Get user full info
            full_user = await client(GetFullUserRequest(user_entity))
            
            # Simulate viewing profile
            console.print("[dim]Viewing user profile...[/dim]")
            await self.delay_system.simulate_page_load()
            
            # Check if user has profile photo
            if hasattr(full_user, 'profile_photo') and full_user.profile_photo:
                console.print("[dim]Viewing profile photo...[/dim]")
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Simulate right-click or menu open
                console.print("[dim]Opening profile options...[/dim]")
                await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Simulate report from profile
            console.print("[dim]Reporting from profile...[/dim]")
            
            # Desktop-style report with detailed description
            report_message = f"User Profile Report:\n\n{description}"
            
            # Add some realistic details
            if hasattr(user_entity, 'username') and user_entity.username:
                report_message += f"\n\nUsername: @{user_entity.username}"
            
            # Truncate if too long
            report_message = report_message[:500]
            
            return True
            
        except Exception as e:
            console.print(f"[yellow]Profile reporting simulation failed: {e}[/yellow]")
            return False
    
    async def create_report_from_tg_link(self, tg_link: str, category: str, subcategory: str, 
                                       description: str, user_id: int) -> Optional[str]:
        """Create report from tg:// link"""
        # Parse tg:// link
        target, target_type = self._parse_tg_link(tg_link)
        
        if not target:
            return None
        
        # Create job
        job_data = {
            "target": target,
            "target_type": target_type,
            "reason_category": category,
            "reason_subcategory": subcategory,
            "description": description,
            "accounts_needed": 3,
            "priority": "HIGH",
            "created_by": user_id,
            "random_delay_enabled": True,
            "delay_min": 3.0,
            "delay_max": 10.0
        }
        
        job_id = hashlib.md5(f"{datetime.now()}{random.random()}".encode()).hexdigest()[:12]
        
        job = ReportJob(
            target=job_data["target"],
            target_type=job_data["target_type"],
            reason_category=job_data["reason_category"],
            reason_subcategory=job_data["reason_subcategory"],
            description=job_data["description"],
            accounts_needed=job_data["accounts_needed"],
            priority=ReportPriority(job_data["priority"]),
            created_by=job_data["created_by"],
            random_delay_enabled=job_data["random_delay_enabled"],
            delay_min=job_data["delay_min"],
            delay_max=job_data["delay_max"]
        )
        
        self.active_jobs[job_id] = job
        return job_id
    
    async def execute_job_with_realistic_delays(self, job_id: str) -> Dict:
        """Execute job with realistic human delays"""
        if job_id not in self.active_jobs:
            return {"error": "Job not found"}
        
        job = self.active_jobs[job_id]
        job.status = ReportStatus.PROCESSING
        
        console.print(f"[cyan]Executing job {job_id} with realistic delays[/cyan]")
        
        # Get available accounts
        accounts = self.account_manager.get_available_accounts(job.accounts_needed)
        
        if len(accounts) < job.accounts_needed:
            job.status = ReportStatus.FAILED
            return {"error": f"Insufficient accounts. Need {job.accounts_needed}, have {len(accounts)}"}
        
        # Assign accounts
        job.assigned_accounts = [acc.phone for acc in accounts]
        
        # Execute with delays between accounts
        results = []
        for i, account in enumerate(accounts):
            console.print(f"[yellow]Account {i+1}/{len(accounts)}: {account.phone}[/yellow]")
            
            # Random delay between account reports (if enabled)
            if job.random_delay_enabled and i > 0:
                delay = random.uniform(job.delay_min, job.delay_max)
                console.print(f"[dim]Waiting {delay:.1f}s before next account...[/dim]")
                await asyncio.sleep(delay)
            
            # Execute single report with enhanced delays
            result = await self._execute_realistic_report(account, job)
            results.append(result)
            
            if result["status"] == "COMPLETED":
                job.completed_accounts.append(account.phone)
            
            # Update account
            account.report_count += 1
            account.total_reports += 1
            account.last_report_time = datetime.now()
            
            # Rotate proxy if reached limit
            if account.report_count >= self.account_manager.reports_per_account:
                new_proxy = await self.proxy_manager.rotate_proxy_for_account(account.phone)
                if new_proxy:
                    account.proxy = new_proxy
                    account.last_proxy_rotation = datetime.now()
                    account.report_count = 0  # Reset counter after proxy rotation
        
        job.results = results
        
        # Update job status
        completed = len(job.completed_accounts)
        if completed >= job.accounts_needed:
            job.status = ReportStatus.COMPLETED
        elif completed > 0:
            job.status = ReportStatus.PARTIAL
        else:
            job.status = ReportStatus.FAILED
        
        # Add to history
        self.job_history.append(job)
        self._save_history()
        
        # Update user stats
        if job.created_by:
            self.user_manager.increment_reports(job.created_by)
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "completed": len(job.completed_accounts),
            "total": job.accounts_needed,
            "results": results,
            "total_time": sum(r.get("total_delay", 0) for r in results if "total_delay" in r)
        }
    
    async def _execute_realistic_report(self, account: TelegramAccount, job: ReportJob) -> Dict:
        """Execute single report with enhanced realism"""
        start_time = time.time()
        
        try:
            # Initialize client if needed
            if not account.client or not account.client.is_connected():
                await self._initialize_realistic_client(account)
            
            if not account.client or not account.client.is_connected():
                return {
                    "account": account.phone,
                    "status": "FAILED",
                    "error": "Client not connected",
                    "time": 0
                }
            
            # Get target entity
            target_entity = await self._resolve_target_with_retry(account.client, job.target, job.target_type)
            if not target_entity:
                return {
                    "account": account.phone,
                    "status": "FAILED",
                    "error": "Could not resolve target",
                    "time": time.time() - start_time
                }
            
            # Prepare report reason
            reason_class = self._get_reason_class(job.reason_category)
            reason = reason_class()
            
            # Simulate desktop report flow
            console.print(f"[dim]Simulating desktop report flow for {account.phone}[/dim]")
            flow_delay = await self._simulate_desktop_report_flow(
                account.client, target_entity, job.description
            )
            
            # For users, simulate profile reporting
            if job.target_type == "user":
                await self._report_user_profile_desktop_style(
                    account.client, target_entity, reason, job.description
                )
            
            # Add thinking delay before final submission
            final_think = random.uniform(0.5, 1.5)
            await asyncio.sleep(final_think)
            flow_delay += final_think
            
            # Execute actual report
            report_request = ReportPeerRequest(
                peer=target_entity,
                reason=reason,
                message=job.description[:300] if job.description else ""
            )
            
            await account.client(report_request)
            
            # Simulate post-submission behavior
            console.print("[dim]Report submitted, waiting for confirmation...[/dim]")
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            # Mark proxy as successful
            if account.proxy:
                self.proxy_manager.mark_success(account.proxy, 1/flow_delay)
            
            total_time = time.time() - start_time
            
            return {
                "account": account.phone,
                "status": "COMPLETED",
                "time": total_time,
                "total_delay": flow_delay,
                "proxy": account.proxy,
                "country": account.country,
                "target": job.target,
                "simulation_time": flow_delay
            }
            
        except FloodWaitError as e:
            account.status = AccountStatus.FLOOD_WAIT
            return {
                "account": account.phone,
                "status": "FLOOD_WAIT",
                "error": f"Flood wait: {e.seconds}s",
                "time": time.time() - start_time
            }
        except Exception as e:
            if account.proxy:
                self.proxy_manager.mark_failed(account.proxy)
            
            return {
                "account": account.phone,
                "status": "FAILED",
                "error": str(e),
                "time": time.time() - start_time
            }
    
    async def _initialize_realistic_client(self, account: TelegramAccount) -> bool:
        """Initialize client with realistic settings"""
        try:
            # Random device configurations to mimic real users
            devices = [
                {"model": "Desktop", "sys_ver": "Windows 10", "app_ver": "4.0.0"},
                {"model": "Desktop", "sys_ver": "Windows 11", "app_ver": "4.1.0"},
                {"model": "Mac", "sys_ver": "macOS 14.0", "app_ver": "4.0.0"},
                {"model": "Linux", "sys_ver": "Ubuntu 22.04", "app_ver": "3.8.0"},
            ]
            
            device = random.choice(devices)
            
            client = TelegramClient(
                str(account.session_file),
                API_ID,
                API_HASH,
                device_model=device["model"],
                system_version=device["sys_ver"],
                app_version=device["app_ver"],
                lang_code="en",
                system_lang_code="en-US"
            )
            
            # Set proxy
            if account.proxy:
                client.set_proxy(account.proxy)
            
            await client.start()
            
            # Update client info to appear online
            await client(UpdateProfileRequest(
                first_name=None,
                last_name=None,
                about=None
            ))
            
            account.client = client
            account.status = AccountStatus.ACTIVE
            account.last_used = datetime.now()
            
            # Get account country info
            try:
                me = await client.get_me()
                if hasattr(me, 'phone'):
                    # Extract country code from phone
                    if me.phone.startswith('+'):
                        account.country = self._get_country_from_phone(me.phone)
                account.is_premium = getattr(me, 'premium', False)
            except:
                pass
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to initialize client for {account.phone}: {e}[/red]")
            account.status = AccountStatus.INACTIVE
            return False
    
    def _get_country_from_phone(self, phone: str) -> str:
        """Get country from phone number"""
        country_codes = {
            '+1': 'United States',
            '+44': 'United Kingdom',
            '+49': 'Germany',
            '+33': 'France',
            '+81': 'Japan',
            '+82': 'South Korea',
            '+65': 'Singapore',
            '+91': 'India',
            '+7': 'Russia',
            '+86': 'China',
            '+90': 'Turkey',
            '+55': 'Brazil',
            '+61': 'Australia',
            '+34': 'Spain',
            '+39': 'Italy',
        }
        
        for code, country in country_codes.items():
            if phone.startswith(code):
                return country
        
        return "Unknown"
    
    def _get_reason_class(self, category: str):
        """Get Telethon reason class from category"""
        mapping = {
            "ILLEGAL_DRUGS": InputReportReasonIllegalDrugs,
            "SPAM": InputReportReasonSpam,
            "VIOLENCE": InputReportReasonViolence,
            "SEXUAL": InputReportReasonPornography,
            "FRAUD": InputReportReasonFake,
            "HARASSMENT": InputReportReasonPersonalDetails,
            "COPYRIGHT": InputReportReasonCopyright,
            "OTHER": InputReportReasonOther
        }
        return mapping.get(category, InputReportReasonOther)
    
    async def _resolve_target_with_retry(self, client, target: str, target_type: str, max_retries: int = 3):
        """Resolve target with retry logic"""
        for attempt in range(max_retries):
            try:
                # Add small delay between retries
                if attempt > 0:
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                
                return await self._resolve_target(client, target, target_type)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                console.print(f"[yellow]Retry {attempt + 1} for {target}: {e}[/yellow]")
        
        return None
    
    async def _resolve_target(self, client, target: str, target_type: str):
        """Resolve target identifier"""
        try:
            target = target.strip()
            
            # Handle tg:// links
            if target.startswith("tg://"):
                parsed_target, parsed_type = self._parse_tg_link(target)
                if parsed_target:
                    target = parsed_target
                    target_type = parsed_type or target_type
            
            # Handle different formats
            if target.startswith("https://t.me/"):
                username = target.split("/")[-1]
                if username.startswith("+"):
                    return await client.get_entity(target)
                else:
                    return await client.get_entity(username)
            
            elif target.startswith("@"):
                return await client.get_entity(target[1:])
            
            elif target.isdigit():
                if target_type == "user":
                    return await client.get_entity(PeerUser(int(target)))
                elif target_type == "channel":
                    return await client.get_entity(PeerChannel(int(target)))
                else:
                    return await client.get_entity(int(target))
            
            else:
                return await client.get_entity(target)
                
        except Exception as e:
            console.print(f"[red]Failed to resolve target {target}: {e}[/red]")
            return None
    
    def _save_history(self):
        """Save job history"""
        history_file = DATA_DIR / "job_history.json"
        try:
            data = [job.to_dict() for job in self.job_history[-500:]]
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving history: {e}[/red]")
    
    def _load_history(self):
        """Load job history"""
        history_file = DATA_DIR / "job_history.json"
        try:
            if history_file.exists():
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    for job_data in data:
                        job = self._dict_to_job(job_data)
                        self.job_history.append(job)
        except Exception as e:
            console.print(f"[yellow]Error loading history: {e}[/yellow]")
    
    def _dict_to_job(self, data: Dict) -> ReportJob:
        """Convert dict to ReportJob"""
        job = ReportJob(
            target=data["target"],
            target_type=data["target_type"],
            reason_category=data["reason_category"],
            reason_subcategory=data["reason_subcategory"],
            description=data["description"],
            accounts_needed=data.get("accounts_needed", 1),
            priority=ReportPriority(data["priority"]),
            created_by=data.get("created_by"),
            created_at=datetime.fromisoformat(data["created_at"]),
            random_delay_enabled=data.get("random_delay_enabled", True),
            delay_min=data.get("delay_min", 2.0),
            delay_max=data.get("delay_max", 8.0)
        )
        
        if data.get("schedule_time"):
            job.schedule_time = datetime.fromisoformat(data["schedule_time"])
        
        job.status = ReportStatus(data["status"])
        job.assigned_accounts = data.get("assigned_accounts", [])
        job.completed_accounts = data.get("completed_accounts", [])
        job.results = data.get("results", [])
        
        return job

# ===== ENHANCED TELEGRAM BOT HANDLER =====

class EnhancedTelegramBotHandler:
    """Enhanced bot handler with owner/sudo system"""
    
    def __init__(self, user_manager: UserManager, account_manager, reporting_engine: EnhancedReportingEngine):
        self.user_manager = user_manager
        self.account_manager = account_manager
        self.reporting_engine = reporting_engine
        
        # Conversation states
        self.ADD_ACCOUNT, self.ADD_OTP, self.ADD_PASSWORD, \
        self.REPORT_TARGET, self.REPORT_TG_LINK, self.REPORT_CATEGORY, \
        self.REPORT_SUBCATEGORY, self.REPORT_DESCRIPTION = range(8)
        
        # Temporary storage
        self.user_sessions: Dict[int, Dict] = {}
        
        # Report categories (same as before, but included for completeness)
        self.report_categories = {
            "ILLEGAL_DRUGS": {
                "name": "Illegal Drugs & Substances",
                "priority": ReportPriority.CRITICAL,
                "subcategories": {
                    1: {"name": "Drug Trafficking", "description": "Selling or distributing illegal drugs"},
                    2: {"name": "Drug Promotion", "description": "Promoting drug use or sale"},
                    3: {"name": "Drug Manufacturing", "description": "Manufacturing of illegal substances"},
                    4: {"name": "Drug Recipes", "description": "Sharing instructions for drug production"},
                    5: {"name": "Prescription Drug Abuse", "description": "Abuse of prescription medications"},
                    6: {"name": "Drug Paraphernalia", "description": "Selling drug-related equipment"},
                    7: {"name": "Cannabis Products", "description": "Illegal cannabis distribution"},
                    8: {"name": "Synthetic Drugs", "description": "Synthetic drug distribution"},
                    9: {"name": "Darknet Market", "description": "Darknet drug market operations"}
                }
            },
            # ... other categories (same as before)
        }
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Update user activity
        self.user_manager.update_user_activity(
            user.id, 
            user.username, 
            user.first_name
        )
        
        role = self.user_manager.get_user_role(user.id)
        role_text = "👑 Owner" if self.user_manager.is_owner(user.id) else \
                   "⚡ Sudo" if self.user_manager.is_sudo(user.id) else "👤 User"
        
        welcome_text = f"""
🤖 *Telegram Enterprise Reporting System v6.0*

*Your Role:* {role_text}

*Features:*
• Multi-account reporting system
• Proxy rotation & management
• Human behavior simulation
• Support for tg:// links
• Realistic desktop emulation
• 9 reports per account limit

*Commands:*
/add - Add new account (Admin/Sudo)
/report - Start reporting
/tgreport - Report using tg:// link
/stats - View statistics
/accounts - List accounts
/jobs - View active jobs
/help - Show help

*Admin Commands:*
/addsudo [user_id] - Add sudo user (Owner only)
/listsudo - List sudo users
/removesudo [user_id] - Remove sudo user
/status - System status
"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def addsudo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addsudo command"""
        user = update.effective_user
        
        # Only owners can add sudo users
        if not self.user_manager.is_owner(user.id):
            await update.message.reply_text("❌ Only owners can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a user ID.\n"
                "Example: `/addsudo 123456789`",
                parse_mode='Markdown'
            )
            return
        
        try:
            sudo_id = int(context.args[0])
            
            # Check if user exists
            if sudo_id == user.id:
                await update.message.reply_text("❌ You cannot add yourself as sudo.")
                return
            
            # Promote to sudo
            success = self.user_manager.promote_to_sudo(sudo_id)
            
            if success:
                await update.message.reply_text(f"✅ User `{sudo_id}` promoted to SUDO.", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to promote user. User may not exist.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
    
    async def listsudo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /listsudo command"""
        user = update.effective_user
        
        if not self.user_manager.is_owner(user.id):
            await update.message.reply_text("❌ Only owners can use this command.")
            return
        
        sudo_users = []
        for user_obj in self.user_manager.users.values():
            if user_obj.role == UserRole.SUDO:
                sudo_users.append(user_obj)
        
        if not sudo_users:
            await update.message.reply_text("📭 No sudo users found.")
            return
        
        sudo_text = "⚡ *Sudo Users*\n\n"
        for i, sudo in enumerate(sudo_users, 1):
            sudo_text += (
                f"*{i}. ID:* `{sudo.user_id}`\n"
                f"   • Username: @{sudo.username if sudo.username else 'N/A'}\n"
                f"   • Name: {sudo.first_name if sudo.first_name else 'N/A'}\n"
                f"   • Added: {sudo.added_at.strftime('%Y-%m-%d')}\n"
                f"   • Reports: {sudo.reports_made}\n\n"
            )
        
        await update.message.reply_text(sudo_text, parse_mode='Markdown')
    
    async def removesudo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removesudo command"""
        user = update.effective_user
        
        if not self.user_manager.is_owner(user.id):
            await update.message.reply_text("❌ Only owners can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a user ID.\n"
                "Example: `/removesudo 123456789`",
                parse_mode='Markdown'
            )
            return
        
        try:
            sudo_id = int(context.args[0])
            
            if sudo_id == user.id:
                await update.message.reply_text("❌ You cannot remove yourself.")
                return
            
            # Demote from sudo
            success = self.user_manager.demote_from_sudo(sudo_id)
            
            if success:
                await update.message.reply_text(f"✅ User `{sudo_id}` demoted from SUDO.", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to demote user.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Must be a number.")
    
    async def tgreport_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tgreport command for tg:// links"""
        user = update.effective_user
        
        # Update activity
        self.user_manager.update_user_activity(user.id, user.username, user.first_name)
        
        # Start conversation
        self.user_sessions[user.id] = {"step": "tg_link"}
        
        await update.message.reply_text(
            "📝 *Report using tg:// link*\n\n"
            "Please send the tg:// link in one of these formats:\n"
            "• `tg://openmessage?user_id=123456789` (User)\n"
            "• `tg://resolve?domain=username` (User/Channel)\n"
            "• `tg://join?invite=abc123` (Group)\n\n"
            "_Note: This will open the profile and report from there._",
            parse_mode='Markdown'
        )
        
        return self.REPORT_TG_LINK
    
    async def handle_tg_link_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle tg:// link input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        tg_link = update.message.text.strip()
        
        # Validate tg:// link
        if not tg_link.startswith("tg://"):
            await update.message.reply_text(
                "❌ Invalid tg:// link. Please send a valid tg:// link."
            )
            return self.REPORT_TG_LINK
        
        self.user_sessions[user_id]["tg_link"] = tg_link
        
        # Parse to determine type
        target, target_type = self.reporting_engine._parse_tg_link(tg_link)
        
        if not target:
            await update.message.reply_text(
                "❌ Could not parse tg:// link. Please check the format."
            )
            return self.REPORT_TG_LINK
        
        self.user_sessions[user_id]["target"] = target
        self.user_sessions[user_id]["target_type"] = target_type or "user"
        
        # Create category keyboard
        keyboard = []
        row = []
        for cat_id, cat_info in self.report_categories.items():
            row.append(InlineKeyboardButton(cat_info["name"], callback_data=f"tgcat_{cat_id}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_tgreport")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Parsed tg:// link\n"
            f"• Type: {target_type or 'user'}\n"
            f"• Target: `{target[:50]}`\n\n"
            "Now select report category:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.REPORT_CATEGORY
    
    async def handle_tg_category_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection for tg report"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel_tgreport":
            await query.edit_message_text("❌ Report cancelled.")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        
        cat_id = query.data.replace("tgcat_", "")
        self.user_sessions[user_id]["category"] = cat_id
        
        cat_info = self.report_categories[cat_id]
        
        # Create subcategory keyboard
        keyboard = []
        for sub_id, sub_info in cat_info["subcategories"].items():
            keyboard.append([InlineKeyboardButton(
                f"{sub_id}. {sub_info['name']}",
                callback_data=f"tgsub_{sub_id}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_tgreport")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📑 *{cat_info['name']}*\n\n"
            "Select specific violation:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.REPORT_DESCRIPTION
    
    async def handle_tg_subcategory_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subcategory selection for tg report"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel_tgreport":
            await query.edit_message_text("❌ Report cancelled.")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return ConversationHandler.END
        
        sub_id = int(query.data.replace("tgsub_", ""))
        cat_id = self.user_sessions[user_id]["category"]
        
        cat_info = self.report_categories[cat_id]
        sub_info = cat_info["subcategories"][sub_id]
        
        self.user_sessions[user_id]["subcategory"] = sub_id
        self.user_sessions[user_id]["subcategory_name"] = sub_info["name"]
        
        await query.edit_message_text(
            f"📝 *Provide Detailed Description*\n\n"
            f"Link: `{self.user_sessions[user_id]['tg_link']}`\n"
            f"Category: {cat_info['name']}\n"
            f"Violation: {sub_info['name']}\n\n"
            "Please provide a detailed description of what you observed "
            "and why it violates Telegram's rules:\n\n"
            "_Example:_ 'This user is selling illegal drugs in their bio "
            "and contacting users with drug offers. I have screenshots "
            "of the conversations showing drug sales.'\n\n"
            "Your description (min 50 characters):",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    async def handle_tg_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle description for tg report"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return
        
        description = update.message.text.strip()
        
        if len(description) < 50:
            await update.message.reply_text(
                "❌ Description too short. Please provide at least 50 characters "
                "with detailed information."
            )
            return
        
        # Get all data from session
        tg_link = self.user_sessions[user_id]["tg_link"]
        category = self.user_sessions[user_id]["category"]
        subcategory_name = self.user_sessions[user_id]["subcategory_name"]
        
        # Create report job
        job_id = await self.reporting_engine.create_report_from_tg_link(
            tg_link, category, subcategory_name, description, user_id
        )
        
        if not job_id:
            await update.message.reply_text(
                "❌ Failed to create report job. Invalid tg:// link format."
            )
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return
        
        # Start execution
        asyncio.create_task(self._execute_tg_report_and_notify(job_id, user_id, tg_link))
        
        await update.message.reply_text(
            f"✅ *tg:// Report Job Created*\n\n"
            f"Job ID: `{job_id}`\n"
            f"Link: `{tg_link}`\n"
            f"Category: `{self.report_categories[category]['name']}`\n"
            f"Violation: `{subcategory_name}`\n\n"
            "⏳ *Simulating desktop reporting flow...*\n"
            "• Opening profile...\n"
            "• Reviewing content...\n"
            "• Filing report...\n\n"
            "_This will take some time with realistic delays._",
            parse_mode='Markdown'
        )
        
        # Cleanup
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def _execute_tg_report_and_notify(self, job_id: str, user_id: int, tg_link: str):
        """Execute tg report and notify user"""
        try:
            result = await self.reporting_engine.execute_job_with_realistic_delays(job_id)
            
            # Send notification
            from telegram.constants import ParseMode
            app = Application.builder().token(BOT_TOKEN).build()
            
            if result.get("status") == "COMPLETED":
                status_text = (
                    f"✅ *tg:// Report Completed*\n\n"
                    f"Link: `{tg_link}`\n"
                    f"Job ID: `{job_id}`\n"
                    f"Status: {result['status']}\n"
                    f"Accounts used: {result['completed']}/{result['total']}\n"
                    f"Total simulation time: {result.get('total_time', 0):.1f}s\n\n"
                    f"🎯 *Successfully reported from {result['completed']} accounts*"
                )
            else:
                status_text = (
                    f"⚠️ *tg:// Report Partial*\n\n"
                    f"Link: `{tg_link}`\n"
                    f"Job ID: `{job_id}`\n"
                    f"Status: {result.get('status', 'FAILED')}\n"
                    f"Accounts completed: {result.get('completed', 0)}/{result.get('total', 0)}\n"
                    f"Check /jobs for details"
                )
            
            await app.bot.send_message(
                chat_id=user_id,
                text=status_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            console.print(f"[red]Error in tg report execution: {e}[/red]")
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command - only for admin/sudo"""
        user = update.effective_user
        
        # Check permissions
        if not self.user_manager.is_sudo(user.id):
            await update.message.reply_text("❌ Permission denied. Admin/Sudo required.")
            return
        
        # Start conversation
        self.user_sessions[user.id] = {"step": "phone"}
        
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_add")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📱 *Add New Telegram Account*\n\n"
            "Please send the phone number in international format:\n"
            "Example: `+1234567890`\n\n"
            "_Note: You must have access to this phone to receive OTP._",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.ADD_ACCOUNT
    
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command"""
        user = update.effective_user
        
        # Update activity
        self.user_manager.update_user_activity(user.id, user.username, user.first_name)
        
        # Start conversation
        self.user_sessions[user.id] = {"step": "target"}
        
        keyboard = [
            [InlineKeyboardButton("👤 User", callback_data="target_user"),
             InlineKeyboardButton("📢 Channel", callback_data="target_channel")],
            [InlineKeyboardButton("👥 Group", callback_data="target_group"),
             InlineKeyboardButton("❌ Cancel", callback_data="cancel_report")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📝 *Start New Report*\n\n"
            "Select target type:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.REPORT_TARGET
    
    # ... (other handlers similar to previous version, but with permission checks)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = update.effective_user
        
        # Get all stats
        user_stats = self.user_manager.get_stats()
        account_stats = self.account_manager.get_stats()
        report_stats = self.reporting_engine.get_stats()
        proxy_stats = self.reporting_engine.proxy_manager.get_stats()
        
        role = self.user_manager.get_user_role(user.id)
        role_text = "👑 Owner" if self.user_manager.is_owner(user.id) else \
                   "⚡ Sudo" if self.user_manager.is_sudo(user.id) else "👤 User"
        
        stats_text = (
            f"📊 *System Statistics*\n\n"
            f"*Your Role:* {role_text}\n"
            f"*Your Reports:* {self.user_manager.users[user.id].reports_made if user.id in self.user_manager.users else 0}\n\n"
            
            f"*👥 Users:*\n"
            f"• Total: {user_stats['total_users']}\n"
            f"• Owners: {user_stats['owners']}\n"
            f"• Sudo: {user_stats['sudo_users']}\n"
            f"• Regular: {user_stats['regular_users']}\n"
            f"• Total Reports: {user_stats['total_reports']}\n\n"
            
            f"*📱 Accounts:*\n"
            f"• Total: {account_stats['total_accounts']}\n"
            f"• Active: {account_stats['active_accounts']}\n"
            f"• Reports Today: {account_stats['total_reports']}\n\n"
            
            f"*📊 Reporting:*\n"
            f"• Total Jobs: {report_stats['total_jobs']}\n"
            f"• Active Jobs: {len(self.reporting_engine.active_jobs)}\n"
            f"• Successful: {report_stats['completed_jobs']}\n\n"
            
            f"*🌐 Proxies:*\n"
            f"• Total: {proxy_stats['total']}\n"
            f"• Active: {proxy_stats['active']}\n"
            f"• Fast Countries: {len(proxy_stats.get('fast_countries', []))}"
        )
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')

# ===== MAIN APPLICATION =====

class EnhancedTelegramReportingBot:
    """Main enhanced application"""
    
    def __init__(self):
        self.user_manager = UserManager()
        self.proxy_manager = EnhancedProxyManager()
        self.account_manager = AccountManager(self.proxy_manager)  # You'll need to update AccountManager to work with EnhancedProxyManager
        self.reporting_engine = EnhancedReportingEngine(
            self.account_manager, 
            self.proxy_manager, 
            self.user_manager
        )
        self.bot_handler = EnhancedTelegramBotHandler(
            self.user_manager,
            self.account_manager,
            self.reporting_engine
        )
        
        # Bot application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup Telegram bot handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.bot_handler.start_command))
        self.application.add_handler(CommandHandler("stats", self.bot_handler.stats_command))
        self.application.add_handler(CommandHandler("addsudo", self.bot_handler.addsudo_command))
        self.application.add_handler(CommandHandler("listsudo", self.bot_handler.listsudo_command))
        self.application.add_handler(CommandHandler("removesudo", self.bot_handler.removesudo_command))
        
        # Conversation handlers (you'll need to implement these similar to previous version)
        # Add handlers for /add, /report, /tgreport, etc.
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        console.print(f"[red]Error: {context.error}[/red]")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again."
            )
    
    async def initialize(self):
        """Initialize the system"""
        console.print("[cyan]Initializing Enhanced Telegram Reporting System v6.0[/cyan]")
        
        # Print banner
        self._print_banner()
        
        # Load proxies
        await self.proxy_manager.load_proxies()
        
        console.print("[green]System initialized successfully[/green]")
    
    def _print_banner(self):
        """Print enhanced banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║     ENHANCED TELEGRAM REPORTING SYSTEM v6.0                 ║
║     Owner/Sudo System • tg:// Support • Realistic Delays    ║
╠══════════════════════════════════════════════════════════════╣
║ Owners: 6118760915, 1366105247                              ║
║ Features:                                                    ║
║ • Owner/Sudo user management                                ║
║ • tg://openmessage?user_id= link support                    ║
║ • Realistic desktop reporting simulation                    ║
║ • Intelligent proxy rotation (9 reports/account)            ║
║ • Random delays (2-8 seconds between reports)               ║
║ • Profile photo reporting                                   ║
╚══════════════════════════════════════════════════════════════╝
        """
        console.print(f"[bright_cyan]{banner}[/bright_cyan]")
    
    async def run(self):
        """Run the bot"""
        await self.initialize()
        
        console.print("[green]Starting enhanced bot...[/green]")
        
        # Start bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        console.print("[green]Bot is running. Press Ctrl+C to stop.[/green]")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the system"""
        console.print("[yellow]Shutting down enhanced system...[/yellow]")
        
        # Save data
        await self.proxy_manager.save_cache()
        self.user_manager._save_users()
        self.account_manager._save_accounts()
        self.reporting_engine._save_history()
        
        # Stop bot
        if self.application.updater:
            await self.application.updater.stop()
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        console.print("[green]System shutdown complete[/green]")

# ===== MAIN ENTRY POINT =====

async def main():
    """Main entry point"""
    bot = EnhancedTelegramReportingBot()
    
    try:
        await bot.run()
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
