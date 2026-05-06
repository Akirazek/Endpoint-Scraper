"""Main web crawler logic."""

import asyncio
import random
from urllib.parse import urlparse

from . import config
from . import session
from . import extractors


async def scrape_page(context, url, base_domain, internal, external, api_calls, assets, semaphore):
    """Scrape a single page and extract URLs."""
    async with semaphore:
        for attempt in range(1, config.MAX_RETRIES + 1):
            page = await context.new_page()
            await page.add_init_script(config.STEALTH_JS)
            await page.set_viewport_size(
                {"width": random.randint(1280, 1920), "height": random.randint(768, 1080)}
            )

            def handle_request(request):
                req_url = request.url.split("#")[0].rstrip("/")
                parsed = urlparse(req_url)
                if not parsed.scheme or not parsed.netloc:
                    return
                if base_domain in parsed.netloc:
                    if any(
                        x in req_url
                        for x in ["/api/", "/graphql", "/v1/", "/v2/", "/v3/", ".json", "/rest/"]
                    ):
                        api_calls.add(req_url)
                    elif any(
                        req_url.endswith(x)
                        for x in [".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2"]
                    ):
                        assets.add(req_url)
                    else:
                        internal.add(req_url)

            page.on("request", handle_request)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(1.2, 2.5))

                # CAPTCHA check
                if await extractors.detect_captcha(page):
                    print(f"\n  ⚠️  CAPTCHA DETECTED on {url}")
                    print(f"  [!] Pausing 15 seconds — manually solve if needed...")
                    await asyncio.sleep(15)

                await extractors.simulate_human(page)
                await extractors.smart_scroll(page)

                # Hover nav items
                nav_items = await page.query_selector_all(
                    "nav a, header a, [class*='nav'] a, [class*='menu'] > li"
                )
                for item in nav_items[:15]:
                    try:
                        await item.hover(timeout=800)
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                    except:
                        pass

                raw_urls = await page.evaluate(config.EXTRACT_JS)
                found = set()

                for href in raw_urls:
                    full_url = href.split("#")[0].rstrip("/")
                    parsed = urlparse(full_url)
                    if not parsed.scheme or not parsed.netloc:
                        continue
                    if base_domain in parsed.netloc:
                        internal.add(full_url)
                        found.add(full_url)
                    else:
                        external.add(full_url)

                # Save cookies after first successful page
                cookies = await context.cookies()
                session.save_cookies(cookies)

                await page.close()
                return found

            except Exception as e:
                await page.close()
                if attempt < config.MAX_RETRIES:
                    wait = attempt * 2
                    print(f"  [retry {attempt}/{config.MAX_RETRIES}] {url} — waiting {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    print(f"  [✗] Gave up on: {url}")
                    return set()


async def crawl_website(browser_context, target, base_url, base_domain, sitemap_urls, mode):
    """Crawl website using BFS queue approach."""
    from collections import deque

    internal = set()
    external = set()
    api_calls = set()
    assets = set()

    semaphore = asyncio.Semaphore(config.CONCURRENT_PAGES)

    if mode == "2":
        print(f"\n  [Mode 2] Single page scrape...\n")
        await scrape_page(browser_context, target, base_domain, internal, external, api_calls, assets, semaphore)

    else:
        print(f"\n  [Mode 1] Crawling entire website (max {config.MAX_PAGES} pages)...\n")

        queue = deque([target])
        visited = set()

        for u in sitemap_urls:
            if base_domain in urlparse(u).netloc:
                queue.append(u.rstrip("/"))

        count = 0
        while queue:
            if config.MAX_PAGES and count >= config.MAX_PAGES:
                print(f"\n  [!] Max pages reached ({config.MAX_PAGES})")
                break

            # Grab a batch of pages to run concurrently
            batch = []
            while queue and len(batch) < config.CONCURRENT_PAGES:
                url = queue.popleft()
                if url not in visited:
                    visited.add(url)
                    batch.append(url)
                    count += 1

            if not batch:
                break

            print(f"\n  [Batch] Crawling {len(batch)} pages concurrently...")
            results = await asyncio.gather(
                *[
                    scrape_page(browser_context, u, base_domain, internal, external, api_calls, assets, semaphore)
                    for u in batch
                ]
            )

            for found in results:
                for link in found:
                    if link not in visited:
                        queue.append(link)

            await asyncio.sleep(random.uniform(0.5, 1.2))

    # Add sitemap URLs
    for u in sitemap_urls:
        if base_domain in urlparse(u).netloc:
            internal.add(u.rstrip("/"))

    return internal, external, api_calls, assets
