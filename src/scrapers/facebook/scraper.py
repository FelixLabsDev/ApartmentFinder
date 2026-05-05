from __future__ import annotations

import logging
import re
import time

from src.models.filters import SearchFilter
from src.models.listing import ListingCreate
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import ScraperHttpClient

from .config import (
    DEFAULT_RADIUS_KM,
    GRAPHQL_DOC_IDS,
    GRAPHQL_HEADERS,
    GRAPHQL_URL,
    LISTING_URL_TEMPLATE,
    LOCATION_IDS,
    MARKETPLACE_BASE_URL,
    PROPERTY_RENTAL_CATEGORY_ID,
)
from .parser import FacebookParser

logger = logging.getLogger(__name__)


class FacebookGraphQLScraper(BaseScraper):
    """Scrape Facebook Marketplace via the internal GraphQL API.

    This approach sends POST requests to /api/graphql/ with a reverse-engineered
    doc_id and structured variables.  It requires valid session cookies or tokens
    obtained from a logged-in browser session.

    **Important**: Facebook aggressively rate-limits and blocks automated access.
    This scraper will often fail without valid auth cookies.  Use the Playwright
    fallback (``FacebookPlaywrightScraper``) when GraphQL access is unavailable.
    """

    def __init__(
        self,
        http_client: ScraperHttpClient | None = None,
        cookies: dict[str, str] | None = None,
        lsd_token: str | None = None,
    ):
        self._client = http_client or ScraperHttpClient()
        self._parser = FacebookParser()
        self._cookies = cookies or {}
        self._lsd_token = lsd_token or ""

    @property
    def source_name(self) -> str:
        return "facebook"

    @property
    def method_name(self) -> str:
        return "graphql"

    async def scrape(self, search_filter: SearchFilter) -> list[ListingCreate]:
        """Fetch property rental listings from Facebook Marketplace GraphQL API."""
        all_listings: list[ListingCreate] = []
        max_pages = 3  # Safety limit — Facebook often blocks after a few pages

        location_ids = self._resolve_location_ids(search_filter)
        if not location_ids:
            logger.warning("No Facebook location IDs matched for filter cities: %s", search_filter.cities)
            return []

        for location_id in location_ids:
            cursor: str | None = None
            page = 0

            while page < max_pages:
                page += 1
                variables = self._build_variables(search_filter, location_id, cursor)

                logger.info(
                    "Facebook GraphQL: fetching page %d for location %s",
                    page, location_id,
                )

                data = await self._execute_graphql(variables)
                if data is None:
                    logger.error("GraphQL request failed for location %s page %d", location_id, page)
                    break

                items = self._parser.extract_feed_items(data)
                if not items:
                    logger.info("No more items for location %s on page %d", location_id, page)
                    break

                for item in items:
                    listing = self._parser.parse_listing(item)
                    if listing:
                        all_listings.append(listing)

                pagination = self._parser.get_pagination(data)
                if not pagination["has_next_page"]:
                    break

                cursor = pagination["end_cursor"]
                await self._client.random_delay()

        logger.info("Facebook GraphQL: scraped %d listings total", len(all_listings))
        return all_listings

    async def health_check(self) -> bool:
        """Check if GraphQL endpoint is reachable (doesn't guarantee auth works)."""
        try:
            variables = {
                "count": 1,
                "params": {
                    "bqf": {"callsite": "COMMERCE_MKTPLACE_WWW", "query": ""},
                    "browse_request_params": {
                        "commerce_search_and_rp_category_id": [PROPERTY_RENTAL_CATEGORY_ID],
                        "filter_location_latitude": 32.0853,
                        "filter_location_longitude": 34.7818,
                    },
                },
            }
            data = await self._execute_graphql(variables)
            return data is not None and "data" in data
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _execute_graphql(self, variables: dict) -> dict | None:
        """Send a single GraphQL request, trying each doc_id until one works."""
        if not self._cookies:
            logger.warning("Facebook GraphQL: no cookies provided — requests will likely fail")

        headers = {**GRAPHQL_HEADERS}
        if self._lsd_token:
            headers["X-FB-LSD"] = self._lsd_token

        for doc_id in GRAPHQL_DOC_IDS:
            form_data = {
                "doc_id": doc_id,
                "variables": _json_dumps(variables),
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "CometMarketplaceSearchContentContainerQuery",
                "server_timestamps": "true",
            }
            if self._lsd_token:
                form_data["lsd"] = self._lsd_token

            try:
                response = await self._client.post(
                    GRAPHQL_URL,
                    data=form_data,
                    headers=headers,
                    cookies=self._cookies if self._cookies else None,
                    max_retries=2,
                )

                content_type = response.headers.get("content-type", "")
                if "json" not in content_type and "javascript" not in content_type:
                    body_preview = response.text[:200]
                    logger.error(
                        "Facebook returned non-JSON (status=%d, type=%s): %s",
                        response.status_code, content_type, body_preview,
                    )
                    continue

                result = response.json()

                # Facebook returns errors inside the response body
                if "errors" in result or "error" in result:
                    logger.warning(
                        "GraphQL error with doc_id %s: %s",
                        doc_id,
                        result.get("errors") or result.get("error"),
                    )
                    continue

                if "data" in result:
                    return result
            except Exception as exc:
                logger.warning("GraphQL request failed with doc_id %s: %s", doc_id, exc)
                continue

        logger.error("Facebook GraphQL: all %d doc_ids failed", len(GRAPHQL_DOC_IDS))
        return None

    def _resolve_location_ids(self, search_filter: SearchFilter) -> list[str]:
        """Map filter cities to Facebook location IDs."""
        if not search_filter.cities:
            # Default to Tel Aviv
            return [LOCATION_IDS.get("tel-aviv", "110884905606138")]

        ids = []
        for city in search_filter.cities:
            location_id = LOCATION_IDS.get(city.lower())
            if location_id:
                ids.append(location_id)
            else:
                logger.warning("No Facebook location ID for city: %s", city)
        return ids

    def _build_variables(
        self,
        search_filter: SearchFilter,
        location_id: str,
        cursor: str | None = None,
    ) -> dict:
        """Build GraphQL variables dict from SearchFilter."""
        lat = search_filter.fb_latitude if search_filter.fb_latitude is not None else 32.0853
        lng = search_filter.fb_longitude if search_filter.fb_longitude is not None else 34.7818
        radius = search_filter.fb_radius_km if search_filter.fb_radius_km is not None else DEFAULT_RADIUS_KM

        browse_params: dict = {
            "commerce_search_and_rp_category_id": [PROPERTY_RENTAL_CATEGORY_ID],
            "filter_location_latitude": lat,
            "filter_location_longitude": lng,
            "filter_radius_kms": radius,
        }

        if search_filter.min_price is not None:
            browse_params["filter_price_lower_bound"] = int(search_filter.min_price)
        if search_filter.max_price is not None:
            browse_params["filter_price_upper_bound"] = int(search_filter.max_price)

        variables: dict = {
            "count": 24,
            "params": {
                "bqf": {
                    "callsite": "COMMERCE_MKTPLACE_WWW",
                    "query": "",
                },
                "browse_request_params": browse_params,
            },
        }

        if cursor:
            variables["cursor"] = cursor

        return variables

    async def close(self) -> None:
        await self._client.close()


class FacebookPlaywrightScraper(BaseScraper):
    """Facebook Marketplace scraper using Playwright with a persistent browser profile.

    Uses a saved browser profile so you only need to log in to Facebook once.
    The session is stored in ``data/fb_profile/`` and reused for future scrapes.

    - First run (headless=False): opens a visible browser, you log in, session is saved.
    - Subsequent runs: reuses the saved session — works headless too.

    Uses the sync Playwright API in a thread to avoid Windows event loop issues.
    """

    PROFILE_DIR = "data/fb_profile"

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._parser = FacebookParser()

    @property
    def source_name(self) -> str:
        return "facebook"

    @property
    def method_name(self) -> str:
        return "playwright"

    async def scrape(self, search_filter: SearchFilter) -> list[ListingCreate]:
        """Scrape Facebook Marketplace via browser automation (runs in thread)."""
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
        location_ids = self._resolve_location_ids(search_filter)

        pw = sync_playwright().start()
        try:
            # Persistent context saves cookies/session across runs
            context = pw.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=self._headless,
                locale="he-IL",
                viewport={"width": 1280, "height": 800},
            )
            page = context.pages[0] if context.pages else context.new_page()

            # Check if we need to log in
            if not self._ensure_logged_in(page):
                return []

            for location_id in location_ids:
                url = self._build_marketplace_url(search_filter, location_id)
                logger.info("Facebook Playwright: navigating to %s", url)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(5000)
                except Exception as exc:
                    logger.error("Failed to load %s: %s", url, exc)
                    continue

                logger.info("Facebook Playwright: page URL: %s", page.url)

                self._dismiss_login_modal(page)

                for scroll_round in range(8):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)

                cards = self._extract_listing_cards(page)
                logger.info(
                    "Facebook Playwright: found %d listing cards for location %s",
                    len(cards), location_id,
                )

                # Visit each listing's detail page to get full images & description
                for i, card_data in enumerate(cards):
                    self._enrich_from_detail_page(page, card_data, i + 1, len(cards))

                parsed_ok = 0
                parsed_fail = 0
                for card_data in cards:
                    listing = self._parser.parse_listing(card_data)
                    if listing:
                        all_listings.append(listing)
                        parsed_ok += 1
                    else:
                        parsed_fail += 1
                        if parsed_fail <= 3:
                            logger.warning(
                                "Facebook Playwright: parse_listing returned None for card #%d, "
                                "id=%s, sample keys=%s",
                                parsed_fail,
                                card_data.get("id", "?"),
                                list(card_data.keys())[:8],
                            )
                            if parsed_fail == 1:
                                import json
                                logger.info(
                                    "Facebook Playwright: first failed card data: %s",
                                    json.dumps(card_data, ensure_ascii=False, default=str)[:1000],
                                )
                logger.info(
                    "Facebook Playwright: parsed %d OK, %d failed out of %d cards",
                    parsed_ok, parsed_fail, len(cards),
                )
        except Exception as exc:
            logger.error("Facebook Playwright scrape error: %s", exc)
        finally:
            # Force-kill the Playwright Node.js transport process.
            # Facebook's persistent WebSocket connections prevent graceful
            # shutdown, making context.close() and pw.stop() hang forever.
            # Killing the transport also kills the browser it spawned.
            logger.info("Facebook Playwright: terminating browser...")
            self._force_kill_playwright(pw)

        logger.info("Facebook Playwright: scraped %d listings total", len(all_listings))
        return all_listings

    @staticmethod
    def _force_kill_playwright(pw) -> None:
        """Kill Playwright's subprocess tree immediately.

        This avoids the hang caused by Facebook keeping connections alive.
        The persistent browser profile is already saved to disk, so killing
        the process doesn't lose session state.
        """
        try:
            # Access the Node.js transport subprocess that Playwright manages.
            # Killing it also terminates the browser process it spawned.
            proc = pw._impl_obj._transport._proc  # type: ignore[attr-defined]
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
                logger.info("Facebook Playwright: process killed")
                return
        except Exception:
            pass

        # Fallback: try pw.stop() directly (may hang briefly)
        try:
            pw.stop()
            logger.info("Facebook Playwright: stopped gracefully")
        except Exception:
            pass

    async def health_check(self) -> bool:
        """Check if Playwright can load the marketplace page."""
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

        try:
            with sync_playwright() as pw:
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=str(__import__("pathlib").Path(self.PROFILE_DIR).resolve()),
                    headless=True,
                    viewport={"width": 1280, "height": 800},
                )
                page = context.pages[0] if context.pages else context.new_page()
                response = page.goto(
                    "https://www.facebook.com/marketplace/",
                    wait_until="domcontentloaded",
                    timeout=15000,
                )
                ok = response is not None and response.status == 200
                context.close()
                return ok
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_location_ids(self, search_filter: SearchFilter) -> list[str]:
        if not search_filter.cities:
            return [LOCATION_IDS.get("tel-aviv", "110884905606138")]
        ids = []
        for city in search_filter.cities:
            loc = LOCATION_IDS.get(city.lower())
            if loc:
                ids.append(loc)
        return ids or [LOCATION_IDS["tel-aviv"]]

    def _build_marketplace_url(self, search_filter: SearchFilter, location_id: str) -> str:
        """Build a Marketplace URL, using lat/lng params when available."""
        base = MARKETPLACE_BASE_URL.format(location_id=location_id)
        params = []
        if search_filter.fb_latitude is not None and search_filter.fb_longitude is not None:
            params.append(f"latitude={search_filter.fb_latitude}")
            params.append(f"longitude={search_filter.fb_longitude}")
            radius = search_filter.fb_radius_km or DEFAULT_RADIUS_KM
            params.append(f"radius={int(radius)}")
        if search_filter.min_price is not None:
            params.append(f"minPrice={int(search_filter.min_price)}")
        if search_filter.max_price is not None:
            params.append(f"maxPrice={int(search_filter.max_price)}")
        if params:
            return base + "?" + "&".join(params)
        return base

    def _ensure_logged_in(self, page, timeout_seconds: int = 120) -> bool:
        """Navigate to marketplace and ensure we're logged in.

        If the saved profile already has a valid session, returns immediately.
        Otherwise (visible browser mode) waits for the user to log in.
        """
        logger.info("Facebook Playwright: checking login status...")
        try:
            page.goto(
                "https://www.facebook.com/marketplace/",
                wait_until="domcontentloaded",
                timeout=30000,
            )
        except Exception as exc:
            logger.error("Failed to load Facebook: %s", exc)
            return False

        # Let redirects settle
        page.wait_for_timeout(4000)

        if self._page_has_listings(page):
            logger.info("Facebook Playwright: already logged in (session reused)")
            return True

        if self._headless:
            logger.error(
                "Facebook Playwright: not logged in and running headless. "
                "Run once with 'Open browser for login' checked to save your session."
            )
            return False

        # Visible browser — wait for user to log in
        logger.info(
            "Facebook Playwright: please log in in the browser window. "
            "You have %d seconds. Your session will be saved for future runs.",
            timeout_seconds,
        )

        start = time.monotonic()
        while time.monotonic() - start < timeout_seconds:
            page.wait_for_timeout(3000)

            # After login, FB typically redirects back to marketplace
            if self._page_has_listings(page):
                logger.info("Facebook Playwright: login successful — session saved")
                return True

            elapsed = int(time.monotonic() - start)
            if elapsed > 0 and elapsed % 15 == 0:
                logger.info(
                    "Facebook Playwright: waiting for login... (%ds / %ds)",
                    elapsed, timeout_seconds,
                )

        logger.warning("Facebook Playwright: login timed out after %ds", timeout_seconds)
        return False

    def _page_has_listings(self, page) -> bool:
        """Check if the current page shows marketplace listings (meaning we're logged in)."""
        url = page.url
        # Definitely not logged in if on login/checkpoint page
        if "/login" in url or "/checkpoint" in url or "/recover" in url:
            return False
        # Check for login form
        if page.query_selector('input[name="email"], input[name="pass"]'):
            return False
        # Positive: marketplace item links visible
        items = page.query_selector_all('a[href*="/marketplace/item/"]')
        if len(items) > 0:
            return True
        # Positive: marketplace category links (shown on logged-in marketplace home)
        categories = page.query_selector_all('a[href*="/marketplace/category/"]')
        if len(categories) > 0:
            return True
        return False

    def _dismiss_login_modal(self, page) -> None:
        """Try to close Facebook's login popup if it appears."""
        try:
            close_btn = page.locator('[aria-label="Close"]').first
            if close_btn.is_visible(timeout=3000):
                close_btn.click()
                page.wait_for_timeout(500)
        except Exception:
            pass

        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    def _extract_listing_cards(self, page) -> list[dict]:
        """Extract listing data from rendered marketplace cards."""
        cards: list[dict] = []

        try:
            links = page.query_selector_all('a[href*="/marketplace/item/"]')

            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    listing_id_match = re.search(r"/marketplace/item/(\d+)", href)
                    if not listing_id_match:
                        continue

                    listing_id = listing_id_match.group(1)

                    text_content = link.inner_text()
                    lines = [l.strip() for l in text_content.split("\n") if l.strip()]

                    img = link.query_selector("img")
                    image_url = img.get_attribute("src") if img else None

                    card_data = self._build_card_dict(listing_id, lines, image_url)
                    cards.append(card_data)
                    if len(cards) <= 3:
                        logger.info(
                            "Facebook Playwright: sample card #%d text_lines=%r, id=%s",
                            len(cards), lines[:5], listing_id,
                        )
                except Exception:
                    continue
        except Exception as exc:
            logger.warning("Failed to extract listing cards: %s", exc)

        return cards

    def _enrich_from_detail_page(
        self,
        page,
        card_data: dict,
        index: int,
        total: int,
    ) -> None:
        """Navigate to a listing's detail page to extract full images and description.

        Mutates card_data in place with richer data when available.
        """
        listing_id = card_data.get("id")
        if not listing_id:
            return

        detail_url = LISTING_URL_TEMPLATE.format(listing_id=listing_id)
        try:
            if index <= 3 or index % 10 == 0:
                logger.info(
                    "Facebook Playwright: fetching detail %d/%d — %s",
                    index, total, detail_url,
                )
            page.goto(detail_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)

            self._dismiss_login_modal(page)

            # --- Extract all images ---
            images: list[dict] = []
            # Facebook detail pages show images in various containers;
            # look for all large images in the listing area.
            img_elements = page.query_selector_all(
                'img[src*="scontent"], img[src*="fbcdn"]'
            )
            seen_srcs: set[str] = set()
            for img in img_elements:
                src = img.get_attribute("src") or ""
                if not src or src in seen_srcs:
                    continue
                # Filter out tiny icons/avatars by checking natural dimensions
                try:
                    width = img.evaluate("el => el.naturalWidth")
                    if width and width < 150:
                        continue
                except Exception:
                    pass
                seen_srcs.add(src)
                images.append({"image": {"uri": src}})

            if images:
                card_data["listing_photos"] = images
                if index <= 3:
                    logger.info(
                        "Facebook Playwright: detail #%d found %d images",
                        index, len(images),
                    )

            # --- Extract full description ---
            # The description is typically in a <span> inside the listing detail section.
            # Try multiple selectors that Facebook uses for listing descriptions.
            description = ""
            for selector in [
                '[data-testid="marketplace_listing_description"] span',
                'div[class*="Description"] span',
                'span[dir="auto"]',
            ]:
                desc_elements = page.query_selector_all(selector)
                for el in desc_elements:
                    text = (el.inner_text() or "").strip()
                    # Pick the longest text block as the description
                    if len(text) > len(description) and len(text) > 50:
                        description = text

            if description:
                card_data["redacted_description"] = {"text": description}
                if index <= 3:
                    logger.info(
                        "Facebook Playwright: detail #%d description length: %d",
                        index, len(description),
                    )

            # Brief delay to avoid rate-limiting
            page.wait_for_timeout(1500)

        except Exception as exc:
            logger.warning(
                "Facebook Playwright: failed to fetch detail for %s: %s",
                listing_id, exc,
            )

    def _build_card_dict(
        self,
        listing_id: str,
        text_lines: list[str],
        image_url: str | None,
    ) -> dict:
        """Build a dict compatible with FacebookParser.parse_listing from card text."""
        price_data = None
        title = ""
        city = ""

        if text_lines:
            price_str = text_lines[0]
            price_match = re.search(r"[\$₪]?([\d,]+)", price_str)
            if price_match:
                amount = price_match.group(1).replace(",", "")
                currency = "USD" if "$" in price_str else "ILS"
                price_data = {"amount": amount, "currency": currency}

        if len(text_lines) > 1:
            title = text_lines[1]
        if len(text_lines) > 2:
            city = text_lines[2]

        photos = []
        if image_url:
            photos = [{"image": {"uri": image_url}}]

        return {
            "id": listing_id,
            "marketplace_listing_title": title,
            "listing_price": price_data,
            "location": {
                "reverse_geocode": {"city": city, "state": ""},
            },
            "listing_photos": photos,
            "redacted_description": {"text": title},
            "creation_time": None,
            "property_type": None,
            "attribute_data": {},
            "seller": {},
            "is_pending": False,
            "is_sold": False,
        }


def _json_dumps(obj: dict) -> str:
    """Compact JSON serialization."""
    import json
    return json.dumps(obj, separators=(",", ":"))
