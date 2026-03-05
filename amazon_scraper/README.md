# amazon_scraper

Amazon supplement product scraper with SQLite storage, data refresh tracking, and a read-only REST API.

> This is a temporary data source while waiting for Amazon Creator API access. See the [project README](../README.md) for full documentation.

## Modules

| Module | Purpose |
|--------|---------|
| `config.py` | All configuration: categories, scraping settings, DB settings, CSS selectors |
| `run.py` | CLI entry point — `python -m amazon_scraper.run [OPTIONS]` |
| `spider.py` | Orchestrator: iterates categories → pages → concurrent product scraping |
| `fetchers.py` | HTTP fetching with retry, exponential backoff, proxy support, anti-detection |
| `extractors.py` | HTML parsing: `ProductScraper` and `ReviewExtractor` using CSS selectors |
| `exporters.py` | Validates data, saves to SQLite (primary) and JSON (secondary) |
| `database.py` | SQLite schema (3 tables), `Database` class, JSON import CLI |
| `api.py` | FastAPI read-only REST API (4 endpoints) — `python -m amazon_scraper.api` |
| `validators.py` | Product data validation (ASIN format, required fields, affiliate tag) |
| `state.py` | Checkpoint/resume state management |
| `utils.py` | Helpers: affiliate links, file I/O, currency/delivery location automation |

## Key Flows

### Scraping

```
run.py → SupplementSpider.start()
  → for each category:
      → extract ASINs from listing pages (paginated)
      → filter already-scraped ASINs
      → _scrape_products_concurrent(asins, category)
          → ThreadPoolExecutor with per-worker fetcher instances
          → ProductScraper + ReviewExtractor parse HTML
          → DataExporter.save_product() validates + writes to SQLite & JSON
```

### Refresh

```
run.py --refresh-stale
  → Database.get_stale_asins(threshold_days)
  → SupplementSpider.refresh_asins(pairs)
      → removes ASINs from scraped set
      → groups by category
      → _scrape_products_concurrent() for each group
      → upsert_product() updates updated_at timestamp
```

### API

```
api.py → FastAPI app
  GET /products       → Database.get_products() with filtering/pagination
  GET /products/{asin} → Database.get_product() with reviews
  GET /categories     → Database.get_categories()
  GET /stats          → Database.get_stats()
```

## Database Schema

```sql
products (asin PK, category, title, price, brand, rating, review_count,
          affiliate_url, description*, images*, best_sellers_rank*,
          product_details*, product_overview*, videos*, validation*,
          scraped_at, updated_at)
          -- * = JSON text columns

reviews  (id PK, asin FK, rating, text, date, verified, reviewer)
          -- UNIQUE(asin, reviewer, date)

scrape_history (id PK, asin, scraped_at, success, error)
```

## Quick Reference

```bash
# Scrape
python -m amazon_scraper.run --category vitamin-d --workers 2

# Refresh stale products
python -m amazon_scraper.run --refresh-stale --stale-days 3

# Import JSON → SQLite
python -m amazon_scraper.database --import

# Start API
python -m amazon_scraper.api  # → http://localhost:8000/docs
```

## Configuration

Edit `config.py` or use environment variables:

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `DB_PATH` | `data/products.db` | SQLite database path |
| `STALE_THRESHOLD_DAYS` | `7` | Days before product is stale |
| `PROXY_URL` | — | Proxy URL for fetchers |

## Thread Safety

- `Database` uses `threading.local()` for per-thread SQLite connections
- `SupplementSpider` uses locks for stats, exporter, and state manager access
- Each worker thread creates its own fetcher instance
- SQLite WAL mode allows concurrent reads during writes
