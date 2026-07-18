import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

API_URL = os.getenv("API_URL", "").rstrip("/")
API_KEY = os.getenv("API_KEY", "")

MONGO_URI = os.getenv("MONGO_URI", "")
DB_NAME = os.getenv("DB_NAME", "MusicBot")

USERBOT_STRINGS = [os.getenv(f"STRING{i}", "") for i in range(1, 11) if os.getenv(f"STRING{i}")]

SONG_DURATION_LIMIT = int(os.getenv("SONG_DURATION_LIMIT", 0) or 0)

LOGGER_ID = os.getenv("LOGGER_ID")
LOGGER_ID = int(LOGGER_ID) if LOGGER_ID and (LOGGER_ID.startswith("-100") or LOGGER_ID.lstrip("-").isdigit()) else None

SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "")
DEVS = [int(x.strip()) for x in os.getenv("DEVS", "").split(",") if x.strip()]

DEFAULT_SERVICE = os.getenv("DEFAULT_SERVICE", "youtube")
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "./downloads")
COOKIES_URL = os.getenv("COOKIES_URL", "")
ENABLE_VPLAY = os.getenv("ENABLE_VPLAY", "false").lower() == "true"
