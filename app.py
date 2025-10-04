from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters
from handlers import handle_message, stop_tracking_callback
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(stop_tracking_callback, pattern=r"^stop_"))
    print("🤖 Price Tracker Telegram bot is running!")
    app.run_polling()