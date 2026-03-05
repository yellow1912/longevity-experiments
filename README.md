# Longevity Health — Amazon Supplement Data Pipeline

Scrapes Amazon supplement product data, stores it in SQLite, and exposes it via a read-only REST API. Built as a temporary data source while waiting for Amazon Creator API access (10 sales/30 days requirement).

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────────┐
│  CLI / Run  │─────▶│    Spider    │─────▶│    Exporters     │
│  (run.py)   │      │ (spider.py)  │      │  (exporters.py)  │
└─────────────┘      └──────┬───────┘      └───────┬──────────┘
                            │                      │
                    ┌───────▼───────┐       ┌──────▼──────┐
                    │   Fetchers    │       │  Database   │──▶ SQLite (primary)
                    │ (fetchers.py) │       │(database.py)│
                    └───────────────┘       └──────┬──────┘──▶ JSON   (secondary)
                                                   │
                                            ┌──────▼──────┐
                                            │   REST API  │
                                            │  (api.py)   │
                                            └─────────────┘
```

**Data flow:** CLI → Spider orchestrates scraping → Fetchers retrieve pages with anti-detection → Extractors parse HTML → Exporters validate and save to SQLite (primary) + JSON (secondary) → API serves data from SQLite.

## Quick Start

### Docker (Recommended)

```bash
# Build
docker compose build

# Run a fresh scrape (writes to SQLite + JSON)
docker compose run --rm scraper

# Resume from checkpoint
docker compose run --rm scraper --resume

# Scrape specific category
docker compose run --rm scraper --category vitamin-d

# Start the API
docker compose up api
# → http://localhost:8000/docs (OpenAPI UI)
```

### Local

```bash
pip install -r requirements.txt

# Scrape
python -m amazon_scraper.run
python -m amazon_scraper.run --category omega-3 --workers 4

# Import existing JSON into SQLite (one-time migration)
python -m amazon_scraper.database --import

# Start API
python -m amazon_scraper.api
# → http://localhost:8000/docs
```

## CLI Reference

```
python -m amazon_scraper.run [OPTIONS]

Scraping:
  --resume              Resume from last checkpoint
  --category NAME       Scrape a single category (vitamin-d, omega-3, etc.)
  --workers N           Concurrent workers (default: 2)
  --dry-run             Extract but don't save
  --verbose             Enable verbose logging

Network:
  --proxy URL           Proxy URL (falls back to PROXY_URL env var)
  --fetcher BACKEND     Fetcher backend name (default: stealthy)

Refresh:
  --refresh-stale       Re-scrape products older than stale threshold
  --refresh-asin ASIN   Re-scrape a specific product
  --stale-days N        Stale threshold in days (default: 7)
```

### Refresh Examples

```bash
# Re-scrape all products not updated in the last 3 days
docker compose run --rm scraper --refresh-stale --stale-days 3

# Re-scrape a single product
docker compose run --rm scraper --refresh-asin B00FMZQKQ6
```

## REST API

Read-only API served by FastAPI on port 8000. Auto-generated docs at `/docs`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/products` | GET | List products with filtering, sorting, pagination |
| `/products/{asin}` | GET | Single product with reviews |
| `/categories` | GET | Category list with counts |
| `/stats` | GET | Database statistics |

### `/products` Query Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `category` | string | — | Filter by category |
| `min_rating` | float | — | Minimum rating filter |
| `brand` | string | — | Brand substring match |
| `search` | string | — | Search title and brand |
| `sort_by` | string | `updated_at` | Sort field: `updated_at`, `rating`, `review_count`, `title`, `price`, `scraped_at` |
| `order` | string | `desc` | `asc` or `desc` |
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Results per page (max 100) |

### Example API Calls

```bash
curl http://localhost:8000/stats
curl http://localhost:8000/categories
curl "http://localhost:8000/products?category=omega-3&min_rating=4.5&page_size=5"
curl http://localhost:8000/products/B00FMZQKQ6
```

## Configuration

All configuration lives in `amazon_scraper/config.py`:

| Setting | Description |
|---------|-------------|
| `PARTNER_TAG` | Amazon affiliate tag (`longevityhe09-20`) |
| `CATEGORIES` | Dict of category name → Amazon search URL |
| `SCRAPING_SETTINGS` | Delays, timeouts, workers, retry config |
| `OUTPUT_SETTINGS` | Data directory, state file paths, JSON indent |
| `DATABASE_SETTINGS` | SQLite path, stale threshold, JSON write toggle |
| `SELECTORS` | CSS selectors for HTML extraction |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `data/products.db` | SQLite database file path |
| `STALE_THRESHOLD_DAYS` | `7` | Days before a product is considered stale |
| `PROXY_URL` | — | Proxy URL for fetchers |

## Database

SQLite with WAL mode for concurrent read/write. Three tables:

**`products`** — One row per ASIN. Complex fields (description, images, validation, etc.) stored as JSON text.
- Key columns: `asin` (PK), `category`, `title`, `price`, `brand`, `rating`, `review_count`, `affiliate_url`, `scraped_at`, `updated_at`
- Indexes on `category`, `rating`, `updated_at`

**`reviews`** — One-to-many from products.
- Columns: `asin`, `rating`, `text`, `date`, `verified`, `reviewer`
- `UNIQUE(asin, reviewer, date)` prevents duplicates on re-scrape

**`scrape_history`** — Append-only audit log.
- Columns: `asin`, `scraped_at`, `success`, `error`

### Migration from JSON

```bash
# Import all existing scraped_data/*.json into SQLite
python -m amazon_scraper.database --import

# Verify
sqlite3 data/products.db "SELECT category, COUNT(*) FROM products GROUP BY category"
```

## Project Structure

```
amazon_scraper/
├── __init__.py
├── config.py          # All configuration constants
├── run.py             # CLI entry point (argparse)
├── spider.py          # Orchestrator: categories → pages → products
├── fetchers.py        # HTTP fetching with retry, proxy, anti-detection
├── extractors.py      # HTML → structured data (ProductScraper, ReviewExtractor)
├── exporters.py       # Validation + save to SQLite/JSON
├── database.py        # SQLite schema, Database class, JSON import
├── api.py             # FastAPI read-only REST API
├── validators.py      # Product data validation rules
├── state.py           # Checkpoint/resume state management
└── utils.py           # Helpers: affiliate links, file I/O, currency setup

data/
└── products.db        # SQLite database (created on first run)

scraped_data/          # JSON files organized by category
├── vitamin-d/
│   └── {ASIN}.json
├── omega-3/
└── ...

scraper_state/
└── scraper_state.json # Resume checkpoint data
```

## Module Reference

### `spider.py` — `SupplementSpider`

Orchestrates the full scraping workflow. Creates per-worker fetcher instances for thread isolation.

| Method | Description |
|--------|-------------|
| `start()` | Scrape all categories |
| `scrape_category(name, url)` | Scrape one category (paginated ASIN discovery → concurrent product scraping) |
| `refresh_asins(pairs)` | Re-scrape a list of `(asin, category)` pairs |
| `initialize_browser_settings()` | Set US delivery location for USD pricing |

### `fetchers.py` — `BaseFetcher` / `StealthyFetcherBackend`

Pluggable fetcher with exponential backoff retry. `create_fetcher(backend, proxy)` factory function.

### `extractors.py` — `ProductScraper` / `ReviewExtractor`

Parses Amazon product pages using CSS selectors from config. Extracts: title, price, brand, description, images, rating, review_count, best_sellers_rank, product_details, product_overview, ingredients, directions, safety_info, videos, reviews.

### `database.py` — `Database`

Thread-safe SQLite manager. Key methods:

| Method | Description |
|--------|-------------|
| `upsert_product(product)` | Insert/update product, preserves original `scraped_at` |
| `insert_reviews(asin, reviews)` | Insert reviews, ignores duplicates |
| `log_scrape(asin, success, error)` | Append to audit log |
| `get_product(asin)` | Full product with reviews |
| `get_products(...)` | Filtered/paginated product list |
| `get_stale_asins(days)` | Products not updated within threshold |
| `get_categories()` | Category list with counts |
| `get_stats()` | Aggregate statistics |

### `exporters.py` — `DataExporter`

Validates products, then saves to SQLite (primary) and JSON (secondary). Tracks scraped ASINs to skip duplicates.

### `validators.py`

Returns `ValidationResult(passed, errors, warnings)`. Checks: ASIN format, required fields, affiliate tag, duplicates.

### `state.py` — `StateManager`

Persists scraping progress to JSON. Tracks: current category/page, completed categories, scraped ASINs. Checkpoints every 50 products and on graceful shutdown.

## Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `scraper` | — | Runs the scraper CLI |
| `api` | 8000 | FastAPI read-only API (mounts `data/` as read-only) |

```bash
# Run scraper
docker compose run --rm scraper --category vitamin-d --workers 2

# Start API in background
docker compose up -d api

# View API logs
docker compose logs -f api
```

## Data Format

Each product (JSON and API response) contains:

```json
{
  "asin": "B000A0F2B2",
  "category": "vitamin-d",
  "title": "Bio-Tech Pharmacal D3-50 ...",
  "price": "$18.99",
  "brand": "Bio-Tech Pharmacal",
  "rating": "4.8",
  "review_count": 2934,
  "affiliate_url": "https://www.amazon.com/dp/B000A0F2B2?tag=longevityhe09-20",
  "description": ["Feature 1", "Feature 2"],
  "images": ["https://..."],
  "reviews": [
    {
      "rating": "5.0",
      "text": "Review text...",
      "date": "Reviewed in the United States on December 25, 2013",
      "verified": true,
      "reviewer": "Username"
    }
  ],
  "validation": { "passed": true, "errors": [], "warnings": [] },
  "scraped_at": "2026-02-26T03:52:41Z",
  "updated_at": "2026-03-05T12:39:20Z"
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cloudflare blocking | StealthyFetcher handles this. Increase `delay_between_products` if persistent |
| Prices in wrong currency | Run via Docker (US locale) or use `--proxy` with a US proxy |
| Missing product data | Check `SELECTORS` in config — Amazon may have changed HTML structure |
| `No module named 'fastapi'` | Run `pip install -r requirements.txt` to install API dependencies |
| Database locked | SQLite WAL mode handles concurrent reads. Only one writer at a time |
| Stale data | Use `--refresh-stale` or `--refresh-asin` to re-scrape |

## Security

- **Never commit credentials** — `.gitignore` excludes `*.csv`, `.env`, and `data/`
- `Longevity-credentials.csv` is mounted read-only in Docker
- API is read-only (no write endpoints)

## Roadmap

- Migrate to Amazon Creator API once 10 sales/30 days requirement is met
- Compare scraped data vs API data for validation
- Automated scheduled scraping via cron/scheduler
