from pyrogram import Client, filters, enums, idle
from pyrogram.types import Message, CallbackQuery
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Optional

from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URL, OWNER_ID, CATBOX_API_KEY, DEFAULT_DATABASE_CHANNEL

try:
    from upload_flow import UploadFlow
    from team_manager import TeamManager
    from utils import UploadUtils
    from database import upload_team_collection, collection, database_channel_collection
    from catbox import CatboxUploader
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
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
        self.database_channel = None
        self.start_time = datetime.now()
        self.upload_count = 0
        self.register_handlers()

    def register_handlers(self):
        @self.app.on_message(filters.command("start") & filters.private)
        async def start_command(client, message: Message):
            await self.handle_start_command(message)

        @self.app.on_message(filters.command("upload") & (filters.group | filters.channel))
        async def upload_command(client, message: Message):
            await self.upload_flow.handle_upload_command(message)

        @self.app.on_message(filters.command("check"))
        async def check_command(client, message: Message):
            await self.handle_check_command(message)

        @self.app.on_message(filters.command("uchar") & (filters.group | filters.channel))
        async def update_command(client, message: Message):
            await self.upload_flow.handle_update_character(message)

        @self.app.on_message(filters.command("delchar") & filters.private)
        async def delete_command(client, message: Message):
            await self.handle_delete_command(message)

        @self.app.on_message(filters.command("addteam") & (filters.group | filters.channel))
        async def add_team_command(client, message: Message):
            await self.handle_add_team_command(message)

        @self.app.on_message(filters.command("rmteam") & (filters.group | filters.channel))
        async def remove_team_command(client, message: Message):
            await self.handle_remove_team_command(message)

        @self.app.on_message(filters.command("team") & filters.private)
        async def team_command(client, message: Message):
            await self.team_manager.show_team(message)

        @self.app.on_message(filters.command("setchannel") & filters.private)
        async def set_channel_command(client, message: Message):
            await self.handle_set_channel_command(message)

        @self.app.on_message(filters.command("channel") & filters.private)
        async def channel_command(client, message: Message):
            await self.handle_channel_info(message)

        @self.app.on_message(filters.command("testcat") & filters.private)
        async def test_catbox_command(client, message: Message):
            await self.handle_test_catbox(message)

        @self.app.on_message(filters.command("testchannel") & filters.private)
        async def test_channel_command(client, message: Message):
            await self.handle_test_channel(message)

        @self.app.on_message(filters.command("stats") & filters.private)
        async def stats_command(client, message: Message):
            await self.handle_stats_command(message)

        @self.app.on_message(filters.command("uploadspeed") & filters.private)
        async def upload_speed_command(client, message: Message):
            await self.handle_upload_speed(message)

        @self.app.on_message(filters.command("ping") & filters.private)
        async def ping_command(client, message: Message):
            await self.handle_ping_command(message)

        @self.app.on_message(filters.command("removechannel") & filters.private)
        async def remove_channel_command(client, message: Message):
            await self.handle_remove_channel(message)

        @self.app.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            await self.upload_flow.handle_callback(callback_query)

    async def handle_start_command(self, message: Message):
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
/setchannel - Set database channel
/channel - View current channel
/removechannel - Remove channel
/testcat - Test Catbox connection
/testchannel - Test channel access
/stats - View statistics
/uploadspeed - View upload speed statistics
/ping - Check bot status

⚡ **Features:**
• Database channel: Set one channel for broadcasting
• Catbox.moe uploads (Under 8 seconds)
• Ultra-fast file hosting
• 50MB file size limit
• Auto-recovery on restart

⚠️ **Note:** Upload commands only work in groups."""
            await message.reply(welcome_text)

    async def handle_check_command(self, message: Message):
        if not message.from_user:
            return
        try:
            args = message.text.split()
            if len(args) < 2:
                await message.reply("❓ Usage: /check <character_id>")
                return
            char_id_input = args[1]
            character = await UploadUtils.find_character_by_id(char_id_input)
            if not character:
                await message.reply(f"❌ Character ID {char_id_input} not found!")
                return
            user_info = await self.upload_flow.get_user_info(character['added_by']['id'])
            caption = UploadUtils.format_caption_for_character(character, {
                "username": user_info["username"],
                "first_name": user_info["first_name"]
            })
            media_url = character.get('img_url')
            if not media_url:
                caption += "\n\n❌ No media URL found"
                await message.reply(caption)
                return
            img_type = character.get('img_type', 'photo')
            try:
                if img_type == 'photo':
                    await message.reply_photo(photo=media_url, caption=caption)
                elif img_type == 'video':
                    await message.reply_video(video=media_url, caption=caption)
                else:
                    await message.reply_document(document=media_url, caption=caption)
            except Exception as media_error:
                logger.warning(f"Failed to send media: {media_error}")
                caption += f"\n\n🔗 Direct Link: {media_url}"
                await message.reply(caption)
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
            logger.error(f"Check command error: {e}")

    async def handle_test_catbox(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
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
                await test_msg.edit(f"❌ Catbox Connection Failed\n\nError: {result.get('error', 'Unknown error')}")
        except Exception as e:
            await test_msg.edit(f"❌ Test failed: {str(e)}")

    async def handle_upload_speed(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        try:
            stats = self.upload_flow.upload_stats
            total_uploads = stats['total_uploads']
            if total_uploads == 0:
                await message.reply("📊 No uploads recorded yet. Use /upload to start!")
                return
            avg_time = stats['total_time'] / total_uploads
            fastest = stats['fastest_upload']
            slowest = stats['slowest_upload']
            estimated_fast_uploads = total_uploads * 0.9
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

    async def handle_set_channel_command(self, message: Message):
        if not message.from_user or not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can set database channel!")
            return
        try:
            args = message.text.split()
            if len(args) < 2:
                await message.reply("❓ Usage: /setchannel <channel_id>\n\nExample: /setchannel -1001234567890")
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
                    await message.reply("❌ Invalid channel ID! Must be a number.\nExample: -1001234567890")
                    return

            try:
                chat = await self.app.get_chat(channel_id)
                test_msg = await self.app.send_message(
                    channel_id,
                    "✅ Database channel test successful! This message will be deleted."
                )
                await asyncio.sleep(2)
                await self.app.delete_messages(channel_id, test_msg.id)

                await database_channel_collection.update_one(
                    {},
                    {"$set": {
                        "channel_id": channel_id,
                        "channel_title": chat.title,
                        "set_by": message.from_user.id,
                        "set_at": datetime.utcnow()
                    }},
                    upsert=True
                )
                self.database_channel = channel_id
                self.upload_flow.set_database_channel(channel_id)

                await message.reply(
                    f"✅ Database channel set successfully!\n\n"
                    f"📡 Channel: {chat.title}\n"
                    f"🆔 ID: `{channel_id}`\n"
                    f"👤 Set by: {message.from_user.first_name}\n"
                    f"⏰ Set at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"⚠️ All future uploads will be broadcasted to this channel."
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

    async def handle_channel_info(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        try:
            channel_data = await database_channel_collection.find_one({})
            if not channel_data or 'channel_id' not in channel_data:
                await message.reply("❌ No database channel set!\n\nUse /setchannel to set one.")
                return
            channel_id = channel_data['channel_id']
            channel_title = channel_data.get('channel_title', 'Unknown')
            set_by = channel_data.get('set_by', 'Unknown')
            set_at = channel_data.get('set_at', datetime.utcnow())
            try:
                chat = await self.app.get_chat(channel_id)
                channel_title = chat.title
                channel_status = "✅ Accessible"
                try:
                    member = await self.app.get_chat_member(channel_id, (await self.app.get_me()).id)
                    can_post = member.privileges.can_post_messages if hasattr(member, 'privileges') else False
                    permissions = f"📤 Can Post: {'✅' if can_post else '❌'}"
                except:
                    permissions = "⚠️ Could not check permissions"
            except Exception as e:
                channel_status = f"❌ Inaccessible - {str(e)}"
                permissions = "❌ No permissions"
            if isinstance(set_at, datetime):
                set_at_str = set_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                set_at_str = str(set_at)
            await message.reply(
                f"📡 **Database Channel Information**\n\n"
                f"📝 **Title:** {channel_title}\n"
                f"🆔 **ID:** `{channel_id}`\n"
                f"🔧 **Status:** {channel_status}\n"
                f"🔑 **Permissions:** {permissions}\n"
                f"👤 **Set by:** `{set_by}`\n"
                f"⏰ **Set at:** {set_at_str}\n\n"
                f"ℹ️ **Note:** All uploads are broadcasted to this channel."
            )
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")

    async def handle_test_channel(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        try:
            channel_data = await database_channel_collection.find_one({})
            if not channel_data or 'channel_id' not in channel_data:
                await message.reply("❌ No database channel set!\n\nUse /setchannel first.")
                return
            channel_id = channel_data['channel_id']
            test_msg = await message.reply(f"🔄 Testing channel {channel_id}...")
            try:
                chat = await self.app.get_chat(channel_id)
                test_channel_msg = await self.app.send_message(
                    channel_id,
                    "📡 Bot channel test - This message will be deleted."
                )
                await self.app.delete_messages(channel_id, test_channel_msg.id)
                member = await self.app.get_chat_member(channel_id, (await self.app.get_me()).id)
                can_post = member.privileges.can_post_messages if hasattr(member, 'privileges') else False
                await test_msg.edit(
                    f"✅ Channel Test Successful!\n\n"
                    f"📝 Channel: {chat.title}\n"
                    f"🆔 ID: `{channel_id}`\n"
                    f"🔧 Status: ✅ Accessible\n"
                    f"📤 Can Post: {'✅ Yes' if can_post else '❌ No'}\n"
                    f"👤 Bot Status: {member.status}\n\n"
                    f"⚠️ {'Bot can post to this channel!' if can_post else 'Bot cannot post! Make bot admin with post permissions.'}"
                )
            except Exception as e:
                await test_msg.edit(
                    f"❌ Channel Test Failed!\n\n"
                    f"🆔 ID: `{channel_id}`\n"
                    f"🔧 Status: ❌ Inaccessible\n"
                    f"⚠️ Error: {str(e)}\n\n"
                    f"🔍 Make sure:\n"
                    f"1. Bot is added to the channel\n"
                    f"2. Bot has admin permissions\n"
                    f"3. Channel ID is correct"
                )
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")

    async def handle_remove_channel(self, message: Message):
        if not message.from_user or not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can remove database channel!")
            return
        try:
            channel_data = await database_channel_collection.find_one({})
            if not channel_data or 'channel_id' not in channel_data:
                await message.reply("❌ No database channel is currently set!")
                return
            channel_id = channel_data['channel_id']
            channel_title = channel_data.get('channel_title', 'Unknown')
            await database_channel_collection.delete_one({})
            self.database_channel = None
            self.upload_flow.set_database_channel(None)
            await message.reply(
                f"✅ Database channel removed successfully!\n\n"
                f"📝 Channel: {channel_title}\n"
                f"🆔 ID: `{channel_id}`\n\n"
                f"⚠️ Warning: Uploads will NOT be broadcasted until a new channel is set!\n"
                f"Use /setchannel to set a new broadcast channel."
            )
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")

    async def handle_ping_command(self, message: Message):
        start_time = datetime.now()
        ping_msg = await message.reply("🏓 Pong!")
        end_time = datetime.now()
        latency = (end_time - start_time).total_seconds() * 1000
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        channel_data = await database_channel_collection.find_one({})
        channel_status = f"✅ Set (ID: {channel_data['channel_id']})" if channel_data and 'channel_id' in channel_data else "❌ Not set"
        status_text = f"""🏓 **Bot Status**

📊 **System:**
• Latency: {latency:.0f}ms
• Uptime: {hours}h {minutes}m {seconds}s
• Uploads: {self.upload_count}

🌐 **Services:**
• Telegram: ✅ Connected
• MongoDB: ✅ Connected
• Catbox.moe: ✅ Ready
• Broadcast Channel: {channel_status}

👤 **User Info:**
• ID: {message.from_user.id}
• Name: {message.from_user.first_name}"""
        await ping_msg.edit(status_text)

    async def handle_stats_command(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        try:
            stats_msg = await message.reply("📊 Collecting statistics...")
            total_characters = await collection.count_documents({"deleted": False})
            deleted_characters = await collection.count_documents({"deleted": True})
            team_members = await upload_team_collection.count_documents({})
            catbox_uploads = await collection.count_documents({"upload_site": "catbox", "deleted": False})
            other_uploads = total_characters - catbox_uploads
            channel_data = await database_channel_collection.find_one({})
            if channel_data and 'channel_id' in channel_data:
                channel_status = f"✅ Set (ID: {channel_data['channel_id']})"
                try:
                    chat = await self.app.get_chat(channel_data['channel_id'])
                    channel_status = f"✅ {chat.title} (ID: {channel_data['channel_id']})"
                except:
                    pass
            else:
                channel_status = "❌ Not set"
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
                f"📡 **Database Channel:**\n"
                f"⚙️ Status: {channel_status}\n\n"
                f"⏱️ **Uptime:** {hours}h {minutes}m {seconds}s\n"
                f"📤 **Session Uploads:** {self.upload_count}\n\n"
                f"🌐 **Current Host:** Catbox.moe\n"
                f"⚡ **Upload System:** Ultra-fast Catbox"
            )
            await stats_msg.edit(stats_text)
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")

    async def handle_delete_command(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission!")
            return
        try:
            args = message.text.split()
            if len(args) < 2:
                await message.reply("❓ Usage: /delchar <character_id>")
                return
            char_id_input = args[1]
            result = await collection.update_one(
                {"id": char_id_input, "deleted": False},
                {"$set": {"deleted": True}}
            )
            if result.modified_count == 0 and char_id_input.isdigit():
                char_id_no_zeros = str(int(char_id_input))
                result = await collection.update_one(
                    {"id": char_id_no_zeros, "deleted": False},
                    {"$set": {"deleted": True}}
                )
            if result.modified_count == 0 and char_id_input.isdigit():
                char_id_4digit = char_id_input.zfill(4)
                if char_id_4digit != char_id_input:
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
        if not message.from_user or message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
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
        if not message.from_user or message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
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

    async def send_startup_message_to_owner(self):
        try:
            owner_id = OWNER_ID
            channel_data = await database_channel_collection.find_one({})
            try:
                status_msg = f"""🤖 Catbox Bot Started ⚡

🔧 Bot: @{(await self.app.get_me()).username}
🌐 Database Channel: {'✅ Set' if channel_data and 'channel_id' in channel_data else '❌ Not set'}
{f'📡 Channel ID: {channel_data["channel_id"]}' if channel_data and 'channel_id' in channel_data else ''}

⚡ Target: Uploads under 8 seconds
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'⚠️ WARNING: No database channel set! Uploads will not be broadcasted.' if not channel_data or 'channel_id' not in channel_data else ''}

Use /setchannel to set the broadcast channel."""
                await self.app.send_message(owner_id, status_msg)
                logger.info(f"✅ Startup message sent to owner ID: {owner_id}")
            except Exception as e:
                logger.error(f"Failed to send startup to {owner_id}: {e}")
        except Exception as e:
            logger.error(f"Startup message error: {e}")

    async def initialize_owner(self):
        try:
            await upload_team_collection.delete_many({})
            logger.info("✅ Cleared all existing team members")
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
                logger.info(f"✅ Owner added: {user.first_name} (ID: {OWNER_ID})")
            except Exception as e:
                logger.error(f"❌ Failed to add owner: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize owner: {e}")

    async def try_set_default_channel(self):
        """Attempt to set the default channel from config if none exists."""
        if DEFAULT_DATABASE_CHANNEL:
            existing = await database_channel_collection.find_one({})
            if not existing:
                logger.info(f"No database channel set. Attempting to set default: {DEFAULT_DATABASE_CHANNEL}")
                try:
                    chat = await self.app.get_chat(DEFAULT_DATABASE_CHANNEL)
                    # Test sending a message
                    test_msg = await self.app.send_message(
                        DEFAULT_DATABASE_CHANNEL,
                        "🤖 Bot started – setting default database channel."
                    )
                    await self.app.delete_messages(DEFAULT_DATABASE_CHANNEL, test_msg.id)
                    await database_channel_collection.update_one(
                        {},
                        {"$set": {
                            "channel_id": DEFAULT_DATABASE_CHANNEL,
                            "channel_title": chat.title,
                            "set_by": "system",
                            "set_at": datetime.utcnow()
                        }},
                        upsert=True
                    )
                    self.database_channel = DEFAULT_DATABASE_CHANNEL
                    self.upload_flow.set_database_channel(DEFAULT_DATABASE_CHANNEL)
                    logger.info(f"✅ Default database channel set to {DEFAULT_DATABASE_CHANNEL}")
                except Exception as e:
                    logger.error(f"❌ Failed to set default channel {DEFAULT_DATABASE_CHANNEL}: {e}")

    async def start(self):
        logger.info("Starting Catbox Upload Bot...")
        try:
            await self.app.start()
            logger.info("Bot client started")
            me = await self.app.get_me()
            logger.info(f"Bot started as @{me.username}")

            await self.initialize_owner()

            # Load database channel from DB or try default
            channel_data = await database_channel_collection.find_one({})
            if channel_data and 'channel_id' in channel_data:
                self.database_channel = channel_data['channel_id']
                self.upload_flow.set_database_channel(self.database_channel)
                logger.info(f"Database channel loaded: {self.database_channel}")
            else:
                await self.try_set_default_channel()

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

            await self.send_startup_message_to_owner()
            logger.info("Bot is now running. Press Ctrl+C to stop.")
            await idle()
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.stop()

    async def stop(self):
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
