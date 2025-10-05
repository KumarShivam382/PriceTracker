from bs4 import BeautifulSoup
import re
import httpx
from urllib.parse import urlparse, parse_qs


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
    path_match = re.search(r'/p/(itm[0-9A-Z]+)', parsed.path)
    if path_match:
        return path_match.group(1)

    return None


# Resolve short Flipkart URLs like https://dl.flipkart.com/s/abcd123
async def resolve_short_flipkart_url(url: str) -> str:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            response = await client.head(url)
            return str(response.url)
    except Exception as e:
        print(f"Error resolving short URL: {e}")
        return None


# Unified PID extraction method
async def extract_flipkart_pid(url: str) -> str:
    parsed_url = urlparse(url)

    if "dl.flipkart.com" in parsed_url.netloc:
        resolved_url = await resolve_short_flipkart_url(url)
        if resolved_url:
            return extract_pid_from_url_path(resolved_url)
        return None
    else:
        return extract_pid_from_url_path(url)
