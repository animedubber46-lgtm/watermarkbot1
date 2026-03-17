import os
import logging
from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from helpers.state import state_manager
from database import db
from config import TEMP_DIR
from watermark.processor import process_video

logger = logging.getLogger(__name__)

def register_callback_handlers(app):
    @app.on_callback_query()
    async def callback_handler(client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        data = callback_query.data
        message = callback_query.message
        
        # Answer the callback query to remove the loading state
        await callback_query.answer()
        
        # Handle watermark type selection
        if data == "wm_type_text":
            state_manager.set_state(user_id, "waiting_for_watermark_text", {})
            await message.edit_text(
                "Enter the text for the watermark:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                ])
            )
        
        elif data == "wm_type_image":
            state_manager.set_state(user_id, "waiting_for_watermark_image", {})
            await message.edit_text(
                "Please upload an image to use as watermark:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                ])
            )
        
        # Handle watermark selection for video processing
        elif data.startswith("select_wm_"):
            watermark_id = data.split("_")[2]
            watermark = db.get_watermark(watermark_id)
            if not watermark:
                await message.edit_text("Watermark not found.")
                return
            
            # Get video details from state
            state = state_manager.get_state(user_id)
            if state['state'] != "waiting_for_watermark_selection":
                await message.edit_text("No video waiting for processing.")
                return
            
            video_data = state['data']
            # Set state to processing
            state_manager.set_state(user_id, "processing", {
                "watermark": watermark,
                "video_data": video_data
            })
            
            # Start processing
            await message.edit_text("Downloading video...")
            # We'll process in the background and update the message
            try:
                # Process the video
                processed_file = await process_video(
                    client, 
                    user_id, 
                    video_data, 
                    watermark,
                    status_message=message
                )
                
                if processed_file and os.path.exists(processed_file):
                    await message.edit_text("Uploading processed video...")
                    # Send the processed video
                    await client.send_video(
                        chat_id=user_id,
                        video=processed_file,
                        caption="Here is your video with watermark applied."
                    )
                    await message.delete()
                    # Clean up
                    state_manager.clear_state(user_id)
                    # Remove the processed file
                    if os.path.exists(processed_file):
                        os.remove(processed_file)
                else:
                    await message.edit_text("Failed to process video.")
            except Exception as e:
                logger.error(f"Error processing video: {e}")
                await message.edit_text(f"An error occurred: {str(e)}")
                state_manager.clear_state(user_id)
        
        # Handle create new watermark
        elif data == "create_new_wm":
            # Same as /addwatermark command
            state_manager.set_state(user_id, "waiting_for_watermark_type")
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Text Watermark", callback_data="wm_type_text"),
                    InlineKeyboardButton("Image Watermark", callback_data="wm_type_image")
                ],
                [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
            ])
            await message.edit_text(
                "What type of watermark do you want to create?",
                reply_markup=keyboard
            )
        
        # Handle cancel
        elif data == "wm_cancel":
            state_manager.clear_state(user_id)
            await message.edit_text("Operation cancelled.")
        
        # Handle watermark position selection (for both text and image)
        elif data.startswith("wm_pos_"):
            position = data.split("_")[2]
            state = state_manager.get_state(user_id)
            if state['state'] in ["waiting_for_position", "waiting_for_watermark_image"]:
                data_dict = state['data']
                data_dict['position'] = position
                state_manager.set_state(user_id, state['state'], data_dict)
                
                # If we were waiting for watermark image and now have position, ask for opacity
                if state['state'] == "waiting_for_watermark_image":
                    await message.edit_text(
                        "Enter opacity for the image watermark (0.0 to 1.0, e.g., 0.5):",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                        ])
                    )
                    state_manager.set_state(user_id, "waiting_for_image_opacity", data_dict)
                else:
                    # For text watermark, after position we ask for animation
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
                    await message.edit_text(
                        "Select animation for the watermark:",
                        reply_markup=keyboard
                    )
                    state_manager.set_state(user_id, "waiting_for_animation", data_dict)
        
        # Handle custom position (we need to ask for X and Y)
        elif data == "wm_pos_custom":
            state = state_manager.get_state(user_id)
            if state['state'] in ["waiting_for_position", "waiting_for_watermark_image"]:
                # We'll ask for X coordinate
                await message.edit_text(
                    "Enter X coordinate for custom position:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Cancel", callback_data="wm_cancel")]
                    ])
                )
                state_manager.set_state(user_id, "waiting_for_custom_x", state['data'])
        
        # Handle animation selection (for both text and image watermarks)
        elif data.startswith("wm_anim_"):
            animation = data.split("_")[2]
            state = state_manager.get_state(user_id)
            if state['state'] == "waiting_for_animation":
                data_dict = state['data']
                data_dict['animation'] = animation
                state_manager.set_state(user_id, "waiting_for_animation", data_dict)
                
                # Now we have all the data, save the watermark
                watermark_type = data_dict.get('type', 'text')  # default to text if not set
                if watermark_type == "text":
                    # Save the text watermark
                    watermark_data = {
                        "type": "text",
                        "text": data_dict.get('text'),
                        "font_size": data_dict.get('font_size', 24),
                        "font_color": data_dict.get('font_color', 'white'),
                        "opacity": data_dict.get('opacity', 0.5),
                        "position": data_dict.get('position', 'center'),
                        "animation": data_dict.get('animation', 'static')
                    }
                    watermark_id = db.add_watermark(user_id, watermark_data)
                    await message.edit_text(f"Text watermark saved successfully! (ID: {watermark_id})")
                    state_manager.clear_state(user_id)
                elif watermark_type == "image":
                    # Save the image watermark
                    watermark_data = {
                        "type": "image",
                        "image_path": data_dict.get('image_path'),
                        "opacity": data_dict.get('opacity', 0.5),
                        "position": data_dict.get('position', 'center'),
                        "animation": data_dict.get('animation', 'static')
                    }
                    watermark_id = db.add_watermark(user_id, watermark_data)
                    await message.edit_text(f"Image watermark saved successfully! (ID: {watermark_id})")
                    state_manager.clear_state(user_id)
                    # Clean up the temp image file? We'll keep it for now, but in production you might want to store it elsewhere.
                    # For now, we'll leave it in temp and clean up later or rely on OS cleanup.
        
        # Handle custom X input (we'll get this from text messages, not callbacks)
        # Actually, we handle custom X and Y in message_handlers.py via text input.
        # So we don't need to handle them here.
        
        # Handle image opacity input (we'll get this from text messages, not callbacks)
        # Similarly, handled in message_handlers.py.
        
        # We don't have any other callback data to handle for now.
