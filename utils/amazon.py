from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

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


# --- Extract ASIN from various Amazon URL formats ---
def extract_amazon_asin(url: str) -> str:
    """
    Extract ASIN (Amazon Standard Identification Number) from various Amazon URL patterns.
    Supports:
    - /dp/ASIN
    - /gp/product/ASIN
    - /product/ASIN
    - /ASIN
    """

    # Normalize and parse the URL
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

    return None
