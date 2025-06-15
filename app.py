# main.py

import os
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai
from extractor import extract_candidate_blocks

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")


def generate_response_from_html(html_block):
    prompt = f"""You are a product info extractor assistant.
Extract the most probable product title and price from the HTML snippet below.
Format:
{{"title": ..., "price": ...}}
HTML Snippet:
{html_block}
"""
    return gemini_model.generate_content(prompt).text


async def scrapper(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            return r.text, str(r.url)  # enlarged url;
    except Exception as e:
        print("❌ Error fetching page:", e)
        return None, None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()

    if user_input.startswith("http://") or user_input.startswith("https://"):
        html, final_url = await scrapper(user_input)
        if not html:
            await update.message.reply_text("❌ Failed to fetch or parse the webpage.")
            return

        domain = urlparse(final_url).netloc.replace("www.", "")
        soup = BeautifulSoup(html, "html.parser")
        snippet = extract_candidate_blocks(soup, domain)

        if not snippet:
            await update.message.reply_text(
                "❌ Couldn't find title or price in the page."
            )
            return

        extracted_info = generate_response_from_html(snippet)
        await update.message.reply_text(f"🔍 Product Info:\n{extracted_info}")

    else:
        reply = gemini_model.generate_content(user_input)
        await update.message.reply_text(reply.text)


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Gemini-powered Telegram bot is running!")
    app.run_polling()
