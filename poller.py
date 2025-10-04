import os
import asyncio
import random
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from notifier import send_price_notification_card
from models import User, Product
from db import Session

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def check_and_update_price(product, old_price):
    # product: Product instance
    # old_price: previous price (str)
    print(f"  📋 Current price: {old_price}")
    
    if "amazon" in product.product_url:
        from utils.scraper import scrapper
        from utils.amazon import extract_amazon_price_and_name
        try:
            html, final_url = await scrapper(product.product_url)
            if html:
                new_price, _ = await extract_amazon_price_and_name(html)
                print(f"  💰 New Amazon price: {new_price}")
            else:
                print(f"  ❌ Failed to fetch Amazon page")
                new_price = None
        except Exception as e:
            print(f"  ❌ Error fetching Amazon price: {e}")
            new_price = None
    elif "flipkart" in product.product_url:
        from utils.scraper import scrapper
        from utils.flipkart import extract_flipkart_price_and_name
        try:
            html, final_url = await scrapper(product.product_url)
            if html:
                new_price, _ = await extract_flipkart_price_and_name(html)
                print(f"  💰 New Flipkart price: {new_price}")
            else:
                print(f"  ❌ Failed to fetch Flipkart page")
                new_price = None
        except Exception as e:
            print(f"  ❌ Error fetching Flipkart price: {e}")
            new_price = None
    else:
        print(f"  ⚠️  Unsupported domain: {product.product_url}")
        return

    if new_price and new_price != old_price:
        session = Session()
        try:
            db_product = session.query(Product).filter_by(id=product.id).first()
            if db_product:
                db_product.last_known_price = new_price
                db_product.last_checked = datetime.utcnow()
                session.commit()
                
                print(f"  📢 Price changed! Old: {old_price} → New: {new_price}")
                
                # Create bot instance for notifications
                if BOT_TOKEN:
                    bot = Bot(token=BOT_TOKEN)
                    print(f"  👥 Notifying {len(db_product.users)} users")
                    for user in db_product.users:
                        try:
                            await send_price_notification_card(
                                bot=bot,
                                chat_id=user.telegram_id,
                                product_url=db_product.product_url,
                                price=new_price,
                                product_id=db_product.product_id,
                                product_name=db_product.product_name,
                                old_price=old_price
                            )
                            print(f"  ✅ Notified user {user.telegram_id}")
                        except Exception as e:
                            print(f"  ❌ Failed to notify user {user.telegram_id}: {e}")
                else:
                    print(f"  ⚠️  BOT_TOKEN not found, cannot send notifications")
        except Exception as e:
            print(f"❌ DB update error: {e}")
            session.rollback()
        finally:
            session.close()
    elif new_price:
        print(f"  ℹ️  No price change detected")
    else:
        print(f"  ❌ Could not fetch new price")

def run_poll_once():
    """Run a single poll cycle for cron or scheduler."""
    import asyncio
    print(f"🕐 Starting price check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    session = Session()
    try:
        products = session.query(Product).all()
        print(f"📊 Found {len(products)} products to check")
    finally:
        session.close()
    
    # Run all price checks sequentially (could be parallelized if needed)
    async def run_checks():
        for i, product in enumerate(products, 1):
            print(f"🔍 Checking product {i}/{len(products)}: {product.product_id} - {product.product_name or 'Unknown'}")
            await check_and_update_price(product, product.last_known_price)
    
    asyncio.run(run_checks())
    print(f"✅ Price check completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    run_poll_once()