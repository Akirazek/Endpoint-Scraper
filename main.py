"""Endpoint Scraper — GUI entry point."""

import sys
import os

os.environ["QT_API"] = "pyqt6"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from endpoint_scraper.gui import run

if __name__ == "__main__":
    run()
