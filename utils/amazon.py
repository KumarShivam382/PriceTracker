from bs4 import BeautifulSoup
import re
from playwright.async_api import async_playwright
import asyncio

playwright_semaphore = asyncio.Semaphore(10)

# --- Extract Amazon product price and name from HTML ---
async def extract_amazon_price_and_name(html: str):
    soup = BeautifulSoup(html, "html.parser")
    price_symbol = soup.find("span", class_="a-price-symbol")
    price_whole = soup.find("span", class_="a-price-whole")
    price_fraction = soup.find("span", class_="a-price-fraction")
    title_tag = soup.find("span", id="productTitle")
    price = None
    if price_whole:
        symbol = price_symbol.get_text(strip=True) if price_symbol else ""
        whole = re.sub(r"[^\d]", "", price_whole.get_text(strip=True))
        fraction = re.sub(r"[^\d]", "", price_fraction.get_text(strip=True)) if price_fraction else "00"
        fraction = (fraction + "00")[:2]
        price = f"{symbol}{whole}.{fraction}"
    name = title_tag.get_text(strip=True) if title_tag else None
    return price, name

# --- Robust ASIN extraction from Amazon URLs ---
def extract_asin_from_url_path(url: str) -> str:
    # Common ASIN patterns
    patterns = [
        r"/(?:dp|gp/product|gp/offer-listing|product)/([A-Z0-9]{10})(?:[/?]|$)",
        r"/([A-Z0-9]{10})(?:[/?]|$)"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    print(f"Could not extract ASIN from URL: {url}")
    return None

# --- Resolve Amazon URLs using Playwright ---
async def resolve_amazon_url(url: str) -> str:
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
        print(f"Playwright failed to resolve Amazon URL: {e}")
        return url

# --- Unified ASIN extraction method ---
async def extract_amazon_asin(text: str) -> str:
    url_pattern = r"https?://(?:www\.|amzn\.|a\.co|amazon\.)[\w\./\-\?=]+"
    match = re.search(url_pattern, text)
    if not match:
        print(f"No valid Amazon URL found in input: {text}")
        return None
    url = match.group(0)
    resolved_url = await resolve_amazon_url(url)
    if resolved_url:
        return extract_asin_from_url_path(resolved_url)
    return None
