import asyncio
import csv
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse, parse_qs
from collections import deque
from playwright.async_api import async_playwright
import requests
import random
import os

# ══════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════
MAX_PAGES        = 200    # 0 = unlimited
CONCURRENT_PAGES = 5      # pages scraped at the same time
MAX_RETRIES      = 3      # retry failed pages
COOKIES_FILE     = "cookies.json"
CAPTCHA_KEYWORDS = ["captcha", "recaptcha", "hcaptcha", "cf-challenge", "challenge-form", "are you human"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

# ══════════════════════════════════════════════
# STEALTH JS — hides Playwright fingerprints
# ══════════════════════════════════════════════
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'permissions', {
    get: () => ({ query: () => Promise.resolve({ state: 'granted' }) })
});
"""

# ══════════════════════════════════════════════
# DOM EXTRACTION JS
# ══════════════════════════════════════════════
EXTRACT_JS = """
() => {
    const urls = new Set();
    document.querySelectorAll('a[href]').forEach(el => { if (el.href) urls.add(el.href); });
    document.querySelectorAll('[data-href],[data-url],[data-link],[data-src]').forEach(el => {
        ['data-href','data-url','data-link','data-src'].forEach(attr => {
            const val = el.getAttribute(attr);
            if (val && val.startsWith('http')) urls.add(val);
        });
    });
    document.querySelectorAll('[onclick]').forEach(el => {
        const match = el.getAttribute('onclick').match(/['\"](https?:\\/\\/[^'\"]+)['\"]/)
        if (match) urls.add(match[1]);
    });
    document.querySelectorAll('form[action]').forEach(el => { if (el.action) urls.add(el.action); });
    document.querySelectorAll('meta[http-equiv="refresh"]').forEach(el => {
        const match = (el.getAttribute('content') || '').match(/url=(.+)/i);
        if (match) urls.add(match[1].trim());
    });
    function pierceDOM(root) {
        root.querySelectorAll('*').forEach(el => {
            if (el.shadowRoot) {
                el.shadowRoot.querySelectorAll('a[href]').forEach(a => { if (a.href) urls.add(a.href); });
                pierceDOM(el.shadowRoot);
            }
        });
    }
    pierceDOM(document);
    return [...urls];
}
"""

# ══════════════════════════════════════════════
# COOKIE PERSISTENCE
# ══════════════════════════════════════════════
def load_cookies():
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "r") as f:
            return json.load(f)
    return []

def save_cookies(cookies):
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"  [cookies] Saved {len(cookies)} cookies to {COOKIES_FILE}")

# ══════════════════════════════════════════════
# CAPTCHA DETECTION
# ══════════════════════════════════════════════
async def detect_captcha(page):
    content = (await page.content()).lower()
    title   = (await page.title()).lower()
    for kw in CAPTCHA_KEYWORDS:
        if kw in content or kw in title:
            return True
    return False

# ══════════════════════════════════════════════
# MOUSE MOVEMENT SIMULATION
# ══════════════════════════════════════════════
async def simulate_human(page):
    try:
        w = random.randint(300, 1600)
        h = random.randint(200, 900)
        # Smooth curved mouse movement
        for _ in range(random.randint(3, 6)):
            await page.mouse.move(
                random.randint(0, w),
                random.randint(0, h),
                steps=random.randint(10, 25)
            )
            await asyncio.sleep(random.uniform(0.1, 0.3))
    except:
        pass

# ══════════════════════════════════════════════
# SMART SCROLL (random speed)
# ══════════════════════════════════════════════
async def smart_scroll(page):
    scroll_height = await page.evaluate("document.body.scrollHeight")
    current = 0
    while current < scroll_height:
        step = random.randint(300, 900)        # random scroll distance
        delay = random.uniform(0.05, 0.25)     # random speed
        await page.evaluate(f"window.scrollTo(0, {current})")
        await asyncio.sleep(delay)
        current += step
        scroll_height = await page.evaluate("document.body.scrollHeight")
    await page.evaluate("window.scrollTo(0, 0)")

# ══════════════════════════════════════════════
# JS FILE PARSER — find hardcoded API routes
# ══════════════════════════════════════════════
async def parse_js_files(context, js_urls, base_domain):
    found_routes = set()
    found_secrets = set()

    # Patterns for API routes inside JS
    route_pattern   = re.compile(r'["\`\'](/[a-zA-Z0-9_\-/]{3,})["\`\']')
    # Patterns for exposed tokens/keys
    secret_patterns = [
        re.compile(r'(?:api[_-]?key|apikey|access[_-]?token|secret[_-]?key|auth[_-]?token|bearer)\s*[:=]\s*["\']([a-zA-Z0-9\-_\.]{10,})["\']', re.IGNORECASE),
        re.compile(r'(?:Authorization|X-Api-Key)\s*:\s*["\']([^"\']{10,})["\']', re.IGNORECASE),
    ]

    print(f"\n  [JS Parser] Scanning {len(js_urls)} JS files...")
    sem = asyncio.Semaphore(5)

    async def fetch_js(js_url):
        async with sem:
            try:
                page = await context.new_page()
                await page.add_init_script(STEALTH_JS)
                res  = await page.goto(js_url, wait_until="domcontentloaded", timeout=15000)
                body = await page.content()
                await page.close()

                # Extract routes
                for match in route_pattern.findall(body):
                    if any(x in match for x in ["/api/", "/v1/", "/v2/", "/v3/", "/graphql", "/rest/"]):
                        found_routes.add(match)

                # Extract secrets
                for pat in secret_patterns:
                    for match in pat.findall(body):
                        found_secrets.add(match)

            except:
                pass

    await asyncio.gather(*[fetch_js(u) for u in list(js_urls)[:30]])  # cap at 30 JS files
    return found_routes, found_secrets

# ══════════════════════════════════════════════
# QUERY PARAMETER EXTRACTION
# ══════════════════════════════════════════════
def extract_query_params(all_urls):
    params = {}
    for url in all_urls:
        parsed = urlparse(url)
        if parsed.query:
            for key, values in parse_qs(parsed.query).items():
                params.setdefault(key, set()).update(values)
    return params

# ══════════════════════════════════════════════
# URL PATTERN GROUPING — detect dynamic routes
# ══════════════════════════════════════════════
def group_url_patterns(urls):
    patterns = {}
    for url in urls:
        path   = urlparse(url).path
        parts  = path.strip("/").split("/")
        # Replace numeric/hash segments with [id] or [slug]
        normalized = []
        for part in parts:
            if re.match(r'^\d+$', part):
                normalized.append("[id]")
            elif re.match(r'^[a-f0-9]{8,}$', part, re.IGNORECASE):
                normalized.append("[hash]")
            elif re.match(r'^[a-zA-Z0-9\-_]{20,}$', part):
                normalized.append("[slug]")
            else:
                normalized.append(part)
        pattern = "/" + "/".join(normalized)
        patterns.setdefault(pattern, []).append(url)
    return patterns

# ══════════════════════════════════════════════
# SUBDOMAIN DISCOVERY
# ══════════════════════════════════════════════
def discover_subdomains(all_urls, base_domain):
    root   = ".".join(base_domain.split(".")[-2:])  # e.g. gamebanana.com
    subs   = set()
    for url in all_urls:
        netloc = urlparse(url).netloc
        if root in netloc and netloc != base_domain:
            subs.add(netloc)
    return subs

# ══════════════════════════════════════════════
# SITEMAP + ROBOTS
# ══════════════════════════════════════════════
def fetch_sitemap(base_url):
    urls = set()
    for path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/sitemap.xml"]:
        try:
            res = requests.get(
                base_url.rstrip("/") + path,
                headers={"User-Agent": random.choice(USER_AGENTS)},
                timeout=10
            )
            if res.status_code == 200 and "xml" in res.headers.get("Content-Type", ""):
                root = ET.fromstring(res.content)
                ns   = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                for loc in root.findall(".//sm:loc", ns):
                    if loc.text:
                        urls.add(loc.text.strip())
                print(f"  [sitemap] {len(urls)} URLs")
                break
        except:
            pass
    return urls

def fetch_robots(base_url):
    disallowed = set()
    try:
        res = requests.get(
            base_url.rstrip("/") + "/robots.txt",
            headers={"User-Agent": random.choice(USER_AGENTS)},
            timeout=10
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

# ══════════════════════════════════════════════
# SCRAPE SINGLE PAGE (with retry)
# ══════════════════════════════════════════════
async def scrape_page(context, url, base_domain, internal, external, api_calls, assets, semaphore):
    async with semaphore:
        for attempt in range(1, MAX_RETRIES + 1):
            page = await context.new_page()
            await page.add_init_script(STEALTH_JS)
            await page.set_viewport_size({
                "width":  random.randint(1280, 1920),
                "height": random.randint(768, 1080)
            })

            def handle_request(request):
                req_url = request.url.split("#")[0].rstrip("/")
                parsed  = urlparse(req_url)
                if not parsed.scheme or not parsed.netloc:
                    return
                if base_domain in parsed.netloc:
                    if any(x in req_url for x in ["/api/", "/graphql", "/v1/", "/v2/", "/v3/", ".json", "/rest/"]):
                        api_calls.add(req_url)
                    elif any(req_url.endswith(x) for x in [".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2"]):
                        assets.add(req_url)
                    else:
                        internal.add(req_url)

            page.on("request", handle_request)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(1.2, 2.5))

                # CAPTCHA check
                if await detect_captcha(page):
                    print(f"\n  ⚠️  CAPTCHA DETECTED on {url}")
                    print(f"  [!] Pausing 15 seconds — manually solve if needed...")
                    await asyncio.sleep(15)

                await simulate_human(page)
                await smart_scroll(page)

                # Hover nav items
                nav_items = await page.query_selector_all("nav a, header a, [class*='nav'] a, [class*='menu'] > li")
                for item in nav_items[:15]:
                    try:
                        await item.hover(timeout=800)
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                    except:
                        pass

                raw_urls = await page.evaluate(EXTRACT_JS)
                found    = set()

                for href in raw_urls:
                    full_url = href.split("#")[0].rstrip("/")
                    parsed   = urlparse(full_url)
                    if not parsed.scheme or not parsed.netloc:
                        continue
                    if base_domain in parsed.netloc:
                        internal.add(full_url)
                        found.add(full_url)
                    else:
                        external.add(full_url)

                # Save cookies after first successful page
                cookies = await context.cookies()
                save_cookies(cookies)

                await page.close()
                return found

            except Exception as e:
                await page.close()
                if attempt < MAX_RETRIES:
                    wait = attempt * 2
                    print(f"  [retry {attempt}/{MAX_RETRIES}] {url} — waiting {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    print(f"  [✗] Gave up on: {url}")
                    return set()

# ══════════════════════════════════════════════
# CATEGORIZE URL
# ══════════════════════════════════════════════
def categorize(url):
    path = urlparse(url).path.lower()
    if any(x in path for x in ["/api/", "/v1/", "/v2/", "/graphql", ".json", "/rest/"]):
        return "api"
    if any(x in path for x in ["/profile", "/user", "/account", "/me/", "/member"]):
        return "user"
    if any(x in path for x in ["/search", "/find", "/query", "/filter", "/browse"]):
        return "search"
    if any(x in path for x in ["/login", "/signup", "/register", "/auth", "/oauth", "/logout"]):
        return "auth"
    if any(x in path for x in ["/admin", "/dashboard", "/panel", "/manage", "/cms"]):
        return "admin"
    if any(x in path for x in ["/download", "/uploads", "/files", "/mods", "/submissions"]):
        return "content"
    return "page"

# ══════════════════════════════════════════════
# PRINT + SAVE
# ══════════════════════════════════════════════
def print_and_save(internal, api_calls, external, disallowed,
                   base_url, js_routes, secrets, query_params,
                   url_patterns, subdomains):

    categories = {}
    for u in sorted(internal):
        cat = categorize(u)
        categories.setdefault(cat, []).append(u)

    print(f"\n{'═'*65}")
    print(f"  ENDPOINT SCRAPER v4.0 — RESULTS")
    print(f"{'═'*65}")

    for cat, urls in sorted(categories.items()):
        print(f"\n  [{cat.upper()}] ({len(urls)})")
        print(f"  {'─'*60}")
        for u in urls:
            print(f"    {u}")

    if api_calls:
        print(f"\n  [API NETWORK CALLS] ({len(api_calls)})")
        print(f"  {'─'*60}")
        for u in sorted(api_calls):
            print(f"    {u}")

    if js_routes:
        print(f"\n  [JS FILE — HARDCODED ROUTES] ({len(js_routes)})")
        print(f"  {'─'*60}")
        for r in sorted(js_routes):
            print(f"    {r}")

    if secrets:
        print(f"\n  [⚠️  EXPOSED SECRETS / TOKENS] ({len(secrets)})")
        print(f"  {'─'*60}")
        for s in sorted(secrets):
            print(f"    {s}")

    if query_params:
        print(f"\n  [QUERY PARAMETERS] ({len(query_params)})")
        print(f"  {'─'*60}")
        for key, vals in sorted(query_params.items()):
            print(f"    ?{key}  →  example: {list(vals)[0] if vals else ''}")

    if url_patterns:
        print(f"\n  [URL PATTERNS / DYNAMIC ROUTES] ({len(url_patterns)})")
        print(f"  {'─'*60}")
        for pattern, examples in sorted(url_patterns.items()):
            print(f"    {pattern}  ({len(examples)} URLs)")

    if subdomains:
        print(f"\n  [SUBDOMAINS DISCOVERED] ({len(subdomains)})")
        print(f"  {'─'*60}")
        for sub in sorted(subdomains):
            print(f"    {sub}")

    if external:
        print(f"\n  [EXTERNAL LINKS] ({len(external)})")
        print(f"  {'─'*60}")
        for u in sorted(external):
            print(f"    {u}")

    if disallowed:
        print(f"\n  [ROBOTS.TXT DISALLOWED] ({len(disallowed)})")
        print(f"  {'─'*60}")
        for p in sorted(disallowed):
            print(f"    {base_url}{p}")

    # ── Save CSV ──
    with open("endpoints.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "URL / Value"])
        for cat, urls in sorted(categories.items()):
            for u in urls:
                writer.writerow([cat, u])
        for u in sorted(api_calls):
            writer.writerow(["api-network", u])
        for r in sorted(js_routes):
            writer.writerow(["js-route", r])
        for s in sorted(secrets):
            writer.writerow(["exposed-secret", s])
        for key, vals in sorted(query_params.items()):
            writer.writerow(["query-param", f"?{key}"])
        for pattern in sorted(url_patterns.keys()):
            writer.writerow(["url-pattern", pattern])
        for sub in sorted(subdomains):
            writer.writerow(["subdomain", sub])
        for u in sorted(external):
            writer.writerow(["external", u])
        for p in sorted(disallowed):
            writer.writerow(["robots-disallowed", base_url + p])

    # ── Save JSON ──
    with open("endpoints.json", "w", encoding="utf-8") as f:
        json.dump({
            "internal":      sorted(internal),
            "api_calls":     sorted(api_calls),
            "js_routes":     sorted(js_routes),
            "secrets":       sorted(secrets),
            "query_params":  {k: list(v) for k, v in query_params.items()},
            "url_patterns":  {k: v for k, v in url_patterns.items()},
            "subdomains":    sorted(subdomains),
            "external":      sorted(external),
            "disallowed":    sorted(disallowed),
        }, f, indent=2)

    total = len(internal) + len(api_calls)
    print(f"\n{'═'*65}")
    print(f"  Internal endpoints : {len(internal)}")
    print(f"  API calls caught   : {len(api_calls)}")
    print(f"  JS hardcoded routes: {len(js_routes)}")
    print(f"  Exposed secrets    : {len(secrets)}")
    print(f"  Query params       : {len(query_params)}")
    print(f"  URL patterns       : {len(url_patterns)}")
    print(f"  Subdomains found   : {len(subdomains)}")
    print(f"  Grand total        : {total}")
    print(f"\n  ✅ Saved: endpoints.csv + endpoints.json")

# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
async def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║       ENDPOINT SCRAPER  v4.0             ║")
    print("╚══════════════════════════════════════════╝\n")

    target = input("Paste the URL to scrape: ").strip()
    if not target.startswith("http"):
        target = "https://" + target

    print("\nSelect scrape mode:")
    print("  [1] Whole website (crawl entire domain)")
    print("  [2] Single page only (links on this URL)\n")
    mode = input("Enter 1 or 2: ").strip()

    base_url    = f"{urlparse(target).scheme}://{urlparse(target).netloc}"
    base_domain = urlparse(target).netloc

    internal  = set()
    external  = set()
    api_calls = set()
    assets    = set()

    print("\n  [*] Checking sitemap.xml...")
    sitemap_urls = fetch_sitemap(base_url)
    print("  [*] Checking robots.txt...")
    disallowed = fetch_robots(base_url)

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
            ]
        )

        # Load saved cookies if available
        saved_cookies = load_cookies()
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            ignore_https_errors=True,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "DNT": "1",
            }
        )
        if saved_cookies:
            await context.add_cookies(saved_cookies)
            print(f"  [cookies] Loaded {len(saved_cookies)} saved cookies")

        semaphore = asyncio.Semaphore(CONCURRENT_PAGES)

        if mode == "2":
            print(f"\n  [Mode 2] Single page scrape...\n")
            await scrape_page(context, target, base_domain, internal, external, api_calls, assets, semaphore)

        else:
            print(f"\n  [Mode 1] Crawling entire website (max {MAX_PAGES} pages)...\n")

            queue   = deque([target])
            visited = set()

            for u in sitemap_urls:
                if base_domain in urlparse(u).netloc:
                    queue.append(u.rstrip("/"))

            count = 0
            while queue:
                if MAX_PAGES and count >= MAX_PAGES:
                    print(f"\n  [!] Max pages reached ({MAX_PAGES})")
                    break

                # Grab a batch of pages to run concurrently
                batch = []
                while queue and len(batch) < CONCURRENT_PAGES:
                    url = queue.popleft()
                    if url not in visited:
                        visited.add(url)
                        batch.append(url)
                        count += 1

                if not batch:
                    break

                print(f"\n  [Batch] Crawling {len(batch)} pages concurrently...")
                results = await asyncio.gather(*[
                    scrape_page(context, u, base_domain, internal, external, api_calls, assets, semaphore)
                    for u in batch
                ])

                for found in results:
                    for link in found:
                        if link not in visited:
                            queue.append(link)

                await asyncio.sleep(random.uniform(0.5, 1.2))

        # ── Parse all collected JS files ──
        print(f"\n  [*] Parsing JS files for hardcoded routes & secrets...")
        js_routes, secrets = await parse_js_files(context, assets, base_domain)

        await browser.close()

    # ── Add sitemap URLs ──
    for u in sitemap_urls:
        if base_domain in urlparse(u).netloc:
            internal.add(u.rstrip("/"))

    all_urls     = internal | external
    query_params = extract_query_params(all_urls)
    url_patterns = group_url_patterns(internal)
    subdomains   = discover_subdomains(all_urls, base_domain)

    print_and_save(
        internal, api_calls, external, disallowed,
        base_url, js_routes, secrets, query_params,
        url_patterns, subdomains
    )

if __name__ == "__main__":
    asyncio.run(main())