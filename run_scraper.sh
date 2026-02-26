#!/bin/bash
# Convenience script to run Amazon scraper

cd "$(dirname "$0")"
source venv/bin/activate
python amazon_scraper/run.py "$@"
