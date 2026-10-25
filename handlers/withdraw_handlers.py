from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import os
import datetime

import database
from utils.excel_export import export_withdrawals_to_excel


def get_withdrawals_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(
                "⏳ Pending Withdrawals", callback_data="wd_pending_list"
            ),
            InlineKeyboardButton(
                "🔍 Check Status (W-ID/User)", callback_data="wd_search_prompt"
            ),
        ],
        [
            InlineKeyboardButton(
                "📥 Export All Withdrawals (xlsx)",
                callback_data="wd_export_all",
            ),
            InlineKeyboardButton(
                "📅 Export by Date (xlsx)", callback_data="wd_export_date_prompt"
            ),
        ],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_withdrawals_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query:
        await query.answer()

    pending_list = await database.get_pending_withdrawals()
    all_wd = await database.get_all_withdrawals()

    total_pending_amt = sum(w.get("amount", 0.0) for w in pending_list)
    total_paid_amt = sum(
        w.get("amount", 0.0) for w in all_wd if w.get("status") == "paid"
    )

    text = (
        "💳 **Withdrawals Management**\n\n"
        f"• **Pending Requests:** `{len(pending_list)}` (${total_pending_amt:.2f})\n"
        f"• **Total Paid Out:** `${total_paid_amt:.2f}`\n\n"
        "উইথড্র রিকোয়েস্ট অনুমোদন, বাতিল অথবা এক্সেল আকারে ডাউনলোড করার অপশন বেছে নিন:"
    )

    if query:
        await query.message.edit_text(
            text,
            reply_markup=get_withdrawals_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=get_withdrawals_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


async def show_pending_withdrawals(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query:
        await query.answer()

    pending = await database.get_pending_withdrawals()
    if not pending:
        await query.message.reply_text(
            "✅ বর্তমানে কোনো পেন্ডিং উইথড্র রিকোয়েস্ট নেই। (No pending withdrawals.)"
        )
        return

    for w in pending[:8]:  # Show up to 8 in separate prompt
        wid = w["wid"]
        text = (
            f"💳 **Withdrawal Request:** `{wid}`\n"
            f"• **User ID:** `{w['user_id']}` (@{w.get('username') or 'N/A'})\n"
            f"• **Amount:** `${w['amount']:.2f}`\n"
            f"• **Method:** `{w['method']}`\n"
            f"• **Account/Wallet:** `{w['wallet']}`\n"
            f"• **Date:** `{w['created_at']}`"
        )
        kb = [
            [
                InlineKeyboardButton(
                    f"✅ Approve & Pay", callback_data=f"wd_pay_{wid}"
                ),
                InlineKeyboardButton(
                    f"❌ Reject (Refund)", callback_data=f"wd_rej_{wid}"
                ),
            ]
        ]
        await query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN,
        )


async def handle_withdrawal_callbacks(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    query = update.callback_query
    data = query.data

    if data == "adm_withdrawals":
        await show_withdrawals_menu(update, context)
        return True

    if data == "wd_pending_list":
        await show_pending_withdrawals(update, context)
        return True

    if data == "wd_search_prompt":
        context.user_data["adm_state"] = "wd_waiting_search"
        await query.message.reply_text(
            "🔍 **উইথড্র স্ট্যাটাস অনুসন্ধান:**\n\n"
            "উইথড্র আইডি (e.g. `W-123456`) অথবা ব্যবহারকারীর User ID লিখে পাঠান:",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data == "wd_export_all":
        await query.answer("Generating Excel file...")
        withdrawals = await database.get_all_withdrawals()
        if not withdrawals:
            await query.message.reply_text("কোনো উইথড্র রেকর্ড পাওয়া যায়নি।")
            return True

        file_path = export_withdrawals_to_excel(
            withdrawals, prefix="all_withdrawals"
        )
        with open(file_path, "rb") as doc:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=doc,
                caption="📥 **All Withdrawals Record (.xlsx)**",
                parse_mode=ParseMode.MARKDOWN,
            )
        try:
            os.remove(file_path)
        except Exception:
            pass
        return True

    if data == "wd_export_date_prompt":
        context.user_data["adm_state"] = "wd_waiting_export_date"
        today = datetime.date.today().isoformat()
        await query.message.reply_text(
            f"📅 **তারিখ অনুযায়ী উইথড্র ডাউনলোড:**\n\n"
            f"তারিখটি `YYYY-MM-DD` ফরম্যাটে লিখে পাঠান (যেমন: `{today}`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data.startswith("wd_pay_"):
        wid = data.replace("wd_pay_", "")
        res = await database.update_withdrawal_status(
            wid, status="paid", admin_note="Approved by Admin"
        )
        if res:
            await query.answer("Payment marked as PAID!")
            await query.message.edit_text(
                f"✅ **Withdrawal {wid} has been approved and marked as PAID!**",
                parse_mode=ParseMode.MARKDOWN,
            )
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=res["user_id"],
                    text=(
                        f"🎉 **আপনার উইথড্র পেমেন্ট সফলভাবে সম্পন্ন হয়েছে!**\n\n"
                        f"• **Withdraw ID:** `{wid}`\n"
                        f"• **Amount:** `${res['amount']:.2f}`\n"
                        f"• **Wallet:** `{res['wallet']}`\n"
                        f"• **Status:** Approved & Paid 🟢"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass

            # Notify Payment Channel
            payment_chan = await database.get_setting("payment_channel", "")
            if payment_chan:
                try:
                    await context.bot.send_message(
                        chat_id=payment_chan,
                        text=(
                            f"✅ **Payment Completed Proof**\n\n"
                            f"• W-ID: `{wid}`\n"
                            f"• User ID: `{res['user_id']}`\n"
                            f"• Amount: `${res['amount']:.2f}`\n"
                            f"• Status: Paid"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass
        return True

    if data.startswith("wd_rej_"):
        wid = data.replace("wd_rej_", "")
        res = await database.update_withdrawal_status(
            wid, status="rejected", admin_note="Rejected and refunded"
        )
        if res:
            await query.answer("Withdrawal rejected & refunded!")
            await query.message.edit_text(
                f"❌ **Withdrawal {wid} was rejected. Balance has been refunded to the user.**",
                parse_mode=ParseMode.MARKDOWN,
            )
            try:
                await context.bot.send_message(
                    chat_id=res["user_id"],
                    text=(
                        f"⚠️ **আপনার উইথড্র রিকোয়েস্ট বাতিল করা হয়েছে!**\n\n"
                        f"• **Withdraw ID:** `{wid}`\n"
                        f"• **Amount:** `${res['amount']:.2f}`\n"
                        f"অর্থ আপনার বটের মূল ব্যালেন্সে রিফান্ড করা হয়েছে।"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
        return True

    return False
