import os
import httpx
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
# from notifier import notify_user
# from poller import start_polling
from utils.amazon import extract_amazon_price
from utils.flipkart import extract_flipkart_price

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

def save_html_for_debug(url: str, html: str):
    """Save HTML to debug file in logs folder"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    filename = os.path.join(logs_dir, f"debug_{domain}_{timestamp}.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🐛 HTML saved to: {filename}")

async def scrapper(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            return r.text, str(r.url)
    except Exception as e:
        print("❌ Error fetching page:", e)
        return None, None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loading_msg = await update.message.reply_text("⏳ Loading and extracting price...")
    user_input = update.message.text.strip()

    if user_input.startswith("http://") or user_input.startswith("https://"):
        # Send loading message
        html, final_url = await scrapper(user_input)
        print(f"Fetched URL: {final_url}")
        if not html:
            await loading_msg.edit_text("❌ Failed to fetch or parse the webpage.")
            return

        # Save HTML for debugging in logs folder
        save_html_for_debug(final_url, html)

        domain = urlparse(final_url).netloc.replace("www.", "")
        price = None

        if "amazon" in domain:
            print("Detected Amazon URL")
            price = await extract_amazon_price(html)
        elif "flipkart" in domain:
            print("Detected Flipkart URL")
            price = await extract_flipkart_price(html)

        if price is not None:
            await loading_msg.edit_text(f"🔍 Current Price: {price}")
        else:
            await loading_msg.edit_text("❌ Couldn't find price in the page.")
    else:
        await update.message.reply_text("❌ Please provide a valid product link.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Price Tracker Telegram bot is running!")
    app.run_polling()