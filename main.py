from pyrogram import Client, filters, enums, idle
from pyrogram.types import Message, CallbackQuery
import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from typing import List, Optional
import aiohttp
from io import BytesIO

from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URL, OWNER_ID, OWNER_IDS, CATBOX_API_KEY
from upload_flow import UploadFlow
from team_manager import TeamManager
from utils import UploadUtils
from database import upload_team_collection, collection, database_channel_collection, counters_collection
from catbox import CatboxUploader

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
        self.start_time = datetime.now(timezone.utc)
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

        # NEW COMMAND: /replaceurl
        @self.app.on_message(filters.command("replaceurl") & filters.private)
        async def replace_url_command(client, message: Message):
            await self.handle_replace_url(message)

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
/replaceurl - Replace character's media URL
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

            # Find character (multiple ID formats handled by utils)
            character = await self.find_character_by_id(char_id_input)
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

            # Try sending with URL first
            try:
                if img_type == 'photo':
                    await message.reply_photo(photo=media_url, caption=caption)
                elif img_type == 'video':
                    await message.reply_video(video=media_url, caption=caption)
                else:
                    await message.reply_document(document=media_url, caption=caption)
                return
            except Exception as e:
                logger.warning(f"Direct URL send failed: {e}")

            # Enhanced fallback: download with browser User-Agent
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(media_url, headers=headers) as resp:
                        if resp.status != 200:
                            raise Exception(f"HTTP {resp.status}")
                        data = await resp.read()
                        file_like = BytesIO(data)

                if img_type == 'photo':
                    await message.reply_photo(photo=file_like, caption=caption)
                elif img_type == 'video':
                    await message.reply_video(video=file_like, caption=caption)
                else:
                    await message.reply_document(document=file_like, caption=caption)
            except Exception as download_error:
                logger.error(f"Download fallback failed: {download_error}", exc_info=True)
                caption += f"\n\n🔗 Direct Link: {media_url}"
                await message.reply(caption)

        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
            logger.error(f"Check command error: {e}")

    async def find_character_by_id(self, char_id_input: str):
        """Helper to find character with various ID formats."""
        # Exact match
        character = await collection.find_one({"id": char_id_input, "deleted": False})
        if character:
            return character

        if char_id_input.isdigit():
            # Remove leading zeros
            no_zeros = str(int(char_id_input))
            if no_zeros != char_id_input:
                character = await collection.find_one({"id": no_zeros, "deleted": False})
                if character:
                    return character
            # 4-digit format
            four_digit = char_id_input.zfill(4)
            if four_digit != char_id_input:
                character = await collection.find_one({"id": four_digit, "deleted": False})
                if character:
                    return character
        return None

    async def handle_replace_url(self, message: Message):
        """Handle /replaceurl <character_id> <new_url>"""
        if not message.from_user:
            return

        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission to replace character URLs!")
            return

        args = message.text.split()
        if len(args) < 3:
            await message.reply("❓ Usage: /replaceurl <character_id> <new_url>\n\nExample: /replaceurl 120 https://files.catbox.moe/newimage.jpg")
            return

        char_id_input = args[1]
        new_url = args[2]

        # Basic URL validation
        if not new_url.startswith(('http://', 'https://')):
            await message.reply("❌ Invalid URL! Must start with http:// or https://")
            return

        character = await self.find_character_by_id(char_id_input)
        if not character:
            await message.reply(f"❌ Character ID {char_id_input} not found!")
            return

        # Determine new media type from URL extension (optional)
        ext = new_url.lower().split('.')[-1] if '.' in new_url else ''
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            new_type = 'photo'
        elif ext in ['mp4', 'mov', 'avi', 'webm']:
            new_type = 'video'
        else:
            new_type = character.get('img_type', 'photo')  # fallback to old type

        # Update the character
        await collection.update_one(
            {"id": character['id']},
            {"$set": {
                "img_url": new_url,
                "img_type": new_type,
                "upload_site": "custom",  # mark as manually replaced
                "replaced_at": datetime.now(timezone.utc),
                "replaced_by": message.from_user.id
            }}
        )

        await message.reply(
            f"✅ Character {character['id']} URL updated successfully!\n\n"
            f"📁 New URL: {new_url}\n"
            f"📁 New Type: {new_type}"
        )
        logger.info(f"User {message.from_user.id} replaced URL for character {character['id']} with {new_url}")

    async def handle_test_catbox(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
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
            return

        stats = self.upload_flow.upload_stats
        total = stats['total_uploads']
        if total == 0:
            await message.reply("📊 No uploads recorded yet. Use /upload to start!")
            return

        avg = stats['total_time'] / total
        fastest = stats['fastest_upload']
        slowest = stats['slowest_upload']
        speed_text = f"""📊 Catbox Upload Speed Statistics ⚡

📈 Total Uploads: {total}
⚡ Fastest Upload: {fastest:.2f}s
🐌 Slowest Upload: {slowest:.2f}s
📊 Average Upload: {avg:.2f}s
🎯 Target Speed: Under 8 seconds

📊 Performance Analysis:
• Average speed: {(1024 / avg):.1f} KB/s (if 1MB file)
• Service: Catbox.moe (Ultra-fast hosting)

💡 Tips for faster uploads:
1. Use compressed images (JPG/WebP)
2. Keep videos under 20MB
3. Stable internet connection
4. Use during off-peak hours

🚀 Current Status: {'⚡ Excellent' if avg < 8 else '⚠️ Needs improvement'}"""
        await message.reply(speed_text)

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
                chat = await self.app.get_chat(channel_input)
                channel_id = chat.id
            else:
                channel_id = int(channel_input)

            # Test access
            chat = await self.app.get_chat(channel_id)
            test_msg = await self.app.send_message(channel_id, "✅ Database channel test successful. This message will be deleted.")
            await asyncio.sleep(2)
            await self.app.delete_messages(channel_id, test_msg.id)

            await database_channel_collection.update_one(
                {},
                {"$set": {
                    "channel_id": channel_id,
                    "channel_title": chat.title,
                    "set_by": message.from_user.id,
                    "set_at": datetime.now(timezone.utc)
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
                f"⏰ Set at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"⚠️ All future uploads will be broadcasted to this channel."
            )

        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")

    async def handle_channel_info(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
            return

        channel_data = await database_channel_collection.find_one({})
        if not channel_data or 'channel_id' not in channel_data:
            await message.reply("❌ No database channel set!\n\nUse /setchannel to set a broadcast channel.")
            return

        channel_id = channel_data['channel_id']
        channel_title = channel_data.get('channel_title', 'Unknown')
        set_by = channel_data.get('set_by', 'Unknown')
        set_at = channel_data.get('set_at', datetime.now(timezone.utc))

        try:
            chat = await self.app.get_chat(channel_id)
            channel_title = chat.title
            status = "✅ Accessible"
        except:
            status = "❌ Inaccessible"

        set_at_str = set_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(set_at, 'strftime') else str(set_at)

        await message.reply(
            f"📡 **Database Channel Information**\n\n"
            f"📝 **Title:** {channel_title}\n"
            f"🆔 **ID:** `{channel_id}`\n"
            f"🔧 **Status:** {status}\n"
            f"👤 **Set by:** `{set_by}`\n"
            f"⏰ **Set at:** {set_at_str}\n\n"
            f"ℹ️ **Note:** All uploads are broadcasted to this channel."
        )

    async def handle_test_channel(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
            return

        channel_data = await database_channel_collection.find_one({})
        if not channel_data or 'channel_id' not in channel_data:
            await message.reply("❌ No database channel set!")
            return

        channel_id = channel_data['channel_id']
        test_msg = await message.reply(f"🔄 Testing channel {channel_id}...")
        try:
            chat = await self.app.get_chat(channel_id)
            test_channel_msg = await self.app.send_message(channel_id, "📡 Bot channel test - This message will be deleted.")
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

    async def handle_remove_channel(self, message: Message):
        if not message.from_user or not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can remove database channel!")
            return

        channel_data = await database_channel_collection.find_one({})
        if not channel_data:
            await message.reply("❌ No database channel is currently set!")
            return

        channel_id = channel_data.get('channel_id')
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

    async def handle_ping_command(self, message: Message):
        start = datetime.now(timezone.utc)
        ping_msg = await message.reply("🏓 Pong!")
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        uptime = datetime.now(timezone.utc) - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        channel_data = await database_channel_collection.find_one({})
        channel_status = f"✅ Set (ID: {channel_data['channel_id']})" if channel_data and 'channel_id' in channel_data else "❌ Not set"

        status_text = f"""🏓 **Bot Status**

📊 **System:**
• Latency: {latency:.0f}ms
• Uptime: {hours}h {minutes}m {seconds}s
• Uploads: {self.upload_flow.upload_stats['total_uploads']}

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
            return

        stats_msg = await message.reply("📊 Collecting statistics...")
        total_characters = await collection.count_documents({"deleted": False})
        deleted = await collection.count_documents({"deleted": True})
        team = await upload_team_collection.count_documents({})
        catbox = await collection.count_documents({"upload_site": "catbox", "deleted": False})
        other = total_characters - catbox

        channel_data = await database_channel_collection.find_one({})
        if channel_data and 'channel_id' in channel_data:
            try:
                chat = await self.app.get_chat(channel_data['channel_id'])
                channel_status = f"✅ {chat.title} (ID: {channel_data['channel_id']})"
            except:
                channel_status = f"✅ Set (ID: {channel_data['channel_id']})"
        else:
            channel_status = "❌ Not set"

        uptime = datetime.now(timezone.utc) - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        text = (
            f"📊 **Bot Statistics**\n\n"
            f"👥 **Characters:**\n"
            f"📈 Total: {total_characters}\n"
            f"⚡ Catbox Uploads: {catbox}\n"
            f"📂 Other Uploads: {other}\n"
            f"🗑️ Deleted: {deleted}\n"
            f"✅ Active: {total_characters - deleted}\n\n"
            f"👤 **Team Members:** {team}\n\n"
            f"📡 **Database Channel:**\n"
            f"⚙️ Status: {channel_status}\n\n"
            f"⏱️ **Uptime:** {hours}h {minutes}m {seconds}s\n"
            f"📤 **Session Uploads:** {self.upload_flow.upload_stats['total_uploads']}\n\n"
            f"🌐 **Current Host:** Catbox.moe\n"
            f"⚡ **Upload System:** Ultra-fast Catbox"
        )
        await stats_msg.edit(text)

    async def handle_delete_command(self, message: Message):
        if not message.from_user or not await UploadUtils.is_uploader(message.from_user.id):
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply("❓ Usage: /delchar <character_id>")
            return

        char_id_input = args[1]
        char = await self.find_character_by_id(char_id_input)
        if not char:
            await message.reply(f"❌ Character ID {char_id_input} not found.")
            return

        await collection.update_one({"id": char['id']}, {"$set": {"deleted": True}})
        await message.reply(f"✅ Character ID {char['id']} deleted.")

    async def handle_add_team_command(self, message: Message):
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply("❌ This command can only be used in groups!")
            return
        if not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can add team members!")
            return

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
            except:
                await message.reply("❌ Invalid user ID!")
                return

        if user_id:
            await self.team_manager.add_team_member(message, user_id)

    async def handle_remove_team_command(self, message: Message):
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply("❌ This command can only be used in groups!")
            return
        if not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can remove team members!")
            return

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
            except:
                await message.reply("❌ Invalid user ID!")
                return

        if user_id:
            await self.team_manager.remove_team_member(message, user_id)

    async def send_startup_message_to_owner(self):
        try:
            owner_id = OWNER_ID
            channel_data = await database_channel_collection.find_one({})
            msg = f"""🤖 Catbox Bot Started ⚡

🔧 Bot: @{(await self.app.get_me()).username}
🌐 Database Channel: {'✅ Set' if channel_data and 'channel_id' in channel_data else '❌ Not set'}
{f'📡 Channel ID: {channel_data["channel_id"]}' if channel_data and 'channel_id' in channel_data else ''}

⚡ Target: Uploads under 8 seconds
🕐 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC

{'⚠️ WARNING: No database channel set! Uploads will not be broadcasted.' if not channel_data or 'channel_id' not in channel_data else ''}

Use /setchannel to set the broadcast channel."""
            await self.app.send_message(owner_id, msg)
            logger.info(f"✅ Startup message sent to owner ID: {owner_id}")
        except Exception as e:
            logger.error(f"Startup message error: {e}")

    async def initialize_owner(self):
        """Add owners from OWNER_IDS if they don't exist (without wiping team)."""
        for owner_id in OWNER_IDS:
            existing = await upload_team_collection.find_one({"user_id": owner_id})
            if not existing:
                try:
                    user = await self.app.get_users(owner_id)
                    await upload_team_collection.insert_one({
                        "user_id": owner_id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "role": "owner",
                        "added_by": owner_id,
                        "added_at": datetime.now(timezone.utc)
                    })
                    logger.info(f"✅ Owner added: {user.first_name} (ID: {owner_id})")
                except Exception as e:
                    logger.error(f"❌ Failed to add owner {owner_id}: {e}")

    async def start(self):
        logger.info("Starting Catbox Upload Bot...")
        try:
            await self.app.start()
            logger.info("Bot client started")
            me = await self.app.get_me()
            logger.info(f"Bot started as @{me.username}")

            await self.initialize_owner()

            channel_data = await database_channel_collection.find_one({})
            if channel_data and 'channel_id' in channel_data:
                self.database_channel = channel_data['channel_id']
                self.upload_flow.set_database_channel(self.database_channel)
                logger.info(f"Database channel loaded: {self.database_channel}")
            else:
                logger.warning("No database channel set. Use /setchannel to set one.")

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
