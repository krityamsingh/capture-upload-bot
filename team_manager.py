from datetime import datetime, timezone
from pyrogram import Client
from pyrogram.types import Message
from database import upload_team_collection
from utils import UploadUtils

class TeamManager:
    def __init__(self, app: Client):
        self.app = app

    async def add_team_member(self, message: Message, user_id: int) -> None:
        if not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can add team members!")
            return

        existing = await upload_team_collection.find_one({"user_id": user_id})
        if existing:
            await message.reply("⚠️ This user is already a team member!")
            return

        try:
            user = await self.app.get_users(user_id)
        except:
            await message.reply("❌ Cannot find user with this ID!")
            return

        await upload_team_collection.insert_one({
            "user_id": user_id,
            "username": user.username,
            "first_name": user.first_name,
            "role": "team_member",
            "added_by": message.from_user.id,
            "added_at": datetime.now(timezone.utc)
        })
        await message.reply(f"✅ User added to uploader team.")

    async def remove_team_member(self, message: Message, user_id: int) -> None:
        if not await UploadUtils.is_owner(message.from_user.id):
            await message.reply("❌ Only owners can remove team members!")
            return

        existing = await upload_team_collection.find_one({"user_id": user_id})
        if not existing:
            await message.reply("❌ User not found in team!")
            return

        if existing.get("role") == "owner":
            await message.reply("❌ Cannot remove an owner!")
            return

        await upload_team_collection.delete_one({"user_id": user_id})
        await message.reply(f"✅ User removed from team.")

    async def show_team(self, message: Message) -> None:
        if not await UploadUtils.is_uploader(message.from_user.id):
            await message.reply("❌ You don't have permission to view the team!")
            return

        team_members = await upload_team_collection.find().sort("role", -1).to_list(None)
        if not team_members:
            await message.reply("👥 Team is empty!")
            return

        text = "**👥 Upload Team:**\n\n"
        for i, member in enumerate(team_members, 1):
            role_emoji = "👑" if member.get("role") == "owner" else "👤"
            username = f"@{member['username']}" if member.get("username") else "No username"
            text += f"{i}. {role_emoji} {member.get('first_name', 'Unknown')}\n"
            text += f"   └─ {username} | ID: `{member['user_id']}`\n"
            text += f"   └─ Role: {member.get('role', 'team_member').title()}\n\n"

        await message.reply(text)
