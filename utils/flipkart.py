from bs4 import BeautifulSoup
import re

async def extract_flipkart_price_and_name(html: str):
    soup = BeautifulSoup(html, "html.parser")
    price_tag = soup.find("div", class_="Nx9bqj CxhGGd")
    name_tag = soup.find("h1", class_="_6EBuvT")
    price = price_tag.get_text(strip=True) if price_tag else None
    name = None
    if name_tag:
        span = name_tag.find("span", class_="VU-ZEz")
        if span:
            name = span.get_text(strip=True)
        else:
            name = name_tag.get_text(strip=True)
    return price, name

def extract_flipkart_pid(url: str) -> str:
    # Flipkart product ID is usually after 'pid=' in the URL
    match = re.search(r"[?&]pid=([A-Z0-9]+)", url)
    if match:
        return match.group(1)
    return None