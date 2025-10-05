# Price Tracker Telegram Bot

This project is a Telegram bot that allows users to track product prices from Amazon and Flipkart. Users can provide links to products, and the bot will scrape the current prices, notify users of any changes, and poll the product pages every 10 minutes.

## Features

- Track prices for Amazon and Flipkart products
- Get notified on price drops
- Manage tracked products easily
- Rate limiting to prevent spam
- Cron-based polling for price updates

## Project Structure

```
PriceTracker/
├── app.py            # Main entry point of the application
├── notifier.py       # Sends notifications to users on price changes
├── poller.py         # Polls product pages for price changes
├── requirements.txt  # Lists project dependencies
├── .env              # Contains environment variables (API keys, tokens)
├── README.md         # Documentation for the project
├── utils/            # Scraper and helper modules
└── logs/             # Debug HTML logs
```

## Getting Started

1. **Clone the repository:**

   ```
   git clone <repository-url>
   cd PriceTracker
   ```

2. **Install dependencies:**

   ```
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the root directory and add your API keys and tokens:

   ```
   BOT_TOKEN=your_telegram_bot_token
   DATABASE_URL=your_database_url
   REDIS_URL=your_redis_url
   ```

4. **Run the application:**

   ```
   python app.py
   ```

5. **Set up polling (optional):**
   To poll every 10 minutes, add this to your crontab (`crontab -e`):

   ```
   */10 * * * * cd /home/ec2-user/PriceTracker && ~/PriceTracker/venv/bin/python poller.py >> poller.log 2>&1
   ```

## Bot Commands

- `/start` — Show welcome/help message
- `/help` — Show usage instructions
- `/list` — List your tracked products
- Send a product link to start tracking
- Use the "Stop Tracking" button to remove a product

## Technical Notes

- **Connection Pooling:** Uses SQLAlchemy's connection pooling for efficient DB access.
- **Anti-bot Measures:** Uses Playwright with anti-detection techniques to mimic real browser behavior.
- **Rate Limiting:** Per-user rate limiting using Redis.
- **Polling:** `poller.py` can be run via cron for regular price checks.

## Security

- Never commit your `.env` file
- Keep your bot token and DB credentials secret
- Validate user input to prevent abuse

## Troubleshooting

- If Playwright fails, ensure all system dependencies are installed and run `python -m playwright install`.
- If you see rate limit errors, wait a minute before retrying.
- Check `poller.log` for polling errors.

## Contributing

Pull requests and issues are welcome!

## License

MIT
