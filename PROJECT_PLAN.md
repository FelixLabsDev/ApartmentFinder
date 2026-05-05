# ApartmentFinder - Project Plan

> **Status**: All phases implemented as of 2026-03-02.
> See [ARCHITECTURE.md](ARCHITECTURE.md) for the current system architecture.
> See [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) for the full implementation history (Steps 1–26).

## What Was Actually Built

| Planned | Implemented | Notes |
|---------|-------------|-------|
| Yad2 scraper via `__NEXT_DATA__` | Yad2 scraper via **internal JSON API** | Discovered unprotected API endpoint — no HTML parsing needed |
| Facebook via Apify (paid) | Facebook via **GraphQL + Playwright** | Free, direct scraping with persistent browser profile |
| Apify fallback | Skipped | Direct scraping works reliably for both sources |
| Streamlit frontend | **React + TypeScript + Vite** | Per user request; split source-specific scraping UI |
| Email notifications | Skipped | Telegram only (sufficient for personal use) |
| Scoring/ranking system | Skipped | Deduplication with completeness scoring used instead |
| `requirements.txt` / `pip` | **`uv` + `pyproject.toml`** | Modern dependency management |

## Overview

A tool that aggregates apartment rental listings from **Yad2** and **Facebook Marketplace**, applies user-defined filters, and presents results in a unified interface. The project uses a combination of API calls, traditional scraping, and browser automation depending on the platform.

---

## Research Summary

### Yad2 (yad2.co.il)

**No official public API exists.** All data access is unofficial.

#### Data Access Methods (ranked by reliability)

| Method | How It Works | Pros | Cons |
|--------|-------------|------|------|
| **Apify Actor** (`amit123/yadscraper`) | Hosted scraper on Apify platform, callable via REST API | Turnkey, maintained, structured output | $6.99/1K results, third-party dependency |
| **`__NEXT_DATA__` parsing** | Yad2's Next.js frontend embeds full JSON payload in HTML `<script id="__NEXT_DATA__">` tag | Free, returns structured JSON, no JS rendering needed | Breaks if Yad2 changes frontend structure |
| **Internal feed URLs** | `https://www.yad2.co.il/realestate/rent?city=...&rooms=...&price=...` with query params | Free, supports filters natively | Returns HTML, needs parsing |
| **Legacy mobile API** | `http://m.yad2.co.il/API/MadorResults.php` with params | Direct JSON API | Old, may be deprecated, limited docs |
| **Browser automation** | Selenium/Playwright rendering full pages | Most resilient to changes | Slowest, most resource-heavy |

#### Yad2 Anti-Bot Measures
- Custom CAPTCHA page ("Are you for real" challenge)
- IP-based rate limiting
- User-Agent validation (requires full browser headers)
- Cookie-based tracking / JS execution checks

#### Yad2 Mitigation Strategies
- Randomize User-Agent per request (`fake_useragent` library)
- Use residential/rotating proxy pool
- Add random delays (3-10s between requests)
- Full browser-like headers (Accept, Accept-Encoding, Sec-Fetch-* headers)
- Implement retry logic with anti-bot detection

#### Yad2 Listing Data Fields
```
token, price, address (topArea, area, city, street, neighborhood),
rooms, floor, squareMeters, propertyType, parking, elevator,
balcony, airConditioning, entryDate, description, images[],
customer (name, phone), dates (createdAt, updatedAt)
```

#### Existing Yad2 Projects/Libraries

| Project | Language | Approach |
|---------|----------|----------|
| [DavOstx7/yad2-scraper](https://github.com/DavOstx7/yad2-scraper) | Python (`pip install yad2-scraper`) | `__NEXT_DATA__` parsing, most mature |
| [NivEz/yad2-scraper](https://github.com/NivEz/yad2-scraper) | Node.js | Cheerio + GitHub Actions + Telegram |
| [Matanga1-2/yad2-apartment-scraper](https://github.com/Matanga1-2/yad2-apartment-scraper) | Python | Selenium + Gmail notifications |
| [MaorBezalel/real-estate-smart-agent](https://github.com/MaorBezalel/real-estate-smart-agent) | Python | Full-stack app |
| [Apify amit123/yadscraper](https://apify.com/amit123/yadscraper) | Hosted | $6.99/1K, API-callable, 5.0 rating |

---

### Facebook Marketplace

**No official public API for reading/searching listings.** The Commerce API only lets *sellers* push listings.

#### Data Access Methods (ranked by reliability)

| Method | How It Works | Pros | Cons |
|--------|-------------|------|------|
| **Apify Actor** (`apify/facebook-marketplace-scraper`) | Hosted scraper, supports `propertyrentals` category | Turnkey, $5/1K results, free tier | Third-party dependency |
| **GraphQL API (reverse-engineered)** | `POST https://www.facebook.com/api/graphql/` with `doc_id` + `variables` | Free, structured JSON response | `doc_id` values rotate, may need auth cookies |
| **Playwright/Puppeteer scraping** | Full browser automation on Marketplace pages | Most resilient | Slowest, login walls, bot detection |
| **Facebook Groups scraping** | `facebook-scraper` Python package for rental groups | Complements Marketplace data | Unstructured post text, needs NLP |
| **Bright Data** | Enterprise scraping service with built-in proxy rotation | Most reliable, legally proven | Expensive ($250+/100K records) |

#### Facebook Marketplace URL Structure for Rentals
```
https://www.facebook.com/marketplace/{location_id}/propertyrentals/
```

#### Facebook GraphQL API Example
```javascript
const variables = {
  params: {
    bqf: { callsite: 'COMMERCE_MKTPLACE_WWW', query: 'apartment' },
    browse_request_params: {
      filter_location_id: '108043585884666',  // Facebook Place ID
      filter_price_lower_bound: 0,
      filter_price_upper_bound: 214748364700,
    },
    custom_request_params: {
      surface: 'SEARCH',
      search_vertical: 'C2C',
    },
  },
};

const res = await fetch('https://www.facebook.com/api/graphql/', {
  headers: { 'content-type': 'application/x-www-form-urlencoded' },
  body: `variables=${JSON.stringify(variables)}&doc_id=2022753507811174`,
  method: 'POST',
});
// Listings at: data.marketplace_search.feed_units.edges[].node.listing
```

#### Facebook Anti-Scraping Measures
- Login walls after a few page views
- Aggressive rate limiting + IP blocking (datacenter IPs blocked)
- Bot detection via behavioral analysis + browser fingerprinting
- Obfuscated/dynamic CSS class names
- GraphQL `doc_id` rotation
- Account suspension for bot-like behavior

#### Facebook Mitigation Strategies
- `puppeteer-extra-plugin-stealth` or `playwright-stealth`
- Residential proxy rotation (Bright Data, SmartProxy, Oxylabs)
- 3-7 second random delays between requests
- Session/cookie management across requests
- Headful (visible) browser mode instead of headless
- `undetected-chromedriver` / `nodriver` for latest evasion

#### Facebook Listing Data Fields
```
id, marketplace_listing_title, listing_price, currency,
location (city, latitude, longitude), primary_listing_photo,
listing_photos[], seller (name, type, location),
description, condition, saleIsPending, is_live, is_sold,
creation_time, category_type
```

#### Existing Facebook Marketplace Projects

| Project | Language | Approach |
|---------|----------|----------|
| [passivebot/facebook-marketplace-scraper](https://github.com/passivebot/facebook-marketplace-scraper) | Python | Playwright + BeautifulSoup + Streamlit GUI |
| [kyleronayne/marketplace-api](https://github.com/kyleronayne/marketplace-api) | Python | GraphQL API wrapper |
| [sumentse/facebook-rental-scraper](https://github.com/sumentse/facebook-rental-scraper) | Node.js | Built specifically for rentals |
| [Apify fb-marketplace-scraper](https://apify.com/apify/facebook-marketplace-scraper) | Hosted | $5/1K, `propertyrentals` category |

---

### Legal Considerations

| Scenario | Risk Level |
|----------|-----------|
| Scraping **public** data while **logged out** | Low (supported by *Meta v. Bright Data* ruling, Jan 2024) |
| Scraping while **logged in** | Medium (potential ToS breach) |
| Scraping after receiving a **cease-and-desist** | High (CFAA violation) |
| Scraping for **personal use** | Lowest risk |
| Collecting/selling **personal data** (PII) | High (GDPR, privacy laws) |

**Key precedent**: In *Meta Platforms v. Bright Data (2024)*, the court ruled that scraping publicly accessible data while logged out does not violate Facebook/Instagram's Terms of Service. Meta dropped the case entirely.

---

## Architecture

### Tech Stack (Recommended)

```
Language:       Python 3.11+
Framework:      FastAPI (API backend) or CLI-first
Database:       SQLite (local) → PostgreSQL (if scaling)
Scraping:       httpx + BeautifulSoup (traditional)
                Playwright (browser automation)
                Apify SDK (managed scraping)
Scheduling:     APScheduler or cron
Notifications:  Telegram Bot API / Email (SMTP)
Frontend:       Streamlit (quick MVP) or React (later)
```

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   ApartmentFinder                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────────┐   ┌──────────────┐   ┌───────────┐  │
│  │  Yad2     │   │   Facebook   │   │  Future   │  │
│  │  Scraper  │   │  Marketplace │   │  Sources  │  │
│  │  Module   │   │   Module     │   │  Module   │  │
│  └─────┬─────┘   └──────┬───────┘   └─────┬─────┘  │
│        │                │                  │        │
│        ▼                ▼                  ▼        │
│  ┌──────────────────────────────────────────────┐   │
│  │          Unified Data Pipeline               │   │
│  │  (normalize, deduplicate, filter, score)     │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                               │
│                     ▼                               │
│  ┌──────────────────────────────────────────────┐   │
│  │              Database (SQLite)                │   │
│  │  listings, search_history, notifications     │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                               │
│        ┌────────────┼────────────┐                  │
│        ▼            ▼            ▼                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐        │
│  │   CLI    │ │   Web    │ │ Notification │        │
│  │ Interface│ │   UI     │ │   Service    │        │
│  └──────────┘ └──────────┘ └──────────────┘        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Directory Structure

```
ApartmentFinder/
├── src/
│   ├── scrapers/
│   │   ├── base.py              # Abstract base scraper class
│   │   ├── yad2/
│   │   │   ├── __init__.py
│   │   │   ├── scraper.py       # Yad2 scraper (NextData + fallbacks)
│   │   │   ├── parser.py        # Parse Yad2 response format
│   │   │   └── config.py        # Yad2 URLs, headers, selectors
│   │   ├── facebook/
│   │   │   ├── __init__.py
│   │   │   ├── scraper.py       # FB Marketplace scraper (GraphQL + browser)
│   │   │   ├── parser.py        # Parse FB response format
│   │   │   └── config.py        # FB URLs, doc_ids, location IDs
│   │   └── apify/
│   │       ├── __init__.py
│   │       └── client.py        # Apify API wrapper (for both Yad2 + FB)
│   ├── models/
│   │   ├── listing.py           # Unified Listing dataclass
│   │   └── filters.py           # Filter/search criteria models
│   ├── pipeline/
│   │   ├── normalizer.py        # Normalize data from different sources
│   │   ├── deduplicator.py      # Detect duplicate listings across sources
│   │   └── scorer.py            # Score/rank listings by user preferences
│   ├── storage/
│   │   ├── database.py          # SQLite database operations
│   │   └── migrations.py        # Schema migrations
│   ├── notifications/
│   │   ├── telegram.py          # Telegram bot notifications
│   │   └── email.py             # Email notifications (SMTP)
│   ├── scheduler/
│   │   └── jobs.py              # Scheduled scraping jobs
│   ├── api/
│   │   └── routes.py            # FastAPI endpoints (optional)
│   └── config.py                # Global config, env vars
├── tests/
│   ├── test_yad2_scraper.py
│   ├── test_fb_scraper.py
│   └── test_pipeline.py
├── .env                         # API keys, tokens (git-ignored)
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Implementation Plan

> All phases below were completed. Checkboxes reflect final status.

### Phase 1: Foundation ✅

**Goal:** Project setup, unified data model, database, and one working scraper.

- [x] **1.1** Initialize project structure, virtual environment, `pyproject.toml`
- [x] **1.2** Define the unified `Listing` data model
  ```python
  @dataclass
  class Listing:
      id: str                    # Internal UUID
      source: str                # "yad2" | "facebook"
      source_id: str             # Original listing ID from platform
      source_url: str            # Direct link to listing
      title: str
      price: float
      currency: str              # "ILS" | "USD"
      city: str
      neighborhood: str | None
      street: str | None
      rooms: float | None
      floor: int | None
      area_sqm: float | None
      description: str | None
      images: list[str]
      property_type: str | None  # apartment, house, penthouse, etc.
      features: dict             # parking, elevator, balcony, AC, etc.
      contact_name: str | None
      contact_phone: str | None
      entry_date: date | None
      posted_at: datetime | None
      scraped_at: datetime
      raw_data: dict             # Full original response for debugging
  ```
- [x] **1.3** Define `SearchFilters` model
  ```python
  @dataclass
  class SearchFilters:
      cities: list[str]
      min_price: float | None
      max_price: float | None
      min_rooms: float | None
      max_rooms: float | None
      min_area_sqm: float | None
      max_area_sqm: float | None
      property_types: list[str] | None
      features: dict | None       # {"parking": True, "elevator": True}
      keywords: list[str] | None  # Free-text search terms
  ```
- [x] **1.4** Set up SQLite database with schema + basic CRUD operations
- [x] **1.5** Create abstract `BaseScraper` class with common interface
- [x] **1.6** Implement Yad2 scraper (used internal JSON API instead of `__NEXT_DATA__`)
  - Fetch rental listings page with proper headers
  - Extract JSON from `<script id="__NEXT_DATA__">`
  - Parse listings from `props.pageProps.dehydratedState.queries`
  - Map to unified `Listing` model
  - Handle anti-bot detection ("Are you for real" page)
  - Add retry logic with backoff

### Phase 2: Facebook Marketplace ✅ (Apify skipped)

**Goal:** Add Facebook Marketplace scraping. Apify skipped — direct scraping works.

- [x] **2.1** Implement Facebook Marketplace scraper
  - **Primary:** GraphQL API approach (`POST /api/graphql/` with `doc_id`)
  - **Fallback:** Playwright browser automation for when GraphQL breaks
  - Map FB listing fields to unified `Listing` model
  - Handle login walls and rate limiting
- [ ] ~~**2.2** Implement Apify client wrapper~~ — Skipped (direct scraping sufficient)
- [x] **2.3** Implement scraper orchestrator
  - Try direct scraping first → fall back to Apify on failure
  - Configurable per-source strategy (direct-only, apify-only, or hybrid)
  - Aggregate results from all active sources

### Phase 3: Data Pipeline + Deduplication ✅

**Goal:** Normalize, deduplicate, filter, and rank listings from multiple sources.

- [x] **3.1** Build normalizer
  - Standardize city/neighborhood names (Hebrew ↔ English)
  - Normalize prices to ILS
  - Standardize property types across platforms
  - Clean and validate phone numbers
- [x] **3.2** Build deduplicator
  - Match listings across Yad2 and Facebook by: address + price + rooms combo
  - Fuzzy matching on description text (Levenshtein / token overlap)
  - Merge duplicates, keep best data from each source
- [x] **3.3** Build filter engine
  - Apply `SearchFilters` against listings in database
  - Support compound queries (city AND price range AND rooms)
- [ ] ~~**3.4** Build scoring/ranking system~~ — Skipped (deduplicator uses completeness scoring instead)

### Phase 4: Scheduling + Notifications ✅ (email skipped)

**Goal:** Automated periodic scraping with alerts for new listings.

- [x] **4.1** Set up APScheduler for periodic scraping runs
  - Configurable interval per source (e.g., Yad2 every 30min, FB every 1hr)
  - Track last-run timestamps to fetch only new listings
- [x] **4.2** Implement Telegram notification bot
  - Send alert when new listing matches saved search filters
  - Include: title, price, rooms, location, link, thumbnail
  - Support multiple saved searches per user
- [ ] ~~**4.3** Implement email notifications~~ — Skipped (Telegram sufficient)

### Phase 5: User Interface ✅ (React instead of Streamlit)

**Goal:** Build a usable frontend for browsing and filtering listings.

- [x] **5.1** ~~Build Streamlit MVP dashboard~~ → Built **React + TypeScript + Vite** frontend instead
  - Filter sidebar with source-specific scrape panels (Yad2 / Facebook tabs)
  - Listing cards with price, location, features, source badges
  - Display filters (city, price, rooms, area, feature checkboxes)
  - Stats bar (total listings, sources, cities)
- [x] **5.2** Build FastAPI REST endpoints (4 endpoints: listings, scrape, stats, health)

---

## Key Decisions to Make

| Decision | Options | Recommendation |
|----------|---------|----------------|
| **Primary Yad2 approach** | `__NEXT_DATA__` parsing vs Apify | Start with `__NEXT_DATA__` (free), Apify as fallback |
| **Primary FB approach** | GraphQL API vs Playwright vs Apify | Start with Apify ($5/1K, most reliable), add GraphQL later |
| **Database** | SQLite vs PostgreSQL | SQLite for MVP (zero setup), migrate if needed |
| **Frontend** | Streamlit vs React vs CLI-only | Streamlit for fast MVP |
| **Notifications** | Telegram vs Email vs Both | Telegram first (real-time, easy API) |
| **Proxy service** | None vs Bright Data vs SmartProxy | None initially, add if getting blocked |
| **Hosting** | Local vs VPS vs Cloud Functions | Local first, VPS for 24/7 scheduling |

---

## Environment Setup

### Required API Keys / Tokens

```env
# .env file
APIFY_API_TOKEN=           # For Apify managed scrapers (optional, paid fallback)
TELEGRAM_BOT_TOKEN=        # For notifications (create via @BotFather)
TELEGRAM_CHAT_ID=          # Your Telegram chat/group ID

# Optional - for proxy rotation if needed
PROXY_HOST=
PROXY_PORT=
PROXY_USERNAME=
PROXY_PASSWORD=
```

### Python Dependencies

```
httpx                  # HTTP client (async support)
beautifulsoup4         # HTML parsing
playwright             # Browser automation (FB fallback)
fake-useragent         # User-Agent randomization
apify-client           # Apify API SDK
sqlalchemy             # Database ORM
alembic                # Database migrations
apscheduler            # Job scheduling
python-telegram-bot    # Telegram notifications
streamlit              # Web UI
pydantic               # Data validation
python-dotenv          # Environment variables
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Yad2 blocks scraping | Rotate User-Agents + headers, add delays, fall back to Apify |
| Facebook login walls | Use Apify as primary for FB, GraphQL as secondary |
| GraphQL `doc_id` changes | Monitor for errors, maintain fallback list of known IDs |
| Rate limiting | Configurable delays, proxy rotation, respect `robots.txt` |
| Data format changes | Loose parsing with fallbacks, alerts on parse failures |
| Anti-bot CAPTCHA | Detect early ("Are you for real"), switch to Apify fallback |
| Legal issues | Only scrape public data while logged out, personal use only |

---

## Getting Started (First Steps)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Install dependencies
pip install httpx beautifulsoup4 fake-useragent pydantic python-dotenv sqlalchemy

# 3. Copy env template
cp .env.example .env

# 4. Run first test scrape (Yad2)
python -m src.scrapers.yad2.scraper --city "tel-aviv" --max-price 5000 --rooms 2-3
```
