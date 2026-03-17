import os
import logging
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helpers.state import state_manager
from database import db
from config import MAX_VIDEO_SIZE, TEMP_DIR
from watermark.processor import process_video
import asyncio

logger = logging.getLogger(__name__)

def register_message_handlers(app):
    # Handle video messages
    @app.on_message(filters.video & filters.private)
    async def video_handler(client, message: Message):
        user_id = message.from_user.id
        
        # Check if user is banned
        if db.is_user_banned(user_id):
            await message.reply_text("You are banned from using this bot.")
            return
        
        # Check video size
        video = message.video
        if video.file_size > MAX_VIDEO_SIZE:
            await message.reply_text("Video size exceeds the limit of 2 GB.")
            return
        
        # Check if user has any saved watermarks
        watermarks = db.get_watermarks(user_id)
        if not watermarks:
            await message.reply_text(
                "You don't have any saved watermarks. Please create one first using /addwatermark."
            )
            return
        
        # Set state to waiting for watermark selection
        state_manager.set_state(user_id, "waiting_for_watermark_selection", {
            "video_file_id": video.file_id,
            "video_file_unique_id": video.file_unique_id,
            "video_file_name": video.file_name or "video.mp4",
            "video_file_size": video.file_size,
            "video_duration": video.duration,
            "video_width": video.width,
            "video_height": video.height
        })
        
        # Create inline keyboard with saved watermarks
        keyboard = []
        for i, wm in enumerate(watermarks, 1):
            wm_type = wm.get("type", "unknown")
            if wm_type == "text":
                label = f"Text: {wm.get('text', '')[:20]}..."
            else:
                label = "Image Watermark"
            keyboard.append([InlineKeyboardButton(f"Watermark {i}: {label}", callback_data=f"select_wm_{wm['_id']}")])
        
        keyboard.append([InlineKeyboardButton("Create New Watermark", callback_data="create_new_wm")])
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="wm_cancel")])
        
        await message.reply_text(
            "Which watermark do you want to apply?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Handle document messages (for other video formats like .mkv, .mov sent as documents)
    @app.on_message(filters.document & filters.private)
    async def document_handler(client, message: Message):
        user_id = message.from_user.id
        
        # Check if user is banned
        if db.is_user_banned(user_id):
            await message.reply_text("You are banned from using this bot.")
            return
        
        # Check if the document is a video file
        doc = message.document
        mime_type = doc.mime_type or ""
        if not mime_type.startswith("video/"):
            # Not a video, ignore or handle differently
            return
        
        # Check file size
        if doc.file_size > MAX_VIDEO_SIZE:
            await message.reply_text("File size exceeds the limit of 2 GB.")
            return
        
        # Check if user has any saved watermarks
        watermarks = db.get_watermarks(user_id)
        if not watermarks:
            await message.reply_text(
                "You don't have any saved watermarks. Please create one first using /addwatermark."
            )
            return
        
        # Set state to waiting for watermark selection
        state_manager.set_state(user_id, "waiting_for_watermark_selection", {
            "video_file_id": doc.file_id,
            "video_file_unique_id": doc.file_unique_id,
            "video_file_name": doc.file_name or "video.mp4",
            "video_file_size": doc.file_size,
            # For documents, we don't have duration, width, height directly. We'll get them after downloading.
            "video_duration": 0,
            "video_width": 0,
            "video_height": 0
        })
        
        # Create inline keyboard with saved watermarks
        keyboard = []
        for i, wm in enumerate(watermarks, 1):
            wm_type = wm.get("type", "unknown")
            if wm_type == "text":
                label = f"Text: {wm.get('text', '')[:20]}..."
            else:
                label = "Image Watermark"
            keyboard.append([InlineKeyboardButton(f"Watermark {i}: {label}", callback_data=f"select_wm_{wm['_id']}")])
        
        keyboard.append([InlineKeyboardButton("Create New Watermark", callback_data="create_new_wm")])
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="wm_cancel")])
        
        await message.reply_text(
            "Which watermark do you want to apply?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # Handle photo messages (for watermark image upload)
    @app.on_message(filters.photo & filters.private)
    async def photo_handler(client, message: Message):
        user_id = message.from_user.id
        state = state_manager.get_state(user_id)
        current_state = state['state']
        
        if current_state == "waiting_for_watermark_image":
            # User is uploading an image for watermark
            photo = message.photo[-1]  # Get the largest photo
            # Save the photo to temp directory
            os.makedirs(TEMP_DIR, exist_ok=True)
            file_path = os.path.join(TEMP_DIR, f"{user_id}_{photo.file_unique_id}.jpg")
            await client.download_media(photo, file_path=file_path)
            
            # Update state data with the image path
            state['data']['image_path'] = file_path
            state_manager.set_state(user_id, current_state, state['data'])
            
            # Ask for position
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Top-Left", callback_data="wm_pos_top_left"),
                    InlineKeyboardButton("Top-Right", callback_data="wm_pos_top_right"),
                    InlineKeyboardButton("Bottom-Left", callback_data="wm_pos_bottom_left"),
                    InlineKeyboardButton("Bottom-Right", callback_data="wm_pos_bottom_right")
                ],
                [
                    InlineKeyboardButton("Center", callback_data="wm_pos_center"),
                    InlineKeyboardButton("Custom", callback_data="wm_pos_custom")
                ],
                [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
            ])
            
            await message.reply_text(
                "Select position for the watermark image:",
                reply_markup=keyboard
            )
        else:
            # Not expecting a photo, ignore
            pass

    # Handle text messages for watermark text input and other text inputs
    @app.on_message(filters.text & filters.private)
    async def text_handler(client, message: Message):
        user_id = message.from_user.id
        state = state_manager.get_state(user_id)
        current_state = state['state']
        data = state['data']
        
        if current_state == "waiting_for_watermark_text":
            # User is entering text for text watermark
            data['text'] = message.text
            state_manager.set_state(user_id, current_state, data)
            
            # Ask for font size
            await message.reply_text(
                "Enter font size (e.g., 24):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                ])
            )
            # We'll change state to waiting for font size in the next step, but we need to handle it in callback or next text?
            # Let's change state now and wait for next text input for font size.
            state_manager.set_state(user_id, "waiting_for_font_size", data)
        
        elif current_state == "waiting_for_font_size":
            try:
                font_size = int(message.text)
                if font_size <= 0:
                    raise ValueError
                data['font_size'] = font_size
                state_manager.set_state(user_id, "waiting_for_font_size", data)
                
                # Ask for font color
                await message.reply_text(
                    "Enter font color (e.g., white or #FFFFFF):",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                    ])
                )
                state_manager.set_state(user_id, "waiting_for_font_color", data)
            except ValueError:
                await message.reply_text("Please enter a valid positive integer for font size.")
        
        elif current_state == "waiting_for_font_color":
            data['font_color'] = message.text
            state_manager.set_state(user_id, "waiting_for_font_color", data)
            
            # Ask for opacity
            await message.reply_text(
                "Enter opacity (0.0 to 1.0, e.g., 0.5):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                ])
            )
            state_manager.set_state(user_id, "waiting_for_opacity", data)
        
        elif current_state == "waiting_for_opacity":
            try:
                opacity = float(message.text)
                if opacity < 0 or opacity > 1:
                    raise ValueError
                data['opacity'] = opacity
                state_manager.set_state(user_id, "waiting_for_opacity", data)
                
                # Ask for position
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Top-Left", callback_data="wm_pos_top_left"),
                        InlineKeyboardButton("Top-Right", callback_data="wm_pos_top_right"),
                        InlineKeyboardButton("Bottom-Left", callback_data="wm_pos_bottom_left"),
                        InlineKeyboardButton("Bottom-Right", callback_data="wm_pos_bottom_right")
                    ],
                    [
                        InlineKeyboardButton("Center", callback_data="wm_pos_center"),
                        InlineKeyboardButton("Custom", callback_data="wm_pos_custom")
                    ],
                    [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                ])
                
                await message.reply_text(
                    "Select position for the watermark:",
                    reply_markup=keyboard
                )
                state_manager.set_state(user_id, "waiting_for_position", data)
            except ValueError:
                await message.reply_text("Please enter a valid number between 0.0 and 1.0 for opacity.")
        
        elif current_state == "waiting_for_custom_x":
            try:
                x = int(message.text)
                data['custom_x'] = x
                state_manager.set_state(user_id, "waiting_for_custom_x", data)
                
                # Ask for custom y
                await message.reply_text(
                    "Enter Y coordinate for custom position:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                    ])
                )
                state_manager.set_state(user_id, "waiting_for_custom_y", data)
            except ValueError:
                await message.reply_text("Please enter a valid integer for X coordinate.")
        
        elif current_state == "waiting_for_custom_y":
            try:
                y = int(message.text)
                data['custom_y'] = y
                state_manager.set_state(user_id, "waiting_for_custom_y", data)
                
                # Now ask for animation
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Static", callback_data="wm_anim_static"),
                        InlineKeyboardButton("Fade In", callback_data="wm_anim_fade_in"),
                        InlineKeyboardButton("Fade Out", callback_data="wm_anim_fade_out")
                    ],
                    [
                        InlineKeyboardButton("Blinking", callback_data="wm_anim_blinking"),
                        InlineKeyboardButton("Slide Left", callback_data="wm_anim_slide_left"),
                        InlineKeyboardButton("Slide Right", callback_data="wm_anim_slide_right")
                    ],
                    [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                ])
                
                await message.reply_text(
                    "Select animation for the watermark:",
                    reply_markup=keyboard
                )
                state_manager.set_state(user_id, "waiting_for_animation", data)
            except ValueError:
                await message.reply_text("Please enter a valid integer for Y coordinate.")
        
        else:
            # Not expecting text input, ignore or handle default
            pass