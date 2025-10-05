from bs4 import BeautifulSoup
import re
import httpx
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# --- Extract Amazon product price and name from HTML ---
async def extract_amazon_price_and_name(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # Amazon's price is typically in these spans
    price_symbol = soup.find("span", class_="a-price-symbol")
    price_whole = soup.find("span", class_="a-price-whole")
    price_fraction = soup.find("span", class_="a-price-fraction")
    title_tag = soup.find("span", id="productTitle")

    # Extract price
    price = None
    if price_whole:
        symbol = price_symbol.get_text(strip=True) if price_symbol else ""
        whole = re.sub(r"[^\d]", "", price_whole.get_text(strip=True))
        fraction = re.sub(r"[^\d]", "", price_fraction.get_text(strip=True)) if price_fraction else "00"
        fraction = (fraction + "00")[:2]  # Ensure 2 digits
        price = f"{symbol}{whole}.{fraction}"

    # Extract name/title
    name = title_tag.get_text(strip=True) if title_tag else None

    return price, name


# Try to extract ASIN from various Amazon URL structures
def extract_asin_from_url_path(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path

    # Common ASIN patterns
    patterns = [
        r"/(?:dp|gp/product|gp/offer-listing|product)/([A-Z0-9]{10})(?:[/?]|$)",
        r"/([A-Z0-9]{10})(?:[/?]|$)"
    ]

    for pattern in patterns:
        match = re.search(pattern, path)
        if match:
            return match.group(1)

    print(f"Could not extract ASIN from URL: {url}")
    return None


# Resolve Amazon URLs using Playwright (primary) with httpx fallback
async def resolve_amazon_url(url: str) -> str:
    """Use Playwright to resolve any Amazon URL, including short links."""
    try:
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
            
            # Navigate with faster wait condition - don't wait for networkidle
            await page.goto(url, timeout=15000, wait_until='domcontentloaded')
            # Wait a brief moment for any immediate redirects
            await page.wait_for_timeout(1000)
            final_url = page.url
            
            await browser.close()
            return final_url
            
    except Exception as e:
        print(f"Playwright failed to resolve Amazon URL: {e}")
        # Fallback to httpx only if Playwright fails
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                response = await client.head(url)
                return str(response.url)
        except Exception as fallback_e:
            print(f"httpx fallback also failed: {fallback_e}")
            return url  # Return original URL if all methods fail


# Unified ASIN extraction method - always use Playwright for reliability
async def extract_amazon_asin(url: str) -> str:
    """
    Extract ASIN using Playwright for all Amazon URLs for maximum reliability.
    Supports short links like amzn.to and a.co as well as regular Amazon URLs.
    """
    # Always resolve URL with Playwright for consistency and reliability
    resolved_url = await resolve_amazon_url(url)
    if resolved_url:
        return extract_asin_from_url_path(resolved_url)
    return None
