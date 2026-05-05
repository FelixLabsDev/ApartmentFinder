from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from src.models.enums import Currency, PropertyType, Source
from src.models.filters import SearchFilter
from src.models.listing import ListingCreate
from src.pipeline.deduplicator import ListingDeduplicator
from src.pipeline.filter_engine import FilterEngine
from src.pipeline.normalizer import ListingNormalizer
from src.scrapers.orchestrator import ScraperOrchestrator, ScrapeResult

logger = logging.getLogger(__name__)

# Fields that AI extraction should try to fill for Facebook listings
_KEY_FIELDS = ["price", "rooms", "city", "area_sqm", "floor", "street", "neighborhood"]


@dataclass
class PipelineResult:
    """Summary of a full pipeline run."""
    total_scraped: int = 0
    total_after_dedup: int = 0
    total_after_filter: int = 0
    scrape_results: list[ScrapeResult] | None = None
    listings: list[ListingCreate] | None = None


class ScrapePipeline:
    """End-to-end pipeline: scrape → normalize → AI enrich → deduplicate → filter.

    Usage::

        orchestrator = ScraperOrchestrator()
        orchestrator.register("yad2", [Yad2ApiScraper()])
        orchestrator.register("facebook", [FacebookGraphQLScraper()])

        pipeline = ScrapePipeline(orchestrator)
        result = await pipeline.run(search_filter)
    """

    def __init__(
        self,
        orchestrator: ScraperOrchestrator,
        normalizer: ListingNormalizer | None = None,
        deduplicator: ListingDeduplicator | None = None,
    ):
        self._orchestrator = orchestrator
        self._normalizer = normalizer or ListingNormalizer()
        self._deduplicator = deduplicator or ListingDeduplicator()

    async def run(
        self,
        search_filter: SearchFilter,
        post_filter: SearchFilter | None = None,
    ) -> PipelineResult:
        """Execute the full scraping pipeline.

        Args:
            search_filter: Passed to scrapers for API-level filtering (city, price, etc.)
            post_filter: Used for post-scrape in-memory filtering. If None, uses
                search_filter. Pass a separate filter to avoid city-name mismatches
                across sources (e.g. "herzliya" vs Hebrew names from Facebook).

        Steps:
        1. Scrape from all sources (via orchestrator with fallback chains)
        2. Normalize (city names, prices, phones, etc.)
        3. Deduplicate across sources
        4. Apply post_filter for any criteria the APIs couldn't handle
        """
        result = PipelineResult()

        # 1. Scrape
        scrape_results = await self._orchestrator.scrape_all(search_filter)
        result.scrape_results = scrape_results

        all_listings: list[ListingCreate] = []
        for sr in scrape_results:
            all_listings.extend(sr.listings)

        result.total_scraped = len(all_listings)
        logger.info("Pipeline: scraped %d total listings from %d sources",
                     len(all_listings), len(scrape_results))

        if not all_listings:
            result.listings = []
            return result

        # 2. Normalize
        normalized = self._normalizer.normalize_batch(all_listings)

        # 3. AI enrich Facebook listings
        enriched = await self._ai_enrich_facebook(normalized)

        # 4. Deduplicate
        deduped = self._deduplicator.deduplicate_batch(enriched)
        result.total_after_dedup = len(deduped)
        logger.info("Pipeline: %d listings after deduplication", len(deduped))

        # 5. Filter (use post_filter if provided, else fall back to search_filter)
        filter_to_apply = post_filter if post_filter is not None else search_filter
        filtered = FilterEngine.apply(deduped, filter_to_apply)
        result.total_after_filter = len(filtered)
        result.listings = filtered
        logger.info("Pipeline: %d listings after filtering", len(filtered))

        return result

    @staticmethod
    async def _ai_enrich_facebook(listings: list[ListingCreate]) -> list[ListingCreate]:
        """Run AI extraction on Facebook listings that have descriptions but are missing key fields."""
        from src.ai.extractor import extract_listing_fields

        fb_with_desc = [
            l for l in listings
            if l.source == Source.FACEBOOK
            and l.description
            and len(l.description.strip()) > 30
        ]

        if not fb_with_desc:
            return listings

        logger.info("Pipeline: AI enriching %d Facebook listings with descriptions", len(fb_with_desc))

        for listing in fb_with_desc:
            try:
                result = await extract_listing_fields(
                    listing.description or "",
                    title=listing.title,
                )
                fields = result.extracted_fields
                if not fields:
                    continue

                # Only fill in fields that are currently missing
                if listing.price is None and fields.get("price") is not None:
                    listing.price = fields["price"]
                if fields.get("currency") == "USD":
                    listing.currency = Currency.USD
                if listing.rooms is None and fields.get("rooms") is not None:
                    listing.rooms = fields["rooms"]
                if (not listing.city or listing.city == "unknown") and fields.get("city"):
                    listing.city = fields["city"]
                if listing.neighborhood is None and fields.get("neighborhood"):
                    listing.neighborhood = fields["neighborhood"]
                if listing.street is None and fields.get("street"):
                    listing.street = fields["street"]
                if listing.house_number is None and fields.get("house_number"):
                    listing.house_number = fields["house_number"]
                if listing.floor is None and fields.get("floor") is not None:
                    listing.floor = fields["floor"]
                if listing.total_floors is None and fields.get("total_floors") is not None:
                    listing.total_floors = fields["total_floors"]
                if listing.area_sqm is None and fields.get("area_sqm") is not None:
                    listing.area_sqm = fields["area_sqm"]
                if listing.entry_date is None and fields.get("entry_date"):
                    try:
                        listing.entry_date = date.fromisoformat(fields["entry_date"])
                    except (ValueError, TypeError):
                        pass
                if listing.property_type is None and fields.get("property_type"):
                    try:
                        listing.property_type = PropertyType(fields["property_type"])
                    except ValueError:
                        listing.property_type = PropertyType.OTHER

                # Boolean features — only fill if not already set
                for feat in [
                    "has_parking", "has_elevator", "has_balcony", "has_air_conditioning",
                    "has_mamad", "is_accessible", "is_furnished", "has_bars",
                    "has_storage", "pet_friendly",
                ]:
                    if getattr(listing, feat) is None and fields.get(feat) is not None:
                        setattr(listing, feat, fields[feat])

                if listing.contact_name is None and fields.get("contact_name"):
                    listing.contact_name = fields["contact_name"]
                if listing.contact_phone is None and fields.get("contact_phone"):
                    listing.contact_phone = fields["contact_phone"]

                listing.ai_guessed_fields = result.guessed_fields

                logger.info(
                    "Pipeline: AI enriched listing %s — extracted %d fields",
                    listing.source_id, len(result.guessed_fields),
                )

            except Exception as exc:
                logger.warning(
                    "Pipeline: AI enrichment failed for listing %s: %s",
                    listing.source_id, exc,
                )

        return listings
