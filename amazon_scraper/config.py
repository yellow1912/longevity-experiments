"""
Amazon Scraper Configuration
Defines categories, settings, and scraping parameters
"""

# Your Amazon affiliate partner tag
PARTNER_TAG = "longevityhe09-20"

# Supplement categories to scrape
# Format: {"category_name": "amazon_search_url"}
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
    "checkpoint_interval": 50,  # save state every N products
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

# CSS Selectors for Amazon product pages
SELECTORS = {
    # Product listing page
    "product_asin": "[data-asin]",
    "next_page": ".s-pagination-next",

    # Product detail page
    "title": ["#productTitle", "h1.product-title"],
    "price": ["#priceblock_ourprice", ".a-price-whole", "#price_inside_buybox"],
    "brand": ["#bylineInfo", ".a-size-medium.po-brand"],
    "description": ["#feature-bullets li", ".a-unordered-list li"],
    "image": ["#landingImage", "#imgBlkFront"],
    "rating": [".a-icon-star", "#acrPopover"],
    "review_count": ["#acrCustomerReviewText"],

    # Reviews section
    "review_text": ".review-text",
    "review_rating": ".a-icon-star",
    "review_date": ".review-date",
    "review_verified": ".avp-badge",
    "reviewer_name": ".a-profile-name",
}
