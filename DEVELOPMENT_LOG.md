# ApartmentFinder — Development Log & Technical Documentation

> **Last Updated**: 2026-03-08
> **Status**: All phases complete (Steps 1–27). Full system operational with Yad2 + Facebook Marketplace + Madlan.
> **Test suite**: 194 tests (193 unit + 1 integration).

---

## Session 9: Listing Card Highlight Border Width Increase (2026-03-08)

### What Changed

**Motivation**: The 2px highlight borders on status-tagged listing cards (new, liked, disliked) were visually subtle and hard to distinguish at a glance. Increasing to 3px makes the state indicators more prominent without altering the color scheme.

**Files modified**:

| File | Change |
|------|--------|
| `frontend/src/App.css` | Changed `border` width on `.listing-new`, `.listing-liked`, and `.listing-disliked` from `2px` to `3px` |

### Failed Approaches

No failed approaches — a single property value change with no alternatives required.

---

## Session 8: Madlan.co.il Scraper Integration (2026-03-08)

### What Changed

**Motivation**: Madlan.co.il is a major Israeli real estate portal distinct from Yad2, offering a different inventory of rental listings. Adding a third data source improves listing coverage and gives users more options when searching.

**Files added**:

| File | Description |
|------|-------------|
| `src/scrapers/madlan/__init__.py` | Package init; exports `MadlanParser`, `MadlanPlaywrightScraper` |
| `src/scrapers/madlan/config.py` | Base URLs, Hebrew city-to-search-term mapping (28 cities), city bounding boxes (17 cities), Hebrew-to-enum property type map (11 types) |
| `src/scrapers/madlan/parser.py` | `MadlanParser` with `parse_api_listing()` and `parse_dom_listing()` methods |
| `src/scrapers/madlan/scraper.py` | `MadlanPlaywrightScraper`: Playwright browser automation with network interception and DOM fallback |
| `tests/test_madlan_parser.py` | 14 unit tests for `MadlanParser` |
| `tests/test_madlan_scraper.py` | 11 unit tests + 1 integration test for `MadlanPlaywrightScraper` |
| `tests/fixtures/madlan_api_sample.json` | Captured API response fixture used by parser tests |

**Files modified**:

| File | Change |
|------|--------|
| `src/models/enums.py` | Added `MADLAN = "madlan"` to `Source` enum |
| `src/main.py` | Registered `MadlanPlaywrightScraper` in CLI scrape command and health check |
| `src/ui/api.py` | Registered `MadlanPlaywrightScraper` in the `POST /api/scrape` endpoint and `GET /api/health` endpoint |

### Implementation Details

**Why Playwright (not HTTP)**: Madlan.co.il returns HTTP 403 to all direct HTTP clients regardless of User-Agent or header configuration. Playwright's persistent browser context bypasses this. This is the same pattern already established for Facebook (v2.0).

**Network interception strategy**: When the search page loads, `MadlanPlaywrightScraper` registers a `response` listener via `page.on("response", on_response)`. The handler filters for JSON responses from URLs containing `/api/`, `/graphql`, or `listings`, then recursively traverses the response body via `_extract_listings_from_api()`. A heuristic `_is_listing_object()` method identifies dicts that contain an ID field plus at least 2 of: price, rooms, area, address, or coordinates.

**DOM fallback**: If network interception yields zero listings (e.g., the API shape changes), `_extract_listing_cards()` selects all `<a href*="/listings/">` elements from the rendered DOM. Each link's `inner_text()` is split into lines and parsed by regex for price, rooms, area, and floor. The scraper scrolls the page 6 times with 2.5 s pauses to trigger lazy-loading before DOM extraction begins.

**URL filter encoding**: Madlan encodes all filter parameters into a single positional underscore-delimited string in the `filters` query parameter. Format: `_{price_range}_{rooms_range}_{7 empty positions}_{area_range}_{empty}_{floor_range}_{7 empty positions}_search-filter-top-bar`. Price, rooms, area, and floor ranges are all supported.

**City resolution**: `CITY_SEARCH_TERMS` maps 28 internal slugs (e.g., `"tel-aviv"`) to Hebrew Madlan search terms (e.g., `"תל-אביב-יפו"`). `CITY_BBOXES` provides bounding boxes for 17 cities to scope results geographically. Cities without a bounding box use term-only search.

**Persistent browser profile**: Profile stored at `data/madlan_profile/` — same pattern as Facebook's `data/fb_profile/`. No login is required for Madlan; the profile primarily caches site cookies and browser state to reduce load times on subsequent runs.

**Parser dual-mode**: `MadlanParser.parse_api_listing()` handles structured API JSON with many optional field name variants (e.g., `rooms` or `numberOfRooms`, `lat` or `latitude`). `MadlanParser.parse_dom_listing()` handles the less-structured card dicts produced by DOM extraction.

**Source-level deduplication**: The scraper deduplicates by `source_id` before returning results, because the same listing may appear in multiple intercepted API responses as the page loads in stages.

### Failed Approaches

No failed approaches — the Playwright network interception strategy was modelled directly on the existing Facebook implementation and worked on the first attempt. The positional URL filter format was discovered by observing Madlan's own UI behaviour in the browser.

---

## Session 7: Automatic AI Enrichment in Scrape Pipeline (2026-03-07)

### What Changed

**Motivation**: The on-demand "AI Extract Fields" button added in Session 6 gave users manual control over AI extraction for individual Facebook listings. However, most users would not know to press it, leaving structured fields unpopulated by default. The natural next step was to run AI extraction automatically for every Facebook listing during the scrape pipeline, so the data arriving in the DB is already as complete as possible.

**Files modified**:

| File | Change |
|------|--------|
| `src/pipeline/pipeline.py` | Added `_ai_enrich_facebook()` static async method. Added a new pipeline step (step 3) between normalize and deduplicate. Changed pipeline docstring to reflect new order. Added `_KEY_FIELDS` module-level constant listing the seven primary fields targeted by enrichment. |

### Implementation Details

- **Pipeline step order** (before this change): scrape → normalize → deduplicate → filter
- **Pipeline step order** (after this change): scrape → normalize → AI enrich → deduplicate → filter
- `_ai_enrich_facebook()` selects only Facebook listings whose description field exists and exceeds 30 characters after stripping whitespace. Listings without a meaningful description are skipped entirely.
- For each qualifying listing, it calls `extract_listing_fields()` from `src/ai/extractor.py` (the same function used by the on-demand `/api/listings/{source}/{source_id}/ai-extract` endpoint).
- All field writes are **additive only** — a field is only set if its current value is `None` (or `"unknown"` for `city`). Existing non-null values from the Facebook scraper are never overwritten.
- Fields populated by AI enrichment: `price`, `currency`, `rooms`, `city`, `neighborhood`, `street`, `house_number`, `floor`, `total_floors`, `area_sqm`, `entry_date`, `property_type`, and all ten boolean feature flags (`has_parking`, `has_elevator`, `has_balcony`, `has_air_conditioning`, `has_mamad`, `is_accessible`, `is_furnished`, `has_bars`, `has_storage`, `pet_friendly`), plus `contact_name` and `contact_phone`.
- `listing.ai_guessed_fields` is set on every successfully enriched listing, marking which fields were AI-inferred.
- Per-listing exceptions are caught and logged as warnings; a failed enrichment does not abort the pipeline or drop the listing.
- AI enrichment now runs on all Facebook scrapes automatically — the on-demand button in `ListingDetailModal` remains as a way to re-extract or update a specific listing after the fact.
- Deduplication runs after enrichment intentionally: AI-filled city/street/floor values improve the accuracy of the SHA256 fingerprint used by `ListingDeduplicator`.

### Failed Approaches

None documented for this session.

---

## Session 6: AI Field Extraction for Facebook Listings (2026-03-07)

### What Changed

**Motivation**: Facebook Marketplace listings often have unstructured descriptions with key fields (price, rooms, city, features) embedded in free text. Existing parsing does not reliably extract all structured fields. An on-demand AI extraction action allows users to trigger a re-scrape and AI-powered parse of individual Facebook listings to fill in missing or incorrect structured data.

**Files modified**:

| File | Change |
|------|--------|
| `src/ui/api.py` | Added `POST /api/listings/{source}/{source_id}/ai-extract` endpoint. Looks up the existing listing in the DB, rescrapes the Facebook listing page via `scrape_fb_listing()` using Playwright, runs `extract_listing_fields()` AI extraction on the scraped text, updates all extracted fields on the listing row (price, rooms, city, features, etc.), and returns the updated listing as `ListingResponse`. Only meaningful for Facebook listings. |
| `frontend/src/api.ts` | Added `aiExtractListing(source, sourceId)` function. Issues a `POST` to the new endpoint with a 120-second timeout (AI extraction + Playwright scrape is slow). |
| `frontend/src/components/ListingDetailModal.tsx` | Added optional prop `onListingUpdated?: (updated: Listing) => void`. Added an "AI Extract Fields" button (purple, `.btn-ai-extract` class) in the action links area, visible only when `source === "facebook"`. Button shows "Extracting..." during the async call and displays any error below the action links on failure. On success, calls `onListingUpdated` with the returned updated listing. |
| `frontend/src/App.tsx` | Wired `onListingUpdated` prop on `ListingDetailModal`. Handler updates `selectedListing` state with the new listing data and invalidates the react-query listings cache so the card list reflects any field changes. |
| `frontend/src/App.css` | Added styles for `.btn-ai-extract` (purple button) and `.ai-extract-error` (error text display). |

### Implementation Details

- The 120-second timeout on the frontend API call accommodates the combined time for Playwright browser startup, page navigation, and AI extraction.
- The button is only rendered for `source === "facebook"` listings — it has no applicable use for Yad2 listings, which are already fully structured.
- After a successful extraction, both the open modal and the listing card in the list are updated without requiring a manual page refresh: `selectedListing` state is updated directly and the react-query cache is invalidated.
- If the extraction fails, the error is shown inline below the action buttons inside the modal; the modal stays open.

### Failed Approaches

None documented for this session.

---

## Session 5: UI — Google Maps Buttons and ListingCard Detail Modal Link (2026-03-07)

### What Changed

**Motivation**: Users had no quick way to open a listing's location in an external map. Additionally, the "View Listing" button on `ListingCard` linked directly to the source URL, bypassing the in-app detail modal — inconsistent with how listings are viewed elsewhere in the UI.

**Files modified**:

| File | Change |
|------|--------|
| `frontend/src/components/MapView.tsx` | Added an "Open on Google Maps" button to `MapPreviewSidebar`. Rendered next to the existing "View Details" button. Only shown when the listing has lat/lng coordinates. Links to `https://www.google.com/maps?q={lat},{lng}`. |
| `frontend/src/components/ListingDetailModal.tsx` | Added an "Open on Google Maps" button in the contact section, next to the "View on {source}" button. Only rendered when the listing has location data (lat/lng). |
| `frontend/src/components/ListingCard.tsx` | Changed "View Listing" from an `<a>` tag (direct link to source URL) to a `<button>` element that calls `onOpenDetail` to open the in-app listing preview modal. |
| `frontend/src/App.css` | Added styles for `.map-preview-actions`, `.map-preview-gmaps`, `.btn-google-maps`. Updated `.btn-view` to work as a `<button>` element (was previously styled for `<a>`). |

### Implementation Details

- The Google Maps link format used is `https://www.google.com/maps?q={lat},{lng}`, which works without an API key and opens a pin at the exact coordinates.
- The button is conditionally rendered — listings without coordinates (no lat/lng) do not show the button in either `MapPreviewSidebar` or `ListingDetailModal`.
- The `ListingCard` "View Listing" button change means the source URL is now only accessible from inside the detail modal via the "View on {source}" button. This centralizes the external link access point and ensures users see full listing details before navigating away.

### Approaches

Single implementation pass — no failed alternatives.

---

## Session 4: Facebook Playwright — Detail Page Enrichment (2026-03-06)

### What Changed

**Motivation**: The Playwright fallback scraper for Facebook Marketplace only extracted preview data from search result cards — one thumbnail image and the listing title used as the description. This produced listings with minimal information: no full description text and only a low-resolution preview image.

**Fix**: Added a detail page enrichment step to `FacebookPlaywrightScraper` that navigates to each listing's individual page (`/marketplace/item/{id}/`) and extracts richer data before the card is parsed.

**Files modified**:

| File | Change |
|------|--------|
| `src/scrapers/facebook/scraper.py` | Added import of `LISTING_URL_TEMPLATE` from `.config`. Added new method `_enrich_from_detail_page()`. Added call to that method in `_scrape_sync()` between `_extract_listing_cards()` and the parse loop. |

### Implementation Details

`_enrich_from_detail_page(page, card_data, index, total)` mutates `card_data` in place:

- **Images**: Queries all `img[src*="scontent"], img[src*="fbcdn"]` elements on the detail page. Filters out small icons and avatars by checking `el.naturalWidth >= 150`. Deduplicates by `src`. Writes result to `card_data["listing_photos"]`.
- **Description**: Tries three CSS selectors in order: `[data-testid="marketplace_listing_description"] span`, `div[class*="Description"] span`, `span[dir="auto"]`. Picks the longest text block that exceeds 50 characters. Writes result to `card_data["redacted_description"]["text"]`.
- **Rate limiting**: Waits 1.5 seconds between detail page loads (`page.wait_for_timeout(1500)`) to reduce the risk of triggering Facebook's automated access detection.
- **Logging**: Logs at INFO level for the first 3 items and every 10th item. Logs image count and description length for the first 3.
- **Error handling**: Any exception during a detail fetch is caught and logged as a warning; the card is still passed to the parser with whatever preview data it already had.

### Approach

Single approach — no failed alternatives. The detail page visit pattern is the same used elsewhere in the scraper (`_ensure_logged_in`, login wait loop): navigate with `wait_until="domcontentloaded"` + `page.wait_for_timeout()` for a fixed settle delay. The `naturalWidth` check is the reliable way to distinguish content images from UI icons without adding a pixel-fetching round-trip.

---

## Session 3: UI Polish — NEW Badge Repositioned to Image Overlay (2026-03-06)

### What Changed

**Motivation**: The "NEW" badge on listing cards was sitting in the card header alongside the rating buttons, source badge, and freshness indicator — a crowded row. Moving it to overlay the card image (top-right corner) makes it more visually prominent and frees up space in the header row.

**Files modified**:

| File | Change |
|------|--------|
| `frontend/src/components/ListingCard.tsx` | Wrapped `<ImageCarousel>` in a `<div className="card-image-wrapper">`. Moved `{isNew && <span className="new-badge">NEW</span>}` inside that wrapper (was previously rendered inside `.card-header-right`). |
| `frontend/src/App.css` | Added `.card-image-wrapper { position: relative; }`. Updated `.new-badge` to use `position: absolute; top: 8px; right: 8px; z-index: 2` so it floats over the image. Added a selector exclusion so `.card-image-wrapper` does not inherit the horizontal padding rule applied to other card children. |

### Approach

Single straightforward approach — no failed alternatives. The `.card-image-wrapper` container provides the `position: relative` stacking context needed for the badge's absolute positioning, which is the standard CSS pattern for overlaying elements on images.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack & Dependencies](#3-tech-stack--dependencies)
4. [Directory Structure](#4-directory-structure)
5. [What Was Built (Steps 1–8)](#5-what-was-built-steps-18)
6. [Research & Discovery Log](#6-research--discovery-log)
7. [What Worked](#7-what-worked)
8. [What Failed](#8-what-failed)
9. [Data Models](#9-data-models)
10. [Database Schema](#10-database-schema)
11. [Scraping Architecture](#11-scraping-architecture)
12. [Yad2 Scraper Deep Dive](#12-yad2-scraper-deep-dive)
13. [Testing Guide](#13-testing-guide)
14. [How to Run](#14-how-to-run)
15. [What Was Built (Steps 9–20)](#15-what-was-built-steps-920)
16. [Session 2: Facebook Integration & UI Improvements](#16-session-2-facebook-integration--ui-improvements-2026-03-02)
17. [Lessons Learned](#17-lessons-learned)

---

## 1. Project Overview

ApartmentFinder aggregates apartment rental listings from **Yad2** (yad2.co.il — Israel's largest classifieds site) and **Facebook Marketplace**, applies user-defined filters (city, price, rooms, features), stores them in a local database, and can send Telegram notifications when new matching listings appear.

**Neither platform has an official public API.** All data access is reverse-engineered.

### Key User Decisions Made During Planning

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Package manager | `uv` | Fast, modern Python package manager |
| Apify (paid fallback) | Skip for now | Build direct scraping first, add Apify later if needed |
| Async vs Sync | Both | Async primary (httpx, aiosqlite), sync wrappers for CLI simplicity |
| Build order | Sequential Phase 1→6 | Layer-by-layer for testability |

---

## 2. Architecture

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────┐
│                   ApartmentFinder                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────────┐   ┌──────────────┐   ┌───────────┐  │
│  │  Yad2     │   │   Facebook   │   │  Future   │  │
│  │  API      │   │  Marketplace │   │  Sources  │  │
│  │  Scraper  │   │   Scraper    │   │           │  │
│  │  ✅ DONE  │   │   ✅ DONE    │   │   🔲      │  │
│  └─────┬─────┘   └──────┬───────┘   └─────┬─────┘  │
│        │                │                  │        │
│        ▼                ▼                  ▼        │
│  ┌──────────────────────────────────────────────┐   │
│  │       ScraperOrchestrator  ✅ DONE           │   │
│  │  (fallback chain: primary → fallback → skip) │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                               │
│                     ▼                               │
│  ┌──────────────────────────────────────────────┐   │
│  │          Pipeline  ✅ DONE                   │   │
│  │  normalize → deduplicate → filter → store    │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                               │
│                     ▼                               │
│  ┌──────────────────────────────────────────────┐   │
│  │         Database (SQLite)  ✅ DONE           │   │
│  │  listings | search_profiles | scrape_runs    │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                               │
│        ┌────────────┼────────────┐                  │
│        ▼            ▼            ▼                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐        │
│  │   CLI    │ │React+API │ │  Telegram    │        │
│  │  ✅ Done │ │  ✅ Done │ │  ✅ Done     │        │
│  └──────────┘ └──────────┘ └──────────────┘        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Layered Architecture

```
┌─────────────────────────────────────┐
│  Presentation Layer                 │
│  (CLI / React+FastAPI / Telegram)   │
├─────────────────────────────────────┤
│  Application Layer                  │
│  (Pipeline, Orchestrator, Scheduler)│
├─────────────────────────────────────┤
│  Domain Layer                       │
│  (Models, Filters, Enums)           │
├─────────────────────────────────────┤
│  Infrastructure Layer               │
│  (Scrapers, HTTP Client, Database)  │
└─────────────────────────────────────┘
```

### Data Flow (per scrape cycle)

```
1. Orchestrator tries each scraper in fallback chain (Yad2 API → FB GraphQL → FB Playwright)
2. Parser converts each raw item → ListingCreate (Pydantic model)
3. Normalizer standardizes city names (Hebrew→slug), USD→ILS prices, phone numbers
4. Deduplicator computes SHA256 fingerprint, removes cross-source duplicates
5. Filter engine applies SearchFilter criteria (city, price, rooms, features, keywords)
6. Repository upserts listings into SQLite (INSERT ON CONFLICT UPDATE)
7. Telegram notifier sends HTML-formatted alerts for new matches
```

---

## 3. Tech Stack & Dependencies

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `httpx[http2]` | ≥0.27 | Async HTTP client with HTTP/2 support |
| `beautifulsoup4` | ≥4.12 | HTML parsing (for `__NEXT_DATA__` fallback) |
| `lxml` | ≥5.0 | Fast HTML/XML parser backend |
| `playwright` | ≥1.40 | Browser automation (Facebook fallback) |
| `fake-useragent` | ≥1.5 | Random User-Agent rotation for anti-bot evasion |
| `sqlalchemy[asyncio]` | ≥2.0 | Async ORM for database operations |
| `aiosqlite` | ≥0.20 | Async SQLite driver |
| `alembic` | ≥1.13 | Database schema migrations |
| `apscheduler` | ≥3.10,<4.0 | Scheduled scraping jobs |
| `python-telegram-bot` | ≥21.0 | Async Telegram Bot API |
| `fastapi` | ≥0.110 | REST API backend for React frontend |
| `uvicorn` | ≥0.27 | ASGI server for FastAPI |
| `pydantic` | ≥2.5 | Data validation and serialization |
| `pydantic-settings` | ≥2.1 | Environment variable configuration |
| `python-dotenv` | ≥1.0 | `.env` file loading |
| `typer` | ≥0.12 | CLI framework |
| `rich` | ≥13.0 | Terminal formatting |

### Dev Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | ≥8.0 | Test framework |
| `pytest-asyncio` | ≥0.23 | Async test support |
| `pytest-httpx` | ≥0.30 | HTTP mocking for httpx |
| `ruff` | ≥0.4 | Linter and formatter |

---

## 4. Directory Structure

```
ApartmentFinder/
├── pyproject.toml                          # Project config, dependencies, tool settings
├── .env.example                            # Environment variable template
├── .gitignore                              # Git exclusions
├── PROJECT_PLAN.md                         # Research and architecture plan
├── DEVELOPMENT_LOG.md                      # ← This file
├── alembic.ini                             # Alembic migration config
├── alembic/
│   ├── env.py                              # Migration runtime environment
│   ├── script.py.mako                      # Migration script template
│   └── versions/
│       └── 0c933bf8a865_initial.py         # Initial schema migration
├── data/
│   └── apartmentfinder.db                  # SQLite database (git-ignored)
├── src/
│   ├── __init__.py
│   ├── config.py                           # Settings via pydantic-settings
│   ├── models/
│   │   ├── __init__.py                     # Re-exports all models
│   │   ├── enums.py                        # Source, PropertyType, Currency
│   │   ├── listing.py                      # ListingCreate + Listing
│   │   └── filters.py                      # SearchFilter
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py                       # Async/sync engine factories
│   │   ├── tables.py                       # SQLAlchemy ORM (3 tables)
│   │   └── repository.py                   # CRUD repositories (3 classes)
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py                         # Abstract BaseScraper
│   │   ├── http_client.py                  # Anti-bot HTTP client
│   │   ├── yad2/
│   │   │   ├── __init__.py
│   │   │   ├── config.py                   # URLs, city codes, feature maps
│   │   │   ├── parser.py                   # Yad2 JSON → ListingCreate
│   │   │   └── scraper.py                  # Yad2ApiScraper (paginated)
│   │   └── facebook/
│   │       ├── __init__.py
│   │       ├── config.py                   # GraphQL URLs, location IDs, feature mapping
│   │       ├── parser.py                   # GraphQL/HTML → ListingCreate
│   │       └── scraper.py                  # GraphQL + Playwright (persistent profile)
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── normalizer.py                  # Hebrew city names, USD→ILS, phone normalization
│   │   ├── deduplicator.py                # SHA256 fingerprint cross-source dedup
│   │   ├── filter_engine.py               # In-memory filter application
│   │   └── pipeline.py                    # End-to-end: scrape → normalize → dedup → filter
│   ├── notifications/
│   │   ├── __init__.py
│   │   ├── formatter.py                   # Telegram message formatting
│   │   └── telegram_bot.py                # Telegram bot client
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── jobs.py                        # APScheduler job definitions
│   │   └── runner.py                      # Scheduler executor
│   └── ui/
│       ├── __init__.py
│       └── api.py                         # FastAPI backend (4 endpoints)
├── data/
│   ├── apartmentfinder.db                 # SQLite database (git-ignored)
│   └── fb_profile/                        # Facebook browser profile (git-ignored)
├── frontend/
│   ├── src/
│   │   ├── main.tsx                       # React entry point
│   │   ├── App.tsx                        # Dashboard with split scrape UI
│   │   ├── App.css                        # Styling
│   │   └── api.ts                         # Axios API client
│   ├── vite.config.ts                     # Vite build config
│   └── package.json
└── tests/
    ├── __init__.py
    ├── conftest.py                         # In-memory SQLite fixture
    ├── fixtures/
    │   ├── yad2_api_sample.json            # Real Yad2 API response (~219 KB)
    │   ├── yad2_single_item.json           # Single listing item (~4.5 KB)
    │   ├── yad2_next_data_sample.json      # __NEXT_DATA__ format (~46 KB)
    │   ├── fb_graphql_sample.json          # Facebook GraphQL response fixture
    │   └── fb_single_item.json             # Single Facebook listing
    ├── test_models.py                      # 12 tests
    ├── test_db_repository.py               # 9 tests
    ├── test_yad2_parser.py                 # 17 tests
    ├── test_yad2_scraper.py                # 5 unit + 1 integration
    ├── test_fb_parser.py                   # 38 tests
    ├── test_fb_scraper.py                  # 10 tests
    ├── test_normalizer.py                  # 19 tests
    ├── test_deduplicator.py                # 12 tests
    ├── test_filter_engine.py               # 21 tests
    ├── test_pipeline.py                    # 9 tests
    └── test_telegram_formatter.py          # 17 tests
```

---

## 5. What Was Built (Steps 1–8)

### Step 1: Project Scaffold
- Created `pyproject.toml` with all dependencies and tool configurations
- Created `.gitignore`, `.env.example`
- Set up `uv` virtual environment
- Created directory structure with `__init__.py` files
- **Installed 78 packages** via `uv sync --all-extras`
- **Verification**: `uv run python -c "import src"` — succeeded

### Step 2: Config Module
- Created `src/config.py` with `Settings(BaseSettings)` class
- Loads from `.env` file with fallback defaults
- Properties for both async (`sqlite+aiosqlite:///`) and sync (`sqlite:///`) database URLs
- Singleton via `@lru_cache`
- **Verification**: Settings load correctly with default database path

### Step 3: Pydantic Models
- `src/models/enums.py`: `Source`, `PropertyType`, `Currency` (all `StrEnum`)
- `src/models/listing.py`: `ListingCreate` (57 fields) + `Listing` (extends with id, fingerprint, timestamps)
  - Rooms as `float` for Israeli 2.5-room convention
  - 10 boolean feature flags (parking, elevator, balcony, AC, mamad, accessible, furnished, bars, storage, pet-friendly)
  - `field_validator` for city whitespace stripping
- `src/models/filters.py`: `SearchFilter` with range filters, feature requirements, keyword search
- **Verification**: 12 tests passing — validates field defaults, types, validators, and edge cases

### Step 4: Database Schema
- `src/db/tables.py`: Three SQLAlchemy ORM models
  - `ListingRow` (40+ columns, 4 indexes, 1 unique constraint)
  - `SearchProfileRow` (7 columns)
  - `ScrapeRunRow` (9 columns)
- `src/db/engine.py`: Factory functions for async/sync engines
- Set up Alembic: `alembic.ini`, `alembic/env.py`
- Generated and applied initial migration
- **Issue encountered**: Alembic `script.py.mako` template missing — had to manually copy it from Alembic's installed package (see [What Failed](#8-what-failed))
- **Verification**: `alembic upgrade head` created all 3 tables + indexes

### Step 5: Repository CRUD
- `src/db/repository.py`: Three repository classes
  - `ListingRepository`: upsert, query with filters, mark inactive, fingerprint lookup
  - `SearchProfileRepository`: CRUD for saved searches
  - `ScrapeRunRepository`: Start/finish audit records
- `_apply_filter()`: Builds dynamic SQLAlchemy WHERE clauses from `SearchFilter`
- **Verification**: 9 tests passing — upsert, duplicate handling, filter queries, feature queries, soft delete

### Step 6: HTTP Client + Base Scraper
- `src/scrapers/base.py`: Abstract `BaseScraper` with `scrape()`, `health_check()`
- `src/scrapers/http_client.py`: `ScraperHttpClient` class
  - Randomized User-Agent via `fake-useragent`
  - Full browser-like headers (Hebrew locale, Sec-Fetch-*, DNT)
  - Exponential backoff retry (2^attempt + random jitter)
  - Optional proxy support
  - `random_delay()` for rate limiting (3–10 seconds configurable)
- **Issue encountered**: httpx `AsyncClient.close()` was renamed to `aclose()` in newer versions (see [What Failed](#8-what-failed))
- **Verification**: Import test + headers inspection shows realistic browser User-Agent

### Step 7: Yad2 Parser (Offline)
- **First**: Captured real data from Yad2 to understand the response format
- `src/scrapers/yad2/config.py`: API URLs, Hebrew→English mappings, city codes, feature field maps
- `src/scrapers/yad2/parser.py`: `Yad2Parser` with static methods for parsing all field types
  - Price parsing: regex strips "4,000 ₪" → `4000.0`
  - Rooms from `Rooms` field or `row_4` array
  - Features from `*_text` fields ("אין" = false, non-empty = true)
  - Property types from Hebrew text mapping
  - Coordinates, dates, images, contact info
  - Preserves full `raw_data` for debugging
- **Verification**: 17 tests passing against real Yad2 API fixture data

### Step 8: Yad2 Live Scraper
- `src/scrapers/yad2/scraper.py`: `Yad2ApiScraper(BaseScraper)`
  - Paginated fetching (max 5 pages safety limit)
  - Maps `SearchFilter` → Yad2 API query params
  - Random delays between pages
  - Health check endpoint
- **Verification**: 5 unit tests (mocked HTTP) + manual integration test confirms live scraping works
- **Result**: Successfully scraped 40+ listings from Yad2 in a single API call

---

## 6. Research & Discovery Log

### Yad2 API Discovery

#### Approach 1: `__NEXT_DATA__` Parsing (Original Plan)

The original plan was to parse the `<script id="__NEXT_DATA__">` JSON from Yad2's Next.js frontend.

**What happened**:
- Fetched `https://www.yad2.co.il/realestate/rent` (lobby page) — got `__NEXT_DATA__` with `pageProps` containing `dehydratedState.queries`
- However, the lobby page has **no listing data** — only CMS content (region links, recommendations)
- Fetching the search results page (`?topArea=2&area=1&city=5000`) **triggered anti-bot**: response contained "Are you for real" captcha page
- **Conclusion**: `__NEXT_DATA__` on the lobby page is useless, and search pages have anti-bot protection

#### Approach 2: Internal JSON API (What Actually Works)

While probing different endpoints, discovered:

```
https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/rent
```

**Findings**:
- Returns raw JSON (not HTML) — no parsing needed
- **No anti-bot protection** on this endpoint
- Supports query params: `city`, `price` (range), `rooms` (range), `page`
- Returns 50 items per page with full pagination metadata
- Each listing has 94 fields including coordinates, features, images, contact info
- Item types: `ad` (38 regular), `advanced_ad` (8 promoted), `innerRich`, `middle_strip`, `title`, `agency_buttons`
- Only `ad` and `advanced_ad` types contain actual listing data

**Other endpoints tried that did NOT work**:

| Endpoint | Result |
|----------|--------|
| `https://gw.yad2.co.il/feed-search-legacy/realestate/rent` | 404 (deprecated) |
| `https://gw.yad2.co.il/realestate/rent` | 404 |
| `https://gw.yad2.co.il/api/feed/realestate/rent` | 404 |
| `https://gw.yad2.co.il/feed/realestate/rent` | 404 |
| `http://m.yad2.co.il/API/MadorResults.php` | Not tested (legacy mobile) |

#### Approach 3: Legacy Mobile API

Documented in research but **not tested**. The `MadorResults.php` endpoint is from Yad2's old mobile app and may be deprecated.

### Facebook Marketplace Research

Research done in Session 1; implementation completed in Session 2 (see [Section 16](#16-session-2-facebook-integration--ui-improvements-2026-03-02)). Key findings:

- **No official API** for reading listings (Commerce API is seller-only)
- **GraphQL API**: `POST https://www.facebook.com/api/graphql/` with `doc_id` values — free but `doc_id`s rotate
- **Playwright**: Full browser scraping — most resilient but slowest
- **Apify**: `apify/facebook-marketplace-scraper` at $5/1K results — skipped per user decision
- **Legal**: *Meta v. Bright Data (2024)* ruled that scraping public data while logged out does not violate ToS

### Existing Libraries Evaluated

| Library | Language | Approach | Verdict |
|---------|----------|----------|---------|
| [DavOstx7/yad2-scraper](https://github.com/DavOstx7/yad2-scraper) | Python | `__NEXT_DATA__` | Good reference but targets vehicle listings |
| [NivEz/yad2-scraper](https://github.com/NivEz/yad2-scraper) | Node.js | Cheerio + GitHub Actions | Good architecture pattern |
| [passivebot/facebook-marketplace-scraper](https://github.com/passivebot/facebook-marketplace-scraper) | Python | Playwright + BS4 | Reference for FB scraping |
| [kyleronayne/marketplace-api](https://github.com/kyleronayne/marketplace-api) | Python | GraphQL | Reference for FB GraphQL doc_ids |

---

## 7. What Worked

### 1. Yad2 Internal JSON API
The biggest win. Instead of fighting anti-bot protection on HTML pages, we found an **unprotected JSON API** that returns structured data with 94 fields per listing. No BeautifulSoup needed, no `__NEXT_DATA__` extraction, no anti-bot evasion required.

**Endpoint**: `https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/rent`

### 2. Fixture-Based Testing
Capturing a real API response as a JSON fixture (`yad2_api_sample.json`, 219 KB) allowed:
- Writing 17 parser tests against real data structure
- No network dependency in unit tests
- Discovering edge cases in the real data (missing fields, `null` values, ad types)

### 3. Pydantic Models with Strict Types
Using `StrEnum` for Source/PropertyType/Currency catches invalid data early. The `field_validator` on city names normalizes whitespace from all sources.

### 4. In-Memory SQLite for Tests
The `conftest.py` fixture creates a fresh in-memory database per test, making the 9 repository tests fast (~0.35s total) and completely isolated.

### 5. `uv` Package Manager
Installed all 78 packages in ~30 seconds including heavy packages like `numpy`, `pandas`, `pyarrow` (Streamlit dependencies), and `playwright`.

### 6. Async Architecture
Using `httpx.AsyncClient` + `aiosqlite` means scraping Yad2 and Facebook can happen concurrently once both scrapers are built.

---

## 8. What Failed

### 1. `__NEXT_DATA__` Approach for Yad2 Search Results
**What**: Tried fetching `https://www.yad2.co.il/realestate/rent?city=5000` to parse `__NEXT_DATA__`
**Result**: Got "Are you for real" anti-bot captcha page (status 200 but captcha HTML instead of results)
**Why**: Yad2 has aggressive bot detection on their search result pages
**Resolution**: Discovered the internal JSON API endpoint which has no anti-bot protection

### 2. `__NEXT_DATA__` on Lobby Page Has No Listings
**What**: Successfully fetched `__NEXT_DATA__` from the lobby page (no search params)
**Result**: The `dehydratedState.queries` contained only CMS content (region links, recommendations), not listing data
**Why**: The lobby page is a different Next.js route that doesn't load feed data
**Resolution**: The lobby fixture was saved but unused. The API endpoint is used instead.

### 3. All `gw.yad2.co.il` Endpoints Return 404
**What**: Tried 4 different paths under the `gw.yad2.co.il` gateway domain
**Result**: All returned 404 with anti-bot JavaScript
**Why**: These are either deprecated or internal-only endpoints
**Resolution**: Found the working endpoint under `www.yad2.co.il/api/pre-load/...`

### 4. Alembic Missing `script.py.mako` Template
**What**: Running `alembic revision --autogenerate` failed with `FileNotFoundError: alembic\script.py.mako`
**Result**: Migration detected all tables correctly but couldn't generate the `.py` file
**Why**: When manually creating the `alembic/` directory (instead of using `alembic init`), the Mako template file isn't included
**Resolution**: Copied the template from Alembic's installed package:
```bash
cp .venv/Lib/site-packages/alembic/templates/generic/script.py.mako alembic/script.py.mako
```

### 5. httpx `AsyncClient.close()` → `aclose()`
**What**: Tests failed with `AttributeError: 'AsyncClient' object has no attribute 'close'`
**Result**: 3 tests that called `await scraper._client.close()` failed on cleanup
**Why**: httpx renamed `close()` to `aclose()` in newer versions for PEP 646 compliance
**Resolution**: Changed `self._client.close()` to `self._client.aclose()` in `http_client.py`

### 6. Unicode Encoding Errors on Windows Console
**What**: Printing Hebrew text from Yad2 API responses crashed with `UnicodeEncodeError: 'charmap' codec can't encode characters`
**Result**: Python scripts would crash when printing Hebrew listing data
**Why**: Windows console uses cp1252 encoding by default, which doesn't support Hebrew characters
**Resolution**: Used `PYTHONIOENCODING=utf-8` environment variable, or wrote output to files instead of stdout

### 7. Integration Test Returns 0 Listings
**What**: The `test_real_scrape` integration test scraped 0 listings from the live API
**Result**: Test assertion `assert len(listings) > 0` failed
**Why**: When running inside pytest, the `pytest-httpx` mock might interfere with real HTTP clients, or the ScraperHttpClient was creating a new client that was affected by test infrastructure
**Resolution**: Confirmed the scraper works correctly outside of pytest via a standalone `asyncio.run()` script (returned 40+ listings). The integration test was marked with `@pytest.mark.integration` and excluded from the default test run.

---

## 9. Data Models

### ListingCreate (Scraper Output)

```python
class ListingCreate(BaseModel):
    # Identity
    source: Source                  # "yad2" or "facebook"
    source_id: str                  # Platform's listing ID
    source_url: str                 # Direct link to listing

    # Core
    title: str = ""
    price: float | None = None
    currency: Currency = Currency.ILS
    city: str                       # Required
    neighborhood: str | None
    street: str | None
    house_number: str | None

    # Property details
    rooms: float | None             # 2.5 rooms is common in Israel
    floor: int | None
    total_floors: int | None
    area_sqm: float | None
    property_type: PropertyType | None
    description: str | None
    image_urls: list[str] = []

    # 10 boolean feature flags
    has_parking: bool | None
    has_elevator: bool | None
    has_balcony: bool | None
    has_air_conditioning: bool | None
    has_mamad: bool | None          # Safe room (common in Israel)
    is_accessible: bool | None
    is_furnished: bool | None
    has_bars: bool | None
    has_storage: bool | None
    pet_friendly: bool | None

    # Contact
    contact_name: str | None
    contact_phone: str | None

    # Dates
    entry_date: date | None
    posted_at: datetime | None
    updated_at: datetime | None

    # Geo
    latitude: float | None
    longitude: float | None

    # Debug
    raw_data: dict = {}
```

### SearchFilter (Query Criteria)

```python
class SearchFilter(BaseModel):
    name: str = "default"
    cities: list[str] = []              # Lowercased automatically
    neighborhoods: list[str] = []       # Lowercased automatically
    min_price / max_price: float | None
    min_rooms / max_rooms: float | None
    min_area_sqm / max_area_sqm: float | None
    min_floor / max_floor: int | None
    property_types: list[str] = []

    # Feature requirements (None = don't care)
    require_parking: bool | None
    require_elevator: bool | None
    require_balcony: bool | None
    require_air_conditioning: bool | None
    require_mamad: bool | None
    require_pet_friendly: bool | None
    require_furnished: bool | None

    # Text search
    keywords: list[str] = []
    exclude_keywords: list[str] = []
```

---

## 10. Database Schema

### Tables

#### `listings` (40+ columns)

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) PK | Auto-generated UUID |
| `source` | VARCHAR(20) | "yad2" or "facebook" |
| `source_id` | VARCHAR(100) | Platform's ID (unique with source) |
| `source_url` | VARCHAR(500) | Direct link |
| `fingerprint` | VARCHAR(64) | Dedup hash (indexed) |
| `title` | VARCHAR(500) | |
| `price` | FLOAT | Nullable |
| `currency` | VARCHAR(5) | "ILS" or "USD" |
| `city` | VARCHAR(100) | Indexed with price and rooms |
| `neighborhood` | VARCHAR(100) | |
| `street` | VARCHAR(200) | |
| `rooms` | FLOAT | 2.5 supported |
| `floor` | INTEGER | |
| `area_sqm` | FLOAT | |
| `description` | TEXT | |
| `image_urls` | JSON | Array of URLs |
| `property_type` | VARCHAR(50) | |
| `has_parking` ... `pet_friendly` | BOOLEAN | 10 feature columns |
| `contact_name`, `contact_phone` | VARCHAR | |
| `entry_date` | DATE | Move-in date |
| `posted_at`, `updated_at` | DATETIME | From platform |
| `latitude`, `longitude` | FLOAT | |
| `raw_data` | JSON | Full original response |
| `first_seen_at` | DATETIME | When we first scraped it |
| `last_seen_at` | DATETIME | Last time we saw it active |
| `is_active` | BOOLEAN | Soft delete flag |

**Indexes**:
- `uq_source_listing`: UNIQUE(source, source_id)
- `ix_city_price`: city + price
- `ix_city_rooms`: city + rooms
- `ix_fingerprint`: fingerprint
- `ix_first_seen`: first_seen_at

#### `search_profiles`

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) PK | UUID |
| `name` | VARCHAR(100) | Human label |
| `telegram_chat_id` | VARCHAR(50) | For notifications |
| `filter_json` | JSON | Serialized SearchFilter |
| `is_active` | BOOLEAN | |
| `created_at` | DATETIME | |
| `last_notified_at` | DATETIME | |

#### `scrape_runs`

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) PK | UUID |
| `source` | VARCHAR(20) | "yad2" or "facebook" |
| `method` | VARCHAR(50) | "api", "graphql", etc. |
| `started_at` | DATETIME | |
| `finished_at` | DATETIME | |
| `listings_found` | INTEGER | |
| `listings_new` | INTEGER | |
| `status` | VARCHAR(20) | "running", "success", "failed" |
| `error_message` | TEXT | |

### Why Individual Boolean Columns for Features?

Storing features as individual columns (`has_parking`, `has_elevator`, etc.) instead of a JSON object allows:

```sql
-- This is fast with indexed boolean columns:
SELECT * FROM listings WHERE city = 'tel-aviv' AND has_parking = 1 AND has_elevator = 1

-- This would be slow with JSON:
SELECT * FROM listings WHERE json_extract(features, '$.parking') = true
```

---

## 11. Scraping Architecture

### Class Hierarchy

```
BaseScraper (ABC)
├── Yad2ApiScraper              ✅ Implemented (JSON API)
├── FacebookGraphQLScraper      ✅ Implemented (needs cookies)
└── FacebookPlaywrightScraper   ✅ Implemented (persistent browser profile)
```

### HTTP Client Anti-Bot Features

```python
ScraperHttpClient:
  Headers:
    User-Agent: [randomized per request via fake-useragent]
    Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
    Accept-Language: he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7
    Accept-Encoding: gzip, deflate, br
    Sec-Fetch-Dest: document
    Sec-Fetch-Mode: navigate
    Sec-Fetch-Site: none
    Sec-Fetch-User: ?1
    Upgrade-Insecure-Requests: 1
    DNT: 1
    Cache-Control: max-age=0

  Retry logic:
    attempt 1: immediate
    attempt 2: wait 2^1 + random(0,1) seconds
    attempt 3: wait 2^2 + random(0,1) seconds

  Rate limiting:
    random_delay(): sleep(uniform(3.0, 10.0)) between pages
```

### Scraper Orchestrator Pattern (Planned)

```python
scraper_chains = {
    "yad2": [Yad2ApiScraper, Yad2PlaywrightScraper],
    "facebook": [FacebookGraphQLScraper, FacebookPlaywrightScraper],
}

# For each source: try primary → fallback → skip
for source, scrapers in chains.items():
    for scraper in scrapers:
        try:
            results = await scraper.scrape(filter)
            if results:
                break  # Success, next source
        except Exception:
            continue  # Try next scraper
```

---

## 12. Yad2 Scraper Deep Dive

### API Endpoint

```
GET https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/rent
```

### Query Parameters

| Param | Format | Example | Notes |
|-------|--------|---------|-------|
| `city` | Yad2 city code | `5000` | Tel Aviv. Multiple: `5000,3000` |
| `price` | `min-max` | `3000-7000` | Omit min/max for open range: `-7000` |
| `rooms` | `min-max` | `2-4` | Supports decimals: `2.5-3.5` |
| `page` | integer | `1` | 50 items per page |

### Response Structure

```json
{
  "feed": {
    "cat_id": "2",
    "subcat_id": "6",
    "feed_items": [
      {
        "type": "ad",               // "ad" = regular, "advanced_ad" = promoted
        "id": "2sdaa2j2",           // Listing token
        "ad_number": 77297233,      // Numeric listing ID
        "city": "תל אביב יפו",
        "neighborhood": "פלורנטין",
        "street": "הרצל",
        "price": "4,000 ₪",
        "currency": "₪",
        "Rooms": 2,
        "square_meters": 50,
        "coordinates": {
          "latitude": "32.0552789836956",
          "longitude": "34.7702480706522"
        },
        "row_4": [
          {"key": "rooms", "label": "חדרים", "value": 2},
          {"key": "floor", "label": "קומה", "value": 1},
          {"key": "SquareMeter", "label": "מ\"ר", "value": "50"}
        ],
        "images_urls": ["https://img.yad2.co.il/..."],
        "HomeTypeID_text": "דירה",  // Property type in Hebrew
        "Parking_text": "",         // Empty = unknown
        "Elevator_text": "",
        "AirConditioner_text": "מיזוג",  // Non-empty = has feature
        "Porch_text": "אין",       // "אין" = no balcony
        "contact_name": "...",
        "date_added": "2026-02-16 13:07:39",
        "date_of_entry": "2026-02-24 00:00:00"
        // ... 94 total fields
      }
    ],
    "current_page": 1,
    "total_pages": 25,
    "total_items": 889,
    "page_size": 50
  }
}
```

### Feature Detection Logic

Yad2 expresses features as Hebrew text fields:

| Field | Value | Parsed As |
|-------|-------|-----------|
| `Parking_text` | `""` (empty) | `has_parking = None` (unknown) |
| `AirConditioner_text` | `"מיזוג"` (AC) | `has_air_conditioning = True` |
| `Porch_text` | `"אין"` (none) | `has_balcony = False` |
| `Furniture_text` | `"ריהוט"` (furniture) | `is_furnished = True` |
| `PetsInHouse_text` | `"חיות מחמד"` (pets) | `pet_friendly = True` |

### City Code Mapping

```python
CITY_CODES = {
    "tel-aviv": "5000",
    "jerusalem": "3000",
    "haifa": "4000",
    "beer-sheva": "7900",
    "netanya": "7400",
    "rishon-lezion": "8300",
    "herzliya": "6400",
    "raanana": "8600",
    "rehovot": "8400",
    "modiin": "1247",
    # ... 18 cities total
}
```

---

## 13. Testing Guide

### Running Tests

```bash
# All unit tests (excludes integration tests)
uv run pytest tests/ -v -m "not integration"

# Specific test file
uv run pytest tests/test_yad2_parser.py -v

# Single test
uv run pytest tests/test_models.py::TestListingCreate::test_half_rooms -v

# Integration tests (hits real APIs — run manually)
uv run pytest tests/ -v -m "integration"

# With coverage (if coverage installed)
uv run pytest tests/ -v --tb=short
```

### Test Organization

| File | Tests | What It Covers |
|------|-------|---------------|
| `test_models.py` | 12 | Pydantic model creation, validation, defaults, edge cases |
| `test_db_repository.py` | 9 | Database CRUD, filter queries, upsert, soft delete |
| `test_yad2_parser.py` | 17 | Field parsing from real API fixtures (price, rooms, features, etc.) |
| `test_yad2_scraper.py` | 5+1 | Mocked HTTP scraping, health checks, param building + 1 live integration |
| **Total** | **43+1** | |

### Test Fixtures

Located in `tests/fixtures/`:

| File | Size | Source | Contains |
|------|------|--------|----------|
| `yad2_api_sample.json` | 219 KB | Live Yad2 API call | Full response with ~50 items (38 listings + 8 promoted + 4 UI elements) |
| `yad2_single_item.json` | 4.5 KB | Extracted from above | Single listing with all 94 fields — the test reference |
| `yad2_next_data_sample.json` | 46 KB | Yad2 lobby page | `__NEXT_DATA__` from lobby (no listings — kept for reference) |

### How to Capture New Fixtures

```python
# Capture a fresh Yad2 API response
import httpx, json
from fake_useragent import UserAgent

ua = UserAgent()
headers = {
    "User-Agent": ua.random,
    "Accept": "application/json",
    "Accept-Language": "he-IL,he;q=0.9",
    "Referer": "https://www.yad2.co.il/realestate/rent",
}

r = httpx.get(
    "https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/rent",
    headers=headers,
    params={"city": "5000", "rooms": "2-4", "price": "3000-7000"},
    timeout=30,
    follow_redirects=True,
)

with open("tests/fixtures/yad2_api_sample.json", "w", encoding="utf-8") as f:
    json.dump(r.json(), f, ensure_ascii=False, indent=2)
```

### Testing Architecture

```
Unit tests (43)
  ├── No network calls — all HTTP mocked with pytest-httpx
  ├── In-memory SQLite — no file I/O
  ├── Fixture-based — real data structure, fake content
  └── Fast — full suite runs in ~9 seconds

Integration tests (1, manual)
  ├── Marked with @pytest.mark.integration
  ├── Excluded from default pytest run
  ├── Hits real Yad2 API (rate limited)
  └── Must be run explicitly: uv run pytest -m integration
```

---

## 14. How to Run

### Initial Setup

```bash
# Clone / navigate to project
cd n:\Dev\3_AI\ApartmentFinder

# Install dependencies
uv sync --all-extras

# Copy environment template
cp .env.example .env

# Run database migrations
uv run alembic upgrade head

# Verify setup
uv run python -c "from src.config import get_settings; print(get_settings().database_path)"
```

### Quick Scrape Test (Yad2)

```python
# Save as test_quick.py and run: uv run python test_quick.py
import asyncio
from src.models.filters import SearchFilter
from src.scrapers.yad2.scraper import Yad2ApiScraper

async def main():
    scraper = Yad2ApiScraper()
    f = SearchFilter(cities=["tel-aviv"], max_price=7000, min_rooms=2, max_rooms=3)
    listings = await scraper.scrape(f)
    print(f"Found {len(listings)} listings")
    for l in listings[:5]:
        print(f"  {l.rooms}r | {l.price} ILS | {l.city} {l.street or ''} | {l.property_type}")
    await scraper._client.close()

asyncio.run(main())
```

### Run All Tests

```bash
uv run pytest tests/ -v -m "not integration"
```

---

## 15. What Was Built (Steps 9–20)

### Step 9: Facebook Parser (Offline) — 38 Tests

**Files created:**
- `src/scrapers/facebook/config.py` — GraphQL endpoint, location IDs for 17 Israeli cities, doc_id list, feature keyword mapping
- `src/scrapers/facebook/parser.py` — `FacebookParser` class with static methods matching the Yad2 parser pattern
- `tests/fixtures/fb_graphql_sample.json` — Realistic GraphQL response fixture (4 listings + 1 sponsored null)
- `tests/fixtures/fb_single_item.json` — Single listing for detailed field tests
- `tests/test_fb_parser.py` — 38 tests covering extraction, pagination, all fields, edge cases

**Key design decisions:**
- Facebook uses `bedrooms` not total rooms — stored as-is (Israeli convention differs)
- Features extracted from both `attribute_data` (structured) and description text (keyword scan)
- Sold/pending listings are automatically skipped
- Property type mapping: `APARTMENT`, `HOUSE`, `TOWNHOUSE`, `CONDO`, `PENTHOUSE`, `STUDIO`, `DUPLEX`

### Step 10: Facebook Scrapers (GraphQL + Playwright) — 10 Tests

**Files created:**
- `src/scrapers/facebook/scraper.py` — Two scraper classes:
  - `FacebookGraphQLScraper` — POST to `/api/graphql/` with doc_id + variables, cursor pagination, multi-location support
  - `FacebookPlaywrightScraper` — Browser automation fallback using Playwright
- `src/scrapers/facebook/__init__.py` — Clean module exports
- `tests/test_fb_scraper.py` — 10 tests (mocked HTTP, fallback behavior, param building)

**GraphQL scraper features:**
- Tries multiple `doc_id` values in sequence (fallback on error)
- Supports session cookies + LSD token for authenticated access
- Cursor-based pagination with configurable max pages
- Maps `SearchFilter` to GraphQL variables (price bounds, location ID)
- Rate limiting between pages via `random_delay()`

**Playwright scraper features:**
- Headless Chromium browser automation
- Auto-dismisses Facebook login modals
- Scrolls page to load more listings
- Extracts listing data from DOM via `a[href*="/marketplace/item/"]` links
- Builds parser-compatible dict from card text lines

**Bug fixed:** `test_health_check_failure` needed `@pytest.mark.httpx_mock(can_send_already_matched_responses=True)` because the HTTP client retries and the scraper tries multiple doc_ids — consuming more mock responses than registered.

### Step 11: Normalizer — 19 Tests

**File:** `src/pipeline/normalizer.py` — `ListingNormalizer` class

**Normalization features:**
- **City names**: 60+ Hebrew→English slug mappings (`"תל אביב יפו"` → `"tel-aviv"`, `"ירושלים"` → `"jerusalem"`)
- **Price conversion**: USD→ILS at 3.7 rate (configurable)
- **Phone numbers**: Normalized to `+972XXXXXXXXX` format (handles `054-`, `+972-`, landlines)
- **Property types**: Hebrew→enum mapping
- **Text cleanup**: Collapses whitespace, strips leading/trailing spaces
- **Batch processing**: `normalize_batch()` with error recovery (keeps original on failure)

### Step 12: Deduplicator — 12 Tests

**File:** `src/pipeline/deduplicator.py` — `ListingDeduplicator` class

**Fingerprint algorithm:**
- SHA256 of `city|street|house_number|rooms|floor|price_bucket`
- Price bucket: 200 ILS tolerance (e.g., 5000 and 5100 → same bucket)
- Cross-source: same apartment on Yad2 and Facebook produces same fingerprint

**Deduplication strategy:**
- When duplicates found, keeps the listing with highest "completeness score"
- Score = count of filled optional fields + image count + feature flag count

### Step 13: Filter Engine — 21 Tests

**File:** `src/pipeline/filter_engine.py` — `FilterEngine.apply()` static method

**Filter criteria (all composable):**
- Cities (list), neighborhoods (list)
- Price range, rooms range, area range, floor range
- Property types (list)
- Feature requirements (parking, elevator, balcony, A/C, mamad, pet-friendly, furnished)
- Keywords (any match in title/description), exclude keywords (any match rejects)

### Step 14: Orchestrator + Pipeline — 9 Tests

**Files:**
- `src/scrapers/orchestrator.py` — `ScraperOrchestrator` with fallback chains per source
- `src/pipeline/pipeline.py` — `ScrapePipeline` end-to-end: scrape → normalize → dedup → filter

**Orchestrator features:**
- Register multiple scrapers per source (e.g., GraphQL primary, Playwright fallback)
- Tries each in order; first to return results wins
- Logs timing and error details for each attempt
- `health_check_all()` for connectivity monitoring

**Pipeline flow:**
1. Scrape from all registered sources (via orchestrator)
2. Normalize city names, prices, phones
3. Deduplicate across sources
4. Apply search filter for client-side criteria
5. Return `PipelineResult` with counts at each stage

### Step 15: Telegram Formatter — 17 Tests

**File:** `src/notifications/formatter.py` — `TelegramFormatter` class

**Message format (HTML for Telegram):**
```
<b>3.0r in tel-aviv</b> — 5,200 ₪
Dizengoff 42, Center, floor 2/5, 60m²
Parking | Elevator | Balcony | A/C
Type: apartment
<i>Beautiful renovated apartment in the heart of Tel Aviv.</i>
<a href="...">View on yad2</a>
```

**Features:** Batch formatting with separators, summary messages, price formatting (ILS ₪ / USD $), description truncation at 100 chars.

### Step 16: Telegram Notifier

**File:** `src/notifications/telegram_bot.py` — `TelegramNotifier` class

- Sends listings in batches of 3 per message (avoids Telegram char limit)
- 1 message/second rate limiting
- `test_connection()` for verifying bot setup
- Lazy-initializes `telegram.Bot` instance

### Step 17: Scheduler

**Files:**
- `src/scheduler/jobs.py` — `scrape_job()` (main pipeline + DB storage + notifications), `cleanup_job()`
- `src/scheduler/runner.py` — APScheduler `AsyncIOScheduler` setup

**Job behavior:**
- Runs pipeline for each active search profile
- Computes fingerprints and upserts to DB
- Sends Telegram notifications for new listings
- Records scrape runs in `scrape_runs` table for audit trail
- First scrape runs immediately on scheduler start

### Step 18: CLI (Typer) — 6 Commands

**File:** `src/main.py` — Typer CLI application

| Command | Description |
|---------|-------------|
| `scrape` | On-demand scrape with source/city/price/rooms filters |
| `list` | Query stored listings from DB with filters |
| `run-scheduler` | Start the background scheduler |
| `add-search` | Create a search profile for scheduled scraping |
| `test-telegram` | Verify Telegram bot configuration |
| `health` | Check connectivity to all scraping sources |

**Usage:** `uv run python -m src.main scrape --source yad2 --city tel-aviv --max-price 7000`

### Step 19–20: React Frontend + FastAPI Backend

**Changed from Streamlit to React** (per user request).

**Backend:** `src/ui/api.py` — FastAPI application

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/listings` | GET | Filtered listings with full query params |
| `/api/scrape` | POST | Trigger on-demand scrape |
| `/api/stats` | GET | Summary statistics (total, sources, cities) |
| `/api/health` | GET | Source connectivity check |

**Frontend:** `frontend/` — React + TypeScript + Vite

- **State management**: TanStack React Query for server state
- **HTTP client**: Axios
- **Components**: FilterSidebar (city dropdown, price/rooms/area ranges, feature checkboxes), ListingCard (price, location, features, description, link), StatsBar (totals)
- **Features**: Live filtering, "Scrape Now" button, auto-refresh, responsive grid layout

**How to run:**
```bash
# Terminal 1: Start API backend
uv run uvicorn src.ui.api:app --reload --port 8000

# Terminal 2: Start React dev server
cd frontend && npm run dev
```

### Test Suite Summary

| Test File | Tests | What It Tests |
|-----------|-------|---------------|
| test_models.py | 12 | Pydantic model validation |
| test_db_repository.py | 9 | Database CRUD operations |
| test_yad2_parser.py | 17 | Yad2 API response parsing |
| test_yad2_scraper.py | 5+1 | Yad2 scraper + integration |
| test_fb_parser.py | 38 | Facebook GraphQL parsing |
| test_fb_scraper.py | 10 | Facebook scraper + fallback |
| test_normalizer.py | 19 | City/price/phone normalization |
| test_deduplicator.py | 12 | Fingerprint + dedup logic |
| test_filter_engine.py | 21 | All filter criteria |
| test_pipeline.py | 9 | End-to-end pipeline + orchestrator |
| test_telegram_formatter.py | 17 | Telegram message formatting |
| **Total** | **170** | **169 unit + 1 integration, all passing** |

### Known Limitations & Future Work

1. **USD→ILS rate is hardcoded** — Should be fetched from an exchange rate API for production use
2. **No image display in React UI** — Listing images are stored but not rendered in cards yet
3. **No map view** — Latitude/longitude data is stored but no map component yet
4. **Facebook `doc_id` values may rotate** — May need updating if Facebook rotates their internal query IDs
5. **DB-level city filter uses English slugs** — Hebrew city names from Facebook don't match the DB `city.in_()` filter; the pipeline post-filter workaround avoids this, but a city normalization mapping in the DB layer would be a proper fix

---

## 16. Session 2: Facebook Integration & UI Improvements (2026-03-02)

This section covers the work done to bring Facebook Marketplace scraping from non-functional to fully operational, plus UI improvements for source-specific scraping.

### Step 21: Split Scraping UI

Separated the single "Scrape Now" button into source-specific panels because Yad2 and Facebook support different API-level filters.

**Changes:**
- `frontend/src/App.tsx` — Replaced single scrape button with tab-based `ScrapeTabSwitcher` component containing:
  - **ScrapeYad2Section**: City, price range (min/max), rooms range (min/max), "Scrape Yad2" button
  - **ScrapeFacebookSection**: City, price range (min/max), "Open browser for login" toggle, "Scrape Facebook" button
  - **DisplayFilters**: Unchanged — city, price, rooms, area, features checkboxes for DB-level filtering
- `frontend/src/api.ts` — New `ScrapeParams` interface with `source`, filter fields, and `headless` flag; 180s timeout for Facebook scrapes
- `frontend/src/App.css` — Tab styles (`.scrape-tab`, `.scrape-tab-yad2`, `.scrape-tab-facebook`), section styles
- `src/ui/api.py` — Added `min_price` and `headless` query parameters to `POST /api/scrape`

### Step 22: Visible Browser Mode for Facebook Login

Facebook requires authentication. Added a "visible browser" mode so users can log in manually on first use.

**Changes:**
- `src/ui/api.py` — `headless` query param (default `True`) passed to `FacebookPlaywrightScraper(headless=headless)`
- `frontend/src/App.tsx` — "Open browser for login" checkbox (default checked), helper text explaining the workflow
- `frontend/src/App.css` — `.browser-toggle` and `.helper-text` styles

### Step 23: Persistent Browser Profile

Rewrote `FacebookPlaywrightScraper` to use a persistent Chromium browser profile so login only needs to happen once.

**Key implementation (`src/scrapers/facebook/scraper.py`):**
```python
# Persistent context saves cookies/session to disk
context = pw.chromium.launch_persistent_context(
    user_data_dir="data/fb_profile/",
    headless=self._headless,
    locale="he-IL",
    viewport={"width": 1280, "height": 800},
)
```

**Methods added:**
- `_ensure_logged_in(page, timeout_seconds=120)` — Checks if saved session is valid; if not (and visible browser), waits for user to log in
- `_page_has_listings(page)` — Detects login state by checking URL patterns (`/login`, `/checkpoint`), login form presence, and positive marketplace element signals
- `_scrape_sync(search_filter)` — Sync Playwright implementation run via `asyncio.to_thread()` to avoid Windows `SelectorEventLoop` subprocess limitation

**User workflow:**
1. First run: Check "Open browser for login" → Chrome opens → log in to Facebook → session saved to `data/fb_profile/`
2. Subsequent runs: Uncheck "Open browser for login" → scrapes headless using saved session

### Step 24: Facebook Page Load Fix

Facebook Marketplace pages never reach Playwright's `networkidle` state because of continuous tracking pixel requests, WebSocket connections, and analytics pings.

**Fix:** Changed from `wait_until="networkidle"` to:
```python
page.goto(url, wait_until="domcontentloaded", timeout=30000)
page.wait_for_timeout(5000)  # Fixed 5s wait for JS rendering
```

### Step 25: Pipeline City Filter Fix

**Problem:** Facebook listings had Hebrew city names (e.g., `"חולון, TA"`) while the pipeline's `FilterEngine` compared against English slugs (e.g., `"herzliya"`). All Facebook listings were silently filtered out before being stored in the DB.

**Root cause:** In `pipeline/filter_engine.py`, `_matches()` checks `if listing_city not in f.cities: return False`. Scrapers use the city slug for API-level location lookup (mapping `"herzliya"` → location ID `107903829228927`), but the listings returned by Facebook contain the Hebrew city names from the source.

**Fix:** Added a `post_filter` parameter to `ScrapePipeline.run()` that separates concerns:
- `search_filter` (with city) → passed to scrapers for API-level location lookup
- `post_filter` (without city) → used by `FilterEngine` for in-memory filtering

In `src/ui/api.py`:
```python
search_filter = SearchFilter(cities=[city] if city else [], ...)
pipeline_filter = SearchFilter(min_price=min_price, max_price=max_price, ...)  # No cities
result = await pipeline.run(search_filter, post_filter=pipeline_filter)
```

### Step 26: End-to-End Verification

Ran real end-to-end scraping tests to verify the full pipeline:
- Facebook Playwright extracted **84 listings** from marketplace
- After normalization + deduplication: **51 unique listings**
- After price filtering: **43 listings stored** in the database
- Combined with **29 existing Yad2 listings** = **72 total** in the database
- React UI successfully displays listings from both sources with source badges

---

## 17. Lessons Learned

### 1. Always Probe for Internal APIs
The Yad2 JSON API was not documented anywhere in the existing scrapers we researched. All existing projects use `__NEXT_DATA__` parsing or Selenium. The JSON API is faster, more reliable, and has no anti-bot protection.

### 2. Anti-Bot on HTML ≠ Anti-Bot on API
Yad2's HTML pages have aggressive bot detection ("Are you for real"), but their internal JSON API endpoint has none. This is a common pattern — the anti-bot middleware is often only applied to HTML-serving routes.

### 3. Capture Real Data First, Write Parser Second
By fetching and saving a real API response before writing any parsing code, we could:
- Understand the actual field names and structure (94 fields!)
- Discover edge cases (items with `type: "innerRich"` that have no listing data)
- Write tests against real data shapes
- Avoid guessing at undocumented schemas

### 4. Hebrew Text Needs Special Handling on Windows
Python's default console encoding on Windows (cp1252) can't handle Hebrew characters. Always use `PYTHONIOENCODING=utf-8` or write to files.

### 5. Alembic Needs Manual Template Setup Without `alembic init`
If you create the `alembic/` directory manually (to have a custom `env.py`), you must also copy `script.py.mako` from Alembic's installed package.

### 6. httpx API Changes Between Versions
The `close()` → `aclose()` rename was a breaking change that caused test failures. Always check the exact API for the version you're using.

### 7. Feature Flags as Individual Columns Pays Off
Storing `has_parking`, `has_elevator`, etc. as individual boolean columns instead of a JSON blob makes database queries trivially efficient. The extra columns are worth the schema complexity.

### 8. Facebook Never Reaches `networkidle`
Playwright's `wait_until="networkidle"` waits for no network activity for 500ms. Facebook's tracking pixels, WebSocket connections, and analytics requests mean this never happens. Always use `domcontentloaded` with a fixed wait for rendering.

### 9. Persistent Browser Profiles Solve Session Management
Instead of trying to detect login state and manage cookies manually, using `launch_persistent_context(user_data_dir=...)` lets the browser handle session persistence natively. First run visible (user logs in), subsequent runs headless.

### 10. Separate Scraper Filters from Pipeline Post-Filters
When aggregating from multiple sources, scraper-level filters use source-specific naming (English slugs for API lookup) while the data returned uses source-native naming (Hebrew city names from Facebook). The pipeline's in-memory filter should not re-apply city filters that the scraper already handled — use a separate `post_filter` without city constraints.

### 11. Windows `SelectorEventLoop` Cannot Spawn Subprocesses
On Windows, Python's default `SelectorEventLoop` doesn't support `asyncio.create_subprocess_exec()`. Playwright's async API uses subprocesses internally. The fix is to use Playwright's **sync** API and run it in a thread via `asyncio.to_thread()`, which avoids the event loop limitation entirely.
