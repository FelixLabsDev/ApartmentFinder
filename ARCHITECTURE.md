# ApartmentFinder â€” Architecture Document

> **Version**: 1.1.1 | **Last Updated**: 2026-05-18

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
|| 2.7 | 2026-05-05 | Full-resolution image fetching for all sources: `Yad2ImageEnricher` class hits per-item API post-feed; Facebook detail enrichment uses response interception for CDN URLs; Madlan DOM fallback prefers `data-src`. |
|| 2.8 | 2026-05-05 | Single-URL Facebook import: `POST /api/scrape/url` endpoint scrapes one Marketplace listing by URL via Playwright + AI extraction + upsert. `ScrapeUrlSection` UI component added to the Facebook scrape tab. |
|| 2.9 | 2026-05-07 | LAN/phone access: Vite dev server bound to `0.0.0.0` (`host: true`); `API_BASE` in `api.ts` uses `window.location.hostname` dynamically; uvicorn started with `--host 0.0.0.0`. Both servers are now reachable from any device on the local network. |
|| 3.0 | 2026-05-07 | Maps button on listing cards: green "Maps" `<a>` added next to "View Listing" on each `ListingCard`. Uses lat/lng when available, falls back to a street+city search URL. Only rendered when the listing has sufficient location data. |
|| 4.0 | 2026-05-07 | Listing tags: `TagRow` table + `TagRepository`; 6 new REST endpoints; `useListingTags` hook with cycling color palette; `ListingCard` shows tag chips and a ðŸ· dropdown to assign/create tags inline. |
|| 4.0.1 | 2026-05-07 | Tag creation race condition fix: `createTag` is now async and awaits the backend before writing the listing-tag association. Color picker (8 swatches) added to the inline tag creation form; `onCreateTag` callback updated to `(name, color)`. |
|| 4.0.2 | 2026-05-08 | `ListingDetailModal` body restructured to a two-column layout: listing details on the left, tags + folders on the right. CSS classes `.modal-body-split`, `.modal-body-details`, `.modal-body-organizers` added. |
|| 4.0.3 | 2026-05-08 | Bug fixes: `useListingRatings` now seeds ratings immediately from listing data (`seedFromListings()`); migration code only clears localStorage after a successful API import; `ScrapeUrlSection` key format fixed from colon to hyphen; `fix_colon_keys()` added to `FolderRepository` and `TagRepository`, called at startup to repair existing bad keys in DB. |
|| 0.6.0 | 2026-05-08 | Global listing search: `search_query` field added to `SearchFilter`; `_apply_filter` applies it as an OR match across `source_url`, `title`, `description`, `street`, `neighborhood`, `city`, `contact_name`, `contact_phone`; `search_query` query param added to `GET /api/listings`; debounced search bar (400ms) added to React toolbar. |
|| 0.6.1 | 2026-05-08 | Bug fix: tag/folder dropdowns clipped by card `overflow: hidden`; set card to `overflow: visible`, moved `overflow: hidden` + border-radius to `.card-image-wrapper`; bumped dropdown `z-index` to 500. |
|| 0.6.2 | 2026-05-08 | Yad2 description enrichment: `Yad2ImageEnricher._fetch_item_data` now returns `(images, description)` tuple; `enrich()` overwrites `listing.description` with seller-written text extracted from per-item API; `_extract_description()` probes common field names at top level and under wrapper keys. No additional HTTP requests. |
|| 0.7.0 | 2026-05-08 | Priority Sort Panel: floating `PriorityPanel` in `App.tsx`; `likedFirst` toggle pins liked listings to the top; `priorityTags` ordered list promotes tag-matching listings within each tier. Toolbar button shows badge count of active rules. |
|| 0.7.3 | 2026-05-08 | Persisted UI state: new `usePersistedState` hook (localStorage-backed `useState` drop-in); six `Dashboard` state variables now persist across sessions (`af_filters`, `af_show_liked_only`, `af_view_mode`, `af_hide_disliked`, `af_prioritize_liked`, `af_tag_priority_ids`). |
|| 0.7.4 | 2026-05-08 | Bug fix: lightbox overlay and close button click events stopped from bubbling to the modal overlay; Escape key handler closes lightbox first if open, modal only if lightbox already closed. |
|| 0.8.4 | 2026-05-10 | WhatsApp integration: optional per-listing WhatsApp chat via Green API; `whatsapp_phone` column on `listings`; 4 new API endpoints; chat panel in `ListingDetailModal`; credentials via `GREEN_API_INSTANCE_ID` / `GREEN_API_TOKEN` env vars. |
|| 0.9.4 | 2026-05-12 | 5-tier quality rating system: `Rating` type `"1"`–`"5"` (Hard No → Perfect Match) replaces `"liked"`/`"disliked"`; `RATING_LEVELS` constant + `setRating(id, level)` replace `toggleLike`/`toggleDislike`; card border tinted per tier; Min Rating dropdown filter; Hide Hard Nos toolbar toggle; Rated First sort; backend accepts `"1"`–`"5"`; legacy DB/localStorage values auto-migrated; Compare view shown for ratings 4+. Rating UI refactored to a compact `RatingBadge` component (colored pill + popover) replacing the 5 inline buttons that crowded the card header. |
|| 0.9.5 | 2026-05-12 | Bug fix: CORS middleware changed from localhost whitelist to `allow_origins=["*"]` (`allow_credentials=False`) so LAN devices can reach the API. |
|| 1.0.0 | 2026-05-13 | Hide by Status/Tag filtering: "Hide Hard Nos" toolbar checkbox replaced with multi-select "Hide by Status" (per rating tier) and "Hide by Tag" (per user tag) sections in the Filters sidebar. State persisted as `af_hidden_ratings` (default `["1"]`) and `af_hidden_tag_ids` (default `[]`). |
|| 1.0.1 | 2026-05-13 | Prev/Next navigation in listing detail modal: navigation row added at modal bottom; `selectedListingIdx` derived from `displayListings`; `openListing` helper centralises modal-open + mark-seen logic. Balcony feature tag fix: Yad2 `_parse_features` now falls back to bare numeric field (e.g. `"Porch"`) when `_text` variant is absent; Madlan parser extended with additional `has_balcony` field aliases (`porches`, `porch`, `balconyArea`, `porchArea`). |
|| 1.1.0 | 2026-05-13 | Listing update detection: `content_updated_at` column on `listings`; `upsert_listings` returns `(total, new, updated)` 3-tuple; `_detect_changes` compares all scraped fields; changed listings get `content_updated_at` set and an auto-inserted `[Update]` system note; purple UPDATED badge on listing cards (clears on open, same as NEW badge); `ScrapeResponse` exposes `updated_listings` count. |

---

## System Overview

ApartmentFinder aggregates apartment rental listings from **Yad2** (Israel's largest classifieds site), **Facebook Marketplace**, and **Madlan.co.il**, normalizes them into a unified format, deduplicates across sources, and stores them in a local SQLite database. Users interact via a React dashboard or CLI. Telegram notifications alert on new matches. None of these platforms have an official API â€” all data access is reverse-engineered.

---

## Architecture Diagram

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        ApartmentFinder                          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚  Yad2     â”‚  â”‚  Facebook Marketplace â”‚  â”‚  Madlan.co.il   â”‚ â”‚
â”‚  â”‚  API      â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚ â”‚
â”‚  â”‚  Scraper  â”‚  â”‚  â”‚ GraphQL (auth) â”‚  â”‚  â”‚  â”‚ Playwright â”‚  â”‚ â”‚
â”‚  â”‚           â”‚  â”‚  â”‚     â†“ fallback â”‚  â”‚  â”‚  â”‚ (intercept â”‚  â”‚ â”‚
â”‚  â”‚           â”‚  â”‚  â”‚ Playwright     â”‚  â”‚  â”‚  â”‚  XHR +     â”‚  â”‚ â”‚
â”‚  â”‚           â”‚  â”‚  â”‚ (persistent    â”‚  â”‚  â”‚  â”‚  DOM       â”‚  â”‚ â”‚
â”‚  â”‚           â”‚  â”‚  â”‚  browser)      â”‚  â”‚  â”‚  â”‚  fallback) â”‚  â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚ â”‚
â”‚        â”‚                  â”‚               â”‚       â”‚           â”‚ â”‚
â”‚        â–¼                  â–¼               â”‚       â–¼           â”‚ â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚                   ScraperOrchestrator                     â”‚ â”‚
â”‚  â”‚      (fallback chain per source: try â†’ skip)             â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                          â”‚                                     â”‚
â”‚                          â–¼                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚                    ScrapePipeline                         â”‚ â”‚
â”‚  â”‚  1. Normalize (Hebrew cities, USDâ†’ILS, phones)           â”‚ â”‚
â”‚  â”‚  2. AI Enrich (Facebook listings w/ description)         â”‚ â”‚
â”‚  â”‚  3. Deduplicate (SHA256 fingerprint)                     â”‚ â”‚
â”‚  â”‚  4. Filter (post_filter â€” no city constraint)            â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                          â”‚                                     â”‚
â”‚                          â–¼                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚             Database (SQLite + SQLAlchemy)                â”‚ â”‚
â”‚  â”‚      listings | search_profiles | scrape_runs            â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                          â”‚                                     â”‚
â”‚          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                    â”‚
â”‚          â–¼               â–¼               â–¼                    â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”              â”‚
â”‚  â”‚  Typer CLI   â”‚ â”‚ React UI â”‚ â”‚  Telegram    â”‚              â”‚
â”‚  â”‚              â”‚ â”‚ + FastAPIâ”‚ â”‚  Notifier    â”‚              â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜              â”‚
â”‚                                                                â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Data Flow

A scrape cycle goes through these steps:

```
1. User triggers scrape (React UI button or CLI command)
2. API creates SearchFilter with city + price + rooms
3. ScraperOrchestrator dispatches to registered scrapers with fallback chains
4. Scraper fetches data:
   - Yad2: REST API â†’ Yad2Parser â†’ Yad2ImageEnricher (per-item API for full-res images + description) â†’ list[ListingCreate]
   - Facebook: GraphQL (if cookies) â†’ Playwright fallback â†’ _extract_listing_cards() â†’ _enrich_from_detail_page() â†’ FacebookParser â†’ list[ListingCreate]
   - Madlan: Playwright â†’ intercept XHR/API responses â†’ MadlanParser.parse_api_listing() per result; falls back to _extract_listing_cards() (DOM) â†’ MadlanParser.parse_dom_listing() if interception yields nothing
5. ListingNormalizer: Hebrew city â†’ English slug, USD â†’ ILS, phone â†’ +972 format
6. AI Enrichment: for each Facebook listing with a description > 30 chars, calls extract_listing_fields() to fill missing structured fields (price, rooms, city, features, etc.) â€” additive only, never overwrites existing values
7. ListingDeduplicator: SHA256 fingerprint on city|street|rooms|floor|price_bucket (runs after AI enrichment so AI-filled fields improve fingerprint accuracy)
8. FilterEngine: applies post_filter (price/rooms only â€” no city, to avoid name mismatches)
9. ListingRepository: upserts to SQLite (INSERT ON CONFLICT UPDATE)
10. React UI fetches /api/listings with display filters â†’ renders listing cards
```

---

## Component Reference

### Scrapers

| Component | File | Description |
|-----------|------|-------------|
| `BaseScraper` | `src/scrapers/base.py` | Abstract class: `scrape(SearchFilter) â†’ list[ListingCreate]`, `health_check() â†’ bool` |
| `ScraperHttpClient` | `src/scrapers/http_client.py` | Shared HTTP client with randomized User-Agent, exponential retry, anti-bot headers, optional proxy |
| `ScraperOrchestrator` | `src/scrapers/orchestrator.py` | Registers scrapers per source with fallback chains; `scrape_all()` tries each in order |
| `Yad2ApiScraper` | `src/scrapers/yad2/scraper.py` | Hits Yad2's internal JSON API; paginated; supports city, price, rooms filters. After feed collection, runs `Yad2ImageEnricher` to replace preview URLs with full-res ones via per-item API. |
| `Yad2ImageEnricher` | `src/scrapers/yad2/scraper.py` | Post-feed enricher: tries two `ITEM_API_URLS` endpoint templates per listing token. `_fetch_item_data()` returns a `(images, description)` tuple. `enrich()` replaces `image_urls` with full-res CDN URLs and overwrites `listing.description` with the seller-written text via `_extract_description()` (probes `info_text`, `description`, `text`, `body`, `details` at top level and under `data`/`item`/`ad` wrapper keys). Falls back to feed preview URLs/description on any per-listing failure. No extra HTTP requests beyond the existing per-item call. |
| `Yad2Parser` | `src/scrapers/yad2/parser.py` | Parses Yad2 JSON response (94 fields per listing) into `ListingCreate` |
| `FacebookGraphQLScraper` | `src/scrapers/facebook/scraper.py` | POST to `/api/graphql/` with doc_id rotation; needs cookies + LSD token |
| `FacebookPlaywrightScraper` | `src/scrapers/facebook/scraper.py` | Browser automation with persistent profile at `data/fb_profile/`; sync API via `asyncio.to_thread()`. After extracting search-result cards, calls `_enrich_from_detail_page()` per card to visit the listing detail page and replace the preview thumbnail + title stub with full images and the longest description block (> 50 chars). Image collection uses a response event listener (registered before page.goto(), removed in finally) to intercept CDN URLs (scontent/fbcdn, content-type image/*); falls back to DOM img.src scraping (naturalWidth >= 150) if interception yields nothing. Rate-limited to 1.5s between detail page loads. |
| `FacebookParser` | `src/scrapers/facebook/parser.py` | Parses GraphQL responses and HTML card data into `ListingCreate` |
| `MadlanPlaywrightScraper` | `src/scrapers/madlan/scraper.py` | Browser automation with persistent profile at `data/madlan_profile/`; sync API via `asyncio.to_thread()`. Registers a `response` listener to intercept XHR/API calls and capture structured listing JSON. Falls back to `_extract_listing_cards()` (DOM parsing) if interception yields nothing. Scrolls 6 times with 2.5 s pauses to trigger lazy-loading. Source-level deduplication by `source_id` before returning. |
| `MadlanParser` | `src/scrapers/madlan/parser.py` | Dual-mode parser: `parse_api_listing()` for structured JSON (handles multiple field-name variants); `parse_dom_listing()` for card dicts from DOM extraction. Maps Hebrew property type names to `PropertyType` enum. |

**Yad2 API-level filters**: city, min_price, max_price, min_rooms, max_rooms
**Facebook API-level filters**: city (via location ID), min_price, max_price
**Madlan API-level filters**: city (Hebrew term + bounding box), min_price, max_price, min_rooms, max_rooms, min_area_sqm, max_area_sqm, min_floor, max_floor

### Pipeline

| Component | File | Description |
|-----------|------|-------------|
| `ListingNormalizer` | `src/pipeline/normalizer.py` | 60+ Hebrewâ†’English city mappings, USDâ†’ILS at 3.7 rate, phone normalization to +972 format |
| `ListingDeduplicator` | `src/pipeline/deduplicator.py` | SHA256 fingerprint on `city\|street\|house_number\|rooms\|floor\|price_bucket` (200 ILS tolerance). Keeps listing with highest completeness score. |
| `FilterEngine` | `src/pipeline/filter_engine.py` | Static `apply()` method: filters by price, rooms, area, floor, property type, features, keywords |
| `ScrapePipeline` | `src/pipeline/pipeline.py` | Orchestrates scrape â†’ normalize â†’ AI enrich â†’ deduplicate â†’ filter. Accepts `post_filter` to separate scraper filters from pipeline filters. `_ai_enrich_facebook()` static async method runs `extract_listing_fields()` on each Facebook listing with a description longer than 30 characters; fills only null/missing fields; sets `ai_guessed_fields`; per-listing failures are caught and logged without aborting the pipeline. |

### Database

| Component | File | Description |
|-----------|------|-------------|
| `engine.py` | `src/db/engine.py` | SQLAlchemy async engine factory (aiosqlite for SQLite) |
| `tables.py` | `src/db/tables.py` | ORM models: `ListingRow` (40+ columns + `whatsapp_phone` + `content_updated_at`, 4 indexes), `SearchProfileRow`, `ScrapeRunRow`, `TagRow` |
| `repository.py` | `src/db/repository.py` | `ListingRepository` (upsert returns `(total, new_count, updated_count)` 3-tuple; `_detect_changes` compares incoming vs stored fields and returns a diff string; query with filters incl. `search_query` OR match; `get_listing()`; `set_whatsapp_phone()`), `SearchProfileRepository`, `ScrapeRunRepository`, `TagRepository` (get_all, create, rename, delete, add_listing, remove_listing), `FolderRepository`. Both `TagRepository` and `FolderRepository` expose a `fix_colon_keys()` method that rewrites `source:source_id` (colon) keys in `listing_ids` JSON columns to the canonical `source-source_id` (hyphen) format — called at API startup. |

**Tables**: `listings` (unique on source+source_id, fingerprint index; `whatsapp_phone` and `content_updated_at` added via startup migration), `search_profiles`, `scrape_runs`, `tags` (auto-created at API startup via `create_all` â€” not managed by Alembic)
**Migrations**: Alembic (`alembic/versions/0c933bf8a865_initial.py`)

### API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/listings` | GET | Filtered listings from DB (city, price, rooms, area, features, `search_query`, pagination). `search_query` performs OR match across source URL, title, description, street, neighborhood, city, contact name, and contact phone. |
| `/api/scrape` | POST | Trigger on-demand scrape (source, city, price, rooms, headless) |
| `/api/stats` | GET | Summary: total listings, sources, cities |
| `/api/health` | GET | Source connectivity check |
| `/api/listings/{source}/{source_id}/ai-extract` | POST | Rescrape a Facebook listing via Playwright, run AI field extraction, update and return the listing. Only meaningful for Facebook source. |
| `/api/scrape/url` | POST | Accept `{ url: string }`, scrape a single Facebook Marketplace listing URL via Playwright, run AI field extraction, upsert to DB, return `{ status, message, listing }`. |
| `/api/tags` | GET | Return all tags. |
| `/api/tags` | POST | Create a new tag (`name`, `color`). |
| `/api/tags/{id}/name` | PUT | Rename a tag. |
| `/api/tags/{id}` | DELETE | Delete a tag and remove it from all listings. |
| `/api/tags/{id}/listings` | POST | Add a listing UUID to a tag. |
| `/api/tags/{id}/listings/{listing_id}` | DELETE | Remove a listing from a tag. |
| `/api/listings/{id}/whatsapp-phone` | PUT | Associate a WhatsApp phone number with a listing (stored in whatsapp_phone column). |
| `/api/listings/{id}/whatsapp-phone` | DELETE | Clear the WhatsApp phone association for a listing. |
| `/api/listings/{id}/whatsapp/history` | GET | Fetch chat history from Green API for the listing's associated phone number. |
| `/api/listings/{id}/whatsapp/send` | POST | Send a WhatsApp message via Green API to the listing's associated phone number. |

**File**: `src/ui/api.py` â€” FastAPI with CORS for React dev server (port 3000). Must be started with `--host 0.0.0.0` for LAN access.

The `/api/scrape` endpoint creates two filters:
- `search_filter` (with city) â†’ passed to scrapers for API-level location lookup
- `pipeline_filter` (without city) â†’ used by FilterEngine to avoid Hebrewâ†”English name mismatches

### Frontend

**Stack**: React 18, TypeScript, Vite, TanStack React Query, Axios. Vite dev server is configured with `host: true` (binds `0.0.0.0`, port 3000) for LAN access. `API_BASE` in `api.ts` uses `window.location.hostname` dynamically so API calls work correctly from any device on the network.

| Component | File | Description |
|-----------|------|-------------|
| `ScrapeTabSwitcher` | `frontend/src/App.tsx` | Tab switcher between Yad2 and Facebook scrape panels |
| `ScrapeYad2Section` | `frontend/src/App.tsx` | City, price range, rooms range, "Scrape Yad2" button |
| `ScrapeFacebookSection` | `frontend/src/App.tsx` | City, price range, browser toggle, "Scrape Facebook" button |
| `ScrapeUrlSection` | `frontend/src/components/ScrapePanel.tsx` | URL text input + folder selector + "Import Listing" button; rendered at top of Facebook scrape tab. Calls `POST /api/scrape/url` to import a single Marketplace listing by URL. Scrape result alerts display new and updated listing counts. |
| `DisplayFilters` | `frontend/src/components/DisplayFilters.tsx` | City, price, rooms, area, feature checkboxes, "Min Rating" dropdown (`"1"`–`"5"` or unset), "Hide by Status" checkboxes (one per rating tier 1–5), and "Hide by Tag" checkboxes (one per user-created tag). DB-query filters forwarded to API; hide filters applied client-side in App.tsx. |
| `RatingBadge` | `frontend/src/components/RatingBadge.tsx` | Shared rating control. Renders a single colored pill (`.rating-badge`) showing the active tier label, or "★ Rate" when unrated. Clicking opens a popover (`.rating-popover`) listing all 5 tiers; the active tier is highlighted, clicking it again clears the rating. Accepts a `large` boolean prop for slightly bigger sizing. Used by both `ListingCard` and `ListingDetailModal`. |
| `ListingCard` | `frontend/src/components/ListingCard.tsx` | Price, location, features, description, source badge. Contains `ImageCarousel` wrapped in `.card-image-wrapper`; "NEW" badge (orange, `isUnseen`) and "UPDATED" badge (purple, `isUpdated`) are absolutely positioned over the image (top-right corner, z-index 2). Applies `.listing-updated` CSS class (purple border) when `isUpdated` (`content_updated_at` set and not yet seen). "View Listing" is a `<button>` that calls `onOpenDetail` to open the in-app detail modal (not a direct external link). A green "Maps" `<a>` button is shown next to "View Listing" when the listing has lat/lng or at least street+city; links to `https://www.google.com/maps?q={lat},{lng}` when coordinates are present, otherwise falls back to a `https://www.google.com/maps/search/` street+city query. Tag chips are rendered to the right of the card title; a ðŸ· button opens a dropdown to assign/unassign existing tags or create new ones inline (name input + 8-color swatch picker; Enter or `+` submits). A `<RatingBadge>` pill shows the current rating tier; clicking opens the tier popover. Card border is tinted per tier (red for 1 through green for 5). |
| `ListingDetailModal` | `frontend/src/components/ListingDetailModal.tsx` | Full listing detail overlay. Modal body uses a two-column layout (`.modal-body-split`): left column (`.modal-body-details`) holds the info grid, features, description, and contact; right column (`.modal-body-organizers`) stacks tags above folders. Contact section has a "View on {source}" external link and, when lat/lng are present, an "Open on Google Maps" button. For Facebook listings, also shows an "AI Extract Fields" button (purple) that calls `POST /api/listings/{source}/{source_id}/ai-extract`, shows loading/error state inline, and invokes `onListingUpdated` prop on success. A chat-bubble button toggles a WhatsApp panel: the user enters/saves a phone number (with country code), views chat history fetched from Green API, and sends messages â€” all without leaving the modal. Chat history is refreshed on every modal open. A `<RatingBadge large>` is shown at the top of the modal for quick tier assignment. A `.modal-listing-nav-row` at the bottom shows "← Previous" / "Next →" buttons (optional `onPrev`/`onNext` props); disabled at boundary listings. |
| `MapView` | `frontend/src/components/MapView.tsx` | Map view of listings. `MapPreviewSidebar` shows a selected listing's details with a "View Details" button and, when lat/lng are present, an "Open on Google Maps" button. |
| `StatsBar` | `frontend/src/App.tsx` | Total listings, sources, cities |
| `SearchBar` | `frontend/src/App.tsx` | Debounced text input (400ms) in the toolbar; sets `search_query` to OR-match across source URL, title, description, street, neighborhood, city, contact name, and contact phone. |
| `api.ts` | `frontend/src/api.ts` | Axios client: `fetchListings` (includes `search_query` param), `triggerScrape` (returns `ScrapeResult` with `updated_listings` count), `fetchStats`, `fetchHealth`, `aiExtractListing` (120s timeout), `scrapeListingUrl` (`ScrapeUrlResult` interface), `fetchTags`, `createTagApi`, `renameTagApi`, `deleteTagApi`, `addListingToTagApi`, `removeFromTagApi`, `setWhatsappPhone`, `deleteWhatsappPhone`, `getWhatsappHistory`, `sendWhatsappMessage` (`WhatsappMessage` interface). `Listing` interface includes `content_updated_at: string | null`. |
| `useListingTags` | `frontend/src/hooks/useListingTags.ts` | Hook managing all tag state: fetches tags, exposes mutations (add, remove, create, rename, delete). `createTag` is async â€” awaits `createTagApi` before calling `addToTag` to prevent a race condition where the tag row didn't exist yet. Accepts `(name, color)` so callers supply the color explicitly. |
| `useListingRatings` | `frontend/src/hooks/useListingRatings.ts` | Hook managing listing rating state. Exports `RATING_LEVELS` constant (5-tier metadata: label, color, symbol for levels 1–5). Exposes `setRating(id, level)` replacing the legacy `toggleLike`/`toggleDislike` API. Seeds ratings from `listing.rating` immediately on fetch via `seedFromListings()`; supplements with `GET /api/ratings` to cover off-screen listings. Auto-migrates legacy localStorage values (`"liked"`→`"4"`, `"disliked"`→`"1"`) on startup before any API call. |
| `usePersistedState` | `frontend/src/hooks/usePersistedState.ts` | Drop-in replacement for `useState<T>` that serializes state to `localStorage` under a given key on every update and restores it on mount. Used in `Dashboard` for filter criteria, view mode, and sort toggles. |

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
**Problem**: Yad2 uses English city slugs ("herzliya") for API lookups. Facebook returns Hebrew city names ("×”×¨×¦×œ×™×”, M"). The pipeline's `FilterEngine` compared listing cities against filter cities â€” all Facebook listings were silently filtered out.
**Solution**: `ScrapePipeline.run()` accepts a separate `post_filter` parameter. The API endpoint passes `search_filter` (with city) to scrapers and `pipeline_filter` (without city) to the filter engine.

### Facebook Playwright Detail Page Enrichment (v2.2, updated v2.7)
**Problem**: Search result cards on Facebook Marketplace only expose a single preview thumbnail and the listing title; descriptions were placeholder stubs and multi-image listings showed only one low-resolution image.
**Solution**: After \_extract_listing_cards()\ builds the initial card list, \_enrich_from_detail_page()\ navigates to each listing's \/marketplace/item/{id}/\ page. A esponse\ event listener (registered before \page.goto()\, removed in \inally\) intercepts CDN image responses matching \scontent\/\bcdn\ with \content-type: image/*\ to collect full-res URLs. Falls back to DOM \img.src\ scraping filtered to aturalWidth >= 150\ if interception yields nothing. The description is extracted by trying three CSS selectors in order and keeping the longest text block over 50 characters. The method mutates \card_data\ in place; if the detail fetch fails, the card falls through to parsing with its original preview data.

### domcontentloaded vs networkidle (v2.0)
**Problem**: `page.goto(url, wait_until="networkidle")` timed out on Facebook because tracking pixels, WebSockets, and analytics requests never stop.
**Solution**: Use `wait_until="domcontentloaded"` + `page.wait_for_timeout(5000)` for consistent loading.

### Madlan Network Interception Strategy (v2.6)
**Problem**: Madlan.co.il returns HTTP 403 to all direct HTTP clients. No public API exists and there is no GraphQL endpoint to reverse-engineer.
**Solution**: Use Playwright to load the search page as a real browser. A `response` listener captures all JSON responses from URLs matching `/api/`, `/graphql`, or `listings`. A recursive `_extract_listings_from_api()` traversal plus a heuristic `_is_listing_object()` check identify listing dicts regardless of nesting depth or GraphQL edge patterns. If no API data is captured (e.g., due to a site update), the scraper falls back to DOM extraction of rendered listing cards.

### Madlan URL Filter Encoding (v2.6)
**Problem**: Madlan does not accept individual query parameters for price, rooms, area, and floor. All filter state is encoded in a single opaque `filters` parameter.
**Solution**: Discovered by browser observation that Madlan uses a positional underscore-delimited string: `_{price_min}-{price_max}_{rooms_min}-{rooms_max}_{7 empty}_{area_min}-{area_max}_{empty}_{floor_min}-{floor_max}_{7 empty}_search-filter-top-bar`. `_build_filter_string()` constructs this format from `SearchFilter` fields.

### Yad2 Full-Resolution Image + Description Enrichment (v2.7, extended v0.6.2)
**Problem**: The Yad2 feed API only returns CDN preview/thumbnail URLs and populates description from a search-index blob (search_text), not the seller-written text.
**Solution**: Yad2ImageEnricher runs after Yad2ApiScraper finishes feed pagination. _fetch_item_data() calls the per-item API and returns a (images, description) tuple. enrich() replaces image_urls in-place with full-res URLs and overwrites listing.description with the real seller text extracted by _extract_description() (probes info_text, description, 	ext, ody, details at top level and under data/item/d wrapper keys). No additional HTTP requests. Any per-listing failure falls back silently to feed preview URLs and the original description.

### Yad2 Internal JSON API (v1.0)
**Problem**: All known Yad2 scrapers use `__NEXT_DATA__` parsing or Selenium, both of which trigger Yad2's anti-bot protection.
**Solution**: Discovered an unprotected internal API at `https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/rent` that returns structured JSON with 94 fields per listing, no anti-bot, and native filter support.

### Individual Boolean Columns for Features (v1.0)
Storing `has_parking`, `has_elevator`, `has_balcony`, etc. as individual columns (not a JSON blob) enables efficient SQL WHERE clauses for feature filtering.


### Ratings Single Source of Truth (v4.0.3)
**Problem**: Ratings were painted only after a dedicated `GET /api/ratings` call, causing a visible delay where ratings appeared empty even though listing objects already carried their `rating` field from the DB.
**Solution**: `useListingRatings.seedFromListings()` is called on every listing fetch to immediately populate ratings from the already-present `listing.rating` values. The full `GET /api/ratings` call is kept to cover off-screen paginated listings not yet rendered. DB is the authoritative source; listing objects are the fast path; the ratings API call is the completeness sweep.

In v0.9.4 the binary `"liked"`/`"disliked"` type was replaced with a 5-tier string enum `"1"`–`"5"`. `RATING_LEVELS` (exported from `useListingRatings`) is the single source of truth for tier metadata. Legacy DB and localStorage values are auto-migrated on first access; no manual migration step is required.

### Canonical Listing Key Format (v4.0.3)
### Listing Update Detection (v1.1.0)
**Problem**: Re-scraping an existing listing silently overwrote changed fields (price, photos, description) with no record of what changed and no way to alert the user.
**Solution**: `_detect_changes()` in `ListingRepository` compares all scraped fields between the incoming `ListingCreate` and the stored `ListingRow`. When differences are found: `content_updated_at` is set to now; a `NoteRow` with an `[Update]` prefix is auto-inserted describing what changed (e.g. `[Update] Price: ₪5,000 → ₪4,800 | 2 new photo(s) added`). The `ListingCard` shows a purple UPDATED badge (`.updated-badge`) when `content_updated_at` is set and `seen_at` is null — cleared the same way as the NEW badge when the user opens the listing. User state (rating, tags, folders, notes, WhatsApp phone) is always preserved across re-scrapes.


**Problem**: `ScrapeUrlSection` was building keys as `source:source_id` (colon) while the rest of the system uses `source-source_id` (hyphen), causing folder/tag associations for URL-imported listings to never resolve. Some previously saved DB rows also contained colon-format keys.
**Solution**: Fixed the key format in `ScrapeUrlSection`. Added `fix_colon_keys()` to `FolderRepository` and `TagRepository`, called idempotently at API startup to repair any existing colon-format keys in the DB.
---

## Configuration

### Environment Variables (`.env`)

```env
# Database
DATABASE_PATH=data/apartmentfinder.db

# Facebook (optional â€” for GraphQL scraper)
FB_COOKIES=                 # JSON string of cookie dict
FB_LSD_TOKEN=               # LSD token from Facebook page

# Telegram notifications
TELEGRAM_BOT_TOKEN=         # From @BotFather
TELEGRAM_CHAT_ID=           # Your chat/group ID

# Scheduler
SCRAPE_INTERVAL_MINUTES=30  # How often to scrape

# Optional proxy
PROXY_URL=                  # HTTP/SOCKS proxy for scraping

# WhatsApp integration (optional â€” via Green API)
GREEN_API_INSTANCE_ID=      # Green API instance ID
GREEN_API_TOKEN=            # Green API token
```

### Facebook Auth Setup

1. In the React UI, switch to the **Facebook** tab
2. Check **"Open browser for login"**
3. Click **"Scrape Facebook"** â€” Chrome opens
4. Log in to Facebook â€” scraping starts automatically
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
- All unit tests use mocked HTTP (pytest-httpx) â€” no network calls
- In-memory SQLite per test â€” no file I/O
- Fixture-based: real API responses captured as JSON files
- Integration tests marked with `@pytest.mark.integration`, excluded by default

```bash
# Unit tests only
uv run pytest tests/ -m "not integration" -v

# All tests including integration
uv run pytest tests/ -v
```


