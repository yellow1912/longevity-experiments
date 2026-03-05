"""
Data Extraction Module
Extracts product details and reviews from Amazon pages
"""
import re
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
                for element in self.page.css(selector):
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
                elements = list(self.page.css(selector))
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
            for acr_elem in self.page.css("#acrPopover"):
                title = acr_elem.attrib.get("title", "")
                if title:
                    match = re.search(r'(\d+\.\d+)', title)
                    return match.group(1) if match else title
        except:
            pass

        # Try .a-icon-alt text as fallback
        try:
            for elem in self.page.css(".a-icon-alt"):
                text = elem.css("::text").get()
                if text and "out of 5" in text:
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
            for container in self.page.css(".a-price"):
                texts = container.css("::text").getall()
                price_parts = [str(t).strip() for t in texts if str(t).strip()]
                if price_parts:
                    full_price = ' '.join(price_parts)
                    words = full_price.split()
                    seen = set()
                    cleaned = []
                    for word in words:
                        if word not in seen or not word.isalpha():
                            cleaned.append(word)
                            seen.add(word)
                    return ' '.join(cleaned[:3])
        except:
            pass

        # Fallback to original selectors
        return self.extract_text(SELECTORS["price"])

    def extract_images(self, selectors: List[str]) -> List[str]:
        """
        Extract image URLs, preferring hi-res data-old-hires over src thumbnails.
        Collects both the landing image and gallery alt images.
        """
        seen = set()
        urls = []

        def add_url(url: str):
            if url and url.startswith("http") and url not in seen:
                seen.add(url)
                urls.append(url)

        # 1. Collect all elements with data-old-hires
        try:
            for elem in self.page.css("[data-old-hires]"):
                hires = elem.attrib.get("data-old-hires")
                if hires:
                    add_url(hires)
        except:
            pass

        # 2. Fallback to configured selectors if no hi-res images found
        if not urls:
            for selector in selectors:
                try:
                    for elem in self.page.css(selector):
                        src = elem.attrib.get("src") or elem.attrib.get("data-src")
                        add_url(src)
                    if urls:
                        break
                except:
                    continue

        return urls

    def extract_price_per_unit(self) -> Optional[str]:
        """Extract price per unit, e.g. '$0.07/count'."""
        try:
            for elem in self.page.css(".apex-priceperunit-accessibility-label"):
                text = elem.css("::text").get()
                if text:
                    parts = text.strip().split()
                    if len(parts) >= 3 and parts[1].lower() == "per":
                        return f"{parts[0]}/{parts[2]}"
                    return text.strip()
            # Fallback: price value + surrounding text
            for val_elem in self.page.css(".apex-priceperunit-value .a-offscreen"):
                price_text = val_elem.css("::text").get()
                if price_text:
                    return price_text.strip()
        except:
            pass
        return None

    def extract_bought_in_past_month(self) -> Optional[str]:
        """Extract social proof text like '10K+'."""
        try:
            for elem in self.page.css("#social-proofing-faceout-title-tk_bought"):
                texts = elem.css("::text").getall()
                full = " ".join(str(t).strip() for t in texts if str(t).strip())
                match = re.match(r'([\d,.]+[KkMm]?\+?)', full)
                if match:
                    return match.group(1)
                return full
        except:
            pass
        return None

    def extract_product_details(self) -> Dict[str, str]:
        """Extract product specifications from the voyager desktop table."""
        details = {}
        try:
            for th_elem in self.page.css(".voyager-ns-desktop-table-label"):
                key = th_elem.css("::text").get()
                if not key or not key.strip():
                    continue
                key = key.strip()
                tr = th_elem.parent
                if tr:
                    for td in tr.css(".voyager-ns-desktop-table-value"):
                        val = td.css("::text").get()
                        if val and val.strip():
                            details[key] = val.strip()
                        break
        except:
            pass
        return details

    def extract_product_overview(self) -> Dict[str, str]:
        """Extract product overview from the po-break-word table."""
        overview = {}
        try:
            for row in self.page.css("table[role='list'] tr[role='listitem']"):
                label_elem = None
                value_elem = None
                for le in row.css(".a-text-bold"):
                    label_elem = le
                    break
                for ve in row.css(".po-break-word"):
                    value_elem = ve
                    break
                if label_elem and value_elem:
                    label = label_elem.css("::text").get()
                    value = value_elem.css("::text").get()
                    if label and value and label.strip() and value.strip():
                        overview[label.strip()] = value.strip()
        except:
            pass
        return overview

    def extract_best_sellers_rank(self) -> List[Dict[str, str]]:
        """Extract Best Sellers Rank entries."""
        ranks = []
        try:
            bsr_td = None
            for th in self.page.css("th.prodDetSectionEntry"):
                text = th.css("::text").get()
                if text and "Best Sellers Rank" in text:
                    tr = th.parent
                    if tr:
                        for td in tr.css("td"):
                            bsr_td = td
                            break
                    break
            if bsr_td:
                for item in bsr_td.css(".a-list-item"):
                    texts = item.css("::text").getall()
                    full = " ".join(str(t).strip() for t in texts if str(t).strip())
                    match = re.match(r'(#[\d,]+)\s+in\s+(.+?)(?:\s*\(|$)', full)
                    if match:
                        ranks.append({
                            "rank": match.group(1),
                            "category": match.group(2).strip(),
                        })
        except:
            pass
        return ranks

    def extract_videos(self) -> List[Dict[str, str]]:
        """Extract product videos from data-video-items JSON attribute."""
        videos = []
        try:
            import json as _json
            from html import unescape
            for elem in self.page.css("[data-video-items]"):
                raw = elem.attrib.get("data-video-items", "")
                items = _json.loads(unescape(raw))
                for item in items:
                    video = {"title": item.get("title", "").strip()}
                    if item.get("videoURL"):
                        video["url"] = item["videoURL"]
                    if item.get("videoImageUrl"):
                        video["thumbnail"] = item["videoImageUrl"]
                    if item.get("formattedDuration"):
                        video["duration"] = item["formattedDuration"]
                    if item.get("vendorName"):
                        video["creator"] = item["vendorName"]
                    videos.append(video)
                break
        except:
            pass
        return videos

    def extract_important_info(self) -> Dict[str, Optional[str]]:
        """Extract Ingredients, Directions, and Safety Information from #important-information."""
        info = {"ingredients": None, "directions": None, "safety_info": None}
        heading_map = {
            "Ingredients": "ingredients",
            "Directions": "directions",
            "Safety Information": "safety_info",
        }
        try:
            for div in self.page.css("#important-information .content"):
                h4 = None
                for h in div.css("h4"):
                    h4 = h
                    break
                if not h4:
                    continue
                heading = h4.css("::text").get()
                if not heading:
                    continue
                heading = heading.strip()
                field = heading_map.get(heading)
                if not field:
                    continue
                texts = []
                for p in div.css("p"):
                    p_texts = p.css("::text").getall()
                    p_full = " ".join(str(t).strip() for t in p_texts if str(t).strip())
                    if p_full:
                        texts.append(p_full)
                if texts:
                    info[field] = " ".join(texts)
        except:
            pass
        return info

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
        price = self.extract_price()
        brand = self.extract_text(SELECTORS["brand"])
        description = self.extract_list(SELECTORS["description"])
        images = self.extract_images(SELECTORS["image"])
        rating = self.extract_rating()
        review_count_text = self.extract_text(SELECTORS["review_count"])

        # Parse review count (e.g., "1,234 ratings" -> 1234)
        review_count = 0
        if review_count_text and review_count_text != "N/A":
            try:
                review_count = int(''.join(filter(str.isdigit, review_count_text)))
            except:
                pass

        # Extract new fields
        important_info = self.extract_important_info()

        # Generate affiliate link
        affiliate_url = generate_affiliate_link(asin, PARTNER_TAG) if asin else "N/A"

        return {
            "asin": asin or "UNKNOWN",
            "title": title,
            "price": price,
            "price_per_unit": self.extract_price_per_unit(),
            "brand": brand,
            "bought_in_past_month": self.extract_bought_in_past_month(),
            "description": description,
            "images": images,
            "rating": rating,
            "review_count": review_count,
            "best_sellers_rank": self.extract_best_sellers_rank(),
            "product_details": self.extract_product_details(),
            "product_overview": self.extract_product_overview(),
            "ingredients": important_info["ingredients"],
            "directions": important_info["directions"],
            "safety_info": important_info["safety_info"],
            "videos": self.extract_videos(),
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
            review_elements = list(self.page.css("[data-hook='review']"))

            for i, review_elem in enumerate(review_elements[:max_reviews]):
                # Extract review rating
                rating = "N/A"
                for rating_elem in review_elem.css(SELECTORS["review_rating"]):
                    rating_text = rating_elem.css("::text").get()
                    if rating_text:
                        match = re.search(r'(\d+\.\d+)', rating_text)
                        rating = match.group(1) if match else rating_text.strip()
                    break

                # Extract review text
                text = "N/A"
                for text_elem in review_elem.css("[data-hook='review-body']"):
                    text_nodes = text_elem.css("::text").getall()
                    text_parts = [str(t).strip() for t in text_nodes if str(t).strip()]
                    text = ' '.join(text_parts) if text_parts else "N/A"
                    break

                # Extract date
                date = "N/A"
                for date_elem in review_elem.css(SELECTORS["review_date"]):
                    d = date_elem.css("::text").get()
                    date = d.strip() if d else "N/A"
                    break

                # Check for verified purchase badge
                verified = False
                for _ in review_elem.css("[data-hook='avp-badge']"):
                    verified = True
                    break

                # Extract reviewer name
                reviewer = "Anonymous"
                for reviewer_elem in review_elem.css(SELECTORS["reviewer_name"]):
                    r = reviewer_elem.css("::text").get()
                    reviewer = r.strip() if r else "Anonymous"
                    break

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
