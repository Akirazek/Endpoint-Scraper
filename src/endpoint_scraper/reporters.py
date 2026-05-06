"""Output formatting and reporting functions."""

import csv
import json
import os
from . import config
from . import utils


def print_and_save(
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
):
    """Print results and save to CSV and JSON files."""
    
    # Ensure output directory exists
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    categories = {}
    for u in sorted(internal):
        cat = utils.categorize(u)
        categories.setdefault(cat, []).append(u)

    print(f"\n{'═'*65}")
    print(f"  ENDPOINT SCRAPER v5.0 — RESULTS")
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
    with open(config.CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
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
    with open(config.JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            {
                "internal": sorted(internal),
                "api_calls": sorted(api_calls),
                "js_routes": sorted(js_routes),
                "secrets": sorted(secrets),
                "query_params": {k: list(v) for k, v in query_params.items()},
                "url_patterns": {k: v for k, v in url_patterns.items()},
                "subdomains": sorted(subdomains),
                "external": sorted(external),
                "disallowed": sorted(disallowed),
            },
            f,
            indent=2,
        )

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
    print(f"\n  ✅ Saved: {config.CSV_OUTPUT} + {config.JSON_OUTPUT}")
    print(f"{'═'*65}\n")
