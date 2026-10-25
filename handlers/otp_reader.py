import re
import os
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from telethon import TelegramClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import config
import database


def discover_disk_sessions() -> List[Path]:
    """Recursively finds all .session files in config.SESSIONS_DIR and subfolders."""
    sessions_dir = Path(config.SESSIONS_DIR)
    if not sessions_dir.exists():
        return []
    # Use rglob to search recursively into free/, spam/, new_acc/, temp/, etc.
    files = list(sessions_dir.rglob("*.session"))
    # Exclude temp files if there are duplicate confirmed files
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


async def get_all_session_items() -> List[Dict[str, Any]]:
    """
    Combines SQLite database accounts and disk .session files to provide a complete list.
    """
    disk_files = discover_disk_sessions()
    file_map = {}
    for f in disk_files:
        clean_stem = f.stem.replace("+", "").strip()
        file_map[clean_stem] = f

    db_accounts = await database.get_all_accounts()
    items = []
    seen = set()

    for acc in db_accounts:
        phone = acc.get("phone", "")
        clean_p = phone.replace("+", "").strip()
        seen.add(clean_p)
        sp = Path(acc.get("session_path", ""))
        if not sp.exists() and clean_p in file_map:
            sp = file_map[clean_p]

        cat = acc.get("category", "Free")
        items.append({
            "phone": phone,
            "label": f"📱 {phone} ({cat})",
            "identifier": clean_p,
            "path": sp,
            "mtime": sp.stat().st_mtime if sp.exists() else 0,
        })

    # Add disk session files that might not be in db_accounts
    for clean_stem, f in file_map.items():
        if clean_stem not in seen:
            seen.add(clean_stem)
            # determine category by parent folder name if possible
            parent_name = f.parent.name.capitalize()
            items.append({
                "phone": f"+{clean_stem}",
                "label": f"📱 +{clean_stem} ({parent_name})",
                "identifier": clean_stem,
                "path": f,
                "mtime": f.stat().st_mtime if f.exists() else 0,
            })

    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


async def get_session_login_code(session_identifier: str) -> Dict[str, Any]:
    """
    Retrieves the latest Telegram login verification code (OTP) sent to a session file.
    Matches session by phone number, database record, filename, or stem.
    """
    if not session_identifier:
        return {"success": False, "error": "Session identifier or phone number is required."}

    clean_id = str(session_identifier).strip()
    clean_digits = re.sub(r"[^\d]", "", clean_id)
    clean_stem = Path(clean_id).stem.lower()

    matching_path: Optional[Path] = None

    # 1. Try finding in database accounts first
    db_accounts = await database.get_all_accounts()
    for acc in db_accounts:
        p_digits = re.sub(r"[^\d]", "", acc.get("phone", ""))
        if clean_digits and (clean_digits == p_digits or clean_digits.endswith(p_digits) or p_digits.endswith(clean_digits)):
            sp = Path(acc.get("session_path", ""))
            if sp.exists():
                matching_path = sp
                break

    # 2. Search recursively on disk via rglob
    if not matching_path:
        all_sessions = discover_disk_sessions()
        for s_path in all_sessions:
            s_stem = s_path.stem.lower()
            if clean_stem and (clean_stem == s_stem or clean_stem in s_stem or s_stem in clean_stem):
                matching_path = s_path
                break

        if not matching_path and clean_digits:
            for s_path in all_sessions:
                s_digits = re.sub(r"[^\d]", "", s_path.stem)
                if s_digits and (clean_digits == s_digits or clean_digits.endswith(s_digits) or s_digits.endswith(clean_digits)):
                    matching_path = s_path
                    break

    if not matching_path or not matching_path.exists():
        return {
            "success": False,
            "error": f"'{session_identifier}' নম্বরের কোনো সেশন ফাইল খুঁজে পাওয়া যায়নি।"
        }

    # Fetch API credentials
    api_id_str = await database.get_setting("app_id", str(config.DEFAULT_API_ID))
    api_hash = await database.get_setting("app_hash", config.DEFAULT_API_HASH)
    try:
        api_id = int(api_id_str)
    except Exception:
        api_id = config.DEFAULT_API_ID

    client = TelegramClient(str(matching_path), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return {
                "success": False,
                "error": f"সেশন `{matching_path.name}` অথরাইজড নয় বা এক্সপায়ার হয়ে গেছে।"
            }

        me = await client.get_me()
        phone_num = f"+{me.phone}" if getattr(me, "phone", None) else f"+{clean_digits}"
        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or "User"
        sess_name = matching_path.stem

        # Fetch messages from Telegram service (777000)
        messages = await client.get_messages(777000, limit=10)

        if not messages:
            return {
                "success": True,
                "found": False,
                "phone": phone_num,
                "name": full_name,
                "session_name": sess_name,
                "message": "টেলিগ্রাম সার্ভিস (777000) থেকে এখনও কোনো বার্তা আসেনি।"
            }

        for msg in messages:
            if not msg.text:
                continue
            code_match = re.search(r"(?:code|код|kod|código|رمز)[^\d]*(\d{5,6})", msg.text, re.I)
            if not code_match:
                code_match = re.search(r"\b(\d{5,6})\b", msg.text)

            if code_match:
                login_code = code_match.group(1)
                date_str = msg.date.strftime("%Y-%m-%d %H:%M:%S UTC") if getattr(msg, "date", None) else "Recent"
                return {
                    "success": True,
                    "found": True,
                    "code": login_code,
                    "date": date_str,
                    "phone": phone_num,
                    "name": full_name,
                    "session_name": sess_name,
                    "raw_text": msg.text
                }

        latest = messages[0]
        date_str = latest.date.strftime("%Y-%m-%d %H:%M:%S UTC") if getattr(latest, "date", None) else "Recent"
        return {
            "success": True,
            "found": True,
            "code": "N/A",
            "date": date_str,
            "phone": phone_num,
            "name": full_name,
            "session_name": sess_name,
            "raw_text": latest.text or "(Empty message)"
        }

    except Exception as e:
        return {"success": False, "error": f"ত্রুটি: {str(e)}"}
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def show_otp_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Displays list of available sessions to retrieve login code from."""
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    session_items = await get_all_session_items()

    if not session_items:
        msg = (
            "🔑 **টেলিগ্রাম লগইন কোড (Get Login Code):**\n\n"
            "⚠️ বর্তমানে বটে কোনো সেশন ফাইল সংরক্ষিত নেই।\n"
            "ইউজার বা এডমিন কোনো নম্বর যুক্ত করার পর এখানে সেশনের তালিকা দেখা যাবে।"
        )
        kb = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")]]
        if query:
            await query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        elif update.message:
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return

    page_size = 5
    total_pages = (len(session_items) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))
    current_batch = session_items[page * page_size : (page + 1) * page_size]

    keyboard = []
    for item in current_batch:
        ident = item["identifier"]
        label = item["label"]
        keyboard.append([
            InlineKeyboardButton(label, callback_data=f"adm_get_code_{ident}")
        ])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"adm_otp_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"adm_otp_page_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton("🔍 ম্যানুয়ালি নম্বর দিয়ে কোড খুঁজুন", callback_data="adm_otp_input_phone")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")])

    text = (
        f"🔑 **টেলিগ্রাম লগইন কোড ড্যাশবোর্ড (Get Login Code)**\n\n"
        f"মোট সেশন: `{len(session_items)}` (পেজ {page + 1}/{total_pages})\n\n"
        "👉 যে অ্যাকাউন্টের লগইন কোড প্রয়োজন নিচের তালিকা থেকে সেই নম্বরে চাপ দিন:"
    )

    if query:
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


async def handle_fetch_otp_click(update: Update, context: ContextTypes.DEFAULT_TYPE, identifier: str):
    """Fetches and displays the OTP code for a selected session."""
    query = update.callback_query
    if query:
        try:
            await query.answer("Fetching Telegram login code... ⏳")
        except Exception:
            pass

    status_msg = None
    wait_text = f"⏳ `{identifier}` অ্যাকাউন্টের টেলিগ্রাম লগইন কোড আনার চেষ্টা করা হচ্ছে..."
    if query:
        status_msg = await query.message.edit_text(wait_text, parse_mode=ParseMode.MARKDOWN)
    elif update.message:
        status_msg = await update.message.reply_text(wait_text, parse_mode=ParseMode.MARKDOWN)

    res = await get_session_login_code(identifier)

    if not res.get("success"):
        kb = [
            [InlineKeyboardButton("🔄 আবার চেষ্টা করুন", callback_data=f"adm_get_code_{identifier}")],
            [InlineKeyboardButton("🔙 Back to Code List", callback_data="adm_get_code")],
        ]
        msg = f"❌ **লগইন কোড আনতে ব্যর্থ হয়েছে:**\n`{res.get('error', 'Unknown error')}`"
        if status_msg:
            await status_msg.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        return

    sess_name = res.get("session_name", identifier)
    kb = [
        [InlineKeyboardButton("🔄 Refresh Code", callback_data=f"adm_get_code_{sess_name}")],
        [InlineKeyboardButton("🔙 Back to List", callback_data="adm_get_code")],
    ]

    code = res.get("code")
    date_str = res.get("date", "Recent")
    phone = res.get("phone", identifier)
    name = res.get("name", "User")

    if not res.get("found") or not code or code == "N/A":
        raw_msg = res.get("raw_text") or "No login code messages found."
        msg = (
            f"⏳ **কোনো নতুন লগইন কোড পাওয়া যায়নি**\n\n"
            f"📱 **Account:** `{phone}` ({name})\n\n"
            "ℹ️ টেলিগ্রাম (777000) এখনও এই অ্যাকাউন্টে নতুন কোনো ওটিপি পাঠায়নি।\n\n"
            "💡 **করণীয়:**\n"
            "১. আপনার টেলিগ্রাম অ্যাপে ফোন নম্বরটি দিয়ে কোড পাঠান।\n"
            "২. পাঠানো হলে নিচের **🔄 Refresh Code** বাটনে চাপ দিন।\n\n"
            f"📩 *সর্বশেষ বার্তা:* `{raw_msg[:120]}`"
        )
    else:
        msg = (
            f"🎉 **টেলিগ্রাম লগইন ভেরিফিকেশন কোড (OTP):**\n\n"
            f"📱 **Phone:** `{phone}` ({name})\n"
            f"🕒 **Code Time:** `{date_str}`\n\n"
            f"🔑 **আপনার লগইন কোড (Login Code):**\n\n"
            f"👉  `{code}`  👈\n\n"
            f"*(কোডটি কপি করতে উপরের নাম্বারে আলতো চাপ দিন)*\n\n"
            f"💡 *নতুন কোড চাইলে ৩ সেকেন্ড পর নিচের Refresh বাটনে চাপ দিন:*"
        )

    if status_msg:
        await status_msg.edit_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
