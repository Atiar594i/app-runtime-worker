from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import os
import datetime
import asyncio
import config

import database
from session_manager import session_manager
from utils.helpers import (
    get_server_metrics,
    create_system_backup,
    test_proxy_ping,
)
from utils.platform_presets import PLATFORM_PRESETS


# ================= 1. CHANNEL MANAGEMENT =================


def get_channels_keyboard(settings: dict):
    keyboard = [
        [
            InlineKeyboardButton(
                "💳 Set Payment Channel", callback_data="ch_set_payment"
            ),
            InlineKeyboardButton(
                "📊 Set Stats Channel", callback_data="ch_set_stats"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔒 Set Join Lock Channel", callback_data="ch_set_join"
            ),
            InlineKeyboardButton(
                "⚠️ Set Error Channel", callback_data="ch_set_error"
            ),
        ],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_channels_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    settings = await database.get_all_settings()
    payment_ch = settings.get("payment_channel") or "❌ None"
    stats_ch = settings.get("stats_channel") or "❌ None"
    join_ch = settings.get("join_lock_channel") or "❌ None"
    error_ch = settings.get("error_channel") or "❌ None"

    text = (
        "📢 **Channel Management (চ্যানেল সেটিংস)**\n\n"
        f"• **Payment Channel:** `{payment_ch}`\n"
        f"• **Stats Channel:** `{stats_ch}`\n"
        f"• **Join Lock (Force Join):** `{join_ch}`\n"
        f"• **Error Report Channel:** `{error_ch}`\n\n"
        "যেকোনো চ্যানেল পরিবর্তন করতে নিচের বাটন চাপুন (User ID বা @username লিখবেন):"
    )

    if query:
        await query.message.edit_text(
            text,
            reply_markup=get_channels_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_channels_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )


# ================= 2. CONFIGURATION =================


def get_config_keyboard(settings: dict):
    m_st = "🟢 ON" if settings.get("maintenance_mode") == "1" else "⚪ OFF"
    w_st = "🟢 ON" if settings.get("withdraw_enabled", "1") == "1" else "🔴 OFF"
    r_st = "🟢 ON" if settings.get("receive_enabled", "1") == "1" else "🔴 OFF"
    min_wd = settings.get("min_wd", "5.0")
    two_fa = (
        f"Set (`{settings.get('default_2fa')}`)"
        if settings.get("default_2fa")
        else "None"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                f"Maintenance: {m_st}", callback_data="cfg_toggle_maint"
            ),
            InlineKeyboardButton(
                f"Withdraw: {w_st}", callback_data="cfg_toggle_wd"
            ),
        ],
        [
            InlineKeyboardButton(
                f"Receive: {r_st}", callback_data="cfg_toggle_rec"
            ),
            InlineKeyboardButton(
                f"Min WD: ${min_wd}", callback_data="cfg_set_min_wd"
            ),
        ],
        [
            InlineKeyboardButton(
                f"🔐 2FA Pass: {two_fa}", callback_data="cfg_set_2fa"
            ),
            InlineKeyboardButton(
                "👑 Manage Admins", callback_data="cfg_manage_admins"
            ),
        ],
        [
            InlineKeyboardButton(
                "💾 Full System Backup Now", callback_data="cfg_backup_now"
            ),
        ],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_config_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    settings = await database.get_all_settings()
    text = (
        "⚙️ **System Configuration (সিস্টেম কনফিগারেশন)**\n\n"
        "বটের যাবতীয় অটোমেশন, সিকিউরিটি ও রক্ষণাবেক্ষণ সেটিংস পরিবর্তন করুন:"
    )

    if query:
        await query.message.edit_text(
            text,
            reply_markup=get_config_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_config_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )


# ================= 3. USER TOOLS =================


def get_user_tools_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(
                "🌐 Filter Users by Country", callback_data="ut_filter_country"
            ),
            InlineKeyboardButton(
                "📱 Find User by Phone", callback_data="ut_find_phone"
            ),
        ],
        [
            InlineKeyboardButton(
                "🧹 Delete Bad Numbers / Sessions",
                callback_data="ut_clean_bad_ask",
            ),
        ],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_user_tools_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query:
        await query.answer()

    text = (
        "🛠 **User Tools & Data Investigation**\n\n"
        "ব্যবহারকারী অনুসন্ধান ও ডেটা পরিচ্ছন্ন করার টুলসমূহ:"
    )

    if query:
        await query.message.edit_text(
            text,
            reply_markup=get_user_tools_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_user_tools_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


# ================= 4. DAILY SUMMARY =================


async def show_daily_summary(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query:
        await query.answer()

    today = datetime.date.today().isoformat()
    summary = await database.get_daily_summary(today)
    metrics = get_server_metrics()

    text = (
        f"📊 **Daily Server & Bot Summary ({today})**\n\n"
        f"👥 **Users Activity:**\n"
        f"• Total Users: `{summary['total_users']}`\n"
        f"• Today's New Users: `{summary['new_users']}`\n\n"
        f"🎯 **Accounts Performance:**\n"
        f"• Today's Accounts Received: `{summary['accounts_count']}`\n"
        f"• Today's Account Payout: `${summary['total_payout']:.2f}`\n\n"
        f"💳 **Withdrawals Overview:**\n"
        f"• Today's Withdrawals: `{summary['withdrawals_count']}`\n"
        f"• Total Amount Paid: `${summary['withdrawals_amount']:.2f}`\n\n"
        f"🖥 **Server Health Status:**\n"
        f"• CPU Usage: `{metrics['cpu_percent']}%`\n"
        f"• RAM Usage: `{metrics['ram_percent']}%` ({metrics['ram_used_gb']}GB / {metrics['ram_total_gb']}GB)\n"
        f"• Disk Free: `{metrics['disk_free_gb']} GB` ({metrics['disk_percent']}% used)"
    )

    kb = [
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="adm_summary")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")],
    ]

    if query:
        await query.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
        )
    elif update.message:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
        )


# ================= 5. BACKEND & TECHNICAL SETTINGS =================


def get_tech_menu_keyboard(settings: dict):
    active_plat = settings.get("active_platform", "TD-direct")
    proxy_st = "🟢 ON" if settings.get("proxy_enabled") == "1" else "⚪ OFF"

    keyboard = [
        [
            InlineKeyboardButton(
                "⚙️ API Configuration", callback_data="tech_api_cfg"
            ),
            InlineKeyboardButton(
                f"📱 Platform: {active_plat}", callback_data="tech_plat_cfg"
            ),
        ],
        [
            InlineKeyboardButton(
                f"🌐 Proxy Settings ({proxy_st})", callback_data="tech_proxy_cfg"
            ),
        ],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_tech_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    settings = await database.get_all_settings()
    app_id = settings.get("app_id", "2040")
    app_hash = settings.get("app_hash", "b18441a1ff607e10a989891a5462e627")
    platform = settings.get("active_platform", "TD-direct")
    proxy_en = "Enabled 🟢" if settings.get("proxy_enabled") == "1" else "Disabled ⚪"

    text = (
        "🔌 **Backend & Technical Settings (হুবহু ভিডিওর মতো)**\n\n"
        f"• **Telegram App ID:** `{app_id}`\n"
        f"• **Telegram App Hash:** `{app_hash[:8]}...{app_hash[-4:]}`\n"
        f"• **Active Platform:** `{platform}`\n"
        f"• **Proxy Status:** {proxy_en}\n\n"
        "নিচের বাটনগুলো দিয়ে যেকোনো ব্যাকএন্ড সেটিংস পরিবর্তন করুন:"
    )

    if query:
        await query.message.edit_text(
            text,
            reply_markup=get_tech_menu_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_tech_menu_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )


def get_proxy_menu_keyboard(settings: dict):
    en = "🟢 ON" if settings.get("proxy_enabled") == "1" else "⚪ OFF"
    keyboard = [
        [
            InlineKeyboardButton(
                f"Proxy: {en}", callback_data="proxy_toggle"
            ),
            InlineKeyboardButton(
                "✏️ Edit Proxy Info", callback_data="proxy_edit_info"
            ),
        ],
        [
            InlineKeyboardButton(
                "📡 Test Ping", callback_data="proxy_test_ping"
            ),
            InlineKeyboardButton(
                "🌍 Change ISO", callback_data="proxy_change_iso"
            ),
        ],
        [InlineKeyboardButton("🔙 Back to Tech", callback_data="adm_tech")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_proxy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    settings = await database.get_all_settings()
    en = "🟢 ON" if settings.get("proxy_enabled") == "1" else "⚪ OFF"
    p_host = settings.get("proxy_host") or "None"
    p_port = settings.get("proxy_port", "1080")
    p_type = settings.get("proxy_type", "socks5").upper()
    p_user = settings.get("proxy_user") or "None"
    p_iso = settings.get("proxy_iso", "US")

    text = (
        "🌐 **Proxy Settings & Configuration:**\n\n"
        f"• **Status:** {en}\n"
        f"• **Type:** `{p_type}`\n"
        f"• **Host:** `{p_host}`\n"
        f"• **Port:** `{p_port}`\n"
        f"• **Username:** `{p_user}`\n"
        f"• **ISO Routing:** `{p_iso}`\n\n"
        "প্রক্সি অন বা অফ করতে 'Proxy' বাটনে চাপুন। প্রক্সি চালু করার পূর্বে 'Edit Proxy Info' দিয়ে আপনার প্রক্সি আইপি ও পোর্ট সেট করে নিন:"
    )

    if query:
        try:
            await query.message.edit_text(
                text,
                reply_markup=get_proxy_menu_keyboard(settings),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_proxy_menu_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )


def get_termination_countdown(
    created_at_val,
    term_completed: int = 0,
    device_count: int = 1,
    status: str = "confirmed",
) -> dict:
    """
    Computes exact live hours, minutes, and seconds remaining for 24-hour auto-termination.
    """
    if status == "revoked":
        return {
            "is_clean": False,
            "is_revoked": True,
            "is_ready": False,
            "remaining_seconds": 0,
            "text_btn": "❌ লগআউট",
            "text_dash": "❌ ইউজার টেলিগ্রাম থেকে বটের সেশন লগআউট করেছে",
        }

    if device_count <= 1 or term_completed == 1:
        return {
            "is_clean": True,
            "is_revoked": False,
            "is_ready": False,
            "remaining_seconds": 0,
            "text_btn": "🟢 1 Dev (সুরক্ষিত)",
            "text_dash": "✅ সুরক্ষিত (১টি ডিভাইস / একক সেশন)",
        }

    try:
        if isinstance(created_at_val, str):
            clean_str = created_at_val.replace("T", " ").split(".")[0]
            dt = datetime.datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        elif isinstance(created_at_val, datetime.datetime):
            dt = created_at_val
        else:
            dt = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        target = dt + datetime.timedelta(hours=24)
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        diff = target - now_utc
        remaining_seconds = int(diff.total_seconds())

        if remaining_seconds > 0:
            h = remaining_seconds // 3600
            m = (remaining_seconds % 3600) // 60
            s = remaining_seconds % 60
            return {
                "is_clean": False,
                "is_ready": False,
                "remaining_seconds": remaining_seconds,
                "text_btn": f"⏳ {h}h {m}m {s}s",
                "text_dash": f"⏳ {h} ঘণ্টা {m} মিনিট {s} সেকেন্ড বাকি",
            }
        else:
            return {
                "is_clean": False,
                "is_ready": True,
                "remaining_seconds": 0,
                "text_btn": "⚡ টার্মিনেট প্রস্তুত",
                "text_dash": "⚡ ২৪ ঘণ্টা অতিক্রান্ত (টার্মিনেশনের জন্য প্রস্তুত)",
            }
    except Exception:
        return {
            "is_clean": False,
            "is_ready": False,
            "remaining_seconds": 0,
            "text_btn": "⏳ ২৪ ঘণ্টা টাইমার",
            "text_dash": "⏳ ২৪ ঘণ্টা টাইমার সক্রিয়",
        }


async def show_device_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0
):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    accounts = await database.get_all_accounts()
    auto_term = await database.get_setting("auto_termination", "1")
    term_status_text = "চালু (ON) ✅" if auto_term == "1" else "বন্ধ (OFF) ❌"
    term_btn_text = f"🛑 টার্মিনেশন: {'চালু ✅' if auto_term == '1' else 'বন্ধ ❌'}"

    if not accounts:
        kb = [
            [InlineKeyboardButton(term_btn_text, callback_data="dev_toggle_auto_term")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")],
        ]
        msg = (
            "📱 **ডিভাইস ও টার্মিনেশন লাইভ কন্ট্রোল প্যানেল:**\n\n"
            f"🛑 **টার্মিনেশন অপশন:** `{term_status_text}`\n"
            "ℹ️ *নতুন অ্যাকাউন্ট আসার পর একাধিক ডিভাইস থাকলে বট স্বয়ংক্রিয়ভাবে টার্মিনেশন সম্পন্ন করবে।*\n\n"
            "ℹ️ **বর্তমানে বটে কোনো নম্বর বা সেশন জমা নেই।**\n\n"
            "ইউজাররা নম্বর যোগ করার সাথে সাথে এখানে সমস্ত নম্বরের তালিকা চলে আসবে।"
        )
        if query:
            await query.message.edit_text(
                msg,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN,
            )
        elif update.message:
            await update.message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    page_size = 5
    total_pages = max(1, (len(accounts) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    page_accounts = accounts[start_idx : start_idx + page_size]

    buttons = [
        [InlineKeyboardButton(term_btn_text, callback_data="dev_toggle_auto_term")]
    ]

    list_report_lines = []
    for idx, acc in enumerate(page_accounts, start=start_idx + 1):
        cat_tag = acc.get("category", "Free")
        dev_count = acc.get("device_count") or 1
        term_completed = acc.get("term_completed") or 0
        acc_status = acc.get("status", "confirmed")
        countdown = get_termination_countdown(
            acc["created_at"], term_completed, dev_count, acc_status
        )

        # Button display
        if countdown.get("is_revoked"):
            btn_tag = "❌ Revoked (লগআউট)"
        elif countdown["is_clean"]:
            btn_tag = "🟢 1 Dev"
        else:
            btn_tag = f"⚠️ {dev_count} Dev | {countdown['text_btn']}"

        btn_text = f"📱 {acc['phone']} [{btn_tag}]"
        buttons.append(
            [
                InlineKeyboardButton(
                    btn_text, callback_data=f"dev_check_{acc['id']}"
                )
            ]
        )

        # Dashboard list display with live count
        if countdown.get("is_revoked"):
            status_line = (
                "   • ⚠️ স্ট্যাটাস: `❌ ইউজার টেলিগ্রাম থেকে বটের সেশন লগআউট করেছে`"
            )
        elif countdown["is_clean"]:
            status_line = "   • 🛡️ ডিভাইস: `১ টি` 🟢 (সুরক্ষিত / একক সেশন)"
        else:
            status_line = (
                f"   • 📱 ডিভাইস: `{dev_count} টি` ⚠️ (অতিরিক্ত ডিভাইস রয়েছে)\n"
                f"   • ⏳ অটো-টার্মিনেশন কাউন্টডাউন: `{countdown['text_dash']}`"
            )

        list_report_lines.append(
            f"**{idx}.** `{acc['phone']}` ({cat_tag})\n{status_line}"
        )

    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                "⬅️ Prev", callback_data=f"dev_inspect_list_{page-1}"
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            "🔄 লাইভ রিফ্রেশ (Live Timer)", callback_data=f"dev_inspect_list_{page}"
        )
    )
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                "Next ➡️", callback_data=f"dev_inspect_list_{page+1}"
            )
        )
    buttons.append(nav_row)

    buttons.append(
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")]
    )

    accounts_str = "\n\n".join(list_report_lines)

    text = (
        f"📱 **ডিভাইস ও অটো-টার্মিনেশন লাইভ ড্যাশবোর্ড (মোট: {len(accounts)} টি):**\n\n"
        f"🛑 **টার্মিনেশন অপশন:** `{term_status_text}`\n"
        "ℹ️ *নতুন অ্যাকাউন্ট পাওয়ার ৫ সেকেন্ড পর অতিরিক্ত ডিভাইস চেক হয়। একাধিক ডিভাইস থাকলে ২৪ ঘণ্টার লাইভ কাউন্টডাউন শুরু হয় এবং সময় শেষ হওয়া মাত্রই বট বাকি সব ডিভাইস টার্মিনেট করে দিবে।*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 **লাইভ ডিভাইস কাউন্ট ও কাউন্টডাউন তালিকা:**\n\n"
        f"{accounts_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *'🔄 লাইভ রিফ্রেশ' বাটনে চাপ দিলে সেকেন্ড ও মিনিট লাইভ কাউন্ট হবে। যেকোনো নম্বরে ক্লিক করে বিস্তারিত ডিভাইস দেখতে পারেন:*"
    )

    if query:
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )


async def show_inspect_accounts_page(
    update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0
):
    await show_device_menu(update, context, page=page)


async def show_account_devices_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE, account_id: int
):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    accounts = await database.get_all_accounts()
    target_acc = next((a for a in accounts if a["id"] == account_id), None)
    if not target_acc:
        if query:
            await query.message.reply_text(
                "❌ Account record not found in database."
            )
        return

    phone = target_acc["phone"]
    session_path = target_acc["session_path"]

    if query:
        try:
            await query.message.edit_text(
                f"⏳ `{phone}`-এর সেশনে কানেক্ট করে ডিভাইসের তালিকা রিট্রিভ করা হচ্ছে, অনুগ্রহ করে অপেক্ষা করুন...\n(Connecting to MTProto & checking authorizations...)",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass

    # Call session_manager to get active devices
    res = await session_manager.get_session_authorizations(session_path)

    kb = [
        [
            InlineKeyboardButton(
                "🔄 Refresh Devices", callback_data=f"dev_check_{account_id}"
            ),
            InlineKeyboardButton(
                "🚪 Log Out", callback_data=f"dev_logout_ask_{account_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🛑 টার্মিনেশন (Terminate Devices)",
                callback_data=f"dev_term_others_{account_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 Back to Accounts List", callback_data="dev_inspect_list_0"
            )
        ],
    ]

    if not res.get("success"):
        err_msg = (
            f"⚠️ **লগইন থাকা ডিভাইস দেখতে সমস্যা হয়েছে:**\n\n"
            f"• **Phone:** `{phone}`\n"
            f"• **Error:** `{res.get('error', 'Unknown error')}`\n\n"
            f"সম্ভবত এই অ্যাকাউন্টটি টেলিগ্রাম থেকে লগআউট বা ডিঅ্যাক্টিভেট করা হয়েছে।"
        )
        if query:
            await query.message.edit_text(
                err_msg,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    devices = res.get("devices", [])
    total_devices = res.get("total", len(devices))

    # Update database with fresh device count
    await database.update_account_device_info(account_id, total_devices)

    term_completed = target_acc.get("term_completed", 0)
    countdown = get_termination_countdown(target_acc["created_at"], term_completed, total_devices)

    if countdown["is_clean"]:
        term_status_tag = "✅ সুরক্ষিত (শুধুমাত্র এই বটের সেশন যুক্ত আছে, অন্য কোনো ডিভাইস নেই)"
    else:
        term_status_tag = (
            f"⚠️ আরও {total_devices - 1} টি অতিরিক্ত ডিভাইস যুক্ত আছে!\n"
            f"• **অটো-টার্মিনেশন কাউন্টডাউন:** `{countdown['text_dash']}`\n"
            "💡 নিচের **'🛑 টার্মিনেশন'** বাটনে চাপ দিয়ে অন্যান্য ডিভাইসগুলো এখনই লগআউট করার ট্রাই করতে পারেন।"
        )

    kb = [
        [
            InlineKeyboardButton(
                "🔄 লাইভ রিফ্রেশ (Live Timer)", callback_data=f"dev_check_{account_id}"
            ),
            InlineKeyboardButton(
                "🚪 Log Out", callback_data=f"dev_logout_ask_{account_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🛑 টার্মিনেশন (Terminate Devices)",
                callback_data=f"dev_term_others_{account_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 Back to Accounts List", callback_data="dev_inspect_list_0"
            )
        ],
    ]

    report = (
        f"📱 **Active Logged-in Devices for `{phone}`**\n\n"
        f"• **Owner User ID:** `{target_acc['user_id']}`"
        f" (@{target_acc.get('username') or 'N/A'})\n"
        f"• **Category:** `{target_acc['category']}` | Status:"
        f" `{target_acc.get('status', 'confirmed')}`\n"
        f"• **মোট লগইন থাকা ডিভাইস:** `{total_devices}` টি\n"
        f"• **টার্মিনেশন স্ট্যাটাস:** {term_status_tag}\n\n"
        f"📋 **ডিভাইসের বিস্তারিত তালিকা:**\n"
        f"{'='*30}\n\n"
    )

    for idx, d in enumerate(devices, 1):
        is_curr = (
            "🟢 [THIS BOT SESSION]"
            if d.get("current")
            else "⚪ [CONNECTED DEVICE]"
        )
        country_str = f" ({d['country']})" if d.get("country") else ""
        report += (
            f"**{idx}. {is_curr}**\n"
            f"• **Device:** `{d.get('device_model', 'Unknown')}`\n"
            f"• **Platform:**"
            f" `{d.get('platform', '')} {d.get('system_version', '')}`\n"
            f"• **App:**"
            f" `{d.get('app_name', 'Telegram')} {d.get('app_version', '')}`\n"
            f"• **IP Address:** `{d.get('ip', 'N/A')}`{country_str}\n"
            f"• **First Login:** `{d.get('date_created', 'N/A')}`\n"
            f"• **Last Active:** `{d.get('date_active', 'N/A')}`\n\n"
        )

    if query:
        await query.message.edit_text(
            report,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            report,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN,
        )


def get_device_spoofing_keyboard(settings: dict):
    active_plat = settings.get("active_platform", "TD-direct")
    keyboard = [
        [
            InlineKeyboardButton(
                "💻 TD-direct (Desktop)", callback_data="set_plat_TD-direct"
            ),
            InlineKeyboardButton(
                "📱 Android (Samsung S24)", callback_data="set_plat_Android"
            ),
        ],
        [
            InlineKeyboardButton(
                "🤖 Bot Android (Pixel 8)", callback_data="set_plat_Bot Android"
            ),
        ],
        [
            InlineKeyboardButton(
                "✏️ Custom Device Model", callback_data="dev_edit_model"
            ),
            InlineKeyboardButton(
                "✏️ Custom OS Version", callback_data="dev_edit_os"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Reset to Preset Defaults",
                callback_data="dev_reset_defaults",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 Back to Device Menu", callback_data="adm_device"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_device_spoofing_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    settings = await database.get_all_settings()
    active_plat = settings.get("active_platform", "TD-direct")
    preset = PLATFORM_PRESETS.get(active_plat, PLATFORM_PRESETS["TD-direct"])

    custom_model = settings.get("custom_device_model", "")
    custom_os = settings.get("custom_system_version", "")

    current_model = (
        custom_model if custom_model else preset.get("device_model", "Desktop")
    )
    current_os = (
        custom_os
        if custom_os
        else preset.get("system_version", "Windows 11 x64")
    )
    current_app_ver = settings.get(
        "app_version", preset.get("app_version", "10.14.5")
    )
    current_lang = settings.get("system_lang_code", "en")

    mode_label = (
        "Custom Modified ⚙️"
        if custom_model
        else f"Preset Default ({active_plat}) ✅"
    )

    text = (
        "⚙️ **Bot Device Spoofing Settings (বটের ডিভাইস প্রোফাইল)**\n\n"
        f"• **Active Preset:** `{active_plat}`\n"
        f"• **Current Mode:** `{mode_label}`\n"
        f"• **Device Model:** `{current_model}`\n"
        f"• **System / OS Version:** `{current_os}`\n"
        f"• **App Version:** `{current_app_ver}`\n"
        f"• **System Language:** `{current_lang}`\n\n"
        "বট অ্যাকাউন্ট কানেক্ট করার সময় টেলিগ্রামকে কোন ডিভাইস ইনফো পাঠাবে তা এখান থেকে নিয়ন্ত্রণ করতে পারেন:"
    )

    if query:
        try:
            await query.message.edit_text(
                text,
                reply_markup=get_device_spoofing_keyboard(settings),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_device_spoofing_keyboard(settings),
            parse_mode=ParseMode.MARKDOWN,
        )


# ================= CALLBACK ROUTER FOR TECH & SETTINGS =================


async def handle_tech_callbacks(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    query = update.callback_query
    data = query.data

    # Menus navigation
    if data == "adm_channels":
        await show_channels_menu(update, context)
        return True
    if data == "adm_config":
        await show_config_menu(update, context)
        return True
    if data == "adm_tools":
        await show_user_tools_menu(update, context)
        return True
    if data == "adm_summary":
        await show_daily_summary(update, context)
        return True
    if data == "adm_tech":
        await show_tech_menu(update, context)
        return True
    if data == "adm_device":
        await show_device_menu(update, context)
        return True

    # --- Channels Setup ---
    if data == "ch_set_payment":
        context.user_data["adm_state"] = "set_chan_payment"
        await query.message.reply_text(
            "💳 **Payment Channel সেট করুন:**\n\n"
            "চ্যানেলের @username অথবা ID লিখে পাঠান (Send @channel or ID, e.g. `@my_payment_chan`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True
    if data == "ch_set_stats":
        context.user_data["adm_state"] = "set_chan_stats"
        await query.message.reply_text(
            "📊 **Stats Channel সেট করুন:**\n\n"
            "চ্যানেলের @username অথবা ID লিখে পাঠান:",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True
    if data == "ch_set_join":
        context.user_data["adm_state"] = "set_chan_join"
        await query.message.reply_text(
            "🔒 **Join Lock (Force Join) Channel সেট করুন:**\n\n"
            "চ্যানেলের @username অথবা ID পাঠান (মুছে ফেলতে `none` লিখুন):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True
    if data == "ch_set_error":
        context.user_data["adm_state"] = "set_chan_error"
        await query.message.reply_text(
            "⚠️ **Error Channel সেট করুন:**\n\n"
            "চ্যানেলের @username অথবা ID পাঠান:",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    # --- Config Toggles ---
    if data == "cfg_toggle_maint":
        current = await database.get_setting("maintenance_mode", "0")
        new_val = "0" if current == "1" else "1"
        await database.set_setting("maintenance_mode", new_val)
        await show_config_menu(update, context)
        return True
    if data == "cfg_toggle_wd":
        current = await database.get_setting("withdraw_enabled", "1")
        new_val = "0" if current == "1" else "1"
        await database.set_setting("withdraw_enabled", new_val)
        await show_config_menu(update, context)
        return True
    if data == "cfg_toggle_rec":
        current = await database.get_setting("receive_enabled", "1")
        new_val = "0" if current == "1" else "1"
        await database.set_setting("receive_enabled", new_val)
        await show_config_menu(update, context)
        return True
    if data == "cfg_set_min_wd":
        context.user_data["adm_state"] = "set_min_wd"
        await query.message.reply_text(
            "💵 **Minimum Withdrawal Amount:**\n\n"
            "ন্যূনতম উইথড্র পরিমাণ লিখুন (e.g. `5.0` or `10.0`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True
    if data == "cfg_set_2fa":
        context.user_data["adm_state"] = "set_default_2fa"
        await query.message.reply_text(
            "🔐 **Default 2FA Password:**\n\n"
            "রিসিভ করা অ্যাকাউন্টে যে 2FA পাসওয়ার্ড সেট করতে চান তা লিখুন (মুছে ফেলতে `none` লিখুন):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True
    if data == "cfg_manage_admins":
        admins = await database.get_all_admins()
        context.user_data["adm_state"] = "waiting_admin_id"
        kb = [
            [
                InlineKeyboardButton(
                    "➕ Add Admin ID", callback_data="cfg_add_admin_prompt"
                ),
                InlineKeyboardButton(
                    "➖ Remove Admin ID", callback_data="cfg_rem_admin_prompt"
                ),
            ],
            [InlineKeyboardButton("🔙 Back to Config", callback_data="adm_config")],
        ]
        text = (
            "👑 **Admin List:**\n"
            + "\n".join(f"• `{aid}`" for aid in admins)
            + "\n\nনতুন অ্যাডমিন যোগ অথবা রিমুভ করতে বাটন চাপুন:"
        )
        await query.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
        )
        return True
    if data == "cfg_add_admin_prompt":
        context.user_data["adm_state"] = "adm_add_admin_id"
        await query.message.reply_text(
            "👑 নতুন অ্যাডমিনের User ID পাঠান (Send User ID):"
        )
        return True
    if data == "cfg_rem_admin_prompt":
        context.user_data["adm_state"] = "adm_rem_admin_id"
        await query.message.reply_text(
            "👑 যে অ্যাডমিনকে রিমুভ করতে চান তার User ID পাঠান:"
        )
        return True
    if data == "cfg_backup_now":
        await query.answer("Creating backup ZIP...")
        zip_path = create_system_backup()
        with open(zip_path, "rb") as doc:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=doc,
                caption="💾 **Full System Database & Sessions Backup Archive**",
                parse_mode=ParseMode.MARKDOWN,
            )
        try:
            os.remove(zip_path)
        except Exception:
            pass
        return True

    # --- User Tools ---
    if data == "ut_filter_country":
        summary = await database.get_accounts_by_country_summary()
        text = "🌐 **দেশ অনুযায়ী ইউজার ও অ্যাকাউন্ট পরিসংখ্যান:**\n\n"
        if not summary:
            text += "কোনো অ্যাকাউন্ট হিস্ট্রি পাওয়া যায়নি।"
        else:
            for s in summary:
                text += (
                    f"• **{s['country_name']}** ({s['dial_code']}): "
                    f"`{s['accounts_count']}` accounts from `{s['users_count']}` users\n"
                )
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return True

    if data == "ut_find_phone":
        context.user_data["adm_state"] = "ut_waiting_phone"
        await query.message.reply_text(
            "📱 **ফোন নম্বর দিয়ে ইউজার বের করুন:**\n\n"
            "নম্বরটি কান্ট্রি কোডসহ পাঠান (Send phone number, e.g. `+8801700000000`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "ut_clean_bad_ask":
        count = await database.delete_bad_numbers()
        await query.answer(f"Cleaned {count} orphan sessions")
        await query.message.reply_text(
            f"🧹 **Cleaned `{count}` broken/missing session records from database.**",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    # --- API Configuration ---
    if data == "tech_api_cfg":
        settings = await database.get_all_settings()
        kb = [
            [
                InlineKeyboardButton(
                    "✏️ Edit App ID", callback_data="api_edit_id"
                ),
                InlineKeyboardButton(
                    "✏️ Edit App Hash", callback_data="api_edit_hash"
                ),
            ],
            [
                InlineKeyboardButton(
                    "✏️ Edit Lang Code", callback_data="api_edit_lang"
                ),
                InlineKeyboardButton(
                    "✏️ Edit App Version", callback_data="api_edit_ver"
                ),
            ],
            [InlineKeyboardButton("🔙 Back to Tech", callback_data="adm_tech")],
        ]
        text = (
            "⚙️ **API Configuration Details:**\n\n"
            f"• **App ID:** `{settings.get('app_id', '2040')}`\n"
            f"• **App Hash:** `{settings.get('app_hash', 'b18441a1ff607e10a989891a5462e627')}`\n"
            f"• **System Lang Code:** `{settings.get('system_lang_code', 'en')}`\n"
            f"• **App Version:** `{settings.get('app_version', '10.14.5')}`\n\n"
            "যেকোনো মান পরিবর্তন করতে বাটন চাপুন:"
        )
        await query.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN
        )
        return True

    if data == "api_edit_id":
        context.user_data["adm_state"] = "set_app_id"
        await query.message.reply_text("Enter new Telegram App ID (Integer):")
        return True
    if data == "api_edit_hash":
        context.user_data["adm_state"] = "set_app_hash"
        await query.message.reply_text("Enter new Telegram App Hash (Hex string):")
        return True
    if data == "api_edit_lang":
        context.user_data["adm_state"] = "set_lang_code"
        await query.message.reply_text("Enter System Lang Code (e.g. `en`, `ru`):")
        return True
    if data == "api_edit_ver":
        context.user_data["adm_state"] = "set_app_version"
        await query.message.reply_text("Enter App Version (e.g. `10.14.5`):")
        return True

    # --- Platform Selection ---
    if data == "tech_plat_cfg":
        current_plat = await database.get_setting("active_platform", "TD-direct")
        buttons = []
        for p_key, p_val in PLATFORM_PRESETS.items():
            check = "🔘 " if p_key == current_plat else "⚪ "
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"{check}{p_key} ({p_val['device_model']})",
                        callback_data=f"set_plat_{p_key}",
                    )
                ]
            )
        buttons.append([InlineKeyboardButton("🔙 Back to Tech", callback_data="adm_tech")])
        await query.message.edit_text(
            "📱 **Platform Selection (প্ল্যাটফর্ম সিলেক্ট করুন):**\n\n"
            "বট কোন ডিভাইস মডেল স্পুফ করে অ্যাকাউন্ট লগইন করবে তা বেছে নিন:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "dev_toggle_auto_term":
        curr = await database.get_setting("auto_termination", "1")
        new_val = "0" if curr == "1" else "1"
        await database.set_setting("auto_termination", new_val)
        status_word = "চালু (ON) ✅" if new_val == "1" else "বন্ধ (OFF) ❌"
        await query.answer(f"টার্মিনেশন অপশন {status_word} করা হয়েছে!")
        await show_device_menu(update, context)
        return True

    if data.startswith("dev_inspect_list_"):
        page_str = data.replace("dev_inspect_list_", "")
        page = int(page_str) if page_str.isdigit() else 0
        await show_inspect_accounts_page(update, context, page)
        return True

    if data.startswith("dev_check_"):
        acc_id_str = data.replace("dev_check_", "")
        if acc_id_str.isdigit():
            await show_account_devices_report(update, context, int(acc_id_str))
        return True

    if data == "dev_search_phone":
        context.user_data["adm_state"] = "dev_waiting_search_phone"
        await query.message.reply_text(
            "📱 **ডিভাইস চেক করতে ফোন নম্বর পাঠান:**\n\n"
            "যে অ্যাকাউন্টের অ্যাক্টিভ ডিভাইস দেখতে চান তার নম্বর কান্ট্রি কোডসহ পাঠান (যেমন: `+8801700000000`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "dev_spoofing_menu":
        await show_device_spoofing_menu(update, context)
        return True

    if data == "dev_page_noop":
        await query.answer()
        return True

    if data.startswith("dev_logout_ask_"):
        acc_id_str = data.replace("dev_logout_ask_", "")
        if acc_id_str.isdigit():
            acc_id = int(acc_id_str)
            accounts = await database.get_all_accounts()
            target_acc = next((a for a in accounts if a["id"] == acc_id), None)
            phone = target_acc["phone"] if target_acc else f"ID: {acc_id}"

            kb = [
                [
                    InlineKeyboardButton(
                        "⚠️ হ্যাঁ, লগআউট করুন (Log Out)",
                        callback_data=f"dev_logout_confirm_{acc_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ না, বাতিল করুন (Cancel)",
                        callback_data=f"dev_check_{acc_id}",
                    )
                ],
            ]
            confirm_text = (
                f"🚪 **সেশন লগআউট নিশ্চিতকরণ (Logout Confirmation):**\n\n"
                f"আপনি কি নিশ্চিত যে `{phone}` নম্বরটির সেশন টেলিগ্রাম থেকে"
                " **Log Out** এবং বট ডাটাবেজ থেকে মুছে ফেলতে চান?\n\n"
                f"• এটি টেলিগ্রাম সার্ভারে `log_out()` রিকোয়েস্ট পাঠাবে যাতে এই"
                " সেশনটি আর সচল না থাকে এবং লোকাল সেশন ফাইল মুছে যাবে।"
            )
            await query.message.edit_text(
                confirm_text,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN,
            )
        return True

    if data.startswith("dev_logout_confirm_"):
        acc_id_str = data.replace("dev_logout_confirm_", "")
        if acc_id_str.isdigit():
            acc_id = int(acc_id_str)
            accounts = await database.get_all_accounts()
            target_acc = next((a for a in accounts if a["id"] == acc_id), None)

            if target_acc:
                phone = target_acc["phone"]
                session_path = target_acc["session_path"]
                await query.answer("Logging out from Telegram...")

                # Call logout
                await session_manager.logout_session(session_path)
                await database.delete_account(acc_id)

                kb = [
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Accounts List",
                            callback_data="dev_inspect_list_0",
                        )
                    ]
                ]
                await query.message.edit_text(
                    f"✅ **সেশন সফলভাবে লগআউট সম্পন্ন হয়েছে!**\n\n"
                    f"• Phone: `{phone}`\n"
                    f"• Status: Logged out from Telegram & removed from bot.",
                    reply_markup=InlineKeyboardMarkup(kb),
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await query.message.reply_text(
                    "❌ Account not found in database."
                )
        return True

    if data.startswith("dev_term_others_"):
        acc_id_str = data.replace("dev_term_others_", "")
        if acc_id_str.isdigit():
            acc_id = int(acc_id_str)
            accounts = await database.get_all_accounts()
            target_acc = next((a for a in accounts if a["id"] == acc_id), None)

            if target_acc:
                phone = target_acc["phone"]
                session_path = target_acc["session_path"]

                await query.answer("Attempting to terminate other sessions...")
                res = await session_manager.terminate_other_sessions(
                    session_path
                )

                kb = [
                    [
                        InlineKeyboardButton(
                            "🔄 Refresh Device List",
                            callback_data=f"dev_check_{acc_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔙 Back to Accounts",
                            callback_data="dev_inspect_list_0",
                        )
                    ],
                ]

                if res.get("success"):
                    await database.update_account_device_info(
                        acc_id, device_count=1, term_completed=1
                    )
                    await query.message.edit_text(
                        f"✅ **টার্মিনেশন সফল হয়েছে!**\n\n"
                        f"`{phone}` অ্যাকাউন্টের অন্যান্য সকল কানেক্টেড"
                        " ডিভাইস টেলিগ্রাম থেকে সফলভাবে লগআউট (Terminate) করা হয়েছে।",
                        reply_markup=InlineKeyboardMarkup(kb),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                elif res.get("fresh_wait"):
                    await query.message.edit_text(
                        f"⏳ **টেলিগ্রাম টার্মিনেশন সিকিউরিটি রুল:**\n\n"
                        "টেলিগ্রামের অফিসিয়াল নিয়মানুযায়ী, নতুন লগইন করা কোনো"
                        " সেশন থেকে অন্যান্য পুরোনো ডিভাইসগুলো লগআউট করার জন্য"
                        " সেশনটি কমপক্ষে **২৪ ঘণ্টা পুরোনো** হতে হয়"
                        " (`FRESH_RESET_AUTHORISATION_FORBIDDEN`)।\n\n"
                        "💡 **অটো শিডিউল তথ্য:** টার্মিনেশন অপশন চালু থাকলে ২৪ ঘণ্টা অতিক্রান্ত হওয়ার পর বট স্বয়ংক্রিয়ভাবে বাকি সকল ডিভাইস টার্মিনেট সম্পন্ন করে আপনাকে অ্যালার্ট পাঠাবে।",
                        reply_markup=InlineKeyboardMarkup(kb),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                else:
                    await query.message.edit_text(
                        f"❌ **টার্মিনেশন ত্রুটি:** {res.get('error', 'Failed to terminate other sessions')}",
                        reply_markup=InlineKeyboardMarkup(kb),
                        parse_mode=ParseMode.MARKDOWN,
                    )
            else:
                await query.message.reply_text(
                    "❌ Account not found in database."
                )
        return True

    if data.startswith("set_plat_"):
        chosen = data.replace("set_plat_", "")
        await database.set_setting("active_platform", chosen)
        await database.set_setting("custom_device_model", "")
        await database.set_setting("custom_system_version", "")
        await query.answer(f"Platform set to {chosen}")
        await show_device_spoofing_menu(update, context)
        return True

    if data == "dev_edit_model":
        context.user_data["adm_state"] = "set_device_model"
        await query.message.reply_text(
            "📱 **নতুন Device Model লিখে পাঠান:**\n\n"
            "👉 উদাহরণ: `Samsung Galaxy S24 Ultra` অথবা `iPhone 15 Pro Max` অথবা `Xiaomi 14 Ultra`\n"
            "ডিফল্টে ফিরিয়ে নিতে `default` লিখুন।",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "dev_edit_os":
        context.user_data["adm_state"] = "set_device_os"
        await query.message.reply_text(
            "💻 **নতুন OS / System Version লিখে পাঠান:**\n\n"
            "👉 উদাহরণ: `Android 14 (API 34)` অথবা `iOS 17.5` অথবা `Windows 11 x64`\n"
            "ডিফল্টে ফিরিয়ে নিতে `default` লিখুন।",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "dev_reset_defaults":
        await database.set_setting("custom_device_model", "")
        await database.set_setting("custom_system_version", "")
        await query.answer("Device reset to preset defaults! 🔄")
        await show_device_spoofing_menu(update, context)
        return True

    # --- Proxy Settings ---
    if data == "tech_proxy_cfg":
        await show_proxy_menu(update, context)
        return True

    if data == "proxy_toggle":
        current = await database.get_setting("proxy_enabled", "0")
        new_val = "0" if current == "1" else "1"
        await database.set_setting("proxy_enabled", new_val)
        settings = await database.get_all_settings()

        status_msg = (
            "Proxy চালু করা হয়েছে (Enabled 🟢)"
            if new_val == "1"
            else "Proxy বন্ধ করা হয়েছে (Disabled ⚪)"
        )
        if new_val == "1" and not settings.get("proxy_host"):
            status_msg += "\n⚠️ সতর্কবার্তা: প্রক্সি Host/Port সেট করা নেই!"
            await query.answer(status_msg, show_alert=True)
        else:
            await query.answer(status_msg)

        await show_proxy_menu(update, context)
        return True

    if data == "proxy_edit_info":
        context.user_data["adm_state"] = "set_proxy_info"
        await query.message.reply_text(
            "✏️ **প্রক্সি ইনফো পাঠান:**\n\n"
            "👉 Format: `type:ip:port:user:pass` অথবা `ip:port`\n"
            "উদাহরণ: `socks5:127.0.0.1:1080` অথবা `http:1.2.3.4:8080:myuser:mypass`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "proxy_test_ping":
        await query.answer("Pinging Telegram DC via proxy...")
        settings = await database.get_all_settings()
        res = test_proxy_ping(
            proxy_type=settings.get("proxy_type", "socks5"),
            host=settings.get("proxy_host", ""),
            port=int(settings.get("proxy_port", "1080") or 1080),
            username=settings.get("proxy_user", ""),
            password=settings.get("proxy_pass", ""),
        )
        if res.get("success"):
            await query.message.reply_text(
                f"📡 **Proxy Ping Successful! ✅**\n\n"
                f"• **Target:** `{res['target']}`\n"
                f"• **Latency:** `{res['latency_ms']} ms`\n"
                f"• **Connection:** Established",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await query.message.reply_text(
                f"📡 **Proxy Ping Failed! ❌**\n\n"
                f"• **Error:** `{res.get('error')}`",
                parse_mode=ParseMode.MARKDOWN,
            )
        return True

    if data == "proxy_change_iso":
        context.user_data["adm_state"] = "set_proxy_iso"
        await query.message.reply_text(
            "🌍 **Change Proxy ISO:**\n\n"
            "Enter 2-letter ISO country code (e.g. `US`, `BD`, `GB`, `DE`):"
        )
        return True

    return False


# ================= 6. AUTO-TERMINATION WORKERS =================


async def trigger_auto_termination(phone: str, session_path: str, bot=None):
    """
    Called after an account is successfully confirmed.
    If auto_termination setting is enabled ('1'):
      1. Waits 5 seconds
      2. Checks connected devices
      3. If > 1 devices, attempts to terminate other sessions immediately
      4. If fresh_wait (Telegram 24h rule), schedules 24h background termination worker
    """
    try:
        auto_term = await database.get_setting("auto_termination", "1")
        if auto_term != "1":
            print(f"[*] Auto-termination is OFF. Skipping check for {phone}.")
            return

        print(f"[*] Auto-termination: waiting 5 seconds before checking devices for {phone}...")
        await asyncio.sleep(5)

        # 1. Query authorizations
        res = await session_manager.get_session_authorizations(session_path)
        if not res.get("success"):
            print(f"[!] Auto-termination failed to get devices for {phone}: {res.get('error')}")
            return

        devices = res.get("devices", [])
        total = res.get("total", len(devices))
        print(f"[*] Auto-termination check for {phone}: {total} active devices detected.")

        acc_db = await database.get_account_by_phone(phone)
        if acc_db:
            await database.update_account_device_info(acc_db["id"], total)

        if total <= 1:
            print(f"[*] Auto-termination: {phone} has only 1 session (Bot session). Account is clean and secure.")
            return

        # More than 1 device exists! Try to terminate immediately
        print(f"[!] Auto-termination: {phone} has {total} devices. Attempting to terminate other sessions...")
        term_res = await session_manager.terminate_other_sessions(session_path)

        admins = await database.get_all_admins()
        admin_targets = set(admins + [a for a in config.ADMIN_IDS if a > 0])

        if term_res.get("success"):
            print(f"[+] Auto-termination: Successfully terminated other sessions for {phone} immediately!")
            if acc_db:
                await database.update_account_device_info(
                    acc_db["id"], device_count=1, term_completed=1
                )
            if bot:
                for aid in admin_targets:
                    try:
                        await bot.send_message(
                            chat_id=aid,
                            text=(
                                f"🛑 **[অটো টার্মিনেশন সম্পন্ন]**\n\n"
                                f"📱 **নম্বর:** `{phone}`\n"
                                f"✅ অ্যাকাউন্টের অন্যান্য অতিরিক্ত ডিভাইসগুলো সাথে সাথেই সফলভাবে টার্মিনেট (লগআউট) করা হয়েছে!\n"
                                f"অ্যাকাউন্টটি এখন সম্পূর্ণ সুরক্ষিত।"
                            ),
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except Exception as e:
                        print(f"[Admin Notify Error] {e}")
        elif term_res.get("fresh_wait"):
            print(f"[*] Auto-termination: Telegram 24h policy applied for {phone}. Scheduling 24h background worker...")
            if bot:
                for aid in admin_targets:
                    try:
                        await bot.send_message(
                            chat_id=aid,
                            text=(
                                f"⏳ **[অটো টার্মিনেশন শিডিউল নোটিশ]**\n\n"
                                f"📱 **নম্বর:** `{phone}`\n"
                                f"⚠️ **তথ্য:** অ্যাকাউন্টে একাধিক (`{total}`) ডিভাইস কানেক্টেড রয়েছে। টেলিগ্রামের সিকিউরিটি রুল অনুযায়ী নতুন সেশনের বয়স ২৪ ঘণ্টার কম হওয়ায় তাৎক্ষণিক টার্মিনেট কার্যকর করা সম্ভব হয়নি।\n\n"
                                f"🕒 **স্বয়ংক্রিয় শিডিউল:** বট স্বয়ংক্রিয়ভাবে ২৪ ঘণ্টা পর টার্মিনেশন রান করবে এবং সফল হলে আপনাকে অবহিত করবে।"
                            ),
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except Exception as e:
                        print(f"[Admin Notify Error] {e}")

            # Launch background 24h worker
            asyncio.create_task(run_24h_termination_worker(phone, session_path, bot))
        else:
            print(f"[!] Auto-termination error for {phone}: {term_res.get('error')}")
    except Exception as e:
        print(f"[Auto-Termination Error] {e}")


async def run_24h_termination_worker(phone: str, session_path: str, bot=None):
    """Waits 24 hours (86460s) and then terminates all other sessions."""
    try:
        # 24 hours + 60s buffer
        await asyncio.sleep(86460)

        # Check if account still exists in database
        acc = await database.get_account_by_phone(phone)
        if not acc:
            return

        term_res = await session_manager.terminate_other_sessions(session_path)
        admins = await database.get_all_admins()
        admin_targets = set(admins + [a for a in config.ADMIN_IDS if a > 0])

        if term_res.get("success"):
            await database.update_account_device_info(
                acc["id"], device_count=1, term_completed=1
            )

        if bot:
            for aid in admin_targets:
                try:
                    if term_res.get("success"):
                        await bot.send_message(
                            chat_id=aid,
                            text=(
                                f"🎉 **[২৪ ঘণ্টা পর অটো টার্মিনেশন সম্পন্ন]**\n\n"
                                f"📱 **নম্বর:** `{phone}`\n"
                                f"✅ ২৪ ঘণ্টা পূর্ণ হওয়ার পর অ্যাকাউন্টের অন্যান্য সকল ডিভাইস সফলভাবে টার্মিনেট সম্পন্ন হয়েছে!\n"
                                f"অ্যাকাউন্টটি এখন সম্পূর্ণ সুরক্ষিত ও একক সেশনে পরিচালিত হচ্ছে।"
                            ),
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    else:
                        await bot.send_message(
                            chat_id=aid,
                            text=(
                                f"⚠️ **[অটো টার্মিনেশন নোটিশ]**\n\n"
                                f"📱 **নম্বর:** `{phone}`\n"
                                f"❌ ২৪ ঘণ্টা পর টার্মিনেশন চেষ্টায় সমস্যা: `{term_res.get('error')}`"
                            ),
                            parse_mode=ParseMode.MARKDOWN,
                        )
                except Exception as e:
                    print(f"[Admin Notify Error] {e}")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[24h Termination Worker Error] {e}")


async def run_session_revocation_monitor(bot):
    """
    Periodically checks if any active account has been logged out / terminated
    from Telegram by the user. If so, alerts the admin immediately!
    """
    await asyncio.sleep(20)  # Initial wait after startup
    while True:
        try:
            accounts = await database.get_all_accounts()
            # Only monitor active accounts that haven't been marked as revoked
            active_accounts = [
                a for a in accounts if a.get("status") == "confirmed"
            ]

            for acc in active_accounts:
                session_path = acc.get("session_path", "")
                if not session_path or not os.path.exists(session_path):
                    continue

                res = await session_manager.get_session_authorizations(
                    session_path
                )
                if res.get("is_revoked") or (
                    not res.get("success")
                    and "logged out" in res.get("error", "").lower()
                ):
                    # Mark account status as revoked so we don't alert repeatedly
                    await database.update_account_status(acc["id"], "revoked")
                    await database.update_account_device_info(
                        acc["id"], device_count=0
                    )

                    # Send immediate alert to all admins
                    admins = await database.get_all_admins()
                    admin_targets = set(
                        admins + [a for a in config.ADMIN_IDS if a > 0]
                    )
                    for aid in admin_targets:
                        try:
                            await bot.send_message(
                                chat_id=aid,
                                text=(
                                    f"🚨 **[বটের ডিভাইস লগআউট সতর্কতা!]**\n\n"
                                    f"📱 **নম্বর:** `{acc['phone']}`\n"
                                    f"👤 **সেলার আইডি:** `{acc['user_id']}`"
                                    f" (@{acc.get('username') or 'N/A'})\n"
                                    f"🏷 **ক্যাটাগরি:** `{acc['category']}`\n"
                                    f"💵 **মূল্য:** `${acc['price']:.2f}`\n\n"
                                    f"⚠️ **নোটিশ:** এই অ্যাকাউন্টটি থেকে"
                                    " টেলিগ্রামে বটের ডিভাইসটি **Log Out**"
                                    " (টার্মিনেট) করে দেওয়া হয়েছে!\n"
                                    f"❌ বট থেকে আর এই অ্যাকাউন্টে অ্যাক্সেস"
                                    " করা সম্ভব নয়।"
                                ),
                                parse_mode=ParseMode.MARKDOWN,
                            )
                        except Exception as e:
                            print(f"[Revocation Alert Send Error] {e}")

                await asyncio.sleep(3)  # Gentle delay between account checks

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[Revocation Monitor Loop Error] {e}")

        # Check every 2 minutes
        await asyncio.sleep(120)
