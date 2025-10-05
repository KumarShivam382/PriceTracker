from bs4 import BeautifulSoup
import re
import httpx
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright


# Extract product name and price from Flipkart product page HTML
async def extract_flipkart_price_and_name(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # Attempt to find price (handle dynamic class names if possible)
    price_tag = (
        soup.select_one("div.Nx9bqj.CxhGGd") or  # Current class (as of your code)
        soup.select_one("div._30jeq3") or       # Common older Flipkart price class
        soup.find(text=re.compile(r"₹\s?\d+"))  # Fallback regex match
    )
    price = price_tag.get_text(strip=True) if hasattr(price_tag, "get_text") else str(price_tag).strip() if price_tag else None

    # Attempt to find product name
    name_tag = soup.select_one("h1._6EBuvT, h1._35KyD6, span.B_NuCI")  # Multiple common selectors
    name = name_tag.get_text(strip=True) if name_tag else None

    return price, name


# Try to extract PID from various Flipkart URL structures
def extract_pid_from_url_path(url: str) -> str:
    parsed = urlparse(url)

    # From query string
    query_params = parse_qs(parsed.query)
    if 'pid' in query_params:
        return query_params['pid'][0]

    # From path, e.g., /p/itmABC123XYZ456
    path_match = re.search(r'/p/(itm[0-9A-Za-z]+)', parsed.path)
    if path_match:
        return path_match.group(1)
    
    # Alternative pattern: /product-name/p/itmXXX?pid=itmXXX
    alt_match = re.search(r'/p/(itm[^/?]+)', parsed.path)
    if alt_match:
        return alt_match.group(1)
    
    # Extract from URL segments that contain 'itm'
    segments = parsed.path.split('/')
    for segment in segments:
        if segment.startswith('itm') and len(segment) > 10:
            return segment

    print(f"Could not extract PID from URL: {url}")
    return None


# Resolve Flipkart URLs using Playwright (primary) with httpx fallback
async def resolve_flipkart_url(url: str) -> str:
    """Use Playwright to resolve any Flipkart URL, including short links."""
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
        print(f"Playwright failed to resolve Flipkart URL: {e}")
        # Fallback to httpx only if Playwright fails
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                response = await client.head(url)
                return str(response.url)
        except Exception as fallback_e:
            print(f"httpx fallback also failed: {fallback_e}")
            return url  # Return original URL if all methods fail


# Unified PID extraction method - always use Playwright for reliability
async def extract_flipkart_pid(url: str) -> str:
    """Extract Flipkart product ID using Playwright for all URLs."""
    # Always resolve URL with Playwright for consistency and reliability
    resolved_url = await resolve_flipkart_url(url)
    if resolved_url:
        return extract_pid_from_url_path(resolved_url)
    return None
