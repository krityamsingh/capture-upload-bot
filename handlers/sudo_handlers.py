# ==================== HANDLERS/SUDO_HANDLERS.PY ====================
# handlers/sudo_handlers.py - UNCHANGED
"""
Sudo user management handlers
Adds sudo system to control who can upload characters
"""
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

from config import config
from database.mongodb import db
from utils import helpers

logger = logging.getLogger(__name__)

class SudoHandlers:
    """Handlers for sudo user management"""
    
    def __init__(self, client: Client):
        self.client = client
    
    async def addsudo_command(self, client: Client, message: Message):
        """Handle /addsudo command - add sudo user (owner only)"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "👑 **Add Sudo User**\n\n"
                    "**Usage:**\n"
                    "`/addsudo <user_id>`\n\n"
                    "**Example:**\n"
                    "`/addsudo 123456789`\n\n"
                    "**Note:** You can get user ID by forwarding user's message to @userinfobot"
                )
                return
            
            user_id = int(args[1])
            
            # Check if user is already sudo
            if await db.is_sudo_user(user_id):
                await message.reply_text("❌ User is already a sudo user!")
                return
            
            # Add sudo user
            success = await db.add_sudo_user(user_id)
            
            if success:
                try:
                    # Try to get username for better confirmation
                    username = await helpers.get_username_from_id(client, user_id)
                    await message.reply_text(f"✅ **Sudo user added successfully!**\n\nUser: {username}\nID: `{user_id}`")
                except:
                    await message.reply_text(f"✅ **Sudo user added successfully!**\n\nUser ID: `{user_id}`")
                
                logger.info(f"Sudo user {user_id} added by {message.from_user.id}")
            else:
                await message.reply_text("❌ Failed to add sudo user!")
                
        except ValueError:
            await message.reply_text("❌ Invalid user ID. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in addsudo command: {e}")
            await message.reply_text("❌ Error adding sudo user. Please try again.")
    
    async def rmsudo_command(self, client: Client, message: Message):
        """Handle /rmsudo command - remove sudo user (owner only)"""
        if not helpers.is_owner(message.from_user.id):
            await message.reply_text("❌ This command is only for bot owner.")
            return
        
        try:
            args = message.text.split()
            if len(args) != 2:
                await message.reply_text(
                    "🗑️ **Remove Sudo User**\n\n"
                    "**Usage:**\n"
                    "`/rmsudo <user_id>`\n\n"
                    "**Example:**\n"
                    "`/rmsudo 123456789`"
                )
                return
            
            user_id = int(args[1])
            
            # Check if user is sudo
            if not await db.is_sudo_user(user_id):
                await message.reply_text("❌ User is not a sudo user!")
                return
            
            # Don't allow removing owner
            if user_id == config.OWNER_ID:
                await message.reply_text("❌ Cannot remove bot owner from sudo users!")
                return
            
            # Remove sudo user
            success = await db.remove_sudo_user(user_id)
            
            if success:
                try:
                    # Try to get username for better confirmation
                    username = await helpers.get_username_from_id(client, user_id)
                    await message.reply_text(f"✅ **Sudo user removed successfully!**\n\nUser: {username}\nID: `{user_id}`")
                except:
                    await message.reply_text(f"✅ **Sudo user removed successfully!**\n\nUser ID: `{user_id}`")
                
                logger.info(f"Sudo user {user_id} removed by {message.from_user.id}")
            else:
                await message.reply_text("❌ Failed to remove sudo user!")
                
        except ValueError:
            await message.reply_text("❌ Invalid user ID. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in rmsudo command: {e}")
            await message.reply_text("❌ Error removing sudo user. Please try again.")
    
    async def staff_command(self, client: Client, message: Message):
        """Handle /staff command - show all sudo users"""
        # Only sudo users and owner can see staff list
        if not await helpers.is_sudo_user(message.from_user.id):
            await message.reply_text("❌ You are not authorized to view staff list.")
            return
        
        try:
            sudo_users = await db.get_sudo_users()
            
            staff_text = "👑 **Bot Staff Members**\n\n"
            
            # Add owner
            owner_username = await helpers.get_username_from_id(client, config.OWNER_ID)
            staff_text += f"👑 **Owner:** {owner_username} (`{config.OWNER_ID}`)\n\n"
            
            # Add sudo users
            if sudo_users:
                staff_text += "**Sudo Users:**\n"
                for user_id in sudo_users:
                    if user_id != config.OWNER_ID:  # Don't list owner twice
                        username = await helpers.get_username_from_id(client, user_id)
                        staff_text += f"• {username} (`{user_id}`)\n"
            else:
                staff_text += "**Sudo Users:** None\n"
            
            staff_text += f"\n**Total Staff:** {len(sudo_users) + 1} users"
            
            await message.reply_text(staff_text)
            
        except Exception as e:
            logger.error(f"Error in staff command: {e}")
            await message.reply_text("❌ Error fetching staff list. Please try again.")

def register_sudo_handlers(client: Client):
    """Register sudo management command handlers"""
    handlers = SudoHandlers(client)
    
    client.on_message(filters.command("addsudo"))(handlers.addsudo_command)
    client.on_message(filters.command("rmsudo"))(handlers.rmsudo_command)
    client.on_message(filters.command("staff"))(handlers.staff_command)
    
    logger.info("Sudo handlers registered successfully")