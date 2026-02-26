# Amazon Supplement Scraper Design Document

**Date:** 2026-02-26
**Project:** Longevity Health Affiliate Website
**Purpose:** Scrape Amazon supplement product data until Creator API becomes accessible (10 sales/30 days requirement)

---

## Executive Summary

Build a category-first web scraper using Scrapling to systematically extract supplement product data from Amazon, including titles, prices, descriptions, images, and reviews. Save data as JSON files with resume capability. Generate affiliate links programmatically using partner tag `longevityhe09-20`.

**Key Requirements:**
- ✅ Maximum product coverage (as many as possible)
- ✅ Resume capability for large-scale scraping
- ✅ JSON file storage for portability
- ✅ Comprehensive validation
- ✅ Ongoing data collection until API access achieved

---

## 1. Architecture & System Overview

### Core System

A Python-based web scraper using **Scrapling** framework with **StealthyFetcher** to systematically crawl Amazon supplement categories, extract product details including reviews, and save everything to JSON files with checkpoint-based resume capability.

### High-Level Flow

```
1. Initialize Spider with StealthyFetcher
   ↓
2. Load Category URLs from config
   → Vitamins & Dietary Supplements categories
   ↓
3. For Each Category:
   a. Navigate to category page
   b. Extract all product ASINs on current page
   c. Click "Next" → Repeat until no more pages
   ↓
4. For Each ASIN:
   a. Check if already scraped (skip duplicates)
   b. Navigate to product detail page
   c. Wait for page load (network_idle=True)
   d. Extract product data
   e. Navigate to reviews section
   f. Extract latest 5-10 reviews
   g. Generate affiliate link programmatically
   h. Save to JSON with validation
   i. Update state checkpoint
   ↓
5. Save Final State & Statistics Report
```

### Technology Stack

| Component | Technology | Reason |
|-----------|-----------|---------|
| **Web Scraping** | Scrapling with StealthyFetcher | Anti-detection, fingerprint spoofing, Cloudflare bypass |
| **Browser Engine** | Playwright (via Scrapling) | JavaScript rendering, dynamic content |
| **Language** | Python 3.9+ | Existing project environment |
| **Data Format** | JSON | Portability, easy to zip/transfer |
| **State Management** | Scrapling's checkpoint system | Built-in pause/resume |
| **Session Management** | Scrapling's unified sessions | Cookies, state persistence |

### Why Scrapling?

- ✅ **StealthyFetcher** - Anti-detection with fingerprint spoofing
- ✅ **Spider Framework** - Built-in pause/resume checkpoints
- ✅ **Cloudflare bypass** - Handles Amazon's protection automatically
- ✅ **Session management** - Cookies and state handled automatically
- ✅ **Adaptive tracking** - Elements relocate automatically when site changes
- ✅ **JSON export** - Native `to_json()` methods
- ✅ **Proxy rotation** - Built-in ProxyRotator support

### File Structure

```
longevity-experiments/
├── amazon_scraper/
│   ├── __init__.py
│   ├── spider.py          # SupplementSpider main class
│   ├── extractors.py      # ProductScraper, ReviewExtractor
│   ├── exporters.py       # DataExporter with validation
│   ├── config.py          # Categories, settings, partner tag
│   ├── validators.py      # Data validation rules
│   ├── utils.py           # Helper functions
│   └── run.py             # CLI entry point
├── scraped_data/
│   ├── vitamin-d/
│   │   ├── B00123ABC.json
│   │   ├── B00456DEF.json
│   │   └── ...
│   ├── omega-3/
│   ├── nad-boosters/
│   └── ...
├── scraper_state.json     # Resume checkpoint
├── scraper_stats.json     # Progress statistics
├── requirements.txt       # Updated dependencies
└── README.md              # Updated usage docs
```

---

## 2. Components & Module Structure

### 2.1 SupplementSpider (Main Spider Class)

**Purpose:** Orchestrates the entire scraping workflow

**Responsibilities:**
- Initialize Scrapling Spider with StealthyFetcher
- Load categories from config
- Manage scraping queue (categories → pages → products)
- Coordinate CategoryCrawler and ProductScraper
- Handle pause/resume via checkpoints
- Track overall progress and statistics

**Key Methods:**
```python
class SupplementSpider(Spider):
    def start(self):
        """Initialize spider with categories"""

    def crawl_category(self, category_url):
        """Crawl all pages in a category"""

    def save_checkpoint(self):
        """Save progress state"""

    def resume_from_checkpoint(self):
        """Resume from last checkpoint"""
```

### 2.2 CategoryCrawler

**Purpose:** Navigate category listing pages and extract product ASINs

**Responsibilities:**
- Navigate to category pages
- Extract all product ASINs from current page
- Handle pagination (click "Next", detect last page)
- Track progress per category (page numbers)
- Pass ASINs to ProductScraper

**Extraction Targets:**
- Product ASINs: `[data-asin]` attributes
- Next page button: `.s-pagination-next`
- Total results: `.s-result-count`

### 2.3 ProductScraper

**Purpose:** Extract detailed product information from product pages

**Responsibilities:**
- Navigate to product detail page
- Wait for page load (network_idle=True)
- Extract all product fields
- Handle missing/unavailable data gracefully
- Return structured product data

**Extraction Targets:**
```python
{
    # Required fields
    "asin": Extract from URL path
    "title": "#productTitle" or "h1.product-title"
    "price": "#priceblock_ourprice" or ".a-price-whole"

    # Optional fields
    "brand": "#bylineInfo" or ".a-size-medium"
    "description": "#feature-bullets li" elements
    "images": "#landingImage" src or "#altImages" thumbs
    "rating": ".a-icon-star" text
    "review_count": "#acrCustomerReviewText"
}
```

**Fallback Selectors:**
Multiple CSS selectors per field to handle Amazon's variations

### 2.4 ReviewExtractor

**Purpose:** Extract latest product reviews

**Responsibilities:**
- Navigate to reviews section or separate reviews page
- Extract top 5-10 reviews
- Parse review data (rating, text, date, verified)
- Handle "See more reviews" if needed

**Extraction Targets:**
```python
{
    "rating": ".a-icon-star" text (e.g., "5.0 out of 5 stars")
    "text": ".review-text" content
    "date": ".review-date" (e.g., "Reviewed on January 15, 2026")
    "verified": Check for "Verified Purchase" badge
    "reviewer": ".a-profile-name"
}
```

### 2.5 DataExporter

**Purpose:** Save product data to JSON files with validation

**Responsibilities:**
- Validate product data before saving
- Generate affiliate link from ASIN
- Save to JSON file (one file per product)
- Organize by category folders
- Maintain ASIN index to avoid duplicates
- Track validation errors/warnings

**Affiliate Link Generation:**
```python
def generate_affiliate_link(asin: str, partner_tag: str) -> str:
    """
    Programmatically construct Amazon affiliate link.
    Format: https://www.amazon.com/dp/{ASIN}?tag={partner_tag}
    """
    return f"https://www.amazon.com/dp/{asin}?tag={partner_tag}"
```

**JSON Output Structure:**
```json
{
  "asin": "B00123ABC",
  "title": "Vitamin D3 5000 IU High Potency - 360 Softgels",
  "price": "$19.99",
  "brand": "NatureWise",
  "description": [
    "High Potency Vitamin D3 5000 IU per softgel",
    "Supports bone health and immune function",
    "Certified by third-party testing"
  ],
  "images": [
    "https://m.media-amazon.com/images/I/71abc123.jpg",
    "https://m.media-amazon.com/images/I/71def456.jpg"
  ],
  "rating": "4.7 out of 5 stars",
  "review_count": 15234,
  "affiliate_url": "https://www.amazon.com/dp/B00123ABC?tag=longevityhe09-20",
  "reviews": [
    {
      "rating": "5.0 out of 5 stars",
      "text": "Great product! I've been taking this daily...",
      "date": "Reviewed on January 15, 2026",
      "verified": true,
      "reviewer": "John D."
    }
  ],
  "validation": {
    "passed": true,
    "errors": [],
    "warnings": []
  },
  "scraped_at": "2026-02-26T10:30:00Z",
  "category": "vitamin-d"
}
```

### 2.6 StateManager

**Purpose:** Track scraping progress and enable resume

**Responsibilities:**
- Save progress after each category/page
- Track: current category, page number, last ASIN processed
- Enable resume from exact stopping point
- Use Scrapling's built-in checkpoint system
- Save statistics for progress monitoring

**State File Format (scraper_state.json):**
```json
{
  "current_category": "vitamin-d",
  "current_page": 5,
  "last_asin": "B00123ABC",
  "completed_categories": ["omega-3"],
  "total_products_scraped": 247,
  "started_at": "2026-02-26T08:00:00Z",
  "last_checkpoint": "2026-02-26T10:30:00Z",
  "scraped_asins": ["B00123ABC", "B00456DEF", ...]
}
```

---

## 3. Data Flow & Scraping Process

### Main Workflow

```
┌─────────────────────────────────────────┐
│ 1. Initialize Spider                    │
│    - Load config (categories, settings) │
│    - Setup StealthyFetcher              │
│    - Check for existing checkpoint      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 2. Load Category URLs                   │
│    - vitamin-d                          │
│    - omega-3                            │
│    - nad-boosters                       │
│    - resveratrol                        │
│    - multivitamins                      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 3. For Each Category:                   │
│    a. Navigate to category page         │
│    b. Extract product ASINs (48-60/pg)  │
│    c. Click "Next" button               │
│    d. Repeat until no more pages        │
│    e. Save category checkpoint          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 4. For Each ASIN:                       │
│    a. Check duplicate (skip if exists)  │
│    b. Navigate to product page          │
│    c. Wait for load (network_idle)      │
│    d. Extract product data              │
│    e. Navigate to reviews               │
│    f. Extract latest 5-10 reviews       │
│    g. Validate data                     │
│    h. Generate affiliate link           │
│    i. Save to JSON                      │
│    j. Update checkpoint (every 50)      │
│    k. Delay 3-5 seconds (rate limit)    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 5. Save Final State & Stats             │
│    - Total products scraped             │
│    - Success rate                       │
│    - Validation results                 │
│    - Time elapsed                       │
└─────────────────────────────────────────┘
```

### Data Extraction Details

**Category Page → ASINs:**
- Selector: `[data-asin]` attributes on product cards
- Pagination: `.s-pagination-next` button
- Results per page: ~48-60 products
- Handle: Empty results, last page detection

**Product Page → Fields:**
| Field | Primary Selector | Fallback Selector | Validation |
|-------|-----------------|-------------------|------------|
| Title | `#productTitle` | `h1.product-title` | Min 10 chars |
| Price | `#priceblock_ourprice` | `.a-price-whole` | Contains $ or "N/A" |
| Brand | `#bylineInfo` | `.a-size-medium` | Optional |
| Description | `#feature-bullets li` | `.a-unordered-list li` | Min 1 bullet |
| Images | `#landingImage@src` | `#altImages img@src` | Valid URLs |
| Rating | `.a-icon-star::text` | `#acrPopover::attr(title)` | Float 0-5 |

**Reviews Section → Reviews:**
- Navigate: Scroll to reviews or visit `/product-reviews/`
- Extract: Top 5-10 most recent reviews
- Fields: rating, text, date, verified badge, reviewer name

---

## 4. Error Handling & Validation

### 4.1 Network Error Handling

| Error Type | Detection | Recovery Strategy |
|------------|-----------|-------------------|
| **Connection timeout** | Request > 30s | Retry with exponential backoff (3 attempts: 5s, 10s, 20s) |
| **Cloudflare block** | Captcha page detected | StealthyFetcher should bypass, log if fails |
| **404 Not Found** | HTTP 404 response | Skip product, log ASIN as unavailable |
| **Rate limiting** | HTTP 429 or slow response | Pause 30 seconds, then resume |
| **Server error (5xx)** | HTTP 500+ | Retry once after 10s, skip if fails again |

### 4.2 Scraping Error Handling

| Error Type | Detection | Recovery Strategy |
|------------|-----------|-------------------|
| **Element not found** | Selector returns empty | Try fallback selector, mark as "N/A" if all fail |
| **Empty data** | Field extraction yields empty string | Mark field as "N/A", continue with other fields |
| **JavaScript timeout** | Page load > 60s | Increase wait time to 90s, retry once |
| **Page structure changed** | Multiple selectors fail | Use Scrapling's adaptive tracking, log for manual review |
| **Invalid data format** | Price without $, malformed ASIN | Log validation error, attempt to fix or skip |

### 4.3 Data Validation Rules

**Required Fields (Must Be Present):**
```python
REQUIRED_VALIDATIONS = {
    "asin": {
        "pattern": r"^B[0-9A-Z]{9}$",
        "error": "Invalid ASIN format"
    },
    "title": {
        "min_length": 10,
        "max_length": 500,
        "not_in": ["Product", "Item", "N/A"],
        "error": "Title too short or generic"
    },
    "price": {
        "pattern": r"^\$[\d,]+\.\d{2}$|^Currently unavailable$|^N/A$",
        "error": "Invalid price format"
    },
    "affiliate_url": {
        "contains": "tag=longevityhe09-20",
        "pattern": r"^https://www\.amazon\.com/dp/",
        "error": "Invalid affiliate link"
    }
}
```

**Optional Fields (Warn If Missing):**
```python
OPTIONAL_WARNINGS = {
    "description": "At least 1 feature bullet recommended",
    "images": "At least 1 image URL recommended",
    "brand": "Brand field empty",
    "reviews": "No reviews found",
    "rating": "No rating available"
}
```

**Additional Validation Checks:**
```python
def validate_product(product: dict) -> ValidationResult:
    """
    Comprehensive product validation
    """
    errors = []
    warnings = []

    # Check required fields
    for field, rule in REQUIRED_VALIDATIONS.items():
        if not validate_field(product[field], rule):
            errors.append(f"{field}: {rule['error']}")

    # Check optional fields
    for field, message in OPTIONAL_WARNINGS.items():
        if not product.get(field) or len(product[field]) == 0:
            warnings.append(message)

    # Check for duplicates
    if product["asin"] in scraped_asins_set:
        errors.append("Duplicate ASIN")

    # Verify image URLs (sample check)
    if product.get("images"):
        if not validate_image_url(product["images"][0]):
            warnings.append("Primary image URL may be invalid")

    # Check review dates (should be recent)
    if product.get("reviews"):
        latest_review = product["reviews"][0]
        if parse_review_date(latest_review["date"]) < (now() - years(2)):
            warnings.append("No recent reviews (within 2 years)")

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
```

### 4.4 State Recovery & Checkpoints

**Checkpoint Strategy:**
- **After each category:** Save state with completed category name
- **Every 50 products:** Save state with current ASIN
- **Before shutdown:** Graceful shutdown saves current position
- **On crash:** Resume from last checkpoint

**State File Updates:**
```python
def save_checkpoint(state: ScraperState):
    """
    Save checkpoint atomically
    """
    # Write to temp file first
    temp_file = "scraper_state.json.tmp"
    with open(temp_file, 'w') as f:
        json.dump(state.to_dict(), f, indent=2)

    # Atomic rename
    os.replace(temp_file, "scraper_state.json")
```

**Resume Logic:**
```python
def resume_from_checkpoint() -> ScraperState:
    """
    Resume scraping from last checkpoint
    """
    if not os.path.exists("scraper_state.json"):
        return ScraperState()  # Start fresh

    with open("scraper_state.json") as f:
        state_dict = json.load(f)

    state = ScraperState.from_dict(state_dict)

    # Log resume point
    logger.info(f"Resuming from category: {state.current_category}")
    logger.info(f"Last ASIN processed: {state.last_asin}")
    logger.info(f"Products scraped so far: {state.total_products_scraped}")

    return state
```

### 4.5 Logging & Monitoring

**Log Levels:**
```python
INFO:  Progress updates (category started, products scraped)
WARN:  Validation warnings, missing optional fields
ERROR: Scraping errors, network errors, validation failures
DEBUG: Detailed extraction info, selector results
```

**Logged Metrics:**
```python
METRICS = {
    "products_scraped": Counter,
    "products_skipped": Counter with ASIN list,
    "validation_passed": Counter,
    "validation_failed": Counter with details,
    "network_errors": Counter with error types,
    "time_per_category": Timer,
    "time_per_product": Timer,
    "estimated_completion": Calculated from current rate
}
```

**Statistics Report (scraper_stats.json):**
```json
{
  "total_products_scraped": 847,
  "successful": 831,
  "success_rate": 0.981,
  "validation_errors": 0,
  "validation_warnings": 16,
  "categories_completed": ["omega-3", "vitamin-d", "nad-boosters"],
  "categories_remaining": ["resveratrol", "multivitamins"],
  "time_elapsed_seconds": 2730,
  "avg_time_per_product_seconds": 3.2,
  "estimated_time_remaining_seconds": 2700,
  "last_updated": "2026-02-26T11:45:00Z"
}
```

---

## 5. Testing & Usage

### 5.1 Installation

```bash
# Navigate to project directory
cd longevity-experiments

# Install Scrapling
pip install scrapling

# Verify installation
python -c "from scrapling import Spider; print('Scrapling installed successfully')"
```

### 5.2 Configuration Setup

**Edit `amazon_scraper/config.py`:**
```python
# Your Amazon affiliate partner tag
PARTNER_TAG = "longevityhe09-20"

# Supplement categories to scrape
CATEGORIES = {
    "vitamin-d": "https://www.amazon.com/s?k=vitamin+d+supplement&rh=n:3760901",
    "omega-3": "https://www.amazon.com/s?k=omega+3+supplement&rh=n:3760901",
    "nad-boosters": "https://www.amazon.com/s?k=nad+supplement&rh=n:3760901",
    "resveratrol": "https://www.amazon.com/s?k=resveratrol+supplement&rh=n:3760901",
    "multivitamins": "https://www.amazon.com/s?k=multivitamin&rh=n:3760901",
}

# Scraping settings
SCRAPING_SETTINGS = {
    "delay_between_products": 3,  # seconds (respectful scraping)
    "max_reviews_per_product": 10,
    "retry_attempts": 3,
    "checkpoint_interval": 50,  # products
    "request_timeout": 30,  # seconds
    "page_load_timeout": 60,  # seconds
}

# Output settings
OUTPUT_SETTINGS = {
    "data_dir": "scraped_data",
    "state_file": "scraper_state.json",
    "stats_file": "scraper_stats.json",
    "json_indent": 2,
}
```

### 5.3 Running the Scraper

**Start Fresh:**
```bash
python amazon_scraper/run.py
```

**Resume from Checkpoint:**
```bash
python amazon_scraper/run.py --resume
```

**Scrape Specific Category:**
```bash
python amazon_scraper/run.py --category vitamin-d
```

**Dry Run (Test Without Saving):**
```bash
python amazon_scraper/run.py --dry-run
```

**Verbose Logging:**
```bash
python amazon_scraper/run.py --verbose
```

### 5.4 CLI Options

```bash
Usage: run.py [OPTIONS]

Options:
  --resume              Resume from last checkpoint
  --category TEXT       Scrape specific category only
  --dry-run            Test mode (don't save files)
  --verbose            Enable verbose logging
  --delay INTEGER      Override delay between products (seconds)
  --max-products INT   Limit total products to scrape
  --help               Show this message and exit
```

### 5.5 Verification & Validation

**Check Scraped Data:**
```bash
# List scraped products by category
ls scraped_data/vitamin-d/

# Count total products
find scraped_data -name "*.json" | wc -l

# View sample product
cat scraped_data/vitamin-d/B00123ABC.json | jq
```

**Run Validation Tool:**
```bash
# Validate all scraped data
python amazon_scraper/validate.py scraped_data/

# Validate specific category
python amazon_scraper/validate.py scraped_data/vitamin-d/

# Generate detailed report
python amazon_scraper/validate.py scraped_data/ --report
```

**Generate Statistics Report:**
```bash
# View current progress
python amazon_scraper/stats.py

# Export stats to file
python amazon_scraper/stats.py --export stats_report.json
```

### 5.6 Success Criteria

**Scraping Success:**
- ✅ Scrapes at least 100 products per category
- ✅ All required fields present in 95%+ of products
- ✅ Validation passes for 95%+ of products
- ✅ Can resume after interruption without data loss
- ✅ No unhandled exceptions or crashes
- ✅ Completes one category in < 30 minutes (approximate)

**Data Quality:**
- ✅ Affiliate URLs contain correct partner tag
- ✅ ASINs match regex pattern `^B[0-9A-Z]{9}$`
- ✅ Prices are formatted correctly or marked "N/A"
- ✅ At least 1 image URL per product
- ✅ Reviews are recent (within 2 years)

**Performance:**
- ✅ Average 3-5 seconds per product
- ✅ Checkpoint saves every 50 products (< 1 second)
- ✅ Memory usage stays < 500MB
- ✅ No rate limiting errors from Amazon

### 5.7 Expected Output Structure

```
scraped_data/
├── vitamin-d/
│   ├── B00123ABC.json   (Vitamin D3 5000 IU)
│   ├── B00456DEF.json   (Vitamin D3 10000 IU)
│   ├── B00789GHI.json   (Vitamin D2 supplement)
│   └── ... (hundreds more)
├── omega-3/
│   ├── B01ABC123.json   (Fish Oil 1000mg)
│   ├── B01DEF456.json   (Krill Oil)
│   └── ... (hundreds more)
├── nad-boosters/
│   ├── B02ABC789.json   (NAD+ Precursor)
│   └── ... (dozens more)
└── ... (more categories)
```

### 5.8 Progress Monitoring

**Real-time Progress Display:**
```
========================================
Amazon Supplement Scraper
========================================

Category: vitamin-d (1/5)
Page: 8/42
Products scraped: 387/~2500
Success rate: 98.2%
Elapsed time: 23 minutes
Estimated remaining: 2 hours 15 minutes

Current: B00789XYZ - Vitamin D3 5000 IU...
Status: ✓ Extracted | ✓ Validated | ✓ Saved

[Progress Bar: ████████░░░░░░░░░░░░ 15.5%]
```

**Statistics Summary:**
```bash
$ python amazon_scraper/stats.py

Amazon Scraper Statistics Report
================================
Total products scraped: 847
Successful: 831 (98.1%)
Validation errors: 0 (0.0%)
Validation warnings: 16 (1.9%)

Categories Completed: 3/5
✓ omega-3 (234 products)
✓ vitamin-d (421 products)
✓ nad-boosters (176 products)
⧗ resveratrol (in progress)
☐ multivitamins (pending)

Time Statistics:
- Total elapsed: 45 minutes
- Avg per product: 3.2 seconds
- Estimated remaining: 42 minutes

Top Warnings:
- No reviews found: 12 products
- Brand field empty: 4 products
```

---

## 6. Future Enhancements

**Phase 2 (After Initial Scraping):**
1. **Image Download Module** - Download and store images locally
2. **Price Change Tracking** - Re-scrape to detect price updates
3. **Inventory Monitoring** - Track "out of stock" status
4. **Review Updates** - Fetch new reviews periodically

**Phase 3 (After API Access Achieved):**
1. **Hybrid Mode** - Use API when available, scraping as fallback
2. **Data Synchronization** - Merge scraped data with API data
3. **Database Migration** - Move from JSON to PostgreSQL/MySQL

**Phase 4 (Website Integration):**
1. **Product Import** - Load JSON data into website database
2. **Automatic Updates** - Schedule regular re-scraping
3. **Search Indexing** - Full-text search on product data

---

## 7. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Amazon blocks scraper** | High | Medium | Use StealthyFetcher, rotate IPs, respectful delays |
| **Page structure changes** | Medium | Medium | Scrapling's adaptive tracking, multiple selectors |
| **Large-scale scraping takes too long** | Low | High | Checkpoint system, can run overnight/multi-day |
| **Invalid affiliate links** | High | Low | Validation checks affiliate tag in every URL |
| **Missing reviews data** | Low | Medium | Mark as warning, not error; acceptable to have no reviews |
| **Memory overflow** | Medium | Low | Process one product at a time, save incrementally |

---

## 8. Legal & Ethical Considerations

**Amazon Terms of Service:**
- ✅ Scraping for affiliate purposes is generally allowed
- ✅ Respectful rate limiting (3-5 seconds between requests)
- ✅ Not overloading servers or causing disruption
- ✅ Using data for legitimate affiliate website

**Best Practices:**
- ⚠️ Do not scrape more aggressively than necessary
- ⚠️ Respect robots.txt (though Amazon blocks aggressive bots, not affiliates)
- ⚠️ Include User-Agent string identifying as affiliate tool
- ⚠️ Do not use scraped data for competitive analysis or resale

**Note:** This scraper is designed as a temporary solution until Creator API becomes accessible (10 sales/30 days requirement met). Once API access is achieved, migrate to official API for better reliability and compliance.

---

## 9. Summary

### What We're Building

A robust, category-first Amazon supplement scraper using Scrapling's advanced features to extract comprehensive product data for a longevity health affiliate website. The scraper prioritizes maximum coverage, resume capability, data quality validation, and respectful scraping practices.

### Key Features

1. **Comprehensive Coverage** - Category-first approach ensures minimal missed products
2. **Resume Capability** - Checkpoint system allows multi-day scraping sessions
3. **Anti-Detection** - StealthyFetcher with fingerprint spoofing and Cloudflare bypass
4. **Data Validation** - Comprehensive validation rules ensure quality data
5. **Affiliate Links** - Programmatic generation with partner tag verification
6. **Progress Monitoring** - Real-time stats and estimated completion time

### Deliverables

- ✅ Fully functional Amazon supplement scraper
- ✅ JSON data files organized by category
- ✅ Validation and statistics tools
- ✅ Resume capability via checkpoints
- ✅ Documentation and usage guide

---

**Document Status:** ✅ Approved
**Next Step:** Create implementation plan via writing-plans skill
