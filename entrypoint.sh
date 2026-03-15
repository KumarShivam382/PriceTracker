#!/bin/sh
set -e

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Start the bot
echo "Starting Price Tracker bot..."
exec python app.py
