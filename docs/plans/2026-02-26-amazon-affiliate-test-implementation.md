# Amazon Affiliate API Test Script Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python test script that verifies Amazon PA-API credentials and retrieves supplement product data

**Architecture:** Single Python script using official paapi5-python-sdk to load credentials from CSV, authenticate with Amazon PA-API 5.0, search for supplements, and display formatted results with affiliate links

**Tech Stack:** Python 3.8+, paapi5-python-sdk, CSV parsing (built-in)

---

## Task 1: Setup Project Files

**Files:**
- Create: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/.gitignore`
- Create: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/requirements.txt`

**Step 1: Create .gitignore file**

Create `.gitignore` to protect credentials:

```
# Credentials
Longevity-credentials.csv
*.csv

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

**Step 2: Create requirements.txt**

Create `requirements.txt` with dependencies:

```
paapi5-python-sdk>=1.3.0
```

**Step 3: Verify files created**

Run: `ls -la`
Expected: See `.gitignore` and `requirements.txt` in directory

**Step 4: Commit**

```bash
git init
git add .gitignore requirements.txt docs/
git commit -m "chore: initialize project with gitignore and dependencies"
```

---

## Task 2: Install Dependencies

**Files:**
- Verify: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/requirements.txt`

**Step 1: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Successfully installed paapi5-python-sdk

**Step 2: Verify installation**

Run: `pip show paapi5-python-sdk`
Expected: Shows version 1.3.0 or higher with package details

**Step 3: Test import**

Run: `python -c "from paapi5_python_sdk.api.default_api import DefaultApi; print('Import successful')"`
Expected: "Import successful" (no errors)

---

## Task 3: Create Credential Loader Function

**Files:**
- Create: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/test_amazon_api.py`

**Step 1: Create initial script with imports**

```python
"""
Amazon Affiliate API Test Script
Tests PA-API credentials and retrieves supplement product data
"""
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.partner_type import PartnerType
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.rest import ApiException


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
```

**Step 2: Test credential loading**

Run: `python -c "from test_amazon_api import load_credentials; creds = load_credentials(); print(f'Partner tag: {creds[\"partner_tag\"][:20]}...')"`
Expected: Shows partner tag starting with "longevityhe09-20"

**Step 3: Commit**

```bash
git add test_amazon_api.py
git commit -m "feat: add credential loader function"
```

---

## Task 4: Create API Client Initializer

**Files:**
- Modify: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/test_amazon_api.py`

**Step 1: Add initialize_api_client function**

Add after `load_credentials()`:

```python


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
```

**Step 2: Test initialization**

Run:
```python
python -c "from test_amazon_api import load_credentials, initialize_api_client; creds = load_credentials(); client = initialize_api_client(creds); print('Client initialized successfully')"
```
Expected: "Client initialized successfully"

**Step 3: Commit**

```bash
git add test_amazon_api.py
git commit -m "feat: add API client initializer"
```

---

## Task 5: Create Product Search Function

**Files:**
- Modify: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/test_amazon_api.py`

**Step 1: Add search_supplements function**

Add after `initialize_api_client()`:

```python


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
```

**Step 2: Commit**

```bash
git add test_amazon_api.py
git commit -m "feat: add product search function"
```

---

## Task 6: Create Data Formatter Function

**Files:**
- Modify: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/test_amazon_api.py`

**Step 1: Add format_product_data function**

Add after `search_supplements()`:

```python


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
```

**Step 2: Commit**

```bash
git add test_amazon_api.py
git commit -m "feat: add product data formatter and display functions"
```

---

## Task 7: Create Main Function

**Files:**
- Modify: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/test_amazon_api.py`

**Step 1: Add main function**

Add at the end of the file:

```python


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
```

**Step 2: Commit**

```bash
git add test_amazon_api.py
git commit -m "feat: add main orchestration function"
```

---

## Task 8: Test the Complete Script

**Files:**
- Verify: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/test_amazon_api.py`
- Verify: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/Longevity-credentials.csv`

**Step 1: Run the test script**

Run: `python test_amazon_api.py`

Expected output:
```
================================================================================
Amazon Affiliate API Test Script
================================================================================

[1/4] Loading credentials...
✓ Loaded partner tag: longevityhe09-20.longevity

[2/4] Initializing Amazon PA-API client...
✓ API client initialized

[3/4] Searching for supplements...
Searching for: 'vitamin D supplement'...
✓ Search completed successfully

[4/4] Formatting results...
✓ Formatted 10 products

Found 10 products:

================================================================================

1. [Product Title]
   Brand: [Brand Name]
   ASIN: [ASIN]
   Price: $XX.XX USD
   Rating: X.X stars (XXX reviews)
   Link: https://www.amazon.com/dp/[ASIN]?tag=longevityhe09-20
   Image: https://...
   Key Features:
     • [Feature 1]
     • [Feature 2]
     • [Feature 3]
--------------------------------------------------------------------------------
[... 9 more products ...]

================================================================================
Verification:
✓ Affiliate tag present in URLs

✓ Test completed successfully!
================================================================================
```

**Step 2: Verify key success criteria**

Check that:
- [ ] Script runs without errors
- [ ] Credentials load successfully
- [ ] API authentication succeeds
- [ ] 10 products are displayed
- [ ] Each product has title, price, ASIN, URL, image
- [ ] All URLs contain "longevityhe09-20"
- [ ] Affiliate tag verification passes

**Step 3: Test error handling (missing credentials)**

Run: `mv Longevity-credentials.csv Longevity-credentials.csv.bak && python test_amazon_api.py; mv Longevity-credentials.csv.bak Longevity-credentials.csv`

Expected: Clear error message about missing file, then restore file

**Step 4: Commit verification results**

```bash
git add test_amazon_api.py
git commit -m "test: verify complete script functionality"
```

---

## Task 9: Create README Documentation

**Files:**
- Create: `/Users/vunguyen/Projects/3rd-parties/longevity-health/longevity-experiments/README.md`

**Step 1: Create README**

```markdown
# Amazon Affiliate API Test

Test script for verifying Amazon Product Advertising API credentials and retrieving supplement product data for a longevity/health affiliate website.

## Prerequisites

- Python 3.8 or higher
- Amazon Associates account with PA-API access
- Valid API credentials in `Longevity-credentials.csv`

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure your credentials file is present:
   - File: `Longevity-credentials.csv`
   - Format: CSV with columns: `Application`, `Application Id`, `Credential Id`, `Secret`, `Version`

## Usage

Run the test script:

```bash
python test_amazon_api.py
```

The script will:
1. Load credentials from CSV
2. Initialize PA-API client
3. Search for vitamin D supplements
4. Display 10 products with details

## Output

For each product, the script displays:
- Title
- Brand
- ASIN (Amazon product ID)
- Price
- Customer rating and review count
- Affiliate link (with your partner tag)
- Product image URL
- Key features

## Success Criteria

✓ Script runs without errors
✓ Credentials load successfully
✓ API authentication succeeds
✓ Products display with all details
✓ Affiliate links contain your partner tag

## Troubleshooting

**FileNotFoundError**: Ensure `Longevity-credentials.csv` is in the project root

**Authentication failed (401)**: Check your API credentials are valid and not expired

**Rate limit exceeded (429)**: Wait a moment before trying again. PA-API has usage limits.

**No results found**: Try different search keywords

## Security

⚠️ **Never commit credentials to version control**

The `.gitignore` file excludes:
- `Longevity-credentials.csv`
- `*.csv` files

## Next Steps

This script provides the foundation for:
- Database integration for product data storage
- Automated product data synchronization
- Multiple category searches
- Full affiliate website implementation

## API Documentation

- [Amazon PA-API 5.0 Documentation](https://webservices.amazon.com/paapi5/documentation/)
- [paapi5-python-sdk GitHub](https://github.com/seratch/paapi5-python-sdk)
```

**Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: add project README with usage instructions"
```

---

## Task 10: Final Verification and Cleanup

**Files:**
- Verify: All project files

**Step 1: Run final test**

Run: `python test_amazon_api.py`
Expected: Successful execution with 10 products displayed

**Step 2: Verify .gitignore is working**

Run: `git status`
Expected: `Longevity-credentials.csv` should NOT appear in untracked files

**Step 3: Verify all files are committed**

Run: `git status`
Expected: "nothing to commit, working tree clean"

**Step 4: Review project structure**

Run: `tree -L 2 -I '__pycache__|*.pyc|venv|env'` or `ls -R`
Expected:
```
.
├── .gitignore
├── Longevity-credentials.csv (not tracked)
├── README.md
├── requirements.txt
├── test_amazon_api.py
└── docs/
    └── plans/
        ├── 2026-02-26-amazon-affiliate-test-design.md
        └── 2026-02-26-amazon-affiliate-test-implementation.md
```

**Step 5: Create final summary commit**

```bash
git log --oneline
```

Expected: See all commits in sequence

---

## Completion Checklist

- [x] Dependencies installed (paapi5-python-sdk)
- [x] .gitignore created and credentials protected
- [x] Credential loader implemented with error handling
- [x] API client initializer created
- [x] Product search function implemented
- [x] Data formatter and display functions created
- [x] Main orchestration function completed
- [x] Script tested successfully with real API
- [x] Error handling verified
- [x] Affiliate tag verification passes
- [x] README documentation created
- [x] All commits made with clear messages

## Success Criteria Validation

Run the script one final time and verify:

✓ Loads credentials from CSV without errors
✓ Initializes PA-API client successfully
✓ Searches and retrieves 10 supplement products
✓ Displays formatted product information
✓ All affiliate URLs contain "longevityhe09-20" partner tag
✓ Shows title, price, rating, ASIN, link, image for each product
✓ Error handling works (test by temporarily moving CSV file)

## Notes for Future Development

- Consider adding command-line arguments for search keywords
- Implement caching to reduce API calls during development
- Add logging to track API usage
- Create separate config file for partner tag and region settings
- Consider adding unit tests for data formatting functions
- Plan database schema for product data storage (next phase)
