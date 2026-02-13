#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Enterprise Reporting Bot
- Uses Pyrogram for Telegram client API
- Sessions stored in MongoDB
- Proxies fetched from @ProxyMTProto channel
- Rotates proxy after 9 reports per account
- Reports users, groups, channels, messages, and profile pictures
- Logs bot messages to a specified group
"""

import asyncio
import logging
import re
import time
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse

import pymongo
from pymongo.collection import Collection
from pyrogram import Client, filters, enums
from pyrogram.raw import functions, types
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired,
    FloodWait, PhoneNumberBanned, PhoneNumberUnoccupied, ApiIdInvalid
)
from pyrogram.storage import Storage
import pyrogram.utils

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters as tfilters, ConversationHandler, ContextTypes
)

# ==================== CONFIGURATION ====================
API_ID = 27157163
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
MONGO_URL = "mongodb+srv://Capture:capture@cluster0.7jqepnf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
LOG_GROUP_ID = -1003662481087  # Group where bot messages are logged
OWNER_IDS = [6118760915, 1366105247]  # Add your owner IDs

# Proxy source channel
PROXY_CHANNEL = "ProxyMTProto"

# Maximum reports per account before proxy rotation
MAX_REPORTS_PER_PROXY = 9

# ==================== MongoDB SETUP ====================
mongo_client = pymongo.MongoClient(MONGO_URL)
db = mongo_client["telegram_bot"]
sessions_collection = db["pyrogram_sessions"]  # Stores session strings
accounts_collection = db["accounts"]            # Stores account metadata
users_collection = db["users"]                  # Bot users
jobs_collection = db["jobs"]                    # Report jobs
proxies_collection = db["proxies"]              # Cached proxies

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CUSTOM PYROGRAM STORAGE ====================
class MongoStorage(Storage):
    """
    Stores Pyrogram session data in MongoDB.
    """
    def __init__(self, name: str, collection: Collection):
        super().__init__(name)
        self.collection = collection
        self.data = {}

    async def open(self):
        doc = self.collection.find_one({"_id": self.name})
        if doc:
            self.data = doc.get("data", {})
        else:
            self.data = {}

    async def save(self):
        self.collection.update_one(
            {"_id": self.name},
            {"$set": {"data": self.data}},
            upsert=True
        )

    async def close(self):
        pass

    async def delete(self):
        self.collection.delete_one({"_id": self.name})

    # Required storage methods
    async def set_dc(self, dc_id: int, auth_key: bytes):
        self.data["dc_id"] = dc_id
        self.data["auth_key"] = auth_key.hex() if auth_key else None
        await self.save()

    async def get_dc(self) -> Tuple[int, bytes]:
        dc_id = self.data.get("dc_id")
        auth_key_hex = self.data.get("auth_key")
        auth_key = bytes.fromhex(auth_key_hex) if auth_key_hex else None
        return dc_id, auth_key

    async def set_user(self, user):
        self.data["user"] = user.write() if user else None
        await self.save()

    async def get_user(self):
        data = self.data.get("user")
        if data:
            return types.User.read(data)
        return None

    async def update_peers(self, peers):
        for peer in peers:
            self.data[f"peer_{peer.id}"] = peer.write()
        await self.save()

    async def get_peer_by_id(self, peer_id: int):
        data = self.data.get(f"peer_{peer_id}")
        if data:
            return pyrogram.utils.get_peer(types.Peer read(data))  # Simplified
        return None

    # ... other methods (get_peer_by_username, get_peer_by_phone) can be added if needed

# ==================== PROXY FETCHER ====================
async def fetch_proxies_from_channel(client: Client, limit: int = 50) -> List[str]:
    """
    Fetch proxy strings from the @ProxyMTProto channel.
    Returns list of proxy URLs.
    """
    proxies = []
    try:
        chat = await client.get_chat(PROXY_CHANNEL)
        async for msg in client.get_chat_history(chat.id, limit=limit):
            if msg.text:
                # Find all proxy links in the message
                found = re.findall(r'(socks5://[^\s]+|mtproto://[^\s]+)', msg.text)
                proxies.extend(found)
        # Remove duplicates
        proxies = list(set(proxies))
        logger.info(f"Fetched {len(proxies)} proxies from {PROXY_CHANNEL}")
    except Exception as e:
        logger.error(f"Failed to fetch proxies: {e}")
    return proxies

def parse_proxy(proxy_str: str) -> Optional[Dict]:
    """
    Convert proxy string to Pyrogram proxy dict.
    Supports socks5:// and mtproto://.
    """
    try:
        parsed = urlparse(proxy_str)
        if parsed.scheme == 'mtproto':
            # MTProto proxy: secret is in query
            secret = parsed.query.split('=')[-1] if parsed.query else ''
            return {
                'scheme': 'mtproto',
                'hostname': parsed.hostname,
                'port': parsed.port,
                'secret': secret
            }
        else:
            # SOCKS5 proxy
            return {
                'scheme': parsed.scheme,
                'hostname': parsed.hostname,
                'port': parsed.port,
                'username': parsed.username,
                'password': parsed.password
            }
    except Exception:
        return None

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
    client: Optional[Client] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    report_count: int = 0
    total_reports: int = 0
    last_report_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    otp_data: Optional[Dict] = None

    def to_dict(self):
        return {
            "phone": self.phone,
            "session_name": self.session_name,
            "proxy": self.proxy,
            "proxy_index": self.proxy_index,
            "status": self.status,
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "report_count": self.report_count,
            "total_reports": self.total_reports,
            "last_report_time": self.last_report_time.isoformat() if self.last_report_time else None,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    @classmethod
    def from_dict(cls, data):
        acc = cls(
            phone=data["phone"],
            session_name=data["session_name"],
            proxy=data.get("proxy"),
            proxy_index=data.get("proxy_index", 0),
            status=data.get("status", AccountStatus.UNVERIFIED),
            user_id=data.get("user_id"),
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            report_count=data.get("report_count", 0),
            total_reports=data.get("total_reports", 0)
        )
        if data.get("last_report_time"):
            acc.last_report_time = datetime.fromisoformat(data["last_report_time"])
        if data.get("created_at"):
            acc.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_login"):
            acc.last_login = datetime.fromisoformat(data["last_login"])
        return acc

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
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role,
            "reports_made": self.reports_made,
            "joined_at": self.joined_at.isoformat(),
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }

    @classmethod
    def from_dict(cls, data):
        user = cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            role=data.get("role", UserRole.USER),
            reports_made=data.get("reports_made", 0)
        )
        if data.get("joined_at"):
            user.joined_at = datetime.fromisoformat(data["joined_at"])
        if data.get("last_active"):
            user.last_active = datetime.fromisoformat(data["last_active"])
        return user

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
        return {
            "job_id": self.job_id,
            "target": self.target,
            "target_type": self.target_type,
            "job_type": self.job_type,
            "category": self.category,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "accounts_used": self.accounts_used,
            "results": self.results,
            "message_chat": self.message_chat,
            "message_id": self.message_id,
        }

# ==================== ACCOUNT MANAGER ====================
class AccountManager:
    def __init__(self):
        self.accounts: Dict[str, TelegramAccount] = {}
        self.proxy_pool: List[str] = []
        self.load_accounts()

    def load_accounts(self):
        """Load accounts from MongoDB."""
        for doc in accounts_collection.find():
            acc = TelegramAccount.from_dict(doc)
            self.accounts[acc.phone] = acc

    def save_account(self, account: TelegramAccount):
        """Save or update an account in MongoDB."""
        accounts_collection.update_one(
            {"phone": account.phone},
            {"$set": account.to_dict()},
            upsert=True
        )

    async def fetch_proxies(self, client: Client):
        """Fetch proxies from channel and store in pool."""
        self.proxy_pool = await fetch_proxies_from_channel(client)
        # Also cache in MongoDB
        proxies_collection.update_one(
            {"_id": "proxy_pool"},
            {"$set": {"proxies": self.proxy_pool, "updated": datetime.now().isoformat()}},
            upsert=True
        )

    def get_next_proxy(self, account: TelegramAccount) -> Optional[str]:
        """Return next proxy for account (round-robin)."""
        if not self.proxy_pool:
            return None
        idx = account.proxy_index % len(self.proxy_pool)
        account.proxy_index += 1
        return self.proxy_pool[idx]

    async def create_client(self, phone: str, proxy: Optional[str] = None) -> Tuple[Client, bool]:
        """
        Create a Pyrogram client for the phone, using MongoDB storage.
        Returns (client, is_authorized).
        """
        session_name = phone.replace('+', '')
        storage = MongoStorage(session_name, sessions_collection)
        proxy_dict = parse_proxy(proxy) if proxy else None
        client = Client(
            name=session_name,
            api_id=API_ID,
            api_hash=API_HASH,
            proxy=proxy_dict,
            storage=storage,
            in_memory=True
        )
        await client.connect()
        authorized = await client.is_user_authorized()
        return client, authorized

    async def add_account(self, phone: str, proxy: Optional[str] = None) -> Tuple[bool, str, Optional[Client]]:
        """Initiate adding a new account."""
        if phone in self.accounts:
            return False, "Account already exists", None
        client, authorized = await self.create_client(phone, proxy)
        account = TelegramAccount(
            phone=phone,
            session_name=phone.replace('+', ''),
            proxy=proxy,
            client=client,
            status=AccountStatus.ACTIVE if authorized else AccountStatus.UNVERIFIED
        )
        if authorized:
            # Already logged in, fetch info
            await self._update_account_info(account, client)
        self.accounts[phone] = account
        self.save_account(account)
        return True, "Account added", client

    async def _update_account_info(self, account: TelegramAccount, client: Client):
        """Fetch and store account details from Telegram."""
        try:
            me = await client.get_me()
            account.user_id = me.id
            account.username = me.username
            account.first_name = me.first_name
            account.last_name = me.last_name
            account.status = AccountStatus.ACTIVE
            account.last_login = datetime.now()
            self.save_account(account)
        except Exception as e:
            logger.error(f"Failed to update account info for {account.phone}: {e}")

    async def send_otp(self, phone: str, client: Client) -> Tuple[bool, str]:
        """Send OTP code to the phone."""
        try:
            sent = await client.send_code(phone)
            # Store phone_code_hash in account for later verification
            acc = self.accounts.get(phone)
            if acc:
                acc.otp_data = {"phone_code_hash": sent.phone_code_hash}
                acc.status = AccountStatus.VERIFYING
                self.save_account(acc)
            return True, "OTP sent"
        except FloodWait as e:
            return False, f"Flood wait: {e.value} seconds"
        except Exception as e:
            return False, str(e)

    async def verify_otp(self, phone: str, code: str) -> Tuple[bool, str, Optional[Client]]:
        """Verify OTP code and complete login."""
        acc = self.accounts.get(phone)
        if not acc or not acc.client:
            return False, "Account not found or client missing", None
        client = acc.client
        try:
            await client.sign_in(phone, code)
            await self._update_account_info(acc, client)
            return True, "Login successful", client
        except SessionPasswordNeeded:
            acc.status = AccountStatus.NEED_PASSWORD
            self.save_account(acc)
            return False, "2FA required", client
        except (PhoneCodeInvalid, PhoneCodeExpired) as e:
            return False, f"Invalid code: {e}", client
        except Exception as e:
            return False, str(e), client

    async def verify_2fa(self, phone: str, password: str) -> Tuple[bool, str]:
        """Verify 2FA password."""
        acc = self.accounts.get(phone)
        if not acc or not acc.client:
            return False, "Account not found"
        try:
            await acc.client.check_password(password)
            await self._update_account_info(acc, acc.client)
            return True, "2FA verified"
        except Exception as e:
            return False, str(e)

    async def rotate_proxy(self, phone: str) -> Tuple[bool, str]:
        """Rotate proxy for an account (after 9 reports)."""
        acc = self.accounts.get(phone)
        if not acc:
            return False, "Account not found"
        new_proxy = self.get_next_proxy(acc)
        if not new_proxy:
            return False, "No proxies available"
        # Stop old client
        if acc.client:
            await acc.client.stop()
        # Create new client with new proxy
        client, authorized = await self.create_client(phone, new_proxy)
        if not authorized:
            # Should not happen if session is valid
            return False, "Session lost after proxy change"
        acc.client = client
        acc.proxy = new_proxy
        acc.report_count = 0
        self.save_account(acc)
        return True, f"Proxy rotated to {new_proxy}"

    async def get_proxy_country(self, proxy: str) -> str:
        """Get country of proxy by IP geolocation."""
        try:
            import aiohttp
            # Extract host from proxy string
            if '@' in proxy:
                host = proxy.split('@')[1].split(':')[0]
            else:
                host = proxy.split('://')[1].split(':')[0] if '://' in proxy else proxy.split(':')[0]
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://ip-api.com/json/{host}") as resp:
                    data = await resp.json()
                    return data.get('country', 'Unknown')
        except:
            return "Unknown"

# ==================== REPORTING ENGINE ====================
class ReportingEngine:
    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
        self.active_jobs: Dict[str, ReportJob] = {}

    # Report reasons mapping for Pyrogram raw API
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
        """Create a new report job."""
        import uuid
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
        # Save to MongoDB
        jobs_collection.insert_one(job.to_dict())
        return True, "Job created", job_id

    async def process_job(self, job_id: str):
        """Process a report job using available accounts."""
        job = self.active_jobs.get(job_id)
        if not job:
            return
        job.status = "processing"
        # Get up to 3 active accounts
        accounts = [acc for acc in self.account_manager.accounts.values()
                    if acc.status == AccountStatus.ACTIVE][:3]
        if not accounts:
            job.status = "failed"
            job.results.append({"error": "No active accounts"})
            self._finish_job(job)
            return

        # For each account, perform the report
        for acc in accounts:
            # Check if need proxy rotation
            if acc.report_count >= MAX_REPORTS_PER_PROXY:
                rotated, msg = await self.account_manager.rotate_proxy(acc.phone)
                if not rotated:
                    job.results.append({"account": acc.phone, "error": f"Proxy rotation failed: {msg}"})
                    continue
            # Execute report
            result = await self._report_with_account(acc, job)
            job.results.append(result)
            job.accounts_used.append(acc.phone)
            if result.get("success"):
                acc.report_count += 1
                acc.total_reports += 1
                acc.last_report_time = datetime.now()
                self.account_manager.save_account(acc)
        # Determine overall status
        successes = [r for r in job.results if r.get("success")]
        job.status = "completed" if successes else "failed"
        self._finish_job(job)

    async def _report_with_account(self, account: TelegramAccount, job: ReportJob) -> Dict:
        """Perform report using a specific account."""
        client = account.client
        if not client or not client.is_connected:
            return {"account": account.phone, "success": False, "error": "Client not connected"}
        try:
            # Resolve target
            if job.target_type == "user":
                peer = await client.resolve_peer(job.target)
            elif job.target_type in ["group", "channel"]:
                peer = await client.resolve_peer(job.target)
            else:
                return {"account": account.phone, "success": False, "error": "Unknown target type"}

            reason = self.REASON_MAP.get(job.category.lower(), types.InputReportReasonOther())

            if job.job_type == "message":
                # Report a specific message
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
                # Check if user has profile picture
                photos = await client.get_chat_photos(job.target)
                if not photos:
                    return {"account": account.phone, "success": False, "error": "No profile picture"}
                # Report the user (there's no direct profile pic report, so we report user with description)
                await client.invoke(
                    functions.account.ReportPeer(
                        peer=peer,
                        reason=reason,
                        message=job.description
                    )
                )
                return {"account": account.phone, "success": True, "type": "profile"}

            else:  # entity (user/group/channel itself)
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

    def _finish_job(self, job: ReportJob):
        """Finalize job and update DB."""
        jobs_collection.update_one({"job_id": job.job_id}, {"$set": job.to_dict()})
        if job.job_id in self.active_jobs:
            del self.active_jobs[job.job_id]

# ==================== USER MANAGER ====================
class UserManager:
    def __init__(self):
        self.users: Dict[int, BotUser] = {}
        self.load_users()

    def load_users(self):
        for doc in users_collection.find():
            user = BotUser.from_dict(doc)
            self.users[user.user_id] = user

    def save_user(self, user: BotUser):
        users_collection.update_one(
            {"user_id": user.user_id},
            {"$set": user.to_dict()},
            upsert=True
        )

    def get_or_create(self, user_id: int, username: str = None,
                      first_name: str = None, last_name: str = None) -> BotUser:
        if user_id in self.users:
            user = self.users[user_id]
            user.last_active = datetime.now()
            # Update name if changed
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
        else:
            user = BotUser(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.OWNER if user_id in OWNER_IDS else UserRole.USER
            )
            self.users[user_id] = user
        self.save_user(user)
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
        self.user_sessions = {}  # temp storage per user

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        bot_user = self.user_manager.get_or_create(
            user.id, user.username, user.first_name, user.last_name
        )
        await self._send_log(f"User {user.id} (@{user.username}) started the bot.")
        await update.message.reply_text(
            f"👋 Hello {user.first_name}!\n"
            f"Your role: {bot_user.role}\n\n"
            "Commands:\n"
            "/addaccount - Add a new Telegram account\n"
            "/report - Report a user/group/channel\n"
            "/accounts - List my accounts\n"
            "/help - Show help"
        )
        return self.MAIN

    async def add_account_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start account addition process."""
        await update.message.reply_text(
            "Please send the phone number in international format:\n"
            "Example: `+1234567890`"
        )
        return self.ADD_PHONE

    async def add_account_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive phone number, create client, send OTP."""
        phone = update.message.text.strip()
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text("Invalid phone number. Use format +1234567890")
            return self.ADD_PHONE

        # Assign a proxy from pool (round-robin)
        proxy = self.account_manager.get_next_proxy(None) if self.account_manager.proxy_pool else None
        success, msg, client = await self.account_manager.add_account(phone, proxy)
        if not success:
            await update.message.reply_text(f"Error: {msg}")
            return self.MAIN

        if client and not await client.is_user_authorized():
            # Send OTP
            ok, msg = await self.account_manager.send_otp(phone, client)
            if not ok:
                await update.message.reply_text(f"Failed to send OTP: {msg}")
                return self.MAIN
            # Store phone in session for later OTP input
            self.user_sessions[update.effective_user.id] = {"phone": phone}
            await update.message.reply_text(
                "OTP sent to your phone. Please enter the 5-digit code."
            )
            return self.ADD_OTP
        else:
            # Already authorized
            country = await self.account_manager.get_proxy_country(proxy) if proxy else "Unknown"
            await update.message.reply_text(
                f"Account already logged in.\nProxy country: {country}"
            )
            return self.MAIN

    async def add_account_otp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Verify OTP code."""
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
            # Get proxy country
            acc = self.account_manager.accounts.get(phone)
            country = await self.account_manager.get_proxy_country(acc.proxy) if acc.proxy else "Unknown"
            await update.message.reply_text(
                f"✅ Login successful!\nProxy country: {country}\nReports today: 0/{MAX_REPORTS_PER_PROXY}"
            )
            await self._send_log(f"Account {phone} added successfully. Proxy: {acc.proxy}")
            # Clear session
            self.user_sessions.pop(user_id, None)
            return self.MAIN
        elif msg == "2FA required":
            # Store that 2FA is needed
            self.user_sessions[user_id] = {"phone": phone, "need_2fa": True}
            await update.message.reply_text(
                "This account has 2FA enabled. Please enter your password."
            )
            return self.ADD_2FA
        else:
            await update.message.reply_text(f"Verification failed: {msg}")
            return self.ADD_OTP

    async def add_account_2fa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle 2FA password."""
        password = update.message.text.strip()
        user_id = update.effective_user.id
        phone = self.user_sessions.get(user_id, {}).get("phone")
        if not phone:
            await update.message.reply_text("Session expired.")
            return self.MAIN
        success, msg = await self.account_manager.verify_2fa(phone, password)
        if success:
            acc = self.account_manager.accounts.get(phone)
            country = await self.account_manager.get_proxy_country(acc.proxy) if acc.proxy else "Unknown"
            await update.message.reply_text(
                f"✅ 2FA verified! Account ready.\nProxy country: {country}"
            )
            await self._send_log(f"Account {phone} added with 2FA. Proxy: {acc.proxy}")
        else:
            await update.message.reply_text(f"2FA failed: {msg}")
            return self.ADD_2FA
        self.user_sessions.pop(user_id, None)
        return self.MAIN

    async def report_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start report conversation."""
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
        target_type = query.data.split('_')[1]  # user, group, channel
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
            # Group or channel: ask entity or message
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
        option = query.data  # user_profile or user_message
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
            # For profile, proceed to category selection
            return await self._show_categories(query, user_id)

    async def report_entity_option_cb(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        option = query.data  # entity_whole or entity_message
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
        # Extract chat and message id
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
        """Show category selection keyboard."""
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
        # Create job
        target = sess["target"]
        target_type = sess["target_type"]
        category = sess["category"]
        # Determine job_type
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
            # Process the job asynchronously
            asyncio.create_task(self.reporting_engine.process_job(job_id))
        else:
            await update.message.reply_text(f"❌ Failed to create job: {msg}")
        # Clear session
        self.user_sessions.pop(user_id, None)
        return self.MAIN

    async def accounts_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all accounts added by the user (simplified: show all accounts)."""
        if not self.account_manager.accounts:
            await update.message.reply_text("No accounts added yet.")
            return
        text = "📱 **Your Accounts**\n\n"
        for phone, acc in self.account_manager.accounts.items():
            status_icon = "🟢" if acc.status == AccountStatus.ACTIVE else "🔴"
            text += f"{status_icon} `{phone}` - {acc.status}\n"
        await update.message.reply_text(text, parse_mode="Markdown")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "/start - Welcome\n"
            "/addaccount - Add a Telegram account\n"
            "/report - Report a user/group/channel\n"
            "/accounts - List accounts\n"
            "/help - This message"
        )
        await update.message.reply_text(help_text)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current conversation."""
        user_id = update.effective_user.id
        self.user_sessions.pop(user_id, None)
        await update.message.reply_text("Operation cancelled.")
        return self.MAIN

    async def _send_log(self, text: str):
        """Send a log message to the designated group."""
        try:
            await self.application.bot.send_message(LOG_GROUP_ID, text)
        except Exception as e:
            logger.error(f"Failed to send log: {e}")

# ==================== MAIN APPLICATION ====================
class TelegramEnterpriseBot:
    def __init__(self):
        self.user_manager = UserManager()
        self.account_manager = AccountManager()
        self.reporting_engine = ReportingEngine(self.account_manager)
        self.bot_handler = BotHandler(self.user_manager, self.account_manager, self.reporting_engine)
        self.application = None

    async def initialize(self):
        """Initialize bot components."""
        # Fetch proxies using a temporary client (or use bot's own client)
        # We'll use a separate client for proxy fetching
        temp_client = Client("proxy_fetcher", api_id=API_ID, api_hash=API_HASH)
        await temp_client.start()
        await self.account_manager.fetch_proxies(temp_client)
        await temp_client.stop()
        logger.info(f"Proxy pool: {len(self.account_manager.proxy_pool)} proxies")

    def run(self):
        """Start the bot."""
        # Build application
        app = Application.builder().token(BOT_TOKEN).build()
        self.application = app
        self.bot_handler.application = app  # for logging

        # Add conversation handlers
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.bot_handler.start),
                CommandHandler("addaccount", self.bot_handler.add_account_start),
                CommandHandler("report", self.bot_handler.report_start),
                CommandHandler("accounts", self.bot_handler.accounts_list),
                CommandHandler("help", self.bot_handler.help),
            ],
            states={
                self.bot_handler.MAIN: [
                    CommandHandler("addaccount", self.bot_handler.add_account_start),
                    CommandHandler("report", self.bot_handler.report_start),
                    CommandHandler("accounts", self.bot_handler.accounts_list),
                    CommandHandler("help", self.bot_handler.help),
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
        )
        app.add_handler(conv_handler)

        # Run bot
        logger.info("Bot started.")
        app.run_polling()

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    bot = TelegramEnterpriseBot()
    asyncio.run(bot.initialize())
    bot.run()
