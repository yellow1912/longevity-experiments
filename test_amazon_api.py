"""
Amazon Affiliate API Test Script
Tests Creator API credentials and retrieves supplement product data
"""
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

from amazon_creatorsapi import AmazonCreatorsApi, Country


def load_credentials(csv_path: str = "Longevity-credentials.csv") -> Dict[str, str]:
    """
    Load Amazon Creator API credentials from CSV file.

    Args:
        csv_path: Path to credentials CSV file

    Returns:
        Dictionary with 'tag', 'credential_id', 'credential_secret', 'version'

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV is malformed or missing required fields
    """
    csv_file = Path(csv_path)

    if not csv_file.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {csv_path}\n"
            f"Expected location: {csv_file.absolute()}"
        )

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            if not rows:
                raise ValueError("CSV file is empty")

            # Get first row (should only be one)
            creds = rows[0]

            # Extract and validate required fields
            tag = creds.get('Application Id', '').strip()
            credential_id = creds.get('Credential Id', '').strip()
            credential_secret = creds.get('Secret', '').strip()
            version = creds.get('Version', '2.2').strip()  # Default to 2.2 if not specified

            if not all([tag, credential_id, credential_secret]):
                raise ValueError(
                    "Missing required fields in CSV. "
                    "Expected: 'Application Id', 'Credential Id', 'Secret'"
                )

            return {
                'tag': tag,
                'credential_id': credential_id,
                'credential_secret': credential_secret,
                'version': version
            }

    except csv.Error as e:
        raise ValueError(f"Error parsing CSV file: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error loading credentials: {e}")


def initialize_api_client(credentials: Dict[str, str]) -> AmazonCreatorsApi:
    """
    Initialize Amazon Creator API client with credentials.

    Args:
        credentials: Dictionary with tag, credential_id, credential_secret, version

    Returns:
        Configured AmazonCreatorsApi client instance
    """
    try:
        api = AmazonCreatorsApi(
            credential_id=credentials['credential_id'],
            credential_secret=credentials['credential_secret'],
            version=credentials['version'],
            tag=credentials['tag'],
            country=Country.US,
            throttling=1  # 1 second between requests to avoid rate limits
        )
        return api
    except Exception as e:
        raise RuntimeError(f"Failed to initialize API client: {e}")


def search_supplements(
    api_client: AmazonCreatorsApi,
    keyword: str = "vitamin D supplement"
) -> Optional[object]:
    """
    Search for supplement products using Creator API SearchItems operation.

    Args:
        api_client: Configured AmazonCreatorsApi instance
        keyword: Search keyword

    Returns:
        SearchItemsResponse object or None if no results

    Raises:
        Exception: If API call fails
    """
    try:
        print(f"Searching for: '{keyword}'...")
        response = api_client.search_items(keywords=keyword)

        if not response or not response.items:
            print("No results found")
            return None

        return response

    except Exception as e:
        error_msg = f"API call failed: {str(e)}"

        # Check for common error patterns
        error_str = str(e).lower()
        if '401' in error_str or 'unauthorized' in error_str or 'authentication' in error_str:
            error_msg += "\n\nAuthentication failed. Possible reasons:"
            error_msg += "\n  - Invalid or expired credential_id/credential_secret"
            error_msg += "\n  - Credentials not associated with Creator API"
            error_msg += "\n  - Partner tag not registered or inactive"
        elif '403' in error_str or 'accessdeniedexception' in error_str or 'not eligible' in error_str:
            error_msg += "\n\nAccount eligibility issue. This means:"
            error_msg += "\n  - Your credentials ARE valid and working correctly"
            error_msg += "\n  - Your Amazon Associates account needs to meet eligibility requirements"
            error_msg += "\n  - Check https://affiliate-program.amazon.com/ for account status"
            error_msg += "\n  - You may need to:"
            error_msg += "\n    • Complete your account profile"
            error_msg += "\n    • Add and verify your website/app"
            error_msg += "\n    • Meet minimum traffic or sales requirements"
        elif '429' in error_str or 'rate limit' in error_str:
            error_msg += "\nRate limit exceeded. Wait a moment and try again."
        elif '400' in error_str or 'bad request' in error_str:
            error_msg += "\nBad request. Check your credentials and search parameters."

        raise RuntimeError(error_msg)


def format_product_data(response: object) -> List[Dict[str, any]]:
    """
    Extract and format product data from Creator API response.

    Args:
        response: SearchItemsResponse object from Creator API

    Returns:
        List of formatted product dictionaries
    """
    if not response or not response.items:
        return []

    products = []

    for item in response.items:
        product = {
            'asin': item.asin,
            'title': 'N/A',
            'brand': 'N/A',
            'price': 'N/A',
            'rating': 'N/A',
            'review_count': 0,
            'url': item.detail_page_url if item.detail_page_url else 'N/A',
            'image': 'N/A',
            'features': []
        }

        # Extract title
        if item.item_info and item.item_info.title:
            product['title'] = item.item_info.title.display_value

        # Extract brand
        if (item.item_info and item.item_info.by_line_info and
            item.item_info.by_line_info.brand):
            product['brand'] = item.item_info.by_line_info.brand.display_value

        # Extract price - UPDATED for Creator API (offers_v2)
        if (item.offers_v2 and item.offers_v2.listings and
            len(item.offers_v2.listings) > 0):
            listing = item.offers_v2.listings[0]
            if listing.price and listing.price.money:
                product['price'] = (
                    f"${listing.price.money.amount:.2f} {listing.price.money.currency_code}"
                )

        # Extract rating
        if (item.customer_reviews and item.customer_reviews.star_rating):
            product['rating'] = item.customer_reviews.star_rating.display_value
            if item.customer_reviews.count:
                product['review_count'] = item.customer_reviews.count

        # Extract image
        if (item.images and item.images.primary and
            item.images.primary.large):
            product['image'] = item.images.primary.large.url

        # Extract features (first 3)
        if (item.item_info and item.item_info.features and
            item.item_info.features.display_values):
            product['features'] = item.item_info.features.display_values[:3]

        products.append(product)

    return products


def display_products(products: List[Dict[str, any]]) -> None:
    """
    Display formatted product information to console.

    Args:
        products: List of product dictionaries
    """
    if not products:
        print("\nNo products to display.")
        return

    print(f"\nFound {len(products)} products:\n")
    print("=" * 80)

    for idx, product in enumerate(products, 1):
        print(f"\n{idx}. {product['title']}")
        print(f"   Brand: {product['brand']}")
        print(f"   ASIN: {product['asin']}")
        print(f"   Price: {product['price']}")
        print(f"   Rating: {product['rating']}", end="")
        if product['review_count']:
            print(f" ({product['review_count']:,} reviews)")
        else:
            print()
        print(f"   Link: {product['url']}")
        print(f"   Image: {product['image']}")

        if product['features']:
            print("   Key Features:")
            for feature in product['features']:
                # Truncate long features
                feature_text = feature if len(feature) <= 70 else feature[:67] + "..."
                print(f"     • {feature_text}")

        print("-" * 80)


def main():
    """
    Main function to orchestrate the credential test workflow.
    """
    print("=" * 80)
    print("Amazon Affiliate API Test Script")
    print("=" * 80)

    try:
        # Step 1: Load credentials
        print("\n[1/4] Loading credentials...")
        credentials = load_credentials()
        print(f"✓ Loaded affiliate tag: {credentials['tag']}")

        # Step 2: Initialize API client
        print("\n[2/4] Initializing Amazon Creator API client...")
        api_client = initialize_api_client(credentials)
        print("✓ API client initialized")

        # Step 3: Search for supplements
        print("\n[3/4] Searching for supplements...")
        response = search_supplements(
            api_client=api_client,
            keyword="vitamin D supplement"
        )

        if response:
            print("✓ Search completed successfully")
        else:
            print("✗ Search returned no results")
            return

        # Step 4: Format and display results
        print("\n[4/4] Formatting results...")
        products = format_product_data(response)
        print(f"✓ Formatted {len(products)} products")

        display_products(products)

        # Verify affiliate tag in URLs
        print("\n" + "=" * 80)
        print("Verification:")
        if products and 'longevityhe09-20' in products[0]['url']:
            print("✓ Affiliate tag present in URLs")
        else:
            print("✗ Warning: Affiliate tag not found in URLs")

        print("\n✓ Test completed successfully!")
        print("=" * 80)

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n✗ Credential Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"\n✗ API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
