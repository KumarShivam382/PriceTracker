import os
from datetime import datetime
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import ContextTypes
from models import User, Product
from notifier import send_price_card
from utils.amazon import extract_amazon_price_and_name, extract_amazon_asin
from utils.flipkart import extract_flipkart_price_and_name, extract_flipkart_pid
from utils.scraper import scrapper, expand_url
from db import Session  

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
        product_name = None

        if "amazon" in domain:
            print("Detected Amazon URL")
            price, product_name = await extract_amazon_price_and_name(html)
            product_id = extract_amazon_asin(final_url)
        elif "flipkart" in domain:
            print("Detected Flipkart URL")
            price, product_name = await extract_flipkart_price_and_name(html)
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
                    last_known_price=price,
                    product_name=product_name
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
                product_name=product_name
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