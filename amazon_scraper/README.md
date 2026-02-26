# Amazon Supplement Scraper

Scrapes Amazon supplement product data until Creator API access is achieved (10 sales/30 days requirement).

## Features

- ✅ Category-first scraping for maximum coverage
- ✅ Resume capability via checkpoints
- ✅ Anti-detection with Scrapling's StealthyFetcher
- ✅ Comprehensive data validation
- ✅ Automatic affiliate link generation
- ✅ JSON output organized by category

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from scrapling import Spider; print('Ready!')"
```

## Usage

```bash
# Start fresh scraping
python amazon_scraper/run.py

# Resume from checkpoint
python amazon_scraper/run.py --resume

# Scrape specific category
python amazon_scraper/run.py --category vitamin-d

# Dry run (test without saving)
python amazon_scraper/run.py --dry-run

# Using convenience script
./run_scraper.sh --resume
```

## Configuration

Edit `amazon_scraper/config.py`:

- `PARTNER_TAG`: Your Amazon affiliate tag
- `CATEGORIES`: URLs to scrape
- `SCRAPING_SETTINGS`: Delays and limits
- `SELECTORS`: CSS selectors for extraction

## Output Structure

```
scraped_data/
├── vitamin-d/
│   ├── B00123ABC.json
│   └── ...
├── omega-3/
└── ...
```

## Resume & Checkpoints

The scraper automatically saves progress:
- After each category
- Every 50 products
- On Ctrl+C (graceful shutdown)

Resume with: `python amazon_scraper/run.py --resume`

## Troubleshooting

**Cloudflare blocking:** StealthyFetcher should bypass automatically. If blocked repeatedly, try increasing delays in config.

**Missing data:** Check `SELECTORS` in config.py - Amazon may have changed their HTML structure.

**Memory issues:** Reduce `checkpoint_interval` to save more frequently.

## Data Validation

Each product is validated for:
- Valid ASIN format
- Required fields (title, price, affiliate URL)
- Affiliate tag presence
- No duplicates

See `validation` field in JSON output for details.

## Next Steps

Once API access is achieved:
1. Migrate to Creator API (test_amazon_api.py)
2. Compare scraped data vs API data
3. Set up automated sync
