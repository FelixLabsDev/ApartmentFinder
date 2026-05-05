from __future__ import annotations

import logging
import re
from datetime import datetime

from src.models.enums import Currency, PropertyType, Source
from src.models.listing import ListingCreate

from .config import FEATURE_TEXT_FIELDS, LISTING_URL_TEMPLATE, PROPERTY_TYPE_MAP

logger = logging.getLogger(__name__)


class Yad2Parser:
    """Transforms raw Yad2 API listing dicts into ListingCreate objects."""

    @staticmethod
    def extract_feed_items(api_response: dict) -> list[dict]:
        """Extract listing items from the API response, filtering out non-listing types."""
        feed = api_response.get("feed", {})
        items = feed.get("feed_items", [])

        # Log all item types found for debugging
        from collections import Counter
        type_counts = Counter(item.get("type", "unknown") for item in items)
        logger.info("Feed item types on page: %s (total %d items)", dict(type_counts), len(items))

        # Keep actual listings
        kept = [item for item in items if item.get("type") in ("ad", "advanced_ad")]
        skipped = len(items) - len(kept)
        if skipped > 0:
            logger.info("Skipped %d non-listing items (types: %s)",
                        skipped, {t: c for t, c in type_counts.items() if t not in ("ad", "advanced_ad")})
        return kept

    @staticmethod
    def get_pagination(api_response: dict) -> dict:
        """Extract pagination info from API response."""
        feed = api_response.get("feed", {})
        return {
            "current_page": feed.get("current_page", 1),
            "total_pages": feed.get("total_pages", 1),
            "total_items": feed.get("total_items", 0),
            "page_size": feed.get("page_size", 50),
        }

    @staticmethod
    def parse_listing(raw: dict) -> ListingCreate | None:
        """Parse a single Yad2 feed item into a ListingCreate."""
        try:
            token = raw.get("id") or raw.get("link_token") or raw.get("token") or raw.get("ad_number") or ""
            if not token:
                logger.debug(
                    "Yad2 listing missing id/link_token (type=%s, keys=%s), skipping",
                    raw.get("type"), list(raw.keys())[:15],
                )
                return None

            # Parse price: "4,000 ₪" -> 4000.0
            price = Yad2Parser._parse_price(raw.get("price", ""))
            currency = Currency.ILS if raw.get("currency") == "₪" else Currency.USD

            # Parse rooms from row_4 or Rooms field
            rooms = Yad2Parser._parse_rooms(raw)

            # Parse floor from row_4
            floor = Yad2Parser._parse_floor(raw)

            # Parse property type
            property_type = Yad2Parser._parse_property_type(raw.get("HomeTypeID_text", ""))

            # Parse features from *_text fields
            features = Yad2Parser._parse_features(raw)

            # Parse coordinates
            coords = raw.get("coordinates", {})
            latitude = Yad2Parser._safe_float(coords.get("latitude"))
            longitude = Yad2Parser._safe_float(coords.get("longitude"))

            # Parse dates
            posted_at = Yad2Parser._parse_datetime(raw.get("date_added"))
            updated_at = Yad2Parser._parse_datetime(raw.get("date"))
            entry_date = Yad2Parser._parse_date(raw.get("date_of_entry"))

            # Images
            image_urls = raw.get("images_urls", []) or []

            return ListingCreate(
                source=Source.YAD2,
                source_id=str(token),
                source_url=LISTING_URL_TEMPLATE.format(token=token),
                title=raw.get("row_2", "") or raw.get("title_2", "") or "",
                price=price,
                currency=currency,
                city=raw.get("city", "").strip(),
                neighborhood=raw.get("neighborhood") or None,
                street=raw.get("street") or None,
                house_number=raw.get("address_home_number") or None,
                rooms=rooms,
                floor=floor,
                area_sqm=Yad2Parser._safe_float(raw.get("square_meters")),
                description=raw.get("search_text") or None,
                image_urls=image_urls,
                property_type=property_type,
                contact_name=raw.get("contact_name") or raw.get("merchant_name") or None,
                posted_at=posted_at,
                updated_at=updated_at,
                entry_date=entry_date,
                latitude=latitude,
                longitude=longitude,
                raw_data=raw,
                **features,
            )
        except Exception as e:
            logger.error("Failed to parse Yad2 listing %s: %s", raw.get("id", "?"), e, exc_info=True)
            return None

    @staticmethod
    def _parse_price(price_str: str) -> float | None:
        """Parse '4,000 ₪' or '4000' into float."""
        if not price_str:
            return None
        # Remove currency symbols, commas, spaces
        cleaned = re.sub(r"[^\d.]", "", price_str.replace(",", ""))
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    @staticmethod
    def _parse_rooms(raw: dict) -> float | None:
        """Extract rooms from Rooms field or row_4."""
        # Direct field first
        rooms = raw.get("Rooms") or raw.get("Rooms_text")
        if rooms is not None:
            try:
                return float(rooms)
            except (ValueError, TypeError):
                pass

        # Try row_4
        for item in raw.get("row_4", []):
            if isinstance(item, dict) and item.get("key") == "rooms":
                try:
                    return float(item["value"])
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _parse_floor(raw: dict) -> int | None:
        """Extract floor from row_4."""
        for item in raw.get("row_4", []):
            if isinstance(item, dict) and item.get("key") == "floor":
                try:
                    return int(item["value"])
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _parse_property_type(hebrew_type: str) -> PropertyType | None:
        """Map Hebrew property type text to PropertyType enum."""
        if not hebrew_type:
            return None
        mapped = PROPERTY_TYPE_MAP.get(hebrew_type.strip())
        if mapped:
            try:
                return PropertyType(mapped)
            except ValueError:
                pass
        return PropertyType.OTHER if hebrew_type else None

    @staticmethod
    def _parse_features(raw: dict) -> dict:
        """Parse feature text fields into boolean flags."""
        features = {}
        for text_field, bool_field in FEATURE_TEXT_FIELDS.items():
            value = raw.get(text_field, "")
            if not value or value.strip() == "":
                features[bool_field] = None  # Unknown
            elif value.strip() == "אין":  # "none" / "no"
                features[bool_field] = False
            else:
                features[bool_field] = True
        return features

    @staticmethod
    def _parse_datetime(dt_str: str | None) -> datetime | None:
        """Parse '2026-02-16 13:07:39' into datetime."""
        if not dt_str:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_date(dt_str: str | None):
        """Parse '2026-02-24 00:00:00' into date."""
        dt = Yad2Parser._parse_datetime(dt_str)
        return dt.date() if dt else None

    @staticmethod
    def _safe_float(value) -> float | None:
        """Safely convert a value to float."""
        if value is None:
            return None
        try:
            cleaned = str(value).strip()
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
