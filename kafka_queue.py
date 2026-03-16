"""
Kafka-based message queue for decoupling price polling from notifications.

The poller produces price-change events to a Kafka topic.
The notification worker consumes them and sends Telegram messages.

Benefits over plain polling+notify in one loop:
- Poller and notifier scale independently
- At-least-once delivery with consumer group offsets
- Backpressure: if notifications are slow, polling isn't blocked
- Easy to add more consumers (email, webhook, analytics, etc.)
"""

import os
import json
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "price_changes")
CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "notifier-group")

async def get_producer() -> AIOKafkaProducer:
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    return producer


async def publish_price_change(producer: AIOKafkaProducer, event: dict):
    """Publish a price-change event to Kafka.

    event keys: product_id, product_url, product_name,
                old_price, new_price, user_telegram_ids
    """
    await producer.send_and_wait(TOPIC, value=event)
    logger.info("Published price change for product %s", event.get("product_id"))


async def get_consumer() -> AIOKafkaConsumer:
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=CONSUMER_GROUP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    return consumer
