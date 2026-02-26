"""
Data Export Module
Handles saving product data to JSON files with validation
"""
import os
from pathlib import Path
from typing import Dict, Any, Set
from .utils import save_json, ensure_directory, timestamp_iso
from .validators import validate_product
from .config import OUTPUT_SETTINGS, PARTNER_TAG


class DataExporter:
    """
    Exports product data to JSON files with validation.
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
        ensure_directory(self.data_dir)

    def is_already_scraped(self, asin: str) -> bool:
        """Check if ASIN has already been scraped"""
        return asin in self.scraped_asins

    def save_product(self, product: Dict[str, Any], category: str) -> tuple[bool, str]:
        """
        Save product data to JSON file with validation.

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
            error_msg = f"Validation failed: {', '.join(validation.errors)}"
            return False, error_msg

        # Save to category directory
        category_dir = os.path.join(self.data_dir, category)
        ensure_directory(category_dir)

        asin = product["asin"]
        filepath = os.path.join(category_dir, f"{asin}.json")

        try:
            save_json(product, filepath, indent=OUTPUT_SETTINGS["json_indent"])
            self.scraped_asins.add(asin)

            # Log warnings if any
            if validation.warnings:
                warnings_msg = f" (warnings: {', '.join(validation.warnings)})"
            else:
                warnings_msg = ""

            return True, f"Saved {asin}.json{warnings_msg}"

        except Exception as e:
            return False, f"Failed to save {asin}: {str(e)}"

    def load_existing_asins(self) -> None:
        """Load ASINs from existing JSON files to avoid duplicates"""
        if not os.path.exists(self.data_dir):
            return

        for category_dir in Path(self.data_dir).iterdir():
            if category_dir.is_dir():
                for json_file in category_dir.glob("*.json"):
                    asin = json_file.stem  # filename without extension
                    self.scraped_asins.add(asin)

        print(f"Loaded {len(self.scraped_asins)} existing ASINs")
