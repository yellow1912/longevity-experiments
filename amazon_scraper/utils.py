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
        # Wait for page to be fully loaded
        page.wait_for_load_state('networkidle', timeout=10000)
        page.wait_for_timeout(2000)

        # Use browser automation to set delivery location to US
        try:
            # Look for the delivery location selector
            deliver_to = page.locator('#nav-global-location-popover-link')
            if deliver_to.count() > 0:
                # Check current location before clicking
                try:
                    current_location = page.locator('#glow-ingress-line2').text_content(timeout=2000)
                    print(f"  Current delivery location: {current_location.strip() if current_location else 'Unknown'}")
                except:
                    pass

                print("  → Clicking delivery location selector...")
                deliver_to.first.click()

                # Wait for modal - try multiple possible elements
                try:
                    # Try waiting for the zip input or the modal container
                    page.wait_for_selector('#GLUXZipUpdateInput, #a-popover-content-3, .a-popover-wrapper', state='visible', timeout=10000)
                    page.wait_for_timeout(1500)
                    print("  → Modal opened, entering US zip code...")
                except Exception as modal_error:
                    print(f"  → Modal wait failed: {str(modal_error)[:100]}")
                    print("  → Trying to find zip input anyway...")

                # Try to find and fill zip input
                zip_input = page.locator('#GLUXZipUpdateInput')
                if zip_input.count() > 0 and zip_input.is_visible():
                    zip_input.fill('10001')
                    page.wait_for_timeout(800)
                    print("  → Zip code entered: 10001")

                    # Click apply button - try multiple selectors
                    apply_selectors = [
                        'input[aria-labelledby="GLUXZipUpdate-announce"]',
                        'button:has-text("Apply")',
                        '#GLUXZipUpdate-announce',
                        'span[id="GLUXZipUpdate"]',
                        '[name="glowDoneButton"]'
                    ]

                    for selector in apply_selectors:
                        apply_button = page.locator(selector)
                        if apply_button.count() > 0:
                            print(f"  → Clicking Apply button (found with: {selector[:30]}...)")
                            apply_button.first.click()
                            page.wait_for_timeout(3000)

                            # Verify location changed
                            try:
                                location_text = page.locator('#glow-ingress-line2').text_content(timeout=3000)
                                if location_text and location_text.strip():
                                    print(f"✓ US delivery location set - Location: {location_text.strip()}")
                                    return page
                            except:
                                pass

                            print("✓ Apply clicked - USD pricing should be enabled")
                            return page

                    print("⚠️  Could not find Apply button with any known selector")
                else:
                    print("⚠️  Zip input field not found or not visible - trying cookie-based approach...")
                    # Fallback: Set location cookie directly
                    page.context.add_cookies([{
                        'name': 'ubid-main',
                        'value': '134-8789256-8392306',  # US session ID format
                        'domain': '.amazon.com',
                        'path': '/'
                    }])
                    print("  → Set US session cookie as fallback")

            else:
                print("⚠️  Delivery location selector (#nav-global-location-popover-link) not found")

        except Exception as e:
            error_msg = str(e)[:200]
            print(f"⚠️  Delivery location error: {error_msg}")
            # Try cookie fallback
            try:
                page.context.add_cookies([{
                    'name': 'ubid-main',
                    'value': '134-8789256-8392306',
                    'domain': '.amazon.com',
                    'path': '/'
                }])
                print("  → Using cookie-based fallback for US location")
            except:
                pass

    except Exception as e:
        print(f"⚠️  Error in set_usd_currency: {str(e)[:200]}")

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
