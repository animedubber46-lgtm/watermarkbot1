import os

def format_file_size(size_bytes):
    """Convert bytes to human readable format."""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f}{size_names[i]}"

def get_file_extension(filename):
    """Get file extension from filename."""
    return os.path.splitext(filename)[1].lower()

def is_video_file(filename):
    """Check if file is a video based on extension."""
    video_extensions = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.wmv'}
    return get_file_extension(filename) in video_extensions

def is_image_file(filename):
    """Check if file is an image based on extension."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
    return get_file_extension(filename) in image_extensions