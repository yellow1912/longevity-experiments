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
                elements = self.page.css(selector).getall()
                if elements:
                    texts = [e.css("::text").get() for e in elements]
                    return [t.strip() for t in texts if t and t.strip()]
            except:
                continue
        return []

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
                img_elements = self.page.css(selector).getall()
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
        price = self.extract_text(SELECTORS["price"])
        brand = self.extract_text(SELECTORS["brand"])
        description = self.extract_list(SELECTORS["description"])
        images = self.extract_images(SELECTORS["image"])
        rating = self.extract_text(SELECTORS["rating"])
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
            review_elements = self.page.css("[data-hook='review']").getall()

            for i, review_elem in enumerate(review_elements[:max_reviews]):
                # Extract review fields
                rating_elem = review_elem.css(SELECTORS["review_rating"]).get()
                rating = rating_elem.attrib.get("title", "N/A") if rating_elem else "N/A"

                text_elem = review_elem.css(SELECTORS["review_text"]).get()
                text = text_elem.css("::text").get().strip() if text_elem else "N/A"

                date_elem = review_elem.css(SELECTORS["review_date"]).get()
                date = date_elem.css("::text").get().strip() if date_elem else "N/A"

                verified_elem = review_elem.css(SELECTORS["review_verified"]).get()
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
