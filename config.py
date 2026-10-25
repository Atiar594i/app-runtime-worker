import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Bot Credentials
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "5597944494,8685436749")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_RAW.split(",") if i.strip().isdigit()]
for _sid in [5597944494, 8685436749]:
    if _sid not in ADMIN_IDS:
        ADMIN_IDS.append(_sid)

# Default MTProto API Configuration (Telegram Desktop / Android official public values)
# These can be dynamically customized from the Admin Panel
DEFAULT_API_ID = int(os.getenv("API_ID", "2040"))
DEFAULT_API_HASH = os.getenv("API_HASH", "b18441a1ff607e10a989891a5462e627")
DEFAULT_APP_VERSION = os.getenv("APP_VERSION", "10.14.5")
DEFAULT_SYSTEM_LANG_CODE = os.getenv("SYSTEM_LANG_CODE", "en")

# Platform presets for device spoofing in Telethon client
PLATFORM_PRESETS = {
    "TD-direct": {
        "name": "TD-direct",
        "device_model": "Desktop",
        "system_version": "Windows 11 x64",
        "app_version": "5.4.1 x64",
        "system_lang_code": "en",
        "lang_code": "en",
    },
    "Android": {
        "name": "Android",
        "device_model": "Samsung Galaxy S24 Ultra",
        "system_version": "Android 14 (API 34)",
        "app_version": "10.14.5",
        "system_lang_code": "en",
        "lang_code": "en",
    },
    "Bot Android": {
        "name": "Bot Android",
        "device_model": "Google Pixel 8 Pro",
        "system_version": "Android 15 (API 35)",
        "app_version": "11.0.1",
        "system_lang_code": "en",
        "lang_code": "en",
    },
}

# Directories
DB_PATH = BASE_DIR / "database.db"
SESSIONS_DIR = BASE_DIR / "sessions"
TEMP_SESSIONS_DIR = SESSIONS_DIR / "temp"
CONFIRMED_SESSIONS_DIR = SESSIONS_DIR / "confirmed"
CONFIRMED_FREE_DIR = CONFIRMED_SESSIONS_DIR / "free"
CONFIRMED_SPAM_DIR = CONFIRMED_SESSIONS_DIR / "spam"
CONFIRMED_NEW_ACC_DIR = CONFIRMED_SESSIONS_DIR / "new_acc"
EXPORTS_DIR = BASE_DIR / "exports"

# Create all necessary runtime directories
for directory in [
    SESSIONS_DIR,
    TEMP_SESSIONS_DIR,
    CONFIRMED_SESSIONS_DIR,
    CONFIRMED_FREE_DIR,
    CONFIRMED_SPAM_DIR,
    CONFIRMED_NEW_ACC_DIR,
    EXPORTS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)
