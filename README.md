# Price Tracker

This project is a Telegram bot that allows users to track product prices from Amazon and Flipkart. Users can provide links to products, and the bot will scrape the current prices, notify users of any changes, and poll the product pages every hour.

## Project Structure

```
price-tracker
├── app.py            # Main entry point of the application
├── extractor.py      # Functions for extracting product information
├── notifier.py       # Sends notifications to users on price changes
├── poller.py         # Polls product pages every hour for price changes
├── requirements.txt   # Lists project dependencies
├── .env              # Contains environment variables (API keys, tokens)
├── README.md         # Documentation for the project
└── utils
    ├── amazon.py     # Utility functions for scraping Amazon
    ├── flipkart.py    # Utility functions for scraping Flipkart
    └── __init__.py   # Marks the utils directory as a Python package
```

## Setup Instructions

1. **Clone the repository:**

   ```
   git clone <repository-url>
   cd price-tracker
   ```

2. **Install dependencies:**
   Make sure you have Python installed. Then, run:

   ```
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the root directory and add your API keys and tokens:

   ```
   BOT_TOKEN=<your-telegram-bot-token>
   GEMINI_API_KEY=<your-gemini-api-key>
   ```

4. **Run the application:**
   Start the bot by running:
   ```
   python app.py
   ```

## Usage

- Send a message to the bot with a product link from Amazon or Flipkart.
- The bot will scrape the product information and notify you of the current price.
- If the price changes, you will receive a notification.

## Contributing

Feel free to submit issues or pull requests if you have suggestions or improvements for the project.

Issues faced/facing :
mimicking a real browser
Currently working with flipkart and amazon urls only
