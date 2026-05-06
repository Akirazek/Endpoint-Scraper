"""Entry point for endpoint scraper."""

import asyncio
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import random

from . import config
from . import session
from . import crawler
from . import extractors
from . import reporters


async def main():
    """Main entry point for the endpoint scraper."""
    print("\n╔══════════════════════════════════════════╗")
    print("║       ENDPOINT SCRAPER  v5.0             ║")
    print("╚══════════════════════════════════════════╝\n")

    target = input("Paste the URL to scrape: ").strip()
    if not target.startswith("http"):
        target = "https://" + target

    print("\nSelect scrape mode:")
    print("  [1] Whole website (crawl entire domain)")
    print("  [2] Single page only (links on this URL)\n")
    mode = input("Enter 1 or 2: ").strip()

    base_url = f"{urlparse(target).scheme}://{urlparse(target).netloc}"
    base_domain = urlparse(target).netloc

    print("\n  [*] Checking sitemap.xml...")
    sitemap_urls = extractors.fetch_sitemap(base_url)
    print("  [*] Checking robots.txt...")
    disallowed = extractors.fetch_robots(base_url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--window-size=1920,1080",
            ],
        )

        # Load saved cookies if available
        saved_cookies = session.load_cookies()
        context = await browser.new_context(
            user_agent=random.choice(config.USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            ignore_https_errors=True,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "DNT": "1",
            },
        )
        if saved_cookies:
            await context.add_cookies(saved_cookies)
            print(f"  [cookies] Loaded {len(saved_cookies)} saved cookies")

        internal, external, api_calls, assets = await crawler.crawl_website(
            context, target, base_url, base_domain, sitemap_urls, mode
        )

        # ── Parse all collected JS files ──
        print(f"\n  [*] Parsing JS files for hardcoded routes & secrets...")
        js_routes, secrets = await extractors.parse_js_files(context, assets, base_domain)

        await browser.close()

    # Aggregate and analyze results
    all_urls = internal | external
    query_params = extractors.extract_query_params(all_urls)
    url_patterns = extractors.group_url_patterns(internal)
    subdomains = extractors.discover_subdomains(all_urls, base_domain)

    # Print and save results
    reporters.print_and_save(
        internal,
        api_calls,
        external,
        disallowed,
        base_url,
        js_routes,
        secrets,
        query_params,
        url_patterns,
        subdomains,
    )


if __name__ == "__main__":
    asyncio.run(main())
