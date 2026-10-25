import os
import random
import string
import datetime
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import config
import database
from session_manager import session_manager
from utils.helpers import normalize_phone_number, check_force_join


def get_persistent_reply_keyboard(is_admin: bool = False):
    """Creates persistent bottom keyboard buttons docked in Telegram chat."""
    if is_admin:
        keyboard = [
            [
                KeyboardButton("👑 Admin Panel"),
                KeyboardButton("📱 Devices"),
            ],
            [
                KeyboardButton("📊 Capacity"),
                KeyboardButton("💰 Balance"),
            ],
            [
                KeyboardButton("➕ Admin Add Number"),
                KeyboardButton("❌ Cancel"),
            ],
        ]
    else:
        keyboard = [
            [
                KeyboardButton("📊 Capacity"),
                KeyboardButton("💰 Balance"),
            ],
            [
                KeyboardButton("❓ Help"),
                KeyboardButton("❌ Cancel"),
            ],
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_main_keyboard(is_admin: bool = False):
    keyboard = []
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("👑 Admin Panel", callback_data="adm_main"),
            InlineKeyboardButton("📱 Devices", callback_data="adm_device"),
        ])
    keyboard.extend([
        [
            InlineKeyboardButton("📊 Capacity", callback_data="btn_capacity"),
            InlineKeyboardButton(
                "💰 Balance & Withdraw", callback_data="btn_balance"
            ),
        ],
        [
            InlineKeyboardButton("❓ Help & Support", callback_data="btn_help"),
            InlineKeyboardButton("❌ Cancel Process", callback_data="btn_cancel"),
        ],
    ])
    return InlineKeyboardMarkup(keyboard)


async def send_force_join_prompt(update: Update, channel: str):
    channel_url = (
        f"https://t.me/{channel.replace('@', '')}"
        if channel.startswith("@")
        else channel
    )
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=channel_url)],
        [InlineKeyboardButton("🔄 Joined (Check)", callback_data="check_join")],
    ]
    text = (
        "⚠️ **Force Join Required!**\n\n"
        "বটটি ব্যবহার করার জন্য আপনাকে আমাদের অফিসিয়াল চ্যানেলে যুক্ত হতে হবে।\n"
        "Please join our channel before continuing to use the bot:"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    # Create or update user in database
    await database.create_or_update_user(user.id, user.username, user.first_name)

    # Check maintenance mode
    maintenance = await database.get_setting("maintenance_mode", "0")
    if maintenance == "1" and not await database.is_admin(user.id):
        await update.message.reply_text(
            "🛠 **Maintenance Mode Active**\n\n"
            "বটটি বর্তমানে মেইনটেনেন্সে রয়েছে। কিছুক্ষণের মধ্যে আবার চালু করা হবে।\n"
            "The bot is currently undergoing scheduled maintenance. Please check back shortly.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Check ban
    db_user = await database.get_user(user.id)
    if db_user and db_user.get("is_banned"):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    # Check Force Join
    join_channel = await database.get_setting("join_lock_channel", "")
    if join_channel:
        is_member = await check_force_join(context.bot, user.id, join_channel)
        if not is_member:
            await send_force_join_prompt(update, join_channel)
            return

    is_admin = await database.is_admin(user.id)
    name = user.first_name or user.username or "User"
    welcome_text = (
        f"👋 **Welcome, {name}!**\n\n"
        "🤖 **Telegram Account & Session Receiver Bot**-এ স্বাগতম!\n\n"
        "💡 **কিভাবে বট ব্যবহার করবেন / How to use:**\n"
        "আপনার টেলিগ্রাম নম্বরটি কান্ট্রি কোডসহ পাঠান (Send your phone number with country code):\n"
        "👉 উদাহরণ: `+8801700000000` অথবা `+12025550123`\n\n"
        "📌 **উপলব্ধ কমান্ডসমূহ / Available Commands:**\n"
        "• `/capacity` - দেশের তালিকা ও রেট দেখুন\n"
        "• `/balance` - ব্যালেন্স চেক ও উত্তোলন করুন\n"
        "• `/cancel` - যেকোনো চলমান প্রসেস বাতিল করুন\n"
        "• `/help` - সাপোর্ট ও আপডেট চ্যানেল"
    )
    if is_admin:
        welcome_text += "\n\n👑 **অ্যাডমিন অপশন:** আপনার জন্য নিচের মেনু এবং ড্যাশবোর্ড বাটনগুলো স্বয়ংক্রিয়ভাবে অ্যাক্টিভ রয়েছে।"

    await update.message.reply_text(
        "⚡️ বট সক্রিয় রয়েছে।" if not is_admin else "👑 **অ্যাডমিন প্যানেল সক্রিয়:** আপনার সমস্ত অপশন নিচে স্বয়ংক্রিয়ভাবে অ্যাক্টিভ করা হয়েছে।",
        reply_markup=get_persistent_reply_keyboard(is_admin),
        parse_mode=ParseMode.MARKDOWN,
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(is_admin),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = await database.is_admin(user_id)
    context.user_data.clear()
    await session_manager.cancel_session(user_id)

    msg = "✅ **চলমান প্রসেস বাতিল করা হয়েছে।**\nAny ongoing process or login attempt has been cancelled."
    if update.callback_query:
        await update.callback_query.answer("Cancelled")
        await update.callback_query.message.reply_text(
            msg,
            reply_markup=get_persistent_reply_keyboard(is_admin),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            msg,
            reply_markup=get_persistent_reply_keyboard(is_admin),
            parse_mode=ParseMode.MARKDOWN,
        )


async def capacity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    countries = await database.get_active_countries()
    if not countries:
        text = "ℹ️ বর্তমানে কোনো সক্রিয় দেশ নেই। (No active countries available right now.)"
    else:
        text = "🌍 **দেশ ও প্রাইস তালিকা (Capacity & Rates):**\n\n"
        for c in countries:
            flag = "🌐"
            avail = max(0, c["capacity"] - c["used_capacity"])
            text += (
                f"{flag} **{c['name']}** ({c['dial_code']})\n"
                f"├ 📊 Capacity: `{avail}/{c['capacity']}`\n"
                f"├ 🟢 Free: `${c['main_price']:.2f}`\n"
                f"├ 🟡 Spam: `${c['spam_price']:.2f}`\n"
                f"├ 🆕 New Acc: `${c['new_acc_price']:.2f}`\n"
                f"└ ⏱ Confirm Time: `{c['confirm_time']}s`\n\n"
            )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN
        )
    elif update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = await database.get_user(user.id)
    if not db_user:
        await database.create_or_update_user(
            user.id, user.username, user.first_name
        )
        db_user = await database.get_user(user.id)

    name = db_user.get("first_name") or user.first_name or "User"
    username = (
        f"@{db_user.get('username')}" if db_user.get("username") else "N/A"
    )
    balance = db_user.get("balance", 0.0)
    accounts_sold = db_user.get("accounts_sold", 0)

    text = (
        f"👤 **ব্যবহারকারীর তথ্য (User Profile):**\n\n"
        f"• **Name:** {name}\n"
        f"• **User ID:** `{user.id}`\n"
        f"• **Username:** {username}\n"
        f"• **Balance:** `${balance:.2f}`\n"
        f"• **Accounts Sold:** `{accounts_sold}`"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 Withdraw Balance", callback_data="btn_withdraw"
            ),
            InlineKeyboardButton(
                "📜 Withdraw History", callback_data="btn_withdraw_history"
            ),
        ]
    ]

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    support_url = await database.get_setting(
        "support_url", "https://t.me/telegram"
    )
    updates_url = await database.get_setting(
        "updates_url", "https://t.me/telegram"
    )

    text = (
        "❓ **সাহায্য ও সাপোর্ট (Help & Support):**\n\n"
        "বট সংক্রান্ত যেকোনো সমস্যায় অথবা আপডেটের জন্য আমাদের অফিসিয়াল চ্যানেলে যুক্ত হোন:\n\n"
        "• কোন সমস্যা হলে সাপোর্ট এডমিনকে নক করুন\n"
        "• অ্যাকাউন্ট কনফার্মেশন পেতে সঠিক কান্ট্রি কোডসহ নম্বর সাবমিট করুন"
    )

    keyboard = [
        [
            InlineKeyboardButton("📢 Updates Channel", url=updates_url),
            InlineKeyboardButton("💬 Support", url=support_url),
        ]
    ]

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )


# ================= WITHDRAWAL FLOW =================


async def handle_withdraw_click(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Check withdraw system status
    withdraw_enabled = await database.get_setting("withdraw_enabled", "1")
    if withdraw_enabled == "0" and not await database.is_admin(user_id):
        await query.message.reply_text(
            "⚠️ **উইথড্র সিস্টেম সাময়িকভাবে বন্ধ আছে।**\nWithdrawals are temporarily disabled by admin.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    db_user = await database.get_user(user_id)
    user_balance = db_user.get("balance", 0.0) if db_user else 0.0

    min_wd_str = await database.get_setting("min_wd", "5.0")
    try:
        min_wd = float(min_wd_str)
    except ValueError:
        min_wd = 5.0

    if user_balance < min_wd:
        await query.message.reply_text(
            f"⚠️ **অপর্যাপ্ত ব্যালেন্স!**\n"
            f"নূন্যতম উইথড্র অ্যামাউন্ট: `${min_wd:.2f}`\n"
            f"আপনার বর্তমান ব্যালেন্স: `${user_balance:.2f}`\n\n"
            f"Minimum withdrawal amount is `${min_wd:.2f}`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    context.user_data["state"] = "waiting_wd_amount"
    context.user_data["max_balance"] = user_balance
    context.user_data["min_wd"] = min_wd

    await query.message.reply_text(
        f"💵 **উইথড্র অ্যামাউন্ট লিখুন (Enter Amount):**\n\n"
        f"• আপনার ব্যালেন্স: `${user_balance:.2f}`\n"
        f"• নূন্যতম উইথড্র: `${min_wd:.2f}`\n\n"
        f"কত ডলার উইথড্র করতে চান তা লিখে পাঠান (Send the amount you wish to withdraw):",
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_withdraw_history_click(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    withdrawals = await database.get_withdrawals_by_user(user_id, limit=10)
    if not withdrawals:
        await query.message.reply_text(
            "📜 আপনার কোনো উইথড্র রেকর্ড নেই। (No withdrawal history found.)"
        )
        return

    text = "📜 **আপনার সাম্প্রতিক উইথড্র হিস্ট্রি (Withdrawal History):**\n\n"
    for w in withdrawals:
        status = w.get("status", "pending")
        if status == "paid":
            st_emoji = "🟢 Approved & Paid"
        elif status == "rejected":
            st_emoji = "🔴 Rejected"
        else:
            st_emoji = "🟡 Pending"

        text += (
            f"• **ID:** `{w['wid']}`\n"
            f"  Amount: `${w['amount']:.2f}`\n"
            f"  Method: `{w['method']}` ({w['wallet']})\n"
            f"  Status: {st_emoji}\n"
            f"  Date: `{w['created_at']}`\n\n"
        )

    await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ================= INCOMING USER TEXT MESSAGE HANDLER =================


async def handle_user_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    text = update.message.text.strip()
    user_id = user.id

    # Check ban
    db_user = await database.get_user(user_id)
    if db_user and db_user.get("is_banned"):
        return

    state = context.user_data.get("state")

    # 1. Handling Withdrawal Amount input
    if state == "waiting_wd_amount":
        try:
            amount = float(text.replace("$", "").strip())
        except ValueError:
            await update.message.reply_text(
                "❌ সঠিক সংখ্যা লিখুন (e.g. 5.50)। Please enter a valid number."
            )
            return

        min_wd = context.user_data.get("min_wd", 5.0)
        max_bal = context.user_data.get("max_balance", 0.0)

        if amount < min_wd:
            await update.message.reply_text(
                f"❌ নূন্যতম উইথড্র `${min_wd:.2f}` হতে হবে।"
            )
            return
        if amount > max_bal:
            await update.message.reply_text(
                f"❌ আপনার ব্যালেন্সে পর্যাপ্ত অর্থ নেই! সর্বোচ্চ: `${max_bal:.2f}`"
            )
            return

        context.user_data["wd_amount"] = amount
        context.user_data["state"] = "waiting_wd_wallet"
        await update.message.reply_text(
            f"💳 **পেমেন্ট মেথড ও ওয়ালেট অ্যাড্রেস লিখুন:**\n\n"
            f"উইথড্র অ্যামাউন্ট: `${amount:.2f}`\n"
            f"আপনার পেমেন্ট মাধ্যম ও অ্যাকাউন্ট নম্বর লিখে পাঠান:\n"
            f"👉 উদাহরণ: `Bkash: 01700000000` অথবা `USDT TRC20: Txxxxxxxx` অথবা `Nagad: 01900000000`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 2. Handling Withdrawal Wallet input
    if state == "waiting_wd_wallet":
        amount = context.user_data.get("wd_amount", 0.0)
        wallet_info = text
        method = "Other"
        if ":" in wallet_info:
            parts = wallet_info.split(":", 1)
            method = parts[0].strip()
            wallet = parts[1].strip()
        else:
            wallet = wallet_info

        # Generate unique W-ID
        wid = "W-" + "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )

        await database.create_withdrawal(
            wid=wid,
            user_id=user_id,
            amount=amount,
            method=method,
            wallet=wallet,
        )
        context.user_data.clear()

        await update.message.reply_text(
            f"✅ **উইথড্র রিকোয়েস্ট সফলভাবে সাবমিট হয়েছে!**\n\n"
            f"• **Withdraw ID:** `{wid}`\n"
            f"• **Amount:** `${amount:.2f}`\n"
            f"• **Method:** `{method}`\n"
            f"• **Account/Wallet:** `{wallet}`\n\n"
            f"অ্যাডমিন ভেরিফাই করে দ্রুত পেমেন্ট সম্পন্ন করবেন।",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Notify Payment Channel or Admin
        payment_chan = await database.get_setting("payment_channel", "")
        if payment_chan:
            try:
                chan_text = (
                    f"💳 **New Withdrawal Request Submitted**\n"
                    f"• W-ID: `{wid}`\n"
                    f"• User ID: `{user_id}`\n"
                    f"• Amount: `${amount:.2f}`\n"
                    f"• Account: `{wallet_info}`"
                )
                await context.bot.send_message(
                    chat_id=payment_chan,
                    text=chan_text,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as e:
                print(f"[PaymentChan Notify Error]: {e}")
        return

    # 3. Check if user is currently in OTP / 2FA login flow
    pending_sess = session_manager.get_pending(user_id)
    if pending_sess:
        # If waiting for 2FA password
        if pending_sess.is_waiting_2fa:
            pwd = text
            await update.message.reply_text(
                "⏳ Verifying 2FA password, please wait..."
            )
            res = await session_manager.submit_2fa(user_id, pwd)
            if res.get("status") == "success":
                await notify_account_success(update, context, res, user_id)
            elif res.get("status") == "invalid_password":
                await update.message.reply_text(
                    "❌ ভুল পাসওয়ার্ড! আবার চেষ্টা করুন অথবা /cancel চাপুন।"
                )
            else:
                await update.message.reply_text(
                    f"❌ {res.get('message', 'Login error')}"
                )
            return

        # If waiting for OTP code (digits or spaced digits)
        clean_text = text.replace(" ", "").replace("-", "")
        if clean_text.isdigit():
            await update.message.reply_text("⏳ Verifying OTP code...")
            res = await session_manager.submit_otp(user_id, clean_text)

            if res.get("status") == "success":
                await notify_account_success(update, context, res, user_id)
            elif res.get("status") == "need_2fa":
                await update.message.reply_text(
                    "🔐 **Two-Step Verification (2FA) চালু আছে!**\n\n"
                    "অনুগ্রহ করে এই অ্যাকাউন্টের 2FA পাসওয়ার্ডটি লিখে পাঠান:\n"
                    "(Please enter the 2FA password for this account. Send /cancel to abort):",
                    parse_mode=ParseMode.MARKDOWN,
                )
            elif res.get("status") == "invalid_code":
                await update.message.reply_text(
                    "❌ **ভুল ওটিপি কোড!** অনুগ্রহ করে সঠিক কোডটি পুনরায় দিন অথবা /cancel চাপুন।"
                )
            elif res.get("status") == "rejected":
                await update.message.reply_text(
                    res.get("message", "Account rejected.")
                )
            else:
                await update.message.reply_text(
                    f"❌ {res.get('message', 'Error')}"
                )
            return

    # Check if text looks like an OTP code but no session is active (e.g. timed out)
    clean_digits = text.replace(" ", "").replace("-", "")
    if clean_digits.isdigit() and 4 <= len(clean_digits) <= 7:
        await update.message.reply_text(
            "⚠️ **কোনো সেশন অপেক্ষমাণ (Pending) নেই বা কোড দেওয়ার সময় শেষ হয়ে গেছে!**\n\n"
            "অনুগ্রহ করে কান্ট্রি কোডসহ মোবাইল নম্বরটি পুনরায় পাঠান (যেমন: `+8801700000000`)।",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # 4. Check if text is a phone number to start a new login
    phone_info = normalize_phone_number(text)
    if phone_info:
        # Check maintenance
        maintenance = await database.get_setting("maintenance_mode", "0")
        if maintenance == "1" and not await database.is_admin(user_id):
            await update.message.reply_text(
                "🛠 বটটি বর্তমানে রক্ষণাবেক্ষণে (Maintenance) আছে।"
            )
            return

        # Check receive enabled
        receive_enabled = await database.get_setting("receive_enabled", "1")
        if receive_enabled == "0" and not await database.is_admin(user_id):
            await update.message.reply_text(
                "🚫 **অ্যাকাউন্ট রিসিভ সিস্টেম সাময়িকভাবে বন্ধ আছে।**\nAccount receiving is currently paused."
            )
            return

        # Force Join check
        join_channel = await database.get_setting("join_lock_channel", "")
        if join_channel:
            is_member = await check_force_join(
                context.bot, user_id, join_channel
            )
            if not is_member:
                await send_force_join_prompt(update, join_channel)
                return

        # Check existing account
        existing = await database.get_account_by_phone(phone_info["e164"])
        if existing:
            await update.message.reply_text(
                "⚠️ **এই নম্বরটি ইতোমধ্যে আমাদের ডেটাবেজে যুক্ত আছে!**\nThis phone number has already been registered."
            )
            return

        # Check country support & capacity
        is_user_admin = await database.is_admin(user_id)
        country = await database.get_country_by_dial_code(
            phone_info["dial_code"]
        )

        if is_user_admin:
            # 👑 ADMIN PRIVILEGE: Admin can add ANY country without restrictions
            if not country:
                import phonenumbers
                import phonenumbers.geocoder
                try:
                    parsed_p = phonenumbers.parse(phone_info["e164"], None)
                    c_name = phonenumbers.geocoder.description_for_number(
                        parsed_p, "en"
                    )
                    if not c_name:
                        c_name = f"Country ({phone_info['dial_code']})"
                except Exception:
                    c_name = f"Country ({phone_info['dial_code']})"

                country_id = await database.add_country(
                    name=c_name,
                    dial_code=phone_info["dial_code"],
                    capacity=999999,
                    main_price=0.80,
                    spam_price=0.40,
                    new_acc_price=0.60,
                    confirm_time=600,
                    status=1,
                    premium_only=0,
                    accept_spam=1,
                    login_email=0,
                )
                country = await database.get_country_by_id(country_id)
        else:
            if not country or not country.get("status", 1):
                await update.message.reply_text(
                    f"❌ এই দেশের ({phone_info['dial_code']}) নম্বর বর্তমানে রিসিভ করা হচ্ছে না।\n"
                    f"Country {phone_info['dial_code']} is not currently supported or inactive. Check /capacity."
                )
                return

            # Capacity check
            if country["used_capacity"] >= country["capacity"]:
                await update.message.reply_text(
                    f"⚠️ এই দেশের আজকের ক্যাপাসিটি পূর্ণ হয়ে গেছে! ({country['name']})\n"
                    f"Capacity limit reached for {country['name']} today."
                )
                return

            # Premium only check
            if country.get("premium_only") and not (
                db_user and db_user.get("is_premium")
            ):
                await update.message.reply_text(
                    "⭐ **এই দেশটি শুধুমাত্র প্রিমিয়াম ইউজারদের জন্য সংরক্ষিত!**\nThis country is restricted to Premium users."
                )
                return

        await update.message.reply_text(
            f"🔄 `{phone_info['e164']}` নম্বরে ওটিপি পাঠানোর চেষ্টা করা হচ্ছে...\nConnecting & requesting code...",
            parse_mode=ParseMode.MARKDOWN,
        )

        async def _on_timeout(uid: int):
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=(
                        "⏱ **কনফার্মেশন সময় শেষ!**\nনির্ধারিত সময়ে কোড না"
                        " দেওয়ায় প্রসেস বাতিল করা হয়েছে।\nSession timed out."
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass

        res = await session_manager.start_login(
            user_id=user_id,
            phone=phone_info["e164"],
            country=country,
            timeout_callback=_on_timeout,
        )

        if not res.get("success"):
            await update.message.reply_text(
                f"❌ **ত্রুটি:** {res.get('error', 'Login request failed')}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        confirm_time = res.get("confirm_time", 600)
        await update.message.reply_text(
            f"📲 **কোড পাঠানো হয়েছে `{phone_info['e164']}` নম্বরে!**\n\n"
            f"⏱ অনুগ্রহ করে পরবর্তী **{confirm_time}** সেকেন্ডের মধ্যে ওটিপি কোডটি পাঠান।\n"
            f"👉 কোড ফরম্যাট: `12345` অথবা `1 2 3 4 5`\n\n"
            f"বাতিল করতে /cancel কমান্ড ব্যবহার করুন।",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Default fallback
    await update.message.reply_text(
        "💡 কান্ট্রি কোডসহ একটি মোবাইল নম্বর পাঠান (যেমন: `+8801700000000`) অথবা নিচের মেনু বাটন ব্যবহার করুন।",
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def notify_account_success(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    res: dict,
    user_id: int,
):
    phone = res["phone"]
    cat = res["category"]
    price = res["price"]
    bal = res["new_balance"]
    c_name = res["country_name"]

    success_msg = (
        f"🎉 **অ্যাকাউন্ট সফলভাবে যুক্ত হয়েছে!**\n\n"
        f"📱 **Number:** `{phone}`\n"
        f"🌐 **Country:** {c_name}\n"
        f"🏷 **Category:** `{cat}`\n"
        f"💵 **Earned:** `+${price:.2f}`\n"
        f"💰 **New Balance:** `${bal:.2f}`\n\n"
        f"ধন্যবাদ! আপনি আরও নম্বর পাঠাতে পারেন।"
    )
    await update.message.reply_text(success_msg, parse_mode=ParseMode.MARKDOWN)

    # Post notification to Stats Channel if configured
    stats_chan = await database.get_setting("stats_channel", "")
    if stats_chan:
        try:
            stat_text = (
                f"📢 **New Account Confirmed!**\n\n"
                f"🌐 Country: {c_name}\n"
                f"🏷 Category: {cat}\n"
                f"💵 Payout: `${price:.2f}`\n"
                f"👤 User: `{user_id}`"
            )
            await context.bot.send_message(
                chat_id=stats_chan,
                text=stat_text,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            print(f"[StatsChan Error]: {e}")

    # Trigger auto termination check (5s delay, check sessions, terminate if needed)
    sess_path = res.get("session_path", "")
    if sess_path:
        from handlers.tech_handlers import trigger_auto_termination
        asyncio.create_task(trigger_auto_termination(phone, sess_path, context.bot))

    # Auto-backup .session file directly to admin Telegram chat so data is never lost
    if sess_path and os.path.exists(sess_path):
        try:
            admins = await database.get_all_admins()
            admin_targets = set(admins + [a for a in config.ADMIN_IDS if a > 0])
            for aid in admin_targets:
                with open(sess_path, "rb") as sf:
                    await context.bot.send_document(
                        chat_id=aid,
                        document=sf,
                        caption=(
                            f"💾 **[অটো সেশন ব্যাকআপ]**\n\n"
                            f"📱 **নম্বর:** `{phone}`\n"
                            f"🏷 **ক্যাটাগরি:** `{cat}`\n\n"
                            f"ক্লাউড সার্ভার রিস্টার্ট বা অফ হলেও আপনার সেশন ফাইলটি এখানে সুরক্ষিত থাকবে।"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
        except Exception as e:
            print(f"[Auto-Backup Error] {e}")
