from __future__ import annotations

from src.models.listing import ListingCreate


class TelegramFormatter:
    """Format ListingCreate objects into Telegram HTML messages."""

    @staticmethod
    def format_listing(listing: ListingCreate) -> str:
        """Format a single listing as an HTML message for Telegram."""
        parts: list[str] = []

        # Title line
        rooms_str = f"{listing.rooms}r" if listing.rooms else ""
        city = listing.city or "Unknown"
        price_str = TelegramFormatter._format_price(listing.price, str(listing.currency))

        if rooms_str and price_str:
            parts.append(f"<b>{rooms_str} in {city}</b> — {price_str}")
        elif price_str:
            parts.append(f"<b>{city}</b> — {price_str}")
        else:
            parts.append(f"<b>{city}</b>")

        # Address line
        address_parts: list[str] = []
        if listing.street:
            addr = listing.street
            if listing.house_number:
                addr += f" {listing.house_number}"
            address_parts.append(addr)
        if listing.neighborhood:
            address_parts.append(listing.neighborhood)
        if listing.floor is not None:
            floor_str = f"floor {listing.floor}"
            if listing.total_floors is not None:
                floor_str += f"/{listing.total_floors}"
            address_parts.append(floor_str)
        if listing.area_sqm:
            address_parts.append(f"{listing.area_sqm:.0f}m\u00b2")

        if address_parts:
            parts.append(", ".join(address_parts))

        # Features line
        features = TelegramFormatter._format_features(listing)
        if features:
            parts.append(features)

        # Property type
        if listing.property_type:
            parts.append(f"Type: {listing.property_type}")

        # Description snippet (first 100 chars)
        if listing.description:
            desc = listing.description[:100]
            if len(listing.description) > 100:
                desc += "..."
            parts.append(f"<i>{desc}</i>")

        # Link
        if listing.source_url:
            parts.append(f'<a href="{listing.source_url}">View on {listing.source}</a>')

        return "\n".join(parts)

    @staticmethod
    def format_batch(listings: list[ListingCreate], header: str | None = None) -> str:
        """Format multiple listings into a single message."""
        parts: list[str] = []

        if header:
            parts.append(f"<b>{header}</b>")
            parts.append("")

        for i, listing in enumerate(listings):
            if i > 0:
                parts.append("---")
            parts.append(TelegramFormatter.format_listing(listing))

        return "\n".join(parts)

    @staticmethod
    def format_summary(total_new: int, total_sources: int) -> str:
        """Format a summary notification."""
        if total_new == 0:
            return "No new listings found in this scan."
        return (
            f"Found <b>{total_new}</b> new listing{'s' if total_new != 1 else ''} "
            f"from {total_sources} source{'s' if total_sources != 1 else ''}."
        )

    @staticmethod
    def _format_price(price: float | None, currency: str) -> str:
        if price is None:
            return ""
        formatted = f"{price:,.0f}"
        if currency == "ILS":
            return f"{formatted} \u20aa"
        elif currency == "USD":
            return f"${formatted}"
        return f"{formatted} {currency}"

    @staticmethod
    def _format_features(listing: ListingCreate) -> str:
        """Build a pipe-separated feature string."""
        features: list[str] = []
        if listing.has_parking:
            features.append("Parking")
        if listing.has_elevator:
            features.append("Elevator")
        if listing.has_balcony:
            features.append("Balcony")
        if listing.has_air_conditioning:
            features.append("A/C")
        if listing.has_mamad:
            features.append("Mamad")
        if listing.is_furnished:
            features.append("Furnished")
        if listing.pet_friendly:
            features.append("Pet OK")
        if listing.has_storage:
            features.append("Storage")
        if listing.is_accessible:
            features.append("Accessible")
        return " | ".join(features)
