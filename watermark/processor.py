import os
import logging
import asyncio
from config import TEMP_DIR
import ffmpeg

logger = logging.getLogger(__name__)

async def process_video(client, user_id, video_data, watermark, status_message=None):
    """
    Process a video by applying a watermark.
    
    Args:
        client: Pyrogram client
        user_id: Telegram user ID
        video_data: Dictionary containing video information
        watermark: Dictionary containing watermark information
        status_message: Message object to update with progress
    
    Returns:
        Path to the processed video file, or None if failed
    """
    try:
        # Create temp directory if it doesn't exist
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # Download the video
        input_path = os.path.join(TEMP_DIR, f"{user_id}_{video_data['video_file_unique_id']}_input.mp4")
        output_path = os.path.join(TEMP_DIR, f"{user_id}_{video_data['video_file_unique_id']}_output.mp4")
        
        if status_message:
            await status_message.edit_text("Downloading video...")
        
        # Download video from Telegram
        await client.download_media(
            message_id=video_data['video_file_id'],
            file_name=input_path
        )
        
        if status_message:
            await status_message.edit_text("Processing video...")
        
        # Apply watermark based on type
        if watermark['type'] == 'text':
            await apply_text_watermark(input_path, output_path, watermark, status_message)
        elif watermark['type'] == 'image':
            await apply_image_watermark(input_path, output_path, watermark, status_message)
        else:
            raise ValueError(f"Unknown watermark type: {watermark['type']}")
        
        if status_message:
            await status_message.edit_text("Processing complete!")
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        if status_message:
            await status_message.edit_text(f"Error processing video: {str(e)}")
        return None
    finally:
        # Clean up input file
        if 'input_path' in locals() and os.path.exists(input_path):
            try:
                os.remove(input_path)
            except:
                pass

async def apply_text_watermark(input_path, output_path, watermark, status_message=None):
    """Apply text watermark to video using FFmpeg."""
    try:
        # Build FFmpeg command for text watermark
        # Escape special characters in text for FFmpeg drawtext filter
        text = watermark['text'].replace("'", r"\'").replace(":", r"\:").replace("%", r"\%")
        
        # Prepare drawtext options
        drawtext_options = [
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Default font, adjust as needed
            f"text='{text}'",
            f"fontsize={watermark['font_size']}",
            f"fontcolor={watermark['font_color']}@{watermark['opacity']}",
        ]
        
        # Add position
        position = watermark['position']
        if position == 'top-left':
            drawtext_options.append("x=10")
            drawtext_options.append("y=10")
        elif position == 'top-right':
            drawtext_options.append("x=w-tw-10")
            drawtext_options.append("y=10")
        elif position == 'bottom-left':
            drawtext_options.append("x=10")
            drawtext_options.append("y=h-th-10")
        elif position == 'bottom-right':
            drawtext_options.append("x=w-tw-10")
            drawtext_options.append("y=h-th-10")
        elif position == 'center':
            drawtext_options.append("x=(w-tw)/2")
            drawtext_options.append("y=(h-th)/2")
        # Custom position would be handled separately
        
        # Add animation effects based on watermark['animation']
        animation = watermark.get('animation', 'static')
        if animation == 'fade_in':
            drawtext_options.append(f"alpha='if(gte(t,0), min(1, t/0.5), 0)'")
        elif animation == 'fade_out':
            # Assuming video duration is available, we'd need to get it
            # For simplicity, we'll use a fixed duration or skip
            pass
        elif animation == 'blinking':
            drawtext_options.append(f"alpha='mod(t, 1)'")
        elif animation == 'slide_left':
            drawtext_options.append(f"x='if(gte(t,0), (w-tw)- (w+t)*t/5, (w-tw))'")
        elif animation == 'slide_right':
            drawtext_options.append(f"x='if(gte(t,0), (w+t)*t/5 - tw, 0)'")
        # For static, no additional options needed
        
        # Join drawtext options
        drawtext_filter = ",".join(drawtext_options)
        
        # Build FFmpeg command
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                vf=f"drawtext={drawtext_filter}",
                **{
                    'c:v': 'libx264',
                    'preset': 'medium',
                    'crf': '23',  # Good quality, reasonable size
                    'c:a': 'copy',  # Copy audio without re-encoding
                }
            )
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
        
        logger.info(f"Text watermark applied successfully: {output_path}")
        
    except Exception as e:
        logger.error(f"Error applying text watermark: {e}")
        raise

async def apply_image_watermark(input_path, output_path, watermark, status_message=None):
    """Apply image watermark to video using FFmpeg."""
    try:
        image_path = watermark['image_path']
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Watermark image not found: {image_path}")
        
        # Prepare overlay options
        position = watermark['position']
        opacity = watermark.get('opacity', 0.5)
        
        # Calculate position coordinates
        if position == 'top-left':
            x, y = '10', '10'
        elif position == 'top-right':
            x, y = 'w-wt-10', '10'
        elif position == 'bottom-left':
            x, y = '10', 'h-ht-10'
        elif position == 'bottom-right':
            x, y = 'w-wt-10', 'h-ht-10'
        elif position == 'center':
            x, y = '(w-wt)/2', '(h-ht)/2'
        else:
            # Default to center
            x, y = '(w-wt)/2', '(h-ht)/2'
        
        # Add animation effects
        animation = watermark.get('animation', 'static')
        if animation == 'fade_in':
            # Fade in over first second
            x, y = x, y
            # We'll need to modify the opacity over time
            # This is more complex, for now we'll use a static position with fade effect
            # FFmpeg doesn't easily support animated position without complex expressions
            # For simplicity, we'll just use static position with opacity fade
            pass
        elif animation == 'fade_out':
            pass
        elif animation == 'blinking':
            pass
        elif animation == 'slide_left':
            pass
        elif animation == 'slide_right':
            pass
        
        # Build FFmpeg command
        (
            ffmpeg
            .input(input_path)
            .input(image_path)
            .filter_('overlay', x=x, y=y)
            .output(
                output_path,
                **{
                    'c:v': 'libx264',
                    'preset': 'medium',
                    'crf': '23',
                    'c:a': 'copy',
                }
            )
            .overwrite_output()
            .run(quiet=True, capture_stdout=True, capture_stderr=True)
        )
        
        logger.info(f"Image watermark applied successfully: {output_path}")
        
    except Exception as e:
        logger.error(f"Error applying image watermark: {e}")
        raise