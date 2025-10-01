from bs4 import BeautifulSoup
import re

async def extract_amazon_price(html: str):
    soup = BeautifulSoup(html, "html.parser")
    price_symbol = soup.find("span", class_="a-price-symbol")
    price_whole = soup.find("span", class_="a-price-whole")
    price_fraction = soup.find("span", class_="a-price-fraction")
    if price_whole:
        symbol = price_symbol.get_text(strip=True) if price_symbol else ""
        # Only keep digits in whole and fraction
        whole = re.sub(r"\D", "", price_whole.get_text(strip=True))
        fraction = re.sub(r"\D", "", price_fraction.get_text(strip=True)) if price_fraction else "00"
        # Ensure fraction is always two digits
        fraction = (fraction + "00")[:2]
        price = f"{symbol}{whole}.{fraction}"
        print(f"Extracted Amazon price: {price}")
        return price
    return None