from __future__ import annotations

import json
import logging
import re
import time
from urllib.parse import quote, urlencode

from src.models.filters import SearchFilter
from src.models.listing import ListingCreate
from src.scrapers.base import BaseScraper

from .config import CITY_BBOXES, CITY_SEARCH_TERMS, SEARCH_BASE_URL
from .parser import MadlanParser

logger = logging.getLogger(__name__)


class MadlanPlaywrightScraper(BaseScraper):
    """Scrape Madlan.co.il listings using Playwright browser automation.

    Madlan blocks direct HTTP clients (returns 403), so we use a headless
    browser to load the search page and extract listing data.

    Strategy:
    1. Intercept XHR/fetch requests to capture raw API responses.
    2. Fall back to DOM extraction from rendered listing cards.

    Uses the sync Playwright API in a thread to avoid Windows event loop issues.
    """

    PROFILE_DIR = "data/madlan_profile"

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._parser = MadlanParser()

    @property
    def source_name(self) -> str:
        return "madlan"

    @property
    def method_name(self) -> str:
        return "playwright"

    async def scrape(self, search_filter: SearchFilter) -> list[ListingCreate]:
        """Scrape Madlan via browser automation (runs in thread)."""
        import asyncio
        return await asyncio.to_thread(self._scrape_sync, search_filter)

    def _scrape_sync(self, search_filter: SearchFilter) -> list[ListingCreate]:
        """Sync scrape implementation that runs in a worker thread."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright not installed — run: playwright install chromium")
            return []

        from pathlib import Path
        profile_path = str(Path(self.PROFILE_DIR).resolve())
        Path(profile_path).mkdir(parents=True, exist_ok=True)

        all_listings: list[ListingCreate] = []
        cities = search_filter.cities or ["tel-aviv"]

        pw = sync_playwright().start()
        try:
            context = pw.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=self._headless,
                locale="he-IL",
                viewport={"width": 1280, "height": 900},
            )
            page = context.pages[0] if context.pages else context.new_page()

            for city in cities:
                url = self._build_search_url(search_filter, city)
                logger.info("Madlan Playwright: navigating to %s", url)

                # Collect API responses via network interception
                intercepted_listings: list[dict] = []

                def on_response(response):
                    """Capture API responses that contain listing data."""
                    try:
                        url_str = response.url
                        # Madlan uses various API endpoints; capture JSON responses
                        # that look like listing data
                        if response.status == 200 and (
                            "/api/" in url_str
                            or "/graphql" in url_str
                            or "listings" in url_str
                        ):
                            content_type = response.headers.get("content-type", "")
                            if "json" in content_type or "javascript" in content_type:
                                try:
                                    body = response.json()
                                    self._extract_listings_from_api(body, intercepted_listings)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                page.on("response", on_response)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(5000)
                except Exception as exc:
                    logger.error("Madlan: failed to load %s: %s", url, exc)
                    continue

                # Scroll to load more listings
                for scroll_round in range(6):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2500)

                logger.info(
                    "Madlan: intercepted %d listings from API calls for city %s",
                    len(intercepted_listings), city,
                )

                # Try API-intercepted data first
                if intercepted_listings:
                    for raw in intercepted_listings:
                        listing = self._parser.parse_api_listing(raw)
                        if listing:
                            all_listings.append(listing)
                else:
                    # Fall back to DOM extraction
                    logger.info("Madlan: no API data intercepted, falling back to DOM extraction")
                    cards = self._extract_listing_cards(page)
                    logger.info("Madlan: extracted %d listing cards from DOM for city %s", len(cards), city)
                    for card_data in cards:
                        listing = self._parser.parse_dom_listing(card_data)
                        if listing:
                            all_listings.append(listing)

                page.remove_listener("response", on_response)

        except Exception as exc:
            logger.error("Madlan Playwright scrape error: %s", exc, exc_info=True)
        finally:
            logger.info("Madlan Playwright: terminating browser...")
            self._force_kill_playwright(pw)

        # Deduplicate by source_id (same listing may appear in multiple API calls)
        seen_ids: set[str] = set()
        unique: list[ListingCreate] = []
        for listing in all_listings:
            if listing.source_id not in seen_ids:
                seen_ids.add(listing.source_id)
                unique.append(listing)

        logger.info("Madlan Playwright: scraped %d unique listings total", len(unique))
        return unique

    async def health_check(self) -> bool:
        """Check if Playwright can load Madlan."""
        import asyncio
        try:
            return await asyncio.to_thread(self._health_check_sync)
        except Exception:
            return False

    def _health_check_sync(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return False

        from pathlib import Path
        profile_path = str(Path(self.PROFILE_DIR).resolve())
        Path(profile_path).mkdir(parents=True, exist_ok=True)

        pw = sync_playwright().start()
        try:
            context = pw.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=True,
                viewport={"width": 1280, "height": 900},
            )
            page = context.pages[0] if context.pages else context.new_page()
            response = page.goto(
                SEARCH_BASE_URL + "?dealType=rent",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            ok = response is not None and response.status == 200
            return ok
        except Exception:
            return False
        finally:
            self._force_kill_playwright(pw)

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------

    def _build_search_url(self, search_filter: SearchFilter, city: str) -> str:
        """Build a Madlan search URL with filters encoded in the URL.

        Madlan URL format:
        /listings?dealType=rent&term={hebrew_city}&bbox={bbox}&filters={filter_string}
        """
        params: dict[str, str] = {"dealType": "rent"}

        # City / location term
        term = CITY_SEARCH_TERMS.get(city.lower(), city)
        params["term"] = term

        # Bounding box
        bbox = CITY_BBOXES.get(city.lower())
        if bbox:
            params["bbox"] = bbox

        # Build filter string
        filter_str = self._build_filter_string(search_filter)
        if filter_str:
            params["filters"] = filter_str

        return SEARCH_BASE_URL + "?" + urlencode(params, quote_via=quote)

    def _build_filter_string(self, search_filter: SearchFilter) -> str:
        """Build the Madlan filter string.

        Madlan encodes filters as a positional underscore-separated string:
        _{price_range}_{rooms_range}_{property_types}_______{area_range}__{floor_range}_______search-filter-top-bar

        We build the full positional format to match Madlan's expectations.
        """
        parts: list[str] = []

        # Position 0: empty (leading underscore)
        parts.append("")

        # Position 1: price range (e.g., "1750-6000")
        if search_filter.min_price is not None or search_filter.max_price is not None:
            min_p = str(int(search_filter.min_price)) if search_filter.min_price else ""
            max_p = str(int(search_filter.max_price)) if search_filter.max_price else ""
            parts.append(f"{min_p}-{max_p}")
        else:
            parts.append("")

        # Position 2: rooms range (e.g., "3-6")
        if search_filter.min_rooms is not None or search_filter.max_rooms is not None:
            min_r = str(int(search_filter.min_rooms)) if search_filter.min_rooms else ""
            max_r = str(int(search_filter.max_rooms)) if search_filter.max_rooms else ""
            parts.append(f"{min_r}-{max_r}")
        else:
            parts.append("")

        # Positions 3-9: empty placeholders (property types, other filters)
        for _ in range(7):
            parts.append("")

        # Position 10: area range (e.g., "80-")
        if search_filter.min_area_sqm is not None or search_filter.max_area_sqm is not None:
            min_a = str(int(search_filter.min_area_sqm)) if search_filter.min_area_sqm else ""
            max_a = str(int(search_filter.max_area_sqm)) if search_filter.max_area_sqm else ""
            parts.append(f"{min_a}-{max_a}")
        else:
            parts.append("")

        # Position 11: empty
        parts.append("")

        # Position 12: floor range (e.g., "0-10000" for any)
        if search_filter.min_floor is not None or search_filter.max_floor is not None:
            min_f = str(search_filter.min_floor) if search_filter.min_floor is not None else "0"
            max_f = str(search_filter.max_floor) if search_filter.max_floor is not None else "10000"
            parts.append(f"{min_f}-{max_f}")
        else:
            parts.append("")

        # Remaining positions: empty + tracking tag
        for _ in range(7):
            parts.append("")
        parts.append("search-filter-top-bar")

        return "_".join(parts)

    # ------------------------------------------------------------------
    # API interception
    # ------------------------------------------------------------------

    def _extract_listings_from_api(self, body: dict | list, out: list[dict]) -> None:
        """Recursively extract listing objects from an API response.

        Madlan's API may return listings in various nested structures.
        We search for objects that look like listing data.
        """
        if isinstance(body, list):
            for item in body:
                if isinstance(item, dict):
                    self._extract_listings_from_api(item, out)
            return

        if not isinstance(body, dict):
            return

        # Check if this object looks like a listing
        if self._is_listing_object(body):
            out.append(body)
            return

        # Recursively search in nested structures
        for key, value in body.items():
            if key in ("data", "result", "results", "listings", "items", "feed",
                       "edges", "nodes", "list", "searchResults", "poiList"):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            # Check for GraphQL edge pattern
                            node = item.get("node") or item
                            if self._is_listing_object(node):
                                out.append(node)
                            else:
                                self._extract_listings_from_api(node, out)
                elif isinstance(value, dict):
                    self._extract_listings_from_api(value, out)

    @staticmethod
    def _is_listing_object(obj: dict) -> bool:
        """Heuristic: does this dict look like a listing?"""
        # Must have some identifying field
        has_id = any(k in obj for k in ("listingId", "id", "adId"))
        if not has_id:
            return False

        # Must have at least 2 of: price, rooms, area, address, city
        listing_indicators = 0
        if any(k in obj for k in ("price", "monthlyRent", "rentPrice", "priceText")):
            listing_indicators += 1
        if any(k in obj for k in ("rooms", "numberOfRooms")):
            listing_indicators += 1
        if any(k in obj for k in ("area", "squareMeters")):
            listing_indicators += 1
        if any(k in obj for k in ("city", "cityName", "street", "streetName", "address")):
            listing_indicators += 1
        if any(k in obj for k in ("lat", "latitude", "lng", "longitude")):
            listing_indicators += 1

        return listing_indicators >= 2

    # ------------------------------------------------------------------
    # DOM extraction (fallback)
    # ------------------------------------------------------------------

    def _extract_listing_cards(self, page) -> list[dict]:
        """Extract listing data from rendered DOM elements.

        Madlan renders listing cards in the search results. We extract
        key data from each card's text content and attributes.
        """
        cards: list[dict] = []

        try:
            # Madlan listing cards are typically links to /listings/{id}
            links = page.query_selector_all('a[href*="/listings/"]')
            seen_ids: set[str] = set()

            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    # Extract listing ID from href
                    id_match = re.search(r"/listings/([a-zA-Z0-9_-]+)", href)
                    if not id_match:
                        continue

                    listing_id = id_match.group(1)

                    # Skip navigation links (too short IDs are likely category links)
                    if len(listing_id) < 5:
                        continue
                    if listing_id in seen_ids:
                        continue
                    seen_ids.add(listing_id)

                    text_content = link.inner_text()
                    lines = [l.strip() for l in text_content.split("\n") if l.strip()]

                    # Extract image; prefer data-src (lazy-load high-res) over src (thumbnail)
                    img = link.query_selector("img")
                    image_url = (img.get_attribute("data-src") or img.get_attribute("src")) if img else None

                    card_data = self._build_card_from_text(listing_id, lines, image_url)
                    cards.append(card_data)

                    if len(cards) <= 3:
                        logger.info(
                            "Madlan: sample card #%d id=%s, lines=%r",
                            len(cards), listing_id, lines[:6],
                        )
                except Exception:
                    continue

        except Exception as exc:
            logger.warning("Madlan: failed to extract listing cards: %s", exc)

        return cards

    @staticmethod
    def _build_card_from_text(
        listing_id: str,
        text_lines: list[str],
        image_url: str | None,
    ) -> dict:
        """Build a card dict from extracted text lines.

        Madlan card text typically contains:
        - Price (e.g., "₪4,000" or "4,000 ₪/חודש")
        - Address/location info
        - Rooms, area, floor details
        """
        card: dict = {"id": listing_id, "image_urls": [image_url] if image_url else []}

        price = None
        rooms = None
        area_sqm = None
        floor = None
        city = ""
        street = ""
        title_parts: list[str] = []

        for line in text_lines:
            # Price detection
            price_match = re.search(r"[\$₪]?\s?([\d,]+)\s*(?:₪|ש\"ח|ILS)?", line)
            if price_match and price is None:
                amount = price_match.group(1).replace(",", "")
                try:
                    val = float(amount)
                    if val > 500:  # Likely a price, not a floor/room count
                        price = val
                        continue
                except ValueError:
                    pass

            # Rooms detection (e.g., "3 חדרים", "3.5 rooms")
            rooms_match = re.search(r"(\d+\.?\d*)\s*(?:חדרים|חד׳|rooms)", line, re.IGNORECASE)
            if rooms_match and rooms is None:
                rooms = float(rooms_match.group(1))
                continue

            # Area detection (e.g., "80 מ\"ר", "80 sqm")
            area_match = re.search(r"(\d+)\s*(?:מ\"ר|מ״ר|sqm|m²)", line, re.IGNORECASE)
            if area_match and area_sqm is None:
                area_sqm = float(area_match.group(1))
                continue

            # Floor detection (e.g., "קומה 3", "floor 3")
            floor_match = re.search(r"(?:קומה|floor)\s*(\d+)", line, re.IGNORECASE)
            if floor_match and floor is None:
                floor = int(floor_match.group(1))
                continue

            # Otherwise treat as location/title
            if line and not title_parts:
                title_parts.append(line)
            elif line and len(title_parts) < 3:
                title_parts.append(line)

        # Try to extract city from title lines (usually last location line)
        if title_parts:
            card["title"] = " | ".join(title_parts)
            # First line is often the street, second the neighborhood/city
            if len(title_parts) >= 2:
                street = title_parts[0]
                city = title_parts[1]
            else:
                city = title_parts[0]

        card["price"] = str(price) if price else ""
        card["rooms"] = rooms
        card["area_sqm"] = area_sqm
        card["floor"] = floor
        card["city"] = city
        card["street"] = street
        card["neighborhood"] = None

        return card

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _force_kill_playwright(pw) -> None:
        """Kill Playwright's subprocess tree immediately."""
        try:
            proc = pw._impl_obj._transport._proc  # type: ignore[attr-defined]
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
                logger.info("Madlan Playwright: process killed")
                return
        except Exception:
            pass

        try:
            pw.stop()
            logger.info("Madlan Playwright: stopped gracefully")
        except Exception:
            pass
