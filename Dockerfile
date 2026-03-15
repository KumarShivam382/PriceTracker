FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required by Playwright and psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
        libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
        libpango-1.0-0 libcairo2 libasound2 libxshmfence1 libx11-xcb1 \
        libxfixes3 libpangocairo-1.0-0 libgtk-3-0 libdbus-glib-1-2 \
        libatspi2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

COPY . .

ENTRYPOINT ["./entrypoint.sh"]
