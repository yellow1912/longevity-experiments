"""
Data Export Module
Handles saving product data to JSON files and SQLite with validation
"""
import os
from pathlib import Path
from typing import Dict, Any, Set
from .utils import save_json, ensure_directory, timestamp_iso
from .validators import validate_product
from .config import OUTPUT_SETTINGS, PARTNER_TAG, DATABASE_SETTINGS
from .database import Database


class DataExporter:
    """
    Exports product data to SQLite (primary) and JSON files (secondary).
    Organizes files by category and tracks scraped ASINs.
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize exporter.

        Args:
            data_dir: Base directory for scraped data
        """
        self.data_dir = data_dir or OUTPUT_SETTINGS["data_dir"]
        self.scraped_asins: Set[str] = set()
        self.db = Database()
        ensure_directory(self.data_dir)

    def is_already_scraped(self, asin: str) -> bool:
        """Check if ASIN has already been scraped"""
        return asin in self.scraped_asins

    def save_product(self, product: Dict[str, Any], category: str) -> tuple[bool, str]:
        """
        Save product data to SQLite and optionally JSON.

        Args:
            product: Product data dictionary
            category: Category name for organization

        Returns:
            (success: bool, message: str)
        """
        # Validate product data
        validation = validate_product(product, PARTNER_TAG, self.scraped_asins)

        # Add validation results to product
        product["validation"] = {
            "passed": validation.passed,
            "errors": validation.errors,
            "warnings": validation.warnings
        }

        # Add metadata
        product["scraped_at"] = timestamp_iso()
        product["category"] = category

        if not validation.passed:
            asin = product.get("asin", "unknown")
            self.db.log_scrape(asin, success=False, error=", ".join(validation.errors))
            error_msg = f"Validation failed: {', '.join(validation.errors)}"
            return False, error_msg

        asin = product["asin"]

        # Primary storage: SQLite
        try:
            reviews = product.get("reviews", [])
            self.db.upsert_product(product)
            if reviews:
                self.db.insert_reviews(asin, reviews)
            self.db.log_scrape(asin, success=True)
        except Exception as e:
            self.db.log_scrape(asin, success=False, error=str(e))
            return False, f"Database error for {asin}: {str(e)}"

        # Secondary storage: JSON (if enabled)
        if DATABASE_SETTINGS["write_json"]:
            category_dir = os.path.join(self.data_dir, category)
            ensure_directory(category_dir)
            filepath = os.path.join(category_dir, f"{asin}.json")
            try:
                save_json(product, filepath, indent=OUTPUT_SETTINGS["json_indent"])
            except Exception as e:
                # JSON write failure is non-fatal since DB is primary
                pass

        self.scraped_asins.add(asin)

        # Log warnings if any
        if validation.warnings:
            warnings_msg = f" (warnings: {', '.join(validation.warnings)})"
        else:
            warnings_msg = ""

        return True, f"Saved {asin}{warnings_msg}"

    def load_existing_asins(self) -> None:
        """Load ASINs from DB first, supplement from JSON directory"""
        # Load from database (primary)
        self.scraped_asins = self.db.get_all_asins()

        # Supplement from JSON files
        if os.path.exists(self.data_dir):
            for category_dir in Path(self.data_dir).iterdir():
                if category_dir.is_dir():
                    for json_file in category_dir.glob("*.json"):
                        self.scraped_asins.add(json_file.stem)

        print(f"Loaded {len(self.scraped_asins)} existing ASINs")
