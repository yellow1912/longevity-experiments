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
