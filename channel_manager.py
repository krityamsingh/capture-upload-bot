import asyncio
import logging
from typing import List, Dict, Any
from database import permanent_channels_collection
from config import PERMANENT_BROADCAST_CHANNELS
from pyrogram import Client
from pyrogram.errors import ChannelInvalid, ChannelPrivate, ChatAdminRequired

logger = logging.getLogger(__name__)

class ChannelManager:
    def __init__(self, app: Client):
        self.app = app
        self.permanent_channels = PERMANENT_BROADCAST_CHANNELS
        self.working_channels: List[int] = []

    async def initialize_channels(self):
        logger.info(f"Initializing {len(self.permanent_channels)} permanent channels...")
        self.working_channels = []

        for channel_id in self.permanent_channels:
            try:
                logger.info(f"Testing channel {channel_id}...")
                try:
                    chat = await self.app.get_chat(channel_id)
                    logger.info(f"Found channel: {chat.title or 'No title'} (ID: {channel_id})")

                    test_msg = await self.app.send_message(
                        channel_id,
                        "📡 Bot connection test... This message will be deleted.",
                        disable_notification=True
                    )
                    await self.app.delete_messages(channel_id, test_msg.id)

                    self.working_channels.append(channel_id)
                    await self.mark_channel_working(channel_id)
                    logger.info(f"✅ Channel {channel_id} is working!")

                except ChannelPrivate:
                    logger.error(f"❌ Channel {channel_id} is PRIVATE. Bot is NOT a member.")
                    logger.error(f"   → Solution: Add @{(await self.app.get_me()).username} to the channel")
                    await self.mark_channel_broken(channel_id, "Bot not in channel (private)")
                except ChannelInvalid:
                    logger.error(f"❌ Channel {channel_id} is INVALID or doesn't exist.")
                    await self.mark_channel_broken(channel_id, "Invalid channel ID")
                except ChatAdminRequired:
                    logger.error(f"❌ Channel {channel_id} - Bot is NOT an ADMIN.")
                    await self.mark_channel_broken(channel_id, "Bot not admin")
                except Exception as e:
                    logger.error(f"❌ Channel {channel_id} error: {str(e)[:100]}")
                    await self.mark_channel_broken(channel_id, str(e))

            except Exception as e:
                logger.error(f"Unexpected error with channel {channel_id}: {e}")
                await self.mark_channel_broken(channel_id, "Unexpected error")

        logger.info(f"Initialization complete. {len(self.working_channels)}/{len(self.permanent_channels)} channels working")

        if len(self.working_channels) == 0:
            logger.error("🔴 CRITICAL: No working channels!")
        else:
            logger.info(f"🟢 Working channels: {self.working_channels}")
            await self.try_fix_broken_channels()

    async def try_fix_broken_channels(self):
        logger.info("Attempting to fix broken channels...")
        for channel_id in self.permanent_channels:
            if channel_id not in self.working_channels:
                fixed = await self.fix_channel_access(channel_id)
                if fixed:
                    self.working_channels.append(channel_id)
                    await self.mark_channel_working(channel_id)
                    logger.info(f"🟢 Fixed channel {channel_id}")

    async def fix_channel_access(self, channel_id: int) -> bool:
        logger.info(f"Trying to fix channel {channel_id}...")
        formats_to_try = [
            channel_id,
            int(f"-100{abs(channel_id)}"),
            abs(channel_id),
        ]
        if str(channel_id).startswith("-100"):
            formats_to_try.append(int(str(channel_id)[4:]))

        for fmt in formats_to_try:
            try:
                if fmt == channel_id:
                    continue
                logger.info(f"  Trying format: {fmt}")
                chat = await self.app.get_chat(fmt)
                test_msg = await self.app.send_message(
                    fmt,
                    "📡 Testing fixed channel ID...",
                    disable_notification=True
                )
                await self.app.delete_messages(fmt, test_msg.id)
                logger.info(f"  ✅ Format {fmt} works! Channel: {chat.title}")
                return True
            except Exception:
                continue
        return False

    async def test_channel_access(self, channel_id: int) -> Dict[str, Any]:
        try:
            chat = await self.app.get_chat(channel_id)
            member = await self.app.get_chat_member(channel_id, (await self.app.get_me()).id)
            can_post = member.privileges.can_post_messages if hasattr(member, 'privileges') else False

            test_msg = await self.app.send_message(
                channel_id,
                "📡 Channel access test...",
                disable_notification=True
            )
            await self.app.delete_messages(channel_id, test_msg.id)

            return {
                "success": True,
                "channel_id": channel_id,
                "title": chat.title,
                "type": str(chat.type),
                "can_post": can_post,
                "member_status": str(member.status),
                "message": "Channel is accessible and bot can post"
            }

        except ChannelPrivate as e:
            return {
                "success": False,
                "channel_id": channel_id,
                "error": "ChannelPrivate",
                "message": "Bot is not a member of this private channel",
                "solution": f"Add @{(await self.app.get_me()).username} to the channel"
            }
        except ChannelInvalid as e:
            return {
                "success": False,
                "channel_id": channel_id,
                "error": "ChannelInvalid",
                "message": "Channel doesn't exist or ID is incorrect",
                "solution": "Check the channel ID"
            }
        except ChatAdminRequired as e:
            return {
                "success": False,
                "channel_id": channel_id,
                "error": "ChatAdminRequired",
                "message": "Bot is not an administrator in this channel",
                "solution": "Make bot an admin with post permissions"
            }
        except Exception as e:
            return {
                "success": False,
                "channel_id": channel_id,
                "error": str(type(e).__name__),
                "message": str(e),
                "solution": "Check bot permissions and channel access"
            }

    async def mark_channel_working(self, channel_id: int):
        await permanent_channels_collection.update_one(
            {"channel_id": channel_id},
            {"$set": {
                "channel_id": channel_id,
                "status": "working",
                "last_checked": asyncio.get_event_loop().time(),
                "last_success": asyncio.get_event_loop().time()
            }},
            upsert=True
        )

    async def mark_channel_broken(self, channel_id: int, reason: str = "Unknown"):
        await permanent_channels_collection.update_one(
            {"channel_id": channel_id},
            {"$set": {
                "channel_id": channel_id,
                "status": "broken",
                "error": reason,
                "last_checked": asyncio.get_event_loop().time()
            }},
            upsert=True
        )

    async def get_working_channels(self) -> List[int]:
        return self.working_channels

    async def get_channel_status_report(self) -> str:
        report_lines = ["📡 **Channel Status Report**\n"]
        for channel_id in self.permanent_channels:
            result = await self.test_channel_access(channel_id)
            if result["success"]:
                report_lines.append(f"✅ **{result['title']}**")
                report_lines.append(f"   ├─ ID: `{channel_id}`")
                report_lines.append(f"   ├─ Type: {result['type']}")
                report_lines.append(f"   ├─ Can Post: {'✅' if result['can_post'] else '❌'}")
                report_lines.append(f"   └─ Status: {result['message']}\n")
            else:
                report_lines.append(f"❌ **Channel {channel_id}**")
                report_lines.append(f"   ├─ Error: {result['error']}")
                report_lines.append(f"   ├─ Message: {result['message']}")
                report_lines.append(f"   └─ Solution: {result.get('solution', 'Unknown')}\n")
        return "\n".join(report_lines)

    async def force_refresh_channels(self):
        logger.info("Force refreshing all channels...")
        await self.initialize_channels()
        return len(self.working_channels)
