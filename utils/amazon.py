from bs4 import BeautifulSoup
import re

async def extract_amazon_price(html: str):
    try:
        print("Starting Amazon price extraction...")
        soup = BeautifulSoup(html, "html.parser")
        
        # Function to check if an element is hidden
        def is_hidden(element):
            if not element:
                return True
                
            # Check if element or its parent has hidden classes
            current = element
            while current and hasattr(current, 'get'):
                classes = current.get('class', [])
                if isinstance(classes, list):
                    # Check for various hidden class patterns
                    hidden_classes = ['aok-hidden', 'a-hidden', 'hidden']
                    if any(hidden_class in classes for hidden_class in hidden_classes):
                        return True
                current = current.parent
            return False
        
        # Priority order for price containers (most reliable first)
        price_selectors = [
            # Main product price (most common and reliable)
            "span.a-price.a-text-price.a-size-medium.a-color-base",
            "span.a-price.a-text-normal.aok-align-center.reinventPriceAccordionT2[data-a-size='l']",
            "span.a-price.a-text-price.a-size-base",
            # Generic price containers
            "span.a-price",
            # Specific price IDs
            "#priceblock_dealprice",
            "#priceblock_ourprice", 
            "#tp_price_block_total_price_ww"
        ]
        
        # Try each selector in priority order
        for selector in price_selectors:
            try:
                containers = soup.select(selector)
                
                for container in containers:
                    if is_hidden(container):
                        continue
                    
                    # Look for price components within this container
                    price_whole = container.find("span", class_="a-price-whole")
                    price_fraction = container.find("span", class_="a-price-fraction") 
                    price_symbol = container.find("span", class_="a-price-symbol")
                    
                    # Also try to get from offscreen text (more reliable)
                    offscreen = container.find("span", class_="a-offscreen")
                    if offscreen:
                        offscreen_text = offscreen.get_text(strip=True)
                        # Extract price from offscreen text (e.g., "₹641.00")
                        price_match = re.search(r'[₹$£€¥]\s*[\d,]+\.?\d*', offscreen_text)
                        if price_match:
                            price = price_match.group().replace(',', '').strip()
                            print(f"Extracted Amazon price (offscreen): {price}")
                            return price
                    
                    # Fallback to component extraction
                    if price_whole:
                        symbol = price_symbol.get_text(strip=True) if price_symbol else "₹"
                        whole = re.sub(r'[^\d]', '', price_whole.get_text(strip=True))
                        fraction = re.sub(r'[^\d]', '', price_fraction.get_text(strip=True)) if price_fraction else "00"
                        
                        # Ensure we have valid numbers
                        if whole and whole.isdigit():
                            # Ensure fraction is exactly 2 digits
                            fraction = (fraction + "00")[:2]
                            price = f"{symbol}{whole}.{fraction}"
                            print(f"Extracted Amazon price (components): {price}")
                            return price
                            
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
                continue
        
        # Last resort: try to find any price-like text in the HTML
        try:
            # Look for Indian Rupee prices in the entire HTML
            price_pattern = r'₹\s*[\d,]+\.?\d*'
            matches = re.findall(price_pattern, html)
            
            if matches:
                # Filter out very small prices (likely shipping, etc.) and very large ones
                valid_prices = []
                for match in matches:
                    # Extract numeric value
                    numeric = re.sub(r'[^\d.]', '', match)
                    if numeric and '.' in numeric:
                        try:
                            value = float(numeric)
                            # Reasonable price range for products (₹10 to ₹100,000)
                            if 10 <= value <= 100000:
                                valid_prices.append(match.strip())
                        except ValueError:
                            continue
                
                if valid_prices:
                    # Return the first reasonable price found
                    price = valid_prices[0].replace(',', '').strip()
                    print(f"Extracted Amazon price (regex fallback): {price}")
                    return price
                    
        except Exception as e:
            print(f"Error in regex fallback: {e}")
        
        print("No Amazon price found")
        return None
        
    except Exception as e:
        print(f"CRITICAL ERROR in extract_amazon_price: {e}")
        import traceback
        traceback.print_exc()
        return None