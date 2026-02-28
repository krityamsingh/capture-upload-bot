from pyrogram import Client, enums
from pyrogram.types import Message, CallbackQuery
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime, timezone
from database import collection, database_channel_collection, counters_collection
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
        self.database_channel: Optional[int] = None
        self.user_cache: Dict[int, Dict[str, Any]] = {}
        self.upload_stats = {
            'total_uploads': 0,
            'total_time': 0.0,
            'fastest_upload': float('inf'),
            'slowest_upload': 0.0
        }

    def set_database_channel(self, channel_id: Optional[int]):
        self.database_channel = channel_id
        if channel_id:
            logger.info(f"Upload flow set with database channel: {channel_id}")
        else:
            logger.info("Upload flow: No database channel set")

    async def get_user_info(self, user_id: int) -> Dict[str, Any]:
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        try:
            user = await self.app.get_users(user_id)
            info = {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name
            }
            self.user_cache[user_id] = info
            return info
        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {e}")
            return {"id": user_id, "username": "Unknown", "first_name": "Unknown"}

    async def handle_upload_command(self, message: Message) -> None:
        if message.chat.type in [enums.ChatType.PRIVATE, enums.ChatType.BOT]:
            await message.reply("❌ This command can only be used in groups or channels!")
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
            await loading_msg.edit("📥 Downloading media...")

            # Download to memory
            file_bytes, file_size = await self.download_media_to_memory_optimized(message.reply_to_message)
            if not file_bytes:
                await loading_msg.edit("❌ Failed to download media!")
                return

            download_time = time.time() - start_time
            logger.info(f"Download completed in {download_time:.2f}s, size: {file_size:,} bytes")

            await loading_msg.edit(f"⚡ Uploading to Catbox.moe...\n📏 Size: {file_size // 1024} KB")
            upload_start = time.time()
            uploader = CatboxUploader()

            timestamp = int(time.time())
            file_extension = '.jpg' if media_type == 'photo' else '.mp4'
            filename = f"char_{timestamp}{file_extension}"

            upload_result = await uploader.upload_bytes(file_bytes, filename)
            upload_time = time.time() - upload_start

            # Update stats
            self.upload_stats['total_uploads'] += 1
            self.upload_stats['total_time'] += upload_time
            self.upload_stats['fastest_upload'] = min(self.upload_stats['fastest_upload'], upload_time)
            self.upload_stats['slowest_upload'] = max(self.upload_stats['slowest_upload'], upload_time)

            if not upload_result['success']:
                await loading_msg.edit(f"❌ Catbox upload failed: {upload_result.get('error', 'Unknown error')}")
                return

            logger.info(f"Catbox upload completed in {upload_time:.2f}s")

            # Generate character ID using counter
            counter = await counters_collection.find_one_and_update(
                {"_id": "character_id"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=True
            )
            char_id = str(counter["seq"])

            session_id = UploadUtils.generate_session_id()
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
                "temp_id": char_id,  # Store without leading zeros
                "file_id": upload_result.get('file_id'),
                "size": file_size,
                "upload_time": upload_time,
                "download_time": download_time,
                "created_at": datetime.now(timezone.utc),
                # DO NOT store file_bytes here – remove to free memory
                "catbox_info": upload_result,
                "filename": filename
            }

            # Immediately delete file_bytes from memory (no longer needed)
            file_bytes.close()
            del file_bytes

            total_time = time.time() - start_time
            speed_kb_s = (file_size / 1024) / upload_time if upload_time > 0 else 0
            channel_status = f"📡 Database channel: {self.database_channel}" if self.database_channel else "⚠️ Warning: No database channel set! Use /setchannel"

            keyboard = UploadKeyboards.get_rarity_keyboard(session_id)
            await loading_msg.edit(
                f"✅ Catbox Upload Successful! ⚡\n\n"
                f"🆔 ID: {char_id}\n"
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
            logger.error(f"Upload error: {e}", exc_info=True)

    async def download_media_to_memory_optimized(self, message) -> tuple:
        try:
            if message.photo:
                file = await self.app.download_media(message.photo.file_id, in_memory=True)
                size = message.photo.file_size or 0
            elif message.video:
                file = await self.app.download_media(message.video.file_id, in_memory=True)
                size = message.video.file_size or 0
            elif message.animation:
                file = await self.app.download_media(message.animation.file_id, in_memory=True)
                size = message.animation.file_size or 0
            elif message.document:
                file = await self.app.download_media(message.document.file_id, in_memory=True)
                size = message.document.file_size or 0
            else:
                return None, 0

            # file is already a BytesIO-like object
            file_bytes = BytesIO(file.getbuffer()) if hasattr(file, 'getbuffer') else BytesIO(file.read())
            file_bytes.seek(0)
            return file_bytes, size
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None, 0

    async def handle_update_character(self, message: Message) -> None:
        # (unchanged – same as before)
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission to update characters!")
            return

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

        char_id_input = args[1]
        character = await self.find_character_by_id(char_id_input)
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
            await collection.update_one({"id": character['id']}, {"$set": {"name": new_name}})
            await message.reply(f"✅ Character {character['id']} name updated to: {new_name}")

        elif update_type == "anime":
            if len(args) < 4:
                await message.reply("❌ Please provide new anime name!")
                return
            new_anime = " ".join(args[3:])
            new_anime = UploadUtils.auto_capitalize(new_anime)
            await collection.update_one({"id": character['id']}, {"$set": {"anime": new_anime}})
            await message.reply(f"✅ Character {character['id']} anime updated to: {new_anime}")

        elif update_type == "media":
            if not message.reply_to_message:
                await message.reply("❌ Reply to an image or video to update media!")
                return
            media_type = UploadUtils.get_media_type(message.reply_to_message)
            if not media_type:
                await message.reply("❌ Please reply to an image or video!")
                return

            loading_msg = await message.reply("🔄 Updating media to Catbox...")
            try:
                file_bytes, file_size = await self.download_media_to_memory_optimized(message.reply_to_message)
                if not file_bytes:
                    await loading_msg.edit("❌ Failed to download media!")
                    return

                timestamp = int(time.time())
                filename = f"update_{character['id']}_{timestamp}.jpg"
                uploader = CatboxUploader()
                upload_result = await uploader.upload_bytes(file_bytes, filename)
                file_bytes.close()

                if not upload_result['success']:
                    await loading_msg.edit(f"❌ Catbox upload failed: {upload_result.get('error')}")
                    return

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
            except Exception as e:
                await loading_msg.edit(f"❌ Error: {str(e)}")

        elif update_type == "rarity":
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

    async def find_character_by_id(self, char_id_input: str):
        # identical to main's helper – you can reuse the one from main or implement here
        # We'll keep a local copy for independence.
        char = await collection.find_one({"id": char_id_input, "deleted": False})
        if char:
            return char
        if char_id_input.isdigit():
            no_zeros = str(int(char_id_input))
            if no_zeros != char_id_input:
                char = await collection.find_one({"id": no_zeros, "deleted": False})
                if char:
                    return char
            four_digit = char_id_input.zfill(4)
            if four_digit != char_id_input:
                char = await collection.find_one({"id": four_digit, "deleted": False})
                if char:
                    return char
        return None

    async def handle_callback(self, callback_query: CallbackQuery) -> None:
        data = callback_query.data
        if "update_" in data:
            await self.handle_update_callback(callback_query)
        else:
            await self.handle_upload_callback(callback_query)

    async def handle_upload_callback(self, callback_query: CallbackQuery) -> None:
        data = callback_query.data
        parts = data.split(":")
        if len(parts) < 2:
            await callback_query.answer("❌ Invalid callback!", show_alert=True)
            return

        session_id = parts[1]
        if session_id not in self.sessions:
            await callback_query.answer("❌ Session expired!", show_alert=True)
            return

        session = self.sessions[session_id]

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
            await callback_query.message.edit_text("Select rarity:", reply_markup=keyboard)

        elif data.startswith("confirm:"):
            await self.confirm_upload(callback_query, session_id)

        elif data.startswith("cancel:"):
            await self.cancel_upload(callback_query, session_id)

    async def handle_update_callback(self, callback_query: CallbackQuery) -> None:
        data = callback_query.data
        parts = data.split(":")
        if len(parts) < 3:
            await callback_query.answer("❌ Invalid callback!", show_alert=True)
            return

        action = parts[0]
        session_id = None
        for part in parts:
            if part.startswith("update_"):
                session_id = part
                break

        if not session_id or session_id.replace("update_", "") not in self.update_sessions:
            await callback_query.answer("❌ Session expired!", show_alert=True)
            return

        clean_id = session_id.replace("update_", "")
        session = self.update_sessions[clean_id]
        char_id = session["char_id"]

        if action == "rarity":
            if len(parts) >= 4:
                rarity = parts[3]
                await callback_query.answer(f"✅ Selected: {rarity}")
                await collection.update_one({"id": char_id}, {"$set": {"rarity": rarity}})
                await callback_query.message.edit_text(f"✅ Character {char_id} rarity updated to: {rarity}")
                del self.update_sessions[clean_id]

        elif action == "cancel":
            await callback_query.answer("❌ Update cancelled")
            await callback_query.message.edit_text("❌ Rarity update cancelled.")
            del self.update_sessions[clean_id]

        elif action == "back":
            await callback_query.answer("↩️ Back to rarities")
            keyboard = UploadKeyboards.get_rarity_keyboard(session_id)
            await callback_query.message.edit_text(
                f"🔄 Updating rarity for character {char_id}\n\nSelect new rarity:",
                reply_markup=keyboard
            )

    async def show_preview(self, callback_query: CallbackQuery, session_id: str) -> None:
        session = self.sessions[session_id]
        user_info = await self.get_user_info(session["user_id"])
        preview_text = await UploadUtils.format_preview_text(session, {
            "username": user_info["username"],
            "first_name": user_info["first_name"]
        })

        if session.get('catbox_info'):
            speed = (session['size'] / 1024) / session['upload_time'] if session['upload_time'] > 0 else 0
            preview_text += f"\n⚡ Upload Speed: {speed:.1f} KB/s"
            preview_text += f"\n⏱ Upload Time: {session['upload_time']:.2f}s"

        if self.database_channel:
            preview_text += f"\n📡 Broadcast: Database channel (ID: {self.database_channel})"
        else:
            preview_text += f"\n⚠️ No database channel set! Character will not be broadcasted."

        keyboard = UploadKeyboards.get_confirmation_keyboard(session_id)
        await callback_query.answer("✅ Preview generated")
        await callback_query.message.edit_text(preview_text, reply_markup=keyboard)

    async def confirm_upload(self, callback_query: CallbackQuery, session_id: str) -> None:
        session = self.sessions[session_id]
        processing_msg = await callback_query.message.edit(
            "⏳ Processing your upload...\n"
            f"🆔 ID: {session['temp_id']}\n"
            f"👤 Character: {session['character_name']}\n"
        )

        user_info = await self.get_user_info(session["user_id"])

        character_doc = {
            "name": session["character_name"],
            "anime": session["anime_name"],
            "rarity": session["rarity"],
            "id": session["temp_id"],
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
            "date_added": datetime.now(timezone.utc),
            "deleted": False,
            "catbox_id": session.get("file_id"),
            "size": session.get("size", 0),
            "upload_time": session.get("upload_time", 0),
            "database_channel": self.database_channel,
            "upload_speed": f"{(session['size'] / 1024) / session['upload_time']:.1f} KB/s" if session.get('upload_time', 0) > 0 else "N/A"
        }

        await collection.insert_one(character_doc)
        logger.info(f"✅ Character saved to database: {character_doc['id']}")

        if not self.database_channel:
            await processing_msg.edit(
                "⚠️ Warning: No database channel configured!\n"
                "Character will be saved to database but NOT broadcasted.\n\n"
                "To fix: Use /setchannel to set a broadcast channel."
            )
            broadcast_success = False
        else:
            await processing_msg.edit(f"📡 Broadcasting to database channel (ID: {self.database_channel})...")
            broadcast_success = await self.broadcast_to_database_channel(character_doc)

        # Clean up session
        if session_id in self.sessions:
            del self.sessions[session_id]

        from keyboards import UploadKeyboards
        rarity_emoji = UploadKeyboards.RARITIES.get(character_doc['rarity'], "")
        type_emoji = "📸" if character_doc['img_type'] == 'photo' else '🎞'
        avg_upload = self.upload_stats['total_time'] / self.upload_stats['total_uploads'] if self.upload_stats['total_uploads'] > 0 else 0

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
📢 Broadcast: {'✅ Success' if broadcast_success else '❌ Failed'}
👤 Uploaded by: @{user_info['username']}

📊 Upload Statistics:
• Total Uploads: {self.upload_stats['total_uploads']}
• Fastest Upload: {self.upload_stats['fastest_upload']:.2f}s
• Average Upload: {avg_upload:.2f}s

✅ Character has been:
• Added to database
• Uploaded to Catbox.moe
• {'Broadcasted to database channel' if broadcast_success else 'NOT broadcasted (no channel set)'}

{f'📡 Database Channel: {self.database_channel}' if self.database_channel else '⚠️ No database channel set. Use /setchannel to set one.'}"""

        await callback_query.answer("✅ Upload completed successfully!")
        await processing_msg.edit(success_text)

    async def broadcast_to_database_channel(self, character_doc: Dict[str, Any]) -> bool:
        if not self.database_channel:
            logger.error("No database channel set for broadcasting!")
            return False

        user_info = await self.get_user_info(character_doc['added_by']['id'])
        caption = UploadUtils.format_caption_for_character(character_doc, {
            "username": user_info["username"],
            "first_name": user_info["first_name"]
        })

        try:
            return await self.broadcast_to_single_channel(self.database_channel, character_doc, caption)
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            return False

    async def broadcast_to_single_channel(self, channel_id: int, character_doc: Dict[str, Any], caption: str) -> bool:
        media_url = character_doc['img_url']
        media_type = character_doc['img_type']

        try:
            chat = await self.app.get_chat(channel_id)

            if media_type == 'photo':
                await self.app.send_photo(chat_id=channel_id, photo=media_url, caption=caption)
            elif media_type == 'video':
                await self.app.send_video(chat_id=channel_id, video=media_url, caption=caption)
            elif media_type == 'animation':
                await self.app.send_animation(chat_id=channel_id, animation=media_url, caption=caption)
            else:
                await self.app.send_document(chat_id=channel_id, document=media_url, caption=caption)

            logger.info(f"✅ Broadcast successful to channel {channel_id} ({chat.title})")
            return True

        except Exception as e:
            logger.error(f"Broadcast attempt failed for channel {channel_id}: {e}")
            return False

    async def cancel_upload(self, callback_query: CallbackQuery, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]
        await callback_query.answer("❌ Upload cancelled")
        await callback_query.message.edit_text(
            "❌ Upload cancelled. No changes were made to the database.\n\n"
            "⚠️ Note: The uploaded file may still exist on Catbox servers."
        )
