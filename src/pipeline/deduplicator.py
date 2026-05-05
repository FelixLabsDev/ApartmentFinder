from __future__ import annotations

import hashlib
import logging

from src.models.listing import ListingCreate

logger = logging.getLogger(__name__)

# Price bucket size in ILS for fuzzy matching (200 ILS tolerance)
PRICE_BUCKET_SIZE = 200


class ListingDeduplicator:
    """Detect and remove duplicate listings across sources.

    Uses a SHA256 fingerprint based on: city, street, house_number, rooms,
    floor, and price_bucket.  Two listings with the same fingerprint are
    considered duplicates even if they come from different sources.
    """

    @staticmethod
    def compute_fingerprint(listing: ListingCreate) -> str:
        """Compute a SHA256 fingerprint for deduplication.

        The fingerprint is based on location + property characteristics so that
        the same physical apartment listed on both Yad2 and Facebook will produce
        the same hash.
        """
        city = (listing.city or "").strip().lower()
        street = (listing.street or "").strip().lower()
        house_number = (listing.house_number or "").strip().lower()
        rooms = str(listing.rooms or "")
        floor = str(listing.floor or "")

        # Bucket prices to tolerate small differences (e.g., 5000 vs 5100)
        price_bucket = ""
        if listing.price is not None:
            price_bucket = str(int(listing.price // PRICE_BUCKET_SIZE))

        fingerprint_input = "|".join([city, street, house_number, rooms, floor, price_bucket])
        return hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()

    def deduplicate_batch(self, listings: list[ListingCreate]) -> list[ListingCreate]:
        """Remove duplicates from a batch, keeping the most complete listing.

        Duplicates are identified by fingerprint.  When multiple listings share
        a fingerprint, the one with the most filled fields is kept.
        """
        fingerprint_map: dict[str, list[tuple[int, ListingCreate]]] = {}

        for idx, listing in enumerate(listings):
            fp = self.compute_fingerprint(listing)
            if fp not in fingerprint_map:
                fingerprint_map[fp] = []
            fingerprint_map[fp].append((idx, listing))

        result: list[ListingCreate] = []
        duplicates_removed = 0

        for fp, candidates in fingerprint_map.items():
            if len(candidates) == 1:
                result.append(candidates[0][1])
            else:
                # Pick the most complete listing
                best = max(candidates, key=lambda c: self._completeness_score(c[1]))
                result.append(best[1])
                duplicates_removed += len(candidates) - 1
                dropped = [c[1] for c in candidates if c is not best]
                logger.info(
                    "Dedup: merged %d listings (kept %s-%s, dropped %s)",
                    len(candidates),
                    best[1].source.value, best[1].source_id,
                    [(l.source.value, l.source_id) for l in dropped],
                )

        if duplicates_removed > 0:
            logger.info(
                "Deduplication: removed %d duplicates from %d listings → %d unique",
                duplicates_removed, len(listings), len(result),
            )

        return result

    @staticmethod
    def _completeness_score(listing: ListingCreate) -> int:
        """Score how many optional fields are populated."""
        score = 0
        fields_to_check = [
            listing.title, listing.description, listing.neighborhood,
            listing.street, listing.house_number, listing.price,
            listing.rooms, listing.floor, listing.area_sqm,
            listing.property_type, listing.contact_name, listing.contact_phone,
            listing.latitude, listing.longitude, listing.entry_date,
            listing.posted_at,
        ]
        for field in fields_to_check:
            if field is not None and field != "" and field != []:
                score += 1

        # Bonus for having images
        score += len(listing.image_urls)

        # Bonus for having feature data (not None)
        feature_fields = [
            listing.has_parking, listing.has_elevator, listing.has_balcony,
            listing.has_air_conditioning, listing.has_mamad, listing.is_accessible,
            listing.is_furnished, listing.has_bars, listing.has_storage,
            listing.pet_friendly,
        ]
        for f in feature_fields:
            if f is not None:
                score += 1

        return score
