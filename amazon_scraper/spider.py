"""
Main Spider Module
Orchestrates the Amazon supplement scraping workflow
"""
import time
from typing import List, Optional
from scrapling import StealthyFetcher
from .config import CATEGORIES, SCRAPING_SETTINGS, SELECTORS
from .extractors import ProductScraper, ReviewExtractor
from .exporters import DataExporter
from .state import StateManager
from .utils import sleep_with_message


class SupplementSpider:
    """
    Main spider class for scraping Amazon supplements.
    Uses category-first approach with resume capability.
    """

    def __init__(self, resume: bool = False):
        """
        Initialize spider.

        Args:
            resume: If True, resume from last checkpoint
        """
        self.state_manager = StateManager()
        self.exporter = DataExporter()
        self.resume = resume
        self.stats = {
            "products_scraped": 0,
            "products_skipped": 0,
            "validation_passed": 0,
            "validation_failed": 0,
            "errors": []
        }

        # Load existing ASINs if resuming
        if resume:
            self.exporter.load_existing_asins()
            resume_point = self.state_manager.get_resume_point()
            print(f"Resuming from category: {resume_point['category']}")
            print(f"Products already scraped: {resume_point['products_scraped']}")

    def start(self) -> None:
        """Start the scraping process"""
        print("=" * 80)
        print("Amazon Supplement Scraper")
        print("=" * 80)
        print(f"Categories to scrape: {len(CATEGORIES)}")
        print(f"Resume mode: {'ON' if self.resume else 'OFF'}")
        print("=" * 80)

        for category_name, category_url in CATEGORIES.items():
            # Skip if already completed
            if self.state_manager.is_category_completed(category_name):
                print(f"\n✓ Skipping completed category: {category_name}")
                continue

            print(f"\n[Category] {category_name}")
            print(f"[URL] {category_url}")

            self.scrape_category(category_name, category_url)
            self.state_manager.complete_category(category_name)

        self.print_final_stats()

    def scrape_category(self, category_name: str, category_url: str) -> None:
        """
        Scrape all products in a category.

        Args:
            category_name: Category identifier
            category_url: Amazon search/category URL
        """
        self.state_manager.start_category(category_name)

        page_num = 1
        max_pages = 50  # Safety limit

        while page_num <= max_pages:
            print(f"\n  [Page {page_num}] Fetching product listings...")

            # Extract ASINs from listing page
            asins = self.extract_asins_from_listing(category_url, page_num)

            if not asins:
                print(f"  No products found on page {page_num}. End of category.")
                break

            print(f"  Found {len(asins)} products")

            # Scrape each product
            for i, asin in enumerate(asins, 1):
                print(f"  [{i}/{len(asins)}] Processing {asin}...", end=" ")

                # Skip if already scraped
                if self.exporter.is_already_scraped(asin):
                    print("(already scraped)")
                    self.stats["products_skipped"] += 1
                    continue

                # Scrape product
                success = self.scrape_product(asin, category_name)

                if success:
                    self.stats["products_scraped"] += 1
                    self.stats["validation_passed"] += 1
                    print("✓")
                else:
                    self.stats["validation_failed"] += 1
                    print("✗")

                # Checkpoint if needed
                if self.state_manager.should_checkpoint():
                    self.state_manager.save_checkpoint()
                    print("  [Checkpoint saved]")

                # Respectful delay
                delay = SCRAPING_SETTINGS["delay_between_products"]
                time.sleep(delay)

            page_num += 1
            self.state_manager.increment_page()

    def extract_asins_from_listing(self, base_url: str, page_num: int) -> List[str]:
        """
        Extract product ASINs from category listing page.

        Args:
            base_url: Category/search URL
            page_num: Page number (1-indexed)

        Returns:
            List of ASINs found on page
        """
        # Add page number and force USD currency
        url = base_url
        if page_num > 1:
            url = f"{url}&page={page_num}"
        # Force US market with USD (avoids VND or other currencies)
        if "currency=USD" not in url:
            url = f"{url}&currency=USD"

        try:
            # Use StealthyFetcher for anti-detection
            response = StealthyFetcher.fetch(
                url,
                headless=True,
                network_idle=True,
                timeout=SCRAPING_SETTINGS["page_load_timeout"] * 1000  # Convert seconds to milliseconds
            )

            # Extract ASINs from data-asin attributes
            asin_elements = response.css(SELECTORS["product_asin"]).get_all()
            asins = []

            for elem in asin_elements:
                asin = elem.attrib.get("data-asin", "")
                # Filter out empty and invalid ASINs
                if asin and asin.startswith("B") and len(asin) == 10:
                    if asin not in asins:  # Avoid duplicates
                        asins.append(asin)

            return asins

        except Exception as e:
            print(f"\n  Error fetching listing page: {e}")
            self.stats["errors"].append(f"Listing page {page_num}: {str(e)}")
            return []

    def scrape_product(self, asin: str, category: str) -> bool:
        """
        Scrape single product detail page.

        Args:
            asin: Product ASIN
            category: Category name

        Returns:
            True if successful, False otherwise
        """
        # Force USD currency for product page
        product_url = f"https://www.amazon.com/dp/{asin}?currency=USD"

        try:
            # Fetch product page
            response = StealthyFetcher.fetch(
                product_url,
                headless=True,
                network_idle=True,
                timeout=SCRAPING_SETTINGS["page_load_timeout"] * 1000  # Convert seconds to milliseconds
            )

            # Extract product data
            scraper = ProductScraper(response)
            product_data = scraper.extract_product_data()

            # Extract reviews
            review_extractor = ReviewExtractor(response)
            product_data["reviews"] = review_extractor.extract_reviews()

            # Save product data
            success, message = self.exporter.save_product(product_data, category)

            if success:
                self.state_manager.add_scraped_asin(asin)

            return success

        except Exception as e:
            error_msg = f"Failed to scrape {asin}: {str(e)}"
            self.stats["errors"].append(error_msg)
            return False

    def print_final_stats(self) -> None:
        """Print final statistics"""
        print("\n" + "=" * 80)
        print("Scraping Complete!")
        print("=" * 80)
        print(f"Total products scraped: {self.stats['products_scraped']}")
        print(f"Products skipped: {self.stats['products_skipped']}")
        print(f"Validation passed: {self.stats['validation_passed']}")
        print(f"Validation failed: {self.stats['validation_failed']}")
        print("=" * 80)
