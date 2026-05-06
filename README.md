# Endpoint Scraper

An advanced, multi-threaded web scraper designed to discover API endpoints, routes, and potential security vulnerabilities. Perfect for security researchers, bug bounty hunters, and penetration testers.

## Features

 **Smart Endpoint Discovery**
- Crawls entire website or analyzes single page
- Extracts URLs from DOM, JavaScript, and network requests
- Discovers hardcoded API routes from minified JS files
- Identifies exposed tokens and API keys

 **Advanced Detection**
- CAPTCHA detection and handling
- Subdomain discovery
- Query parameter extraction
- Dynamic URL pattern detection
- Robots.txt and sitemap parsing

 **Anti-Detection**
- Browser fingerprint spoofing
- Human-like mouse movements
- Random scroll speeds and patterns
- Cookie persistence
- Random User-Agent rotation

 **Output Formats**
- CSV export for spreadsheet analysis
- JSON export for programmatic use
- Categorized endpoint listing
- Network call logging

## Installation

### Requirements
- Python 3.8+
- pip or uv

### Setup

Clone and install:
```bash
git clone https://github.com/Zejestry/endpoint-scraper.git
cd endpoint-scraper
pip install -r requirements.txt
playwright install  # Install browser binaries
```

Or install from PyPI (when available):
```bash
pip install endpoint-scraper
playwright install
```

## Usage

### As a Module

```bash
python -m endpoint_scraper
```

Or run the scraper directly:
```bash
cd src
python -m endpoint_scraper
```

### Interactive Mode

The scraper will prompt you for:
1. **Target URL** - Website to scrape
2. **Mode** - Choose between:
   - Mode 1: Full website crawl
   - Mode 2: Single page analysis

### Example

```
Paste the URL to scrape: example.com

Select scrape mode:
  [1] Whole website (crawl entire domain)
  [2] Single page only (links on this URL)

Enter 1 or 2: 1
```

## Output

Results are saved in the `output/` directory:

- **endpoints.csv** - Categorized endpoints in spreadsheet format
- **endpoints.json** - Structured data for programmatic access

### Categories

- **api** - API endpoints and endpoints
- **user** - User profile and account pages
- **search** - Search and filtering pages
- **auth** - Authentication endpoints
- **admin** - Administrative panels
- **content** - File/content hosting pages
- **page** - Regular pages
- **api-network** - Intercepted network API calls
- **js-route** - Hardcoded routes found in JavaScript
- **exposed-secret** - Potential tokens and API keys
- **query-param** - Query parameters discovered
- **url-pattern** - Dynamic URL patterns
- **subdomain** - Discovered subdomains
- **external** - External links
- **robots-disallowed** - Disallowed paths from robots.txt

## Configuration

Edit `src/endpoint_scraper/config.py` to customize:

```python
MAX_PAGES = 200              # Maximum pages to crawl (0 = unlimited)
CONCURRENT_PAGES = 5        # Parallel page requests
MAX_RETRIES = 3             # Retry failed pages
CAPTCHA_KEYWORDS = [...]    # CAPTCHA detection keywords
USER_AGENTS = [...]         # User agent rotation list
```

## Architecture

```
endpoint-scraper/
├── src/endpoint_scraper/
│   ├── __init__.py         # Package init
│   ├── __main__.py         # Entry point
│   ├── config.py           # Configuration & constants
│   ├── session.py          # Cookie management
│   ├── extractors.py       # URL extraction & parsing
│   ├── crawler.py          # Web crawling logic
│   ├── reporters.py        # Output formatting
│   └── utils.py            # Utility functions
├── output/                 # Results directory
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata
├── README.md              # This file
├── .gitignore             # Git ignore rules
└── LICENSE                # MIT License
```

## Disclaimer

⚠️ **Legal Notice**: This tool is designed for authorized security testing only. Unauthorized access to computer systems is illegal. Always obtain proper permission before using this tool on any website you do not own or have explicit written permission to test.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation

## Roadmap

- [ ] GUI interface
- [ ] Proxy support
- [ ] Custom header injection
- [ ] Request scheduling
- [ ] Advanced filtering
- [ ] Integration with security tools

---

**Made with ❤️ for security researchers and bug bounty hunters**
