"""
CLI Entry Point
Command-line interface for running the scraper
"""
import sys
import argparse
from .spider import SupplementSpider


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

    args = parser.parse_args()

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

    # Initialize and run spider
    try:
        spider = SupplementSpider(resume=args.resume)

        if args.category:
            # Scrape single category
            from .config import CATEGORIES
            category_url = CATEGORIES[args.category]
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


if __name__ == "__main__":
    main()
