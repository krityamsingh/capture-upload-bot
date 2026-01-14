import asyncio
import logging
from typing import List, Dict, Any
from database import permanent_channels_collection
from config import PERMANENT_BROADCAST_CHANNELS
from pyrogram import Client

logger = logging.getLogger(__name__)

class ChannelManager:
    def __init__(self, app: Client):
        self.app = app
        self.permanent_channels = PERMANENT_BROADCAST_CHANNELS
        self.working_channels: List[int] = []
        
    async def initialize_channels(self):
        """Initialize and verify all permanent channels"""
        logger.info(f"Initializing {len(self.permanent_channels)} permanent channels...")
        
        for channel_id in self.permanent_channels:
            try:
                # Check if channel is already marked as working in DB
                channel_data = await permanent_channels_collection.find_one({"channel_id": channel_id})
                
                if channel_data and channel_data.get("status") == "working":
                    # If previously working, test it
                    is_accessible = await self.test_channel_access(channel_id)
                    
                    if is_accessible:
                        self.working_channels.append(channel_id)
                        logger.info(f"Channel {channel_id} restored from DB (Working)")
                    else:
                        # Try to fix access
                        fixed = await self.fix_channel_access(channel_id)
                        if fixed:
                            self.working_channels.append(channel_id)
                            await self.mark_channel_working(channel_id)
                            logger.info(f"Channel {channel_id} fixed and added to working list")
                else:
                    # New channel, test and add if working
                    is_accessible = await self.test_channel_access(channel_id)
                    
                    if is_accessible:
                        self.working_channels.append(channel_id)
                        await self.mark_channel_working(channel_id)
                        logger.info(f"Channel {channel_id} added to working list")
                    else:
                        # Try to fix
                        fixed = await self.fix_channel_access(channel_id)
                        if fixed:
                            self.working_channels.append(channel_id)
                            await self.mark_channel_working(channel_id)
                            logger.info(f"Channel {channel_id} fixed and added to working list")
                        else:
                            await self.mark_channel_broken(channel_id)
                            logger.warning(f"Channel {channel_id} cannot be accessed")
                            
            except Exception as e:
                logger.error(f"Error initializing channel {channel_id}: {e}")
                await self.mark_channel_broken(channel_id)
        
        logger.info(f"Initialization complete. {len(self.working_channels)}/{len(self.permanent_channels)} channels working")
        
        if len(self.working_channels) == 0:
            logger.error("CRITICAL: No working channels! Uploads will fail.")
        else:
            logger.info(f"Working channels: {self.working_channels}")
    
    async def test_channel_access(self, channel_id: int) -> bool:
        """Test if bot can access a channel"""
        try:
            # Try to get chat info
            chat = await self.app.get_chat(channel_id)
            
            # Try to send a test message and delete it
            test_msg = await self.app.send_message(
                channel_id,
                "📡 Channel connection test...",
                disable_notification=True
            )
            await self.app.delete_messages(channel_id, test_msg.id)
            
            logger.info(f"✅ Channel accessible: {chat.title} (ID: {channel_id})")
            return True
            
        except Exception as e:
            logger.warning(f"❌ Channel {channel_id} inaccessible: {str(e)[:100]}")
            return False
    
    async def fix_channel_access(self, channel_id: int) -> bool:
        """Try to fix channel access issues"""
        logger.info(f"Attempting to fix channel {channel_id}...")
        
        # Try different channel ID formats
        channel_variants = [
            channel_id,  # Original
            abs(channel_id),  # Positive version
        ]
        
        # For -100 prefixed channels, try without -100
        if str(channel_id).startswith("-100"):
            channel_variants.append(int(str(channel_id).replace("-100", "")))
        
        # For non -100 channels, try with -100 prefix
        elif not str(channel_id).startswith("-100") and channel_id < 0:
            channel_variants.append(int(f"-100{abs(channel_id)}"))
        
        for variant in channel_variants:
            try:
                if await self.test_channel_access(variant):
                    logger.info(f"Fixed channel ID: {channel_id} -> {variant}")
                    return True
            except:
                continue
        
        return False
    
    async def mark_channel_working(self, channel_id: int):
        """Mark channel as working in database"""
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
    
    async def mark_channel_broken(self, channel_id: int):
        """Mark channel as broken in database"""
        await permanent_channels_collection.update_one(
            {"channel_id": channel_id},
            {"$set": {
                "channel_id": channel_id,
                "status": "broken",
                "last_checked": asyncio.get_event_loop().time(),
                "error": "Channel inaccessible"
            }},
            upsert=True
        )
    
    async def get_working_channels(self) -> List[int]:
        """Get list of working channels"""
        if not self.working_channels:
            await self.initialize_channels()
        return self.working_channels
    
    async def broadcast_status(self) -> str:
        """Get broadcast channels status report"""
        status_lines = []
        
        for channel_id in self.permanent_channels:
            is_working = channel_id in self.working_channels
            status = "✅ WORKING" if is_working else "❌ BROKEN"
            
            try:
                chat = await self.app.get_chat(channel_id)
                title = chat.title
            except:
                title = "Unknown"
            
            status_lines.append(f"{status} - {title} (ID: {channel_id})")
        
        return "📡 **Permanent Broadcast Channels Status:**\n\n" + "\n".join(status_lines)
    
    async def force_refresh_channels(self):
        """Force refresh all channels"""
        logger.info("Force refreshing all channels...")
        self.working_channels = []
        await self.initialize_channels()
        return len(self.working_channels)
