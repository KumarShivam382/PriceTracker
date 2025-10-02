import os
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def send_price_card(bot, chat_id, product_url, price, product_id, product_name=None):
    from datetime import datetime
    now_str = datetime.now().strftime('%d %b %Y, %H:%M')
    text = f"<b>The Product has Started Tracking!</b>\n\n"
    text += f"☀️ <b>{product_name or 'Product'}</b>\n\n"
    text += f"Current Price: <b>{price}</b>\n\n"
    text += f"<a href='{product_url}'>Click here to open in Amazon!</a>\n\n"
    text += f"⏱ Updated at [ {now_str} ]"

    keyboard = [
        [InlineKeyboardButton("✅ Buy Now", url=product_url)],
        [InlineKeyboardButton("🛑 Stop Tracking", callback_data=f"stop_{product_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="HTML",
        disable_web_page_preview=False
    )

async def send_price_notification_card(bot, chat_id, product_url, price, product_id, product_name=None, old_price=None):
    # Determine if price increased or decreased
    try:
        new_price_val = float(str(price).replace('₹', '').replace(',', '').strip())
        old_price_val = float(str(old_price).replace('₹', '').replace(',', '').strip()) if old_price else None
    except Exception:
        new_price_val = old_price_val = None

    if old_price_val is not None and new_price_val is not None:
        diff = abs(new_price_val - old_price_val)
        diff_str = f"₹{diff:,.0f}"
        if new_price_val < old_price_val:
            change_text = f"<b>🟢 Product Price is decreased by {diff_str}.</b>"
        elif new_price_val > old_price_val:
            change_text = f"<b>🔴 Product Price is increased by {diff_str}.</b>"
        else:
            change_text = f"<b>Price Unchanged:</b> {price}"
    else:
        change_text = f"<b>New Price:</b> {price}"

    text = f"{change_text}\n\n"
    text += f"☀️ <b>{product_name or 'Product'}</b>\n\n"
    if old_price_val is not None and new_price_val is not None and new_price_val != old_price_val:
        text += f"Previous price: <s>₹{old_price_val:,.0f}</s>\n"
        text += f"Current Price: <b>₹{new_price_val:,.0f}</b>\n\n"
    else:
        text += f"Current Price: <b>{price}</b>\n\n"
    text += f"<a href='{product_url}'>Click here to open in Flipkart!</a>"

    keyboard = [
        [InlineKeyboardButton("✅ Buy Now", url=product_url)],
        [InlineKeyboardButton("🛑 Stop Tracking", callback_data=f"stop_{product_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="HTML",
        disable_web_page_preview=False
    )