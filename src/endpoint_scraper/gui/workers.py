"""Background worker threads for scraping and status checking."""

import asyncio
import csv
import os
import random
from urllib.parse import urlparse

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from .. import config, session, crawler, extractors, utils
from .constants import CSV_PATH
from playwright.async_api import async_playwright


class ScrapeWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, url, mode):
        super().__init__()
        self.url = url
        self.mode = mode

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._scrape())
        except Exception as e:
            self.error.emit(str(e))

    async def _scrape(self):
        target = self.url
        if not target.startswith("http"):
            target = "https://" + target

        parsed = urlparse(target)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        base_domain = parsed.netloc

        self.log.emit(f"Checking sitemap.xml for {base_domain}...")
        sitemap_urls = extractors.fetch_sitemap(base_url)

        self.log.emit("Checking robots.txt...")
        disallowed = extractors.fetch_robots(base_url)

        async with async_playwright() as p:
            self.log.emit("Launching browser...")
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
                self.log.emit(f"Loaded {len(saved_cookies)} saved cookies")

            mode_label = "whole site" if self.mode == "1" else "single page"
            self.log.emit(f"Scraping ({mode_label}): {target}")

            internal, external, api_calls, assets = await crawler.crawl_website(
                context, target, base_url, base_domain, sitemap_urls, self.mode
            )

            self.log.emit("Parsing JS files for hardcoded routes & secrets...")
            js_routes, secrets = await extractors.parse_js_files(context, assets, base_domain)

            await browser.close()

        # Build results
        all_urls = internal | external
        query_params = extractors.extract_query_params(all_urls)
        url_patterns = extractors.group_url_patterns(internal)
        subdomains = extractors.discover_subdomains(all_urls, base_domain)

        rows = []
        for u in sorted(internal):
            rows.append({"category": utils.categorize(u), "value": u})
        for u in sorted(api_calls):
            rows.append({"category": "api-network", "value": u})
        for r in sorted(js_routes):
            rows.append({"category": "js-route", "value": r})
        for s in sorted(secrets):
            rows.append({"category": "exposed-secret", "value": s})
        for key in sorted(query_params):
            rows.append({"category": "query-param", "value": f"?{key}"})
        for pattern in sorted(url_patterns):
            rows.append({"category": "url-pattern", "value": pattern})
        for sub in sorted(subdomains):
            rows.append({"category": "subdomain", "value": sub})
        for u in sorted(external):
            rows.append({"category": "external", "value": u})
        for p in sorted(disallowed):
            rows.append({"category": "robots-disallowed", "value": base_url + p})

        # Save CSV
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Category", "URL / Value"])
            for r in rows:
                w.writerow([r["category"], r["value"]])

        self.log.emit(f"Done — {len(rows)} endpoints found")
        self.finished.emit(rows)


class StatusWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, urls):
        super().__init__()
        self.urls = urls

    def run(self):
        for i, url in enumerate(self.urls):
            try:
                if url.startswith("http"):
                    r = requests.head(url, timeout=8, allow_redirects=True)
                    self.progress.emit(i, str(r.status_code))
                else:
                    self.progress.emit(i, "—")
            except Exception:
                self.progress.emit(i, "ERR")
        self.finished.emit()
