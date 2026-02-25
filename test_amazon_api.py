"""
Amazon Affiliate API Test Script
Tests PA-API credentials and retrieves supplement product data
"""
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

from paapi5_python_sdk import (
    DefaultApi,
    PartnerType,
    SearchItemsRequest,
    SearchItemsResource,
    ProductAdvertisingAPIClientException,
    ApiException,
)


def load_credentials(csv_path: str = "Longevity-credentials.csv") -> Dict[str, str]:
    """
    Load Amazon PA-API credentials from CSV file.

    Args:
        csv_path: Path to credentials CSV file

    Returns:
        Dictionary with 'partner_tag', 'access_key', 'secret_key'

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
            partner_tag = creds.get('Application Id', '').strip()
            access_key = creds.get('Credential Id', '').strip()
            secret_key = creds.get('Secret', '').strip()

            if not all([partner_tag, access_key, secret_key]):
                raise ValueError(
                    "Missing required fields in CSV. "
                    "Expected: 'Application Id', 'Credential Id', 'Secret'"
                )

            return {
                'partner_tag': partner_tag,
                'access_key': access_key,
                'secret_key': secret_key
            }

    except csv.Error as e:
        raise ValueError(f"Error parsing CSV file: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error loading credentials: {e}")


def initialize_api_client(credentials: Dict[str, str]) -> DefaultApi:
    """
    Initialize Amazon PA-API client with credentials.

    Args:
        credentials: Dictionary with partner_tag, access_key, secret_key

    Returns:
        Configured DefaultApi client instance
    """
    try:
        api_client = DefaultApi(
            access_key=credentials['access_key'],
            secret_key=credentials['secret_key'],
            host='webservices.amazon.com',
            region='us-east-1'
        )
        return api_client
    except Exception as e:
        raise RuntimeError(f"Failed to initialize API client: {e}")


def search_supplements(
    api_client: DefaultApi,
    partner_tag: str,
    keyword: str = "vitamin D supplement",
    item_count: int = 10
) -> Optional[object]:
    """
    Search for supplement products using PA-API SearchItems operation.

    Args:
        api_client: Configured DefaultApi instance
        partner_tag: Amazon affiliate partner tag
        keyword: Search keyword
        item_count: Number of results to return (max 10)

    Returns:
        SearchItemsResponse object or None if no results

    Raises:
        ApiException: If API call fails
    """
    # Define which product data fields to retrieve
    search_items_resource = [
        SearchItemsResource.IMAGES_PRIMARY_LARGE,
        SearchItemsResource.ITEMINFO_TITLE,
        SearchItemsResource.ITEMINFO_BYLINEINFO,
        SearchItemsResource.ITEMINFO_FEATURES,
        SearchItemsResource.OFFERS_LISTINGS_PRICE,
        SearchItemsResource.CUSTOMERREVIEWS_STARRRATING,
        SearchItemsResource.CUSTOMERREVIEWS_COUNT,
    ]

    # Create search request
    try:
        search_items_request = SearchItemsRequest(
            partner_tag=partner_tag,
            partner_type=PartnerType.ASSOCIATES,
            keywords=keyword,
            item_count=item_count,
            resources=search_items_resource,
            marketplace="www.amazon.com"
        )
    except Exception as e:
        raise ValueError(f"Failed to create search request: {e}")

    # Execute search
    try:
        print(f"Searching for: '{keyword}'...")
        response = api_client.search_items(search_items_request)

        if response.search_result is None:
            print("No results found")
            return None

        if response.errors:
            print("API returned errors:")
            for error in response.errors:
                print(f"  - {error.code}: {error.message}")
            return None

        return response

    except ApiException as e:
        error_msg = f"API call failed (HTTP {e.status})"

        if e.status == 401:
            error_msg += "\nAuthentication failed. Check your credentials."
        elif e.status == 429:
            error_msg += "\nRate limit exceeded. Wait a moment and try again."
        elif e.status == 400:
            error_msg += f"\nBad request. Check your partner tag and search parameters."

        raise ApiException(status=e.status, reason=error_msg)


def format_product_data(response: object) -> List[Dict[str, any]]:
    """
    Extract and format product data from API response.

    Args:
        response: SearchItemsResponse object

    Returns:
        List of formatted product dictionaries
    """
    if not response or not response.search_result or not response.search_result.items:
        return []

    products = []

    for item in response.search_result.items:
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

        # Extract price
        if (item.offers and item.offers.listings and
            len(item.offers.listings) > 0):
            listing = item.offers.listings[0]
            if listing.price:
                product['price'] = (
                    f"${listing.price.amount:.2f} {listing.price.currency}"
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
        print(f"✓ Loaded partner tag: {credentials['partner_tag']}")

        # Step 2: Initialize API client
        print("\n[2/4] Initializing Amazon PA-API client...")
        api_client = initialize_api_client(credentials)
        print("✓ API client initialized")

        # Step 3: Search for supplements
        print("\n[3/4] Searching for supplements...")
        response = search_supplements(
            api_client=api_client,
            partner_tag=credentials['partner_tag'],
            keyword="vitamin D supplement",
            item_count=10
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
    except ApiException as e:
        print(f"\n✗ API Error: {e.reason if hasattr(e, 'reason') else e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
