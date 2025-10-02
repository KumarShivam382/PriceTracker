import os
import asyncio
from datetime import datetime
from notifier import send_price_notification_card
from models import Session, User, Product

async def check_and_update_price(product, old_price):
    # product: Product instance
    # old_price: previous price (str)
    if "amazon" in product.product_url:
        from utils.amazon import extract_amazon_price
        # Fetch HTML and extract price (implement as needed)
        # new_price = await extract_amazon_price(html)
        new_price = None  # Replace with actual fetch logic
    elif "flipkart" in product.product_url:
        from utils.flipkart import extract_flipkart_price
        # Fetch HTML and extract price (implement as needed)
        # new_price = await extract_flipkart_price(html)
        new_price = None  # Replace with actual fetch logic
    else:
        return

    if new_price and new_price != old_price:
        session = Session()
        try:
            db_product = session.query(Product).filter_by(id=product.id).first()
            if db_product:
                db_product.last_known_price = new_price
                db_product.last_checked = datetime.utcnow()
                session.commit()
                # Notify all users tracking this product
                for user in db_product.users:
                    await send_price_notification_card(
                        bot=None,  # Pass your bot instance here
                        chat_id=user.telegram_id,
                        product_url=db_product.product_url,
                        price=new_price,
                        product_id=db_product.product_id,
                        product_name=None
                    )
        except Exception as e:
            print(f"❌ DB update error: {e}")
            session.rollback()
        finally:
            session.close()

async def poll_price_changes():
    while True:
        session = Session()
        try:
            products = session.query(Product).all()
        finally:
            session.close()
        # You need to store old prices somewhere or fetch them before update
        # Example: for product in products: await check_and_update_price(product, product.last_known_price)
        await asyncio.sleep(1200)  # Wait for 20 mins

if __name__ == "__main__":
    asyncio.run(poll_price_changes())