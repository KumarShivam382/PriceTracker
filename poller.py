import os
import time
import asyncio
from datetime import datetime, timedelta
from utils.amazon import get_amazon_price
from utils.flipkart import get_flipkart_price
from notifier import send_price_notification

class PriceTracker:
    def __init__(self, user_id, product_url, initial_price):
        self.user_id = user_id
        self.product_url = product_url
        self.initial_price = initial_price
        self.current_price = initial_price

    async def check_price(self):
        if "amazon" in self.product_url:
            self.current_price = await get_amazon_price(self.product_url)
        elif "flipkart" in self.product_url:
            self.current_price = await get_flipkart_price(self.product_url)

    async def notify_if_price_changed(self):
        await self.check_price()
        if self.current_price < self.initial_price:
            await send_price_notification(self.user_id, self.product_url, self.current_price)
            self.initial_price = self.current_price

async def poll_price_changes(tracked_products):
    while True:
        for tracker in tracked_products:
            await tracker.notify_if_price_changed()
        await asyncio.sleep(3600)  # Wait for 1 hour

if __name__ == "__main__":
    tracked_products = []
    # Example: Add a product to track (user_id, product_url, initial_price)
    tracked_products.append(PriceTracker(user_id="12345", product_url="https://www.amazon.com/example-product", initial_price=100.00))
    tracked_products.append(PriceTracker(user_id="12345", product_url="https://www.flipkart.com/example-product", initial_price=200.00))

    asyncio.run(poll_price_changes(tracked_products))