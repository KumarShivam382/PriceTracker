import re
import os
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright   
import random
import string

async def playwright_fetch(url):
    async with async_playwright() as p:
        # Launch browser with enhanced anti-detection
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--start-minimized'
            ]
        )
        
        # Create context with realistic settings
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Hide automation indicators
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        await page.goto(url, timeout=15000, wait_until='domcontentloaded')
        await page.wait_for_timeout(1000)  # Brief delay for dynamic content
        html = await page.content()
        await browser.close()
        return html

async def scrapper(url: str):
    try:
        html = await playwright_fetch(url)
        soup = BeautifulSoup(html, 'lxml')
        return html, url
    except Exception as e:
        print(f"❌ Playwright fetch failed: {e}")
        return None, None

async def expand_url(url: str) -> str:
    """Expand shortened URLs to their final destination."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/119.0.0.0 Safari/537.36"
            )
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=8) as client:
            response = await client.get(url, headers=headers)
            return str(response.url)

    except httpx.RequestError as e:
        print(f"❌ Request error: {e}")
    except Exception as e:
        print(f"❌ General error: {e}")
    return url
