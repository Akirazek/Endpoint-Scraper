"""Session and cookie management."""

import json
import os
from . import config


def load_cookies():
    """Load cookies from file if available."""
    if os.path.exists(config.COOKIES_FILE):
        with open(config.COOKIES_FILE, "r") as f:
            return json.load(f)
    return []


def save_cookies(cookies):
    """Save cookies to file."""
    with open(config.COOKIES_FILE, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"  [cookies] Saved {len(cookies)} cookies to {config.COOKIES_FILE}")
