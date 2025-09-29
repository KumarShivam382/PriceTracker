from bs4 import BeautifulSoup

async def extract_flipkart_price(html: str):
    soup = BeautifulSoup(html, "html.parser")
    price_tag = soup.find("div", class_="Nx9bqj CxhGGd")
    if price_tag:
        print(f"Extracted Flipkart price: {price_tag.get_text(strip=True)}")
    return price_tag.get_text(strip=True) if price_tag else None