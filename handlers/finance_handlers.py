from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import os

import database
from utils.excel_export import export_users_to_excel


def get_finance_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Balance", callback_data="fin_add"),
            InlineKeyboardButton("➖ Deduct Balance", callback_data="fin_deduct"),
        ],
        [
            InlineKeyboardButton("🚫 Ban User", callback_data="fin_ban"),
            InlineKeyboardButton("🟢 Unban User", callback_data="fin_unban"),
        ],
        [
            InlineKeyboardButton(
                "🔄 Reset All Balances", callback_data="fin_reset_ask"
            ),
            InlineKeyboardButton(
                "📥 Export Users (xlsx)", callback_data="fin_export_excel"
            ),
        ],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_finance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    total_users = await database.get_users_count()
    users = await database.get_all_users()
    total_bal = sum(u.get("balance", 0.0) for u in users)

    text = (
        "💰 **Finance & User Balance Management**\n\n"
        f"• **Total Registered Users:** `{total_users}`\n"
        f"• **Total Active Balances:** `${total_bal:.2f}`\n\n"
        "নিচের অপশনগুলো থেকে আপনার প্রয়োজনীয় অ্যাকশন বেছে নিন:"
    )

    if query:
        await query.message.edit_text(
            text,
            reply_markup=get_finance_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_finance_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


async def handle_finance_callbacks(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    query = update.callback_query
    data = query.data

    if data == "adm_finance":
        await show_finance_menu(update, context)
        return True

    if data == "fin_add":
        context.user_data["adm_state"] = "fin_waiting_add"
        await query.message.reply_text(
            "➕ **ব্যালেন্স অ্যাড করুন (Add Balance):**\n\n"
            "ইউজার আইডি এবং অ্যামাউন্ট স্পেস দিয়ে লিখুন:\n"
            "👉 ফরম্যাট: `<User_ID> <Amount>` (যেমন: `123456789 10.50`)",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "fin_deduct":
        context.user_data["adm_state"] = "fin_waiting_deduct"
        await query.message.reply_text(
            "➖ **ব্যালেন্স মাইনাস করুন (Deduct Balance):**\n\n"
            "ইউজার আইডি এবং অ্যামাউন্ট স্পেস দিয়ে লিখুন:\n"
            "👉 ফরম্যাট: `<User_ID> <Amount>` (যেমন: `123456789 5.00`)",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "fin_ban":
        context.user_data["adm_state"] = "fin_waiting_ban"
        await query.message.reply_text(
            "🚫 **ইউজার ব্যান করুন (Ban User):**\n\n"
            "ব্যান করার জন্য ইউজার আইডি পাঠান (Send User ID):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "fin_unban":
        context.user_data["adm_state"] = "fin_waiting_unban"
        await query.message.reply_text(
            "🟢 **ইউজার আনব্যান করুন (Unban User):**\n\n"
            "আনব্যান করার জন্য ইউজার আইডি পাঠান (Send User ID):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "fin_reset_ask":
        kb = [
            [
                InlineKeyboardButton(
                    "⚠️ YES, RESET ALL", callback_data="fin_reset_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ No, Cancel", callback_data="adm_finance"
                )
            ],
        ]
        await query.message.edit_text(
            "⚠️ **Are you sure?**\n\n"
            "আপনি কি নিশ্চিত যে সকল ইউজারের ব্যালেন্স ০.০০ ($0.00) করতে চান?\n"
            "This will reset ALL users' balances to 0.00!",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "fin_reset_confirm":
        count = await database.reset_all_balances()
        await query.answer("All balances reset!")
        await query.message.reply_text(
            f"✅ **সকল ইউজারের ব্যালেন্স রিসেট সফল হয়েছে!**\nReset balances for `{count}` users.",
            parse_mode=ParseMode.MARKDOWN,
        )
        await show_finance_menu(update, context)
        return True

    if data == "fin_export_excel":
        await query.answer("Generating Excel file...")
        users = await database.get_all_users()
        if not users:
            await query.message.reply_text("কোনো ইউজার পাওয়া যায়নি।")
            return True

        file_path = export_users_to_excel(users)
        with open(file_path, "rb") as doc:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=doc,
                caption="📥 **All Users Database Export (.xlsx)**",
                parse_mode=ParseMode.MARKDOWN,
            )
        try:
            os.remove(file_path)
        except Exception:
            pass
        return True

    return False
