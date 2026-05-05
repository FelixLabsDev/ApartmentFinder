from __future__ import annotations

import logging

from src.models.filters import SearchFilter
from src.models.listing import ListingCreate

logger = logging.getLogger(__name__)


class FilterEngine:
    """Apply SearchFilter criteria to a list of listings in-memory.

    This is used *after* scraping to further filter results that the source
    API couldn't filter server-side.
    """

    @staticmethod
    def apply(listings: list[ListingCreate], search_filter: SearchFilter) -> list[ListingCreate]:
        """Return only listings that match all filter criteria."""
        result = []
        filter_reasons: dict[str, int] = {}
        for listing in listings:
            reason = FilterEngine._rejection_reason(listing, search_filter)
            if reason is None:
                result.append(listing)
            else:
                filter_reasons[reason] = filter_reasons.get(reason, 0) + 1
                logger.debug(
                    "FilterEngine: rejected %s-%s (%s) reason=%s",
                    listing.source.value if listing.source else "?",
                    listing.source_id, listing.city, reason,
                )

        filtered_count = len(listings) - len(result)
        if filtered_count > 0:
            logger.info("FilterEngine: %d of %d listings filtered out. Reasons: %s",
                        filtered_count, len(listings), filter_reasons)

        return result

    @staticmethod
    def _rejection_reason(listing: ListingCreate, f: SearchFilter) -> str | None:
        """Return None if listing passes, or a reason string if rejected."""

        # --- City ---
        if f.cities:
            listing_city = (listing.city or "").strip().lower()
            if listing_city not in f.cities:
                return f"city={listing.city!r} not in {f.cities}"

        # --- Neighborhoods ---
        if f.neighborhoods:
            listing_neighborhood = (listing.neighborhood or "").strip().lower()
            if listing_neighborhood not in f.neighborhoods:
                return f"neighborhood={listing.neighborhood!r}"

        # --- Price range ---
        if listing.price is not None:
            if f.min_price is not None and listing.price < f.min_price:
                return f"price={listing.price}<min={f.min_price}"
            if f.max_price is not None and listing.price > f.max_price:
                return f"price={listing.price}>max={f.max_price}"

        # --- Rooms range ---
        if listing.rooms is not None:
            if f.min_rooms is not None and listing.rooms < f.min_rooms:
                return f"rooms={listing.rooms}<min={f.min_rooms}"
            if f.max_rooms is not None and listing.rooms > f.max_rooms:
                return f"rooms={listing.rooms}>max={f.max_rooms}"

        # --- Area range ---
        if listing.area_sqm is not None:
            if f.min_area_sqm is not None and listing.area_sqm < f.min_area_sqm:
                return f"area={listing.area_sqm}<min={f.min_area_sqm}"
            if f.max_area_sqm is not None and listing.area_sqm > f.max_area_sqm:
                return f"area={listing.area_sqm}>max={f.max_area_sqm}"

        # --- Floor range ---
        if listing.floor is not None:
            if f.min_floor is not None and listing.floor < f.min_floor:
                return f"floor={listing.floor}<min={f.min_floor}"
            if f.max_floor is not None and listing.floor > f.max_floor:
                return f"floor={listing.floor}>max={f.max_floor}"

        # --- Property types ---
        if f.property_types:
            if listing.property_type is None:
                return "property_type=None"
            if str(listing.property_type) not in f.property_types:
                return f"property_type={listing.property_type}"

        # --- Feature requirements ---
        if f.require_parking and not listing.has_parking:
            return "missing_parking"
        if f.require_elevator and not listing.has_elevator:
            return "missing_elevator"
        if f.require_balcony and not listing.has_balcony:
            return "missing_balcony"
        if f.require_air_conditioning and not listing.has_air_conditioning:
            return "missing_ac"
        if f.require_mamad and not listing.has_mamad:
            return "missing_mamad"
        if f.require_pet_friendly and not listing.pet_friendly:
            return "missing_pet_friendly"
        if f.require_furnished and not listing.is_furnished:
            return "missing_furnished"

        # --- Keywords (any match in title or description) ---
        if f.keywords:
            text = f"{listing.title} {listing.description or ''}".lower()
            if not any(kw.lower() in text for kw in f.keywords):
                return f"keywords={f.keywords}"

        # --- Exclude keywords ---
        if f.exclude_keywords:
            text = f"{listing.title} {listing.description or ''}".lower()
            if any(kw.lower() in text for kw in f.exclude_keywords):
                return f"exclude_keywords={f.exclude_keywords}"

        return None
