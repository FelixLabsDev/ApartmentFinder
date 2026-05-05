from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from src.models.enums import Currency, PropertyType, Source
from src.models.listing import ListingCreate

from .config import FEATURE_KEYWORDS, LISTING_URL_TEMPLATE

logger = logging.getLogger(__name__)

# Facebook property_type string → our PropertyType enum
_PROPERTY_TYPE_MAP: dict[str, PropertyType] = {
    "APARTMENT": PropertyType.APARTMENT,
    "HOUSE": PropertyType.HOUSE,
    "TOWNHOUSE": PropertyType.HOUSE,
    "CONDO": PropertyType.APARTMENT,
    "PENTHOUSE": PropertyType.PENTHOUSE,
    "STUDIO": PropertyType.STUDIO,
    "DUPLEX": PropertyType.DUPLEX,
    "OTHER": PropertyType.OTHER,
}


class FacebookParser:
    """Parse Facebook Marketplace GraphQL responses into ListingCreate objects."""

    @staticmethod
    def extract_feed_items(graphql_response: dict) -> list[dict]:
        """Extract listing nodes from a GraphQL marketplace search response.

        Filters out sponsored/null listings.
        """
        try:
            edges = (
                graphql_response
                .get("data", {})
                .get("marketplace_search", {})
                .get("feed_units", {})
                .get("edges", [])
            )
        except (AttributeError, TypeError):
            logger.warning("Unexpected GraphQL response structure")
            return []

        items: list[dict] = []
        for edge in edges:
            node = edge.get("node", {})
            listing = node.get("listing")
            if listing and isinstance(listing, dict) and listing.get("id"):
                items.append(listing)
        return items

    @staticmethod
    def get_pagination(graphql_response: dict) -> dict:
        """Extract pagination info (has_next_page + end_cursor)."""
        try:
            page_info = (
                graphql_response
                .get("data", {})
                .get("marketplace_search", {})
                .get("feed_units", {})
                .get("page_info", {})
            )
        except (AttributeError, TypeError):
            page_info = {}

        return {
            "has_next_page": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    @staticmethod
    def parse_listing(raw: dict) -> ListingCreate | None:
        """Transform a single Facebook listing dict into a ListingCreate.

        Returns None if the listing is missing essential data (id).
        """
        listing_id = raw.get("id")
        if not listing_id:
            logger.debug("Skipping listing with no id")
            return None

        # Skip sold/pending
        if raw.get("is_sold") or raw.get("is_pending"):
            logger.debug("Skipping sold/pending listing %s", listing_id)
            return None

        try:
            # Price
            price, currency = FacebookParser._parse_price(raw.get("listing_price"))

            # Location
            location = raw.get("location", {})
            reverse_geo = location.get("reverse_geocode", {})
            city = reverse_geo.get("city", "")

            # Attributes
            attrs = raw.get("attribute_data") or {}

            # Rooms: Facebook uses "bedrooms" — in Israel the convention
            # is total rooms (including living room), so bedrooms works
            # as a rough proxy. We store it as-is.
            rooms = FacebookParser._safe_float(attrs.get("bedrooms"))

            # Floor
            floor = FacebookParser._safe_int(attrs.get("floor_number"))
            total_floors = FacebookParser._safe_int(attrs.get("num_floors"))

            # Area
            area = FacebookParser._safe_float(attrs.get("area_size"))

            # Property type
            property_type = FacebookParser._parse_property_type(
                attrs.get("property_type") or raw.get("property_type")
            )

            # Features from attribute_data + description text
            description = (raw.get("redacted_description") or {}).get("text", "")
            features = FacebookParser._parse_features(attrs, description)

            # Images
            image_urls = FacebookParser._parse_images(raw)

            # Seller / contact
            seller = raw.get("seller") or {}

            # Dates
            posted_at = FacebookParser._parse_timestamp(raw.get("creation_time"))

            title = (
                raw.get("custom_title")
                or raw.get("marketplace_listing_title")
                or ""
            )

            return ListingCreate(
                source=Source.FACEBOOK,
                source_id=str(listing_id),
                source_url=LISTING_URL_TEMPLATE.format(listing_id=listing_id),
                title=title,
                city=city,
                description=description or None,
                price=price,
                currency=currency,
                rooms=rooms,
                floor=floor,
                total_floors=total_floors,
                area_sqm=area,
                property_type=property_type,
                image_urls=image_urls,
                contact_name=seller.get("name"),
                posted_at=posted_at,
                latitude=FacebookParser._safe_float(location.get("latitude")),
                longitude=FacebookParser._safe_float(location.get("longitude")),
                raw_data=raw,
                **features,
            )
        except Exception as exc:
            logger.exception("Failed to parse Facebook listing %s: %s", listing_id, exc)
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_price(price_data: dict | None) -> tuple[float | None, Currency]:
        """Extract price and currency from listing_price object."""
        if not price_data:
            return None, Currency.ILS

        amount_str = price_data.get("amount", "")
        currency_str = price_data.get("currency", "ILS")

        amount = FacebookParser._safe_float(amount_str)
        currency = Currency.USD if currency_str == "USD" else Currency.ILS

        return amount, currency

    @staticmethod
    def _parse_property_type(type_str: str | None) -> PropertyType | None:
        if not type_str:
            return None
        return _PROPERTY_TYPE_MAP.get(type_str.upper(), PropertyType.OTHER)

    @staticmethod
    def _parse_features(attrs: dict, description: str) -> dict[str, bool | None]:
        """Derive boolean feature flags from attribute_data and description text."""
        features: dict[str, bool | None] = {}

        # From structured attribute_data
        if attrs.get("furnish_type") == "FURNISHED":
            features["is_furnished"] = True
        elif attrs.get("furnish_type") == "UNFURNISHED":
            features["is_furnished"] = False

        if attrs.get("parking_type") and attrs["parking_type"] != "NONE":
            features["has_parking"] = True

        if attrs.get("heating_type") == "AIR_CONDITIONING":
            features["has_air_conditioning"] = True

        # Scan description text for Hebrew/English keywords
        desc_lower = description.lower()
        for keyword, field in FEATURE_KEYWORDS.items():
            if keyword.lower() in desc_lower and field not in features:
                features[field] = True

        return features

    @staticmethod
    def _parse_images(raw: dict) -> list[str]:
        """Extract image URLs from listing_photos array."""
        photos = raw.get("listing_photos") or []
        urls: list[str] = []
        for photo in photos:
            uri = (photo.get("image") or {}).get("uri")
            if uri:
                urls.append(uri)
        return urls

    @staticmethod
    def _parse_timestamp(ts: int | None) -> datetime | None:
        """Convert Unix epoch seconds to datetime."""
        if ts is None:
            return None
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            return None

    @staticmethod
    def _parse_rooms_from_subtitles(raw: dict) -> float | None:
        """Fallback: extract rooms from custom_sub_titles_with_rendering_flags."""
        subtitles = raw.get("custom_sub_titles_with_rendering_flags") or []
        for entry in subtitles:
            text = entry.get("subtitle", "")
            match = re.search(r"(\d+(?:\.\d+)?)\s*חדר", text)
            if match:
                return float(match.group(1))
        return None

    @staticmethod
    def _parse_area_from_subtitles(raw: dict) -> float | None:
        """Fallback: extract area from custom_sub_titles_with_rendering_flags."""
        subtitles = raw.get("custom_sub_titles_with_rendering_flags") or []
        for entry in subtitles:
            text = entry.get("subtitle", "")
            match = re.search(r"(\d+(?:\.\d+)?)\s*מ", text)
            if match:
                return float(match.group(1))
        return None

    @staticmethod
    def _parse_floor_from_subtitles(raw: dict) -> int | None:
        """Fallback: extract floor from custom_sub_titles_with_rendering_flags."""
        subtitles = raw.get("custom_sub_titles_with_rendering_flags") or []
        for entry in subtitles:
            text = entry.get("subtitle", "")
            match = re.search(r"קומה\s*(\d+)", text)
            if match:
                return int(match.group(1))
        return None

    @staticmethod
    def _safe_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
