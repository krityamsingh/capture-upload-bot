from pyrogram import Client
from config import config


async def send_character_to_channel(client: Client, character):
    """
    Sends uploaded character to capture database channel
    """
    caption = (
        f"✨ **New Character Added** ✨\n\n"
        f"👤 **Name:** {character.char_name}\n"
        f"🎬 **Anime:** {character.anime_name}\n"
        f"🎯 **Rarity:** {character.rarity_label}\n"
        f"👮 **Uploaded by:** `{character.uploaded_by}`"
    )

    if character.media_type == "photo":
        await client.send_photo(
            chat_id=config.CAPTURE_CHANNEL,
            photo=character.media_url,
            caption=caption
        )

    elif character.media_type == "video":
        await client.send_video(
            chat_id=config.CAPTURE_CHANNEL,
            video=character.media_url,
            caption=caption
        )

    elif character.media_type == "audio":
        await client.send_audio(
            chat_id=config.CAPTURE_CHANNEL,
            audio=character.media_url,
            caption=caption
        )

    else:
        await client.send_document(
            chat_id=config.CAPTURE_CHANNEL,
            document=character.media_url,
            caption=caption
        )
