import os
import logging
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
import aioredis
import time
import re
import asyncio

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT = 10  # requests
RATE_LIMIT_WINDOW = 60  # seconds

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show welcome message and instructions."""
    welcome_text = """
🤖 **Welcome to the Price Tracker Bot!**

I help you track prices for Amazon and Flipkart products and notify you when prices drop.

**How to use:**
1. Send me a product link (Amazon or Flipkart)
2. I'll track the price and show you a product card
3. Get notified when the price changes
4. Use the "Stop Tracking" button to remove products

**Commands:**
/start - Show this welcome message
/help - Get detailed help
/list - See your tracked products
/stats - View your statistics
/clear - Remove all tracked products

**Rate Limits:**
You can track up to 10 products per minute.

Just send me a product link to get started! 🛍️
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - show detailed usage instructions."""
    help_text = """
📖 **Price Tracker Bot Help**

**Supported Sites:**
• Amazon (amazon.in, amazon.com, etc.)
• Flipkart (flipkart.com)

**How it works:**
1. Send a product link
2. I'll extract the price and product info
3. You'll get a product card with current price
4. I check prices every 10 minutes
5. You get notified of any price changes

**Commands:**
• `/start` - Welcome message
• `/help` - This help text
• `/list` - Your tracked products
• `/stats` - View your statistics
• `/clear` - Remove all tracked products

**Features:**
• Real-time price extraction
• Automatic price monitoring
• Price change notifications
• Easy product management

**Tips:**
• Make sure links are from supported sites (amazon and flipkart only for now)
• You can track multiple products
• Use "Stop Tracking" button to remove products
• Rate limited to prevent spam (10 requests/minute)

Need more help? Just mail to skshivamkumar382@gmail.com ! 💬
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command - show user's tracked products."""
    telegram_id = update.effective_user.id
    
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user or not user.tracked_products:
            await update.message.reply_text("📭 You're not tracking any products yet.\n\nSend me a product link to start tracking!")
            return
        
        products_text = f"📋 **Your Tracked Products** ({len(user.tracked_products)} items)\n\n"
        
        for i, product in enumerate(user.tracked_products, 1):
            price_info = f"💰 {product.last_known_price}" if product.last_known_price else "❓ Price not available"
            product_name = product.product_name[:50] + "..." if product.product_name and len(product.product_name) > 50 else product.product_name or "Unknown Product"
            
            products_text += f"{i}. **{product_name}**\n"
            products_text += f"   {price_info}\n"
            products_text += f"   🔗 [View Product]({product.product_url})\n\n"
        
        products_text += "To stop tracking a product, use the 'Stop Tracking' button on its product card."
        
        await update.message.reply_text(products_text, parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"❌ Error in list command: {e}")
        await update.message.reply_text("❌ Sorry, I couldn't fetch your tracked products. Please try again later.")
    finally:
        session.close()

async def is_rate_limited(user_id):
    redis = await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    key = f"rate_limit:{user_id}"
    now = int(time.time())
    await redis.zremrangebyscore(key, 0, now - RATE_LIMIT_WINDOW)
    count = await redis.zcard(key)
    limited = count >= RATE_LIMIT
    if not limited:
        await redis.zadd(key, {str(now): now})
        await redis.expire(key, RATE_LIMIT_WINDOW)
    await redis.close()
    return limited, count

# def save_html_for_debug(url: str, html: str):
#     """Save HTML to debug file in logs folder"""
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
#     logs_dir = "logs"
#     os.makedirs(logs_dir, exist_ok=True)
#     filename = os.path.join(logs_dir, f"debug_{domain}_{timestamp}.html")
#     with open(filename, "w", encoding="utf-8") as f:
#         f.write(html)
#     logger.info(f"🐛 HTML saved to: {filename}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_input = update.message.text.strip()
        telegram_id = update.effective_user.id
        username = update.effective_user.username

        logger.info(f"User {telegram_id} sent message: {user_input[:100]}...")

        # --- Redis Rate limiting logic ---
        try:
            limited, user_rate = await is_rate_limited(telegram_id)
            logger.info(f"User {telegram_id} has made {user_rate} requests in the last {RATE_LIMIT_WINDOW} seconds.")
            if limited:
                await update.message.reply_text(f"🚫 Rate limit exceeded. You made {user_rate} requests in the last minute. Please wait before trying again.")
                return
        except Exception as e:
            logger.error(f"Rate limiting error for user {telegram_id}: {e}")
            await update.message.reply_text("❌ Unable to process request. Please try again later.")
            return
        # --- End rate limiting ---
        
        if user_input.startswith("http://") or user_input.startswith("https://"):
                
            loading_msg = await update.message.reply_text("🔍 Validating URL...")

            # Expand the URL before scraping with timeout
            try:
                await loading_msg.edit_text("🌐 Resolving short links if present...")
                # Extract the first URL from the user message (commonly used)
                # Extract URL starting at first http(s) and cut at first space
                http_idx = user_input.find("http")
                if http_idx != -1:
                    space_idx = user_input.find(" ", http_idx)
                    if space_idx == -1:
                        url_to_expand = user_input[http_idx:]
                    else:
                        url_to_expand = user_input[http_idx:space_idx]

                    # Strip surrounding whitespace and common punctuation
                    url_to_expand = url_to_expand.strip().rstrip('.,;:!?)\"\'')
                    url_to_expand = url_to_expand.lstrip('(<"\'')
                    logger.info(f"Extracted URL to expand from message: {url_to_expand}")
                else:
                    await loading_msg.edit_text("❌ No valid URL found in the message. Please send a proper product link.")
                    return

                # Add total timeout wrapper for the entire scraping process
                expanded_url = await asyncio.wait_for(expand_url(url_to_expand), timeout=12.0)
                logger.info(f"Expanded URL: {expanded_url}")

                await loading_msg.edit_text("📄 Loading product page...")
                html, final_url = await asyncio.wait_for(scrapper(expanded_url), timeout=15.0)
                logger.info(f"Fetched URL: {final_url}")

                if not html:
                    await loading_msg.edit_text("❌ Failed to load the webpage. The site might be blocking requests or taking too long.")
                    return

                # save_html_for_debug(final_url, html)
            except asyncio.TimeoutError:
                logger.error(f"Timeout while processing URL {user_input}")
                await loading_msg.edit_text("⏰ Request timed out. The website is taking too long to respond. Please try again later.")
                return
            except Exception as e:
                logger.error(f"Error expanding/scraping URL {user_input}: {e}")
                await loading_msg.edit_text("❌ Failed to access the webpage. Please check the URL and try again.")
                return

            domain = urlparse(final_url).netloc.replace("www.", "")
            price = None
            product_id = None
            product_name = None

            try:
                if "amazon" in domain:
                    print("Detected Amazon URL")
                    await loading_msg.edit_text("🛒 Extracting Amazon product details...")
                    price, product_name = await extract_amazon_price_and_name(html)
                    product_id = await extract_amazon_asin(final_url)
                elif "flipkart" in domain:
                    print("Detected Flipkart URL")
                    await loading_msg.edit_text("🛍️ Extracting Flipkart product details...")
                    price, product_name = await extract_flipkart_price_and_name(html)
                    product_id = await extract_flipkart_pid(final_url)
                else:
                    await loading_msg.edit_text("❌ Unsupported website. Please use Amazon or Flipkart product links.")
                    return
            except Exception as e:
                logger.error(f"Error extracting price/product info: {e}")
                await loading_msg.edit_text("❌ Failed to extract product information. Please try again later.")
                return

            # --- Store user and product in DB ---
            try:
                await loading_msg.edit_text("💾 Saving to database...")
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
                    logger.info(f"Product already tracked for user {telegram_id}: {product_id}")
                    await loading_msg.edit_text("ℹ️ This product is already being tracked.")
                    await send_price_card(
                        bot=context.bot,
                        chat_id=update.effective_chat.id,
                        product_url=final_url,
                        price=price,
                        product_id=product_id,
                        product_name=product_name
                    )
                    return
                else:
                    user.tracked_products.append(product)
                    session.commit()
                    logger.info(f"✅ Saved to DB: User {telegram_id}, Price {price}, Product ID {product_id}")
            except Exception as db_error:
                logger.error(f"Database error for user {telegram_id}: {db_error}")
                session.rollback()
                await loading_msg.edit_text("❌ Database error. Please try again later.")
                return
            finally:
                session.close()
            # --- End DB logic ---

            if price is not None:
                await loading_msg.edit_text("✅ Creating product card...")
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
                await loading_msg.edit_text("❌ Couldn't find price on this page. The product might be unavailable or the page format changed.")
        else:
            await update.message.reply_text("📝 Please send me a valid product link from Amazon or Flipkart to start tracking!")
    
    except Exception as e:
        logger.error(f"Unexpected error in handle_message for user {update.effective_user.id}: {e}")
        try:
            if 'loading_msg' in locals():
                await loading_msg.edit_text("❌ An unexpected error occurred. Please try again later.")
            else:
                await update.message.reply_text("❌ An unexpected error occurred. Please try again later.")
        except Exception:
            pass  # If even error message fails, don't crash

async def stop_tracking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    if data.startswith("stop_"):
        product_id = data.replace("stop_", "")
        session = Session()

        logger.info(f"Stop tracking request: product_id={product_id}, user_id={user_id}")
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
                    logger.info(f"Cleaned up unused product: {product_id}")
                await query.edit_message_text("🛑 Tracking stopped for this product.")
                logger.info(f"Tracking stopped for product {product_id} by user {user_id}")
            else:
                await query.edit_message_text("❌ Product was not being tracked or already removed.")
                logger.warning(f"Stop tracking failed: product {product_id} not tracked by user {user_id}")
        except Exception as e:
            logger.error(f"Error stopping tracking for user {user_id}, product {product_id}: {e}")
            await query.edit_message_text("❌ Failed to stop tracking due to an error.")
            session.rollback()
        finally:
            session.close()

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show user statistics and system info."""
    telegram_id = update.effective_user.id
    
    session = Session()
    try:
        # Get user stats
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        user_product_count = len(user.tracked_products) if user else 0
        
        # Get system stats
        total_products = session.query(Product).count()
        total_users = session.query(User).count()
        
        # Calculate user's products with valid prices
        products_with_prices = 0
        if user:
            for product in user.tracked_products:
                if product.last_known_price:
                    products_with_prices += 1
        
        stats_text = f"""
📊 **Your Statistics**

👤 **Your Profile:**
• Tracked products: {user_product_count}
• Products with prices: {products_with_prices}
• Member since: {user.created_at.strftime('%B %Y') if user and user.created_at else 'Unknown'}

🌐 **System Stats:**
• Total users: {total_users}
• Total tracked products: {total_products}
• Supported sites: Amazon, Flipkart


Use /list to see your tracked products or /help for more info!
"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error in stats command: {e}")
        await update.message.reply_text("❌ Sorry, I couldn't fetch statistics. Please try again later.")
    finally:
        session.close()

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - remove all tracked products for user."""
    telegram_id = update.effective_user.id
    
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user or not user.tracked_products:
            await update.message.reply_text("📭 You don't have any products to clear!")
            return
        
        product_count = len(user.tracked_products)
        
        # Remove all tracked products for this user
        products_to_check = list(user.tracked_products)
        user.tracked_products.clear()
        session.commit()
        
        # Clean up: Delete products that no longer have any users
        cleaned_products = 0
        for product in products_to_check:
            session.refresh(product)  # Refresh to get updated relationships
            if not product.users:
                session.delete(product)
                cleaned_products += 1
        
        session.commit()
        
        clear_text = f"""
🗑️ **Products Cleared Successfully!**

• Removed {product_count} products from your tracking list
• Cleaned up {cleaned_products} unused products from system

You can start tracking new products by sending me product links.
Use /help if you need assistance!
"""
        
        await update.message.reply_text(clear_text, parse_mode='Markdown')
        logger.info(f"User {telegram_id} cleared {product_count} products, cleaned {cleaned_products} unused products")
        
    except Exception as e:
        logger.error(f"❌ Error in clear command: {e}")
        session.rollback()
        await update.message.reply_text("❌ Sorry, I couldn't clear your products. Please try again later.")
    finally:
        session.close()