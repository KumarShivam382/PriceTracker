from bs4 import BeautifulSoup
import re

async def extract_amazon_price_and_name(html: str):
    soup = BeautifulSoup(html, "html.parser")
    price_symbol = soup.find("span", class_="a-price-symbol")
    price_whole = soup.find("span", class_="a-price-whole")
    price_fraction = soup.find("span", class_="a-price-fraction")
    title_tag = soup.find("span", id="productTitle")

    price = None
    name = None
    if price_whole:
        symbol = price_symbol.get_text(strip=True) if price_symbol else ""
        whole = re.sub(r"\D", "", price_whole.get_text(strip=True))
        fraction = re.sub(r"\D", "", price_fraction.get_text(strip=True)) if price_fraction else "00"
        fraction = (fraction + "00")[:2]
        price = f"{symbol}{whole}.{fraction}"
        print(f"Extracted Amazon price: {price}")
    if title_tag:
        name = title_tag.get_text(strip=True)
    return price, name


def extract_amazon_asin(url: str) -> str:
    # Robustly extract ASIN from Amazon URLs
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", url)
    if match:
        return match.group(1)
    match = re.search(r"/([A-Z0-9]{10})(?:[/?]|$)", url)
    if match:
        return match.group(1)
    return None

