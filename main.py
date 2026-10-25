import logging
import html
import json
import traceback
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

import config
import database
from handlers.user_handlers import (
    start_command,
    cancel_command,
    capacity_command,
    balance_command,
    help_command,
    handle_withdraw_click,
    handle_withdraw_history_click,
    handle_user_text_message,
)
from handlers.admin_handlers import (
    admin_command,
    admin_callback_router,
    handle_admin_text_inputs,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Logs the error and sends a notice to the configured error channel."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb_string = "".join(tb_list)

    error_channel = await database.get_setting("error_channel", "")
    if error_channel:
        try:
            update_str = (
                update.to_dict()
                if isinstance(update, Update)
                else str(update)
            )
            message = (
                f"⚠️ **An exception occurred in Bot!**\n\n"
                f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False)[:400])}</pre>\n\n"
                f"<pre>{html.escape(tb_string[-800:])}</pre>"
            )
            await context.bot.send_message(
                chat_id=error_channel,
                text=message,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.error(f"Failed to send error notification to channel: {e}")


async def general_callback_router(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Central callback query router for user and admin buttons."""
    query = update.callback_query
    data = query.data

    # User main buttons
    if data == "btn_capacity":
        await capacity_command(update, context)
        return
    elif data == "btn_balance":
        await balance_command(update, context)
        return
    elif data == "btn_help":
        await help_command(update, context)
        return
    elif data == "btn_cancel":
        await cancel_command(update, context)
        return
    elif data == "btn_withdraw":
        await handle_withdraw_click(update, context)
        return
    elif data == "btn_withdraw_history":
        await handle_withdraw_history_click(update, context)
        return
    elif data == "check_join":
        await query.answer("Checking membership...")
        await start_command(update, context)
        return

    # Admin buttons
    await admin_callback_router(update, context)


async def unified_text_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Dispatches text messages to admin state processor or user processor."""
    user = update.effective_user
    if not user or not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    is_admin = await database.is_admin(user.id)

    # Handle persistent reply keyboard clicks (docked at the bottom)
    if "Admin Panel" in text:
        if is_admin:
            await admin_command(update, context)
            return
    elif "Devices" in text:
        if is_admin:
            from handlers.tech_handlers import show_device_menu

            await show_device_menu(update, context)
            return
    elif "Admin Add Number" in text:
        if is_admin:
            await update.message.reply_text(
                "📲 **অ্যাডমিন নম্বর যোগ করুন (Admin Add Number):**\n\n"
                "কান্ট্রি কোডসহ যেকোনো মোবাইল নম্বর চ্যাটে পাঠান:\n"
                "👉 উদাহরণ: `+8801700000000` অথবা `+12025550123`\n\n"
                "নম্বর পাঠানোর পর ওটিপি কোড চাওয়া হবে। বাতিল করতে /cancel চাপুন।",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
    elif "Capacity" in text:
        await capacity_command(update, context)
        return
    elif "Balance" in text:
        await balance_command(update, context)
        return
    elif "Help" in text:
        await help_command(update, context)
        return
    elif "Cancel" in text:
        await cancel_command(update, context)
        return

    # If admin and has active admin wizard state
    if is_admin and context.user_data.get("adm_state"):
        handled = await handle_admin_text_inputs(update, context)
        if handled:
            return

    # Otherwise route to standard user handler (numbers, OTP, withdrawals)
    await handle_user_text_message(update, context)


async def post_init(application):
    """Runs after application is built: initializes database and prints banner."""
    await database.init_db()
    print("=" * 60)
    print("[*] Telegram Account & Session Receiver Bot Started Successfully!")
    print(f"[*] Sessions Directory: {config.SESSIONS_DIR}")
    print(f"[*] Database Path: {config.DB_PATH}")
    print("[*] Default Admin IDs:", config.ADMIN_IDS)
    print("=" * 60)

    # Start continuous background monitor for session revocation / logouts
    import asyncio
    from handlers.tech_handlers import run_session_revocation_monitor
    asyncio.create_task(run_session_revocation_monitor(application.bot))


def start_dummy_health_server():
    """Starts a minimal HTTP health-check server for Render / cloud hosts."""
    port_str = os.environ.get("PORT")
    if not port_str:
        return
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading

        port = int(port_str)

        class HealthCheckHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Bot is healthy and running.")

            def log_message(self, format, *args):
                pass

        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"[*] Started cloud health check HTTP server on port {port}")
    except Exception as e:
        print(f"[!] Health check server warning: {e}")


def main():
    start_dummy_health_server()
    if not config.BOT_TOKEN or config.BOT_TOKEN.startswith("1234567890:"):
        print("\n" + "!" * 60)
        print("[!] BOT_TOKEN is not set or using placeholder!")
        print("Please edit .env and set your real BOT_TOKEN from @BotFather:")
        print("BOT_TOKEN=your_bot_token_here")
        print("ADMIN_IDS=your_telegram_id_here")
        print("!" * 60 + "\n")
        return

    app = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("capacity", capacity_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin_command))

    # Callback Query Handler
    app.add_handler(CallbackQueryHandler(general_callback_router))

    # Unified Message Handler for phone numbers, OTP, 2FA, and inputs
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND, unified_text_message_handler
        )
    )

    # Global Error Handler
    app.add_error_handler(error_handler)

    print("[*] Bot polling started... Press Ctrl+C to terminate.")
    app.run_polling()


if __name__ == "__main__":
    main()
