from __future__ import annotations

import asyncio
import logging

from src.models.filters import SearchFilter
from src.models.listing import ListingCreate
from src.scrapers.base import BaseScraper
from src.scrapers.http_client import ScraperHttpClient

from .config import CITY_CODES, FEED_API_URL, ITEM_API_URLS, PROPERTY_TYPE_CODES
from .parser import Yad2Parser

logger = logging.getLogger(__name__)


class Yad2ApiScraper(BaseScraper):
    """Primary Yad2 scraper using the internal JSON API endpoint."""

    def __init__(self, http_client: ScraperHttpClient | None = None):
        self._client = http_client or ScraperHttpClient()
        self._parser = Yad2Parser()

    @property
    def source_name(self) -> str:
        return "yad2"

    @property
    def method_name(self) -> str:
        return "api"

    async def scrape(self, search_filter: SearchFilter) -> list[ListingCreate]:
        """Fetch listings from Yad2 API, paginating through results."""
        params = self._build_params(search_filter)
        all_listings: list[ListingCreate] = []

        max_pages = 10  # Safety limit
        page = 1

        while page <= max_pages:
            params["page"] = str(page)
            logger.info("Yad2 API: fetching page %d with params %s", page, params)

            try:
                response = await self._client.get(
                    FEED_API_URL,
                    params=params,
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Referer": "https://www.yad2.co.il/realestate/rent",
                        "Origin": "https://www.yad2.co.il",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-origin",
                    },
                )

                # Detect bot-detection redirect
                final_url = str(response.url)
                if "validate.perfdrive.com" in final_url or "perfdrive" in final_url:
                    logger.error(
                        "Yad2 API: bot detection triggered on page %d! "
                        "Redirected to %s. Scraped %d listings before block.",
                        page, final_url, len(all_listings),
                    )
                    break

                content_type = response.headers.get("content-type", "")
                if "application/json" not in content_type:
                    logger.error(
                        "Yad2 API: unexpected content-type '%s' on page %d (url=%s). "
                        "Possible bot block. Body preview: %.200s",
                        content_type, page, final_url,
                        response.text[:200] if response.text else "(empty)",
                    )
                    break

                data = response.json()
            except Exception as e:
                logger.error("Yad2 API request failed on page %d: %s", page, e)
                break

            # Parse items
            items = self._parser.extract_feed_items(data)
            if not items:
                logger.info("No more items on page %d", page)
                break

            parsed_count = 0
            skipped_count = 0
            for item in items:
                listing = self._parser.parse_listing(item)
                if listing:
                    all_listings.append(listing)
                    parsed_count += 1
                else:
                    skipped_count += 1

            logger.info(
                "Page %d: %d feed items → %d parsed, %d failed to parse",
                page, len(items), parsed_count, skipped_count,
            )

            # Check pagination
            pagination = self._parser.get_pagination(data)
            logger.info(
                "Pagination: page %d/%d, total_items=%s, page_size=%s",
                pagination["current_page"], pagination["total_pages"],
                pagination["total_items"], pagination["page_size"],
            )
            if page >= pagination["total_pages"]:
                break

            page += 1

            # Rate limiting between pages
            await self._client.random_delay()

        logger.info("Yad2 API: scraped %d listings across %d pages", len(all_listings), page)

        # Enrich listings with full-resolution images from the per-item API
        enricher = Yad2ImageEnricher(self._client)
        all_listings = await enricher.enrich(all_listings)

        return all_listings

    async def health_check(self) -> bool:
        """Check if the Yad2 API is reachable."""
        try:
            response = await self._client.get(
                FEED_API_URL,
                params={"page": "1"},
                headers={"Accept": "application/json"},
                max_retries=1,
            )
            data = response.json()
            return "feed" in data
        except Exception:
            return False

    def _build_params(self, search_filter: SearchFilter) -> dict[str, str]:
        """Map SearchFilter to Yad2 API query params."""
        params: dict[str, str] = {}

        # City
        if search_filter.cities:
            city_codes = []
            for city in search_filter.cities:
                code = CITY_CODES.get(city.lower())
                if code:
                    city_codes.append(code)
                else:
                    # Try using the city name directly as a code
                    city_codes.append(city)
            if city_codes:
                params["city"] = ",".join(city_codes)

        # Area code
        if search_filter.area_code:
            params["area"] = search_filter.area_code

        # Neighborhood code
        if search_filter.neighborhood_code:
            params["neighborhood"] = search_filter.neighborhood_code

        # Price range
        if search_filter.min_price is not None or search_filter.max_price is not None:
            min_p = int(search_filter.min_price) if search_filter.min_price else ""
            max_p = int(search_filter.max_price) if search_filter.max_price else ""
            params["price"] = f"{min_p}-{max_p}"

        # Rooms range
        if search_filter.min_rooms is not None or search_filter.max_rooms is not None:
            min_r = search_filter.min_rooms if search_filter.min_rooms else ""
            max_r = search_filter.max_rooms if search_filter.max_rooms else ""
            params["rooms"] = f"{min_r}-{max_r}"

        # Floor range
        if search_filter.min_floor is not None or search_filter.max_floor is not None:
            min_f = search_filter.min_floor if search_filter.min_floor is not None else ""
            max_f = search_filter.max_floor if search_filter.max_floor is not None else ""
            params["floor"] = f"{min_f}-{max_f}"

        # Area (sqm) range
        if search_filter.min_area_sqm is not None or search_filter.max_area_sqm is not None:
            min_a = int(search_filter.min_area_sqm) if search_filter.min_area_sqm else ""
            max_a = int(search_filter.max_area_sqm) if search_filter.max_area_sqm else ""
            params["squaremeter"] = f"{min_a}-{max_a}"

        # Property type
        if search_filter.property_types:
            type_codes = []
            for pt in search_filter.property_types:
                code = PROPERTY_TYPE_CODES.get(pt)
                if code:
                    type_codes.append(code)
            if type_codes:
                params["property"] = ",".join(type_codes)

        return params


class Yad2ImageEnricher:
    """Enriches listings with full-resolution images and real descriptions from the per-item API.

    The feed API only returns thumbnail-sized images and a search-index blob
    (`search_text`) instead of the actual seller description.  The per-item
    endpoints return the real gallery URLs and the free-text description.
    """

    # Delay between per-item requests to avoid bot detection
    _REQUEST_DELAY = 0.4

    def __init__(self, http_client: ScraperHttpClient | None = None):
        self._client = http_client or ScraperHttpClient()

    async def enrich(self, listings: list[ListingCreate]) -> list[ListingCreate]:
        """Fetch full-size images and real description for each listing in-place."""
        image_count = 0
        desc_count = 0
        for i, listing in enumerate(listings):
            images, description = await self._fetch_item_data(listing.source_id)
            if images:
                listing.image_urls = images
                image_count += 1
            # Only overwrite description when a real one is found — the feed's
            # search_text is a search-index blob, not a seller-written description
            if description:
                listing.description = description
                desc_count += 1
            # Rate-limit between requests; skip delay on last item
            if i < len(listings) - 1:
                await asyncio.sleep(self._REQUEST_DELAY)

        logger.info(
            "Yad2 enrichment: %d/%d listings got full-res images, %d/%d got real descriptions",
            image_count, len(listings), desc_count, len(listings),
        )
        return listings

    async def _fetch_item_data(self, token: str) -> tuple[list[str], str | None]:
        """Try each per-item API endpoint; return (image_urls, description) from first success."""
        for url_template in ITEM_API_URLS:
            url = url_template.format(token=token)
            try:
                response = await self._client.get(
                    url,
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Referer": f"https://www.yad2.co.il/realestate/item/{token}",
                        "Origin": "https://www.yad2.co.il",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-origin",
                    },
                    max_retries=1,
                )
                data = response.json()
                images = self._extract_images(data)
                description = self._extract_description(data)
                if images or description:
                    logger.debug(
                        "Yad2 item %s: %d images, description=%s from %s",
                        token, len(images), bool(description), url,
                    )
                    return images, description
            except Exception as exc:
                logger.debug("Yad2 item API %s failed for %s: %s", url_template, token, exc)

        return [], None

    @staticmethod
    def _extract_images(data: dict) -> list[str]:
        """Extract image URL strings from various possible per-item API response shapes."""
        def _urls_from_list(items: list) -> list[str]:
            urls = []
            for item in items:
                if isinstance(item, str) and item.startswith("http"):
                    urls.append(item)
                elif isinstance(item, dict):
                    url = item.get("url") or item.get("src") or item.get("uri") or ""
                    if url:
                        urls.append(url)
            return urls

        # Try top-level image fields directly
        for field in ("images_urls", "images", "gallery", "photos"):
            items = data.get(field) or []
            if isinstance(items, list) and items:
                urls = _urls_from_list(items)
                if urls:
                    return urls

        # Try one level of nesting under common wrapper keys
        for wrapper in ("data", "item", "ad"):
            nested = data.get(wrapper)
            if isinstance(nested, dict):
                for field in ("images_urls", "images", "gallery", "photos"):
                    items = nested.get(field) or []
                    if isinstance(items, list) and items:
                        urls = _urls_from_list(items)
                        if urls:
                            return urls

        return []

    @staticmethod
    def _extract_description(data: dict) -> str | None:
        """Extract the seller-written description from a per-item API response.

        Yad2's per-item API may use any of several field names for the description
        across different endpoint versions; tries the most common ones in order.
        """
        # Candidate field names for the free-text description
        desc_fields = ("info_text", "description", "text", "body", "details")

        # Check top-level fields first
        for field in desc_fields:
            value = data.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()

        # Check one level of nesting under common wrapper keys
        for wrapper in ("data", "item", "ad"):
            nested = data.get(wrapper)
            if isinstance(nested, dict):
                for field in desc_fields:
                    value = nested.get(field)
                    if isinstance(value, str) and value.strip():
                        return value.strip()

        return None
