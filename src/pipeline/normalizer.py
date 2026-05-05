from __future__ import annotations

import logging
import re

from src.models.enums import Currency, PropertyType
from src.models.listing import ListingCreate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hebrew city name → canonical English slug
# ---------------------------------------------------------------------------
CITY_NAME_MAP: dict[str, str] = {
    # Hebrew names
    "תל אביב יפו": "tel-aviv",
    "תל אביב": "tel-aviv",
    "תל-אביב": "tel-aviv",
    "ירושלים": "jerusalem",
    "חיפה": "haifa",
    "באר שבע": "beer-sheva",
    "נתניה": "netanya",
    "ראשון לציון": "rishon-lezion",
    "פתח תקווה": "petah-tikva",
    "פתח תקוה": "petah-tikva",
    "אשדוד": "ashdod",
    "הרצליה": "herzliya",
    "רעננה": "raanana",
    "כפר סבא": "kfar-saba",
    "רחובות": "rehovot",
    "מודיעין": "modiin",
    "מודיעין מכבים רעות": "modiin",
    "גבעתיים": "givatayim",
    "רמת גן": "ramat-gan",
    "בת ים": "bat-yam",
    "חולון": "holon",
    "הוד השרון": "hod-hasharon",
    "רמת השרון": "ramat-hasharon",
    "אילת": "eilat",
    "טבריה": "tiberias",
    "נצרת": "nazareth",
    "עכו": "akko",
    "בני ברק": "bnei-brak",
    # English variants
    "tel aviv": "tel-aviv",
    "tel-aviv": "tel-aviv",
    "tel aviv-yafo": "tel-aviv",
    "tel aviv yafo": "tel-aviv",
    "jerusalem": "jerusalem",
    "haifa": "haifa",
    "beer sheva": "beer-sheva",
    "beer-sheva": "beer-sheva",
    "beersheba": "beer-sheva",
    "netanya": "netanya",
    "rishon lezion": "rishon-lezion",
    "rishon-lezion": "rishon-lezion",
    "petah tikva": "petah-tikva",
    "petah-tikva": "petah-tikva",
    "ashdod": "ashdod",
    "herzliya": "herzliya",
    "raanana": "raanana",
    "ra'anana": "raanana",
    "kfar saba": "kfar-saba",
    "kfar-saba": "kfar-saba",
    "rehovot": "rehovot",
    "modiin": "modiin",
    "modi'in": "modiin",
    "givatayim": "givatayim",
    "ramat gan": "ramat-gan",
    "ramat-gan": "ramat-gan",
    "bat yam": "bat-yam",
    "bat-yam": "bat-yam",
    "holon": "holon",
    "bnei brak": "bnei-brak",
    "bnei-brak": "bnei-brak",
    "eilat": "eilat",
}

# Hebrew property type → PropertyType enum
PROPERTY_TYPE_MAP: dict[str, PropertyType] = {
    "דירה": PropertyType.APARTMENT,
    "דירת גן": PropertyType.GARDEN_APARTMENT,
    "בית פרטי": PropertyType.HOUSE,
    "קוטג'": PropertyType.HOUSE,
    "פנטהאוז": PropertyType.PENTHOUSE,
    "סטודיו": PropertyType.STUDIO,
    "לופט": PropertyType.STUDIO,
    "דופלקס": PropertyType.DUPLEX,
    "דירת גג": PropertyType.ROOF_APARTMENT,
    "יחידת דיור": PropertyType.UNIT,
}

# Approximate USD→ILS rate (updated periodically)
USD_TO_ILS_RATE = 3.7


class ListingNormalizer:
    """Normalize scraped listings into a consistent canonical form."""

    def normalize(self, listing: ListingCreate) -> ListingCreate:
        """Apply all normalization steps to a single listing."""
        data = listing.model_dump()

        data["city"] = self._normalize_city(data.get("city", ""))
        data["price"], data["currency"] = self._normalize_price(
            data.get("price"), data.get("currency", Currency.ILS)
        )
        data["contact_phone"] = self._normalize_phone(data.get("contact_phone"))
        data["property_type"] = self._normalize_property_type(data.get("property_type"))
        data["title"] = self._clean_text(data.get("title", ""))
        data["description"] = self._clean_text(data.get("description") or "")
        if not data["description"]:
            data["description"] = None

        return ListingCreate(**data)

    def normalize_batch(self, listings: list[ListingCreate]) -> list[ListingCreate]:
        """Normalize a list of listings."""
        normalized = []
        for listing in listings:
            try:
                normalized.append(self.normalize(listing))
            except Exception:
                logger.exception("Failed to normalize listing %s", listing.source_id)
                normalized.append(listing)  # Keep original on error
        return normalized

    # ------------------------------------------------------------------
    # City normalization
    # ------------------------------------------------------------------

    def _normalize_city(self, city: str) -> str:
        """Map Hebrew/English city name to canonical slug."""
        if not city:
            return city

        stripped = city.strip().lower()
        canonical = CITY_NAME_MAP.get(stripped)
        if canonical:
            return canonical

        # Try without dashes/spaces variations
        no_dash = stripped.replace("-", " ")
        canonical = CITY_NAME_MAP.get(no_dash)
        if canonical:
            return canonical

        # Return original stripped value if no mapping found
        return stripped

    # ------------------------------------------------------------------
    # Price normalization (convert USD → ILS)
    # ------------------------------------------------------------------

    def _normalize_price(
        self, price: float | None, currency: str | Currency
    ) -> tuple[float | None, Currency]:
        """Convert all prices to ILS."""
        if price is None:
            return None, Currency.ILS

        currency_str = str(currency)
        if currency_str == Currency.USD:
            return round(price * USD_TO_ILS_RATE, 0), Currency.ILS

        return price, Currency.ILS

    # ------------------------------------------------------------------
    # Phone normalization
    # ------------------------------------------------------------------

    def _normalize_phone(self, phone: str | None) -> str | None:
        """Normalize Israeli phone numbers to +972XXXXXXXXX format."""
        if not phone:
            return None

        # Strip all non-digit characters
        digits = re.sub(r"\D", "", phone)

        if not digits:
            return None

        # Handle Israeli numbers
        if digits.startswith("972"):
            digits = digits[3:]
        elif digits.startswith("0"):
            digits = digits[1:]

        # Israeli mobile numbers are 9 digits (after removing leading 0/972)
        if len(digits) == 9 and digits[0] == "5":
            return f"+972{digits}"

        # Landline numbers are 8 digits
        if len(digits) == 8:
            return f"+972{digits}"

        # Return cleaned but unformatted if we can't parse
        return phone.strip() if phone else None

    # ------------------------------------------------------------------
    # Property type normalization
    # ------------------------------------------------------------------

    def _normalize_property_type(self, pt: str | PropertyType | None) -> PropertyType | None:
        """Ensure property type is a valid enum value."""
        if pt is None:
            return None

        if isinstance(pt, PropertyType):
            return pt

        pt_str = str(pt).strip()

        # Try direct enum match
        try:
            return PropertyType(pt_str)
        except ValueError:
            pass

        # Try Hebrew mapping
        canonical = PROPERTY_TYPE_MAP.get(pt_str)
        if canonical:
            return canonical

        return PropertyType.OTHER

    # ------------------------------------------------------------------
    # Text cleanup
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """Remove excess whitespace and normalize line breaks."""
        if not text:
            return ""
        # Collapse multiple whitespace/newlines
        text = re.sub(r"\s+", " ", text).strip()
        return text
