# Endpoint Scraper

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Playwright](https://img.shields.io/badge/Powered%20by-Playwright-2EAD33.svg)](https://playwright.dev)

> A web crawling tool built for security research and bug bounty hunting.

Endpoint Scraper is a multi-threaded web crawler that digs through websites to find API endpoints, routes, and things that probably shouldn't be publicly visible. It uses Playwright under the hood with some anti-detection stuff baked in, so it's pretty good at crawling modern JS-heavy sites without getting immediately blocked.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Output & Categories](#output--categories)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Development](#development)
- [Legal & Disclaimer](#legal--disclaimer)
- [Contributing](#contributing)
- [License](#license)
- [Roadmap](#roadmap)

---

## Features

### Endpoint Discovery
- **Full Website Crawling** — BFS-based crawler with configurable depth limits
- **Single Page Analysis** — Deep extraction from individual pages
- **Multi-Source Extraction** — Pulls URLs from the DOM, JavaScript files, network requests, and shadow DOM
- **API Route Detection** — Finds REST, GraphQL, and other API endpoints
- **JavaScript Analysis** — Parses minified JS for hardcoded routes and secrets

### Anti-Detection
- **Browser Fingerprint Spoofing** — Tries to look like a real browser
- **Human-Like Behavior** — Simulates mouse movements, scrolling, and basic interactions
- **Dynamic User Agents** — Rotates through different browser signatures
- **Cookie Persistence** — Keeps session state between crawls
- **CAPTCHA Handling** — Detects CAPTCHAs and pauses for manual intervention

### Analysis
- **Subdomain Discovery** — Finds related domains and subdomains
- **Query Parameter Extraction** — Catalogs all URL params with examples
- **Dynamic Route Detection** — Groups URLs into patterns like `/users/[id]/posts`
- **Secret Scanning** — Looks for exposed tokens, API keys, and credentials
- **Robots.txt & Sitemap Parsing** — Uses site directives to find hidden endpoints

### Output
- **CSV Export** — Easy to open in spreadsheets
- **JSON Export** — Structured data for scripting or further processing
- **Categorized Results** — Endpoints are auto-classified by type
- **Network Call Logging** — Captures AJAX and API calls in real-time

---

## Installation

### Requirements
- Python 3.8 or higher
- At least 2GB RAM (4GB is better for larger sites)
- 100MB free storage
- A stable internet connection

### Setup

#### Option 1: Basic Install
```bash
git clone https://github.com/yourusername/endpoint-scraper.git
cd endpoint-scraper

pip install -r requirements.txt

playwright install chromium
```

#### Option 2: Dev Setup
```bash
git clone https://github.com/yourusername/endpoint-scraper.git
cd endpoint-scraper

pip install -e ".[dev]"

playwright install

# optional
pytest
```

#### Option 3: Docker (Coming Soon)
```bash
# planned for v6.0
docker run -it endpoint-scraper:latest
```

### Dependencies
- `playwright>=1.40.0` — browser automation
- `requests>=2.31.0` — HTTP client for sitemap/robots parsing

---

## Usage

### Running It

```bash
# from project root
python main.py

# as a module
python -m endpoint_scraper

# from src directory
cd src && python -m endpoint_scraper
```

### Interactive Mode

The tool runs interactively and asks you two things:

1. **Target URL**
Paste the URL to scrape: https://example.com

text

2. **Scrape Mode**
Select scrape mode:
Whole website (crawl entire domain)
Single page only (links on this URL)

Enter 1 or 2: 1

text

### Programmatic Usage

```python
from endpoint_scraper import crawler, extractors, reporters

async def custom_scrape():
 # your custom logic here
 pass
```

```python
import endpoint_scraper.config as config

config.MAX_PAGES = 500
config.CONCURRENT_PAGES = 10
```

### Example Output
╔══════════════════════════════════════════╗
║ ENDPOINT SCRAPER v5.0 ║
╚══════════════════════════════════════════╝

Paste the URL to scrape: https://api.example.com
Select scrape mode: 1

[*] Checking sitemap.xml...
[*] Checking robots.txt...
[cookies] Loaded 15 saved cookies

[Mode 1] Crawling entire website (max 200 pages)...

[Batch] Crawling 5 pages concurrently...
[JS Parser] Scanning 23 JS files...
Saved: output/endpoints.csv + output/endpoints.json

text

---

## Output & Categories

Results are saved to the `output/` folder with timestamped filenames.

### CSV (`endpoints.csv`)
```csv
Category,URL / Value
api,/api/v1/users
api,/api/v2/posts/123
user,/profile/settings
auth,/login/oauth
```

### JSON (`endpoints.json`)
```json
{
  "internal": ["/", "/about", "/api/v1/users"],
  "api_calls": ["/api/graphql", "/api/rest/v2/data"],
  "js_routes": ["/api/internal/logs"],
  "secrets": ["sk_live_abc123def456"],
  "query_params": {"id": ["123", "456"], "token": ["xyz789"]},
  "url_patterns": {"/users/[id]": ["/users/123", "/users/456"]},
  "subdomains": ["api.example.com", "cdn.example.com"],
  "external": ["https://external-service.com/api"],
  "disallowed": ["/admin", "/private"]
}
```

### Categories

| Category | Description | Example |
|----------|-------------|---------|
| `api` | REST/GraphQL endpoints | `/api/v1/users`, `/graphql` |
| `user` | User profiles & accounts | `/profile`, `/account/settings` |
| `search` | Search & filtering | `/search`, `/api/search/users` |
| `auth` | Authentication routes | `/login`, `/oauth/callback` |
| `admin` | Admin panels | `/admin`, `/dashboard` |
| `content` | Files and uploads | `/uploads`, `/files/docs.pdf` |
| `page` | Regular web pages | `/about`, `/contact` |
| `api-network` | Intercepted AJAX calls | `POST /api/messages/send` |
| `js-route` | Routes found in JS files | Hardcoded paths in minified JS |
| `exposed-secret` | API keys and tokens | `sk_live_abc123...` |
| `query-param` | URL parameters | `?id=123&token=xyz` |
| `url-pattern` | Dynamic route patterns | `/users/[id]/posts` |
| `subdomain` | Discovered subdomains | `api.example.com` |
| `external` | External links | `https://external.com` |
| `robots-disallowed` | Blocked by robots.txt | `/private`, `/admin` |

---

## Configuration

Edit `src/endpoint_scraper/config.py` to adjust behavior:

```python
# crawl limits
MAX_PAGES = 200              # 0 = unlimited
CONCURRENT_PAGES = 5         # parallel pages
MAX_RETRIES = 3              # retries on failure

# anti-detection
USER_AGENTS = [...]          # user agent rotation list
CAPTCHA_KEYWORDS = [...]     # keywords to detect CAPTCHAs

# output
OUTPUT_DIR = "output"
CSV_OUTPUT = f"{OUTPUT_DIR}/endpoints.csv"
JSON_OUTPUT = f"{OUTPUT_DIR}/endpoints.json"

# browser scripts
STEALTH_JS = """..."""       # injected to avoid detection
EXTRACT_JS = """..."""       # DOM extraction logic
```

### Environment Variables
```bash
export ENDPOINT_SCRAPER_OUTPUT_DIR="/custom/path"
export ENDPOINT_SCRAPER_DEBUG=1
```

---

## Architecture
endpoint-scraper/
├── src/endpoint_scraper/
│ ├── _init_.py
│ ├── _main_.py
│ ├── config.py
│ ├── session.py
│ ├── crawler.py
│ ├── extractors.py
│ ├── reporters.py
│ └── utils.py
├── main.py
├── output/
├── requirements.txt
├── pyproject.toml
├── README.md
├── .gitignore
└── LICENSE

text

### Modules

| Module | What it does |
|--------|--------------|
| `config.py` | Constants, user agents, JS payloads |
| `session.py` | Cookie loading/saving, session persistence |
| `crawler.py` | Page scraping, queue management, concurrency |
| `extractors.py` | URL parsing, pattern detection, secret scanning |
| `reporters.py` | Result formatting, CSV/JSON export |
| `utils.py` | Helper functions, URL categorization |

---

## Development

```bash
git clone https://github.com/zejestry/endpoint-scraper.git
cd endpoint-scraper

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -e ".[dev]"

pre-commit install

pytest
black src/
flake8 src/
mypy src/
```

### Tests
```bash
pytest tests/
pytest tests/integration/
pytest --cov=endpoint_scraper --cov-report=html
```

### Code Quality Tools
- **Black** — formatting
- **Flake8** — linting
- **MyPy** — type checking
- **Pre-commit** — runs checks before each commit

---

## Legal & Disclaimer

**This tool is for authorized security testing only.**

Seriously — don't use this on systems you don't own or have explicit permission to test. Unauthorized use can violate computer fraud laws depending on your jurisdiction. The usual stuff applies:

- Only test systems you own or have written permission to test
- Respect robots.txt and terms of service
- Report findings responsibly
- Follow responsible disclosure practices

This software is provided as-is. The authors aren't responsible for how you use it.

---

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

Try to follow PEP 8, add tests for new features, and update the docs if needed. Meaningful commit messages go a long way.

---

## License

MIT License — Copyright (c) 2026 Endpoint Scraper Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Roadmap

### v5.1 (Current)
- Modular architecture refactor
- Better error handling
- Improved docs

### v6.0 (Next)
- Docker support
- Proxy rotation
- Web dashboard for real-time monitoring
- Plugin system
- Performance metrics

### Further Down the Road
- ML-based vulnerability detection
- Cloud function support (AWS Lambda, GCP)
- REST API for external integrations
- Custom rules engine

---
---

<div align="center">

Built for security researchers, bug bounty hunters, and anyone doing defensive work.

*Use it responsibly.*

</div>