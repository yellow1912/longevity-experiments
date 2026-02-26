"""
Data Validation Module
Validates scraped product data for quality and completeness
"""
import re
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of product validation"""
    passed: bool
    errors: List[str]
    warnings: List[str]


def validate_asin(asin: str) -> bool:
    """
    Validate Amazon ASIN format.
    Format: B followed by 9 alphanumeric characters
    """
    if not asin:
        return False
    pattern = r"^B[0-9A-Z]{9}$"
    return bool(re.match(pattern, asin))


def validate_title(title: str) -> tuple[bool, str]:
    """Validate product title"""
    if not title or title == "N/A":
        return False, "Title is missing"
    if len(title) < 10:
        return False, "Title too short (< 10 chars)"
    if len(title) > 500:
        return False, "Title too long (> 500 chars)"
    if title.lower() in ["product", "item"]:
        return False, "Title is generic placeholder"
    return True, ""


def validate_price(price: str) -> tuple[bool, str]:
    """Validate price format"""
    if not price:
        return False, "Price is missing"
    if price in ["N/A", "Currently unavailable"]:
        return True, ""  # These are acceptable
    pattern = r"^\$[\d,]+\.\d{2}$"
    if not re.match(pattern, price):
        return False, f"Invalid price format: {price}"
    return True, ""


def validate_affiliate_url(url: str, partner_tag: str) -> tuple[bool, str]:
    """Validate affiliate URL contains partner tag"""
    if not url:
        return False, "URL is missing"
    if partner_tag not in url:
        return False, f"URL missing partner tag: {partner_tag}"
    if not url.startswith("https://www.amazon.com/dp/"):
        return False, "URL format incorrect"
    return True, ""


def validate_product(product: Dict[str, Any], partner_tag: str, scraped_asins: set = None) -> ValidationResult:
    """
    Comprehensive product validation.
    Returns ValidationResult with pass/fail, errors, and warnings.
    """
    errors = []
    warnings = []

    # Required field validations
    if not validate_asin(product.get("asin", "")):
        errors.append("Invalid ASIN format")

    title_valid, title_error = validate_title(product.get("title", ""))
    if not title_valid:
        errors.append(title_error)

    price_valid, price_error = validate_price(product.get("price", ""))
    if not price_valid:
        errors.append(price_error)

    url_valid, url_error = validate_affiliate_url(product.get("affiliate_url", ""), partner_tag)
    if not url_valid:
        errors.append(url_error)

    # Check for duplicates
    if scraped_asins and product.get("asin") in scraped_asins:
        errors.append(f"Duplicate ASIN: {product.get('asin')}")

    # Optional field warnings
    if not product.get("description") or len(product.get("description", [])) == 0:
        warnings.append("No product description/features found")

    if not product.get("images") or len(product.get("images", [])) == 0:
        warnings.append("No product images found")

    if not product.get("brand") or product.get("brand") == "N/A":
        warnings.append("Brand information missing")

    if not product.get("reviews") or len(product.get("reviews", [])) == 0:
        warnings.append("No reviews found")

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
