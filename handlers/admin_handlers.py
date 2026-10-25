from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database
import config
from utils.excel_export import export_withdrawals_to_excel
from handlers.country_handlers import (
    handle_country_callbacks,
    show_country_details,
)
from handlers.finance_handlers import handle_finance_callbacks
from handlers.withdraw_handlers import handle_withdrawal_callbacks
from handlers.account_handlers import handle_account_callbacks
from handlers.tech_handlers import handle_tech_callbacks


def get_admin_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(
                "🌍 Country Settings", callback_data="adm_countries"
            ),
            InlineKeyboardButton(
                "📢 Channel Management", callback_data="adm_channels"
            ),
        ],
        [
            InlineKeyboardButton("💰 Finance", callback_data="adm_finance"),
            InlineKeyboardButton(
                "💳 Withdrawals", callback_data="adm_withdrawals"
            ),
        ],
        [
            InlineKeyboardButton("🛠 User Tools", callback_data="adm_tools"),
            InlineKeyboardButton(
                "📁 Accounts Manager", callback_data="adm_accounts"
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 Daily Summary", callback_data="adm_summary"
            ),
            InlineKeyboardButton(
                "⚙️ Configuration", callback_data="adm_config"
            ),
        ],
        [
            InlineKeyboardButton(
                "📱 Device Settings", callback_data="adm_device"
            ),
            InlineKeyboardButton(
                "🔌 API & Technical Settings", callback_data="adm_tech"
            ),
        ],
        [
            InlineKeyboardButton(
                "➕ Admin Add Number", callback_data="adm_add_phone_flow"
            ),
            InlineKeyboardButton("❌ Close Panel", callback_data="adm_close"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await database.is_admin(user_id):
        await update.message.reply_text("🚫 **Access Denied.** You are not an administrator.")
        return

    text = (
        "👑 **Admin Control Panel (অ্যাডমিন প্যানেল)**\n\n"
        "স্বাগতম এডমিন! বটের যাবতীয় সেটিংস ও কার্যক্রম নিয়ন্ত্রণ করতে নিচের বাটনগুলো ব্যবহার করুন:"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            text,
            reply_markup=get_admin_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_admin_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


async def admin_callback_router(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    user_id = query.from_user.id

    if not await database.is_admin(user_id):
        await query.answer("Access Denied", show_alert=True)
        return

    data = query.data

    if data == "adm_main":
        await admin_command(update, context)
        return

    if data == "adm_close":
        await query.answer("Closed")
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if data == "adm_add_phone_flow":
        await query.answer()
        await query.message.reply_text(
            "📲 **অ্যাডমিন নম্বর যোগ করুন (Admin Add Number):**\n\n"
            "কান্ট্রি কোডসহ যেকোনো মোবাইল নম্বর চ্যাটে পাঠান:\n"
            "👉 উদাহরণ: `+8801700000000` অথবা `+12025550123`\n\n"
            "নম্বর পাঠানোর পর লগইন কোড (OTP) চাওয়া হবে। বাতিল করতে /cancel চাপুন।",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Check Country submenus
    if await handle_country_callbacks(update, context):
        return

    # Check Finance submenus
    if await handle_finance_callbacks(update, context):
        return

    # Check Withdrawal submenus
    if await handle_withdrawal_callbacks(update, context):
        return

    # Check Account Manager submenus
    if await handle_account_callbacks(update, context):
        return

    # Check Tech & Settings submenus
    if await handle_tech_callbacks(update, context):
        return

    await query.answer("Unknown action")


# ================= ADMIN TEXT INPUT FSM HANDLER =================


async def handle_admin_text_inputs(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    user_id = update.effective_user.id
    if not await database.is_admin(user_id):
        return False

    state = context.user_data.get("adm_state")
    if not state:
        return False

    text = update.message.text.strip()

    # --- Country Add Wizard ---
    if state == "c_add_name":
        context.user_data["c_add_data"]["name"] = text
        context.user_data["adm_state"] = "c_add_dial"
        await update.message.reply_text(
            "➕ **Step 2/5:** দেশের ডায়াল কোড লিখুন (e.g. `+234` or `+880`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if state == "c_add_dial":
        dial = text if text.startswith("+") else "+" + text
        context.user_data["c_add_data"]["dial_code"] = dial
        context.user_data["adm_state"] = "c_add_cap"
        await update.message.reply_text(
            "➕ **Step 3/5:** ক্যাপাসিটি সংখ্যা লিখুন (e.g. `100`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if state == "c_add_cap":
        try:
            cap = int(text)
        except ValueError:
            await update.message.reply_text("❌ পূর্ণসংখ্যা লিখুন (e.g. 100):")
            return True
        context.user_data["c_add_data"]["capacity"] = cap
        context.user_data["adm_state"] = "c_add_prices"
        await update.message.reply_text(
            "➕ **Step 4/5:** ৩টি ক্যাটাগরির প্রাইস লিখুন (Format: `Main Spam NewAcc`)\n"
            "👉 উদাহরণ: `0.80 0.40 0.60`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if state == "c_add_prices":
        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ ৩টি প্রাইস স্পেস দিয়ে লিখুন (e.g. `0.80 0.40 0.60`):"
            )
            return True
        try:
            mp, sp, np = float(parts[0]), float(parts[1]), float(parts[2])
        except ValueError:
            await update.message.reply_text("❌ সঠিক সংখ্যা লিখুন:")
            return True
        context.user_data["c_add_data"]["main_price"] = mp
        context.user_data["c_add_data"]["spam_price"] = sp
        context.user_data["c_add_data"]["new_acc_price"] = np
        context.user_data["adm_state"] = "c_add_time"
        await update.message.reply_text(
            "➕ **Step 5/5:** কনফার্মেশন টাইম সেকেন্ডে লিখুন (e.g. `600`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if state == "c_add_time":
        try:
            ct = int(text)
            if ct <= 10:
                ct = ct * 60
            if ct < 60:
                ct = 600
        except ValueError:
            ct = 600
        d = context.user_data["c_add_data"]
        cid = await database.add_country(
            name=d["name"],
            dial_code=d["dial_code"],
            capacity=d["capacity"],
            main_price=d["main_price"],
            spam_price=d["spam_price"],
            new_acc_price=d["new_acc_price"],
            confirm_time=ct,
        )
        context.user_data.pop("adm_state", None)
        context.user_data.pop("c_add_data", None)
        await update.message.reply_text(
            f"🎉 **দেশ যুক্ত করা হয়েছে!**\nCountry `{d['name']}` ({d['dial_code']}) added successfully.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    # --- Edit Country Prices / Capacity ---
    if state.startswith("waiting_prices_"):
        cid = int(state.split("_")[2])
        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ ৩টি প্রাইস স্পেস দিয়ে লিখুন (e.g. `0.80 0.40 0.60`):"
            )
            return True
        try:
            mp, sp, np = float(parts[0]), float(parts[1]), float(parts[2])
            await database.update_country(
                cid, main_price=mp, spam_price=sp, new_acc_price=np
            )
            context.user_data.pop("adm_state", None)
            await update.message.reply_text("✅ প্রাইস আপডেট সম্পন্ন হয়েছে!")
        except ValueError:
            await update.message.reply_text("❌ সঠিক সংখ্যা লিখুন:")
        return True

    if state.startswith("waiting_cap_"):
        cid = int(state.split("_")[2])
        try:
            cap = int(text)
            await database.update_country(cid, capacity=cap)
            context.user_data.pop("adm_state", None)
            await update.message.reply_text("✅ ক্যাপাসিটি আপডেট সম্পন্ন হয়েছে!")
        except ValueError:
            await update.message.reply_text("❌ পূর্ণসংখ্যা লিখুন:")
        return True

    # --- Finance: Add / Deduct Balance ---
    if state == "fin_waiting_add":
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ Format: `<User_ID> <Amount>`")
            return True
        try:
            target_uid = int(parts[0])
            amt = float(parts[1])
            new_b = await database.update_balance(target_uid, amt)
            context.user_data.pop("adm_state", None)
            await update.message.reply_text(
                f"✅ **Balance Added!**\nUser `{target_uid}`-এর নতুন ব্যালেন্স: `${new_b:.2f}`",
                parse_mode=ParseMode.MARKDOWN,
            )
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=f"🎁 **অ্যাডমিন আপনার অ্যাকাউন্টে +${amt:.2f} যোগ করেছেন!**\nবর্তমান ব্যালেন্স: `${new_b:.2f}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("❌ সঠিক আইডি ও সংখ্যা লিখুন:")
        return True

    if state == "fin_waiting_deduct":
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ Format: `<User_ID> <Amount>`")
            return True
        try:
            target_uid = int(parts[0])
            amt = float(parts[1])
            new_b = await database.update_balance(target_uid, -amt)
            context.user_data.pop("adm_state", None)
            await update.message.reply_text(
                f"✅ **Balance Deducted!**\nUser `{target_uid}`-এর নতুন ব্যালেন্স: `${new_b:.2f}`",
                parse_mode=ParseMode.MARKDOWN,
            )
        except ValueError:
            await update.message.reply_text("❌ সঠিক আইডি ও সংখ্যা লিখুন:")
        return True

    # --- Finance: Ban / Unban ---
    if state == "fin_waiting_ban":
        try:
            target_uid = int(text)
            await database.set_user_ban_status(target_uid, True)
            context.user_data.pop("adm_state", None)
            await update.message.reply_text(f"🚫 User `{target_uid}` has been banned.")
        except ValueError:
            await update.message.reply_text("❌ সঠিক User ID লিখুন:")
        return True

    if state == "fin_waiting_unban":
        try:
            target_uid = int(text)
            await database.set_user_ban_status(target_uid, False)
            context.user_data.pop("adm_state", None)
            await update.message.reply_text(f"🟢 User `{target_uid}` has been unbanned.")
        except ValueError:
            await update.message.reply_text("❌ সঠিক User ID লিখুন:")
        return True

    # --- Withdrawals: Search Status ---
    if state == "wd_waiting_search":
        context.user_data.pop("adm_state", None)
        wd = await database.get_withdrawal_by_wid(text)
        if wd:
            text_res = (
                f"💳 **Withdrawal Details ({wd['wid']}):**\n\n"
                f"• User ID: `{wd['user_id']}`\n"
                f"• Amount: `${wd['amount']:.2f}`\n"
                f"• Method: `{wd['method']}`\n"
                f"• Wallet: `{wd['wallet']}`\n"
                f"• Status: `{wd['status'].upper()}`\n"
                f"• Date: `{wd['created_at']}`\n"
                f"• Note: `{wd.get('admin_note') or 'None'}`"
            )
            await update.message.reply_text(text_res, parse_mode=ParseMode.MARKDOWN)
        else:
            # Check by user ID
            try:
                uid = int(text)
                wds = await database.get_withdrawals_by_user(uid, limit=5)
                if wds:
                    txt = f"💳 **Withdrawals for User `{uid}`:**\n\n"
                    for w in wds:
                        txt += f"• `{w['wid']}` | `${w['amount']:.2f}` | `{w['status']}`\n"
                    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text("কোনো উইথড্র রেকর্ড পাওয়া যায়নি।")
            except ValueError:
                await update.message.reply_text("কোনো উইথড্র রেকর্ড পাওয়া যায়নি।")
        return True

    # --- Withdrawals: Export by Date ---
    if state == "wd_waiting_export_date":
        context.user_data.pop("adm_state", None)
        date_str = text
        wds = await database.get_withdrawals_by_date(date_str)
        if not wds:
            await update.message.reply_text(f"No withdrawals found on {date_str}.")
            return True
        file_path = export_withdrawals_to_excel(wds, prefix=f"wd_{date_str}")
        with open(file_path, "rb") as doc:
            await context.bot.send_document(
                chat_id=user_id,
                document=doc,
                caption=f"📅 **Withdrawals Report for {date_str} (.xlsx)**",
                parse_mode=ParseMode.MARKDOWN,
            )
        try:
            import os
            os.remove(file_path)
        except Exception:
            pass
        return True

    # --- Channel Management ---
    if state == "set_chan_payment":
        val = "" if text.lower() == "none" else text
        await database.set_setting("payment_channel", val)
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"💳 Payment Channel set to: `{val or 'None'}`")
        return True

    if state == "set_chan_stats":
        val = "" if text.lower() == "none" else text
        await database.set_setting("stats_channel", val)
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"📊 Stats Channel set to: `{val or 'None'}`")
        return True

    if state == "set_chan_join":
        val = "" if text.lower() == "none" else text
        await database.set_setting("join_lock_channel", val)
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"🔒 Join Lock Channel set to: `{val or 'None'}`")
        return True

    if state == "set_chan_error":
        val = "" if text.lower() == "none" else text
        await database.set_setting("error_channel", val)
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"⚠️ Error Channel set to: `{val or 'None'}`")
        return True

    # --- Config: Min WD & 2FA ---
    if state == "set_min_wd":
        try:
            val = float(text)
            await database.set_setting("min_wd", str(val))
            context.user_data.pop("adm_state", None)
            await update.message.reply_text(f"💵 Minimum withdrawal set to: `${val:.2f}`")
        except ValueError:
            await update.message.reply_text("❌ সঠিক সংখ্যা লিখুন:")
        return True

    if state == "set_default_2fa":
        val = "" if text.lower() == "none" else text
        await database.set_setting("default_2fa", val)
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"🔐 Default 2FA Password set to: `{val or 'None'}`")
        return True

    # --- Manage Admins ---
    if state == "adm_add_admin_id":
        try:
            new_aid = int(text)
            await database.add_admin(new_aid)
            context.user_data.pop("adm_state", None)
            await update.message.reply_text(f"👑 Added `{new_aid}` to Admins list.")
        except ValueError:
            await update.message.reply_text("❌ সঠিক User ID দিন:")
        return True

    if state == "adm_rem_admin_id":
        try:
            rem_aid = int(text)
            res = await database.remove_admin(rem_aid)
            context.user_data.pop("adm_state", None)
            if res:
                await update.message.reply_text(f"👑 Removed `{rem_aid}` from Admins list.")
            else:
                await update.message.reply_text("❌ Could not remove primary environment admin.")
        except ValueError:
            await update.message.reply_text("❌ সঠিক User ID দিন:")
        return True

    # --- User Tools: Find by Phone ---
    if state == "ut_waiting_phone":
        context.user_data.pop("adm_state", None)
        acc = await database.get_account_by_phone(text)
        if acc:
            text_res = (
                f"📱 **Account Record Found:**\n\n"
                f"• Phone: `{acc['phone']}`\n"
                f"• User ID: `{acc['user_id']}`\n"
                f"• Username: @{acc.get('username') or 'N/A'}\n"
                f"• Country: {acc.get('country_name', 'Unknown')}\n"
                f"• Category: `{acc['category']}`\n"
                f"• Payout: `${acc['price']:.2f}`\n"
                f"• Date: `{acc['created_at']}`"
            )
            await update.message.reply_text(text_res, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ এই ফোন নম্বরের কোনো রেকর্ড পাওয়া যায়নি।")
        return True

    # --- Technical Settings Inputs ---
    if state == "set_app_id":
        await database.set_setting("app_id", text)
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"⚙️ App ID updated to: `{text}`")
        return True

    if state == "set_app_hash":
        await database.set_setting("app_hash", text)
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"⚙️ App Hash updated.")
        return True

    if state == "set_lang_code":
        await database.set_setting("system_lang_code", text)
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"⚙️ System Lang Code updated to: `{text}`")
        return True

    if state == "set_app_version":
        await database.set_setting("app_version", text)
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"⚙️ App Version updated to: `{text}`")
        return True

    if state == "set_proxy_info":
        context.user_data.pop("adm_state", None)
        text_clean = text.strip()
        if text_clean.lower() in ("none", "clear", "remove"):
            await database.set_setting("proxy_host", "")
            await database.set_setting("proxy_port", "1080")
            await database.set_setting("proxy_user", "")
            await database.set_setting("proxy_pass", "")
            await database.set_setting("proxy_enabled", "0")
            await update.message.reply_text("✅ প্রক্সি কনফিগারেশন মুছে ফেলা হয়েছে এবং বন্ধ করা হয়েছে।")
            return True

        # Check URL format (e.g. socks5://user:pass@host:port)
        import urllib.parse
        if "://" in text_clean:
            parsed = urllib.parse.urlsplit(text_clean)
            p_type = parsed.scheme.lower() or "socks5"
            p_host = parsed.hostname or ""
            p_port = str(parsed.port or (1080 if "socks" in p_type else 8080))
            p_user = parsed.username or ""
            p_pass = parsed.password or ""
        else:
            parts = text_clean.split(":")
            if len(parts) >= 3 and parts[0].lower() in ("socks5", "socks4", "http", "https"):
                p_type = parts[0].lower()
                p_host = parts[1]
                p_port = parts[2]
                p_user = parts[3] if len(parts) >= 4 else ""
                p_pass = parts[4] if len(parts) >= 5 else ""
            elif len(parts) >= 4:
                # host:port:user:pass
                p_type = "socks5"
                p_host = parts[0]
                p_port = parts[1]
                p_user = parts[2]
                p_pass = parts[3]
            elif len(parts) >= 2:
                # host:port
                p_type = "socks5"
                p_host = parts[0]
                p_port = parts[1]
                p_user = ""
                p_pass = ""
            else:
                await update.message.reply_text(
                    "❌ ফরম্যাট ভুল হয়েছে। উদাহরণ:\n`socks5:127.0.0.1:1080` অথবা `http://user:pass@ip:port`",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return True

        await database.set_setting("proxy_type", p_type)
        await database.set_setting("proxy_host", p_host)
        await database.set_setting("proxy_port", p_port)
        await database.set_setting("proxy_user", p_user)
        await database.set_setting("proxy_pass", p_pass)
        await update.message.reply_text(
            f"🌐 **Proxy Info Saved!**\n"
            f"• Type: `{p_type.upper()}`\n"
            f"• Host: `{p_host}`\n"
            f"• Port: `{p_port}`\n"
            f"• User: `{p_user or 'None'}`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if state == "set_proxy_iso":
        await database.set_setting("proxy_iso", text.upper())
        context.user_data.pop("adm_state", None)
        await update.message.reply_text(f"🌍 Proxy ISO updated to: `{text.upper()}`")
        return True

    if state == "set_device_model":
        context.user_data.pop("adm_state", None)
        if text.lower() == "default":
            await database.set_setting("custom_device_model", "")
            await update.message.reply_text("✅ Device Model রিসেট হয়ে ডিফল্ট প্রি-সেটে ফিরে এসেছে।")
        else:
            await database.set_setting("custom_device_model", text)
            await update.message.reply_text(f"📱 Device Model আপডেট হয়েছে: `{text}`", parse_mode=ParseMode.MARKDOWN)
        return True

    if state == "set_device_os":
        context.user_data.pop("adm_state", None)
        if text.lower() == "default":
            await database.set_setting("custom_system_version", "")
            await update.message.reply_text("✅ System OS Version রিসেট হয়ে ডিফল্ট প্রি-সেটে ফিরে এসেছে।")
        else:
            await database.set_setting("custom_system_version", text)
            await update.message.reply_text(f"💻 System OS Version আপডেট হয়েছে: `{text}`", parse_mode=ParseMode.MARKDOWN)
        return True

    if state == "dev_waiting_search_phone":
        context.user_data.pop("adm_state", None)
        phone_input = text.strip()
        account = await database.get_account_by_phone(phone_input)
        if not account:
            alt_phone = phone_input if phone_input.startswith("+") else "+" + phone_input
            account = await database.get_account_by_phone(alt_phone)

        if not account:
            await update.message.reply_text(
                f"❌ `{phone_input}` নম্বরের কোনো সেশন বা অ্যাকাউন্ট ডেটাবেজে পাওয়া যায়নি।",
                parse_mode=ParseMode.MARKDOWN,
            )
            return True

        from handlers.tech_handlers import show_account_devices_report
        await show_account_devices_report(update, context, account["id"])
        return True

    return False
