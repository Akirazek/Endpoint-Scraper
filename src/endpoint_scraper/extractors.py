"""URL extraction and parsing functions."""

import asyncio
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse, parse_qs
import requests
import random

from . import config


async def detect_captcha(page):
    """Detect if page has a CAPTCHA challenge."""
    content = (await page.content()).lower()
    title = (await page.title()).lower()
    for kw in config.CAPTCHA_KEYWORDS:
        if kw in content or kw in title:
            return True
    return False


async def simulate_human(page):
    """Simulate human-like mouse movements."""
    try:
        w = random.randint(300, 1600)
        h = random.randint(200, 900)
        # Smooth curved mouse movement
        for _ in range(random.randint(3, 6)):
            await page.mouse.move(
                random.randint(0, w),
                random.randint(0, h),
                steps=random.randint(10, 25),
            )
            await asyncio.sleep(random.uniform(0.1, 0.3))
    except:
        pass


async def smart_scroll(page):
    """Scroll page with random speed and distance."""
    scroll_height = await page.evaluate("document.body.scrollHeight")
    current = 0
    while current < scroll_height:
        step = random.randint(300, 900)  # random scroll distance
        delay = random.uniform(0.05, 0.25)  # random speed
        await page.evaluate(f"window.scrollTo(0, {current})")
        await asyncio.sleep(delay)
        current += step
        scroll_height = await page.evaluate("document.body.scrollHeight")
    await page.evaluate("window.scrollTo(0, 0)")


async def parse_js_files(context, js_urls, base_domain):
    """Find hardcoded API routes and exposed secrets in JS files."""
    found_routes = set()
    found_secrets = set()

    # Patterns for API routes inside JS
    route_pattern = re.compile(r'["\`\'](/[a-zA-Z0-9_\-/]{3,})["\`\']')
    # Patterns for exposed tokens/keys
    secret_patterns = [
        re.compile(
            r'(?:api[_-]?key|apikey|access[_-]?token|secret[_-]?key|auth[_-]?token|bearer)\s*[:=]\s*["\']([a-zA-Z0-9\-_\.]{10,})["\']',
            re.IGNORECASE,
        ),
        re.compile(
            r'(?:Authorization|X-Api-Key)\s*:\s*["\']([^"\']{10,})["\']', re.IGNORECASE
        ),
    ]

    print(f"\n  [JS Parser] Scanning {len(js_urls)} JS files...")
    sem = asyncio.Semaphore(5)

    async def fetch_js(js_url):
        async with sem:
            try:
                page = await context.new_page()
                await page.add_init_script(config.STEALTH_JS)
                res = await page.goto(
                    js_url, wait_until="domcontentloaded", timeout=15000
                )
                body = await page.content()
                await page.close()

                # Extract routes
                for match in route_pattern.findall(body):
                    if any(
                        x in match
                        for x in ["/api/", "/v1/", "/v2/", "/v3/", "/graphql", "/rest/"]
                    ):
                        found_routes.add(match)

                # Extract secrets
                for pat in secret_patterns:
                    for match in pat.findall(body):
                        found_secrets.add(match)

            except:
                pass

    await asyncio.gather(*[fetch_js(u) for u in list(js_urls)[:30]])  # cap at 30 JS files
    return found_routes, found_secrets


def extract_query_params(all_urls):
    """Extract query parameters from URLs."""
    params = {}
    for url in all_urls:
        parsed = urlparse(url)
        if parsed.query:
            for key, values in parse_qs(parsed.query).items():
                params.setdefault(key, set()).update(values)
    return params


def group_url_patterns(urls):
    """Detect dynamic routes by normalizing URL patterns."""
    patterns = {}
    for url in urls:
        path = urlparse(url).path
        parts = path.strip("/").split("/")
        # Replace numeric/hash segments with [id] or [slug]
        normalized = []
        for part in parts:
            if re.match(r"^\d+$", part):
                normalized.append("[id]")
            elif re.match(r"^[a-f0-9]{8,}$", part, re.IGNORECASE):
                normalized.append("[hash]")
            elif re.match(r"^[a-zA-Z0-9\-_]{20,}$", part):
                normalized.append("[slug]")
            else:
                normalized.append(part)
        pattern = "/" + "/".join(normalized)
        patterns.setdefault(pattern, []).append(url)
    return patterns


def discover_subdomains(all_urls, base_domain):
    """Discover subdomains from collected URLs."""
    root = ".".join(base_domain.split(".")[-2:])  # e.g. gamebanana.com
    subs = set()
    for url in all_urls:
        netloc = urlparse(url).netloc
        if root in netloc and netloc != base_domain:
            subs.add(netloc)
    return subs


def fetch_sitemap(base_url):
    """Fetch URLs from sitemap.xml."""
    urls = set()
    for path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/sitemap.xml"]:
        try:
            res = requests.get(
                base_url.rstrip("/") + path,
                headers={"User-Agent": random.choice(config.USER_AGENTS)},
                timeout=10,
            )
            if res.status_code == 200 and "xml" in res.headers.get("Content-Type", ""):
                root = ET.fromstring(res.content)
                ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                for loc in root.findall(".//sm:loc", ns):
                    if loc.text:
                        urls.add(loc.text.strip())
                print(f"  [sitemap] {len(urls)} URLs")
                break
        except:
            pass
    return urls


def fetch_robots(base_url):
    """Fetch disallowed paths from robots.txt."""
    disallowed = set()
    try:
        res = requests.get(
            base_url.rstrip("/") + "/robots.txt",
            headers={"User-Agent": random.choice(config.USER_AGENTS)},
            timeout=10,
        )
        if res.status_code == 200:
            for line in res.text.splitlines():
                if line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[-1].strip()
                    if path:
                        disallowed.add(path)
    except:
        pass
    return disallowed
