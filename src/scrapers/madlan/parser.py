from __future__ import annotations

import logging
import re
from datetime import datetime

from src.models.enums import Currency, PropertyType, Source
from src.models.listing import ListingCreate

from .config import LISTING_URL_TEMPLATE, PROPERTY_TYPE_MAP

logger = logging.getLogger(__name__)


class MadlanParser:
    """Transforms raw Madlan listing data into ListingCreate objects.

    Handles two data formats:
    1. API data intercepted from network requests (structured JSON)
    2. DOM-extracted data from rendered listing cards (less structured)
    """

    @staticmethod
    def parse_api_listing(raw: dict) -> ListingCreate | None:
        """Parse a single listing from Madlan's API response."""
        try:
            listing_id = raw.get("listingId") or raw.get("id") or raw.get("adId") or ""
            if not listing_id:
                logger.debug("Madlan listing missing ID, keys=%s", list(raw.keys())[:15])
                return None

            price = MadlanParser._parse_price(raw)
            rooms = MadlanParser._safe_float(
                raw.get("rooms") or raw.get("numberOfRooms")
            )
            floor = MadlanParser._safe_int(raw.get("floor"))
            total_floors = MadlanParser._safe_int(raw.get("totalFloors") or raw.get("numberOfFloors"))
            area_sqm = MadlanParser._safe_float(raw.get("area") or raw.get("squareMeters"))

            # Address components
            city = raw.get("city") or raw.get("cityName") or ""
            neighborhood = raw.get("neighborhood") or raw.get("neighborhoodName") or None
            street = raw.get("street") or raw.get("streetName") or None
            house_number = raw.get("houseNumber") or raw.get("streetNumber") or None

            # Coordinates
            latitude = MadlanParser._safe_float(raw.get("lat") or raw.get("latitude"))
            longitude = MadlanParser._safe_float(raw.get("lng") or raw.get("longitude"))

            # Images
            image_urls = MadlanParser._extract_images(raw)

            # Property type
            property_type = MadlanParser._parse_property_type(
                raw.get("propertyType") or raw.get("assetType") or ""
            )

            # Features
            features = MadlanParser._parse_features(raw)

            # Dates
            posted_at = MadlanParser._parse_datetime(
                raw.get("publishedAt") or raw.get("createdAt") or raw.get("updatedDate")
            )
            updated_at = MadlanParser._parse_datetime(
                raw.get("updatedAt") or raw.get("updatedDate")
            )
            entry_date = MadlanParser._parse_date(raw.get("entryDate") or raw.get("entranceDate"))

            # Description
            description = raw.get("description") or raw.get("text") or None

            # Contact
            contact_name = raw.get("contactName") or raw.get("agentName") or None
            contact_phone = raw.get("contactPhone") or raw.get("phone") or None

            # Title
            title = MadlanParser._build_title(raw, city, street, rooms, area_sqm)

            return ListingCreate(
                source=Source.MADLAN,
                source_id=str(listing_id),
                source_url=LISTING_URL_TEMPLATE.format(listing_id=listing_id),
                title=title,
                price=price,
                currency=Currency.ILS,
                city=city.strip() if city else "unknown",
                neighborhood=neighborhood,
                street=street,
                house_number=str(house_number) if house_number else None,
                rooms=rooms,
                floor=floor,
                total_floors=total_floors,
                area_sqm=area_sqm,
                description=description,
                image_urls=image_urls,
                property_type=property_type,
                contact_name=contact_name,
                contact_phone=contact_phone,
                posted_at=posted_at,
                updated_at=updated_at,
                entry_date=entry_date,
                latitude=latitude,
                longitude=longitude,
                raw_data=raw,
                **features,
            )
        except Exception as e:
            logger.error(
                "Failed to parse Madlan listing %s: %s",
                raw.get("listingId", raw.get("id", "?")),
                e,
                exc_info=True,
            )
            return None

    @staticmethod
    def parse_dom_listing(card_data: dict) -> ListingCreate | None:
        """Parse a listing extracted from the DOM (less structured)."""
        try:
            listing_id = card_data.get("id") or ""
            if not listing_id:
                return None

            price = MadlanParser._parse_price_str(card_data.get("price", ""))
            rooms = MadlanParser._safe_float(card_data.get("rooms"))
            floor = MadlanParser._safe_int(card_data.get("floor"))
            area_sqm = MadlanParser._safe_float(card_data.get("area_sqm"))
            city = card_data.get("city") or ""
            neighborhood = card_data.get("neighborhood") or None
            street = card_data.get("street") or None

            image_urls = card_data.get("image_urls") or []
            description = card_data.get("description") or None
            title = card_data.get("title") or ""

            return ListingCreate(
                source=Source.MADLAN,
                source_id=str(listing_id),
                source_url=LISTING_URL_TEMPLATE.format(listing_id=listing_id),
                title=title,
                price=price,
                currency=Currency.ILS,
                city=city.strip() if city else "unknown",
                neighborhood=neighborhood,
                street=street,
                rooms=rooms,
                floor=floor,
                area_sqm=area_sqm,
                description=description,
                image_urls=image_urls,
                raw_data=card_data,
            )
        except Exception as e:
            logger.error("Failed to parse Madlan DOM card %s: %s", card_data.get("id", "?"), e)
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_price(raw: dict) -> float | None:
        """Extract price from various field patterns."""
        # Try structured price field first
        price = raw.get("price") or raw.get("monthlyRent") or raw.get("rentPrice")
        if price is not None:
            try:
                return float(price)
            except (ValueError, TypeError):
                pass

        # Try formatted string
        price_str = raw.get("priceText") or raw.get("formattedPrice") or ""
        return MadlanParser._parse_price_str(price_str)

    @staticmethod
    def _parse_price_str(price_str: str) -> float | None:
        """Parse '4,000 ₪' or '₪4,000' into float."""
        if not price_str:
            return None
        cleaned = re.sub(r"[^\d.]", "", price_str.replace(",", ""))
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    @staticmethod
    def _extract_images(raw: dict) -> list[str]:
        """Extract image URLs from various formats."""
        # Direct list of URLs
        images = raw.get("images") or raw.get("imageUrls") or raw.get("photos") or []
        if isinstance(images, list):
            urls = []
            for img in images:
                if isinstance(img, str):
                    urls.append(img)
                elif isinstance(img, dict):
                    url = img.get("url") or img.get("src") or img.get("imageUrl") or ""
                    if url:
                        urls.append(url)
            return urls

        # Single image
        single = raw.get("imageUrl") or raw.get("mainImage") or ""
        return [single] if single else []

    @staticmethod
    def _parse_property_type(type_str: str) -> PropertyType | None:
        """Map Hebrew/English property type to PropertyType enum."""
        if not type_str:
            return None

        # Try Hebrew mapping
        mapped = PROPERTY_TYPE_MAP.get(type_str.strip())
        if mapped:
            try:
                return PropertyType(mapped)
            except ValueError:
                pass

        # Try direct English match
        type_lower = type_str.lower().strip()
        for pt in PropertyType:
            if pt.value == type_lower:
                return pt

        return PropertyType.OTHER if type_str else None

    @staticmethod
    def _parse_features(raw: dict) -> dict:
        """Extract boolean feature flags."""
        features: dict[str, bool | None] = {}

        feature_map = {
            "has_parking": ["parking", "hasParking", "חניה"],
            "has_elevator": ["elevator", "hasElevator", "מעלית"],
            "has_balcony": ["balcony", "hasBalcony", "מרפסת"],
            "has_air_conditioning": ["airConditioning", "hasAirConditioning", "ac", "מיזוג"],
            "has_mamad": ["mamad", "hasMamad", "safeRoom", "ממ\"ד"],
            "is_accessible": ["accessible", "isAccessible", "נגיש"],
            "is_furnished": ["furnished", "isFurnished", "מרוהש"],
            "has_bars": ["bars", "hasBars", "סורגים"],
            "has_storage": ["storage", "hasStorage", "machsan", "מחסן"],
            "pet_friendly": ["petFriendly", "pets", "petsAllowed", "חיות"],
        }

        # Check amenities array if present
        amenities = raw.get("amenities") or raw.get("features") or []
        amenity_set = set()
        if isinstance(amenities, list):
            for a in amenities:
                if isinstance(a, str):
                    amenity_set.add(a.lower())
                elif isinstance(a, dict):
                    name = (a.get("name") or a.get("key") or "").lower()
                    if name:
                        amenity_set.add(name)

        for bool_field, keys in feature_map.items():
            # Check direct fields
            value = None
            for key in keys:
                if key in raw:
                    val = raw[key]
                    if isinstance(val, bool):
                        value = val
                    elif val is not None:
                        value = bool(val)
                    break

            # Check amenities set
            if value is None and amenity_set:
                for key in keys:
                    if key.lower() in amenity_set:
                        value = True
                        break

            features[bool_field] = value

        return features

    @staticmethod
    def _build_title(raw: dict, city: str, street: str | None, rooms: float | None, area: float | None) -> str:
        """Build a readable title from available data."""
        title = raw.get("title") or raw.get("headline") or ""
        if title:
            return title

        parts = []
        prop_type = raw.get("propertyType") or raw.get("assetType") or ""
        if prop_type:
            parts.append(prop_type)
        if rooms:
            parts.append(f"{rooms} חדרים")
        if street:
            parts.append(street)
        elif city:
            parts.append(city)
        if area:
            parts.append(f"{area} מ\"ר")

        return " | ".join(parts) if parts else "Madlan Listing"

    @staticmethod
    def _parse_datetime(dt_str: str | None) -> datetime | None:
        if not dt_str:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(dt_str, fmt)
            except (ValueError, TypeError):
                continue
        return None

    @staticmethod
    def _parse_date(dt_str: str | None):
        dt = MadlanParser._parse_datetime(dt_str)
        return dt.date() if dt else None

    @staticmethod
    def _safe_float(value) -> float | None:
        if value is None:
            return None
        try:
            cleaned = str(value).strip()
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value) -> int | None:
        if value is None:
            return None
        try:
            return int(float(str(value).strip()))
        except (ValueError, TypeError):
            return None
