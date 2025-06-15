from bs4 import BeautifulSoup

# Domain-specific selectors
SITE_SELECTORS = {
    "flipkart.com": {
        "title": ["span.B_NuCI"],
        "price": ["div._30jeq3", "div._25b18c span._30jeq3"],
    },
    "amazon.in": {
        "title": ["span#productTitle"],
        "price": ["span.a-price-whole", "span.a-offscreen"],
    },
    "snapdeal.com": {
        "title": ["h1.pdp-e-i-head"],
        "price": ["span.payBlkBig"],
    },
    "croma.com": {
        "title": ["h1.plp-pro-title"],
        "price": ["span.amount"],
    },
    "reliancedigital.in": {
        "title": ["h1.pdp__title"],
        "price": ["span.pdp__offerPrice"],
    },
}


def extract_with_selectors(soup, domain):
    selectors = SITE_SELECTORS.get(domain, {})
    title = ""
    price = ""

    for selector in selectors.get("title", []):
        tag = soup.select_one(selector)
        if tag:
            title = tag.get_text(strip=True)
            break

    for selector in selectors.get("price", []):
        tag = soup.select_one(selector)
        if tag and "₹" in tag.get_text():
            price = tag.get_text(strip=True)
            break

    return title, price


def fallback_extract(soup):
    title_tag = soup.select_one("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    price = ""
    for tag in soup.find_all(["span", "div"]):
        text = tag.get_text(strip=True)
        if "₹" in text:
            price = text
            break
    return title, price


def extract_candidate_blocks(soup, domain):
    title, price = extract_with_selectors(soup, domain)
    if not title and not price:
        title, price = fallback_extract(soup)
    parts = []
    if title:
        parts.append(f"title: {title}")
    if price:
        parts.append(f"price: {price}")
    return "\n".join(parts)
