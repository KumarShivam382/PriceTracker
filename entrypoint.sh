#!/bin/sh
set -e

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Determine which component to run based on ROLE env var
ROLE="${ROLE:-bot}"

case "$ROLE" in
  bot)
    echo "Starting Price Tracker bot..."
    exec python app.py
    ;;
  poller)
    echo "Starting price poller..."
    exec python poller.py
    ;;
  notifier)
    echo "Starting Kafka notification worker..."
    exec python notification_worker.py
    ;;
  *)
    echo "Unknown ROLE: $ROLE (expected: bot, poller, notifier)"
    exit 1
    ;;
esac
