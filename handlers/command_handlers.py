from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helpers.state import state_manager
from database import db
from config import OWNER_ID
import os

def register_command_handlers(app):
    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client, message: Message):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        
        # Add user to database
        db.add_user(user_id, username, first_name, last_name)
        
        welcome_text = (
            f"Hello {first_name}! 👋\n"
            "I am a Telegram bot that adds watermarks to videos.\n"
            "You can save multiple watermark presets and apply them to videos.\n"
            "Send me a video to get started, or use /help to see available commands."
        )
        await message.reply_text(welcome_text)

    @app.on_message(filters.command("help") & filters.private)
    async def help_command(client, message: Message):
        help_text = (
            "Available commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/mywatermarks - View your saved watermarks\n"
            "/addwatermark - Create a new watermark\n"
            "/settings - Bot settings (if any)\n"
            "/cancel - Cancel current operation\n"
            "\n"
            "How to use:\n"
            "1. Send a video to the bot.\n"
            "2. If you have saved watermarks, choose one to apply.\n"
            "3. If not, create a watermark first using /addwatermark.\n"
            "4. The bot will process the video and send it back with the watermark.\n"
            "\n"
            "Features:\n"
            "- Text and image watermarks\n"
            "- Multiple watermark presets per user\n"
            "- Position, opacity, color, style, animation options\n"
            "- Quality-preserving processing\n"
            "- Supports videos up to 2 GB"
        )
        await message.reply_text(help_text)

    @app.on_message(filters.command("mywatermarks") & filters.private)
    async def mywatermarks_command(client, message: Message):
        user_id = message.from_user.id
        watermarks = db.get_watermarks(user_id)
        
        if not watermarks:
            await message.reply_text("You don't have any saved watermarks. Use /addwatermark to create one.")
            return
        
        text = "Your saved watermarks:\n\n"
        for i, wm in enumerate(watermarks, 1):
            wm_type = wm.get("type", "unknown")
            if wm_type == "text":
                text += f"{i}. Text: {wm.get('text', '')} (Position: {wm.get('position', 'center')})\n"
            else:
                text += f"{i}. Image watermark (Position: {wm.get('position', 'center')})\n"
        
        await message.reply_text(text)

    @app.on_message(filters.command("addwatermark") & filters.private)
    async def addwatermark_command(client, message: Message):
        user_id = message.from_user.id
        # Set state to waiting for watermark type
        state_manager.set_state(user_id, "waiting_for_watermark_type")
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Text Watermark", callback_data="wm_type_text"),
                InlineKeyboardButton("Image Watermark", callback_data="wm_type_image")
            ],
            [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
        ])
        
        await message.reply_text(
            "What type of watermark do you want to create?",
            reply_markup=keyboard
        )

    @app.on_message(filters.command("settings") & filters.private)
    async def settings_command(client, message: Message):
        # Placeholder for settings
        await message.reply_text("Settings feature is not implemented yet.")

    @app.on_message(filters.command("cancel") & filters.private)
    async def cancel_command(client, message: Message):
        user_id = message.from_user.id
        state_manager.clear_state(user_id)
        await message.reply_text("Operation cancelled.")

    # Owner commands
    @app.on_message(filters.command("broadcast") & filters.user(OWNER_ID) & filters.private)
    async def broadcast_command(client, message: Message):
        # This is a simplified broadcast. In production, you might want to use a proper broadcasting mechanism.
        if len(message.command) < 2:
            await message.reply_text("Usage: /broadcast <message>")
            return
        
        broadcast_msg = " ".join(message.command[1:])
        users = db.users.find({})
        count = 0
        for user in users:
            try:
                await client.send_message(user["_id"], broadcast_msg)
                count += 1
            except Exception as e:
                print(f"Failed to send message to {user['_id']}: {e}")
        
        await message.reply_text(f"Broadcast sent to {count} users.")

    @app.on_message(filters.command("stats") & filters.user(OWNER_ID) & filters.private)
    async def stats_command(client, message: Message):
        total_users = db.users.count_documents({})
        total_watermarks = db.watermarks.count_documents({})
        total_tasks = db.tasks.count_documents({})
        
        stats_text = (
            f"Bot Statistics:\n"
            f"Total users: {total_users}\n"
            f"Total watermarks: {total_watermarks}\n"
            f"Total processing tasks: {total_tasks}"
        )
        await message.reply_text(stats_text)

    @app.on_message(filters.command("ban") & filters.user(OWNER_ID) & filters.private)
    async def ban_command(client, message: Message):
        if len(message.command) < 2:
            await message.reply_text("Usage: /ban <user_id>")
            return
        
        try:
            user_id = int(message.command[1])
            db.ban_user(user_id)
            await message.reply_text(f"User {user_id} has been banned.")
        except ValueError:
            await message.reply_text("User ID must be a number.")
        except Exception as e:
            await message.reply_text(f"Error: {e}")

    @app.on_message(filters.command("unban") & filters.user(OWNER_ID) & filters.private)
    async def unban_command(client, message: Message):
        if len(message.command) < 2:
            await message.reply_text("Usage: /unban <user_id>")
            return
        
        try:
            user_id = int(message.command[1])
            db.unban_user(user_id)
            await message.reply_text(f"User {user_id} has been unbanned.")
        except ValueError:
            await message.reply_text("User ID must be a number.")
        except Exception as e:
            await message.reply_text(f"Error: {e}")