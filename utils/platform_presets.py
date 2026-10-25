from typing import Dict, Any
import config

PLATFORM_PRESETS = {
    "TD-direct": {
        "name": "TD-direct",
        "description": "Telegram Desktop (Windows 11 Direct x64)",
        "device_model": "Desktop",
        "system_version": "Windows 11 x64",
        "app_version": "5.4.1 x64",
        "system_lang_code": "en",
        "lang_code": "en",
    },
    "Android": {
        "name": "Android",
        "description": "Official Telegram for Android (Samsung Galaxy S24 Ultra)",
        "device_model": "Samsung Galaxy S24 Ultra",
        "system_version": "Android 14 (API 34)",
        "app_version": "10.14.5",
        "system_lang_code": "en",
        "lang_code": "en",
    },
    "Bot Android": {
        "name": "Bot Android",
        "description": "Custom Android Preset (Google Pixel 8 Pro)",
        "device_model": "Google Pixel 8 Pro",
        "system_version": "Android 15 (API 35)",
        "app_version": "11.0.1",
        "system_lang_code": "en",
        "lang_code": "en",
    },
}


def get_platform_info(platform_name: str) -> Dict[str, Any]:
    return PLATFORM_PRESETS.get(platform_name, PLATFORM_PRESETS["TD-direct"])
