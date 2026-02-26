"""
Data Extraction Module
Extracts product details and reviews from Amazon pages
"""
from typing import List, Dict, Any, Optional
from .config import SELECTORS, SCRAPING_SETTINGS, PARTNER_TAG
from .utils import generate_affiliate_link, extract_asin_from_url


class ProductScraper:
    """Extracts product data from Amazon product detail pages"""

    def __init__(self, page):
        """
        Initialize with Scrapling page object.

        Args:
            page: Scrapling page object (from StealthyFetcher)
        """
        self.page = page

    def extract_text(self, selectors: List[str], default: str = "N/A") -> str:
        """
        Try multiple selectors and return first match.

        Args:
            selectors: List of CSS selectors to try
            default: Default value if no match

        Returns:
            Extracted text or default
        """
        for selector in selectors:
            try:
                element = self.page.css(selector).get()
                if element:
                    text = element.css("::text").get()
                    if text and text.strip():
                        return text.strip()
            except:
                continue
        return default

    def extract_list(self, selectors: List[str]) -> List[str]:
        """
        Extract multiple elements as list.

        Args:
            selectors: List of CSS selectors to try

        Returns:
            List of extracted texts
        """
        for selector in selectors:
            try:
                elements = self.page.css(selector).get_all()
                if elements:
                    texts = [e.css("::text").get() for e in elements]
                    return [t.strip() for t in texts if t and t.strip()]
            except:
                continue
        return []

    def extract_rating(self) -> str:
        """
        Extract product rating (e.g., "4.7 out of 5 stars").

        Returns:
            Rating string with numeric value
        """
        # Try #acrPopover title attribute first
        try:
            acr_elem = self.page.css("#acrPopover").get()
            if acr_elem:
                title = acr_elem.attrib.get("title", "")
                if title:
                    # Extract number from "X.X out of 5 stars"
                    import re
                    match = re.search(r'(\d+\.\d+)', title)
                    return match.group(1) if match else title
        except:
            pass

        # Try .a-icon-alt text as fallback
        try:
            alt_elems = self.page.css(".a-icon-alt").get_all()
            for elem in alt_elems:
                text = elem.css("::text").get()
                if text and "out of 5" in text:
                    import re
                    match = re.search(r'(\d+\.\d+)', text)
                    return match.group(1) if match else text.strip()
        except:
            pass

        # Fallback to original selectors
        return self.extract_text(SELECTORS["rating"])

    def extract_price(self) -> str:
        """
        Extract price with currency (handles international formats).

        Returns:
            Price string with currency (e.g., "$13.49" or "VND 347,715")
        """
        # Try .a-price container first (has full price with currency)
        try:
            price_containers = self.page.css(".a-price").get_all()
            if price_containers:
                # Get all text from first price container
                texts = price_containers[0].css("::text").get_all()
                price_parts = [t.get().strip() for t in texts if t.get() and t.get().strip()]
                if price_parts:
                    # Join parts and clean up (e.g., "VND 347,715 VND 347,715" -> "VND 347,715")
                    full_price = ' '.join(price_parts)
                    # Remove duplicate currency mentions
                    words = full_price.split()
                    seen = set()
                    cleaned = []
                    for word in words:
                        if word not in seen or not word.isalpha():
                            cleaned.append(word)
                            seen.add(word)
                    return ' '.join(cleaned[:3])  # Take first 3 parts (currency + amount)
        except:
            pass

        # Fallback to original selectors
        return self.extract_text(SELECTORS["price"])

    def extract_images(self, selectors: List[str]) -> List[str]:
        """
        Extract image URLs.

        Args:
            selectors: List of CSS selectors for img tags

        Returns:
            List of image URLs
        """
        urls = []
        for selector in selectors:
            try:
                # Try to get src attribute
                img_elements = self.page.css(selector).get_all()
                for elem in img_elements:
                    src = elem.attrib.get("src") or elem.attrib.get("data-src")
                    if src and src.startswith("http"):
                        urls.append(src)
                if urls:
                    break
            except:
                continue
        return urls

    def extract_product_data(self) -> Dict[str, Any]:
        """
        Extract all product data from current page.

        Returns:
            Dictionary with product data
        """
        # Extract ASIN from URL
        asin = extract_asin_from_url(self.page.url)

        # Extract fields using selectors
        title = self.extract_text(SELECTORS["title"])
        price = self.extract_price()  # Use special price extraction
        brand = self.extract_text(SELECTORS["brand"])
        description = self.extract_list(SELECTORS["description"])
        images = self.extract_images(SELECTORS["image"])
        rating = self.extract_rating()  # Use special rating extraction
        review_count_text = self.extract_text(SELECTORS["review_count"])

        # Parse review count (e.g., "1,234 ratings" -> 1234)
        review_count = 0
        if review_count_text and review_count_text != "N/A":
            try:
                review_count = int(''.join(filter(str.isdigit, review_count_text)))
            except:
                pass

        # Generate affiliate link
        affiliate_url = generate_affiliate_link(asin, PARTNER_TAG) if asin else "N/A"

        return {
            "asin": asin or "UNKNOWN",
            "title": title,
            "price": price,
            "brand": brand,
            "description": description,
            "images": images,
            "rating": rating,
            "review_count": review_count,
            "affiliate_url": affiliate_url,
            "reviews": []  # Will be filled by ReviewExtractor
        }


class ReviewExtractor:
    """Extracts product reviews from Amazon review section"""

    def __init__(self, page):
        """
        Initialize with Scrapling page object.

        Args:
            page: Scrapling page object
        """
        self.page = page

    def extract_reviews(self, max_reviews: int = None) -> List[Dict[str, Any]]:
        """
        Extract product reviews from current page.

        Args:
            max_reviews: Maximum number of reviews to extract

        Returns:
            List of review dictionaries
        """
        max_reviews = max_reviews or SCRAPING_SETTINGS["max_reviews_per_product"]
        reviews = []

        try:
            # Find all review containers
            review_elements = self.page.css("[data-hook='review']").get_all()

            for i, review_elem in enumerate(review_elements[:max_reviews]):
                # Extract review rating - parse from text like "5.0 out of 5 stars"
                rating_elem = review_elem.css(SELECTORS["review_rating"]).get()
                rating = "N/A"
                if rating_elem:
                    rating_text = rating_elem.css("::text").get()
                    if rating_text:
                        # Extract number from "X.X out of 5 stars"
                        import re
                        match = re.search(r'(\d+\.\d+)', rating_text)
                        rating = match.group(1) if match else rating_text.strip()

                # Extract review text - use data-hook and get all text
                text_elem = review_elem.css("[data-hook='review-body']").get()
                text = "N/A"
                if text_elem:
                    # Get all text nodes and join them
                    text_nodes = text_elem.css("::text").get_all()
                    text_parts = [t.get().strip() for t in text_nodes if t.get() and t.get().strip()]
                    text = ' '.join(text_parts) if text_parts else "N/A"

                date_elem = review_elem.css(SELECTORS["review_date"]).get()
                date = date_elem.css("::text").get().strip() if date_elem else "N/A"

                # Check for verified purchase badge using data-hook
                verified_elem = review_elem.css("[data-hook='avp-badge']").get()
                verified = verified_elem is not None

                reviewer_elem = review_elem.css(SELECTORS["reviewer_name"]).get()
                reviewer = reviewer_elem.css("::text").get().strip() if reviewer_elem else "Anonymous"

                reviews.append({
                    "rating": rating,
                    "text": text,
                    "date": date,
                    "verified": verified,
                    "reviewer": reviewer
                })

        except Exception as e:
            print(f"Warning: Failed to extract reviews: {e}")

        return reviews
