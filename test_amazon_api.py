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
