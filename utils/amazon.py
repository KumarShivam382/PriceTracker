from bs4 import BeautifulSoup

async def extract_amazon_price(html: str):
    soup = BeautifulSoup(html, "html.parser")
    price_symbol = soup.find("span", class_="a-price-symbol")
    price_whole = soup.find("span", class_="a-price-whole")
    price_fraction = soup.find("span", class_="a-price-fraction")
    if price_whole:
        symbol = price_symbol.get_text(strip=True) if price_symbol else ""
        whole = price_whole.get_text(strip=True).replace(",", "")
        fraction = price_fraction.get_text(strip=True) if price_fraction else "00"
        price = f"{symbol}{whole}.{fraction}"
        print(f"Extracted Amazon price: {price}")
        return price
    return None