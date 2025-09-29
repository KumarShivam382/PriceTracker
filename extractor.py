def extract_amazon_product_info(soup):
    title = soup.find("span", {"id": "productTitle"}).get_text(strip=True)
    price = soup.find("span", {"id": "priceblock_ourprice"}).get_text(strip=True)
    return {"title": title, "price": price}

def extract_flipkart_product_info(soup):
    title = soup.find("span", {"class": "B_NuCI"}).get_text(strip=True)
    price = soup.find("div", {"class": "_30jeq3 _16Jk6d"}).get_text(strip=True)
    return {"title": title, "price": price}

def extract_product_info(soup, domain):
    if "amazon" in domain:
        return extract_amazon_product_info(soup)
    elif "flipkart" in domain:
        return extract_flipkart_product_info(soup)
    else:
        raise ValueError("Unsupported domain")