from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import os

import database
from session_manager import session_manager
from utils.helpers import create_sessions_zip
from utils.excel_export import export_accounts_to_excel


def get_accounts_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(
                "📦 Download All Confirmed (ZIP)", callback_data="acc_dl_all"
            ),
            InlineKeyboardButton(
                "🟢 Download Free (ZIP)", callback_data="acc_dl_free"
            ),
        ],
        [
            InlineKeyboardButton(
                "🟡 Download Spam (ZIP)", callback_data="acc_dl_spam"
            ),
            InlineKeyboardButton(
                "🆕 Download New Acc (ZIP)", callback_data="acc_dl_new"
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 Accounts Excel Report", callback_data="acc_dl_excel"
            ),
        ],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_accounts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    stats = await database.get_accounts_stats()
    # In-memory pending count from session_manager
    pending_count = len(session_manager.pending_sessions)

    cats = stats.get("categories", {})
    free_cnt = cats.get("Free", 0)
    spam_cnt = cats.get("Spam", 0) + cats.get("Permanent Spam", 0)
    new_cnt = cats.get("New Register", 0)

    text = (
        "📁 **Accounts Manager & Statistics**\n\n"
        f"• **Total Confirmed Accounts:** `{stats['total_confirmed']}`\n"
        f"• **Currently In-Progress (Pending):** `{pending_count}`\n"
        f"• **Previously Downloaded:** `{stats['downloaded']}`\n\n"
        "📊 **ক্যাটাগরি ভিত্তিক পরিসংখ্যান:**\n"
        f"├ 🟢 Clean / Free: `{free_cnt}`\n"
        f"├ 🟡 Spam Accounts: `{spam_cnt}`\n"
        f"└ 🆕 New Register: `{new_cnt}`\n\n"
        "সেশন ফাইল (.session) জিপ আকারে অথবা এক্সেল রিপোর্ট ডাউনলোড করতে নিচের বাটন চাপুন:"
    )

    if query:
        await query.message.edit_text(
            text,
            reply_markup=get_accounts_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_accounts_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


async def handle_account_callbacks(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    query = update.callback_query
    data = query.data

    if data == "adm_accounts":
        await show_accounts_menu(update, context)
        return True

    if data in ("acc_dl_all", "acc_dl_free", "acc_dl_spam", "acc_dl_new"):
        await query.answer("Preparing session ZIP...")
        cat_map = {
            "acc_dl_all": None,
            "acc_dl_free": "Free",
            "acc_dl_spam": "Spam",
            "acc_dl_new": "New Register",
        }
        target_cat = cat_map[data]
        zip_path = create_sessions_zip(target_cat)

        if not zip_path or not os.path.exists(zip_path):
            await query.message.reply_text(
                "❌ কোনো সেশন ফাইল পাওয়া যায়নি। (No .session files found for this category.)"
            )
            return True

        caption = f"📦 **Telegram Sessions Package** ({target_cat or 'All Confirmed'})"
        with open(zip_path, "rb") as doc:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=doc,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )

        # Mark accounts as downloaded
        accs = await database.get_accounts_by_category(target_cat)
        acc_ids = [a["id"] for a in accs]
        await database.mark_accounts_downloaded(acc_ids)

        try:
            os.remove(zip_path)
        except Exception:
            pass
        return True

    if data == "acc_dl_excel":
        await query.answer("Generating Accounts Excel...")
        accounts = await database.get_all_accounts()
        if not accounts:
            await query.message.reply_text("কোনো অ্যাকাউন্ট পাওয়া যায়নি।")
            return True

        file_path = export_accounts_to_excel(accounts)
        with open(file_path, "rb") as doc:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=doc,
                caption="📊 **Accounts Database Report (.xlsx)**",
                parse_mode=ParseMode.MARKDOWN,
            )
        try:
            os.remove(file_path)
        except Exception:
            pass
        return True

    return False
