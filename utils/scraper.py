import re
import os
import logging
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser
import random
import string
import asyncio

logger = logging.getLogger(__name__)

# ── Persistent browser pool ────────────────────────────────────
# Instead of launching a new Chromium per request (~500ms+ overhead),
# we keep ONE browser alive and create lightweight contexts per request.
# The semaphore limits concurrent pages (not browsers).
_browser: Browser | None = None
_browser_lock = asyncio.Lock()
_page_semaphore = asyncio.Semaphore(int(os.getenv("MAX_BROWSER_PAGES", "10")))

BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-blink-features=AutomationControlled',
    '--disable-web-security',
    '--disable-features=VizDisplayCompositor',
    '--disable-dev-shm-usage',
    '--no-first-run',
    '--start-minimized',
]

ANTI_DETECT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""


async def _get_browser() -> Browser:
    """Return the shared browser, launching it once if needed."""
    global _browser
    if _browser and _browser.is_connected():
        return _browser

    async with _browser_lock:
        # Double-check after acquiring lock
        if _browser and _browser.is_connected():
            return _browser
        pw = await async_playwright().start()
        _browser = await pw.chromium.launch(headless=True, args=BROWSER_ARGS)
        logger.info("Launched shared Chromium browser (PID %s)", _browser.process.pid if _browser.process else "?")
        return _browser


async def _fetch_page(url: str, return_final_url: bool = False):
    """Open a page in a fresh context, return (html, final_url).

    Uses the shared browser and limits concurrency via _page_semaphore.
    """
    async with _page_semaphore:
        browser = await _get_browser()
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/119.0.0.0 Safari/537.36',
        )
        try:
            page = await context.new_page()
            await page.add_init_script(ANTI_DETECT_SCRIPT)
            await page.goto(url, timeout=8000, wait_until='commit')
            await page.wait_for_timeout(800)  # Brief delay for dynamic content
            html = await page.content()
            final_url = page.url
            return (html, final_url) if return_final_url else (html, url)
        finally:
            await context.close()


async def playwright_fetch(url):
    html, _ = await _fetch_page(url)
    return html


async def scrapper(url: str):
    try:
        html = await playwright_fetch(url)
        soup = BeautifulSoup(html, 'lxml')
        return html, url
    except Exception as e:
        logger.error("Playwright fetch failed: %s", e)
        return None, None


async def expand_url(url: str) -> str:
    """Expand shortened URLs to their final destination using Playwright."""
    try:
        _, final_url = await _fetch_page(url, return_final_url=True)
        return final_url
    except Exception as e:
        logger.error("Playwright expand_url error: %s", e)
    return url
