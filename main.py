"""
Endpoint Scraper - Entry point
Simple wrapper that imports and runs the refactored scraper from src/
"""

import sys
import os

# Add src to path so we can import endpoint_scraper
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from endpoint_scraper.__main__ import main
import asyncio


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[*] Scraping interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)