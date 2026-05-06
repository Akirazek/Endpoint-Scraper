"""Configuration and constants for endpoint scraper."""

# ══════════════════════════════════════════════
# SCRAPING CONFIG
# ══════════════════════════════════════════════
MAX_PAGES = 200  # 0 = unlimited
CONCURRENT_PAGES = 5  # pages scraped at the same time
MAX_RETRIES = 3  # retry failed pages
COOKIES_FILE = "cookies.json"

CAPTCHA_KEYWORDS = [
    "captcha",
    "recaptcha",
    "hcaptcha",
    "cf-challenge",
    "challenge-form",
    "are you human",
]

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

# Output paths
OUTPUT_DIR = "output"
CSV_OUTPUT = f"{OUTPUT_DIR}/endpoints.csv"
JSON_OUTPUT = f"{OUTPUT_DIR}/endpoints.json"
