import os
import httpx
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from google import generativeai as genai

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")


def generate_response_from_html(html_content):
    prompt = f"""
You are a price and title extractor assistant from link . Extract the product's name and price from the HTML below.
Respond in this format:
{{"title": , "price": }}

HTML:
{html_content[:4000]}
"""
    response = gemini_model.generate_content(prompt)
    return response.text


def generate_response_from_link(link):
    prompt = f"""
You are a price and title extractor assistant from link . Extract the product's name and price from the given link below.
Respond in this format:
{{"title": , "price": }} and the link is {link}"""

    response = gemini_model.generate_content(prompt)
    return response.text


async def scrapper(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except Exception as e:
        print(" HTTP error:", e)
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    return soup.prettify()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    print(user_input)

    direct_message = generate_response_from_link(user_input)
    print(direct_message)

    if user_input.startswith("http://") or user_input.startswith("https://"):
        html_content = await scrapper(user_input)
        if not html_content:
            await update.message.reply_text(" Failed to fetch or parse the webpage.")
            return

        extracted_info = generate_response_from_html(html_content)
        await update.message.reply_text(f" Product Info:\n{extracted_info}")
    else:
        reply = gemini_model.generate_content(user_input)
        await update.message.reply_text(f" {reply.text}")


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(" Gemini-powered telegram bot is running!")
    app.run_polling()
