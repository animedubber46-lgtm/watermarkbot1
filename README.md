# Telegram Video Watermark Bot

A production-ready Telegram bot that adds watermarks to videos without noticeably reducing visual quality and without unnecessarily increasing file size. Built with Pyrogram, FFmpeg, and MongoDB.

## Features

- Support for videos up to 2 GB
- Text and image watermark modes
- Save multiple watermark presets per user
- Position, opacity, color, style, and animation options
- Quality-preserving FFmpeg processing
- Inline keyboard interface for easy watermark selection
- Progress updates for download, processing, and upload
- Owner/admin features (broadcast, stats, ban/unban)
- Clean temporary files after processing
- Modular and maintainable code structure

## Requirements

- Python 3.7+
- FFmpeg installed and available in PATH
- MongoDB instance
- Telegram API credentials (from my.telegram.org)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/telegram-watermark-bot.git
   cd telegram-watermark-bot
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on `.env.example`:
   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   OWNER_ID=your_telegram_user_id
   MONGO_URI=mongodb://localhost:27017/watermark_bot
   ```

4. Ensure FFmpeg is installed and accessible:
   - Windows: Download from https://ffmpeg.org/download.html and add to PATH
   - Linux: `sudo apt install ffmpeg` or equivalent
   - macOS: `brew install ffmpeg`

5. Run the bot:
   ```
   python bot.py
   ```

## Usage

1. Start the bot with `/start`
2. Create watermark presets using `/addwatermark`
   - Choose between text or image watermark
   - Customize text: font, size, color, opacity, position, animation
   - Customize image: opacity, position, animation
3. Send a video to the bot
4. Select which saved watermark to apply
5. Receive the processed video back

## Commands

- `/start` - Welcome message
- `/help` - Show help
- `/mywatermarks` - View your saved watermarks
- `/addwatermark` - Create a new watermark
- `/settings` - Bot settings (placeholder)
- `/cancel` - Cancel current operation

## Owner Commands

- `/broadcast <message>` - Send message to all users
- `/stats` - View bot statistics
- `/ban <user_id>` - Ban a user
- `/unban <user_id>` - Unban a user

## Environment Variables

- `API_ID` - Telegram API ID
- `API_HASH` - Telegram API hash
- `BOT_TOKEN` - Telegram bot token
- `OWNER_ID` - Telegram user ID of the bot owner
- `MONGO_URI` - MongoDB connection string

## FFmpeg Settings

The bot uses the following FFmpeg settings for quality preservation:
- Video codec: libx264
- Preset: medium (balance of speed and compression)
- CRF: 23 (good quality, reasonable file size)
- Audio: copied without re-encoding

## Project Structure

```
telegram-watermark-bot/
├── bot.py                 # Main bot entry point
├── config.py              # Configuration and environment variables
├── database.py            # MongoDB connection and models
├── requirements.txt       # Python dependencies
├── Procfile               # For Heroku-like deployment
├── README.md              # This file
├── .env.example           # Example environment variables
├── handlers/              # Message and callback handlers
│   ├── __init__.py
│   ├── command_handlers.py
│   ├── message_handlers.py
│   └── callback_handlers.py
├── helpers/               # Helper classes
│   └── state.py           # User conversation state management
├── utils/                 # Utility functions (to be expanded)
└── watermark/             # Watermark processing logic
    └── processor.py       # FFmpeg-based watermark application
```

## Deployment

The bot is ready for deployment on VPS, Render, Heroku, or similar platforms:

### Heroku
1. Create a Heroku app
2. Add the MongoDB addon or set MONGO_URI config var
3. Set all required environment variables
4. Deploy using Git or Heroku CLI

### Docker (example)
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

CMD ["python", "bot.py"]
```

## License

MIT License - feel free to use and modify as needed.