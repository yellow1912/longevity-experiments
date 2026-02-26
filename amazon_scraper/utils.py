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


def set_usd_currency(page):
    """
    Page action function to set US delivery location for USD pricing.
    Sets delivery location to US address, which forces USD currency.
    Use this with StealthyFetcher's page_action parameter.

    Args:
        page: Playwright page object

    Returns:
        page: The page object (required by Scrapling)
    """
    try:
        # Set locale preferences cookie
        page.context.add_cookies([{
            'name': 'lc-main',
            'value': 'en_US',
            'domain': '.amazon.com',
            'path': '/',
            'sameSite': 'Lax'
        }])

        # Navigate to Amazon homepage first to set delivery location
        current_url = page.url
        if 'amazon.com' not in current_url:
            # If we haven't loaded an Amazon page yet, go to homepage
            page.goto('https://www.amazon.com', wait_until='domcontentloaded', timeout=30000)

        # Wait for page to be interactive
        page.wait_for_load_state('networkidle', timeout=15000)

        # Use browser automation to set delivery location to US
        try:
            # Look for the delivery location selector
            deliver_to = page.locator('#nav-global-location-popover-link')
            if deliver_to.count() > 0 and deliver_to.first.is_visible(timeout=5000):
                deliver_to.first.click()
                page.wait_for_timeout(1500)

                # Enter US zip code (10001 = New York City)
                zip_input = page.locator('#GLUXZipUpdateInput')
                if zip_input.count() > 0 and zip_input.is_visible(timeout=3000):
                    zip_input.fill('10001')
                    page.wait_for_timeout(500)

                    # Click apply button
                    apply_button = page.locator('input[aria-labelledby="GLUXZipUpdate-announce"]')
                    if apply_button.count() > 0:
                        apply_button.click()
                        page.wait_for_timeout(2000)
                        print("✓ US delivery location set (ZIP: 10001 - NYC) - USD pricing enabled")
                        return page

            print("⚠️  Could not find/click delivery location selector")
        except Exception as e:
            print(f"⚠️  Delivery location automation error: {str(e)[:100]}")

    except Exception as e:
        print(f"⚠️  Error in set_usd_currency: {str(e)[:100]}")

    return page


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
