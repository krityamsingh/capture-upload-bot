from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
from database import collection, database_channel_collection
from utils import UploadUtils
from keyboards import UploadKeyboards
from catbox import CatboxUploader
import aiohttp
import logging
from io import BytesIO
import time

logger = logging.getLogger(__name__)

class UploadFlow:
    def __init__(self, app: Client):
        self.app = app
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.update_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Permanent broadcast channels (will be set after bot initialization)
        self.permanent_broadcast_channels: List[int] = []
        
        # Cache for user info to reduce API calls
        self.user_cache: Dict[int, Dict[str, Any]] = {}
        
        # Upload speed tracking
        self.upload_stats = {
            'total_uploads': 0,
            'total_time': 0.0,
            'fastest_upload': float('inf'),
            'slowest_upload': 0.0
        }
    
    def set_permanent_channels(self, channels: List[int]):
        """Set permanent broadcast channels from ChannelManager"""
        self.permanent_broadcast_channels = channels
        logger.info(f"Upload flow set with {len(channels)} permanent channels: {channels}")
    
    async def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Get user info with caching for performance"""
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        try:
            user = await self.app.get_users(user_id)
            user_info = {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name
            }
            self.user_cache[user_id] = user_info
            return user_info
        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {e}")
            return {"id": user_id, "username": "Unknown", "first_name": "Unknown"}
    
    async def handle_upload_command(self, message: Message) -> None:
        """Handle /upload command with ultra-fast Catbox upload"""
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply("❌ This command can only be used in groups!")
            return
            
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission to upload characters!")
            return
            
        if not message.reply_to_message:
            await message.reply(
                "❓ Usage: Reply to an image/video with:\n"
                "/upload Character-Name Anime-Name\n\n"
                "📝 Examples:\n"
                "/upload Tessia-Eralith The-Beginning-After-The-End\n"
                "/upload Goku Dragon-Ball"
            )
            return
            
        media_type = UploadUtils.get_media_type(message.reply_to_message)
        if not media_type:
            await message.reply("❌ Please reply to an image or video!")
            return
            
        result = UploadUtils.parse_upload_command(message.text)
        if not result:
            await message.reply(
                "❓ Usage: Reply to an image/video with:\n"
                "/upload Character-Name Anime-Name\n\n"
                "📝 Examples:\n"
                "/upload Tessia-Eralith The-Beginning-After-The-End\n"
                "/upload Goku Dragon-Ball"
            )
            return
            
        character_name, anime_name = result
        
        loading_msg = await message.reply("🚀 Starting Catbox upload...")
        
        try:
            start_time = time.time()
            
            # Step 1: Download media directly to memory
            await loading_msg.edit("📥 Downloading media...")
            
            file_bytes, file_size = await self.download_media_to_memory_optimized(message.reply_to_message)
            if not file_bytes:
                await loading_msg.edit("❌ Failed to download media!")
                return
            
            download_time = time.time() - start_time
            logger.info(f"Download completed in {download_time:.2f}s, size: {file_size:,} bytes")
            
            # Step 2: Upload to Catbox (Ultra-fast)
            await loading_msg.edit(f"⚡ Uploading to Catbox.moe...\n📏 Size: {file_size // 1024} KB")
            
            upload_start = time.time()
            uploader = CatboxUploader()
            
            # Generate filename
            timestamp = int(time.time())
            file_extension = '.jpg' if media_type == 'photo' else '.mp4'
            filename = f"char_{timestamp}{file_extension}"
            
            upload_result = await uploader.upload_bytes(file_bytes, filename)
            
            upload_time = time.time() - upload_start
            
            # Update upload statistics
            self.upload_stats['total_uploads'] += 1
            self.upload_stats['total_time'] += upload_time
            self.upload_stats['fastest_upload'] = min(self.upload_stats['fastest_upload'], upload_time)
            self.upload_stats['slowest_upload'] = max(self.upload_stats['slowest_upload'], upload_time)
            
            if not upload_result['success']:
                await loading_msg.edit(f"❌ Catbox upload failed: {upload_result.get('error', 'Unknown error')}")
                return
            
            logger.info(f"Catbox upload completed in {upload_time:.2f}s, URL: {upload_result.get('url', 'N/A')}")
            
            # Step 3: Create session
            session_id = UploadUtils.generate_session_id()
            character_id = await UploadUtils.generate_character_id()
            
            # Remove leading zeros for display and storage
            display_id = character_id
            if display_id.isdigit():
                display_id = str(int(display_id))
            
            self.sessions[session_id] = {
                "user_id": message.from_user.id,
                "chat_id": message.chat.id,
                "message_id": message.id,
                "step": "rarity",
                "character_name": character_name,
                "anime_name": anime_name,
                "media_url": upload_result['url'],
                "file_extension": file_extension,
                "img_type": media_type,
                "temp_id": display_id,  # Store without leading zeros
                "file_id": upload_result.get('file_id'),
                "size": file_size,
                "upload_time": upload_time,
                "download_time": download_time,
                "created_at": datetime.utcnow(),
                "file_bytes": file_bytes,
                "catbox_info": upload_result,
                "filename": filename
            }
            
            total_time = time.time() - start_time
            
            # Calculate speed
            speed_kb_s = (file_size / 1024) / upload_time if upload_time > 0 else 0
            
            # Get channel status
            channel_status = f"📡 Channels: {len(self.permanent_broadcast_channels)} permanent"
            if not self.permanent_broadcast_channels:
                channel_status = "⚠️ Warning: No channels configured!"
            
            # Send rarity selection with new keyboard
            keyboard = UploadKeyboards.get_rarity_keyboard(session_id)
            await loading_msg.edit(
                f"✅ Catbox Upload Successful! ⚡\n\n"
                f"🆔 ID: {display_id}\n"
                f"👤 Character: {character_name}\n"
                f"🎬 Anime: {anime_name}\n"
                f"📁 Type: {'📸 Photo' if media_type == 'photo' else '🎞 Video'}\n"
                f"📏 Size: {file_size // 1024} KB\n"
                f"⚡ Speed: {speed_kb_s:.1f} KB/s\n"
                f"⏱ Upload Time: {upload_time:.2f}s\n"
                f"⏱ Total Time: {total_time:.2f}s\n"
                f"{channel_status}\n"
                f"🌐 URL: {upload_result.get('url', 'N/A')[:50]}...\n\n"
                f"Select rarity:",
                reply_markup=keyboard
            )
            
        except Exception as e:
            await loading_msg.edit(f"❌ Error: {str(e)}")
            logger.error(f"Upload error: {e}")
            import traceback
            traceback.print_exc()
    
    async def download_media_to_memory_optimized(self, message) -> tuple:
        """Optimized download method for Catbox"""
        try:
            file_bytes = BytesIO()
            file_size = 0
            
            # Determine the best method based on message type
            if message.photo:
                # Download photo
                file = await self.app.download_media(
                    message.photo.file_id,
                    in_memory=True
                )
                file_bytes.write(file.getbuffer() if hasattr(file, 'getbuffer') else file.read())
                file_size = message.photo.file_size or 0
                
            elif message.video:
                # Download video
                file = await self.app.download_media(
                    message.video.file_id,
                    in_memory=True
                )
                file_bytes.write(file.getbuffer() if hasattr(file, 'getbuffer') else file.read())
                file_size = message.video.file_size or 0
                
            elif message.animation:
                # Download animation (GIF)
                file = await self.app.download_media(
                    message.animation.file_id,
                    in_memory=True
                )
                file_bytes.write(file.getbuffer() if hasattr(file, 'getbuffer') else file.read())
                file_size = message.animation.file_size or 0
                
            elif message.document:
                # Download document
                file = await self.app.download_media(
                    message.document.file_id,
                    in_memory=True
                )
                file_bytes.write(file.getbuffer() if hasattr(file, 'getbuffer') else file.read())
                file_size = message.document.file_size or 0
                
            else:
                return None, 0
            
            file_bytes.seek(0)
            return file_bytes, file_size
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None, 0
    
    async def handle_update_character(self, message: Message) -> None:
        """Handle /uchar command with Catbox"""
        # Check permissions
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission to update characters!")
            return
        
        # Parse command
        args = message.text.split()
        if len(args) < 3:
            await message.reply("❓ Usage: /uchar <char_id> <type> [updated_info]\n\n"
                              "📋 Types: name, anime, media, rarity\n"
                              "📝 Examples:\n"
                              "/uchar 3 name Iron-Man-Mark-85\n"
                              "/uchar 3 anime Marvel-Cinematic-Universe\n"
                              "/uchar 3 media (reply to media)\n"
                              "/uchar 3 rarity")
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
        
        update_type = args[2].lower()
        
        if update_type == "name":
            if len(args) < 4:
                await message.reply("❌ Please provide new name!")
                return
            
            new_name = " ".join(args[3:])
            new_name = UploadUtils.auto_capitalize(new_name)
            
            await collection.update_one(
                {"id": character['id']},
                {"$set": {"name": new_name}}
            )
            await message.reply(f"✅ Character {character['id']} name updated to: {new_name}")
            
        elif update_type == "anime":
            if len(args) < 4:
                await message.reply("❌ Please provide new anime name!")
                return
            
            new_anime = " ".join(args[3:])
            new_anime = UploadUtils.auto_capitalize(new_anime)
            
            await collection.update_one(
                {"id": character['id']},
                {"$set": {"anime": new_anime}}
            )
            await message.reply(f"✅ Character {character['id']} anime updated to: {new_anime}")
            
        elif update_type == "media":
            if not message.reply_to_message:
                await message.reply("❌ Reply to an image or video to update media!")
                return
            
            # Check media type
            media_type = UploadUtils.get_media_type(message.reply_to_message)
            if not media_type:
                await message.reply("❌ Please reply to an image or video!")
                return
            
            loading_msg = await message.reply("🔄 Updating media to Catbox...")
            
            try:
                # Download to memory
                file_bytes, file_size = await self.download_media_to_memory_optimized(
                    message.reply_to_message
                )
                if not file_bytes:
                    await loading_msg.edit("❌ Failed to download media!")
                    return
                
                # Upload to Catbox
                timestamp = int(time.time())
                filename = f"update_{character['id']}_{timestamp}.jpg"
                uploader = CatboxUploader()
                upload_result = await uploader.upload_bytes(file_bytes, filename)
                
                if not upload_result['success']:
                    await loading_msg.edit(f"❌ Catbox upload failed: {upload_result.get('error')}")
                    return
                
                # Update database
                await collection.update_one(
                    {"id": character['id']},
                    {"$set": {
                        "img_url": upload_result['url'],
                        "img_type": media_type,
                        "file_extension": f".{filename.split('.')[-1]}" if '.' in filename else ".jpg",
                        "catbox_id": upload_result.get('file_id'),
                        "size": file_size,
                        "upload_site": "catbox"
                    }}
                )
                
                await loading_msg.edit(f"✅ Character {character['id']} media updated successfully!\n"
                                      f"⚡ Upload Time: {upload_result.get('upload_time', 0):.2f}s\n"
                                      f"🌐 URL: {upload_result['url'][:50]}...")
                
                # Clean up
                file_bytes.close()
                
            except Exception as e:
                await loading_msg.edit(f"❌ Error: {str(e)}")
                
        elif update_type == "rarity":
            # Create update session for rarity selection
            session_id = UploadUtils.generate_session_id()
            
            self.update_sessions[session_id] = {
                "char_id": character['id'],
                "user_id": message.from_user.id,
                "chat_id": message.chat.id,
                "message_id": message.id
            }
            
            keyboard = UploadKeyboards.get_rarity_keyboard(f"update_{session_id}")
            await message.reply(f"🔄 Updating rarity for character {character['id']}\n\n"
                              f"📊 Current: {character.get('rarity', 'Unknown')}\n\n"
                              f"Select new rarity:",
                              reply_markup=keyboard)
            
        else:
            await message.reply("❌ Invalid update type!\n"
                              "✅ Valid types: name, anime, media, rarity")
    
    async def handle_callback(self, callback_query: CallbackQuery) -> None:
        """Handle callback queries for both upload and update"""
        data = callback_query.data
        
        if "update_" in data:
            # This is an update callback
            await self.handle_update_callback(callback_query)
        else:
            # This is a regular upload callback
            await self.handle_upload_callback(callback_query)
    
    async def handle_upload_callback(self, callback_query: CallbackQuery) -> None:
        """Handle upload callbacks"""
        data = callback_query.data
        parts = data.split(":")
        
        if len(parts) < 2:
            await callback_query.answer("❌ Invalid callback!", show_alert=True)
            return
        
        session_id = parts[1]
        
        if not session_id or session_id not in self.sessions:
            await callback_query.answer("❌ Session expired!", show_alert=True)
            return
        
        session = self.sessions[session_id]
        
        # Handle different callback types
        if data.startswith("rarity:"):
            if len(parts) >= 3:
                rarity = parts[2]
                session["rarity"] = rarity
                session["step"] = "preview"
                
                await callback_query.answer(f"✅ Selected: {rarity}")
                await self.show_preview(callback_query, session_id)
        
        elif data.startswith("back:"):
            session["step"] = "rarity"
            keyboard = UploadKeyboards.get_rarity_keyboard(session_id)
            
            await callback_query.answer("↩️ Back to rarities")
            await callback_query.message.edit_text(
                "Select rarity:",
                reply_markup=keyboard
            )
            
        elif data.startswith("confirm:"):
            await self.confirm_upload(callback_query, session_id)
            
        elif data.startswith("cancel:"):
            await self.cancel_upload(callback_query, session_id)
    
    async def handle_update_callback(self, callback_query: CallbackQuery) -> None:
        """Handle update callbacks"""
        data = callback_query.data
        parts = data.split(":")
        
        if len(parts) < 3:
            await callback_query.answer("❌ Invalid callback!", show_alert=True)
            return
        
        action = parts[0]
        
        # Extract session_id from callback data
        session_id = None
        for part in parts:
            if part.startswith("update_"):
                session_id = part
                break
        
        if not session_id or session_id.replace("update_", "") not in self.update_sessions:
            await callback_query.answer("❌ Session expired!", show_alert=True)
            return
        
        clean_session_id = session_id.replace("update_", "")
        session = self.update_sessions[clean_session_id]
        char_id = session["char_id"]
        
        if action == "rarity":
            if len(parts) >= 4:
                rarity = parts[3]
                
                await callback_query.answer(f"✅ Selected: {rarity}")
                
                # Update directly
                await collection.update_one(
                    {"id": char_id},
                    {"$set": {"rarity": rarity}}
                )
                
                await callback_query.message.edit_text(f"✅ Character {char_id} rarity updated to: {rarity}")
                del self.update_sessions[clean_session_id]
        
        elif action == "cancel":
            await callback_query.answer("❌ Update cancelled")
            await callback_query.message.edit_text("❌ Rarity update cancelled.")
            if clean_session_id in self.update_sessions:
                del self.update_sessions[clean_session_id]
        
        elif action == "back":
            await callback_query.answer("↩️ Back to rarities")
            
            keyboard = UploadKeyboards.get_rarity_keyboard(session_id)
            await callback_query.message.edit_text(
                f"🔄 Updating rarity for character {char_id}\n\n"
                f"Select new rarity:",
                reply_markup=keyboard
            )
    
    async def show_preview(self, callback_query: CallbackQuery, session_id: str) -> None:
        """Show preview before confirmation"""
        session = self.sessions[session_id]
        
        # Get user info
        user_info = await self.get_user_info(session["user_id"])
        
        # Format preview text with proper emojis
        preview_text = await UploadUtils.format_preview_text(session, {
            "username": user_info["username"],
            "first_name": user_info["first_name"]
        })
        
        # Add Catbox info
        if session.get('catbox_info'):
            preview_text += f"\n⚡ Upload Speed: {(session['size'] / 1024) / session['upload_time']:.1f} KB/s"
            preview_text += f"\n⏱ Upload Time: {session['upload_time']:.2f}s"
        
        # Add channel info
        preview_text += f"\n📡 Broadcast: {len(self.permanent_broadcast_channels)} permanent channels"
        
        keyboard = UploadKeyboards.get_confirmation_keyboard(session_id)
        
        await callback_query.answer("✅ Preview generated")
        await callback_query.message.edit_text(
            preview_text,
            reply_markup=keyboard
        )
    
    async def broadcast_to_all_channels(self, character_doc: Dict[str, Any]) -> List[int]:
        """Broadcast character to all permanent channels"""
        successful_channels = []
        
        if not self.permanent_broadcast_channels:
            logger.error("No permanent channels configured for broadcasting!")
            return successful_channels
        
        # Get user info for caption
        user_info = await self.get_user_info(character_doc['added_by']['id'])
        caption = UploadUtils.format_caption_for_character(character_doc, {
            "username": user_info["username"],
            "first_name": user_info["first_name"]
        })
        
        # Broadcast to each permanent channel
        for channel_id in self.permanent_broadcast_channels:
            try:
                result = await self.broadcast_to_single_channel(channel_id, character_doc, caption)
                if result:
                    successful_channels.append(channel_id)
                    logger.info(f"✅ Successfully broadcast to channel: {channel_id}")
                else:
                    logger.error(f"❌ Failed to broadcast to channel: {channel_id}")
            except Exception as e:
                logger.error(f"❌ Error broadcasting to channel {channel_id}: {e}")
        
        return successful_channels
    
    async def broadcast_to_single_channel(self, channel_id: int, character_doc: Dict[str, Any], caption: str) -> bool:
        """Broadcast to a single channel with enhanced error handling"""
        try:
            # Ensure channel_id is integer
            if not isinstance(channel_id, int):
                try:
                    channel_id = int(channel_id)
                except ValueError:
                    logger.error(f"❌ Invalid channel ID format: {channel_id}")
                    return False
            
            # Try multiple access methods
            for attempt in range(3):
                try:
                    # First try: direct send
                    return await self._send_media_to_channel(channel_id, character_doc, caption, attempt)
                except Exception as e:
                    logger.warning(f"⚠️ Broadcast attempt {attempt + 1} failed for channel {channel_id}: {e}")
                    
                    if attempt < 2:
                        # Wait before retry
                        await asyncio.sleep(1)
                        
                        # Try alternative channel formats
                        if attempt == 1:
                            # Try different channel ID format
                            alt_channel_id = self._get_alternative_channel_id(channel_id)
                            if alt_channel_id != channel_id:
                                try:
                                    logger.info(f"Trying alternative channel ID: {alt_channel_id}")
                                    return await self._send_media_to_channel(alt_channel_id, character_doc, caption, attempt)
                                except:
                                    continue
                    else:
                        logger.error(f"❌ Final broadcast failed for channel {channel_id}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Broadcast exception for channel {channel_id}: {e}")
            return False
    
    async def _send_media_to_channel(self, channel_id: int, character_doc: Dict[str, Any], caption: str, attempt: int) -> bool:
        """Send media to channel with specific method"""
        media_url = character_doc['img_url']
        media_type = character_doc['img_type']
        
        try:
            # Get chat info first to verify access
            chat = await self.app.get_chat(channel_id)
            
            if media_type == 'photo':
                await self.app.send_photo(
                    chat_id=channel_id,
                    photo=media_url,
                    caption=caption
                )
            elif media_type == 'video':
                await self.app.send_video(
                    chat_id=channel_id,
                    video=media_url,
                    caption=caption
                )
            elif media_type == 'animation':
                await self.app.send_animation(
                    chat_id=channel_id,
                    animation=media_url,
                    caption=caption
                )
            else:
                await self.app.send_document(
                    chat_id=channel_id,
                    document=media_url,
                    caption=caption
                )
            
            logger.info(f"✅ Broadcast attempt {attempt + 1} successful for channel {channel_id} ({chat.title})")
            return True
            
        except Exception as e:
            raise e
    
    def _get_alternative_channel_id(self, channel_id: int) -> int:
        """Get alternative format for channel ID"""
        # If -100 prefixed, try without -100
        if str(channel_id).startswith("-100"):
            try:
                return int(str(channel_id).replace("-100", ""))
            except:
                pass
        # If not -100 prefixed and negative, try with -100
        elif channel_id < 0 and not str(channel_id).startswith("-100"):
            try:
                return int(f"-100{abs(channel_id)}")
            except:
                pass
        # Try positive version
        return abs(channel_id)
    
    async def confirm_upload(self, callback_query: CallbackQuery, session_id: str) -> None:
        """Confirm and save upload with enhanced broadcasting"""
        session = self.sessions[session_id]
        
        # Show processing message
        processing_msg = await callback_query.message.edit(
            "⏳ Processing your upload...\n"
            f"🆔 ID: {session['temp_id']}\n"
            f"👤 Character: {session['character_name']}\n"
        )
        
        # Get user info
        user_info = await self.get_user_info(session["user_id"])
        
        # Ensure character ID is stored without leading zeros
        char_id = session['temp_id']
        # Remove any leading zeros for storage
        if char_id.isdigit():
            char_id = str(int(char_id))
        
        # Create character document
        character_doc = {
            "name": session["character_name"],
            "anime": session["anime_name"],
            "rarity": session["rarity"],
            "id": char_id,
            "subtype": "",
            "img_url": session["media_url"],
            "file_extension": session["file_extension"],
            "img_type": session["img_type"],
            "upload_site": "catbox",
            "added_by": {
                "id": user_info["id"],
                "username": user_info["username"],
                "first_name": user_info["first_name"]
            },
            "edition": "",
            "date_added": datetime.utcnow(),
            "deleted": False,
            "catbox_id": session.get("file_id"),
            "size": session.get("size", 0),
            "upload_time": session.get("upload_time", 0),
            "permanent_channels": self.permanent_broadcast_channels,
            "upload_speed": f"{(session['size'] / 1024) / session['upload_time']:.1f} KB/s" if session.get('upload_time', 0) > 0 else "N/A"
        }
        
        # Save to database
        await collection.insert_one(character_doc)
        logger.info(f"✅ Character saved to database: {character_doc['id']}")
        
        # Check if we have channels
        if not self.permanent_broadcast_channels:
            await processing_msg.edit(
                "⚠️ Warning: No broadcast channels configured!\n"
                "Character will be saved to database but NOT broadcasted.\n\n"
                "To fix: Add bot to channels and use /refreshchannels"
            )
            # Still save character but skip broadcasting
            successful_channels = []
        else:
            await processing_msg.edit(
                f"📡 Broadcasting to {len(self.permanent_broadcast_channels)} channels..."
            )
            successful_channels = await self.broadcast_to_all_channels(character_doc)
        
        # Clean up memory
        if "file_bytes" in session:
            try:
                session["file_bytes"].close()
            except:
                pass
        
        # Clean session from memory
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        # Format channel status with emojis
        channel_status = []
        for channel_id in self.permanent_broadcast_channels:
            if channel_id in successful_channels:
                channel_status.append(f"✅ Channel {channel_id} - Success")
            else:
                channel_status.append(f"❌ Channel {channel_id} - Failed")
        
        channel_list = "\n".join(channel_status)
        
        # Get rarity emoji
        from keyboards import UploadKeyboards
        rarity_emoji = UploadKeyboards.RARITIES.get(character_doc['rarity'], "")
        
        # Get type emoji
        type_emoji = "📸" if character_doc['img_type'] == 'photo' else '🎞'
        
        # Calculate average upload time
        avg_upload_time = self.upload_stats['total_time'] / self.upload_stats['total_uploads'] if self.upload_stats['total_uploads'] > 0 else 0
        
        # Format success text with proper emojis
        success_text = f"""🎉 Character Uploaded Successfully! ⚡

🆔 ID: {character_doc['id']}
👤 Character: {character_doc['name']}
🎬 Anime: {character_doc['anime']}
🌟 Rarity: {rarity_emoji} {character_doc['rarity']}
📁 Type: {type_emoji} {'Photo' if character_doc['img_type'] == 'photo' else 'Video'}
⚡ Upload Speed: {character_doc['upload_speed']}
⏱ Upload Time: {character_doc['upload_time']:.2f}s
📏 Size: {character_doc.get('size', 0) // 1024} KB
🌐 Host: Catbox.moe
📢 Broadcast: {len(successful_channels)}/{len(self.permanent_broadcast_channels)} channels
👤 Uploaded by: @{user_info['username']}

📊 Upload Statistics:
• Total Uploads: {self.upload_stats['total_uploads']}
• Fastest Upload: {self.upload_stats['fastest_upload']:.2f}s
• Average Upload: {avg_upload_time:.2f}s

✅ Character has been:
• Added to database
• Uploaded to Catbox.moe
• Broadcasted to permanent channels

📡 Permanent Channels Results:
{channel_list}

🚀 Note: These channels will always receive uploads, even after bot restart."""

        await callback_query.answer("✅ Upload completed successfully!")
        await processing_msg.edit(success_text)
    
    async def cancel_upload(self, callback_query: CallbackQuery, session_id: str) -> None:
        """Cancel upload session and clean up"""
        if session_id in self.sessions:
            # Free memory
            if "file_bytes" in self.sessions[session_id]:
                try:
                    self.sessions[session_id]["file_bytes"].close()
                except:
                    pass
            # Remove session
            del self.sessions[session_id]
        
        await callback_query.answer("❌ Upload cancelled")
        await callback_query.message.edit_text(
            "❌ Upload cancelled. No changes were made to the database.\n\n"
            "⚠️ Note: The uploaded file may still exist on Catbox servers."
        )
