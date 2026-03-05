"""
CLI Entry Point
Command-line interface for running the scraper
"""
import os
import sys
import argparse
from .spider import SupplementSpider
from .config import SCRAPING_SETTINGS, DATABASE_SETTINGS


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Amazon Supplement Scraper - Extract product data for affiliate website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python amazon_scraper/run.py                    # Start fresh
  python amazon_scraper/run.py --resume           # Resume from checkpoint
  python amazon_scraper/run.py --category vitamin-d  # Scrape specific category
  python amazon_scraper/run.py --workers 4 --proxy http://user:pass@host:port
  python amazon_scraper/run.py --refresh-stale    # Re-scrape stale products
  python amazon_scraper/run.py --refresh-asin B00FMZQKQ6  # Re-scrape one product

For more info: https://github.com/yourusername/longevity-experiments
        """
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )

    parser.add_argument(
        '--category',
        type=str,
        help='Scrape specific category only (e.g., vitamin-d)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test mode - extract but don\'t save data'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=SCRAPING_SETTINGS["workers"],
        help=f'Number of concurrent workers (default: {SCRAPING_SETTINGS["workers"]})'
    )

    parser.add_argument(
        '--proxy',
        type=str,
        default=None,
        help='Proxy URL (falls back to PROXY_URL env var)'
    )

    parser.add_argument(
        '--fetcher',
        type=str,
        default=SCRAPING_SETTINGS["fetcher_backend"],
        help=f'Fetcher backend name (default: {SCRAPING_SETTINGS["fetcher_backend"]})'
    )

    # Refresh flags
    parser.add_argument(
        '--refresh-stale',
        action='store_true',
        help='Re-scrape products older than stale threshold'
    )

    parser.add_argument(
        '--refresh-asin',
        type=str,
        help='Re-scrape a specific product by ASIN'
    )

    parser.add_argument(
        '--stale-days',
        type=int,
        default=DATABASE_SETTINGS["stale_threshold_days"],
        help=f'Stale threshold in days (default: {DATABASE_SETTINGS["stale_threshold_days"]})'
    )

    args = parser.parse_args()

    # Resolve proxy: CLI flag > env var
    proxy = args.proxy or os.environ.get("PROXY_URL")

    # Validate arguments
    if args.category:
        from .config import CATEGORIES
        if args.category not in CATEGORIES:
            print(f"Error: Unknown category '{args.category}'")
            print(f"Available categories: {', '.join(CATEGORIES.keys())}")
            sys.exit(1)

    # Show warning for dry-run
    if args.dry_run:
        print("⚠️  DRY RUN MODE - Data will not be saved")
        print()

    # Print config
    print(f"Workers: {args.workers}")
    print(f"Proxy: {'configured' if proxy else 'none'}")
    print(f"Fetcher: {args.fetcher}")
    print()

    # Handle refresh modes
    if args.refresh_stale or args.refresh_asin:
        _handle_refresh(args, proxy)
        return

    # Initialize and run spider
    try:
        spider = SupplementSpider(
            resume=args.resume,
            workers=args.workers,
            proxy=proxy,
            fetcher_backend=args.fetcher,
        )

        # Initialize browser settings (delivery location) for USD pricing
        spider.initialize_browser_settings()

        if args.category:
            # Scrape single category
            from .config import CATEGORIES
            category_url = CATEGORIES[args.category]
            print("=" * 80)
            print(f"Amazon Supplement Scraper - Category: {args.category}")
            print("=" * 80)
            spider.scrape_category(args.category, category_url)
            spider.state_manager.complete_category(args.category)
        else:
            # Scrape all categories
            spider.start()

        spider.print_final_stats()

    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
        print("Progress has been saved. Use --resume to continue.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


def _handle_refresh(args, proxy: str) -> None:
    """Handle --refresh-stale and --refresh-asin flags."""
    from .database import Database

    db = Database()

    if args.refresh_asin:
        # Refresh a single ASIN
        product = db.get_product(args.refresh_asin)
        if product:
            pairs = [(args.refresh_asin, product["category"])]
        else:
            # ASIN not in DB — let user specify category or default
            print(f"ASIN {args.refresh_asin} not found in database, will scrape as new.")
            category = args.category or "unknown"
            pairs = [(args.refresh_asin, category)]
    else:
        # Refresh stale
        pairs = db.get_stale_asins(threshold_days=args.stale_days)

    if not pairs:
        print("No products to refresh.")
        sys.exit(0)

    print(f"Found {len(pairs)} product(s) to refresh")

    try:
        spider = SupplementSpider(
            resume=False,
            workers=args.workers,
            proxy=proxy,
            fetcher_backend=args.fetcher,
        )
        spider.exporter.load_existing_asins()
        spider.initialize_browser_settings()
        spider.refresh_asins(pairs)
        spider.print_final_stats()
    except KeyboardInterrupt:
        print("\n\n⚠️  Refresh interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
