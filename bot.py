#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM ENTERPRISE REPORTING SYSTEM v5.0
Advanced multi-account reporting bot with proxy rotation, human simulation
and comprehensive target analysis
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
    PhoneCodeExpiredError, AuthKeyDuplicatedError
)
from telethon.tl.functions.messages import ReportRequest, SendReactionRequest
from telethon.tl.functions.channels import JoinChannelRequest, GetParticipantsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.account import ReportPeerRequest, UpdateProfileRequest
from telethon.tl.types import (
    InputReportReasonSpam, InputReportReasonViolence, InputReportReasonPornography,
    InputReportReasonChildAbuse, InputReportReasonCopyright, InputReportReasonGeoIrrelevant,
    InputReportReasonFake, InputReportReasonIllegalDrugs, InputReportReasonPersonalDetails,
    InputReportReasonOther, PeerUser, PeerChannel, PeerChat,
    InputPeerUser, InputPeerChannel, InputPeerChat,
    User, Channel, Chat,
    ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRow,
    ReactionEmoji
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

console = Console()

# ===== CONFIGURATION =====
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
API_ID = 26676741
API_HASH = "6fbc29f23c15bdb0c7fbbefe65c9193a"

# Proxy configuration
PROXY_FILE = "data.txt"
PROXY_GITHUB_URLS = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt"
]

# Session and data directories
SESSION_DIR = Path("sessions")
DATA_DIR = Path("data")
LOGS_DIR = Path("logs")
EXPORTS_DIR = Path("exports")
PROXY_CACHE_FILE = Path("proxy_cache.json")

# Create directories
for dir_path in [SESSION_DIR, DATA_DIR, LOGS_DIR, EXPORTS_DIR]:
    dir_path.mkdir(exist_ok=True)

# ===== DATA MODELS =====

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
class TelegramAccount:
    """Telegram account with session management"""
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
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TelegramAccount':
        account = cls(
            phone=data["phone"],
            session_file=Path(data["session_file"]),
            proxy=data.get("proxy"),
            status=AccountStatus(data["status"]),
            report_count=data.get("report_count", 0),
            total_reports=data.get("total_reports", 0)
        )
        if data.get("created_at"):
            account.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_used"):
            account.last_used = datetime.fromisoformat(data["last_used"])
        account.tags = data.get("tags", [])
        return account

@dataclass
class ReportJob:
    """Reporting job with target and configuration"""
    target: str
    target_type: str  # "user", "channel", "group"
    reason_category: str
    reason_subcategory: str
    description: str
    accounts_needed: int = 1
    priority: ReportPriority = ReportPriority.MEDIUM
    schedule_time: Optional[datetime] = None
    created_by: int = None  # Telegram user ID
    created_at: datetime = field(default_factory=datetime.now)
    status: ReportStatus = ReportStatus.PENDING
    assigned_accounts: List[str] = field(default_factory=list)  # List of phone numbers
    completed_accounts: List[str] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)
    
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
            "results": self.results
        }

# ===== ENHANCED REPORTING CATEGORIES =====

REPORT_CATEGORIES = {
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
    "SPAM": {
        "name": "Spam & Scams",
        "priority": ReportPriority.MEDIUM,
        "subcategories": {
            1: {"name": "Financial Scams", "description": "Financial fraud or investment scams"},
            2: {"name": "Phishing Attempts", "description": "Attempts to steal credentials"},
            3: {"name": "Malware Distribution", "description": "Distributing malicious software"},
            4: {"name": "Bulk Spam Messages", "description": "Unsolicited bulk messaging"},
            5: {"name": "Fake Giveaways", "description": "Fake contests or giveaways"},
            6: {"name": "Pyramid Schemes", "description": "Pyramid or Ponzi schemes"},
            7: {"name": "Fake Jobs", "description": "Fake job offers or opportunities"},
            8: {"name": "Clickbait Links", "description": "Misleading clickbait content"}
        }
    },
    "VIOLENCE": {
        "name": "Violence & Harm",
        "priority": ReportPriority.HIGH,
        "subcategories": {
            1: {"name": "Physical Threats", "description": "Threats of physical violence"},
            2: {"name": "Terrorist Content", "description": "Terrorism-related material"},
            3: {"name": "Extremist Propaganda", "description": "Extremist recruitment"},
            4: {"name": "Weapons Trafficking", "description": "Illegal weapons trade"},
            5: {"name": "Animal Cruelty", "description": "Animal abuse or torture"},
            6: {"name": "Self-Harm Promotion", "description": "Promotion of self-harm"},
            7: {"name": "Hate Crimes", "description": "Hate-motivated violence"},
            8: {"name": "Gang Activity", "description": "Organized gang violence"}
        }
    },
    "SEXUAL": {
        "name": "Sexual Content",
        "priority": ReportPriority.HIGH,
        "subcategories": {
            1: {"name": "Child Exploitation", "description": "Child abuse material"},
            2: {"name": "Non-consensual Intimate", "description": "Non-consensual sharing"},
            3: {"name": "Sex Trafficking", "description": "Human trafficking for sex"},
            4: {"name": "Pornography Distribution", "description": "Adult content distribution"},
            5: {"name": "Sexual Harassment", "description": "Unwanted sexual advances"},
            6: {"name": "Revenge Porn", "description": "Non-consensual intimate media"},
            7: {"name": "Sexual Extortion", "description": "Sextortion attempts"}
        }
    },
    "FRAUD": {
        "name": "Fraud & Impersonation",
        "priority": ReportPriority.HIGH,
        "subcategories": {
            1: {"name": "Identity Theft", "description": "Stealing personal identity"},
            2: {"name": "Account Impersonation", "description": "Fake account impersonation"},
            3: {"name": "Fake Government", "description": "Government impersonation"},
            4: {"name": "Celebrity Impersonation", "description": "Fake celebrity account"},
            5: {"name": "Banking Fraud", "description": "Bank account fraud"},
            6: {"name": "Credit Card Scams", "description": "Credit card fraud"},
            7: {"name": "Fake Documents", "description": "Forged document sales"}
        }
    },
    "HARASSMENT": {
        "name": "Harassment & Bullying",
        "priority": ReportPriority.MEDIUM,
        "subcategories": {
            1: {"name": "Cyberbullying", "description": "Online bullying attacks"},
            2: {"name": "Stalking", "description": "Repeated unwanted contact"},
            3: {"name": "Doxxing", "description": "Sharing private information"},
            4: {"name": "Hate Speech", "description": "Discriminatory language"},
            5: {"name": "Threats", "description": "Threatening behavior"},
            6: {"name": "Workplace Harassment", "description": "Professional harassment"}
        }
    },
    "COPYRIGHT": {
        "name": "Copyright Violation",
        "priority": ReportPriority.MEDIUM,
        "subcategories": {
            1: {"name": "Movie Piracy", "description": "Illegal movie distribution"},
            2: {"name": "Music Piracy", "description": "Unauthorized music sharing"},
            3: {"name": "Software Piracy", "description": "Cracked software distribution"},
            4: {"name": "Book Piracy", "description": "Ebook piracy"},
            5: {"name": "TV Show Piracy", "description": "TV content piracy"},
            6: {"name": "Game Piracy", "description": "Video game piracy"}
        }
    },
    "OTHER": {
        "name": "Other Violations",
        "priority": ReportPriority.LOW,
        "subcategories": {
            1: {"name": "Platform Manipulation", "description": "Artificial boosting"},
            2: {"name": "False Information", "description": "Spreading misinformation"},
            3: {"name": "Geographic Irrelevance", "description": "Wrong region content"},
            4: {"name": "Unauthorized Sales", "description": "Prohibited item sales"},
            5: {"name": "Terms Violation", "description": "Other ToS violations"}
        }
    }
}

# Mapping to Telegram's report reasons
REASON_MAPPING = {
    "ILLEGAL_DRUGS": InputReportReasonIllegalDrugs,
    "SPAM": InputReportReasonSpam,
    "VIOLENCE": InputReportReasonViolence,
    "SEXUAL": InputReportReasonPornography,
    "FRAUD": InputReportReasonFake,
    "HARASSMENT": InputReportReasonPersonalDetails,
    "COPYRIGHT": InputReportReasonCopyright,
    "OTHER": InputReportReasonOther
}

# ===== PROXY MANAGEMENT SYSTEM =====

class ProxyManager:
    """Intelligent proxy management with rotation and validation"""
    
    def __init__(self):
        self.proxies: List[Dict] = []
        self.proxy_history: Dict[str, List] = defaultdict(list)
        self.country_stats: Dict[str, Dict] = defaultdict(lambda: {"success": 0, "fail": 0, "speed": []})
        self.banned_proxies: set = set()
        
    async def load_proxies(self):
        """Load proxies from multiple sources"""
        console.print("[cyan]Loading proxies from sources...[/cyan]")
        
        # Load from local file
        if Path(PROXY_FILE).exists():
            await self._load_from_file()
        
        # Load from GitHub sources
        await self._load_from_github()
        
        # Load from cache
        await self._load_from_cache()
        
        console.print(f"[green]Loaded {len(self.proxies)} proxies[/green]")
    
    async def _load_from_file(self):
        """Load proxies from local file"""
        try:
            with open(PROXY_FILE, 'r') as f:
                for line in f:
                    proxy = line.strip()
                    if proxy and self._validate_proxy_format(proxy):
                        self._add_proxy(proxy)
        except Exception as e:
            console.print(f"[red]Error loading proxy file: {e}[/red]")
    
    async def _load_from_github(self):
        """Fetch proxies from GitHub sources"""
        async with aiohttp.ClientSession() as session:
            for url in PROXY_GITHUB_URLS:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            text = await response.text()
                            for line in text.split('\n'):
                                proxy = line.strip()
                                if proxy and self._validate_proxy_format(proxy):
                                    self._add_proxy(proxy)
                except Exception as e:
                    console.print(f"[yellow]Failed to fetch from {url}: {e}[/yellow]")
    
    async def _load_from_cache(self):
        """Load proxies from cache"""
        try:
            if PROXY_CACHE_FILE.exists():
                with open(PROXY_CACHE_FILE, 'r') as f:
                    cache = json.load(f)
                    for proxy in cache.get("proxies", []):
                        self._add_proxy(proxy)
        except Exception as e:
            console.print(f"[yellow]Cache load error: {e}[/yellow]")
    
    def _validate_proxy_format(self, proxy: str) -> bool:
        """Validate proxy format"""
        patterns = [
            r'^https?://[\w\.\-]+:\d+$',
            r'^socks[45]://[\w\.\-]+:\d+$',
            r'^[\w\.\-]+:\d+$',
            r'^[\w\.\-]+:\d+:[\w\.\-]+:[\w\.\-]+$'  # with auth
        ]
        return any(re.match(pattern, proxy) for pattern in patterns)
    
    def _add_proxy(self, proxy: str):
        """Add proxy to list with metadata"""
        proxy_data = {
            "proxy": proxy,
            "last_used": None,
            "success_count": 0,
            "fail_count": 0,
            "avg_speed": 0,
            "country": self._detect_country(proxy),
            "type": self._detect_proxy_type(proxy),
            "banned": False
        }
        if proxy not in [p["proxy"] for p in self.proxies]:
            self.proxies.append(proxy_data)
    
    def _detect_country(self, proxy: str) -> str:
        """Detect proxy country from hostname"""
        # Simple detection based on common TLDs
        host = proxy.split('://')[-1].split(':')[0]
        
        country_map = {
            'us': 'United States',
            'uk': 'United Kingdom',
            'de': 'Germany',
            'fr': 'France',
            'nl': 'Netherlands',
            'sg': 'Singapore',
            'jp': 'Japan',
            'kr': 'South Korea',
            'ca': 'Canada',
            'au': 'Australia',
            'ru': 'Russia',
            'tr': 'Turkey',
            'in': 'India',
            'br': 'Brazil'
        }
        
        for tld, country in country_map.items():
            if host.endswith(f'.{tld}') or f'.{tld}.' in host:
                return country
        
        return "Unknown"
    
    def _detect_proxy_type(self, proxy: str) -> str:
        """Detect proxy type"""
        if proxy.startswith('http://'):
            return 'HTTP'
        elif proxy.startswith('https://'):
            return 'HTTPS'
        elif proxy.startswith('socks4://'):
            return 'SOCKS4'
        elif proxy.startswith('socks5://'):
            return 'SOCKS5'
        else:
            return 'HTTP'  # Default
    
    async def get_best_proxy(self, account_phone: str = None) -> Optional[str]:
        """Get the best available proxy"""
        if not self.proxies:
            return None
        
        # Filter available proxies
        available = [p for p in self.proxies if not p["banned"]]
        
        if not available:
            return None
        
        # Sort by success rate and speed
        available.sort(key=lambda x: (
            x["success_count"] - x["fail_count"],
            x["avg_speed"]
        ), reverse=True)
        
        best_proxy = available[0]
        best_proxy["last_used"] = datetime.now()
        
        # Update history
        if account_phone:
            self.proxy_history[account_phone].append({
                "proxy": best_proxy["proxy"],
                "time": datetime.now().isoformat()
            })
        
        return best_proxy["proxy"]
    
    def mark_success(self, proxy: str, speed: float):
        """Mark proxy as successful"""
        for p in self.proxies:
            if p["proxy"] == proxy:
                p["success_count"] += 1
                p["avg_speed"] = (p["avg_speed"] * (p["success_count"] - 1) + speed) / p["success_count"]
                break
    
    def mark_failed(self, proxy: str):
        """Mark proxy as failed"""
        for p in self.proxies:
            if p["proxy"] == proxy:
                p["fail_count"] += 1
                if p["fail_count"] > 3:
                    p["banned"] = True
                    self.banned_proxies.add(proxy)
                break
    
    def get_stats(self) -> Dict:
        """Get proxy statistics"""
        total = len(self.proxies)
        banned = len(self.banned_proxies)
        active = total - banned
        
        country_dist = defaultdict(int)
        type_dist = defaultdict(int)
        
        for proxy in self.proxies:
            if not proxy["banned"]:
                country_dist[proxy["country"]] += 1
                type_dist[proxy["type"]] += 1
        
        return {
            "total": total,
            "active": active,
            "banned": banned,
            "countries": dict(country_dist),
            "types": dict(type_dist)
        }
    
    async def save_cache(self):
        """Save proxies to cache"""
        try:
            cache_data = {
                "proxies": [p["proxy"] for p in self.proxies],
                "timestamp": datetime.now().isoformat()
            }
            with open(PROXY_CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Failed to save proxy cache: {e}[/red]")

# ===== ACCOUNT MANAGER =====

class AccountManager:
    """Manage multiple Telegram accounts"""
    
    def __init__(self, proxy_manager: ProxyManager):
        self.accounts: Dict[str, TelegramAccount] = {}
        self.proxy_manager = proxy_manager
        self.account_data_file = DATA_DIR / "accounts.json"
        self.reports_per_account = 9  # Max reports per account per cycle
        self.cooldown_hours = 24  # Cooldown period after max reports
        
        # Load existing accounts
        self._load_accounts()
    
    def _load_accounts(self):
        """Load accounts from file"""
        try:
            if self.account_data_file.exists():
                with open(self.account_data_file, 'r') as f:
                    data = json.load(f)
                    for phone, acc_data in data.items():
                        self.accounts[phone] = TelegramAccount.from_dict(acc_data)
                console.print(f"[green]Loaded {len(self.accounts)} accounts[/green]")
        except Exception as e:
            console.print(f"[red]Error loading accounts: {e}[/red]")
    
    def _save_accounts(self):
        """Save accounts to file"""
        try:
            data = {phone: acc.to_dict() for phone, acc in self.accounts.items()}
            with open(self.account_data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving accounts: {e}[/red]")
    
    async def add_account(self, phone: str, session_data: bytes = None) -> bool:
        """Add a new Telegram account"""
        if phone in self.accounts:
            console.print(f"[yellow]Account {phone} already exists[/yellow]")
            return False
        
        session_file = SESSION_DIR / f"{phone}.session"
        
        # Save session data if provided
        if session_data:
            try:
                with open(session_file, 'wb') as f:
                    f.write(session_data)
            except Exception as e:
                console.print(f"[red]Error saving session: {e}[/red]")
                return False
        
        # Get proxy for this account
        proxy = await self.proxy_manager.get_best_proxy(phone)
        
        # Create account object
        account = TelegramAccount(
            phone=phone,
            session_file=session_file,
            proxy=proxy,
            status=AccountStatus.INACTIVE
        )
        
        self.accounts[phone] = account
        self._save_accounts()
        
        console.print(f"[green]Account {phone} added successfully[/green]")
        return True
    
    def remove_account(self, phone: str) -> bool:
        """Remove an account"""
        if phone in self.accounts:
            # Delete session file
            try:
                self.accounts[phone].session_file.unlink(missing_ok=True)
            except:
                pass
            
            del self.accounts[phone]
            self._save_accounts()
            console.print(f"[green]Account {phone} removed[/green]")
            return True
        return False
    
    def get_account(self, phone: str) -> Optional[TelegramAccount]:
        """Get account by phone"""
        return self.accounts.get(phone)
    
    def get_available_accounts(self, count: int = 1) -> List[TelegramAccount]:
        """Get available accounts for reporting"""
        available = []
        
        for account in self.accounts.values():
            # Check if account can report
            if self._can_account_report(account):
                available.append(account)
            
            if len(available) >= count:
                break
        
        return available
    
    def _can_account_report(self, account: TelegramAccount) -> bool:
        """Check if account can make reports"""
        if account.status != AccountStatus.ACTIVE:
            return False
        
        if account.report_count >= self.reports_per_account:
            # Check if cooldown has passed
            if account.last_report_time:
                cooldown_end = account.last_report_time + timedelta(hours=self.cooldown_hours)
                if datetime.now() < cooldown_end:
                    return False
                else:
                    # Reset counter after cooldown
                    account.report_count = 0
        
        return True
    
    async def rotate_account_proxy(self, phone: str) -> bool:
        """Rotate proxy for an account"""
        account = self.get_account(phone)
        if not account:
            return False
        
        # Get new proxy
        new_proxy = await self.proxy_manager.get_best_proxy(phone)
        if not new_proxy:
            return False
        
        # Update account
        account.proxy = new_proxy
        account.report_count = 0  # Reset report counter
        
        # Disconnect and reconnect with new proxy
        if account.client and account.client.is_connected():
            await account.client.disconnect()
            account.client = None
        
        self._save_accounts()
        console.print(f"[green]Rotated proxy for {phone}[/green]")
        return True
    
    def get_stats(self) -> Dict:
        """Get account statistics"""
        total = len(self.accounts)
        active = sum(1 for a in self.accounts.values() if a.status == AccountStatus.ACTIVE)
        banned = sum(1 for a in self.accounts.values() if a.status == AccountStatus.BANNED)
        
        total_reports = sum(a.total_reports for a in self.accounts.values())
        
        return {
            "total_accounts": total,
            "active_accounts": active,
            "banned_accounts": banned,
            "total_reports": total_reports,
            "accounts": {phone: acc.to_dict() for phone, acc in self.accounts.items()}
        }

# ===== HUMAN BEHAVIOR SIMULATION =====

class HumanSimulator:
    """Simulate human-like behavior for reporting"""
    
    def __init__(self):
        self.behavior_patterns = {
            "typing_speed": {"min": 50, "max": 200},  # characters per minute
            "thinking_time": {"min": 1, "max": 5},  # seconds before action
            "random_actions": ["scroll", "pause", "recheck", "edit"]
        }
    
    async def simulate_typing(self, text: str):
        """Simulate typing with human-like delays"""
        words = text.split()
        total_chars = len(text)
        
        # Calculate typing time based on speed
        cpm = random.randint(
            self.behavior_patterns["typing_speed"]["min"],
            self.behavior_patterns["typing_speed"]["max"]
        )
        typing_time = (total_chars / cpm) * 60  # Convert to seconds
        
        # Add random pauses
        pause_count = random.randint(1, len(words) // 5)
        pause_positions = random.sample(range(len(words)), min(pause_count, len(words)))
        
        elapsed = 0
        for i, word in enumerate(words):
            # Type word
            word_time = len(word) / cpm
            await asyncio.sleep(word_time)
            elapsed += word_time
            
            # Add space
            await asyncio.sleep(0.05)
            
            # Random pause
            if i in pause_positions:
                pause_time = random.uniform(0.5, 2.0)
                await asyncio.sleep(pause_time)
                elapsed += pause_time
        
        return elapsed
    
    async def simulate_thinking(self):
        """Simulate thinking before action"""
        thinking_time = random.uniform(
            self.behavior_patterns["thinking_time"]["min"],
            self.behavior_patterns["thinking_time"]["max"]
        )
        await asyncio.sleep(thinking_time)
        return thinking_time
    
    async def simulate_report_flow(self, action_type: str):
        """Simulate complete report flow"""
        actions = []
        
        # Initial thinking
        think_time = await self.simulate_thinking()
        actions.append(("thinking", think_time))
        
        # Random actions
        if random.random() > 0.3:  # 70% chance of random action
            action = random.choice(self.behavior_patterns["random_actions"])
            if action == "scroll":
                scroll_time = random.uniform(0.5, 2.0)
                await asyncio.sleep(scroll_time)
                actions.append(("scroll", scroll_time))
            elif action == "pause":
                pause_time = random.uniform(1.0, 3.0)
                await asyncio.sleep(pause_time)
                actions.append(("pause", pause_time))
        
        return actions
    
    async def simulate_desktop_client(self):
        """Simulate desktop client behavior"""
        # Random mouse movement simulation
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Random tab switching simulation
        if random.random() > 0.7:
            await asyncio.sleep(random.uniform(0.3, 1.0))
        
        # Network delay simulation
        network_delay = random.expovariate(1.0) * 0.5  # Exponential distribution
        await asyncio.sleep(min(network_delay, 2.0))

# ===== ENHANCED REPORTING ENGINE =====

class ReportingEngine:
    """Enhanced reporting engine with human simulation"""
    
    def __init__(self, account_manager: AccountManager, proxy_manager: ProxyManager):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.human_simulator = HumanSimulator()
        self.active_jobs: Dict[str, ReportJob] = {}
        self.job_history: List[ReportJob] = []
        
        # Load job history
        self._load_history()
    
    def _load_history(self):
        """Load job history from file"""
        history_file = DATA_DIR / "job_history.json"
        try:
            if history_file.exists():
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    for job_data in data:
                        job = self._dict_to_job(job_data)
                        self.job_history.append(job)
        except Exception as e:
            console.print(f"[yellow]Error loading job history: {e}[/yellow]")
    
    def _save_history(self):
        """Save job history to file"""
        history_file = DATA_DIR / "job_history.json"
        try:
            data = [job.to_dict() for job in self.job_history[-1000:]]  # Keep last 1000 jobs
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving job history: {e}[/red]")
    
    def _dict_to_job(self, data: Dict) -> ReportJob:
        """Convert dictionary to ReportJob"""
        job = ReportJob(
            target=data["target"],
            target_type=data["target_type"],
            reason_category=data["reason_category"],
            reason_subcategory=data["reason_subcategory"],
            description=data["description"],
            accounts_needed=data.get("accounts_needed", 1),
            priority=ReportPriority(data["priority"]),
            created_by=data.get("created_by"),
            created_at=datetime.fromisoformat(data["created_at"])
        )
        
        if data.get("schedule_time"):
            job.schedule_time = datetime.fromisoformat(data["schedule_time"])
        
        job.status = ReportStatus(data["status"])
        job.assigned_accounts = data.get("assigned_accounts", [])
        job.completed_accounts = data.get("completed_accounts", [])
        job.results = data.get("results", [])
        
        return job
    
    async def create_report_job(self, job_data: Dict) -> str:
        """Create a new report job"""
        job_id = hashlib.md5(f"{datetime.now()}{random.random()}".encode()).hexdigest()[:12]
        
        job = ReportJob(
            target=job_data["target"],
            target_type=job_data["target_type"],
            reason_category=job_data["reason_category"],
            reason_subcategory=job_data["reason_subcategory"],
            description=job_data["description"],
            accounts_needed=job_data.get("accounts_needed", 1),
            priority=ReportPriority(job_data.get("priority", "MEDIUM")),
            created_by=job_data.get("created_by")
        )
        
        if "schedule_time" in job_data:
            job.schedule_time = datetime.fromisoformat(job_data["schedule_time"])
        
        self.active_jobs[job_id] = job
        return job_id
    
    async def execute_job(self, job_id: str) -> Dict:
        """Execute a report job"""
        if job_id not in self.active_jobs:
            return {"error": "Job not found"}
        
        job = self.active_jobs[job_id]
        job.status = ReportStatus.PROCESSING
        
        console.print(f"[cyan]Executing job {job_id}: {job.target}[/cyan]")
        
        # Get available accounts
        accounts = self.account_manager.get_available_accounts(job.accounts_needed)
        
        if len(accounts) < job.accounts_needed:
            job.status = ReportStatus.FAILED
            return {"error": f"Insufficient accounts. Need {job.accounts_needed}, have {len(accounts)}"}
        
        # Assign accounts to job
        job.assigned_accounts = [acc.phone for acc in accounts]
        
        # Execute reports
        results = []
        for account in accounts:
            result = await self._execute_single_report(account, job)
            results.append(result)
            
            if result["status"] == "COMPLETED":
                job.completed_accounts.append(account.phone)
            
            # Update account statistics
            account.report_count += 1
            account.total_reports += 1
            account.last_report_time = datetime.now()
        
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
        
        # Rotate proxies for used accounts
        for account in accounts:
            if account.report_count >= self.account_manager.reports_per_account:
                await self.account_manager.rotate_account_proxy(account.phone)
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "completed": len(job.completed_accounts),
            "total": job.accounts_needed,
            "results": results
        }
    
    async def _execute_single_report(self, account: TelegramAccount, job: ReportJob) -> Dict:
        """Execute a single report from an account"""
        start_time = time.time()
        
        try:
            # Initialize client if needed
            if not account.client or not account.client.is_connected():
                await self._initialize_account_client(account)
            
            if not account.client or not account.client.is_connected():
                return {
                    "account": account.phone,
                    "status": "FAILED",
                    "error": "Client not connected",
                    "time": 0
                }
            
            # Simulate human behavior before reporting
            await self.human_simulator.simulate_desktop_client()
            await self.human_simulator.simulate_report_flow("report")
            
            # Get target entity
            target_entity = await self._resolve_target(account.client, job.target, job.target_type)
            if not target_entity:
                return {
                    "account": account.phone,
                    "status": "FAILED",
                    "error": "Could not resolve target",
                    "time": time.time() - start_time
                }
            
            # Prepare report reason
            reason_class = REASON_MAPPING.get(job.reason_category, InputReportReasonOther)
            reason = reason_class()
            
            # Simulate typing description
            if job.description:
                typing_time = await self.human_simulator.simulate_typing(job.description)
                console.print(f"[dim]Typed description in {typing_time:.1f}s[/dim]")
            
            # Execute report with human-like delays
            await self.human_simulator.simulate_thinking()
            
            # For users, also report profile photo if available
            if job.target_type == "user":
                await self._report_user_profile(account.client, target_entity, reason, job.description)
            
            # Main report
            report_request = ReportPeerRequest(
                peer=target_entity,
                reason=reason,
                message=job.description[:200] if job.description else ""  # Limit message length
            )
            
            await account.client(report_request)
            
            # Simulate post-report behavior (like checking status)
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            execution_time = time.time() - start_time
            
            # Mark proxy as successful
            if account.proxy:
                self.proxy_manager.mark_success(account.proxy, 1/execution_time)  # Speed = 1/time
            
            return {
                "account": account.phone,
                "status": "COMPLETED",
                "time": execution_time,
                "proxy": account.proxy,
                "target": job.target
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
            # Mark proxy as failed
            if account.proxy:
                self.proxy_manager.mark_failed(account.proxy)
            
            return {
                "account": account.phone,
                "status": "FAILED",
                "error": str(e),
                "time": time.time() - start_time
            }
    
    async def _initialize_account_client(self, account: TelegramAccount) -> bool:
        """Initialize Telegram client for account"""
        try:
            # Client settings to mimic desktop
            client = TelegramClient(
                str(account.session_file),
                API_ID,
                API_HASH,
                device_model="Desktop",
                system_version="Windows 10",
                app_version="4.0",
                lang_code="en",
                system_lang_code="en-US"
            )
            
            # Set proxy if available
            if account.proxy:
                client.set_proxy(account.proxy)
            
            await client.start()
            
            # Update status to online
            await client(UpdateProfileRequest(
                first_name=None,
                last_name=None,
                about=None
            ))
            
            account.client = client
            account.status = AccountStatus.ACTIVE
            account.last_used = datetime.now()
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to initialize client for {account.phone}: {e}[/red]")
            account.status = AccountStatus.INACTIVE
            return False
    
    async def _resolve_target(self, client, target: str, target_type: str):
        """Resolve target to Telegram entity"""
        try:
            # Clean target string
            target = target.strip()
            
            # Handle different target formats
            if target.startswith("https://t.me/"):
                # Extract username from URL
                username = target.split("/")[-1]
                if username.startswith("+"):
                    # Invite link
                    return await client.get_entity(target)
                else:
                    # Direct link
                    return await client.get_entity(username)
            
            elif target.isdigit():
                # Numeric ID
                if target_type == "user":
                    return await client.get_entity(PeerUser(int(target)))
                elif target_type == "channel":
                    return await client.get_entity(PeerChannel(int(target)))
                else:
                    return await client.get_entity(int(target))
            
            else:
                # Assume username
                return await client.get_entity(target)
                
        except Exception as e:
            console.print(f"[red]Failed to resolve target {target}: {e}[/red]")
            return None
    
    async def _report_user_profile(self, client, user_entity, reason, description: str):
        """Report user profile photo"""
        try:
            # Get user full info
            full_user = await client(GetFullUserRequest(user_entity))
            
            if hasattr(full_user, 'profile_photo') and full_user.profile_photo:
                # Simulate viewing profile
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Report profile photo (this is a simplified version)
                # Note: Telegram API doesn't have direct profile photo reporting
                # We'll include it in the main report description
                pass
                
        except Exception as e:
            console.print(f"[yellow]Failed to report profile: {e}[/yellow]")
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status"""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            return {
                "job_id": job_id,
                "status": job.status.value,
                "target": job.target,
                "completed": len(job.completed_accounts),
                "total": job.accounts_needed,
                "created_at": job.created_at.isoformat()
            }
        return None
    
    def get_stats(self) -> Dict:
        """Get reporting statistics"""
        total_jobs = len(self.job_history)
        completed_jobs = sum(1 for j in self.job_history if j.status == ReportStatus.COMPLETED)
        failed_jobs = sum(1 for j in self.job_history if j.status == ReportStatus.FAILED)
        
        total_reports = sum(len(j.completed_accounts) for j in self.job_history)
        
        category_dist = defaultdict(int)
        for job in self.job_history:
            category_dist[job.reason_category] += 1
        
        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "total_reports": total_reports,
            "category_distribution": dict(category_dist),
            "active_jobs": len(self.active_jobs)
        }

# ===== TELEGRAM BOT HANDLER =====

class TelegramBotHandler:
    """Handle Telegram bot commands and interactions"""
    
    def __init__(self, account_manager: AccountManager, reporting_engine: ReportingEngine):
        self.account_manager = account_manager
        self.reporting_engine = reporting_engine
        
        # Conversation states
        self.ADD_ACCOUNT, self.ADD_OTP, self.REPORT_TARGET, self.REPORT_CATEGORY, \
        self.REPORT_SUBCATEGORY, self.REPORT_DESCRIPTION = range(6)
        
        # Temporary storage
        self.user_sessions: Dict[int, Dict] = {}
        
        # Admin and sudo users
        self.admin_users = []  # Will be loaded from config
        self.sudo_users = []
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        welcome_text = """
🤖 *Telegram Enterprise Reporting System v5.0*

*Features:*
• Multi-account reporting system
• Proxy rotation & management
• Human behavior simulation
• Advanced report categories
• Real-time monitoring

*Commands:*
/add - Add new account
/report - Start reporting
/stats - View statistics
/accounts - List accounts
/jobs - View active jobs
/help - Show help

*Admin Commands:*
/status - System status
/export - Export data
/config - Configuration
"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command"""
        user_id = update.effective_user.id
        
        # Check permissions
        if not await self._check_permissions(user_id):
            await update.message.reply_text("❌ Permission denied.")
            return
        
        # Start conversation
        self.user_sessions[user_id] = {"step": "phone"}
        
        keyboard = [[
            InlineKeyboardButton("Cancel", callback_data="cancel_add")
        ]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📱 *Add New Account*\n\n"
            "Please send the phone number in international format:\n"
            "Example: `+1234567890`",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.ADD_ACCOUNT
    
    async def add_account_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        phone = update.message.text.strip()
        
        # Validate phone number
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text("❌ Invalid phone number format. Please use international format: +1234567890")
            return self.ADD_ACCOUNT
        
        # Store phone
        self.user_sessions[user_id]["phone"] = phone
        
        # Initialize temporary client for authentication
        temp_session = SESSION_DIR / f"temp_{user_id}_{int(time.time())}.session"
        
        try:
            client = TelegramClient(
                str(temp_session),
                API_ID,
                API_HASH,
                device_model="iPhone",
                system_version="iOS 15.0",
                app_version="8.0"
            )
            
            await client.connect()
            
            # Send code
            sent = await client.send_code_request(phone)
            self.user_sessions[user_id]["phone_code_hash"] = sent.phone_code_hash
            self.user_sessions[user_id]["temp_client"] = client
            self.user_sessions[user_id]["temp_session"] = temp_session
            
            await update.message.reply_text(
                f"✅ Verification code sent to `{phone}`\n\n"
                "Please send the 5-digit code you received:",
                parse_mode='Markdown'
            )
            
            return self.ADD_OTP
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            return ConversationHandler.END
    
    async def add_account_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle OTP input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        otp = update.message.text.strip()
        
        if not otp.isdigit() or len(otp) != 5:
            await update.message.reply_text("❌ Invalid code. Please enter the 5-digit code.")
            return self.ADD_OTP
        
        phone = self.user_sessions[user_id]["phone"]
        phone_code_hash = self.user_sessions[user_id]["phone_code_hash"]
        client = self.user_sessions[user_id]["temp_client"]
        
        try:
            # Sign in with code
            await client.sign_in(
                phone=phone,
                code=otp,
                phone_code_hash=phone_code_hash
            )
            
            # Save session data
            session_data = None
            with open(client.session.filename, 'rb') as f:
                session_data = f.read()
            
            # Add account to manager
            success = await self.account_manager.add_account(phone, session_data)
            
            if success:
                await update.message.reply_text(
                    f"✅ Account `{phone}` added successfully!\n\n"
                    f"• Status: Active\n"
                    f"• Proxy: Assigned\n"
                    f"• Reports remaining: 9",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Failed to add account.")
            
        except SessionPasswordNeededError:
            await update.message.reply_text(
                "🔒 2FA is enabled for this account.\n"
                "Please send your password:"
            )
            self.user_sessions[user_id]["step"] = "password"
            return self.ADD_OTP
            
        except PhoneCodeInvalidError:
            await update.message.reply_text("❌ Invalid code. Please try again.")
            return self.ADD_OTP
            
        except PhoneCodeExpiredError:
            await update.message.reply_text("❌ Code expired. Please start over.")
            return ConversationHandler.END
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            
        finally:
            # Cleanup
            if "temp_client" in self.user_sessions[user_id]:
                await self.user_sessions[user_id]["temp_client"].disconnect()
            if "temp_session" in self.user_sessions[user_id]:
                try:
                    self.user_sessions[user_id]["temp_session"].unlink()
                except:
                    pass
            
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
        
        return ConversationHandler.END
    
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command"""
        user_id = update.effective_user.id
        
        # Start report conversation
        self.user_sessions[user_id] = {"step": "target"}
        
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
    
    async def handle_target_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle target type selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel_report":
            await query.edit_message_text("❌ Report cancelled.")
            del self.user_sessions[user_id]
            return ConversationHandler.END
        
        target_type = query.data.replace("target_", "")
        self.user_sessions[user_id]["target_type"] = target_type
        
        await query.edit_message_text(
            f"📌 *{target_type.capitalize()} Report*\n\n"
            "Please send the target:\n"
            "• Username (e.g., `@username`)\n"
            "• Profile link (e.g., `https://t.me/username`)\n"
            "• User ID (for users only)",
            parse_mode='Markdown'
        )
        
        return self.REPORT_CATEGORY
    
    async def handle_target_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle target input"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return ConversationHandler.END
        
        target = update.message.text.strip()
        self.user_sessions[user_id]["target"] = target
        
        # Create category keyboard
        keyboard = []
        row = []
        for i, (cat_id, cat_info) in enumerate(REPORT_CATEGORIES.items()):
            row.append(InlineKeyboardButton(cat_info["name"], callback_data=f"cat_{cat_id}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_report")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📋 *Select Report Category*\n\n"
            "Choose the main category:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.REPORT_SUBCATEGORY
    
    async def handle_category_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel_report":
            await query.edit_message_text("❌ Report cancelled.")
            del self.user_sessions[user_id]
            return ConversationHandler.END
        
        cat_id = query.data.replace("cat_", "")
        self.user_sessions[user_id]["category"] = cat_id
        
        cat_info = REPORT_CATEGORIES[cat_id]
        
        # Create subcategory keyboard
        keyboard = []
        for sub_id, sub_info in cat_info["subcategories"].items():
            keyboard.append([InlineKeyboardButton(
                f"{sub_id}. {sub_info['name']}",
                callback_data=f"sub_{sub_id}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_report")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📑 *{cat_info['name']}*\n\n"
            "Select specific violation:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.REPORT_DESCRIPTION
    
    async def handle_subcategory_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subcategory selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "cancel_report":
            await query.edit_message_text("❌ Report cancelled.")
            del self.user_sessions[user_id]
            return ConversationHandler.END
        
        sub_id = int(query.data.replace("sub_", ""))
        cat_id = self.user_sessions[user_id]["category"]
        
        cat_info = REPORT_CATEGORIES[cat_id]
        sub_info = cat_info["subcategories"][sub_id]
        
        self.user_sessions[user_id]["subcategory"] = sub_id
        self.user_sessions[user_id]["subcategory_name"] = sub_info["name"]
        
        await query.edit_message_text(
            f"📝 *Provide Details*\n\n"
            f"Category: {cat_info['name']}\n"
            f"Violation: {sub_info['name']}\n"
            f"Description: {sub_info['description']}\n\n"
            "Please provide detailed description of the violation "
            "(what you observed, why it violates rules, etc.):\n\n"
            "_This description will be sent to Telegram moderators._",
            parse_mode='Markdown'
        )
        
        # Next step will be handled by handle_description
        return ConversationHandler.END
    
    async def handle_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle description input and create report job"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_sessions:
            return
        
        description = update.message.text.strip()
        
        if len(description) < 10:
            await update.message.reply_text("❌ Description too short. Please provide more details.")
            return
        
        # Create job data
        job_data = {
            "target": self.user_sessions[user_id]["target"],
            "target_type": self.user_sessions[user_id]["target_type"],
            "reason_category": self.user_sessions[user_id]["category"],
            "reason_subcategory": self.user_sessions[user_id]["subcategory_name"],
            "description": description,
            "accounts_needed": 3,  # Default: use 3 accounts
            "priority": "MEDIUM",
            "created_by": user_id
        }
        
        # Create job
        job_id = await self.reporting_engine.create_report_job(job_data)
        
        # Start execution (async)
        asyncio.create_task(self._execute_and_notify(job_id, user_id))
        
        await update.message.reply_text(
            f"✅ *Report Job Created*\n\n"
            f"Job ID: `{job_id}`\n"
            f"Target: `{job_data['target']}`\n"
            f"Category: `{REPORT_CATEGORIES[job_data['reason_category']]['name']}`\n"
            f"Violation: `{job_data['reason_subcategory']}`\n"
            f"Accounts: {job_data['accounts_needed']}\n\n"
            f"⏳ Processing with human simulation...",
            parse_mode='Markdown'
        )
        
        # Cleanup
        del self.user_sessions[user_id]
    
    async def _execute_and_notify(self, job_id: str, user_id: int):
        """Execute job and notify user"""
        try:
            result = await self.reporting_engine.execute_job(job_id)
            
            # Send notification
            from telegram.constants import ParseMode
            app = Application.builder().token(BOT_TOKEN).build()
            
            status_text = (
                f"📊 *Report Completed*\n\n"
                f"Job ID: `{job_id}`\n"
                f"Status: {result['status']}\n"
                f"Completed: {result['completed']}/{result['total']}\n"
                f"Success Rate: {result['completed']/result['total']*100:.1f}%\n"
            )
            
            await app.bot.send_message(
                chat_id=user_id,
                text=status_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            console.print(f"[red]Error in job execution: {e}[/red]")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        account_stats = self.account_manager.get_stats()
        report_stats = self.reporting_engine.get_stats()
        proxy_stats = self.reporting_engine.proxy_manager.get_stats()
        
        stats_text = (
            f"📈 *System Statistics*\n\n"
            f"*Accounts:*\n"
            f"• Total: {account_stats['total_accounts']}\n"
            f"• Active: {account_stats['active_accounts']}\n"
            f"• Banned: {account_stats['banned_accounts']}\n"
            f"• Total Reports: {account_stats['total_reports']}\n\n"
            
            f"*Reporting:*\n"
            f"• Total Jobs: {report_stats['total_jobs']}\n"
            f"• Completed: {report_stats['completed_jobs']}\n"
            f"• Active Jobs: {report_stats['active_jobs']}\n"
            f"• Total Reports: {report_stats['total_reports']}\n\n"
            
            f"*Proxies:*\n"
            f"• Total: {proxy_stats['total']}\n"
            f"• Active: {proxy_stats['active']}\n"
            f"• Banned: {proxy_stats['banned']}\n"
        )
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /accounts command"""
        accounts = self.account_manager.accounts.values()
        
        if not accounts:
            await update.message.reply_text("No accounts added yet.")
            return
        
        accounts_text = "📱 *Accounts List*\n\n"
        
        for i, acc in enumerate(list(accounts)[:10], 1):  # Show first 10
            accounts_text += (
                f"*{i}. {acc.phone}*\n"
                f"• Status: {acc.status.value}\n"
                f"• Reports: {acc.report_count}/9\n"
                f"• Total: {acc.total_reports}\n"
                f"• Proxy: {acc.proxy[:30] if acc.proxy else 'None'}\n\n"
            )
        
        if len(accounts) > 10:
            accounts_text += f"... and {len(accounts) - 10} more accounts"
        
        await update.message.reply_text(accounts_text, parse_mode='Markdown')
    
    async def jobs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /jobs command"""
        active_jobs = self.reporting_engine.active_jobs
        
        if not active_jobs:
            await update.message.reply_text("No active jobs.")
            return
        
        jobs_text = "📋 *Active Jobs*\n\n"
        
        for job_id, job in list(active_jobs.items())[:5]:  # Show first 5
            jobs_text += (
                f"*{job_id}*\n"
                f"• Target: {job.target[:30]}\n"
                f"• Type: {job.target_type}\n"
                f"• Status: {job.status.value}\n"
                f"• Progress: {len(job.completed_accounts)}/{job.accounts_needed}\n"
                f"• Created: {job.created_at.strftime('%H:%M')}\n\n"
            )
        
        if len(active_jobs) > 5:
            jobs_text += f"... and {len(active_jobs) - 5} more jobs"
        
        await update.message.reply_text(jobs_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🆘 *Help Guide*

*Basic Commands:*
/start - Start the bot
/add - Add new Telegram account
/report - Start reporting process
/stats - View system statistics
/accounts - List all accounts
/jobs - View active jobs
/help - Show this help

*Reporting Process:*
1. Use /report to start
2. Select target type (User/Channel/Group)
3. Enter target (username or link)
4. Choose category and subcategory
5. Provide detailed description
6. System executes with human simulation

*Account Management:*
• Each account can report 9 times
• Proxies rotate automatically
• Human behavior simulation
• Real desktop client emulation

*Note:* This system is for legitimate reporting only.
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _check_permissions(self, user_id: int) -> bool:
        """Check if user has permission"""
        # Add your admin/sudo user IDs here
        admin_ids = [123456789]  # Replace with actual admin ID
        sudo_ids = [987654321]   # Replace with actual sudo IDs
        
        return user_id in admin_ids + sudo_ids
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation"""
        user_id = update.effective_user.id
        
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        
        await update.message.reply_text("Operation cancelled.")
        return ConversationHandler.END

# ===== MAIN APPLICATION =====

class TelegramReportingBot:
    """Main application class"""
    
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.account_manager = AccountManager(self.proxy_manager)
        self.reporting_engine = ReportingEngine(self.account_manager, self.proxy_manager)
        self.bot_handler = TelegramBotHandler(self.account_manager, self.reporting_engine)
        
        # Bot application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup Telegram bot handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.bot_handler.start_command))
        self.application.add_handler(CommandHandler("stats", self.bot_handler.stats_command))
        self.application.add_handler(CommandHandler("accounts", self.bot_handler.accounts_command))
        self.application.add_handler(CommandHandler("jobs", self.bot_handler.jobs_command))
        self.application.add_handler(CommandHandler("help", self.bot_handler.help_command))
        
        # Conversation handler for adding accounts
        add_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("add", self.bot_handler.add_command)],
            states={
                self.bot_handler.ADD_ACCOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.add_account_phone)
                ],
                self.bot_handler.ADD_OTP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.add_account_otp)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.cancel)]
        )
        self.application.add_handler(add_conv_handler)
        
        # Conversation handler for reporting
        report_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("report", self.bot_handler.report_command)],
            states={
                self.bot_handler.REPORT_TARGET: [
                    CallbackQueryHandler(self.bot_handler.handle_target_type)
                ],
                self.bot_handler.REPORT_CATEGORY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_target_input)
                ],
                self.bot_handler.REPORT_SUBCATEGORY: [
                    CallbackQueryHandler(self.bot_handler.handle_category_selection)
                ],
                self.bot_handler.REPORT_DESCRIPTION: [
                    CallbackQueryHandler(self.bot_handler.handle_subcategory_selection)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.cancel)]
        )
        self.application.add_handler(report_conv_handler)
        
        # Handle description (end of conversation)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handler.handle_description)
        )
    
    async def initialize(self):
        """Initialize the system"""
        console.print("[cyan]Initializing Telegram Reporting System v5.0[/cyan]")
        
        # Load proxies
        await self.proxy_manager.load_proxies()
        
        # Print banner
        self._print_banner()
        
        console.print("[green]System initialized successfully[/green]")
    
    def _print_banner(self):
        """Print system banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║      TELEGRAM ENTERPRISE REPORTING SYSTEM v5.0              ║
║      Advanced Multi-Account Bot with Human Simulation       ║
╠══════════════════════════════════════════════════════════════╣
║ Features:                                                    ║
║ • Multi-account management                                   ║
║ • Intelligent proxy rotation                                 ║
║ • Human behavior simulation                                  ║
║ • Advanced reporting categories                              ║
║ • Real desktop client emulation                              ║
║ • 9 reports per account limit                                ║
╚══════════════════════════════════════════════════════════════╝
        """
        console.print(f"[bright_cyan]{banner}[/bright_cyan]")
        
        # System info
        account_stats = self.account_manager.get_stats()
        proxy_stats = self.proxy_manager.get_stats()
        
        info_panel = Panel(
            f"[bright_white]Accounts:[/bright_white] [green]{account_stats['total_accounts']}[/green] "
            f"[bright_white]Active:[/bright_white] [cyan]{account_stats['active_accounts']}[/cyan]\n"
            f"[bright_white]Proxies:[/bright_white] [green]{proxy_stats['total']}[/green] "
            f"[bright_white]Active:[/bright_white] [cyan]{proxy_stats['active']}[/cyan]\n"
            f"[bright_white]Reports Today:[/bright_white] [yellow]{account_stats['total_reports']}[/yellow]",
            title="System Status",
            border_style="bright_blue"
        )
        
        console.print(info_panel)
    
    async def run(self):
        """Run the bot"""
        await self.initialize()
        
        console.print("[green]Starting bot...[/green]")
        
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
        console.print("[yellow]Shutting down system...[/yellow]")
        
        # Save proxy cache
        await self.proxy_manager.save_cache()
        
        # Save account data
        self.account_manager._save_accounts()
        
        # Save job history
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
    bot = TelegramReportingBot()
    
    try:
        await bot.run()
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

