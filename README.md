# Amazon Affiliate API Test

Test script for verifying Amazon Creator API credentials and retrieving supplement product data for a longevity/health affiliate website.

## Prerequisites

- Python 3.8 or higher
- Amazon Associates account with Creator API access
- Valid API credentials in `Longevity-credentials.csv`
- **Note:** Your Associates account must meet Amazon's eligibility requirements (verified website/app, minimum traffic/sales)

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
2. Initialize Creator API client
3. Search for vitamin D supplements
4. Display product results with details

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

**Account not eligible (403)**: Your Associates account needs to meet eligibility requirements:
- Complete your account profile at https://affiliate-program.amazon.com/
- Add and verify your website/app
- Meet minimum traffic or sales requirements
- Ensure your account status is "Approved"

**Rate limit exceeded (429)**: Wait a moment before trying again. Creator API has usage limits.

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

- [Amazon Creator API Documentation](https://affiliate-program.amazon.com/creatorsapi)
- [python-amazon-paapi GitHub](https://github.com/sergioteula/python-amazon-paapi)
- [python-amazon-paapi Documentation](https://python-amazon-paapi.readthedocs.io/)

## Amazon Product Scraper (Temporary Solution)

While waiting to meet the 10 sales/30 days requirement for Creator API access, use the Amazon scraper to collect product data:

```bash
# Run the scraper
python amazon_scraper/run.py

# Resume if interrupted
python amazon_scraper/run.py --resume
```

See [amazon_scraper/README.md](amazon_scraper/README.md) for full documentation.

**Note:** This is a temporary solution. Once API access is achieved, migrate to the official Creator API for better reliability and compliance.
