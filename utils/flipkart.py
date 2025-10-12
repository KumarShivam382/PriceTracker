from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import asyncio


playwright_semaphore = asyncio.Semaphore(10)


# Extract product name and price from Flipkart product page HTML
async def extract_flipkart_price_and_name(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # Attempt to find price (handle dynamic class names if possible)
    price_tag = (
        soup.select_one("div.Nx9bqj.CxhGGd") or  
        soup.select_one("div._30jeq3") or      
        soup.find(text=re.compile(r"₹\s?\d+"))  # Fallback regex match
    )
    price = price_tag.get_text(strip=True) if hasattr(price_tag, "get_text") else str(price_tag).strip() if price_tag else None

    # Attempt to find product name
    name_tag = soup.select_one("h1._6EBuvT, h1._35KyD6, span.B_NuCI")  # Multiple common selectors
    name = name_tag.get_text(strip=True) if name_tag else None

    return price, name


# Robust PID extraction from Flipkart URLs
def extract_pid_from_url_path(url: str) -> str:
    parsed = urlparse(url)

    # From query string
    path_match = re.search(r'/p/(itm[0-9A-Za-z]+)', parsed.path)
    if path_match:
        return path_match.group(1)
    
    # Extract from URL segments that contain 'itm'
    segments = parsed.path.split('/')
    for segment in segments:
        if segment.startswith('itm') and len(segment) > 10:
            return segment

    logger.info(f"Could not extract PID from URL: {url}")
    return None


# Resolve Flipkart URLs using Playwright
async def resolve_flipkart_url(url: str) -> str:
    """Use Playwright to resolve any Flipkart URL, including short links."""
    try:
        async with playwright_semaphore:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-dev-shm-usage',
                        '--no-first-run'
                    ]
                )
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
                """)
                
                await page.goto(url, timeout=10000, wait_until='commit')
                await page.wait_for_timeout(2000)
                final_url = page.url
                
                await browser.close()
                return final_url
            
    except Exception as e:
        print(f"Playwright failed to resolve Flipkart URL: {e}")
        return url


# Unified PID extraction method
async def extract_flipkart_pid(text: str) -> str:
    """
    Extract Flipkart product ID using Playwright for all URLs.
    Accepts text containing a URL and other content.
    """
    url_pattern = r"https?://(?:www\.|fkrt\.it|flipkart\.)[\w\./\-\?=]+"
    match = re.search(url_pattern, text)
    if not match:
        print(f"No valid Flipkart URL found in input: {text}")
        return None
    url = match.group(0)
    resolved_url = await resolve_flipkart_url(url)
    if resolved_url:
        return extract_pid_from_url_path(resolved_url)
    return None
