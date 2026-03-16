"""
Kafka consumer that reads price-change events and sends Telegram notifications.

Run as a standalone process:
    python notification_worker.py
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Bot
from kafka_queue import get_consumer
from notifier import send_price_notification_card

load_dotenv()
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def handle_event(bot, event: dict):
    """Send Telegram notifications for a single price-change event."""
    user_ids = event.get("user_telegram_ids", [])
    logger.info(
        "Notifying %d users about %s", len(user_ids), event.get("product_id")
    )

    for tid in user_ids:
        try:
            await send_price_notification_card(
                bot=bot,
                chat_id=tid,
                product_url=event["product_url"],
                price=event["new_price"],
                product_id=event["product_id"],
                product_name=event.get("product_name"),
                old_price=event.get("old_price"),
            )
            logger.info("Notified user %s", tid)
        except Exception as e:
            logger.error("Failed to notify user %s: %s", tid, e)


async def run_consumer():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set — cannot send notifications")
        return

    bot = Bot(token=BOT_TOKEN)
    consumer = await get_consumer()
    logger.info("Notification worker started, listening for price changes…")

    try:
        async for msg in consumer:
            event = msg.value
            await handle_event(bot, event)
    finally:
        await consumer.stop()


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    asyncio.run(run_consumer())


if __name__ == "__main__":
    main()
