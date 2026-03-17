import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI", "")

# Other settings
MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB in bytes
TEMP_DIR = "temp"