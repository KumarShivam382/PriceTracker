import os
import httpx
from telegram import Update

class Notifier:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.previous_price = None

    async def notify_price_change(self, update: Update, new_price: float):
        if self.previous_price is None:
            self.previous_price = new_price
            return

        if new_price != self.previous_price:
            message = f"💰 Price Alert! The price has changed from {self.previous_price} to {new_price}."
            await update.message.reply_text(message)
            self.previous_price = new_price

    async def send_initial_price(self, update: Update, initial_price: float):
        self.previous_price = initial_price
        await update.message.reply_text(f"🔍 Initial Price: {initial_price}")