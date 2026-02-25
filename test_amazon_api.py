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
