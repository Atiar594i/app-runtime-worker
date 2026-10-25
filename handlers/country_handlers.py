from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database


def get_country_detail_keyboard(country: dict):
    cid = country["id"]
    status_str = "🟢 Active" if country.get("status", 1) else "🔴 Inactive"
    prem_str = "⭐ ON" if country.get("premium_only") else "⚪ OFF"
    spam_str = "✅ YES" if country.get("accept_spam", 1) else "❌ NO"
    email_str = "📧 ON" if country.get("login_email") else "⚪ OFF"

    keyboard = [
        [
            InlineKeyboardButton(
                f"Status: {status_str}", callback_data=f"c_toggle_status_{cid}"
            ),
            InlineKeyboardButton(
                f"Premium Only: {prem_str}",
                callback_data=f"c_toggle_prem_{cid}",
            ),
        ],
        [
            InlineKeyboardButton(
                f"Accept Spam: {spam_str}",
                callback_data=f"c_toggle_spam_{cid}",
            ),
            InlineKeyboardButton(
                f"Login Email: {email_str}",
                callback_data=f"c_toggle_email_{cid}",
            ),
        ],
        [
            InlineKeyboardButton(
                "✏️ Edit Prices", callback_data=f"c_edit_prices_{cid}"
            ),
            InlineKeyboardButton(
                "✏️ Edit Capacity", callback_data=f"c_edit_cap_{cid}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🗑 Delete Country", callback_data=f"c_del_{cid}"
            ),
            InlineKeyboardButton(
                "🔙 Back to Countries", callback_data="adm_countries"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_countries_list(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query:
        await query.answer()

    countries = await database.get_all_countries()
    buttons = []
    for c in countries:
        st = "🟢" if c.get("status", 1) else "🔴"
        btn_text = f"{st} {c['name']} ({c['dial_code']}) [{c['used_capacity']}/{c['capacity']}]"
        buttons.append(
            [InlineKeyboardButton(btn_text, callback_data=f"c_view_{c['id']}")]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "➕ Add New Country", callback_data="c_add_start"
            )
        ]
    )
    buttons.append(
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_main")]
    )

    text = (
        "🌍 **Country Settings & Configuration**\n\n"
        "যেকোনো দেশের উপর ক্লিক করে তার রেট, স্ট্যাটাস ও রুলস পরিবর্তন করতে পারবেন।\n"
        "Click any country to manage prices, capacity, and toggles:"
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


async def show_country_details(
    update: Update, context: ContextTypes.DEFAULT_TYPE, country_id: int
):
    query = update.callback_query
    if query:
        await query.answer()

    c = await database.get_country_by_id(country_id)
    if not c:
        if query:
            await query.message.reply_text("Country not found.")
        return

    text = (
        f"🌍 **Country Details: {c['name']}**\n\n"
        f"• **Dial Code:** `{c['dial_code']}`\n"
        f"• **Capacity:** `{c['used_capacity']}/{c['capacity']}`\n"
        f"• **Main Price (Free):** `${c['main_price']:.2f}`\n"
        f"• **Spam Acc Price:** `${c['spam_price']:.2f}`\n"
        f"• **New Acc Price:** `${c['new_acc_price']:.2f}`\n"
        f"• **Confirm Time:** `{c['confirm_time']}s`\n"
        f"• **Status:** {'🟢 Active' if c.get('status', 1) else '🔴 Inactive'}\n"
        f"• **Premium Only:** {'Yes' if c.get('premium_only') else 'No'}\n"
        f"• **Accept Spam:** {'Yes' if c.get('accept_spam', 1) else 'No'}\n"
        f"• **Login Email:** {'Yes' if c.get('login_email') else 'No'}"
    )

    keyboard = get_country_detail_keyboard(c)
    if query:
        await query.message.edit_text(
            text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN
        )


async def handle_country_callbacks(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    query = update.callback_query
    data = query.data

    if data == "adm_countries":
        await show_countries_list(update, context)
        return True

    if data.startswith("c_view_"):
        cid = int(data.split("_")[2])
        await show_country_details(update, context, cid)
        return True

    if data.startswith("c_toggle_status_"):
        cid = int(data.split("_")[3])
        c = await database.get_country_by_id(cid)
        if c:
            new_st = 0 if c.get("status", 1) else 1
            await database.update_country(cid, status=new_st)
            await show_country_details(update, context, cid)
        return True

    if data.startswith("c_toggle_prem_"):
        cid = int(data.split("_")[3])
        c = await database.get_country_by_id(cid)
        if c:
            new_pr = 0 if c.get("premium_only") else 1
            await database.update_country(cid, premium_only=new_pr)
            await show_country_details(update, context, cid)
        return True

    if data.startswith("c_toggle_spam_"):
        cid = int(data.split("_")[3])
        c = await database.get_country_by_id(cid)
        if c:
            new_sp = 0 if c.get("accept_spam", 1) else 1
            await database.update_country(cid, accept_spam=new_sp)
            await show_country_details(update, context, cid)
        return True

    if data.startswith("c_toggle_email_"):
        cid = int(data.split("_")[3])
        c = await database.get_country_by_id(cid)
        if c:
            new_em = 0 if c.get("login_email") else 1
            await database.update_country(cid, login_email=new_em)
            await show_country_details(update, context, cid)
        return True

    if data.startswith("c_edit_prices_"):
        cid = int(data.split("_")[3])
        context.user_data["adm_state"] = f"waiting_prices_{cid}"
        await query.message.reply_text(
            "✏️ নতুন প্রাইস লিখে পাঠান (Format: `Main Spam NewAcc`)\n"
            "👉 উদাহরণ: `0.80 0.40 0.60`\n"
            "Send 3 numbers separated by spaces:",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data.startswith("c_edit_cap_"):
        cid = int(data.split("_")[3])
        context.user_data["adm_state"] = f"waiting_cap_{cid}"
        await query.message.reply_text(
            "✏️ নতুন ক্যাপাসিটি সংখ্যা লিখুন (Enter new capacity number, e.g. `200`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    if data.startswith("c_del_"):
        cid = int(data.split("_")[2])
        await database.delete_country(cid)
        await query.answer("Country deleted successfully!")
        await show_countries_list(update, context)
        return True

    # Wizard for adding new country
    if data == "c_add_start":
        context.user_data["adm_state"] = "c_add_name"
        context.user_data["c_add_data"] = {}
        await query.message.reply_text(
            "➕ **নতুন দেশ যুক্ত করুন (Step 1/5):**\n\n"
            "দেশের নাম লিখুন (Enter Country Name, e.g. `Nigeria`):",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    return False
