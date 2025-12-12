# ==================== UTILS/HELPERS.PY ====================
# utils/helpers.py - UPDATED
import logging
import aiohttp
import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pyrogram import Client
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ForceReply

from config import config
from database.mongodb import db
from database.models import UserSession

logger = logging.getLogger(__name__)

class UploadService:
    """Handles media uploads exclusively with Catbox service"""
    
    @staticmethod
    async def upload_to_catbox(file_path: str, filename: str) -> Optional[str]:
        """Upload file to Catbox.moe with improved error handling and faster timeout"""
        try:
            # Use shorter timeout for faster response
            timeout = aiohttp.ClientTimeout(total=30)  # Reduced from 300 to 30 seconds
            async with aiohttp.ClientSession(timeout=timeout) as session:
                with open(file_path, 'rb') as file:
                    form_data = aiohttp.FormData()
                    form_data.add_field('reqtype', 'fileupload')
                    form_data.add_field('fileToUpload', file, filename=filename)
                    
                    async with session.post('https://catbox.moe/user/api.php', data=form_data) as response:
                        if response.status == 200:
                            media_url = await response.text()
                            if media_url and media_url.startswith('http'):
                                logger.info(f"Successfully uploaded to Catbox: {media_url}")
                                return media_url.strip()
                        logger.error(f"Catbox upload failed with status {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Catbox upload timeout")
            return None
        except Exception as e:
            logger.error(f"Catbox upload error: {e}")
            return None

class Helpers:
    """Utility functions for the bot with Catbox-only upload capabilities"""
    
    def __init__(self):
        self.upload_service = UploadService()
    
    @staticmethod
    def force_reply():
        """Create a force reply markup"""
        return ForceReply(selective=True)
    
    async def upload_media_with_fallback(
        self, 
        client: Client, 
        message: Message,
        status_callback: callable = None
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Upload media using Catbox service only with optimized speed
        Returns: (media_url, media_type)
        """
        try:
            # Determine media type and file ID
            media_type = None
            file_id = None
            filename = f"media_{uuid.uuid4().hex[:8]}"
            
            if message.photo:
                file_id = message.photo.file_id
                media_type = "photo"
                filename += ".jpg"
            elif message.video:
                file_id = message.video.file_id
                media_type = "video"
                filename = message.video.file_name or f"{filename}.mp4"
            elif message.audio:
                file_id = message.audio.file_id
                media_type = "audio"
                filename = message.audio.file_name or f"{filename}.mp3"
            elif message.document:
                file_id = message.document.file_id
                media_type = "document"
                filename = message.document.file_name or f"{filename}.bin"
            else:
                return None, None
            
            # Check file size
            file_size = 0
            if message.photo:
                file_size = message.photo.file_size or 0
            elif message.video:
                file_size = message.video.file_size or 0
            elif message.audio:
                file_size = message.audio.file_size or 0
            elif message.document:
                file_size = message.document.file_size or 0
                
            if file_size > config.MAX_FILE_SIZE:
                logger.error(f"File too large: {file_size} bytes")
                return None, None
            
            # Download file to temporary location with progress
            if status_callback:
                await status_callback("📥 Downloading media file...")
                
            # Use faster download method with chunk size optimization
            file_path = await client.download_media(
                file_id, 
                file_name=filename,
                progress=self._download_progress,
                progress_args=(status_callback,)
            )
            
            if not file_path:
                logger.error("Failed to download media file")
                return None, None
            
            try:
                # Upload to Catbox only with faster timeout
                if status_callback:
                    await status_callback("🔄 Uploading to Catbox... (This should take 5-8 seconds)")
                    
                media_url = await self.upload_service.upload_to_catbox(file_path, filename)
                
                if media_url:
                    if status_callback:
                        await status_callback("✅ Upload successful!")
                    return media_url, media_type
                else:
                    if status_callback:
                        await status_callback("❌ Catbox upload failed")
                    return None, None
                    
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")
            
        except Exception as e:
            logger.error(f"Error in upload_media_with_fallback: {e}")
            if status_callback:
                await status_callback("❌ Upload process failed")
            return None, None
    
    async def _download_progress(self, current, total, status_callback):
        """Progress callback for download with percentage"""
        if status_callback and total > 0:
            percentage = (current / total) * 100
            if int(percentage) % 25 == 0:  # Update at 25%, 50%, 75%, 100%
                await status_callback(f"📥 Downloading... {int(percentage)}%")
    
    @staticmethod
    def format_character_preview(session: UserSession) -> str:
        """Format character data for preview"""
        preview = "📋 **Character Upload Preview**\n\n"
        preview += f"👤 **Name:** {session.char_name}\n"
        preview += f"🎞️ **Anime:** {session.anime_name}\n"
        preview += f"🏅 **Rarity:** {session.rarity}\n"
        
        if session.subrarity:
            preview += f"💠 **Sub-Rarity:** {session.subrarity}\n"
        
        if session.media_url:
            preview += f"📸 **Media:** Uploaded successfully\n"
        else:
            preview += f"📸 **Media:** Waiting for upload\n"
        
        return preview
    
    @staticmethod
    def format_log_message(character_data: Dict[str, Any], username: str, user_id: int) -> str:
        """Format character data for log channels"""
        log_msg = "🆕 **New Character Added!**\n\n"
        log_msg += f"👤 **Name:** {character_data['char_name']}\n"
        log_msg += f"🎞️ **Anime:** {character_data['anime_name']}\n"
        log_msg += f"🏅 **Rarity:** {character_data['rarity']}\n"
        
        if character_data.get('subrarity'):
            log_msg += f"💠 **Sub-Rarity:** {character_data['subrarity']}\n"
        
        log_msg += f"🧍 **Added by:** @{username} ({user_id})\n"
        log_msg += f"🆔 **Character ID:** {character_data['character_id']}\n\n"
        
        if character_data.get('media_url'):
            log_msg += "📸 Character media uploaded successfully\n\n"
        
        log_msg += "**Note:** Character IDs increase automatically — next one will be " \
                  f"{character_data['character_id'] + 1}, {character_data['character_id'] + 2}, etc."
        
        return log_msg
    
    @staticmethod
    async def send_to_log_channels(
        client: Client, 
        character_data: Dict[str, Any], 
        username: str,
        user_id: int,
        db
    ) -> bool:
        """Send character data to configured log channels - FIXED: Media URL issues"""
        try:
            log_config = await db.get_log_config()
            log_message = Helpers.format_log_message(character_data, username, user_id)
            
            success = True
            sent_to = []
            
            # Send to log_chat_1
            if log_config.get('log_chat_1'):
                try:
                    # Send media if available and valid
                    if character_data.get('media_url') and character_data.get('media_type'):
                        try:
                            if character_data.get('media_type') == 'photo':
                                await client.send_photo(
                                    chat_id=log_config['log_chat_1'],
                                    photo=character_data['media_url'],
                                    caption=log_message
                                )
                            elif character_data.get('media_type') == 'video':
                                await client.send_video(
                                    chat_id=log_config['log_chat_1'],
                                    video=character_data['media_url'],
                                    caption=log_message
                                )
                            elif character_data.get('media_type') == 'audio':
                                await client.send_audio(
                                    chat_id=log_config['log_chat_1'],
                                    audio=character_data['media_url'],
                                    caption=log_message
                                )
                            else:
                                await client.send_document(
                                    chat_id=log_config['log_chat_1'],
                                    document=character_data['media_url'],
                                    caption=log_message
                                )
                        except Exception as e:
                            logger.warning(f"Failed to send media to log_chat_1: {e}")
                            # Fallback to text message with URL
                            log_message += f"\n\n📸 **Media URL:** {character_data['media_url']}"
                            await client.send_message(
                                chat_id=log_config['log_chat_1'],
                                text=log_message
                            )
                    else:
                        # No media, send text only
                        await client.send_message(
                            chat_id=log_config['log_chat_1'],
                            text=log_message
                        )
                    sent_to.append("Log Channel 1")
                except Exception as e:
                    logger.error(f"Failed to send to log_chat_1: {e}")
                    success = False
            
            # Send to log_chat_2  
            if log_config.get('log_chat_2'):
                try:
                    # Send media if available and valid
                    if character_data.get('media_url') and character_data.get('media_type'):
                        try:
                            if character_data.get('media_type') == 'photo':
                                await client.send_photo(
                                    chat_id=log_config['log_chat_2'],
                                    photo=character_data['media_url'],
                                    caption=log_message
                                )
                            elif character_data.get('media_type') == 'video':
                                await client.send_video(
                                    chat_id=log_config['log_chat_2'],
                                    video=character_data['media_url'],
                                    caption=log_message
                                )
                            elif character_data.get('media_type') == 'audio':
                                await client.send_audio(
                                    chat_id=log_config['log_chat_2'],
                                    audio=character_data['media_url'],
                                    caption=log_message
                                )
                            else:
                                await client.send_document(
                                    chat_id=log_config['log_chat_2'],
                                    document=character_data['media_url'],
                                    caption=log_message
                                )
                        except Exception as e:
                            logger.warning(f"Failed to send media to log_chat_2: {e}")
                            # Fallback to text message with URL
                            log_message += f"\n\n📸 **Media URL:** {character_data['media_url']}"
                            await client.send_message(
                                chat_id=log_config['log_chat_2'],
                                text=log_message
                            )
                    else:
                        # No media, send text only
                        await client.send_message(
                            chat_id=log_config['log_chat_2'],
                            text=log_message
                        )
                    sent_to.append("Log Channel 2")
                except Exception as e:
                    logger.error(f"Failed to send to log_chat_2: {e}")
                    success = False
            
            if not sent_to:
                logger.warning("No log channels configured")
                return False
                
            logger.info(f"Log message sent to: {', '.join(sent_to)}")
            return success
            
        except Exception as e:
            logger.error(f"Error in send_to_log_channels: {e}")
            return False
    
    @staticmethod
    def is_owner(user_id: int) -> bool:
        """Check if user is bot owner"""
        return user_id == config.OWNER_ID
    
    @staticmethod
    async def is_sudo_user(user_id: int) -> bool:
        """Check if user is sudo user"""
        try:
            if user_id == config.OWNER_ID:
                return True
            return await db.is_sudo_user(user_id)
        except Exception as e:
            logger.error(f"Error checking sudo user: {e}")
            return False
    
    @staticmethod
    async def get_username_from_id(client: Client, user_id: int) -> str:
        """Get username from user ID"""
        try:
            user = await client.get_users(user_id)
            return f"@{user.username}" if user.username else user.first_name
        except:
            return f"User ({user_id})"
    
    @staticmethod
    def format_session_duration(start_time: datetime) -> str:
        """Format session duration for display"""
        duration = datetime.utcnow() - start_time
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

helpers = Helpers()
