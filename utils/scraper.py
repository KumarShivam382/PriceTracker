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
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        async with httpx.AsyncClient(
            follow_redirects=True, 
            timeout=10,
            headers=headers
        ) as client:
            # Use HEAD request first to avoid downloading full page content
            try:
                response = await client.head(url)
                expanded_url = str(response.url)
                print(f"HEAD request expanded: {url} -> {expanded_url}")
                return expanded_url
            except Exception as head_error:
                print(f"HEAD request failed, trying GET: {head_error}")
                # Fallback to GET request if HEAD fails
                response = await client.get(url)
                expanded_url = str(response.url)
                print(f"GET request expanded: {url} -> {expanded_url}")
                return expanded_url

    except httpx.TimeoutException as e:
        print(f"❌ Timeout expanding URL {url}: {e}")
    except httpx.RequestError as e:
        print(f"❌ Request error expanding URL {url}: {e}")
    except Exception as e:
        print(f"❌ General error expanding URL {url}: {e}")
    
    print(f"⚠️ URL expansion failed, returning original: {url}")
    return url
