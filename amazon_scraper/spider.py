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

        # This method will be implemented in Part 2
        print(f"Scraping category: {category_name}")
        print("(Implementation continued in next task)")

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
