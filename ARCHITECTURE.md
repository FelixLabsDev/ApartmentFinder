# ApartmentFinder — Architecture Document

> **Version**: 2.6 | **Last Updated**: 2026-03-08

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-26 | Initial build: Yad2 scraper, SQLite DB, CLI, pipeline (normalize/dedup/filter), React UI, Telegram notifications. 170 tests. |
| 2.0 | 2026-03-02 | Facebook Marketplace integration (GraphQL + Playwright), split scraping UI, persistent browser profile, pipeline post-filter fix for cross-source city names. |
| 2.1 | 2026-03-06 | UI polish: "NEW" badge moved from card header row to image overlay (top-right, absolute positioned). `ListingCard` extracted to `frontend/src/components/ListingCard.tsx`. |
| 2.2 | 2026-03-06 | Facebook Playwright detail page enrichment: `_enrich_from_detail_page()` visits each listing's detail page to extract full images and description before parsing. |
| 2.3 | 2026-03-07 | UI: "Open on Google Maps" buttons added to `MapPreviewSidebar` and `ListingDetailModal`. `ListingCard` "View Listing" changed from external `<a>` link to `onOpenDetail` button. |
| 2.4 | 2026-03-07 | AI field extraction: new `POST /api/listings/{source}/{source_id}/ai-extract` endpoint; "AI Extract Fields" button in `ListingDetailModal` for Facebook listings. |
| 2.5 | 2026-03-07 | Automatic AI enrichment in scrape pipeline: `_ai_enrich_facebook()` step added between normalize and deduplicate in `ScrapePipeline`. All Facebook listings with descriptions are now enriched automatically on every scrape. |
| 2.6 | 2026-03-08 | Madlan.co.il scraper: new `MadlanPlaywrightScraper` + `MadlanParser`; network interception with DOM fallback; `MADLAN` added to `Source` enum; 25 new tests (194 total). |

---

## System Overview

ApartmentFinder aggregates apartment rental listings from **Yad2** (Israel's largest classifieds site), **Facebook Marketplace**, and **Madlan.co.il**, normalizes them into a unified format, deduplicates across sources, and stores them in a local SQLite database. Users interact via a React dashboard or CLI. Telegram notifications alert on new matches. None of these platforms have an official API — all data access is reverse-engineered.

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                        ApartmentFinder                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌───────────┐  ┌──────────────────────┐  ┌─────────────────┐ │
│  │  Yad2     │  │  Facebook Marketplace │  │  Madlan.co.il   │ │
│  │  API      │  │  ┌────────────────┐  │  │  ┌───────────┐  │ │
│  │  Scraper  │  │  │ GraphQL (auth) │  │  │  │ Playwright │  │ │
│  │           │  │  │     ↓ fallback │  │  │  │ (intercept │  │ │
│  │           │  │  │ Playwright     │  │  │  │  XHR +     │  │ │
│  │           │  │  │ (persistent    │  │  │  │  DOM       │  │ │
│  │           │  │  │  browser)      │  │  │  │  fallback) │  │ │
│  └─────┬─────┘  └────────┬─────────┘  │  └──────┬────────┘  │ │
│        │                  │               │       │           │ │
│        ▼                  ▼               │       ▼           │ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   ScraperOrchestrator                     │ │
│  │      (fallback chain per source: try → skip)             │ │
│  └──────────────────────┬───────────────────────────────────┘ │
│                          │                                     │
│                          ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    ScrapePipeline                         │ │
│  │  1. Normalize (Hebrew cities, USD→ILS, phones)           │ │
│  │  2. AI Enrich (Facebook listings w/ description)         │ │
│  │  3. Deduplicate (SHA256 fingerprint)                     │ │
│  │  4. Filter (post_filter — no city constraint)            │ │
│  └──────────────────────┬───────────────────────────────────┘ │
│                          │                                     │
│                          ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │             Database (SQLite + SQLAlchemy)                │ │
│  │      listings | search_profiles | scrape_runs            │ │
│  └──────────────────────┬───────────────────────────────────┘ │
│                          │                                     │
│          ┌───────────────┼───────────────┐                    │
│          ▼               ▼               ▼                    │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────┐              │
│  │  Typer CLI   │ │ React UI │ │  Telegram    │              │
│  │              │ │ + FastAPI│ │  Notifier    │              │
│  └──────────────┘ └──────────┘ └──────────────┘              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

A scrape cycle goes through these steps:

```
1. User triggers scrape (React UI button or CLI command)
2. API creates SearchFilter with city + price + rooms
3. ScraperOrchestrator dispatches to registered scrapers with fallback chains
4. Scraper fetches data:
   - Yad2: REST API → Yad2Parser → list[ListingCreate]
   - Facebook: GraphQL (if cookies) → Playwright fallback → _extract_listing_cards() → _enrich_from_detail_page() → FacebookParser → list[ListingCreate]
   - Madlan: Playwright → intercept XHR/API responses → MadlanParser.parse_api_listing() per result; falls back to _extract_listing_cards() (DOM) → MadlanParser.parse_dom_listing() if interception yields nothing
5. ListingNormalizer: Hebrew city → English slug, USD → ILS, phone → +972 format
6. AI Enrichment: for each Facebook listing with a description > 30 chars, calls extract_listing_fields() to fill missing structured fields (price, rooms, city, features, etc.) — additive only, never overwrites existing values
7. ListingDeduplicator: SHA256 fingerprint on city|street|rooms|floor|price_bucket (runs after AI enrichment so AI-filled fields improve fingerprint accuracy)
8. FilterEngine: applies post_filter (price/rooms only — no city, to avoid name mismatches)
9. ListingRepository: upserts to SQLite (INSERT ON CONFLICT UPDATE)
10. React UI fetches /api/listings with display filters → renders listing cards
```

---

## Component Reference

### Scrapers

| Component | File | Description |
|-----------|------|-------------|
| `BaseScraper` | `src/scrapers/base.py` | Abstract class: `scrape(SearchFilter) → list[ListingCreate]`, `health_check() → bool` |
| `ScraperHttpClient` | `src/scrapers/http_client.py` | Shared HTTP client with randomized User-Agent, exponential retry, anti-bot headers, optional proxy |
| `ScraperOrchestrator` | `src/scrapers/orchestrator.py` | Registers scrapers per source with fallback chains; `scrape_all()` tries each in order |
| `Yad2ApiScraper` | `src/scrapers/yad2/scraper.py` | Hits Yad2's internal JSON API; paginated; supports city, price, rooms filters |
| `Yad2Parser` | `src/scrapers/yad2/parser.py` | Parses Yad2 JSON response (94 fields per listing) into `ListingCreate` |
| `FacebookGraphQLScraper` | `src/scrapers/facebook/scraper.py` | POST to `/api/graphql/` with doc_id rotation; needs cookies + LSD token |
| `FacebookPlaywrightScraper` | `src/scrapers/facebook/scraper.py` | Browser automation with persistent profile at `data/fb_profile/`; sync API via `asyncio.to_thread()`. After extracting search-result cards, calls `_enrich_from_detail_page()` per card to visit the listing detail page and replace the preview thumbnail + title stub with full images (naturalWidth >= 150 filter) and the longest description block (> 50 chars). Rate-limited to 1.5s between detail page loads. |
| `FacebookParser` | `src/scrapers/facebook/parser.py` | Parses GraphQL responses and HTML card data into `ListingCreate` |
| `MadlanPlaywrightScraper` | `src/scrapers/madlan/scraper.py` | Browser automation with persistent profile at `data/madlan_profile/`; sync API via `asyncio.to_thread()`. Registers a `response` listener to intercept XHR/API calls and capture structured listing JSON. Falls back to `_extract_listing_cards()` (DOM parsing) if interception yields nothing. Scrolls 6 times with 2.5 s pauses to trigger lazy-loading. Source-level deduplication by `source_id` before returning. |
| `MadlanParser` | `src/scrapers/madlan/parser.py` | Dual-mode parser: `parse_api_listing()` for structured JSON (handles multiple field-name variants); `parse_dom_listing()` for card dicts from DOM extraction. Maps Hebrew property type names to `PropertyType` enum. |

**Yad2 API-level filters**: city, min_price, max_price, min_rooms, max_rooms
**Facebook API-level filters**: city (via location ID), min_price, max_price
**Madlan API-level filters**: city (Hebrew term + bounding box), min_price, max_price, min_rooms, max_rooms, min_area_sqm, max_area_sqm, min_floor, max_floor

### Pipeline

| Component | File | Description |
|-----------|------|-------------|
| `ListingNormalizer` | `src/pipeline/normalizer.py` | 60+ Hebrew→English city mappings, USD→ILS at 3.7 rate, phone normalization to +972 format |
| `ListingDeduplicator` | `src/pipeline/deduplicator.py` | SHA256 fingerprint on `city\|street\|house_number\|rooms\|floor\|price_bucket` (200 ILS tolerance). Keeps listing with highest completeness score. |
| `FilterEngine` | `src/pipeline/filter_engine.py` | Static `apply()` method: filters by price, rooms, area, floor, property type, features, keywords |
| `ScrapePipeline` | `src/pipeline/pipeline.py` | Orchestrates scrape → normalize → AI enrich → deduplicate → filter. Accepts `post_filter` to separate scraper filters from pipeline filters. `_ai_enrich_facebook()` static async method runs `extract_listing_fields()` on each Facebook listing with a description longer than 30 characters; fills only null/missing fields; sets `ai_guessed_fields`; per-listing failures are caught and logged without aborting the pipeline. |

### Database

| Component | File | Description |
|-----------|------|-------------|
| `engine.py` | `src/db/engine.py` | SQLAlchemy async engine factory (aiosqlite for SQLite) |
| `tables.py` | `src/db/tables.py` | ORM models: `ListingRow` (40+ columns, 4 indexes), `SearchProfileRow`, `ScrapeRunRow` |
| `repository.py` | `src/db/repository.py` | `ListingRepository` (upsert, query with filters), `SearchProfileRepository`, `ScrapeRunRepository` |

**Tables**: `listings` (unique on source+source_id, fingerprint index), `search_profiles`, `scrape_runs`
**Migrations**: Alembic (`alembic/versions/0c933bf8a865_initial.py`)

### API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/listings` | GET | Filtered listings from DB (city, price, rooms, area, features, pagination) |
| `/api/scrape` | POST | Trigger on-demand scrape (source, city, price, rooms, headless) |
| `/api/stats` | GET | Summary: total listings, sources, cities |
| `/api/health` | GET | Source connectivity check |
| `/api/listings/{source}/{source_id}/ai-extract` | POST | Rescrape a Facebook listing via Playwright, run AI field extraction, update and return the listing. Only meaningful for Facebook source. |

**File**: `src/ui/api.py` — FastAPI with CORS for React dev server (port 5173)

The `/api/scrape` endpoint creates two filters:
- `search_filter` (with city) → passed to scrapers for API-level location lookup
- `pipeline_filter` (without city) → used by FilterEngine to avoid Hebrew↔English name mismatches

### Frontend

**Stack**: React 18, TypeScript, Vite, TanStack React Query, Axios

| Component | File | Description |
|-----------|------|-------------|
| `ScrapeTabSwitcher` | `frontend/src/App.tsx` | Tab switcher between Yad2 and Facebook scrape panels |
| `ScrapeYad2Section` | `frontend/src/App.tsx` | City, price range, rooms range, "Scrape Yad2" button |
| `ScrapeFacebookSection` | `frontend/src/App.tsx` | City, price range, browser toggle, "Scrape Facebook" button |
| `DisplayFilters` | `frontend/src/App.tsx` | City, price, rooms, area, feature checkboxes — controls DB query |
| `ListingCard` | `frontend/src/components/ListingCard.tsx` | Price, location, features, description, source badge. Contains `ImageCarousel` wrapped in `.card-image-wrapper`; "NEW" badge is absolutely positioned over the image (top-right corner, z-index 2). "View Listing" is a `<button>` that calls `onOpenDetail` to open the in-app detail modal (not a direct external link). |
| `ListingDetailModal` | `frontend/src/components/ListingDetailModal.tsx` | Full listing detail overlay. Contact section has a "View on {source}" external link and, when lat/lng are present, an "Open on Google Maps" button linking to `https://www.google.com/maps?q={lat},{lng}`. For Facebook listings, also shows an "AI Extract Fields" button (purple) that calls `POST /api/listings/{source}/{source_id}/ai-extract`, shows loading/error state inline, and invokes `onListingUpdated` prop on success. |
| `MapView` | `frontend/src/components/MapView.tsx` | Map view of listings. `MapPreviewSidebar` shows a selected listing's details with a "View Details" button and, when lat/lng are present, an "Open on Google Maps" button. |
| `StatsBar` | `frontend/src/App.tsx` | Total listings, sources, cities |
| `api.ts` | `frontend/src/api.ts` | Axios client: `fetchListings`, `triggerScrape`, `fetchStats`, `fetchHealth`, `aiExtractListing` (120s timeout) |

### Notifications

| Component | File | Description |
|-----------|------|-------------|
| `TelegramFormatter` | `src/notifications/formatter.py` | HTML-formatted listing messages for Telegram |
| `TelegramNotifier` | `src/notifications/telegram_bot.py` | Sends messages in batches of 3, 1 msg/sec rate limit |

### Scheduler

| Component | File | Description |
|-----------|------|-------------|
| `jobs.py` | `src/scheduler/jobs.py` | `scrape_job()` runs pipeline + DB storage + notifications per search profile |
| `runner.py` | `src/scheduler/runner.py` | APScheduler `AsyncIOScheduler` setup with configurable intervals |

---

## Key Design Decisions

### Persistent Browser Profile (v2.0)
**Problem**: Facebook requires login. Managing cookies manually (extract from browser, pass to GraphQL) was fragile and broke frequently.
**Solution**: `pw.chromium.launch_persistent_context(user_data_dir="data/fb_profile/")` saves the full browser session to disk. First run opens a visible browser for the user to log in; subsequent runs reuse the session headless.

### Sync Playwright in Thread (v2.0)
**Problem**: Windows Python uses `SelectorEventLoop` by default, which doesn't support `asyncio.create_subprocess_exec()`. Playwright's async API uses subprocesses internally and fails on Windows.
**Solution**: Use Playwright's **sync** API and run the entire scrape in a worker thread via `asyncio.to_thread(self._scrape_sync, search_filter)`.

### Separate post_filter (v2.0)
**Problem**: Yad2 uses English city slugs ("herzliya") for API lookups. Facebook returns Hebrew city names ("הרצליה, M"). The pipeline's `FilterEngine` compared listing cities against filter cities — all Facebook listings were silently filtered out.
**Solution**: `ScrapePipeline.run()` accepts a separate `post_filter` parameter. The API endpoint passes `search_filter` (with city) to scrapers and `pipeline_filter` (without city) to the filter engine.

### Facebook Playwright Detail Page Enrichment (v2.2)
**Problem**: Search result cards on Facebook Marketplace only expose a single preview thumbnail and the listing title — the description field was being populated with the title as a placeholder, and multi-image listings showed only one low-resolution image.
**Solution**: After `_extract_listing_cards()` builds the initial card list, `_enrich_from_detail_page()` navigates to each listing's `/marketplace/item/{id}/` page before parsing. Images are collected from `img[src*="scontent"], img[src*="fbcdn"]` and filtered to `naturalWidth >= 150` to exclude UI icons. The description is extracted by trying three CSS selectors in order and keeping the longest text block over 50 characters. The method mutates `card_data` in place; if the detail fetch fails, the card falls through to parsing with its original preview data.

### domcontentloaded vs networkidle (v2.0)
**Problem**: `page.goto(url, wait_until="networkidle")` timed out on Facebook because tracking pixels, WebSockets, and analytics requests never stop.
**Solution**: Use `wait_until="domcontentloaded"` + `page.wait_for_timeout(5000)` for consistent loading.

### Madlan Network Interception Strategy (v2.6)
**Problem**: Madlan.co.il returns HTTP 403 to all direct HTTP clients. No public API exists and there is no GraphQL endpoint to reverse-engineer.
**Solution**: Use Playwright to load the search page as a real browser. A `response` listener captures all JSON responses from URLs matching `/api/`, `/graphql`, or `listings`. A recursive `_extract_listings_from_api()` traversal plus a heuristic `_is_listing_object()` check identify listing dicts regardless of nesting depth or GraphQL edge patterns. If no API data is captured (e.g., due to a site update), the scraper falls back to DOM extraction of rendered listing cards.

### Madlan URL Filter Encoding (v2.6)
**Problem**: Madlan does not accept individual query parameters for price, rooms, area, and floor. All filter state is encoded in a single opaque `filters` parameter.
**Solution**: Discovered by browser observation that Madlan uses a positional underscore-delimited string: `_{price_min}-{price_max}_{rooms_min}-{rooms_max}_{7 empty}_{area_min}-{area_max}_{empty}_{floor_min}-{floor_max}_{7 empty}_search-filter-top-bar`. `_build_filter_string()` constructs this format from `SearchFilter` fields.

### Yad2 Internal JSON API (v1.0)
**Problem**: All known Yad2 scrapers use `__NEXT_DATA__` parsing or Selenium, both of which trigger Yad2's anti-bot protection.
**Solution**: Discovered an unprotected internal API at `https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/rent` that returns structured JSON with 94 fields per listing, no anti-bot, and native filter support.

### Individual Boolean Columns for Features (v1.0)
Storing `has_parking`, `has_elevator`, `has_balcony`, etc. as individual columns (not a JSON blob) enables efficient SQL WHERE clauses for feature filtering.

---

## Configuration

### Environment Variables (`.env`)

```env
# Database
DATABASE_PATH=data/apartmentfinder.db

# Facebook (optional — for GraphQL scraper)
FB_COOKIES=                 # JSON string of cookie dict
FB_LSD_TOKEN=               # LSD token from Facebook page

# Telegram notifications
TELEGRAM_BOT_TOKEN=         # From @BotFather
TELEGRAM_CHAT_ID=           # Your chat/group ID

# Scheduler
SCRAPE_INTERVAL_MINUTES=30  # How often to scrape

# Optional proxy
PROXY_URL=                  # HTTP/SOCKS proxy for scraping
```

### Facebook Auth Setup

1. In the React UI, switch to the **Facebook** tab
2. Check **"Open browser for login"**
3. Click **"Scrape Facebook"** — Chrome opens
4. Log in to Facebook — scraping starts automatically
5. Session saved to `data/fb_profile/` for future headless runs

---

## Testing

**194 tests total** (193 unit + 1 integration) across 14 test files.

| Test File | Count | Coverage |
|-----------|-------|----------|
| `test_models.py` | 12 | Pydantic model validation |
| `test_db_repository.py` | 9 | Database CRUD, filters, features |
| `test_yad2_parser.py` | 17 | Yad2 API response parsing |
| `test_yad2_scraper.py` | 6 | Yad2 scraper (5 unit + 1 integration) |
| `test_fb_parser.py` | 38 | Facebook GraphQL response parsing |
| `test_fb_scraper.py` | 10 | Facebook scraper, fallback behavior |
| `test_madlan_parser.py` | 14 | Madlan API + DOM listing parsing |
| `test_madlan_scraper.py` | 12 | Madlan scraper (11 unit + 1 integration) |
| `test_normalizer.py` | 19 | Hebrew city mapping, price/phone normalization |
| `test_deduplicator.py` | 12 | SHA256 fingerprint, cross-source dedup |
| `test_filter_engine.py` | 21 | All filter criteria (composable) |
| `test_pipeline.py` | 9 | End-to-end pipeline + orchestrator |
| `test_telegram_formatter.py` | 17 | Telegram message formatting |

**Test architecture**:
- All unit tests use mocked HTTP (pytest-httpx) — no network calls
- In-memory SQLite per test — no file I/O
- Fixture-based: real API responses captured as JSON files
- Integration tests marked with `@pytest.mark.integration`, excluded by default

```bash
# Unit tests only
uv run pytest tests/ -m "not integration" -v

# All tests including integration
uv run pytest tests/ -v
```
