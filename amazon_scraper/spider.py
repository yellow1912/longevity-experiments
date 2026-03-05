"""
Main Spider Module
Orchestrates the Amazon supplement scraping workflow
"""
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from typing import List, Tuple
from .config import CATEGORIES, SCRAPING_SETTINGS, SELECTORS
from .extractors import ProductScraper, ReviewExtractor
from .exporters import DataExporter
from .state import StateManager
from .utils import set_usd_currency
from .fetchers import BaseFetcher, FetchError, create_fetcher


class SupplementSpider:
    """
    Main spider class for scraping Amazon supplements.
    Uses category-first approach with resume capability.
    """

    def __init__(self, resume: bool = False, workers: int = None,
                 fetcher: BaseFetcher = None, proxy: str = None,
                 fetcher_backend: str = None):
        """
        Initialize spider.

        Args:
            resume: If True, resume from last checkpoint
            workers: Number of concurrent workers
            fetcher: Pre-configured fetcher instance
            proxy: Proxy URL string
            fetcher_backend: Fetcher backend name
        """
        self.state_manager = StateManager()
        self.exporter = DataExporter()
        self.resume = resume
        self.workers = workers or SCRAPING_SETTINGS["workers"]
        self.proxy = proxy
        self.fetcher = fetcher or create_fetcher(
            backend=fetcher_backend, proxy=proxy
        )
        self.stats = {
            "products_scraped": 0,
            "products_skipped": 0,
            "validation_passed": 0,
            "validation_failed": 0,
            "fetch_errors": 0,
            "extraction_errors": 0,
            "errors": []
        }

        # Thread safety locks
        self._stats_lock = threading.Lock()
        self._exporter_lock = threading.Lock()
        self._state_lock = threading.Lock()

        # Load existing ASINs if resuming
        if resume:
            self.exporter.load_existing_asins()
            resume_point = self.state_manager.get_resume_point()
            print(f"Resuming from category: {resume_point['category']}")
            print(f"Products already scraped: {resume_point['products_scraped']}")

    def initialize_browser_settings(self) -> None:
        """Initialize browser settings by setting US delivery location once"""
        print("\n[Initialization] Setting up US delivery location for USD pricing...")
        try:
            self.fetcher.fetch(
                'https://www.amazon.com',
                network_idle=True,
                timeout=30000,
                page_action=set_usd_currency,
                block_webrtc=False,
                google_search=False,
            )
            print("✓ Initialization complete")
            print("  Waiting 5 seconds before starting scrape...\n")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️  Could not initialize delivery location: {str(e)[:150]}")
            print("  Continuing with default location (prices may not be in USD)\n")

    def start(self) -> None:
        """Start the scraping process"""
        print("=" * 80)
        print("Amazon Supplement Scraper")
        print("=" * 80)
        print(f"Categories to scrape: {len(CATEGORIES)}")
        print(f"Resume mode: {'ON' if self.resume else 'OFF'}")
        print(f"Workers: {self.workers}")
        print("=" * 80)

        for category_name, category_url in CATEGORIES.items():
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
        max_pages = 50

        while page_num <= max_pages:
            print(f"\n  [Page {page_num}] Fetching product listings...")

            asins = self.extract_asins_from_listing(category_url, page_num)

            if not asins:
                print(f"  No products found on page {page_num}. End of category.")
                break

            print(f"  Found {len(asins)} products")

            # Filter already-scraped ASINs
            with self._exporter_lock:
                new_asins = [a for a in asins if not self.exporter.is_already_scraped(a)]

            skipped = len(asins) - len(new_asins)
            if skipped:
                print(f"  Skipping {skipped} already-scraped products")
                with self._stats_lock:
                    self.stats["products_skipped"] += skipped

            if new_asins:
                self._scrape_products_concurrent(new_asins, category_name)

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
        url = base_url
        if page_num > 1:
            url = f"{url}&page={page_num}"
        if "currency=USD" not in url:
            url = f"{url}&currency=USD"

        try:
            response = self.fetcher.fetch(url)

            asins = []

            for elem in response.css(SELECTORS["product_asin"]):
                asin = elem.attrib.get("data-asin", "")
                if asin and asin.startswith("B") and len(asin) == 10:
                    if asin not in asins:
                        asins.append(asin)

            return asins

        except FetchError as e:
            print(f"\n  Error fetching listing page (all retries exhausted): {e}")
            with self._stats_lock:
                self.stats["fetch_errors"] += 1
                self.stats["errors"].append(f"Listing page {page_num}: {str(e)}")
            return []
        except Exception as e:
            print(f"\n  Error fetching listing page: {e}")
            with self._stats_lock:
                self.stats["errors"].append(f"Listing page {page_num}: {str(e)}")
            return []

    def _scrape_products_concurrent(self, asins: List[str], category_name: str) -> None:
        """
        Scrape products concurrently using a thread pool.

        Args:
            asins: List of ASINs to scrape
            category_name: Category name for organizing output
        """
        total = len(asins)
        print(f"  Scraping {total} products with {self.workers} workers...")

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self._scrape_single_product_worker, asin, category_name): asin
                for asin in asins
            }

            completed = 0
            for future in as_completed(futures):
                asin = futures[future]
                completed += 1
                try:
                    success = future.result()
                    status = "✓" if success else "✗"
                    print(f"  [{completed}/{total}] {asin} {status}")
                except Exception as e:
                    print(f"  [{completed}/{total}] {asin} ✗ (unexpected: {str(e)[:80]})")
                    with self._stats_lock:
                        self.stats["errors"].append(f"Worker {asin}: {str(e)}")

                # Checkpoint if needed
                with self._state_lock:
                    if self.state_manager.should_checkpoint():
                        self.state_manager.save_checkpoint()
                        print("  [Checkpoint saved]")

    def _scrape_single_product_worker(self, asin: str, category: str) -> bool:
        """
        Worker method to scrape a single product. Runs in a thread.

        Each worker creates its own fetcher instance for thread isolation.

        Args:
            asin: Product ASIN
            category: Category name

        Returns:
            True if successful, False otherwise
        """
        # Each worker gets its own fetcher (StealthyFetcher spawns a new browser per call)
        worker_fetcher = create_fetcher(
            backend=SCRAPING_SETTINGS["fetcher_backend"],
            proxy=self.proxy,
        )

        product_url = f"https://www.amazon.com/dp/{asin}?currency=USD"

        try:
            response = worker_fetcher.fetch(product_url)
        except FetchError as e:
            with self._stats_lock:
                self.stats["fetch_errors"] += 1
                self.stats["errors"].append(f"Fetch {asin}: {str(e)}")
            return False

        # Extraction is not retried — failures are data issues, not transient
        try:
            scraper = ProductScraper(response)
            product_data = scraper.extract_product_data()

            review_extractor = ReviewExtractor(response)
            product_data["reviews"] = review_extractor.extract_reviews()
        except Exception as e:
            with self._stats_lock:
                self.stats["extraction_errors"] += 1
                self.stats["errors"].append(f"Extract {asin}: {str(e)}")
            return False

        # Save product data under lock
        with self._exporter_lock:
            success, message = self.exporter.save_product(product_data, category)

        if success:
            with self._state_lock:
                self.state_manager.add_scraped_asin(asin)
            with self._stats_lock:
                self.stats["products_scraped"] += 1
                self.stats["validation_passed"] += 1
        else:
            with self._stats_lock:
                self.stats["validation_failed"] += 1

        # Respectful delay per worker
        delay = SCRAPING_SETTINGS["delay_between_products"]
        time.sleep(delay)

        return success

    def refresh_asins(self, asin_category_pairs: List[Tuple[str, str]]) -> None:
        """
        Re-scrape specific products by removing them from the scraped set
        and re-running the scraper for each category group.

        Args:
            asin_category_pairs: List of (asin, category) tuples to refresh
        """
        if not asin_category_pairs:
            print("No ASINs to refresh.")
            return

        # Remove ASINs from scraped set so they bypass the "already scraped" check
        for asin, _ in asin_category_pairs:
            self.exporter.scraped_asins.discard(asin)

        # Group by category
        by_category: dict[str, list[str]] = defaultdict(list)
        for asin, category in asin_category_pairs:
            by_category[category].append(asin)

        print(f"\nRefreshing {len(asin_category_pairs)} products across {len(by_category)} categories")

        for category, asins in by_category.items():
            print(f"\n  [{category}] Refreshing {len(asins)} products...")
            self._scrape_products_concurrent(asins, category)

    def print_final_stats(self) -> None:
        """Print final statistics"""
        print("\n" + "=" * 80)
        print("Scraping Complete!")
        print("=" * 80)
        print(f"Total products scraped: {self.stats['products_scraped']}")
        print(f"Products skipped: {self.stats['products_skipped']}")
        print(f"Validation passed: {self.stats['validation_passed']}")
        print(f"Validation failed: {self.stats['validation_failed']}")
        print(f"Fetch errors: {self.stats['fetch_errors']}")
        print(f"Extraction errors: {self.stats['extraction_errors']}")
        print("=" * 80)
