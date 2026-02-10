#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTIMATE TELEGRAM ENTERPRISE REPORTING SYSTEM v12.0
Optimized Professional Solution with Advanced Features
"""

# ============================================
# STANDARD LIBRARY IMPORTS
# ============================================
import asyncio
import csv
import hashlib
import io
import json
import logging
import random
import re
import string
import sys
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# ============================================
# THIRD-PARTY NETWORKING IMPORTS
# ============================================
import aiohttp
import certifi
import requests
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================
# TELEGRAM BOT API (python-telegram-bot v20+)
# ============================================
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

# ============================================
# TELETHON (Telegram Client)
# ============================================
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    PhoneNumberBannedError,
    SessionPasswordNeededError,
    AuthKeyDuplicatedError,
)
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.functions.auth import SendCodeRequest, SignInRequest
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import (
    InputPeerUser,
    InputPeerChannel,
    InputPeerChat,
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonChildAbuse,
    InputReportReasonCopyright,
    InputReportReasonGeoIrrelevant,
    InputReportReasonFake,
    InputReportReasonIllegalDrugs,
    InputReportReasonPersonalDetails,
    InputReportReasonOther,
)

# ============================================
# RICH CONSOLE OUTPUT
# ============================================
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.traceback import install as install_rich_traceback

# Install rich traceback for better error display
install_rich_traceback()
console = Console()

# ============================================
# CONFIGURATION
# ============================================

# Bot Configuration (REPLACE WITH YOUR VALUES)
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
API_ID = 27157163
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"

# Owner IDs
OWNER_IDS = [6118760915, 1366105247]
ADMIN_IDS = []

# File paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SESSION_DIR = BASE_DIR / "sessions"
BACKUP_DIR = BASE_DIR / "backups"

# Create directories
for directory in [DATA_DIR, SESSION_DIR, BACKUP_DIR]:
    directory.mkdir(exist_ok=True)

# Data files
USERS_FILE = DATA_DIR / "users.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
PROXY_FILE = DATA_DIR / "proxies.txt"
PROXY_CACHE_FILE = DATA_DIR / "proxy_cache.json"
JOBS_FILE = DATA_DIR / "jobs.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# ============================================
# ENUMERATIONS
# ============================================

class UserRole(IntEnum):
    """User role hierarchy"""
    BANNED = 0
    VIEWER = 1
    USER = 2
    REPORTER = 3
    MODERATOR = 4
    ADMIN = 5
    OWNER = 6

class AccountStatus(IntEnum):
    """Account status tracking"""
    UNVERIFIED = 0
    VERIFYING = 1
    ACTIVE = 2
    INACTIVE = 3
    BANNED = 4
    FLOOD_WAIT = 5
    NEED_PASSWORD = 6
    PROXY_FAILED = 7

class ReportStatus(IntEnum):
    """Report job status"""
    PENDING = 0
    PROCESSING = 1
    COMPLETED = 2
    FAILED = 3
    CANCELLED = 4

class ProxyType(IntEnum):
    """Proxy protocol types"""
    HTTP = 0
    HTTPS = 1
    SOCKS4 = 2
    SOCKS5 = 3

# ============================================
# DATA MODELS
# ============================================

@dataclass
class TelegramUser:
    """User model with permissions"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER
    added_at: datetime = None
    reports_made: int = 0
    last_active: Optional[datetime] = None
    
    def __post_init__(self):
        if self.added_at is None:
            self.added_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role.value,
            "added_at": self.added_at.isoformat(),
            "reports_made": self.reports_made,
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TelegramUser':
        user = cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            role=UserRole(data.get("role", 2)),
            reports_made=data.get("reports_made", 0),
        )
        user.added_at = datetime.fromisoformat(data["added_at"])
        if data.get("last_active"):
            user.last_active = datetime.fromisoformat(data["last_active"])
        return user

@dataclass
class ProxyEntry:
    """Proxy entry with performance tracking"""
    proxy: str
    proxy_type: ProxyType = ProxyType.HTTP
    country: str = "Unknown"
    is_active: bool = True
    success_count: int = 0
    fail_count: int = 0
    avg_response_time: float = 0.0
    last_used: Optional[datetime] = None
    reports_used: int = 0
    verified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "proxy": self.proxy,
            "proxy_type": self.proxy_type.value,
            "country": self.country,
            "is_active": self.is_active,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "avg_response_time": self.avg_response_time,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "reports_used": self.reports_used,
            "verified": self.verified,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProxyEntry':
        entry = cls(
            proxy=data["proxy"],
            country=data.get("country", "Unknown"),
            is_active=data.get("is_active", True),
            success_count=data.get("success_count", 0),
            fail_count=data.get("fail_count", 0),
            avg_response_time=data.get("avg_response_time", 0.0),
            reports_used=data.get("reports_used", 0),
            verified=data.get("verified", False),
        )
        entry.proxy_type = ProxyType(data.get("proxy_type", 0))
        if data.get("last_used"):
            entry.last_used = datetime.fromisoformat(data["last_used"])
        return entry

@dataclass
class TelegramAccount:
    """Telegram account model"""
    phone: str
    session_file: Path
    proxy: Optional[str] = None
    status: AccountStatus = AccountStatus.UNVERIFIED
    report_count: int = 0
    total_reports: int = 0
    last_report_time: Optional[datetime] = None
    created_at: datetime = None
    last_used: Optional[datetime] = None
    client: Optional[TelegramClient] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phone": self.phone,
            "session_file": str(self.session_file),
            "proxy": self.proxy,
            "status": self.status.value,
            "report_count": self.report_count,
            "total_reports": self.total_reports,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "last_report_time": self.last_report_time.isoformat() if self.last_report_time else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TelegramAccount':
        account = cls(
            phone=data["phone"],
            session_file=Path(data["session_file"]),
            proxy=data.get("proxy"),
            status=AccountStatus(data["status"]),
            report_count=data.get("report_count", 0),
            total_reports=data.get("total_reports", 0),
        )
        account.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_used"):
            account.last_used = datetime.fromisoformat(data["last_used"])
        if data.get("last_report_time"):
            account.last_report_time = datetime.fromisoformat(data["last_report_time"])
        return account

@dataclass
class ReportJob:
    """Report job model"""
    job_id: str
    target: str
    target_type: str
    category: str
    description: str
    created_by: int
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: ReportStatus = ReportStatus.PENDING
    accounts_used: List[str] = None
    results: List[Dict] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.accounts_used is None:
            self.accounts_used = []
        if self.results is None:
            self.results = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "target": self.target,
            "target_type": self.target_type,
            "category": self.category,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "accounts_used": self.accounts_used,
            "results": self.results,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportJob':
        job = cls(
            job_id=data["job_id"],
            target=data["target"],
            target_type=data["target_type"],
            category=data["category"],
            description=data["description"],
            created_by=data["created_by"],
        )
        job.created_at = datetime.fromisoformat(data["created_at"])
        job.status = ReportStatus(data["status"])
        if data.get("started_at"):
            job.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            job.completed_at = datetime.fromisoformat(data["completed_at"])
        job.accounts_used = data.get("accounts_used", [])
        job.results = data.get("results", [])
        return job

# ============================================
# CORE MANAGERS
# ============================================

class UserManager:
    """Manages bot users and permissions"""
    
    def __init__(self):
        self.users: Dict[int, TelegramUser] = {}
        self._load_users()
    
    def _load_users(self):
        """Load users from JSON file"""
        try:
            if USERS_FILE.exists():
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for user_id_str, user_data in data.items():
                    try:
                        user = TelegramUser.from_dict(user_data)
                        self.users[user.user_id] = user
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Skipping invalid user data: {e}[/yellow]")
                        continue
                
                console.print(f"[green]✅ Loaded {len(self.users)} users[/green]")
        except Exception as e:
            console.print(f"[red]❌ Error loading users: {e}[/red]")
    
    def _save_users(self):
        """Save users to JSON file"""
        try:
            data = {str(uid): user.to_dict() for uid, user in self.users.items()}
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red]❌ Error saving users: {e}[/red]")
    
    def get_or_create_user(self, user_id: int, username: str = None,
                          first_name: str = None, last_name: str = None) -> TelegramUser:
        """Get existing user or create new one"""
        if user_id not in self.users:
            user = TelegramUser(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.OWNER if user_id in OWNER_IDS else UserRole.USER,
            )
            self.users[user_id] = user
            self._save_users()
            console.print(f"[green]✅ Created new user: {user_id}[/green]")
        
        user = self.users[user_id]
        user.last_active = datetime.now()
        
        # Update user info if provided
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        
        self._save_users()
        return user
    
    def check_permission(self, user_id: int, required_role: UserRole) -> bool:
        """Check if user has required permission"""
        if user_id not in self.users:
            return False
        return self.users[user_id].role >= required_role

class ProxyManager:
    """Manages proxy verification and rotation"""
    
    def __init__(self):
        self.proxies: List[ProxyEntry] = []
        self.proxy_map: Dict[str, ProxyEntry] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize proxy manager"""
        console.print("[cyan]🚀 Initializing Proxy Manager...[/cyan]")
        
        # Create aiohttp session
        self.session = aiohttp.ClientSession(
            connector=TCPConnector(ssl=False, limit=50),
            timeout=ClientTimeout(total=30)
        )
        
        # Load proxies
        await self._load_proxies()
        
        if not self.proxies:
            console.print("[red]❌ No proxies found[/red]")
            return False
        
        console.print(f"[green]✅ Loaded {len(self.proxies)} proxies[/green]")
        
        # Verify proxies
        await self.verify_all_proxies()
        
        return True
    
    async def _load_proxies(self):
        """Load proxies from file"""
        try:
            if PROXY_FILE.exists():
                with open(PROXY_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines:
                    proxy_str = line.strip()
                    if not proxy_str or proxy_str.startswith('#'):
                        continue
                    
                    # Create proxy entry
                    proxy_entry = ProxyEntry(proxy=proxy_str)
                    self.proxies.append(proxy_entry)
                    self.proxy_map[proxy_str] = proxy_entry
                
                console.print(f"[green]✅ Parsed {len(self.proxies)} proxies[/green]")
            else:
                console.print(f"[yellow]⚠️ Proxy file not found: {PROXY_FILE}[/yellow]")
                console.print("[yellow]💡 Create proxies.txt with one proxy per line[/yellow]")
                
        except Exception as e:
            console.print(f"[red]❌ Error loading proxies: {e}[/red]")
    
    async def verify_all_proxies(self):
        """Verify all proxies"""
        console.print("[cyan]🔍 Verifying proxies...[/cyan]")
        
        working = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Verifying...", total=len(self.proxies))
            
            for proxy in self.proxies:
                is_working = await self._verify_proxy(proxy)
                if is_working:
                    working += 1
                progress.update(task, advance=1)
        
        console.print(f"[green]✅ {working}/{len(self.proxies)} proxies working[/green]")
    
    async def _verify_proxy(self, proxy_entry: ProxyEntry) -> bool:
        """Verify single proxy"""
        try:
            test_urls = [
                "https://httpbin.org/ip",
                "https://api.ipify.org?format=json",
                "https://icanhazip.com",
            ]
            
            for url in test_urls:
                try:
                    start_time = time.time()
                    async with self.session.get(
                        url,
                        proxy=proxy_entry.proxy,
                        timeout=10,
                        ssl=False
                    ) as response:
                        if response.status == 200:
                            proxy_entry.verified = True
                            proxy_entry.is_active = True
                            proxy_entry.avg_response_time = time.time() - start_time
                            return True
                except:
                    continue
            
            proxy_entry.verified = False
            proxy_entry.is_active = False
            return False
            
        except Exception as e:
            proxy_entry.verified = False
            proxy_entry.is_active = False
            return False
    
    def get_best_proxy(self) -> Optional[str]:
        """Get best available proxy"""
        working_proxies = [p for p in self.proxies if p.is_active and p.verified]
        if not working_proxies:
            return None
        
        # Sort by response time and usage
        working_proxies.sort(key=lambda x: (x.avg_response_time, x.reports_used))
        return working_proxies[0].proxy
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

class AccountManager:
    """Manages Telegram accounts"""
    
    def __init__(self, proxy_manager: ProxyManager):
        self.proxy_manager = proxy_manager
        self.accounts: Dict[str, TelegramAccount] = {}
        self._load_accounts()
    
    def _load_accounts(self):
        """Load accounts from JSON file"""
        try:
            if ACCOUNTS_FILE.exists():
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for phone, acc_data in data.items():
                    try:
                        account = TelegramAccount.from_dict(acc_data)
                        self.accounts[phone] = account
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Skipping invalid account {phone}: {e}[/yellow]")
                        continue
                
                console.print(f"[green]✅ Loaded {len(self.accounts)} accounts[/green]")
        except Exception as e:
            console.print(f"[red]❌ Error loading accounts: {e}[/red]")
    
    def _save_accounts(self):
        """Save accounts to JSON file"""
        try:
            data = {phone: account.to_dict() for phone, account in self.accounts.items()}
            with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red]❌ Error saving accounts: {e}[/red]")
    
    async def add_account(self, phone: str, added_by: int) -> Tuple[bool, str]:
        """Add new Telegram account"""
        # Validate phone number
        if not re.match(r'^\+\d{10,15}$', phone):
            return False, "Invalid phone number format. Use: +1234567890"
        
        # Check if account already exists
        if phone in self.accounts:
            return False, "Account already exists"
        
        # Get proxy for account
        proxy = self.proxy_manager.get_best_proxy()
        if not proxy:
            return False, "No working proxies available"
        
        # Create session file
        session_file = SESSION_DIR / f"{phone.replace('+', '')}.session"
        
        # Create account
        account = TelegramAccount(
            phone=phone,
            session_file=session_file,
            proxy=proxy,
            status=AccountStatus.UNVERIFIED
        )
        
        self.accounts[phone] = account
        self._save_accounts()
        
        console.print(f"[green]✅ Added account: {phone}[/green]")
        return True, f"Account {phone} added successfully"
    
    async def create_session(self, phone: str, update: Update) -> Tuple[bool, str]:
        """Create Telegram session with OTP verification"""
        if phone not in self.accounts:
            return False, "Account not found"
        
        account = self.accounts[phone]
        
        # Create Telegram client
        client = TelegramClient(
            str(account.session_file),
            API_ID,
            API_HASH,
            device_model="Desktop",
            system_version="Windows 10",
            app_version="4.0.0",
            system_lang_code="en",
            lang_code="en"
        )
        
        try:
            # Connect to Telegram
            await client.connect()
            
            # Check if already authorized
            if await client.is_user_authorized():
                account.client = client
                account.status = AccountStatus.ACTIVE
                account.last_used = datetime.now()
                self._save_accounts()
                
                await update.message.reply_text(
                    f"✅ *Already Logged In!*\n\n"
                    f"Account `{phone}` was already logged in.\n"
                    f"Session restored successfully!",
                    parse_mode='Markdown'
                )
                return True, "Session restored"
            
            # Send OTP
            await update.message.reply_text(
                f"📱 *Sending OTP to {phone}...*\n\n"
                f"Please wait for the OTP code.",
                parse_mode='Markdown'
            )
            
            sent_code = await client.send_code_request(phone)
            phone_code_hash = sent_code.phone_code_hash
            
            # Store session data
            update._user_sessions = getattr(update, '_user_sessions', {})
            update._user_sessions[update.effective_user.id] = {
                "phone": phone,
                "client": client,
                "phone_code_hash": phone_code_hash,
                "step": "waiting_otp"
            }
            
            await update.message.reply_text(
                f"✅ *OTP Sent!*\n\n"
                f"Please reply with the 5-digit code you received.\n\n"
                f"Format: `12345`",
                parse_mode='Markdown'
            )
            
            return True, "OTP sent successfully"
            
        except FloodWaitError as e:
            account.status = AccountStatus.FLOOD_WAIT
            self._save_accounts()
            return False, f"Flood wait: {e.seconds} seconds"
        except PhoneNumberInvalidError:
            return False, "Invalid phone number"
        except PhoneNumberBannedError:
            account.status = AccountStatus.BANNED
            self._save_accounts()
            return False, "Phone number is banned"
        except Exception as e:
            return False, f"Error: {str(e)[:100]}"
    
    async def verify_otp(self, phone: str, otp_code: str, update: Update) -> Tuple[bool, str]:
        """Verify OTP code"""
        user_id = update.effective_user.id
        
        if not hasattr(update, '_user_sessions') or user_id not in update._user_sessions:
            return False, "Session expired"
        
        session_data = update._user_sessions[user_id]
        if session_data.get("phone") != phone:
            return False, "Phone mismatch"
        
        client = session_data["client"]
        phone_code_hash = session_data["phone_code_hash"]
        
        try:
            # Sign in with OTP
            await client.sign_in(
                phone=phone,
                code=otp_code,
                phone_code_hash=phone_code_hash
            )
            
            # Update account
            account = self.accounts[phone]
            account.client = client
            account.status = AccountStatus.ACTIVE
            account.last_used = datetime.now()
            self._save_accounts()
            
            # Get account info
            me = await client.get_me()
            account_info = f"✅ *Login Successful!*\n\n"
            account_info += f"📱 Phone: `{phone}`\n"
            account_info += f"👤 User ID: `{me.id}`\n"
            if me.username:
                account_info += f"📛 Username: @{me.username}\n"
            account_info += f"👋 Name: {me.first_name or ''}"
            if me.last_name:
                account_info += f" {me.last_name}"
            account_info += f"\n\nReady for reporting!"
            
            await update.message.reply_text(account_info, parse_mode='Markdown')
            return True, "Login successful"
            
        except SessionPasswordNeededError:
            return False, "2FA_PASSWORD_NEEDED"
        except PhoneCodeInvalidError:
            return False, "Invalid OTP code"
        except PhoneCodeExpiredError:
            return False, "OTP code expired"
        except Exception as e:
            return False, f"Verification error: {str(e)[:100]}"
    
    def get_available_accounts(self, count: int = 3) -> List[TelegramAccount]:
        """Get available accounts for reporting"""
        available = []
        
        for account in self.accounts.values():
            if (account.status == AccountStatus.ACTIVE and 
                account.report_count < 9 and
                account.client):
                available.append(account)
                if len(available) >= count:
                    break
        
        return available

class ReportingEngine:
    """Handles report creation and processing"""
    
    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
        self.active_jobs: Dict[str, ReportJob] = {}
        self.job_history: List[ReportJob] = {}
        
        # Report categories
        self.categories = {
            "spam": {"name": "Spam", "reason": InputReportReasonSpam},
            "violence": {"name": "Violence", "reason": InputReportReasonViolence},
            "pornography": {"name": "Pornography", "reason": InputReportReasonPornography},
            "child_abuse": {"name": "Child Abuse", "reason": InputReportReasonChildAbuse},
            "copyright": {"name": "Copyright", "reason": InputReportReasonCopyright},
            "fake": {"name": "Fake Account", "reason": InputReportReasonFake},
            "drugs": {"name": "Illegal Drugs", "reason": InputReportReasonIllegalDrugs},
            "other": {"name": "Other", "reason": InputReportReasonOther},
        }
    
    async def create_job(self, target: str, category: str,
                        description: str, user_id: int) -> Tuple[bool, str, Optional[str]]:
        """Create new report job"""
        if category not in self.categories:
            return False, f"Invalid category: {category}", None
        
        # Generate job ID
        job_id = hashlib.sha256(
            f"{target}{category}{user_id}{time.time()}".encode()
        ).hexdigest()[:16]
        
        # Create job
        job = ReportJob(
            job_id=job_id,
            target=target,
            target_type="user",  # Will be detected
            category=category,
            description=description,
            created_by=user_id
        )
        
        self.active_jobs[job_id] = job
        console.print(f"[cyan]📝 Created job {job_id} for {target}[/cyan]")
        
        return True, "Job created successfully", job_id
    
    async def process_job(self, job_id: str):
        """Process report job"""
        if job_id not in self.active_jobs:
            return
        
        job = self.active_jobs[job_id]
        job.status = ReportStatus.PROCESSING
        job.started_at = datetime.now()
        
        console.print(f"[cyan]🔧 Processing job {job_id}[/cyan]")
        
        try:
            # Get accounts
            accounts = self.account_manager.get_available_accounts(3)
            if not accounts:
                raise Exception("No accounts available")
            
            # Process with each account
            for account in accounts:
                result = await self._process_with_account(account, job)
                job.results.append(result)
                job.accounts_used.append(account.phone)
                
                # Update account
                account.report_count += 1
                account.total_reports += 1
                account.last_report_time = datetime.now()
            
            job.status = ReportStatus.COMPLETED
            job.completed_at = datetime.now()
            
            console.print(f"[green]✅ Completed job {job_id}[/green]")
            
        except Exception as e:
            job.status = ReportStatus.FAILED
            console.print(f"[red]❌ Job {job_id} failed: {e}[/red]")
        
        # Move to history
        self.job_history.append(job)
        del self.active_jobs[job_id]
    
    async def _process_with_account(self, account: TelegramAccount,
                                  job: ReportJob) -> Dict[str, Any]:
        """Process report with single account"""
        result = {
            "account": account.phone,
            "status": "FAILED",
            "timestamp": datetime.now().isoformat(),
        }
        
        try:
            if not account.client or not account.client.is_connected():
                await account.client.connect()
            
            # Resolve target
            entity = await account.client.get_entity(job.target)
            
            # Get report reason
            category_info = self.categories[job.category]
            reason = category_info["reason"]()
            
            # Submit report
            await account.client(ReportPeerRequest(
                peer=entity,
                reason=reason(),
                message=job.description[:200]
            ))
            
            # Simulate realistic delay
            await asyncio.sleep(random.uniform(2, 5))
            
            result["status"] = "COMPLETED"
            result["target_id"] = getattr(entity, 'id', None)
            
        except Exception as e:
            result["error"] = str(e)[:200]
        
        return result

# ============================================
# BOT HANDLER
# ============================================

class BotHandler:
    """Handles Telegram bot commands and conversations"""
    
    def __init__(self, user_manager: UserManager,
                 account_manager: AccountManager,
                 reporting_engine: ReportingEngine):
        self.user_manager = user_manager
        self.account_manager = account_manager
        self.reporting_engine = reporting_engine
        
        # Conversation states
        self.ADD_PHONE, self.ADD_OTP = range(2)
        self.REPORT_TARGET, self.REPORT_CATEGORY, self.REPORT_DESCRIPTION = range(3, 6)
    
    async def start_command(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        user = update.effective_user
        
        # Get or create user
        telegram_user = self.user_manager.get_or_create_user(
            user.id, user.username, user.first_name, user.last_name
        )
        
        welcome_message = f"""
🤖 *Telegram Enterprise Reporting System*

👤 *Your Status:*
• Role: {telegram_user.role.name}
• Reports Made: {telegram_user.reports_made}
• Last Active: {telegram_user.last_active.strftime('%Y-%m-%d %H:%M') if telegram_user.last_active else 'Never'}

🛠️ *Available Commands:*
/report - Start new report
/accounts - Account management
/stats - View statistics
/help - Help guide

💡 *Quick Start:*
1. Add accounts with /accounts
2. Start reporting with /report
3. Monitor with /stats
"""
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        help_text = """
🆘 *Help Guide*

*Basic Commands:*
/start - Welcome message
/report - Start new report
/accounts - Manage Telegram accounts
/stats - View statistics
/help - This guide

*Reporting Process:*
1. Use /report to start
2. Enter target (username or link)
3. Select category
4. Add description
5. System processes with multiple accounts

*Account Management:*
• Add accounts with /accounts
• Each account can report 9 times
• Automatic proxy rotation
• OTP verification required

*Best Practices:*
• Use detailed descriptions
• Add multiple accounts for better results
• Monitor account health
• Use working proxies
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: CallbackContext):
        """Handle /stats command"""
        user = update.effective_user
        telegram_user = self.user_manager.users.get(user.id)
        
        if not telegram_user:
            await update.message.reply_text("Please use /start first.")
            return
        
        # Get account stats
        active_accounts = sum(1 for a in self.account_manager.accounts.values() 
                            if a.status == AccountStatus.ACTIVE)
        total_accounts = len(self.account_manager.accounts)
        
        stats_message = f"""
📊 *Statistics*

👤 *Personal:*
• Role: {telegram_user.role.name}
• Reports Made: {telegram_user.reports_made}
• Trust Level: {'⭐' * min(telegram_user.role.value, 5)}

📱 *Accounts:*
• Total: {total_accounts}
• Active: {active_accounts}
• Available for reporting: {sum(1 for a in self.account_manager.accounts.values() 
                              if a.status == AccountStatus.ACTIVE and a.report_count < 9)}

📈 *System:*
• Active Jobs: {len(self.reporting_engine.active_jobs)}
• Completed Jobs: {len(self.reporting_engine.job_history)}
• System Status: ✅ Operational
"""
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
    
    async def accounts_command(self, update: Update, context: CallbackContext):
        """Handle /accounts command"""
        keyboard = [
            [InlineKeyboardButton("📱 Add Account", callback_data="acc_add")],
            [InlineKeyboardButton("📋 List Accounts", callback_data="acc_list")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="acc_refresh")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📱 *Account Management*\n\n"
            "Manage your Telegram accounts for reporting.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def report_command(self, update: Update, context: CallbackContext):
        """Handle /report command"""
        # Check if user has accounts
        active_accounts = sum(1 for a in self.account_manager.accounts.values() 
                            if a.status == AccountStatus.ACTIVE and a.report_count < 9)
        
        if active_accounts == 0:
            await update.message.reply_text(
                "❌ *No accounts available for reporting*\n\n"
                "Please add accounts first with /accounts",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(
            "📝 *Start New Report*\n\n"
            "Please send the target username or link:\n\n"
            "*Examples:*\n"
            "• @username\n"
            "• https://t.me/username\n"
            "• channelname",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
        
        return self.REPORT_TARGET
    
    async def handle_report_target(self, update: Update, context: CallbackContext):
        """Handle report target input"""
        target = update.message.text.strip()
        
        # Store in context
        context.user_data["report_target"] = target
        
        # Create category keyboard
        keyboard = []
        for category_id, category_info in self.reporting_engine.categories.items():
            keyboard.append([InlineKeyboardButton(
                category_info["name"],
                callback_data=f"cat_{category_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ *Target Accepted:* `{target}`\n\n"
            "Now select the report category:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return self.REPORT_CATEGORY
    
    async def handle_report_category(self, update: Update, context: CallbackContext):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        category = query.data.replace("cat_", "")
        
        if category not in self.reporting_engine.categories:
            await query.edit_message_text("Invalid category selected.")
            return self.REPORT_CATEGORY
        
        # Store in context
        context.user_data["report_category"] = category
        
        await query.edit_message_text(
            f"📑 *Category:* {self.reporting_engine.categories[category]['name']}\n\n"
            "Please provide a detailed description of the violation:\n\n"
            "*Requirements:*\n"
            "• Minimum 20 characters\n"
            "• Be specific and factual\n"
            "• Include evidence if available\n\n"
            "*Example:*\n"
            "\"This account is sending spam messages promoting fake investments.\"",
            parse_mode='Markdown'
        )
        
        return self.REPORT_DESCRIPTION
    
    async def handle_report_description(self, update: Update, context: CallbackContext):
        """Handle description and create report job"""
        description = update.message.text.strip()
        
        if len(description) < 20:
            await update.message.reply_text(
                "❌ Description must be at least 20 characters.",
                parse_mode='Markdown'
            )
            return self.REPORT_DESCRIPTION
        
        # Get data from context
        target = context.user_data.get("report_target")
        category = context.user_data.get("report_category")
        user_id = update.effective_user.id
        
        if not target or not category:
            await update.message.reply_text("Session expired. Please start over.")
            return ConversationHandler.END
        
        # Create job
        success, message, job_id = await self.reporting_engine.create_job(
            target=target,
            category=category,
            description=description,
            user_id=user_id
        )
        
        if success:
            # Start processing
            asyncio.create_task(self.reporting_engine.process_job(job_id))
            
            await update.message.reply_text(
                f"✅ *Report Job Created!*\n\n"
                f"Job ID: `{job_id}`\n"
                f"Target: `{target}`\n"
                f"Category: {self.reporting_engine.categories[category]['name']}\n\n"
                f"⏳ *Processing started...*\n\n"
                f"Using 3 accounts simultaneously.\n"
                f"You'll receive a notification when complete.",
                parse_mode='Markdown'
            )
            
            # Update user's report count
            if user_id in self.user_manager.users:
                self.user_manager.users[user_id].reports_made += 1
                self.user_manager._save_users()
        else:
            await update.message.reply_text(
                f"❌ *Failed to create job:*\n{message}",
                parse_mode='Markdown'
            )
        
        # Clear context
        context.user_data.clear()
        
        return ConversationHandler.END
    
    async def handle_callback_query(self, update: Update, context: CallbackContext):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "acc_add":
            await query.edit_message_text(
                "📱 *Add New Account*\n\n"
                "Please send the phone number:\n"
                "Format: `+1234567890`",
                parse_mode='Markdown'
            )
            
            # Store state
            context.user_data["action"] = "add_account"
            return self.ADD_PHONE
        
        elif data == "acc_list":
            accounts = list(self.account_manager.accounts.values())
            
            if not accounts:
                await query.edit_message_text("No accounts added yet.")
                return
            
            accounts_list = "📋 *Accounts List*\n\n"
            for i, account in enumerate(accounts, 1):
                status_icon = {
                    AccountStatus.ACTIVE: "🟢",
                    AccountStatus.INACTIVE: "🟡",
                    AccountStatus.BANNED: "🔴",
                    AccountStatus.FLOOD_WAIT: "⏳",
                }.get(account.status, "❓")
                
                accounts_list += (
                    f"{i}. {status_icon} `{account.phone}`\n"
                    f"   Status: {account.status.name}\n"
                    f"   Reports: {account.report_count}/9\n"
                )
                
                if account.last_used:
                    accounts_list += f"   Last Used: {account.last_used.strftime('%Y-%m-%d')}\n"
                
                accounts_list += "\n"
            
            await query.edit_message_text(accounts_list, parse_mode='Markdown')
        
        elif data == "acc_refresh":
            await query.edit_message_text("Refreshing accounts...")
            # Could implement refresh logic here
    
    async def handle_add_phone(self, update: Update, context: CallbackContext):
        """Handle phone number for account addition"""
        phone = update.message.text.strip()
        
        # Validate phone number
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text(
                "❌ Invalid phone number format.\n"
                "Please use: `+1234567890`",
                parse_mode='Markdown'
            )
            return self.ADD_PHONE
        
        # Add account
        success, message = await self.account_manager.add_account(
            phone, update.effective_user.id
        )
        
        if success:
            await update.message.reply_text(
                f"✅ *Account Added*\n\n"
                f"Phone: `{phone}`\n\n"
                f"Now creating session...",
                parse_mode='Markdown'
            )
            
            # Create session
            session_success, session_message = await self.account_manager.create_session(
                phone, update
            )
            
            if session_success:
                return self.ADD_OTP
            else:
                await update.message.reply_text(
                    f"⚠️ *Session Creation:*\n{session_message}",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
        else:
            await update.message.reply_text(
                f"❌ *Failed to add account:*\n{message}",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    
    async def handle_otp(self, update: Update, context: CallbackContext):
        """Handle OTP verification"""
        otp_code = update.message.text.strip()
        
        if not re.match(r'^\d{5}$', otp_code):
            await update.message.reply_text(
                "❌ Invalid OTP format. Must be 5 digits.",
                parse_mode='Markdown'
            )
            return self.ADD_OTP
        
        # Get phone from context (simplified - in production, store in user_data)
        accounts = list(self.account_manager.accounts.values())
        if not accounts:
            await update.message.reply_text("No accounts found.")
            return ConversationHandler.END
        
        # Use the most recently added account
        account = accounts[-1]
        
        success, message = await self.account_manager.verify_otp(
            account.phone, otp_code, update
        )
        
        if success:
            await update.message.reply_text(
                "✅ *Account Verified!*\n\n"
                "Ready for reporting!",
                parse_mode='Markdown'
            )
        elif message == "2FA_PASSWORD_NEEDED":
            await update.message.reply_text(
                "🔒 *2FA Password Required*\n\n"
                "Please send your 2FA password:",
                parse_mode='Markdown'
            )
            # Could add 2FA handling here
        else:
            await update.message.reply_text(
                f"❌ *Verification Failed:*\n{message}",
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
    
    async def cancel_command(self, update: Update, context: CallbackContext):
        """Cancel any operation"""
        await update.message.reply_text(
            "Operation cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

# ============================================
# MAIN APPLICATION
# ============================================

class TelegramEnterpriseBot:
    """Main enterprise bot application"""
    
    def __init__(self):
        console.print("[cyan]🚀 Initializing Telegram Enterprise Bot[/cyan]")
        
        # Initialize managers
        self.user_manager = UserManager()
        self.proxy_manager = ProxyManager()
        self.account_manager = AccountManager(self.proxy_manager)
        self.reporting_engine = ReportingEngine(self.account_manager)
        
        # Initialize bot handler
        self.bot_handler = BotHandler(
            self.user_manager,
            self.account_manager,
            self.reporting_engine
        )
        
        # Create Telegram bot application
        persistence = PicklePersistence(filepath="data/bot_persistence.pickle")
        
        self.application = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .persistence(persistence)
            .post_init(self._setup_commands)
            .build()
        )
        
        # Setup handlers
        self._setup_handlers()
    
    async def _setup_commands(self, application: Application):
        """Setup bot commands"""
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help information"),
            BotCommand("report", "Start a new report"),
            BotCommand("accounts", "Manage accounts"),
            BotCommand("stats", "Show statistics"),
            BotCommand("cancel", "Cancel current operation"),
        ]
        
        await application.bot.set_my_commands(commands)
        console.print("[green]✅ Bot commands setup complete[/green]")
    
    def _setup_handlers(self):
        """Setup all bot handlers"""
        
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.bot_handler.start_command))
        self.application.add_handler(CommandHandler("help", self.bot_handler.help_command))
        self.application.add_handler(CommandHandler("stats", self.bot_handler.stats_command))
        self.application.add_handler(CommandHandler("accounts", self.bot_handler.accounts_command))
        self.application.add_handler(CommandHandler("cancel", self.bot_handler.cancel_command))
        
        # Report conversation
        report_conv = ConversationHandler(
            entry_points=[CommandHandler("report", self.bot_handler.report_command)],
            states={
                self.bot_handler.REPORT_TARGET: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,
                                 self.bot_handler.handle_report_target)
                ],
                self.bot_handler.REPORT_CATEGORY: [
                    CallbackQueryHandler(self.bot_handler.handle_report_category,
                                       pattern="^cat_")
                ],
                self.bot_handler.REPORT_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,
                                 self.bot_handler.handle_report_description)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.cancel_command)],
        )
        self.application.add_handler(report_conv)
        
        # Account addition conversation
        account_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.bot_handler.handle_callback_query,
                pattern="^acc_"
            )],
            states={
                self.bot_handler.ADD_PHONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,
                                 self.bot_handler.handle_add_phone)
                ],
                self.bot_handler.ADD_OTP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,
                                 self.bot_handler.handle_otp)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.cancel_command)],
        )
        self.application.add_handler(account_conv)
        
        # Callback query handler
        self.application.add_handler(
            CallbackQueryHandler(self.bot_handler.handle_callback_query)
        )
        
        console.print("[green]✅ Bot handlers setup complete[/green]")
    
    async def initialize(self) -> bool:
        """Initialize the enterprise system"""
        console.print("[cyan]🔧 Initializing system components...[/cyan]")
        
        try:
            # Initialize proxy manager
            proxy_ok = await self.proxy_manager.initialize()
            if not proxy_ok:
                console.print("[yellow]⚠️ Continuing without proxies[/yellow]")
            
            # Display system status
            await self._display_status()
            
            console.print("[green]✅ System initialization complete[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Initialization failed: {e}[/red]")
            return False
    
    async def _display_status(self):
        """Display system status"""
        user_stats = len(self.user_manager.users)
        account_stats = len(self.account_manager.accounts)
        active_accounts = sum(1 for a in self.account_manager.accounts.values() 
                            if a.status == AccountStatus.ACTIVE)
        
        status_table = Table(title="System Status", box=box.ROUNDED)
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="green")
        status_table.add_column("Details", style="yellow")
        
        status_table.add_row("Users", str(user_stats), "Loaded from storage")
        status_table.add_row("Accounts", str(account_stats), f"{active_accounts} active")
        status_table.add_row("Proxies", "✅" if self.proxy_manager.proxies else "⚠️", 
                           f"{len([p for p in self.proxy_manager.proxies if p.is_active])} working")
        status_table.add_row("Bot", "✅", "Ready")
        
        console.print(status_table)
    
    async def run(self):
        """Run the enterprise bot"""
        # Initialize system
        initialized = await self.initialize()
        if not initialized:
            console.print("[red]❌ Cannot start bot[/red]")
            return
        
        # Start bot
        console.print("[green]🤖 Starting Telegram Enterprise Bot...[/green]")
        
        try:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            console.print("[green]✅ Bot is running![/green]")
            console.print("[yellow]📱 Use /start in Telegram to begin[/yellow]")
            
            # Keep running
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Shutting down...[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Bot error: {e}[/red]")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the system gracefully"""
        console.print("[yellow]🔧 Shutting down...[/yellow]")
        
        try:
            # Stop proxy manager
            await self.proxy_manager.cleanup()
            
            # Save data
            self.user_manager._save_users()
            self.account_manager._save_accounts()
            
            # Stop bot
            if hasattr(self.application, 'updater'):
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            console.print("[green]✅ Shutdown complete[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Shutdown error: {e}[/red]")

# ============================================
# MAIN ENTRY POINT
# ============================================

async def main():
    """Main entry point"""
    console.print("[bright_cyan]⚡ TELEGRAM ENTERPRISE REPORTING SYSTEM[/bright_cyan]")
    
    # Create and run bot
    bot = TelegramEnterpriseBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")

if __name__ == "__main__":
    # Set event loop policy for Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Application terminated[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Fatal error: {e}[/red]")
        sys.exit(1)
