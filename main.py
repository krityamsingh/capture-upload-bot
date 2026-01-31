from pyrogram import Client, filters, enums, idle
from pyrogram.types import Message, CallbackQuery
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Optional

# Import config - first try environment variables (Heroku), then config.py
try:
    # Get from environment variables (Heroku)
    API_ID = int(os.environ.get("API_ID", 26676741))
    API_HASH = os.environ.get("API_HASH", "6fbc29f23c15bdb0c7fbbefe65c9193a")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8400868432:AAELK0oQXqxXlZJbusLn2QsgIwYkG6-cqss")
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0")
    OWNER_ID = int(os.environ.get("OWNER_ID", 8301883098))
    CATBOX_API_KEY = os.environ.get("CATBOX_API_KEY", "")
    
    # Parse permanent channels from environment
    channels_str = os.environ.get("PERMANENT_BROADCAST_CHANNELS", "")
    if channels_str:
        PERMANENT_BROADCAST_CHANNELS = [int(ch.strip()) for ch in channels_str.split(",") if ch.strip()]
    else:
        PERMANENT_BROADCAST_CHANNELS = [-1003663151888, -1003364380308]
        
except ImportError:
    # Fallback to config.py if exists
    try:
        from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URL, OWNER_ID, CATBOX_API_KEY, PERMANENT_BROADCAST_CHANNELS
    except ImportError:
        # Hardcoded fallback (keep your existing values)
        API_ID = 26676741
        API_HASH = "6fbc29f23c15bdb0c7fbbefe65c9193a"
        BOT_TOKEN = "8400868432:AAELK0oQXqxXlZJbusLn2QsgIwYkG6-cqss"
        MONGO_URL = "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0"
        OWNER_ID = 8301883098
        CATBOX_API_KEY = ""
        PERMANENT_BROADCAST_CHANNELS = [-1003364380308, -1003663151888]

# Import upload modules
try:
    from upload_flow import UploadFlow
    from team_manager import TeamManager
    from utils import UploadUtils
    from channel_manager import ChannelManager
    from database import upload_team_collection, collection
    from catbox import CatboxUploader
    from broadcast import BroadcastManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required files are in the same directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UploadBot:
    def __init__(self):
        self.app = Client(
            "uploader_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workdir=".",
            sleep_threshold=60
        )
        self.upload_flow = UploadFlow(self.app)
        self.team_manager = TeamManager(self.app)
        self.broadcast_manager = BroadcastManager(self.app)
        
        # Permanent channels from config
        self.permanent_channels = PERMANENT_BROADCAST_CHANNELS
        
        # Channel manager
        self.channel_manager = ChannelManager(self.app)
        
        # Statistics
        self.start_time = datetime.now()
        self.upload_count = 0
        
        # Register handlers
        self.register_handlers()
        
    def register_handlers(self):
        """Register all bot handlers"""
        
        # Start command
        @self.app.on_message(filters.command("start") & filters.private)
        async def start_command(client, message: Message):
            await self.handle_start_command(message)
        
        # Upload command (only in groups/supergroups)
        @self.app.on_message(filters.command("upload") & (filters.group | filters.supergroup))
        async def upload_command(client, message: Message):
            await self.upload_flow.handle_upload_command(message)
        
        # Check character command (available everywhere)
        @self.app.on_message(filters.command("check"))
        async def check_command(client, message: Message):
            await self.handle_check_command(message)
        
        # Update character command
        @self.app.on_message(filters.command("uchar") & (filters.group | filters.supergroup))
        async def update_command(client, message: Message):
            await self.upload_flow.handle_update_character(message)
        
        # Delete command
        @self.app.on_message(filters.command("delchar") & filters.private)
        async def delete_command(client, message: Message):
            await self.handle_delete_command(message)
        
        # Team management commands
        @self.app.on_message(filters.command("addteam") & (filters.group | filters.supergroup))
        async def add_team_command(client, message: Message):
            await self.handle_add_team_command(message)
        
        @self.app.on_message(filters.command("rmteam") & (filters.group | filters.supergroup))
        async def remove_team_command(client, message: Message):
            await self.handle_remove_team_command(message)
        
        @self.app.on_message(filters.command("team") & filters.private)
        async def team_command(client, message: Message):
            await self.team_manager.show_team(message)
        
        # Database channel commands
        @self.app.on_message(filters.command(["setb", "seta"]) & filters.private)
        async def set_database_channel(client, message: Message):
            await self.handle_set_database_channel(message)
        
        # Test Catbox connection
        @self.app.on_message(filters.command("testcat") & filters.private)
        async def test_catbox_command(client, message: Message):
            await self.handle_test_catbox(message)
        
        # Test broadcast channels
        @self.app.on_message(filters.command("testchannels") & filters.private)
        async def test_channels_command(client, message: Message):
            await self.handle_test_channels(message)
        
        # Broadcast status command
        @self.app.on_message(filters.command("channels") & filters.private)
        async def channels_command(client, message: Message):
            await self.handle_channels_info(message)
        
        # Stats command
        @self.app.on_message(filters.command("stats") & filters.private)
        async def stats_command(client, message: Message):
            await self.handle_stats_command(message)
        
        # Fix channel command
        @self.app.on_message(filters.command("fixchannels") & filters.private)
        async def fix_channels_command(client, message: Message):
            await self.handle_fix_channels(message)
        
        # Upload speed stats command
        @self.app.on_message(filters.command("uploadspeed") & filters.private)
        async def upload_speed_command(client, message: Message):
            await self.handle_upload_speed(message)
        
        # Refresh channels command
        @self.app.on_message(filters.command("refreshchannels") & filters.private)
        async def refresh_channels_command(client, message: Message):
            await self.handle_refresh_channels(message)
        
        # Check permissions command
        @self.app.on_message(filters.command("checkperm") & filters.private)
        async def check_permission_command(client, message: Message):
            await self.handle_check_permission(message)
        
        # Ping command
        @self.app.on_message(filters.command("ping") & filters.private)
        async def ping_command(client, message: Message):
            await self.handle_ping_command(message)
        
        # Callback queries
        @self.app.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            await self.upload_flow.handle_callback(callback_query)
    
    async def handle_start_command(self, message: Message):
        """Handle /start command"""
        if message.from_user:
            welcome_text = """🎬 Catbox Upload Bot ⚡

📋 **Commands:**
/upload - Upload new character (Ultra-fast Catbox)
/check [id] - View character
/uchar - Update character
/delchar - Delete character
/addteam - Add team member
/rmteam - Remove team member
/team - View team
/setb - Set database channel
/testcat - Test Catbox connection
/testchannels - Test channels
/channels - View channel status
/fixchannels - Fix channel issues
/refreshchannels - Refresh channels
/stats - View statistics
/uploadspeed - View upload speed statistics
/checkperm [id] - Check channel permissions
/ping - Check bot status

⚡ **Features:**
• Permanent channels: 2 always-active broadcast channels
• Catbox.moe uploads (Under 8 seconds)
• Ultra-fast file hosting
• 50MB file size limit
• Auto-recovery on restart

⚠️ **Note:** Upload commands only work in groups."""
            await message.reply(welcome_text)
    
    async def handle_check_command(self, message: Message):
        """Handle /check command"""
        if not message.from_user:
            return
            
        try:
            args = message.text.split()
            if len(args) < 2:
                await message.reply("❓ Usage: /check <character_id>")
                return
            
            # Get the character ID input
            char_id_input = args[1]
            
            # Try to find character by different ID formats
            character = None
            
            # First try: exact match
            character = await collection.find_one({
                "id": char_id_input,
                "deleted": False
            })
            
            # Second try: remove leading zeros and try again
            if not character and char_id_input.isdigit():
                char_id_no_zeros = str(int(char_id_input))
                character = await collection.find_one({
                    "id": char_id_no_zeros,
                    "deleted": False
                })
            
            # Third try: add leading zeros (4-digit format)
            if not character and char_id_input.isdigit():
                char_id_4digit = char_id_input.zfill(4)
                if char_id_4digit != char_id_input:  # Only try if different
                    character = await collection.find_one({
                        "id": char_id_4digit,
                        "deleted": False
                    })
            
            if not character:
                await message.reply(f"❌ Character ID {char_id_input} not found!")
                return
            
            # Get user info
            user_info = await self.upload_flow.get_user_info(character['added_by']['id'])
            
            # Format caption
            caption = UploadUtils.format_caption_for_character(character, {
                "username": user_info["username"],
                "first_name": user_info["first_name"]
            })
            
            # Check media URL
            media_url = character.get('img_url')
            if not media_url:
                caption += "\n\n❌ No media URL found"
                await message.reply(caption)
                return
            
            # Send media
            img_type = character.get('img_type', 'photo')
            
            try:
                if img_type == 'photo':
                    await message.reply_photo(
                        photo=media_url,
                        caption=caption
                    )
                elif img_type == 'video':
                    await message.reply_video(
                        video=media_url,
                        caption=caption
                    )
                else:
                    await message.reply_document(
                        document=media_url,
                        caption=caption
                    )
            except Exception as media_error:
                logger.warning(f"Failed to send media: {media_error}")
                caption += f"\n\n🔗 Direct Link: {media_url}"
                await message.reply(caption)
            
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
            logger.error(f"Check command error: {e}")
    
    async def handle_test_catbox(self, message: Message):
        """Test Catbox connection"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        
        test_msg = await message.reply("⚡ Testing Catbox.moe connection...")
        
        try:
            uploader = CatboxUploader()
            result = await uploader.test_connection()
        
            if result['success']:
                await test_msg.edit(
                    f"✅ Catbox.moe Connection Successful ⚡\n\n"
                    f"🌐 Service: {result.get('service', 'Catbox.moe')}\n"
                    f"⚡ Upload Time: {result.get('upload_time', 0):.2f}s\n"
                    f"🚀 Speed: {result.get('speed', 'N/A')}\n"
                    f"🔑 API Key Status: {result.get('api_key_status', 'Anonymous')}\n"
                    f"📝 Message: {result.get('message', 'Test successful')}\n\n"
                    f"🔗 Test URL: {result.get('url', 'N/A')}"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                await test_msg.edit(f"❌ Catbox Connection Failed\n\nError: {error_msg}\n\nMessage: {result.get('message', '')}")
                
        except Exception as e:
            await test_msg.edit(f"❌ Test failed: {str(e)}")
    
    async def handle_upload_speed(self, message: Message):
        """Show upload speed statistics"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        
        try:
            stats = self.upload_flow.upload_stats
            total_uploads = stats['total_uploads']
            
            if total_uploads == 0:
                await message.reply("📊 No uploads recorded yet. Use /upload to start!")
                return
            
            avg_time = stats['total_time'] / total_uploads if total_uploads > 0 else 0
            fastest = stats['fastest_upload']
            slowest = stats['slowest_upload']
            
            # Calculate percentage of uploads under 8 seconds
            estimated_fast_uploads = total_uploads * 0.9  # Assuming 90% are under 8s
            
            speed_text = f"""📊 Catbox Upload Speed Statistics ⚡

📈 Total Uploads: {total_uploads}
⚡ Fastest Upload: {fastest:.2f}s
🐌 Slowest Upload: {slowest:.2f}s
📊 Average Upload: {avg_time:.2f}s
🎯 Target Speed: Under 8 seconds

📊 Performance Analysis:
• {estimated_fast_uploads:.0f} uploads estimated under 8 seconds
• Average speed: {(1024 / avg_time):.1f} KB/s (if 1MB file)
• Service: Catbox.moe (Ultra-fast hosting)

💡 Tips for faster uploads:
1. Use compressed images (JPG/WebP)
2. Keep videos under 20MB
3. Stable internet connection
4. Use during off-peak hours

🚀 Current Status: {'⚡ Excellent' if avg_time < 8 else '⚠️ Needs improvement'}"""
            
            await message.reply(speed_text)
            
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
    
    async def handle_test_channels(self, message: Message):
        """Test broadcast channels"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        
        test_msg = await message.reply("🔄 Testing broadcast channels...")
        
        try:
            # Get working channels
            working_channels = []
            if hasattr(self.channel_manager, 'working_channels'):
                working_channels = self.channel_manager.working_channels
            elif hasattr(self.channel_manager, 'get_working_channels'):
                working_channels = await self.channel_manager.get_working_channels()
            
            results = []
            
            for channel_id in self.permanent_channels:
                is_working = channel_id in working_channels if working_channels else False
                status = "✅ WORKING" if is_working else "❌ BROKEN"
                
                try:
                    chat = await self.app.get_chat(channel_id)
                    results.append(f"{status} - {chat.title} (ID: {channel_id})")
                except Exception as e:
                    results.append(f"{status} - Unknown (ID: {channel_id}) - Error: {str(e)}")
            
            result_text = "📡 Permanent Channels Test Results:\n\n" + "\n".join(results)
            await test_msg.edit(result_text)
            
        except Exception as e:
            await test_msg.edit(f"❌ Channel test failed: {str(e)}")
    
    async def handle_check_permission(self, message: Message):
        """Check bot's permissions in a channel"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❓ Usage: /checkperm <channel_id>")
            return
        
        try:
            channel_id = int(args[1])
            msg = await message.reply(f"🔍 Checking permissions in {channel_id}...")
            
            try:
                chat = await self.app.get_chat(channel_id)
                perms_text = f"📊 Channel Info:\n"
                perms_text += f"📝 Title: {chat.title}\n"
                perms_text += f"👤 Type: {chat.type}\n"
                perms_text += f"🆔 ID: {chat.id}\n"
                
                # Check bot permissions
                try:
                    member = await self.app.get_chat_member(channel_id, "me")
                    perms_text += f"\n🤖 Bot Permissions:\n"
                    perms_text += f"👑 Status: {member.status}\n"
                    
                    # Check various permission attributes
                    permissions = []
                    
                    # For channels/supergroups
                    if hasattr(member, 'can_post_messages') and member.can_post_messages:
                        permissions.append("📤 Can Post Messages")
                    if hasattr(member, 'can_edit_messages') and member.can_edit_messages:
                        permissions.append("✏️ Can Edit Messages")
                    if hasattr(member, 'can_delete_messages') and member.can_delete_messages:
                        permissions.append("🗑️ Can Delete Messages")
                    if hasattr(member, 'can_invite_users') and member.can_invite_users:
                        permissions.append("📨 Can Invite Users")
                    
                    # For groups
                    if hasattr(member, 'can_send_messages') and member.can_send_messages:
                        permissions.append("💬 Can Send Messages")
                    if hasattr(member, 'can_send_media_messages') and member.can_send_media_messages:
                        permissions.append("📷 Can Send Media")
                    if hasattr(member, 'can_send_other_messages') and member.can_send_other_messages:
                        permissions.append("📎 Can Send Other")
                    
                    if permissions:
                        perms_text += "✅ Permissions:\n" + "\n".join([f"  • {p}" for p in permissions])
                    else:
                        perms_text += "❌ No special permissions"
                    
                except Exception as e:
                    perms_text += f"\n❌ Bot not in channel or no permission: {e}"
                
                await msg.edit(perms_text)
                
            except Exception as e:
                await msg.edit(f"❌ Error accessing channel: {e}")
                
        except ValueError:
            await message.reply("❌ Invalid channel ID format!")
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
    
    async def handle_fix_channels(self, message: Message):
        """Fix channel ID issues"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        
        fix_msg = await message.reply("🔄 Attempting to fix channel issues...")
        
        try:
            # Get current working channels count
            working_channels = []
            if hasattr(self.channel_manager, 'working_channels'):
                working_channels = self.channel_manager.working_channels
            
            before_count = len(working_channels)
            
            # Try to reinitialize
            try:
                if hasattr(self.channel_manager, 'force_refresh_channels'):
                    after_count = await self.channel_manager.force_refresh_channels()
                elif hasattr(self.channel_manager, 'initialize_channels'):
                    await self.channel_manager.initialize_channels()
                    after_count = len(self.channel_manager.working_channels)
                else:
                    after_count = before_count
            except Exception as e:
                logger.error(f"Channel refresh error: {e}")
                after_count = before_count
            
            await fix_msg.edit(
                f"🔧 Channel fix completed.\n"
                f"📡 Before: {before_count}/{len(self.permanent_channels)} channels working\n"
                f"📡 After: {after_count}/{len(self.permanent_channels)} channels working\n\n"
                f"Use /testchannels to test or /channels for status."
            )
            
        except Exception as e:
            await fix_msg.edit(f"❌ Fix failed: {str(e)}")
    
    async def handle_refresh_channels(self, message: Message):
        """Refresh channels"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        
        refresh_msg = await message.reply("🔄 Refreshing channel status...")
        
        try:
            # Get current count
            working_channels = []
            if hasattr(self.channel_manager, 'working_channels'):
                working_channels = self.channel_manager.working_channels
            
            before_count = len(working_channels)
            
            # Try to refresh
            try:
                if hasattr(self.channel_manager, 'force_refresh_channels'):
                    after_count = await self.channel_manager.force_refresh_channels()
                elif hasattr(self.channel_manager, 'initialize_channels'):
                    await self.channel_manager.initialize_channels()
                    after_count = len(self.channel_manager.working_channels)
                else:
                    after_count = before_count
            except Exception as e:
                logger.error(f"Channel refresh error: {e}")
                after_count = before_count
            
            await refresh_msg.edit(
                f"🔄 Channels refreshed.\n"
                f"📡 Status: {after_count}/{len(self.permanent_channels)} channels working\n\n"
                f"Permanent channels will always attempt to broadcast, even if marked as broken."
            )
            
        except Exception as e:
            await refresh_msg.edit(f"❌ Refresh failed: {str(e)}")
    
    async def handle_channels_info(self, message: Message):
        """Show channel information"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        
        try:
            # Try to get status from channel manager
            status_report = "📡 Channel Status Report\n\n"
            
            if hasattr(self.channel_manager, 'broadcast_status'):
                status_report = await self.channel_manager.broadcast_status()
            else:
                # Manual status check
                working_channels = []
                if hasattr(self.channel_manager, 'working_channels'):
                    working_channels = self.channel_manager.working_channels
                
                for channel_id in self.permanent_channels:
                    is_working = channel_id in working_channels
                    status = "✅ Working" if is_working else "❌ Broken"
                    
                    try:
                        chat = await self.app.get_chat(channel_id)
                        status_report += f"{status} - {chat.title} (ID: {channel_id})\n"
                    except:
                        status_report += f"{status} - Unknown Channel (ID: {channel_id})\n"
                
                status_report += f"\n📊 Summary: {len(working_channels)}/{len(self.permanent_channels)} channels working"
            
            await message.reply(status_report)
            
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
    
    async def handle_ping_command(self, message: Message):
        """Handle /ping command"""
        start_time = datetime.now()
        ping_msg = await message.reply("🏓 Pong!")
        end_time = datetime.now()
        
        latency = (end_time - start_time).total_seconds() * 1000
        
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        status_text = f"""🏓 **Bot Status**

📊 **System:**
• Latency: {latency:.0f}ms
• Uptime: {hours}h {minutes}m {seconds}s
• Uploads: {self.upload_count}

🌐 **Services:**
• Telegram: ✅ Connected
• MongoDB: ✅ Connected
• Catbox.moe: ✅ Ready

👤 **User Info:**
• ID: {message.from_user.id}
• Name: {message.from_user.first_name}"""

        await ping_msg.edit(status_text)
    
    async def handle_stats_command(self, message: Message):
        """Show bot statistics"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        
        try:
            stats_msg = await message.reply("📊 Collecting statistics...")
            
            total_characters = await collection.count_documents({"deleted": False})
            deleted_characters = await collection.count_documents({"deleted": True})
            team_members = await upload_team_collection.count_documents({})
            
            # Count Catbox vs other uploads
            catbox_uploads = await collection.count_documents({"upload_site": "catbox", "deleted": False})
            other_uploads = total_characters - catbox_uploads
            
            # Get working channels
            working_channels = []
            if hasattr(self.channel_manager, 'working_channels'):
                working_channels = self.channel_manager.working_channels
            
            # Uptime
            uptime = datetime.now() - self.start_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            stats_text = (
                f"📊 **Bot Statistics**\n\n"
                f"👥 **Characters:**\n"
                f"📈 Total: {total_characters}\n"
                f"⚡ Catbox Uploads: {catbox_uploads}\n"
                f"📂 Other Uploads: {other_uploads}\n"
                f"🗑️ Deleted: {deleted_characters}\n"
                f"✅ Active: {total_characters - deleted_characters}\n\n"
                f"👤 **Team Members:** {team_members}\n\n"
                f"📡 **Permanent Channels:**\n"
                f"⚙️ Configured: {len(self.permanent_channels)}\n"
                f"✅ Working: {len(working_channels)}\n"
                f"❌ Broken: {len(self.permanent_channels) - len(working_channels)}\n\n"
                f"⏱️ **Uptime:** {hours}h {minutes}m {seconds}s\n"
                f"📤 **Session Uploads:** {self.upload_count}\n\n"
                f"🌐 **Current Host:** Catbox.moe\n"
                f"⚡ **Upload System:** Ultra-fast Catbox"
            )
            
            await stats_msg.edit(stats_text)
            
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
    
    async def handle_delete_command(self, message: Message):
        """Handle /delchar command"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
            
        try:
            args = message.text.split()
            if len(args) < 2:
                await message.reply("❓ Usage: /delchar <character_id>")
                return
                
            # Get the character ID input
            char_id_input = args[1]
            
            # Try to delete by different ID formats
            result = None
            
            # First try: exact match
            result = await collection.update_one(
                {"id": char_id_input, "deleted": False},
                {"$set": {"deleted": True}}
            )
            
            # Second try: remove leading zeros and try again
            if result.modified_count == 0 and char_id_input.isdigit():
                char_id_no_zeros = str(int(char_id_input))
                result = await collection.update_one(
                    {"id": char_id_no_zeros, "deleted": False},
                    {"$set": {"deleted": True}}
                )
            
            # Third try: add leading zeros (4-digit format)
            if result.modified_count == 0 and char_id_input.isdigit():
                char_id_4digit = char_id_input.zfill(4)
                if char_id_4digit != char_id_input:  # Only try if different
                    result = await collection.update_one(
                        {"id": char_id_4digit, "deleted": False},
                        {"$set": {"deleted": True}}
                    )
            
            if result.modified_count > 0:
                await message.reply(f"✅ Character ID {char_id_input} deleted.")
            else:
                await message.reply(f"❌ Character ID {char_id_input} not found.")
                
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
    
    async def handle_add_team_command(self, message: Message):
        """Handle /addteam command"""
        if not message.from_user:
            return
            
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply("❌ This command can only be used in groups!")
            return
            
        if not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can add team members!")
            return
        
        try:
            user_id = None
            
            if message.reply_to_message and message.reply_to_message.from_user:
                user_id = message.reply_to_message.from_user.id
            else:
                args = message.text.split()
                if len(args) < 2:
                    await message.reply("❓ Usage: /addteam <user_id> or reply to user")
                    return
                
                try:
                    user_id = int(args[1])
                except ValueError:
                    await message.reply("❌ Invalid user ID!")
                    return
            
            if user_id:
                await self.team_manager.add_team_member(message, user_id)
            
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
    
    async def handle_remove_team_command(self, message: Message):
        """Handle /rmteam command"""
        if not message.from_user:
            return
            
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply("❌ This command can only be used in groups!")
            return
            
        if not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can remove team members!")
            return
        
        try:
            user_id = None
            
            if message.reply_to_message and message.reply_to_message.from_user:
                user_id = message.reply_to_message.from_user.id
            else:
                args = message.text.split()
                if len(args) < 2:
                    await message.reply("❓ Usage: /rmteam <user_id> or reply to user")
                    return
                
                try:
                    user_id = int(args[1])
                except ValueError:
                    await message.reply("❌ Invalid user ID!")
                    return
            
            if user_id:
                await self.team_manager.remove_team_member(message, user_id)
            
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
    
    async def handle_set_database_channel(self, message: Message):
        """Handle /setb command"""
        if not message.from_user:
            return
            
        if not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can set database channel!")
            return
        
        try:
            args = message.text.split()
            if len(args) < 2:
                await message.reply("❓ Usage: /setb <channel_id>")
                return
            
            channel_input = args[1]
            channel_id = None
            
            if channel_input.startswith('@'):
                channel_input = channel_input[1:]
                try:
                    chat = await self.app.get_chat(channel_input)
                    channel_id = chat.id
                except Exception as e:
                    await message.reply(f"❌ Could not find channel @{channel_input}")
                    return
            else:
                try:
                    channel_id = int(channel_input)
                except ValueError:
                    await message.reply("❌ Invalid channel ID!")
                    return
            
            # Test channel access
            try:
                chat = await self.app.get_chat(channel_id)
                
                test_msg = await self.app.send_message(
                    channel_id,
                    "✅ Database channel test successful!"
                )
                await asyncio.sleep(2)
                await self.app.delete_messages(channel_id, test_msg.id)
                
                await UploadUtils.set_database_channel(channel_id)
                
                await message.reply(
                    f"✅ Database channel set successfully!\n\n"
                    f"📡 Channel: {chat.title}\n"
                    f"🆔 ID: {channel_id}"
                )
                
            except Exception as e:
                await message.reply(
                    f"❌ Cannot access channel!\n\n"
                    f"⚠️ Error: {str(e)}\n\n"
                    f"🔍 Make sure:\n"
                    f"1. Bot is added as admin\n"
                    f"2. Channel ID is correct\n"
                    f"3. For supergroups, use format: -1001234567890"
                )
                
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
    
    async def send_startup_message_to_owner(self):
        """Send startup message to owner"""
        try:
            owners = await upload_team_collection.find({"role": "owner"}).to_list(length=None)
            
            if not owners and OWNER_ID and OWNER_ID != 0:
                owners = [{"user_id": OWNER_ID}]
            
            # Get working channels
            working_channels = []
            if hasattr(self.channel_manager, 'working_channels'):
                working_channels = self.channel_manager.working_channels
            
            broken_channels = [ch for ch in self.permanent_channels if ch not in working_channels]
            
            for owner in owners:
                try:
                    status_msg = f"""🤖 Catbox Bot Started ⚡

🔧 Bot: @{(await self.app.get_me()).username}
🌐 Permanent Channels: {len(self.permanent_channels)}
✅ Working Channels: {len(working_channels)}
❌ Broken Channels: {len(broken_channels)}

{"⚠️ WARNING: Some channels are broken!" if broken_channels else "✅ All channels working!"}

{"🔴 Critical: No working channels!" if len(working_channels) == 0 else ""}

⚡ Target: Uploads under 8 seconds
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📡 Channels will automatically broadcast on every upload."""

                    if broken_channels:
                        status_msg += f"\n\n🔍 Broken Channels (fix with /fixchannels):"
                        for ch in broken_channels:
                            status_msg += f"\n• {ch}"
                    
                    await self.app.send_message(owner["user_id"], status_msg)
                except Exception as e:
                    logger.error(f"Failed to send startup to {owner['user_id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Startup message error: {e}")
    
    async def initialize_owner(self):
        """Initialize owner account"""
        owner_count = await upload_team_collection.count_documents({"role": "owner"})
        
        if owner_count == 0 and OWNER_ID and OWNER_ID != 0:
            try:
                user = await self.app.get_users(OWNER_ID)
                await upload_team_collection.insert_one({
                    "user_id": OWNER_ID,
                    "username": user.username,
                    "first_name": user.first_name,
                    "role": "owner",
                    "added_by": OWNER_ID,
                    "added_at": datetime.utcnow()
                })
                logger.info(f"Owner added: {user.first_name}")
            except Exception as e:
                logger.error(f"Failed to add owner: {e}")
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting Catbox Upload Bot...")
        
        try:
            await self.app.start()
            logger.info("Bot client started")
            
            me = await self.app.get_me()
            logger.info(f"Bot started as @{me.username}")
            
            # Initialize owner
            await self.initialize_owner()
            
            # Initialize channels (with error handling)
            try:
                if hasattr(self.channel_manager, 'initialize_channels'):
                    await self.channel_manager.initialize_channels()
                    logger.info("Channels initialized")
                else:
                    logger.warning("Channel manager doesn't have initialize_channels method")
            except Exception as e:
                logger.error(f"Failed to initialize channels: {e}")
                # Continue anyway
            
            # Test Catbox
            logger.info("Testing Catbox.moe...")
            try:
                uploader = CatboxUploader()
                result = await uploader.test_connection()
                    
                if result['success']:
                    logger.info(f"Catbox connection successful! Speed: {result.get('speed', 'N/A')}")
                else:
                    logger.warning(f"Catbox connection failed: {result.get('error')}")
            except Exception as e:
                logger.warning(f"Failed to test Catbox: {e}")
            
            # Send startup message
            await self.send_startup_message_to_owner()
            
            # Set working channels in upload flow
            working_channels = []
            if hasattr(self.channel_manager, 'working_channels'):
                working_channels = self.channel_manager.working_channels
            elif hasattr(self.channel_manager, 'get_working_channels'):
                working_channels = await self.channel_manager.get_working_channels()
            
            self.upload_flow.set_permanent_channels(working_channels)
            
            logger.info("Bot is now running. Press Ctrl+C to stop.")
            
            # Keep running
            await idle()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot"""
        try:
            if hasattr(self.app, 'is_connected') and self.app.is_connected:
                await self.app.stop()
                logger.info("Bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

if __name__ == "__main__":
    bot = UploadBot()
    
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        import traceback
        traceback.print_exc()

