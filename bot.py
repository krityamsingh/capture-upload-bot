#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ULTIMATE TELEGRAM ENTERPRISE REPORTING SYSTEM v11.0
Converted to Pyrogram
"""

# ============================================
# STANDARD LIBRARY IMPORTS (Keep as is)
# ============================================
import asyncio
import csv
import hashlib
import io
import json
import logging
import random
import re
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# ============================================
# THIRD-PARTY IMPORTS (Keep as is)
# ============================================
import aiohttp
import certifi
import pytz
import backoff
import numpy as np
from rich.console import Console

# ============================================
# PYROGRAM IMPORTS (Replace Telethon/telegram)
# ============================================
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, User, Chat, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, WebAppInfo
)
from pyrogram.errors import (
    FloodWait, PhoneNumberInvalid, PhoneCodeInvalid,
    PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid,
    PhoneNumberBanned, PhoneNumberFlood, PhoneNumberUnoccupied,
    BadRequest, Unauthorized, NotAcceptable
)
from pyrogram.enums import ParseMode, ChatType, ChatMemberStatus, MessageMediaType

# ============================================
# CONFIGURATION (Keep as is)
# ============================================
BOT_TOKEN = "7813598075:AAFUrbGZfBeRiZb1H1MOBULU_ed69OSTwzY"
API_ID = 27157163
API_HASH = "e0145db12519b08e1d2f5628e2db18c4"
OWNER_IDS = [6118760915, 1366105247]

# ============================================
# ENHANCED DATA MODELS (Keep as is)
# ============================================
# Keep your existing data models (UserRole, AccountStatus, etc.)
# They don't depend on the Telegram library

# ============================================
# ADVANCED PROXY MANAGER (Adapt for Pyrogram)
# ============================================
class AdvancedProxyManager:
    def __init__(self):
        # Keep your existing proxy management logic
        # Update proxy format for Pyrogram
        pass
    
    def format_proxy_for_pyrogram(self, proxy_str: str) -> Optional[Dict]:
        """Format proxy string for Pyrogram"""
        if not proxy_str:
            return None
        
        try:
            proxy_lower = proxy_str.lower()
            
            if proxy_lower.startswith('socks5://'):
                protocol = "socks5"
                proxy_str = proxy_str[9:]
            elif proxy_lower.startswith('socks4://'):
                protocol = "socks4"
                proxy_str = proxy_str[9:]
            elif proxy_lower.startswith('https://'):
                protocol = "http"  # Pyrogram uses "http" for HTTPS
                proxy_str = proxy_str[8:]
            elif proxy_lower.startswith('http://'):
                protocol = "http"
                proxy_str = proxy_str[7:]
            else:
                protocol = "http"
            
            # Parse host and port
            if '@' in proxy_str:
                # Has authentication
                auth, hostport = proxy_str.split('@', 1)
                username, password = auth.split(':', 1)
                host, port = hostport.split(':', 1)
                
                return {
                    "scheme": protocol,
                    "hostname": host,
                    "port": int(port),
                    "username": username,
                    "password": password
                }
            else:
                # No authentication
                host, port = proxy_str.split(':', 1)
                return {
                    "scheme": protocol,
                    "hostname": host,
                    "port": int(port)
                }
                
        except Exception as e:
            console.print(f"[red]❌ Error parsing proxy: {e}[/red]")
            return None

# ============================================
# ADVANCED ACCOUNT MANAGER (Converted to Pyrogram)
# ============================================
class AdvancedAccountManager:
    def __init__(self, proxy_manager):
        self.accounts = {}
        self.proxy_manager = proxy_manager
        self.clients = {}  # Store Pyrogram clients
    
    async def create_pyrogram_client(self, phone: str, session_file: str, 
                                   proxy: Optional[str] = None) -> Optional[Client]:
        """Create a Pyrogram client for an account"""
        try:
            # Get proxy dict for Pyrogram
            proxy_dict = None
            if proxy:
                proxy_dict = self.proxy_manager.format_proxy_for_pyrogram(proxy)
            
            # Create client with enhanced configuration
            client = Client(
                name=session_file,
                api_id=API_ID,
                api_hash=API_HASH,
                app_version="4.0.0",
                device_model="Desktop",
                system_version="Windows 10",
                lang_code="en",
                proxy=proxy_dict
            )
            
            return client
            
        except Exception as e:
            console.print(f"[red]❌ Error creating Pyrogram client: {e}[/red]")
            return None
    
    async def start_session(self, phone: str) -> Tuple[bool, str]:
        """Start a Pyrogram session for an account"""
        if phone not in self.accounts:
            return False, "Account not found"
        
        account = self.accounts[phone]
        
        try:
            # Create or get client
            if phone not in self.clients:
                client = await self.create_pyrogram_client(
                    phone, str(account.session_file), account.proxy
                )
                if not client:
                    return False, "Failed to create client"
                self.clients[phone] = client
            
            client = self.clients[phone]
            
            # Connect and authorize
            await client.connect()
            
            # Check if authorized
            if await client.is_user_authorized():
                account.status = AccountStatus.ACTIVE
                account.last_login = datetime.now()
                
                # Get account info
                me = await client.get_me()
                account.user_id = me.id
                account.username = me.username
                account.first_name = me.first_name
                account.last_name = me.last_name
                account.is_premium = me.is_premium if hasattr(me, 'is_premium') else False
                
                return True, "Session started successfully"
            else:
                # Need to send code
                account.status = AccountStatus.VERIFYING
                return True, "Need OTP verification"
                
        except FloodWait as e:
            account.status = AccountStatus.FLOOD_WAIT
            account.flood_wait_seconds = e.value
            return False, f"Flood wait: {e.value} seconds"
            
        except Exception as e:
            console.print(f"[red]❌ Session start error: {e}[/red]")
            return False, f"Error: {str(e)[:100]}"
    
    async def send_otp_code(self, phone: str) -> Tuple[bool, str]:
        """Send OTP code using Pyrogram"""
        if phone not in self.clients:
            return False, "Client not initialized"
        
        try:
            client = self.clients[phone]
            sent_code = await client.send_code(phone)
            
            # Store code info
            if phone in self.accounts:
                self.accounts[phone].otp_code_hash = sent_code.phone_code_hash
            
            return True, "OTP sent successfully"
            
        except PhoneNumberInvalid:
            return False, "Invalid phone number"
        except PhoneNumberFlood:
            return False, "Phone number flood protection"
        except PhoneNumberBanned:
            return False, "Phone number is banned"
        except Exception as e:
            return False, f"Error: {str(e)[:100]}"
    
    async def verify_otp_code(self, phone: str, code: str) -> Tuple[bool, str]:
        """Verify OTP code using Pyrogram"""
        if phone not in self.clients:
            return False, "Client not initialized"
        
        try:
            client = self.clients[phone]
            
            if phone in self.accounts:
                account = self.accounts[phone]
                
                # Sign in with code
                await client.sign_in(
                    phone_number=phone,
                    phone_code_hash=account.otp_code_hash,
                    phone_code=code
                )
                
                # Update account status
                account.status = AccountStatus.ACTIVE
                account.last_login = datetime.now()
                
                return True, "OTP verified successfully"
                
        except PhoneCodeInvalid:
            return False, "Invalid OTP code"
        except PhoneCodeExpired:
            return False, "OTP code expired"
        except SessionPasswordNeeded:
            return False, "2FA_PASSWORD_NEEDED"
        except Exception as e:
            return False, f"Error: {str(e)[:100]}"

# ============================================
# MAIN BOT HANDLER (Converted to Pyrogram)
# ============================================
class AdvancedBotHandler:
    def __init__(self, user_manager, account_manager, reporting_engine):
        self.user_manager = user_manager
        self.account_manager = account_manager
        self.reporting_engine = reporting_engine
        self.bot = None
        self.user_sessions = {}
        
    async def initialize_bot(self):
        """Initialize the Pyrogram bot"""
        self.bot = Client(
            "enterprise_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=100
        )
        
        # Register handlers
        self.register_handlers()
        
        return self.bot
    
    def register_handlers(self):
        """Register all bot handlers"""
        
        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_command(client, message):
            await self.start_command_handler(message)
        
        @self.bot.on_message(filters.command("help") & filters.private)
        async def help_command(client, message):
            await self.help_command_handler(message)
        
        @self.bot.on_message(filters.command("report") & filters.private)
        async def report_command(client, message):
            await self.report_command_handler(message)
        
        @self.bot.on_message(filters.command("stats") & filters.private)
        async def stats_command(client, message):
            await self.stats_command_handler(message)
        
        @self.bot.on_callback_query()
        async def callback_handler(client, callback_query):
            await self.callback_handler(callback_query)
        
        @self.bot.on_message(filters.private & ~filters.command)
        async def message_handler(client, message):
            await self.message_handler(message)
    
    async def start_command_handler(self, message: Message):
        """Handle /start command"""
        user = message.from_user
        
        # Update user activity
        self.user_manager.update_user_activity(
            user.id, user.username, user.first_name, user.last_name
        )
        
        # Prepare welcome message
        welcome_text = f"""
🤖 *Telegram Enterprise Reporting System v11.0 (Pyrogram)*

*Welcome,* {user.first_name or 'User'}!

📊 *System Status:*
• Users: {len(self.user_manager.users)} registered
• Accounts: {len(self.account_manager.accounts)} available
• Proxies: {len([p for p in self.account_manager.proxy_manager.proxies if p.is_active])} working

🛠️ *Available Commands:*
/report - Start a new report
/stats - View statistics
/help - Detailed help guide
/accounts - Account management
/proxies - Proxy status
/jobs - View your jobs
/settings - User settings
/admin - Admin panel

💡 *Quick Start:*
1. Use /report to start reporting
2. Add accounts with /accounts
3. Check /stats for performance

⚠️ *Important:*
• Each account can report 9 times before proxy rotation
• Use premium proxies for better results
• Monitor system health regularly
"""
        
        # Create keyboard
        keyboard = [
            [KeyboardButton("📊 Stats"), KeyboardButton("🆘 Help")],
            [KeyboardButton("📝 Report"), KeyboardButton("📋 My Jobs")],
            [KeyboardButton("📱 Accounts"), KeyboardButton("🌐 Proxies")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def report_command_handler(self, message: Message):
        """Handle /report command with inline keyboard"""
        user_id = message.from_user.id
        
        # Check permissions
        if not self.user_manager.check_permission(user_id, "create_report"):
            await message.reply_text("❌ You don't have permission to create reports.")
            return
        
        # Create category selection keyboard
        keyboard = []
        row = []
        
        categories = {
            "SPAM": "🚫 Spam",
            "VIOLENCE": "🔪 Violence",
            "ILLEGAL_DRUGS": "💊 Drugs",
            "SEXUAL": "🔞 Sexual Content",
            "FRAUD": "🎭 Fraud",
            "HARASSMENT": "😠 Harassment",
            "COPYRIGHT": "©️ Copyright",
            "OTHER": "📌 Other"
        }
        
        for cat_id, cat_name in categories.items():
            row.append(InlineKeyboardButton(cat_name, callback_data=f"cat_{cat_id}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "📝 *Start New Report*\n\n"
            "Please select the violation category:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Store user session
        self.user_sessions[user_id] = {
            "step": "select_category",
            "created_at": datetime.now()
        }
    
    async def callback_handler(self, callback_query: CallbackQuery):
        """Handle callback queries"""
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        await callback_query.answer()
        
        if data == "cancel":
            await callback_query.message.edit_text("❌ Report cancelled.")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            return
        
        if data.startswith("cat_"):
            category = data[4:]
            
            # Store category and ask for target
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["category"] = category
                self.user_sessions[user_id]["step"] = "enter_target"
            
            await callback_query.message.edit_text(
                f"✅ *Category Selected:* {category}\n\n"
                "Now please send the target username or link:\n\n"
                "*Examples:*\n"
                "• @username\n"
                "• https://t.me/username\n"
                "• https://t.me/joinchat/xxxxxx\n\n"
                "⚠️ Make sure the target exists and is accessible.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def message_handler(self, message: Message):
        """Handle general messages"""
        user_id = message.from_user.id
        text = message.text.strip()
        
        if user_id in self.user_sessions:
            session = self.user_sessions[user_id]
            
            if session.get("step") == "enter_target":
                # Process target input
                await self.process_report_target(message, text, session)
            elif session.get("step") == "enter_description":
                # Process description input
                await self.process_report_description(message, text, session)
        else:
            # Handle general messages
            await self.handle_general_message(message, text)
    
    async def process_report_target(self, message: Message, target: str, session: dict):
        """Process report target input"""
        user_id = message.from_user.id
        
        # Store target
        session["target"] = target
        session["step"] = "enter_description"
        
        await message.reply_text(
            f"✅ *Target Accepted:* `{target[:50]}`\n\n"
            "Now please provide a detailed description of the violation:\n\n"
            "*Requirements:*\n"
            "• Minimum 20 characters\n"
            "• Be specific and factual\n"
            "• Include evidence if available\n"
            "• Avoid emotional language\n\n"
            "*Example:*\n"
            "\"This account is sending mass spam messages promoting "
            "fake cryptocurrency investments.\"",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def process_report_description(self, message: Message, description: str, session: dict):
        """Process report description and create job"""
        user_id = message.from_user.id
        
        if len(description) < 20:
            await message.reply_text(
                "❌ Description must be at least 20 characters.\n"
                "Please provide more details."
            )
            return
        
        # Create report job
        success, message_text, job_id = await self.reporting_engine.create_job(
            target=session["target"],
            target_type="user",  # You might want to detect this
            category=session["category"],
            subcategory=1,  # Default subcategory
            description=description,
            user_id=user_id
        )
        
        if success:
            await message.reply_text(
                f"✅ *Report Job Created!*\n\n"
                f"Job ID: `{job_id}`\n"
                f"Target: `{session['target'][:50]}`\n"
                f"Status: ⏳ Processing started\n\n"
                f"You will be notified when completed.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await message.reply_text(
                f"❌ *Failed to create job*\n\n"
                f"Error: {message_text}",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Cleanup session
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def stats_command_handler(self, message: Message):
        """Handle /stats command"""
        user_id = message.from_user.id
        user_data = self.user_manager.users.get(user_id)
        
        if not user_data:
            await message.reply_text("❌ User data not found. Use /start first.")
            return
        
        # Get statistics
        account_stats = self.account_manager.get_system_stats()
        proxy_stats = self.account_manager.proxy_manager.get_detailed_stats()
        
        stats_text = f"""
📊 *Comprehensive Statistics*

👤 *Personal Stats:*
• Role: {user_data.role.name}
• Trust Score: {user_data.trust_score:.1f}/100
• Reports Made: {user_data.reports_made}
• Success Rate: {user_data.statistics.get('report_success_rate', 0.0):.1f}%

🏢 *System Status:*
• Total Accounts: {account_stats['total_accounts']}
• Active Accounts: {account_stats['active_accounts']}
• Working Proxies: {proxy_stats['active_proxies']}/{proxy_stats['total_proxies']}
• Avg Proxy Speed: {proxy_stats['average_response_time']:.2f}s

⚡ *Performance:*
• Account Health Avg: {account_stats['average_health_score']:.1f}/100
• Proxy Reliability: {proxy_stats['average_reliability']:.1f}%
• System Uptime: 100% (monitored)

💡 *Recommendations:*
• Add more proxies if count < 10
• Perform maintenance if health < 60
• Rotate proxies regularly
"""
        
        await message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command_handler(self, message: Message):
        """Handle /help command"""
        help_text = """
🆘 *Comprehensive Help Guide*

📚 *Available Commands:*
/start - Welcome message and system status
/help - This comprehensive guide
/report - Start a new report
/stats - View system and personal statistics
/accounts - Account management (if permitted)
/proxies - Proxy status
/jobs - View your report jobs
/settings - User preferences
/admin - Admin panel (admins only)

📝 *Reporting Guide:*
1. Use /report to start
2. Select violation category
3. Enter target username/link
4. Provide detailed description
5. System processes with multiple accounts

🔧 *Account Management:*
• Add accounts with phone verification
• Monitor account health scores
• Rotate proxies after 9 reports
• Perform regular maintenance

🌐 *Proxy System:*
• Automatic verification
• Performance-based selection
• Geographic optimization
• Failover mechanisms

⚠️ *Important Notes:*
• Each account can make 9 reports before proxy rotation
• Use residential proxies for best results
• Monitor account health regularly
• Report only legitimate violations

💡 *Tips for Success:*
• Provide detailed, factual descriptions
• Use multiple accounts for better coverage
• Monitor system performance regularly
• Keep proxies updated and verified
"""
        
        await message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    
    async def handle_general_message(self, message: Message, text: str):
        """Handle general messages not part of any session"""
        # Check for OTP codes
        if re.match(r'^\d{5}$', text):
            await message.reply_text(
                "🔐 *OTP Code Detected*\n\n"
                "If you're trying to verify an account, "
                "please use the account management menu.\n\n"
                "Use /accounts for account management.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Default response
        await message.reply_text(
            "🤖 *Telegram Reporting System*\n\n"
            "I didn't understand that command.\n\n"
            "*Try these commands:*\n"
            "/start - Welcome message\n"
            "/help - Comprehensive guide\n"
            "/report - Start new report\n"
            "/stats - View statistics\n"
            "/accounts - Account management\n\n"
            "*Or use the keyboard buttons below.*",
            parse_mode=ParseMode.MARKDOWN
        )

# ============================================
# REPORTING ENGINE (Converted to Pyrogram)
# ============================================
class AdvancedReportingEngine:
    def __init__(self, account_manager, proxy_manager, user_manager):
        self.account_manager = account_manager
        self.proxy_manager = proxy_manager
        self.user_manager = user_manager
        
        # Pyrogram report reasons mapping
        self.report_reasons = {
            "SPAM": enums.ChatReportReason.SPAM,
            "VIOLENCE": enums.ChatReportReason.VIOLENCE,
            "ILLEGAL_DRUGS": enums.ChatReportReason.ILLEGAL_DRUGS,
            "SEXUAL": enums.ChatReportReason.PORNOGRAPHY,
            "FRAUD": enums.ChatReportReason.FRAUD,
            "HARASSMENT": enums.ChatReportReason.PERSONAL_DETAILS,
            "COPYRIGHT": enums.ChatReportReason.COPYRIGHT,
            "OTHER": enums.ChatReportReason.OTHER
        }
    
    async def execute_report(self, client: Client, target: str, 
                           reason: str, description: str) -> Dict[str, Any]:
        """Execute a report using Pyrogram"""
        try:
            # Resolve target (simplified)
            chat = await client.get_chat(target)
            
            # Submit report
            result = await client.report_chat(
                chat_id=chat.id,
                reason=self.report_reasons.get(reason, enums.ChatReportReason.OTHER),
                text=description[:200]  # Limit description length
            )
            
            return {
                "success": True,
                "chat_id": chat.id,
                "chat_type": chat.type,
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)[:200]
            }

# ============================================
# MAIN APPLICATION (Updated for Pyrogram)
# ============================================
class TelegramEnterpriseBot:
    def __init__(self):
        console = Console()
        console.print("[cyan]🚀 Initializing Telegram Enterprise Bot v11.0 (Pyrogram)[/cyan]")
        
        # Initialize managers
        self.proxy_manager = AdvancedProxyManager()
        self.user_manager = AdvancedUserManager()
        self.account_manager = AdvancedAccountManager(self.proxy_manager)
        
        # Update proxy manager reference
        self.account_manager.proxy_manager = self.proxy_manager
        
        # Initialize reporting engine
        self.reporting_engine = AdvancedReportingEngine(
            self.account_manager,
            self.proxy_manager,
            self.user_manager
        )
        
        # Initialize bot handler
        self.bot_handler = AdvancedBotHandler(
            self.user_manager,
            self.account_manager,
            self.reporting_engine
        )
    
    async def initialize_system(self) -> bool:
        """Initialize the entire system"""
        try:
            # Initialize proxy manager
            console.print("[cyan]1. Initializing Proxy Manager...[/cyan]")
            # await self.proxy_manager.initialize()  # You'll need to adapt this
            
            # Load existing data
            console.print("[cyan]2. Loading system data...[/cyan]")
            # Your existing data loading logic
            
            # Initialize bot
            console.print("[cyan]3. Initializing Bot...[/cyan]")
            self.bot = await self.bot_handler.initialize_bot()
            
            console.print("[green]✅ Enterprise system initialization complete[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ System initialization failed: {e}[/red]")
            return False
    
    async def run(self):
        """Run the enterprise bot"""
        # Initialize system
        initialized = await self.initialize_system()
        
        if not initialized:
            console.print("[red]❌ System initialization failed. Cannot start bot.[/red]")
            return
        
        # Start bot
        console.print("[green]🤖 Starting Telegram Enterprise Bot...[/green]")
        
        try:
            await self.bot.start()
            console.print("[green]✅ Bot is running![/green]")
            console.print("[yellow]📱 Use /start in Telegram to begin[/yellow]")
            
            # Keep running
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Received shutdown signal...[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Runtime error: {e}[/red]")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the system gracefully"""
        console.print("[yellow]🔧 Shutting down enterprise system...[/yellow]")
        
        try:
            # Stop bot
            if hasattr(self, 'bot'):
                await self.bot.stop()
            
            # Save all data
            if hasattr(self, 'user_manager'):
                self.user_manager._save_users()
            
            console.print("[green]✅ Enterprise system shutdown complete[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Shutdown error: {e}[/red]")

# ============================================
# MAIN ENTRY POINT
# ============================================
async def main():
    enterprise_bot = TelegramEnterpriseBot()
    await enterprise_bot.run()

if __name__ == "__main__":
    asyncio.run(main())
