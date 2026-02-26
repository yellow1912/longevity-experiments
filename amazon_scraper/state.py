"""
State Management Module
Tracks scraping progress and enables resume capability
"""
import os
from typing import Dict, Any, Set
from .utils import save_json, load_json, timestamp_iso
from .config import OUTPUT_SETTINGS


class StateManager:
    """
    Manages scraping state for resume capability.
    Tracks current category, page, ASINs processed.
    """

    def __init__(self, state_file: str = None):
        """
        Initialize state manager.

        Args:
            state_file: Path to state JSON file
        """
        self.state_file = state_file or OUTPUT_SETTINGS["state_file"]
        self.state = self.load_state()

    def load_state(self) -> Dict[str, Any]:
        """Load state from file or create new state"""
        if os.path.exists(self.state_file):
            return load_json(self.state_file)
        return self.create_initial_state()

    def create_initial_state(self) -> Dict[str, Any]:
        """Create initial empty state"""
        return {
            "current_category": None,
            "current_page": 1,
            "last_asin": None,
            "completed_categories": [],
            "total_products_scraped": 0,
            "started_at": timestamp_iso(),
            "last_checkpoint": timestamp_iso(),
            "scraped_asins": []
        }

    def save_checkpoint(self) -> None:
        """Save current state to file"""
        self.state["last_checkpoint"] = timestamp_iso()
        save_json(self.state, self.state_file, indent=2)

    def start_category(self, category: str) -> None:
        """Mark category as started"""
        self.state["current_category"] = category
        self.state["current_page"] = 1
        self.save_checkpoint()

    def complete_category(self, category: str) -> None:
        """Mark category as completed"""
        if category not in self.state["completed_categories"]:
            self.state["completed_categories"].append(category)
        self.state["current_category"] = None
        self.state["current_page"] = 1
        self.save_checkpoint()

    def increment_page(self) -> None:
        """Increment current page number"""
        self.state["current_page"] += 1
        self.save_checkpoint()

    def add_scraped_asin(self, asin: str) -> None:
        """Record scraped ASIN"""
        if asin not in self.state["scraped_asins"]:
            self.state["scraped_asins"].append(asin)
        self.state["last_asin"] = asin
        self.state["total_products_scraped"] += 1

    def should_checkpoint(self) -> bool:
        """Check if it's time to save checkpoint"""
        interval = OUTPUT_SETTINGS.get("checkpoint_interval", 50)
        return self.state["total_products_scraped"] % interval == 0

    def get_scraped_asins(self) -> Set[str]:
        """Get set of scraped ASINs"""
        return set(self.state.get("scraped_asins", []))

    def is_category_completed(self, category: str) -> bool:
        """Check if category already completed"""
        return category in self.state.get("completed_categories", [])

    def get_resume_point(self) -> Dict[str, Any]:
        """Get information about where to resume"""
        return {
            "category": self.state.get("current_category"),
            "page": self.state.get("current_page", 1),
            "products_scraped": self.state.get("total_products_scraped", 0),
            "last_asin": self.state.get("last_asin")
        }
