#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Enterprise Reporting Bot (Advanced & Stable)
- Uses Pyrogram v2+ for MTProto operations
- MongoDB (async via motor) for persistent storage
- Environment variables for all secrets
- Periodic proxy refresh from @ProxyMTProto
- Robust error handling and retries
"""

import asyncio
import logging
import logging.handlers
import os
import re
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse

import motor.motor_asyncio
from pymongo import IndexModel, ASCENDING

# Pyrogram imports with version check
try:
    import pyrogram
    from pyrogram import Client, filters, enums
    from pyrogram.raw import functions, types
    from pyrogram.errors import (
        SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired,
        FloodWait, PhoneNumberBanned, PhoneNumberUnoccupied, ApiIdInvalid,
        AuthKeyUnregistered, UserDeactivated, UserDeactivatedBan
    )
    from pyrogram.types import User as PyroUser
except ImportError as e:
    raise ImportError(
        "Pyrogram is not installed. Please install pyrogram>=2.0.0 with: pip install pyrogram>=2.0.0"
    ) from e

# Check Pyrogram version
if pyrogram.__version__ < "2.0.0":
    raise ImportError(
        f"Pyrogram version {pyrogram.__version__} is too old. Please upgrade to >=2.0.0"
    )

# PTB imports
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, ParseMode
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters as tfilters, ConversationHandler, ContextTypes
)
from telegram.error import TelegramError

# ==================== CONFIGURATION ====================
class Config:
    # Load from environment
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    LOG_GROUP_ID = int(os.environ.get("LOG_GROUP_ID", "-1001234567890"))
    OWNER_IDS = list(map(int, os.environ.get("OWNER_IDS", "6118760915,1366105247").split(',')))
    PROXY_CHANNEL = os.environ.get("PROXY_CHANNEL", "ProxyMTProto")
    MAX_REPORTS_PER_PROXY = int(os.environ.get("MAX_REPORTS_PER_PROXY", "9"))
    MAX_ACCOUNTS_PER_JOB = int(os.environ.get("MAX_ACCOUNTS_PER_JOB", "3"))
    PROXY_REFRESH_INTERVAL = int(os.environ.get("PROXY_REFRESH_INTERVAL", "3600"))  # seconds
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    LOG_FILE = os.environ.get("LOG_FILE", "bot.log")

    @classmethod
    def validate(cls):
        if not cls.API_ID or not cls.API_HASH or not cls.BOT_TOKEN or not cls.MONGO_URL:
            raise ValueError("Missing required environment variables: API_ID, API_HASH, BOT_TOKEN, MONGO_URL")
        if cls.LOG_GROUP_ID >= 0:
            raise ValueError("LOG_GROUP_ID must be negative (group ID)")

# ==================== LOGGING SETUP ====================
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(Config.LOG_LEVEL)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(Config.LOG_LEVEL)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Rotating file handler
    if Config.LOG_FILE:
        file_handler = logging.handlers.RotatingFileHandler(
            Config.LOG_FILE, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = setup_logging()

# ==================== MONGODB (ASYNC) ====================
class Database:
    def __init__(self, uri: str):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client["telegram_bot"]
        self.sessions = self.db["pyrogram_sessions"]
        self.accounts = self.db["accounts"]
        self.users = self.db["users"]
        self.jobs = self.db["jobs"]
        self.proxies = self.db["proxies"]

        # Create indexes
        asyncio.create_task(self._create_indexes())

    async def _create_indexes(self):
        await self.accounts.create_index("phone", unique=True)
        await self.accounts.create_index("status")
        await self.users.create_index("user_id", unique=True)
        await self.jobs.create_index("job_id", unique=True)
        await self.jobs.create_index("created_at")
        await self.proxies.create_index("proxy", unique=True)

db = Database(Config.MONGO_URL)

# ==================== PROXY UTILITIES ====================
def parse_proxy(proxy_str: str) -> Optional[Dict]:
    """Convert proxy string to Pyrogram proxy dict."""
    try:
        parsed = urlparse(proxy_str)
        if parsed.scheme == 'mtproto':
            secret = parsed.query.split('=')[-1] if parsed.query else ''
            return {
                'scheme': 'mtproto',
                'hostname': parsed.hostname,
                'port': parsed.port,
                'secret': secret
            }
        else:  # socks5, http, https
            return {
                'scheme': parsed.scheme,
                'hostname': parsed.hostname,
                'port': parsed.port,
                'username': parsed.username,
                'password': parsed.password
            }
    except Exception as e:
        logger.error(f"Proxy parse error: {e}")
        return None

async def get_proxy_country(proxy: str) -> str:
    """Fetch country of proxy IP via ip-api.com (cached)."""
    try:
        import aiohttp
        # Extract host
        if '@' in proxy:
            host = proxy.split('@')[1].split(':')[0]
        else:
            host = proxy.split('://')[1].split(':')[0] if '://' in proxy else proxy.split(':')[0]
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://ip-api.com/json/{host}", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('country', 'Unknown')
    except Exception as e:
        logger.debug(f"Country lookup failed for {proxy}: {e}")
    return "Unknown"

async def fetch_proxies_from_channel(client: Client, limit: int = 50) -> List[str]:
    """Fetch proxy strings from the configured channel."""
    proxies = []
    try:
        chat = await client.get_chat(Config.PROXY_CHANNEL)
        async for msg in client.get_chat_history(chat.id, limit=limit):
            if msg.text:
                # Look for socks5:// or mtproto:// URLs
                found = re.findall(r'(socks5://[^\s]+|mtproto://[^\s]+)', msg.text)
                proxies.extend(found)
        proxies = list(set(proxies))
        logger.info(f"Fetched {len(proxies)} unique proxies from {Config.PROXY_CHANNEL}")
    except Exception as e:
        logger.error(f"Failed to fetch proxies: {e}")
    return proxies

async def refresh_proxy_pool():
    """Periodic task to refresh proxy pool from channel."""
    while True:
        try:
            # Use a temporary client (or reuse one from account manager? but we don't have one yet)
            async with Client("proxy_fetcher", api_id=Config.API_ID, api_hash=Config.API_HASH) as temp_client:
                await temp_client.start()
                proxies = await fetch_proxies_from_channel(temp_client)
                # Store in DB
                for proxy in proxies:
                    await db.proxies.update_one(
                        {"proxy": proxy},
                        {"$set": {"proxy": proxy, "last_seen": datetime.now().isoformat()}},
                        upsert=True
                    )
                # Remove old proxies (optional)
                # await db.proxies.delete_many({"last_seen": {"$lt": (datetime.now() - timedelta(days=7)).isoformat()}})
                logger.info(f"Proxy pool refreshed. Total: {len(proxies)}")
        except Exception as e:
            logger.error(f"Proxy refresh failed: {e}")
        await asyncio.sleep(Config.PROXY_REFRESH_INTERVAL)

# ==================== DATA MODELS ====================
class AccountStatus:
    UNVERIFIED = "unverified"
    VERIFYING = "verifying"
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    NEED_PASSWORD = "need_password"
    FLOOD_WAIT = "flood_wait"

class UserRole:
    BANNED = 0
    USER = 1
    ADMIN = 2
    OWNER = 3

@dataclass
class TelegramAccount:
    phone: str
    session_name: str
    proxy: Optional[str] = None
    proxy_index: int = 0
    status: str = AccountStatus.UNVERIFIED
    user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    report_count: int = 0
    total_reports: int = 0
    last_report_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    flood_until: Optional[datetime] = None  # if flood_wait

    def to_dict(self):
        d = asdict(self)
        d["last_report_time"] = self.last_report_time.isoformat() if self.last_report_time else None
        d["created_at"] = self.created_at.isoformat()
        d["last_login"] = self.last_login.isoformat() if self.last_login else None
        d["flood_until"] = self.flood_until.isoformat() if self.flood_until else None
        return d

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        # Parse datetimes
        for field in ["last_report_time", "created_at", "last_login", "flood_until"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)

@dataclass
class BotUser:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: int = UserRole.USER
    reports_made: int = 0
    joined_at: datetime = field(default_factory=datetime.now)
    last_active: Optional[datetime] = None

    def to_dict(self):
        d = asdict(self)
        d["joined_at"] = self.joined_at.isoformat()
        d["last_active"] = self.last_active.isoformat() if self.last_active else None
        return d

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        if data.get("joined_at"):
            data["joined_at"] = datetime.fromisoformat(data["joined_at"])
        if data.get("last_active"):
            data["last_active"] = datetime.fromisoformat(data["last_active"])
        return cls(**data)

@dataclass
class ReportJob:
    job_id: str
    target: str
    target_type: str  # user, group, channel
    job_type: str      # profile, message, entity
    category: str
    description: str
    created_by: int
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, processing, completed, failed
    accounts_used: List[str] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)
    message_chat: Optional[str] = None   # for message reports
    message_id: Optional[int] = None     # for message reports

    def to_dict(self):
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

# ==================== ACCOUNT MANAGER ====================
class AccountManager:
    def __init__(self):
        self.accounts: Dict[str, TelegramAccount] = {}
        self.clients: Dict[str, Client] = {}  # phone -> client instance
        self.lock = asyncio.Lock()
        asyncio.create_task(self._load_accounts())

    async def _load_accounts(self):
        async for doc in db.accounts.find():
            acc = TelegramAccount.from_dict(doc)
            self.accounts[acc.phone] = acc
        logger.info(f"Loaded {len(self.accounts)} accounts from DB")

    async def get_proxy_pool(self) -> List[str]:
        cursor = db.proxies.find().sort("last_seen", -1)
        proxies = [doc["proxy"] async for doc in cursor]
        return proxies

    async def get_next_proxy(self, account: Optional[TelegramAccount] = None) -> Optional[str]:
        pool = await self.get_proxy_pool()
        if not pool:
            return None
        if account:
            idx = account.proxy_index % len(pool)
            account.proxy_index += 1
            return pool[idx]
        else:
            return pool[0]

    async def save_session_string(self, phone: str, client: Client):
        session_string = await client.export_session_string()
        session_name = phone.replace('+', '')
        await db.sessions.update_one(
            {"_id": session_name},
            {"$set": {"session": session_string}},
            upsert=True
        )

    async def create_client(self, phone: str, proxy: Optional[str] = None) -> Tuple[Client, bool]:
        session_name = phone.replace('+', '')
        doc = await db.sessions.find_one({"_id": session_name})
        session_string = doc.get("session") if doc else None
        proxy_dict = parse_proxy(proxy) if proxy else None

        if session_string:
            client = Client(
                name=session_name,
                session_string=session_string,
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                proxy=proxy_dict,
                in_memory=True
            )
        else:
            client = Client(
                name=session_name,
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                proxy=proxy_dict,
                in_memory=True
            )

        await client.connect()
        authorized = await client.is_user_authorized()
        return client, authorized

    async def add_account(self, phone: str, proxy: Optional[str] = None) -> Tuple[bool, str, Optional[Client]]:
        async with self.lock:
            if phone in self.accounts:
                return False, "Account already exists", None
            try:
                client, authorized = await self.create_client(phone, proxy)
            except Exception as e:
                return False, f"Failed to create client: {e}", None

            account = TelegramAccount(
                phone=phone,
                session_name=phone.replace('+', ''),
                proxy=proxy,
                status=AccountStatus.ACTIVE if authorized else AccountStatus.UNVERIFIED
            )
            if authorized:
                await self._update_account_info(account, client)
                await self.save_session_string(phone, client)
                self.clients[phone] = client
            self.accounts[phone] = account
            await db.accounts.insert_one(account.to_dict())
            return True, "Account added", client

    async def _update_account_info(self, account: TelegramAccount, client: Client):
        try:
            me: PyroUser = await client.get_me()
            account.user_id = me.id
            account.username = me.username
            account.first_name = me.first_name
            account.last_name = me.last_name
            account.status = AccountStatus.ACTIVE
            account.last_login = datetime.now()
            await db.accounts.update_one({"phone": account.phone}, {"$set": account.to_dict()})
        except Exception as e:
            logger.error(f"Failed to update account info for {account.phone}: {e}")

    async def send_otp(self, phone: str, client: Client) -> Tuple[bool, str]:
        try:
            sent = await client.send_code(phone)
            acc = self.accounts.get(phone)
            if acc:
                acc.otp_data = {"phone_code_hash": sent.phone_code_hash}  # store in account? we'll store in session
                acc.status = AccountStatus.VERIFYING
                await db.accounts.update_one({"phone": phone}, {"$set": {"status": AccountStatus.VERIFYING}})
            return True, "OTP sent"
        except FloodWait as e:
            return False, f"Flood wait: {e.value} seconds"
        except Exception as e:
            return False, str(e)

    async def verify_otp(self, phone: str, code: str) -> Tuple[bool, str, Optional[Client]]:
        acc = self.accounts.get(phone)
        if not acc:
            return False, "Account not found", None
        client = self.clients.get(phone) or (await self.create_client(phone, acc.proxy))[0]
        if not client.is_connected:
            await client.connect()
        try:
            await client.sign_in(phone, code)
            await self._update_account_info(acc, client)
            await self.save_session_string(phone, client)
            self.clients[phone] = client
            return True, "Login successful", client
        except SessionPasswordNeeded:
            acc.status = AccountStatus.NEED_PASSWORD
            await db.accounts.update_one({"phone": phone}, {"$set": {"status": AccountStatus.NEED_PASSWORD}})
            return False, "2FA required", client
        except (PhoneCodeInvalid, PhoneCodeExpired) as e:
            return False, f"Invalid code: {e}", client
        except Exception as e:
            return False, str(e), client

    async def verify_2fa(self, phone: str, password: str) -> Tuple[bool, str]:
        acc = self.accounts.get(phone)
        if not acc:
            return False, "Account not found"
        client = self.clients.get(phone)
        if not client or not client.is_connected:
            return False, "Client not connected"
        try:
            await client.check_password(password)
            await self._update_account_info(acc, client)
            await self.save_session_string(phone, client)
            return True, "2FA verified"
        except Exception as e:
            return False, str(e)

    async def rotate_proxy(self, phone: str) -> Tuple[bool, str]:
        acc = self.accounts.get(phone)
        if not acc:
            return False, "Account not found"
        new_proxy = await self.get_next_proxy(acc)
        if not new_proxy:
            return False, "No proxies available"
        # Close old client if any
        old_client = self.clients.pop(phone, None)
        if old_client:
            await old_client.stop()
        try:
            client, authorized = await self.create_client(phone, new_proxy)
            if not authorized:
                return False, "Session lost after proxy change. Re-login required."
            self.clients[phone] = client
            acc.client = client  # not stored
            acc.proxy = new_proxy
            acc.report_count = 0
            await db.accounts.update_one({"phone": phone}, {"$set": {"proxy": new_proxy, "report_count": 0}})
            return True, f"Proxy rotated to {new_proxy}"
        except Exception as e:
            return False, f"Rotation failed: {e}"

    async def get_client(self, phone: str) -> Optional[Client]:
        """Get a connected client for the account."""
        acc = self.accounts.get(phone)
        if not acc:
            return None
        if phone in self.clients:
            client = self.clients[phone]
            if client.is_connected:
                return client
            else:
                await client.connect()
                return client
        else:
            client, authorized = await self.create_client(phone, acc.proxy)
            if authorized:
                self.clients[phone] = client
                return client
            else:
                return None

    async def remove_account(self, phone: str) -> bool:
        async with self.lock:
            if phone in self.clients:
                await self.clients[phone].stop()
                del self.clients[phone]
            if phone in self.accounts:
                del self.accounts[phone]
            result = await db.accounts.delete_one({"phone": phone})
            await db.sessions.delete_one({"_id": phone.replace('+', '')})
            return result.deleted_count > 0

# ==================== REPORTING ENGINE ====================
class ReportingEngine:
    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
        self.active_jobs: Dict[str, ReportJob] = {}
        self.lock = asyncio.Lock()

    REASON_MAP = {
        "spam": types.InputReportReasonSpam(),
        "violence": types.InputReportReasonViolence(),
        "pornography": types.InputReportReasonPornography(),
        "child_abuse": types.InputReportReasonChildAbuse(),
        "illegal_drugs": types.InputReportReasonIllegalDrugs(),
        "personal_details": types.InputReportReasonPersonalDetails(),
        "copyright": types.InputReportReasonCopyright(),
        "other": types.InputReportReasonOther(),
    }

    async def create_job(self, target: str, target_type: str, job_type: str,
                         category: str, description: str, user_id: int,
                         message_chat: Optional[str] = None,
                         message_id: Optional[int] = None) -> Tuple[bool, str, str]:
        job_id = str(uuid.uuid4())[:8]
        job = ReportJob(
            job_id=job_id,
            target=target,
            target_type=target_type,
            job_type=job_type,
            category=category,
            description=description,
            created_by=user_id,
            message_chat=message_chat,
            message_id=message_id
        )
        self.active_jobs[job_id] = job
        await db.jobs.insert_one(job.to_dict())
        logger.info(f"Job {job_id} created by {user_id}")
        return True, "Job created", job_id

    async def process_job(self, job_id: str):
        job = self.active_jobs.get(job_id)
        if not job:
            # try load from DB
            doc = await db.jobs.find_one({"job_id": job_id})
            if doc:
                job = ReportJob.from_dict(doc)
            else:
                return
        job.status = "processing"
        await self._update_job(job)

        # Get active accounts, not flood-waiting
        accounts = []
        for acc in self.account_manager.accounts.values():
            if acc.status == AccountStatus.ACTIVE:
                if acc.flood_until and acc.flood_until > datetime.now():
                    continue
                accounts.append(acc)

        # Limit accounts per job
        accounts = accounts[:Config.MAX_ACCOUNTS_PER_JOB]
        if not accounts:
            job.status = "failed"
            job.results.append({"error": "No active accounts available"})
            await self._finish_job(job)
            return

        for acc in accounts:
            # Check proxy rotation
            if acc.report_count >= Config.MAX_REPORTS_PER_PROXY:
                rotated, msg = await self.account_manager.rotate_proxy(acc.phone)
                if not rotated:
                    job.results.append({"account": acc.phone, "error": f"Proxy rotation failed: {msg}"})
                    continue
            # Get client
            client = await self.account_manager.get_client(acc.phone)
            if not client:
                job.results.append({"account": acc.phone, "error": "Client not available"})
                continue

            result = await self._report_with_account(acc, client, job)
            job.results.append(result)
            job.accounts_used.append(acc.phone)
            if result.get("success"):
                acc.report_count += 1
                acc.total_reports += 1
                acc.last_report_time = datetime.now()
                # Update account in DB
                await db.accounts.update_one(
                    {"phone": acc.phone},
                    {"$set": {
                        "report_count": acc.report_count,
                        "total_reports": acc.total_reports,
                        "last_report_time": acc.last_report_time.isoformat()
                    }}
                )
            # If flood wait, set flood_until
            if "flood" in result.get("error", "").lower():
                match = re.search(r'(\d+)', result["error"])
                if match:
                    seconds = int(match.group(1))
                    acc.flood_until = datetime.now() + timedelta(seconds=seconds)
                    await db.accounts.update_one(
                        {"phone": acc.phone},
                        {"$set": {"flood_until": acc.flood_until.isoformat()}}
                    )

        successes = [r for r in job.results if r.get("success")]
        job.status = "completed" if successes else "failed"
        await self._finish_job(job)

    async def _report_with_account(self, account: TelegramAccount, client: Client, job: ReportJob) -> Dict:
        try:
            if job.target_type == "user":
                peer = await client.resolve_peer(job.target)
            else:
                peer = await client.resolve_peer(job.target)

            reason = self.REASON_MAP.get(job.category.lower(), types.InputReportReasonOther())

            if job.job_type == "message":
                if not job.message_chat or not job.message_id:
                    return {"account": account.phone, "success": False, "error": "Message details missing"}
                msg_peer = await client.resolve_peer(job.message_chat)
                await client.invoke(
                    functions.messages.Report(
                        peer=msg_peer,
                        id=[job.message_id],
                        reason=reason,
                        message=job.description
                    )
                )
                return {"account": account.phone, "success": True, "type": "message"}
            elif job.job_type == "profile":
                # For profile, we need to report the user with a reason (profile picture)
                # There is no direct "report profile picture" method; we report the user with a message about the photo.
                # Alternatively, we could use account.ReportPeer which is same as entity.
                # But we'll use account.ReportPeer (same as entity) with description indicating profile picture.
                await client.invoke(
                    functions.account.ReportPeer(
                        peer=peer,
                        reason=reason,
                        message=f"Profile picture: {job.description}"
                    )
                )
                return {"account": account.phone, "success": True, "type": "profile"}
            else:  # entity
                await client.invoke(
                    functions.account.ReportPeer(
                        peer=peer,
                        reason=reason,
                        message=job.description
                    )
                )
                return {"account": account.phone, "success": True, "type": "entity"}
        except FloodWait as e:
            return {"account": account.phone, "success": False, "error": f"Flood wait {e.value}s"}
        except Exception as e:
            return {"account": account.phone, "success": False, "error": str(e)}

    async def _update_job(self, job: ReportJob):
        await db.jobs.update_one({"job_id": job.job_id}, {"$set": job.to_dict()})

    async def _finish_job(self, job: ReportJob):
        await self._update_job(job)
        if job.job_id in self.active_jobs:
            del self.active_jobs[job.job_id]
        # Optionally notify user via bot (handled separately)

# ==================== USER MANAGER ====================
class UserManager:
    def __init__(self):
        self.users: Dict[int, BotUser] = {}
        asyncio.create_task(self._load_users())

    async def _load_users(self):
        async for doc in db.users.find():
            user = BotUser.from_dict(doc)
            self.users[user.user_id] = user
        logger.info(f"Loaded {len(self.users)} users from DB")

    async def get_or_create(self, user_id: int, username: str = None,
                            first_name: str = None, last_name: str = None) -> BotUser:
        if user_id in self.users:
            user = self.users[user_id]
            user.last_active = datetime.now()
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
        else:
            role = UserRole.OWNER if user_id in Config.OWNER_IDS else UserRole.USER
            user = BotUser(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            self.users[user_id] = user
        await db.users.update_one({"user_id": user_id}, {"$set": user.to_dict()}, upsert=True)
        return user

    def has_permission(self, user_id: int, min_role: int = UserRole.USER) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        return user.role >= min_role

# ==================== BOT HANDLER ====================
class BotHandler:
    # Conversation states
    (MAIN, ADD_PHONE, ADD_OTP, ADD_2FA,
     REPORT_TARGET_TYPE, REPORT_TARGET, REPORT_USER_OPTION,
     REPORT_MESSAGE_LINK, REPORT_ENTITY_OPTION, REPORT_CATEGORY,
     REPORT_DESCRIPTION) = range(11)

    def __init__(self, user_manager: UserManager, account_manager: AccountManager,
                 reporting_engine: ReportingEngine):
        self.user_manager = user_manager
        self.account_manager = account_manager
        self.reporting_engine = reporting_engine
        self.user_sessions = {}
        self.application = None  # will be set later

    async def _log(self, text: str):
        try:
            await self.application.bot.send_message(Config.LOG_GROUP_ID, text)
        except Exception as e:
            logger.error(f"Failed to send log: {e}")

    # -------------------- Start --------------------
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        bot_user = await self.user_manager.get_or_create(
            user.id, user.username, user.first_name, user.last_name
        )
        await self._log(f"🆕 User {user.id} (@{user.username}) started the bot.")
        await update.message.reply_text(
            f"👋 Hello {user.first_name}!\n"
            f"Your role: {bot_user.role}\n\n"
            "Commands:\n"
            "/addaccount - Add a new Telegram account\n"
            "/accounts - List my accounts\n"
            "/removeaccount - Remove an account\n"
            "/report - Report a user/group/channel\n"
            "/jobs - List my report jobs\n"
            "/refreshproxies - Manually refresh proxy list (admin)\n"
            "/stats - Bot statistics (admin)\n"
            "/help - Show help"
        )
        return self.MAIN

    # -------------------- Account Addition --------------------
    async def add_account_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Please send the phone number in international format:\n"
            "Example: `+1234567890`"
        )
        return self.ADD_PHONE

    async def add_account_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        phone = update.message.text.strip()
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text("Invalid phone number. Use format +1234567890")
            return self.ADD_PHONE

        proxy = await self.account_manager.get_next_proxy()
        success, msg, client = await self.account_manager.add_account(phone, proxy)
        if not success:
            await update.message.reply_text(f"Error: {msg}")
            return self.MAIN

        if client and not await client.is_user_authorized():
            ok, otp_msg = await self.account_manager.send_otp(phone, client)
            if not ok:
                await update.message.reply_text(f"Failed to send OTP: {otp_msg}")
                return self.MAIN
            self.user_sessions[update.effective_user.id] = {"phone": phone}
            await update.message.reply_text(
                "OTP sent to your phone. Please enter the 5-digit code."
            )
            return self.ADD_OTP
        else:
            country = await get_proxy_country(proxy) if proxy else "Unknown"
            await update.message.reply_text(
                f"Account already logged in.\nProxy country: {country}"
            )
            return self.MAIN

    async def add_account_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        code = update.message.text.strip()
        if not code.isdigit() or len(code) != 5:
            await update.message.reply_text("Invalid code. Please enter 5 digits.")
            return self.ADD_OTP

        user_id = update.effective_user.id
        phone = self.user_sessions.get(user_id, {}).get("phone")
        if not phone:
            await update.message.reply_text("Session expired. Start over with /addaccount.")
            return self.MAIN

        success, msg, client = await self.account_manager.verify_otp(phone, code)
        if success:
            acc = self.account_manager.accounts.get(phone)
            country = await get_proxy_country(acc.proxy) if acc.proxy else "Unknown"
            await update.message.reply_text(
                f"✅ Login successful!\nProxy country: {country}\nReports today: {acc.report_count}/{Config.MAX_REPORTS_PER_PROXY}"
            )
            await self._log(f"✅ Account {phone} added successfully. Proxy: {acc.proxy}")
            self.user_sessions.pop(user_id, None)
            return self.MAIN
        elif msg == "2FA required":
            self.user_sessions[user_id] = {"phone": phone, "need_2fa": True}
            await update.message.reply_text(
                "This account has 2FA enabled. Please enter your password."
            )
            return self.ADD_2FA
        else:
            await update.message.reply_text(f"Verification failed: {msg}")
            return self.ADD_OTP

    async def add_account_2fa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text.strip()
        user_id = update.effective_user.id
        phone = self.user_sessions.get(user_id, {}).get("phone")
        if not phone:
            await update.message.reply_text("Session expired.")
            return self.MAIN
        success, msg = await self.account_manager.verify_2fa(phone, password)
        if success:
            acc = self.account_manager.accounts.get(phone)
            country = await get_proxy_country(acc.proxy) if acc.proxy else "Unknown"
            await update.message.reply_text(
                f"✅ 2FA verified! Account ready.\nProxy country: {country}"
            )
            await self._log(f"✅ Account {phone} added with 2FA. Proxy: {acc.proxy}")
        else:
            await update.message.reply_text(f"2FA failed: {msg}")
            return self.ADD_2FA
        self.user_sessions.pop(user_id, None)
        return self.MAIN

    # -------------------- Account Management --------------------
    async def accounts_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.account_manager.accounts:
            await update.message.reply_text("No accounts added yet.")
            return
        text = "📱 **Your Accounts**\n\n"
        for phone, acc in self.account_manager.accounts.items():
            status_icon = "🟢" if acc.status == AccountStatus.ACTIVE else "🔴"
            text += f"{status_icon} `{phone}` - {acc.status} (Reports: {acc.report_count}/{Config.MAX_REPORTS_PER_PROXY})\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def remove_account_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.account_manager.accounts:
            await update.message.reply_text("No accounts to remove.")
            return
        keyboard = []
        for phone in self.account_manager.accounts.keys():
            keyboard.append([InlineKeyboardButton(phone, callback_data=f"del_{phone}")])
        await update.message.reply_text(
            "Select account to remove:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return self.MAIN  # We'll handle via callback

    async def remove_account_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        phone = query.data[4:]  # remove 'del_'
        success = await self.account_manager.remove_account(phone)
        if success:
            await query.edit_message_text(f"Account {phone} removed.")
            await self._log(f"❌ Account {phone} removed by {query.from_user.id}")
        else:
            await query.edit_message_text(f"Failed to remove account {phone}.")
        return self.MAIN

    # -------------------- Reporting --------------------
    async def report_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("👤 User", callback_data="target_user")],
            [InlineKeyboardButton("👥 Group", callback_data="target_group")],
            [InlineKeyboardButton("📢 Channel", callback_data="target_channel")]
        ]
        await update.message.reply_text(
            "What would you like to report?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return self.REPORT_TARGET_TYPE

    async def report_target_type_cb(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        target_type = query.data.split('_')[1]
        self.user_sessions[user_id] = {"target_type": target_type}
        if target_type == "user":
            await query.edit_message_text(
                "Send the username or link of the user.\n"
                "Example: @username or https://t.me/username"
            )
        else:
            await query.edit_message_text(
                f"Send the public {target_type} link.\n"
                "Example: @channel or https://t.me/joinchat/xxx"
            )
        return self.REPORT_TARGET

    async def report_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        target = update.message.text.strip()
        sess = self.user_sessions.get(user_id)
        if not sess:
            await update.message.reply_text("Session expired. Start over with /report.")
            return self.MAIN
        target_type = sess["target_type"]
        sess["target"] = target

        if target_type == "user":
            keyboard = [
                [InlineKeyboardButton("🖼 Profile Picture", callback_data="user_profile")],
                [InlineKeyboardButton("💬 Message", callback_data="user_message")]
            ]
            await update.message.reply_text(
                "What do you want to report about this user?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return self.REPORT_USER_OPTION
        else:
            keyboard = [
                [InlineKeyboardButton(f"📢 Report entire {target_type}", callback_data="entity_whole")],
                [InlineKeyboardButton("💬 Report a specific message", callback_data="entity_message")]
            ]
            await update.message.reply_text(
                f"What would you like to report?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return self.REPORT_ENTITY_OPTION

    async def report_user_option_cb(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        option = query.data
        sess = self.user_sessions.get(user_id)
        if not sess:
            await query.edit_message_text("Session expired.")
            return self.MAIN
        sess["user_option"] = option
        if option == "user_message":
            await query.edit_message_text(
                "Please send the link to the specific message.\n"
                "Example: https://t.me/username/123"
            )
            return self.REPORT_MESSAGE_LINK
        else:
            return await self._show_categories(query, user_id)

    async def report_entity_option_cb(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        option = query.data
        sess = self.user_sessions.get(user_id)
        if not sess:
            await query.edit_message_text("Session expired.")
            return self.MAIN
        sess["entity_option"] = option
        if option == "entity_message":
            await query.edit_message_text(
                "Please send the link to the specific message.\n"
                "Example: https://t.me/channel/123"
            )
            return self.REPORT_MESSAGE_LINK
        else:
            return await self._show_categories(query, user_id)

    async def report_message_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        link = update.message.text.strip()
        match = re.search(r't\.me/([^/]+)/(\d+)', link)
        if not match:
            await update.message.reply_text("Invalid message link. Please provide a valid t.me link.")
            return self.REPORT_MESSAGE_LINK
        chat = match.group(1)
        msg_id = int(match.group(2))
        sess = self.user_sessions.get(user_id)
        if not sess:
            await update.message.reply_text("Session expired.")
            return self.MAIN
        sess["message_chat"] = chat
        sess["message_id"] = msg_id
        return await self._show_categories(update.message, user_id, via_message=True)

    async def _show_categories(self, target, user_id, via_message=False):
        keyboard = []
        categories = [
            ("spam", "Spam"),
            ("violence", "Violence"),
            ("pornography", "Pornography"),
            ("child_abuse", "Child Abuse"),
            ("illegal_drugs", "Illegal Drugs"),
            ("personal_details", "Personal Details"),
            ("copyright", "Copyright"),
            ("other", "Other")
        ]
        for value, label in categories:
            keyboard.append([InlineKeyboardButton(label, callback_data=f"cat_{value}")])
        markup = InlineKeyboardMarkup(keyboard)
        if via_message:
            await target.reply_text("Select the violation category:", reply_markup=markup)
        else:
            await target.edit_message_text("Select the violation category:", reply_markup=markup)
        return self.REPORT_CATEGORY

    async def report_category_cb(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        category = query.data.split('_')[1]
        sess = self.user_sessions.get(user_id)
        if not sess:
            await query.edit_message_text("Session expired.")
            return self.MAIN
        sess["category"] = category
        await query.edit_message_text(
            "Please provide a detailed description of the violation (minimum 20 characters)."
        )
        return self.REPORT_DESCRIPTION

    async def report_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        description = update.message.text.strip()
        if len(description) < 20:
            await update.message.reply_text("Description must be at least 20 characters. Please try again.")
            return self.REPORT_DESCRIPTION
        sess = self.user_sessions.get(user_id)
        if not sess:
            await update.message.reply_text("Session expired.")
            return self.MAIN
        target = sess["target"]
        target_type = sess["target_type"]
        category = sess["category"]
        if target_type == "user" and sess.get("user_option") == "user_profile":
            job_type = "profile"
        elif sess.get("user_option") == "user_message" or sess.get("entity_option") == "entity_message":
            job_type = "message"
        else:
            job_type = "entity"
        message_chat = sess.get("message_chat")
        message_id = sess.get("message_id")

        success, msg, job_id = await self.reporting_engine.create_job(
            target=target,
            target_type=target_type,
            job_type=job_type,
            category=category,
            description=description,
            user_id=user_id,
            message_chat=message_chat,
            message_id=message_id
        )
        if success:
            await update.message.reply_text(f"✅ Report job created! Job ID: {job_id}\nProcessing started...")
            asyncio.create_task(self.reporting_engine.process_job(job_id))
            await self._log(f"📝 Job {job_id} created by {user_id} for {target}")
        else:
            await update.message.reply_text(f"❌ Failed to create job: {msg}")
        self.user_sessions.pop(user_id, None)
        return self.MAIN

    # -------------------- Job List --------------------
    async def jobs_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        cursor = db.jobs.find({"created_by": user_id}).sort("created_at", -1).limit(10)
        jobs = await cursor.to_list(length=10)
        if not jobs:
            await update.message.reply_text("You have no recent jobs.")
            return
        text = "📋 **Your Recent Jobs**\n\n"
        for job in jobs:
            job = ReportJob.from_dict(job)
            text += f"• `{job.job_id}` - {job.target_type} - {job.status} - {job.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # -------------------- Admin Commands --------------------
    async def refresh_proxies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.has_permission(user_id, UserRole.ADMIN):
            await update.message.reply_text("Admin only.")
            return
        await update.message.reply_text("Refreshing proxy pool...")
        asyncio.create_task(self._do_refresh_proxies(update))

    async def _do_refresh_proxies(self, update: Update):
        try:
            async with Client("proxy_fetcher", api_id=Config.API_ID, api_hash=Config.API_HASH) as temp_client:
                await temp_client.start()
                proxies = await fetch_proxies_from_channel(temp_client)
                for proxy in proxies:
                    await db.proxies.update_one(
                        {"proxy": proxy},
                        {"$set": {"proxy": proxy, "last_seen": datetime.now().isoformat()}},
                        upsert=True
                    )
            await update.effective_message.reply_text(f"✅ Proxy pool refreshed. {len(proxies)} proxies stored.")
        except Exception as e:
            await update.effective_message.reply_text(f"❌ Refresh failed: {e}")

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.user_manager.has_permission(user_id, UserRole.ADMIN):
            await update.message.reply_text("Admin only.")
            return
        total_accounts = await db.accounts.count_documents({})
        active_accounts = await db.accounts.count_documents({"status": AccountStatus.ACTIVE})
        total_users = await db.users.count_documents({})
        total_jobs = await db.jobs.count_documents({})
        text = (
            f"📊 **Bot Statistics**\n\n"
            f"Accounts: {total_accounts} (active: {active_accounts})\n"
            f"Users: {total_users}\n"
            f"Jobs: {total_jobs}\n"
            f"Proxies in pool: {await db.proxies.count_documents({})}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    # -------------------- Help --------------------
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "/start - Welcome\n"
            "/addaccount - Add a Telegram account\n"
            "/accounts - List accounts\n"
            "/removeaccount - Remove an account\n"
            "/report - Report a user/group/channel\n"
            "/jobs - List your report jobs\n"
            "/refreshproxies - Refresh proxy list (admin)\n"
            "/stats - Bot statistics (admin)\n"
            "/help - This message"
        )
        await update.message.reply_text(help_text)

    # -------------------- Cancel --------------------
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self.user_sessions.pop(user_id, None)
        await update.message.reply_text("Operation cancelled.")
        return self.MAIN

# ==================== MAIN APPLICATION ====================
class TelegramEnterpriseBot:
    def __init__(self):
        self.user_manager = UserManager()
        self.account_manager = AccountManager()
        self.reporting_engine = ReportingEngine(self.account_manager)
        self.bot_handler = BotHandler(self.user_manager, self.account_manager, self.reporting_engine)
        self.application = None

    async def initialize(self):
        # Start proxy refresh task
        asyncio.create_task(refresh_proxy_pool())
        logger.info("Bot initialized.")

    def run(self):
        # Build application
        app = Application.builder().token(Config.BOT_TOKEN).build()
        self.application = app
        self.bot_handler.application = app

        # Conversation handler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.bot_handler.start),
                CommandHandler("addaccount", self.bot_handler.add_account_start),
                CommandHandler("report", self.bot_handler.report_start),
                CommandHandler("accounts", self.bot_handler.accounts_list),
                CommandHandler("removeaccount", self.bot_handler.remove_account_start),
                CommandHandler("jobs", self.bot_handler.jobs_list),
                CommandHandler("refreshproxies", self.bot_handler.refresh_proxies),
                CommandHandler("stats", self.bot_handler.stats),
                CommandHandler("help", self.bot_handler.help),
            ],
            states={
                self.bot_handler.MAIN: [
                    CommandHandler("addaccount", self.bot_handler.add_account_start),
                    CommandHandler("report", self.bot_handler.report_start),
                    CommandHandler("accounts", self.bot_handler.accounts_list),
                    CommandHandler("removeaccount", self.bot_handler.remove_account_start),
                    CommandHandler("jobs", self.bot_handler.jobs_list),
                    CommandHandler("refreshproxies", self.bot_handler.refresh_proxies),
                    CommandHandler("stats", self.bot_handler.stats),
                    CommandHandler("help", self.bot_handler.help),
                    CallbackQueryHandler(self.bot_handler.remove_account_callback, pattern="^del_"),
                ],
                self.bot_handler.ADD_PHONE: [MessageHandler(tfilters.TEXT & ~tfilters.COMMAND, self.bot_handler.add_account_phone)],
                self.bot_handler.ADD_OTP: [MessageHandler(tfilters.TEXT & ~tfilters.COMMAND, self.bot_handler.add_account_otp)],
                self.bot_handler.ADD_2FA: [MessageHandler(tfilters.TEXT & ~tfilters.COMMAND, self.bot_handler.add_account_2fa)],
                self.bot_handler.REPORT_TARGET_TYPE: [CallbackQueryHandler(self.bot_handler.report_target_type_cb, pattern="^target_")],
                self.bot_handler.REPORT_TARGET: [MessageHandler(tfilters.TEXT & ~tfilters.COMMAND, self.bot_handler.report_target)],
                self.bot_handler.REPORT_USER_OPTION: [CallbackQueryHandler(self.bot_handler.report_user_option_cb, pattern="^user_")],
                self.bot_handler.REPORT_MESSAGE_LINK: [MessageHandler(tfilters.TEXT & ~tfilters.COMMAND, self.bot_handler.report_message_link)],
                self.bot_handler.REPORT_ENTITY_OPTION: [CallbackQueryHandler(self.bot_handler.report_entity_option_cb, pattern="^entity_")],
                self.bot_handler.REPORT_CATEGORY: [CallbackQueryHandler(self.bot_handler.report_category_cb, pattern="^cat_")],
                self.bot_handler.REPORT_DESCRIPTION: [MessageHandler(tfilters.TEXT & ~tfilters.COMMAND, self.bot_handler.report_description)],
            },
            fallbacks=[CommandHandler("cancel", self.bot_handler.cancel)],
            per_chat=True,
        )
        app.add_handler(conv_handler)

        # Also handle non-command messages (like cancel in any state is handled by fallback)
        logger.info("Starting bot polling...")
        app.run_polling()

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    try:
        Config.validate()
        bot = TelegramEnterpriseBot()
        asyncio.run(bot.initialize())
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.exception("Fatal error")
