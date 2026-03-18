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
    input_path = None
    output_path = None

    try:
        os.makedirs(TEMP_DIR, exist_ok=True)

        input_path = os.path.join(
            TEMP_DIR,
            f"{user_id}_{video_data['video_file_unique_id']}_input.mp4"
        )
        output_path = os.path.join(
            TEMP_DIR,
            f"{user_id}_{video_data['video_file_unique_id']}_output.mp4"
        )

        if status_message:
            await status_message.edit_text("Downloading video...")

        # FIXED: do not use message_id=
        await client.download_media(
            video_data['video_file_id'],
            file_name=input_path
        )

        if not os.path.exists(input_path):
            raise FileNotFoundError("Downloaded input video was not found.")

        if status_message:
            await status_message.edit_text("Processing video...")

        if watermark['type'] == 'text':
            await apply_text_watermark(input_path, output_path, watermark, status_message)
        elif watermark['type'] == 'image':
            await apply_image_watermark(input_path, output_path, watermark, status_message)
        else:
            raise ValueError(f"Unknown watermark type: {watermark['type']}")

        if not os.path.exists(output_path):
            raise FileNotFoundError("Output video was not created by FFmpeg.")

        if status_message:
            await status_message.edit_text("Processing complete!")

        return output_path

    except Exception as e:
        logger.exception("Error processing video")
        if status_message:
            msg = str(e)
            if len(msg) > 3500:
                msg = msg[:3500] + "..."
            await status_message.edit_text(f"❌ Processing failed!\n\n{msg}")
        return None

    finally:
        if input_path and os.path.exists(input_path):
            try:
                os.remove(input_path)
            except Exception:
                pass


async def apply_text_watermark(input_path, output_path, watermark, status_message=None):
    """Apply text watermark to video using FFmpeg."""
    try:
        text = str(watermark['text'])
        text = (
            text.replace("\\", r"\\")
                .replace(":", r"\:")
                .replace("'", r"\'")
                .replace("%", r"\%")
                .replace("[", r"\[")
                .replace("]", r"\]")
                .replace(",", r"\,")
        )

        font_size = int(watermark.get('font_size', 30))
        font_color = str(watermark.get('font_color', 'white'))
        opacity = float(watermark.get('opacity', 1.0))
        opacity = max(0.0, min(1.0, opacity))

        drawtext_options = [
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            f"text='{text}'",
            f"fontsize={font_size}",
            f"fontcolor={font_color}@{opacity}",
        ]

        position = watermark.get('position', 'top-left')
        if position == 'top-left':
            drawtext_options += ["x=10", "y=10"]
        elif position == 'top-right':
            drawtext_options += ["x=w-tw-10", "y=10"]
        elif position == 'bottom-left':
            drawtext_options += ["x=10", "y=h-th-10"]
        elif position == 'bottom-right':
            drawtext_options += ["x=w-tw-10", "y=h-th-10"]
        elif position == 'center':
            drawtext_options += ["x=(w-tw)/2", "y=(h-th)/2"]
        else:
            drawtext_options += ["x=10", "y=10"]

        # Keep static first for debugging
        animation = watermark.get('animation', 'static')
        if animation == 'blinking':
            drawtext_options.append("alpha=if(lt(mod(t\\,1)\\,0.5)\\,1\\,0)")
        elif animation == 'fade_in':
            drawtext_options.append("alpha=if(lt(t\\,1)\\,t\\,1)")
        # For now skip slide animations until basic mode works

        drawtext_filter = ":".join(drawtext_options)

        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(
            stream,
            output_path,
            vf=f"drawtext={drawtext_filter}",
            vcodec='libx264',
            preset='medium',
            crf=23,
            acodec='copy'
        )

        stream = ffmpeg.overwrite_output(stream)

        try:
            out, err = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            if err:
                logger.info("FFmpeg text watermark stderr:\n%s", err.decode("utf-8", errors="ignore"))
        except ffmpeg.Error as e:
            stderr_text = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            logger.error("FFmpeg text watermark failed:\n%s", stderr_text)
            raise Exception(f"FFmpeg text watermark error:\n{stderr_text}")

        logger.info(f"Text watermark applied successfully: {output_path}")

    except Exception as e:
        logger.exception("Error applying text watermark")
        raise


async def apply_image_watermark(input_path, output_path, watermark, status_message=None):
    """Apply image watermark to video using FFmpeg."""
    try:
        image_path = watermark['image_path']
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Watermark image not found: {image_path}")

        position = watermark.get('position', 'center')
        opacity = float(watermark.get('opacity', 0.5))
        opacity = max(0.0, min(1.0, opacity))

        if position == 'top-left':
            x, y = '10', '10'
        elif position == 'top-right':
            x, y = 'main_w-overlay_w-10', '10'
        elif position == 'bottom-left':
            x, y = '10', 'main_h-overlay_h-10'
        elif position == 'bottom-right':
            x, y = 'main_w-overlay_w-10', 'main_h-overlay_h-10'
        elif position == 'center':
            x, y = '(main_w-overlay_w)/2', '(main_h-overlay_h)/2'
        else:
            x, y = '(main_w-overlay_w)/2', '(main_h-overlay_h)/2'

        video_stream = ffmpeg.input(input_path)
        watermark_stream = ffmpeg.input(image_path)

        # Apply opacity correctly
        watermark_stream = watermark_stream.filter('format', 'rgba').filter(
            'colorchannelmixer',
            aa=opacity
        )

        stream = ffmpeg.overlay(video_stream, watermark_stream, x=x, y=y)

        stream = ffmpeg.output(
            stream,
            output_path,
            vcodec='libx264',
            preset='medium',
            crf=23,
            acodec='copy'
        )

        stream = ffmpeg.overwrite_output(stream)

        try:
            out, err = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            if err:
                logger.info("FFmpeg image watermark stderr:\n%s", err.decode("utf-8", errors="ignore"))
        except ffmpeg.Error as e:
            stderr_text = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            logger.error("FFmpeg image watermark failed:\n%s", stderr_text)
            raise Exception(f"FFmpeg image watermark error:\n{stderr_text}")

        logger.info(f"Image watermark applied successfully: {output_path}")

    except Exception as e:
        logger.exception("Error applying image watermark")
        raise
