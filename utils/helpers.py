import re
import socket
import time
import zipfile
import datetime
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import phonenumbers
import psutil
from telegram import Bot
from telegram.error import TelegramError
import config
import socks


def normalize_phone_number(raw_phone: str) -> Optional[Dict[str, Any]]:
    """Cleans and validates phone number string into E.164 and dial code."""
    # Keep only digits and '+'
    cleaned = re.sub(r"[^\d+]", "", raw_phone.strip())
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    try:
        parsed = phonenumbers.parse(cleaned, None)
        if not phonenumbers.is_possible_number(parsed):
            return None

        e164_format = phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        )
        dial_code = f"+{parsed.country_code}"

        return {
            "e164": e164_format,
            "dial_code": dial_code,
            "national_number": str(parsed.national_number),
            "country_code": parsed.country_code,
        }
    except Exception:
        # Fallback regex if phonenumbers library rejects
        m = re.match(r"^(\+\d{1,4})(\d{6,14})$", cleaned)
        if m:
            return {
                "e164": cleaned,
                "dial_code": m.group(1),
                "national_number": m.group(2),
                "country_code": int(m.group(1).replace("+", "")),
            }
        return None


async def check_force_join(bot: Bot, user_id: int, channel: str) -> bool:
    """Returns True if force join is disabled or if user is a member of the channel."""
    if not channel or not channel.strip():
        return True

    channel = channel.strip()
    try:
        # Check chat member status
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in ["creator", "administrator", "member", "restricted"]:
            return True
        return False
    except TelegramError as e:
        # If bot is not admin in the channel or channel not found, log but don't hard block user
        print(f"[ForceJoin Warning] Could not check membership in {channel}: {e}")
        return True


def get_server_metrics() -> Dict[str, Any]:
    """Returns current CPU, RAM, and Disk metrics."""
    cpu = psutil.cpu_percent(interval=0.1)
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(config.BASE_DIR))

    return {
        "cpu_percent": cpu,
        "ram_percent": vm.percent,
        "ram_used_gb": round(vm.used / (1024**3), 2),
        "ram_total_gb": round(vm.total / (1024**3), 2),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_percent": disk.percent,
    }


def create_system_backup() -> str:
    """Creates a full backup zip of database and session files."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.zip"
    backup_path = config.EXPORTS_DIR / backup_filename

    with zipfile.ZipFile(
        backup_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
    ) as zipf:
        # Add database file if exists
        if config.DB_PATH.exists():
            zipf.write(config.DB_PATH, arcname="database.db")

        # Add all session files
        if config.SESSIONS_DIR.exists():
            for root, dirs, files in os.walk(config.SESSIONS_DIR):
                for file in files:
                    full_file_path = Path(root) / file
                    arc_path = full_file_path.relative_to(config.BASE_DIR)
                    zipf.write(full_file_path, arcname=str(arc_path))

    return str(backup_path)


def create_sessions_zip(category: Optional[str] = None) -> Optional[str]:
    """Creates a ZIP archive of .session files for a specific category or all confirmed."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = config.CONFIRMED_SESSIONS_DIR

    prefix = "all_confirmed"
    if category:
        cat_lower = category.lower().replace(" ", "_")
        prefix = cat_lower
        if "spam" in cat_lower:
            target_dir = config.CONFIRMED_SPAM_DIR
        elif "new" in cat_lower:
            target_dir = config.CONFIRMED_NEW_ACC_DIR
        else:
            target_dir = config.CONFIRMED_FREE_DIR

    session_files = list(target_dir.rglob("*.session"))
    if not session_files:
        return None

    zip_filename = f"sessions_{prefix}_{timestamp}.zip"
    zip_path = config.EXPORTS_DIR / zip_filename

    with zipfile.ZipFile(
        zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
    ) as zipf:
        for f in session_files:
            zipf.write(f, arcname=f.name)

    return str(zip_path)


def test_proxy_ping(
    proxy_type: str,
    host: str,
    port: int,
    username: str = "",
    password: str = "",
) -> Dict[str, Any]:
    """Tests connection to Telegram server through proxy and measures latency."""
    if not host or not port:
        return {"success": False, "error": "Host or Port not specified"}

    test_target_host = "149.154.167.50"  # Telegram DC2 IP
    test_target_port = 443

    proxy_type_upper = proxy_type.strip().upper()
    sock_type = (
        socks.SOCKS5 if "SOCKS5" in proxy_type_upper else socks.HTTP
    )

    s = socks.socksocket()
    s.set_proxy(
        sock_type,
        addr=host,
        port=int(port),
        username=username if username else None,
        password=password if password else None,
    )
    s.settimeout(8.0)

    start_time = time.time()
    try:
        s.connect((test_target_host, test_target_port))
        latency_ms = round((time.time() - start_time) * 1000, 1)
        s.close()
        return {
            "success": True,
            "latency_ms": latency_ms,
            "target": f"{test_target_host}:{test_target_port}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


import os
