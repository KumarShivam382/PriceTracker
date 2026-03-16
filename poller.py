import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from models import Product
from db import Session
from kafka_queue import get_producer, publish_price_change

load_dotenv()
logger = logging.getLogger(__name__)

# Max concurrent scrapes to avoid overwhelming target sites / getting blocked
MAX_CONCURRENT_SCRAPES = int(os.getenv("MAX_CONCURRENT_SCRAPES", "5"))


async def fetch_new_price(product_url: str):
    """Scrape the current price for a product URL. Returns (new_price, product_name) or (None, None)."""
    if "amazon" in product_url:
        from utils.scraper import scrapper
        from utils.amazon import extract_amazon_price_and_name
        html, _ = await scrapper(product_url)
        if html:
            return await extract_amazon_price_and_name(html)
    elif "flipkart" in product_url:
        from utils.scraper import scrapper
        from utils.flipkart import extract_flipkart_price_and_name
        html, _ = await scrapper(product_url)
        if html:
            return await extract_flipkart_price_and_name(html)
    return None, None


def _update_price_in_db(product_db_id, new_price):
    """Synchronous DB update — meant to run in a thread via asyncio.to_thread."""
    session = Session()
    try:
        db_product = session.query(Product).filter_by(id=product_db_id).first()
        if not db_product:
            return None
        db_product.last_known_price = new_price
        db_product.last_checked = datetime.utcnow()
        user_ids = [u.telegram_id for u in db_product.users]
        session.commit()
        return user_ids
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def check_product(semaphore, producer, product_id, product_url,
                        product_name, product_db_id, old_price):
    """Check a single product under the concurrency semaphore.

    On price change → update DB (in thread) and publish event to Kafka.
    """
    async with semaphore:
        logger.info("Checking %s (%s)", product_db_id, product_name or "Unknown")
        try:
            new_price, _ = await fetch_new_price(product_url)
        except Exception as e:
            logger.error("Scrape failed for %s: %s", product_db_id, e)
            return

        if not new_price or new_price == old_price:
            if new_price:
                logger.info("No change for %s", product_db_id)
            else:
                logger.warning("Could not fetch price for %s", product_db_id)
            return

        # --- Price changed: update DB in a thread to avoid blocking the loop ---
        try:
            user_ids = await asyncio.to_thread(
                _update_price_in_db, product_db_id, new_price
            )
            if user_ids is None:
                return
            logger.info("Price changed for %s: %s → %s", product_id, old_price, new_price)
        except Exception as e:
            logger.error("DB error for %s: %s", product_db_id, e)
            return

        # --- Publish to Kafka (notification is the consumer's job) ---
        await publish_price_change(producer, {
            "product_id": product_id,
            "product_url": product_url,
            "product_name": product_name,
            "old_price": old_price,
            "new_price": new_price,
            "user_telegram_ids": user_ids,
        })


async def run_poll_cycle():
    """Run a single poll cycle: fetch all products, check prices concurrently,
    publish changes to Kafka."""
    logger.info("Starting price check at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    session = Session()
    try:
        products = session.query(Product).all()
        # Detach data we need so session can close before async work
        product_data = [
            (p.id, p.product_id, p.product_url, p.product_name, p.last_known_price)
            for p in products
        ]
    finally:
        session.close()

    logger.info("Found %d products to check", len(product_data))

    producer = await get_producer()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)

    tasks = [
        check_product(semaphore, producer, pid, url, name, db_id, price)
        for db_id, pid, url, name, price in product_data
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    await producer.stop()
    logger.info("Price check completed at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def run_poll_once():
    """Entry point for cron / scheduler — runs one poll cycle."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    asyncio.run(run_poll_cycle())


if __name__ == "__main__":
    run_poll_once()