import os
import httpx
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Product
from utils.amazon import extract_amazon_price
from utils.flipkart import extract_flipkart_price
from playwright.async_api import async_playwright
import re
from notifier import send_price_card, send_price_notification_card

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
            headless=True,
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
        
        await page.goto(url, timeout=7000, wait_until='domcontentloaded')
        await page.wait_for_timeout(500)  # Minimal delay for dynamic content
        html = await page.content()
        await browser.close()
        return html

async def scrapper(url: str):
    try:
        html = await playwright_fetch(url)
        soup = BeautifulSoup(html, 'lxml')
        return html, url
    except Exception as e:
        print(f"❌ Playwright fetch failed: {e}")
        return None, None

async def expand_url(url: str) -> str:
    """Expand shortened URLs to their final destination."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/119.0.0.0 Safari/537.36"
            )
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(url, headers=headers)
            return str(response.url)

    except httpx.RequestError as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ General error: {e}")
    return url

# Helper functions to extract product IDs

def extract_amazon_asin(url: str) -> str:
    # Robustly extract ASIN from Amazon URLs
    import re
    # Handles /dp/ASIN, /gp/product/ASIN, and ignores query params
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", url)
    if match:
        return match.group(1)
    # Fallback: look for 10-char ASIN in the path
    match = re.search(r"/([A-Z0-9]{10})(?:[/?]|$)", url)
    if match:
        return match.group(1)
    return None

def extract_flipkart_pid(url: str) -> str:
    # Flipkart product ID is usually after 'pid=' in the URL
    match = re.search(r"[?&]pid=([A-Z0-9]+)", url)
    if match:
        return match.group(1)
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loading_msg = await update.message.reply_text("⏳ Loading and extracting price...")
    user_input = update.message.text.strip()
    telegram_id = update.effective_user.id
    username = update.effective_user.username

    if user_input.startswith("http://") or user_input.startswith("https://"):
        # Expand the URL before scraping
        expanded_url = await expand_url(user_input)
        print(f"Expanded URL: {expanded_url}")
        html, final_url = await scrapper(expanded_url)
        print(f"Fetched URL: {final_url}")
        if not html:
            await loading_msg.edit_text("❌ Failed to fetch or parse the webpage.")
            return

        save_html_for_debug(final_url, html)

        domain = urlparse(final_url).netloc.replace("www.", "")
        price = None
        product_id = None

        if "amazon" in domain:
            print("Detected Amazon URL")
            price = await extract_amazon_price(html)
            product_id = extract_amazon_asin(final_url)
        elif "flipkart" in domain:
            print("Detected Flipkart URL")
            price = await extract_flipkart_price(html)
            product_id = extract_flipkart_pid(final_url)

        # --- Store user and product in DB ---
        try:
            session = Session()
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id, username=username)
                session.add(user)
                session.commit()
            if not product_id:
                await loading_msg.edit_text("❌ Could not extract a valid product ID from the link. Please check the URL.")
                return
            # Check if product exists, else create
            product = session.query(Product).filter_by(product_id=product_id).first()
            if not product:
                product = Product(
                    product_id=product_id,
                    product_url=final_url,
                    last_known_price=price
                )
                session.add(product)
                session.commit()
            # Check if user is already tracking this product
            if product in user.tracked_products:
                print(f"ℹ️ Product already tracked for user {telegram_id}: {product_id}")
            else:
                user.tracked_products.append(product)
                session.commit()
                print(f"✅ Saved to DB: User {telegram_id}, Price {price}, Product ID {product_id}")
        except Exception as db_error:
            print(f"❌ Database error: {db_error}")
            session.rollback()
        finally:
            session.close()
        # --- End DB logic ---

        if price is not None:
            # Send card with Buy Now and Stop Tracking buttons
            await send_price_card(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                product_url=final_url,
                price=price,
                product_id=product_id,
                product_name=None  # You can extract product name if needed
            )
            await loading_msg.delete()
        else:
            await loading_msg.edit_text("❌ Couldn't find price in the page.")
    else:
        await update.message.reply_text("❌ Please provide a valid product link.")

async def stop_tracking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    if data.startswith("stop_"):
        product_id = data.replace("stop_", "")
        session = Session()

        print(f"{product_id} is product_id")
        print(f"{user_id} is user_id ")
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            product = session.query(Product).filter_by(product_id=product_id).first()
            if user and product and product in user.tracked_products:
                user.tracked_products.remove(product)
                session.commit()
                # Clean up: If no users are tracking this product, delete the product
                if not product.users:
                    session.delete(product)
                    session.commit()
                await query.edit_message_text("🛑 Tracking stopped for this product.")
                print("Tracking stopped for this product.")
            else:
                await query.edit_message_text("Product was not being tracked or already removed.")
        except Exception as e:
            print(f"❌ Error stopping tracking: {e}")
            await query.edit_message_text("❌ Failed to stop tracking due to an error.")
            session.rollback()
        finally:
            session.close()

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(stop_tracking_callback, pattern=r"^stop_"))
    print("🤖 Price Tracker Telegram bot is running!")
    app.run_polling()