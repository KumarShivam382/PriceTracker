import os
import httpx
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, TrackedProduct
from utils.amazon import extract_amazon_price
from utils.flipkart import extract_flipkart_price
from playwright.async_api import async_playwright

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  
    pool_recycle=300,    
    pool_size=5,         # Connection pool size
    max_overflow=10      
)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

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

async def playwright_fetch(url):
    async with async_playwright() as p:
        # Launch browser with enhanced anti-detection
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--start-minimized'
            ]
        )
        
        # Create context with realistic settings
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Hide automation indicators
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        await page.goto(url, timeout=10000, wait_until='domcontentloaded')
        await page.wait_for_timeout(500)  # Minimal delay for dynamic content
        html = await page.content()
        await browser.close()
        return html

async def scrapper(url: str):
    try:
        html = await playwright_fetch(url)
        return html, url
    except Exception as e:
        print(f"❌ Playwright fetch failed: {e}")
        return None, None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loading_msg = await update.message.reply_text("⏳ Loading and extracting price...")
    user_input = update.message.text.strip()
    telegram_id = update.effective_user.id
    username = update.effective_user.username

    if user_input.startswith("http://") or user_input.startswith("https://"):
        html, final_url = await scrapper(user_input)
        print(f"Fetched URL: {final_url}")
        if not html:
            await loading_msg.edit_text("❌ Failed to fetch or parse the webpage.")
            return

        save_html_for_debug(final_url, html)

        domain = urlparse(final_url).netloc.replace("www.", "")
        price = None

        if "amazon" in domain:
            print("Detected Amazon URL")
            price = await extract_amazon_price(html)
        elif "flipkart" in domain:
            print("Detected Flipkart URL")
            price = await extract_flipkart_price(html)

        # --- Store user and product in DB ---
        try:
            session = Session()
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id, username=username)
                session.add(user)
                session.commit()
            tracked = TrackedProduct(user_id=user.id, product_url=final_url, last_known_price=price)
            session.add(tracked)
            session.commit()
            print(f"✅ Saved to DB: User {telegram_id}, Price {price}")
        except Exception as db_error:
            print(f"❌ Database error: {db_error}")
            session.rollback()
        finally:
            session.close()
        # --- End DB logic ---

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