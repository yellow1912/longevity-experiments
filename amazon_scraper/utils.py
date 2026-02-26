"""
Utility Functions
Helper functions for scraping, file operations, and data processing
"""
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def generate_affiliate_link(asin: str, partner_tag: str) -> str:
    """
    Programmatically generate Amazon affiliate link from ASIN.

    Args:
        asin: Amazon Standard Identification Number
        partner_tag: Amazon affiliate partner tag

    Returns:
        Full affiliate URL with partner tag
    """
    return f"https://www.amazon.com/dp/{asin}?tag={partner_tag}"


def extract_asin_from_url(url: str) -> str:
    """
    Extract ASIN from Amazon product URL.

    Args:
        url: Amazon product URL

    Returns:
        ASIN string or empty string if not found
    """
    # Common patterns: /dp/B123456789/ or /gp/product/B123456789
    import re
    pattern = r"/(?:dp|gp/product)/([B][0-9A-Z]{9})"
    match = re.search(pattern, url)
    return match.group(1) if match else ""


def ensure_directory(path: str) -> Path:
    """
    Create directory if it doesn't exist.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def save_json(data: Dict[str, Any], filepath: str, indent: int = 2) -> None:
    """
    Save data to JSON file.

    Args:
        data: Dictionary to save
        filepath: Output file path
        indent: JSON indentation level
    """
    # Ensure parent directory exists
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first, then rename (atomic operation)
    temp_file = f"{filepath}.tmp"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)

    os.replace(temp_file, filepath)


def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load data from JSON file.

    Args:
        filepath: Input file path

    Returns:
        Dictionary or empty dict if file doesn't exist
    """
    if not os.path.exists(filepath):
        return {}

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def timestamp_iso() -> str:
    """Get current timestamp in ISO format"""
    return datetime.utcnow().isoformat() + 'Z'


def sleep_with_message(seconds: int, message: str = "Waiting") -> None:
    """Sleep with progress message"""
    print(f"{message}... ({seconds}s)")
    time.sleep(seconds)
