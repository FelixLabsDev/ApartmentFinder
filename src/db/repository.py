from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, delete, or_, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.filters import SearchFilter
from src.models.listing import ListingCreate

from .tables import FacebookCityRow, FolderRow, ListingRow, NoteRow, ScrapeRunRow, SearchProfileRow


class ListingRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert_listings(
        self, listings: list[ListingCreate], fingerprints: list[str]
    ) -> tuple[int, int]:
        """Insert new or update existing listings. Returns (total, new_count)."""
        new_count = 0
        for listing, fingerprint in zip(listings, fingerprints):
            existing = await self._session.execute(
                select(ListingRow).where(
                    ListingRow.source == listing.source,
                    ListingRow.source_id == listing.source_id,
                )
            )
            row = existing.scalar_one_or_none()

            if row is None:
                row = ListingRow(
                    id=str(uuid.uuid4()),
                    fingerprint=fingerprint,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow(),
                    **listing.model_dump(exclude={"raw_data"}),
                    raw_data=listing.raw_data,
                )
                self._session.add(row)
                new_count += 1
            else:
                # Update existing listing with fresh data
                row.last_seen_at = datetime.utcnow()
                row.fingerprint = fingerprint
                row.price = listing.price
                row.title = listing.title
                row.description = listing.description
                row.image_urls = listing.image_urls
                row.updated_at = listing.updated_at
                row.is_active = True
                if listing.ai_guessed_fields:
                    row.ai_guessed_fields = listing.ai_guessed_fields

        await self._session.flush()
        return len(listings), new_count

    _SORT_MAP = {
        "newest": func.coalesce(ListingRow.posted_at, ListingRow.first_seen_at).desc(),
        "price_asc": ListingRow.price.asc(),
        "price_desc": ListingRow.price.desc(),
        "rooms_asc": ListingRow.rooms.asc(),
        "area_desc": ListingRow.area_sqm.desc(),
        "price_per_sqm_asc": (ListingRow.price / ListingRow.area_sqm).asc(),
        "price_per_sqm_desc": (ListingRow.price / ListingRow.area_sqm).desc(),
    }

    async def get_listings(
        self,
        search_filter: SearchFilter | None = None,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = True,
        sort_by: str | None = None,
    ) -> list[ListingRow]:
        """Query listings matching filter criteria."""
        stmt = select(ListingRow)

        if active_only:
            stmt = stmt.where(ListingRow.is_active == True)  # noqa: E712

        if search_filter:
            stmt = self._apply_filter(stmt, search_filter)

        order = self._SORT_MAP.get(sort_by or "newest", ListingRow.first_seen_at.desc())
        stmt = stmt.order_by(order).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_new_since(
        self, since: datetime, search_filter: SearchFilter | None = None
    ) -> list[ListingRow]:
        """Get listings first seen after a given timestamp."""
        stmt = select(ListingRow).where(
            ListingRow.first_seen_at > since,
            ListingRow.is_active == True,  # noqa: E712
        )

        if search_filter:
            stmt = self._apply_filter(stmt, search_filter)

        stmt = stmt.order_by(ListingRow.first_seen_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_inactive(self, source: str, active_source_ids: set[str]) -> int:
        """Mark listings not in active_source_ids as inactive. Returns count updated."""
        stmt = (
            update(ListingRow)
            .where(
                ListingRow.source == source,
                ListingRow.is_active == True,  # noqa: E712
                ListingRow.source_id.not_in(active_source_ids),
            )
            .values(is_active=False)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def delete_all(self) -> int:
        """Delete all listings. Returns count deleted."""
        result = await self._session.execute(delete(ListingRow))
        await self._session.flush()
        return result.rowcount

    async def get_listings_by_keys(self, keys: list[str]) -> list[ListingRow]:
        """Fetch listings by their source-source_id keys (e.g. 'facebook-123')."""
        if not keys:
            return []
        conditions = []
        for key in keys:
            parts = key.split("-", 1)
            if len(parts) == 2:
                conditions.append(
                    and_(ListingRow.source == parts[0], ListingRow.source_id == parts[1])
                )
        if not conditions:
            return []
        stmt = select(ListingRow).where(or_(*conditions))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_listing_by_fingerprint(self, fingerprint: str) -> ListingRow | None:
        """Check if listing exists by dedup fingerprint."""
        result = await self._session.execute(
            select(ListingRow).where(ListingRow.fingerprint == fingerprint)
        )
        return result.scalar_one_or_none()

    def _apply_filter(self, stmt, f: SearchFilter):
        """Apply SearchFilter criteria to a SELECT statement."""
        if f.sources:
            stmt = stmt.where(ListingRow.source.in_(f.sources))
        if f.cities:
            # Match against preset_city_name (user-configured name) with fallback to raw city
            lower_cities = [c.lower() for c in f.cities]
            stmt = stmt.where(
                or_(
                    func.lower(ListingRow.preset_city_name).in_(lower_cities),
                    ListingRow.city.in_(lower_cities),
                )
            )
        if f.neighborhoods:
            stmt = stmt.where(ListingRow.neighborhood.in_([n.lower() for n in f.neighborhoods]))
        if f.min_price is not None:
            stmt = stmt.where(ListingRow.price >= f.min_price)
        if f.max_price is not None:
            stmt = stmt.where(ListingRow.price <= f.max_price)
        if f.min_rooms is not None:
            stmt = stmt.where(ListingRow.rooms >= f.min_rooms)
        if f.max_rooms is not None:
            stmt = stmt.where(ListingRow.rooms <= f.max_rooms)
        if f.min_area_sqm is not None:
            stmt = stmt.where(ListingRow.area_sqm >= f.min_area_sqm)
        if f.max_area_sqm is not None:
            stmt = stmt.where(ListingRow.area_sqm <= f.max_area_sqm)
        if f.min_floor is not None:
            stmt = stmt.where(ListingRow.floor >= f.min_floor)
        if f.max_floor is not None:
            stmt = stmt.where(ListingRow.floor <= f.max_floor)
        if f.property_types:
            stmt = stmt.where(ListingRow.property_type.in_(f.property_types))
        if f.min_entry_date is not None:
            stmt = stmt.where(ListingRow.entry_date >= f.min_entry_date)
        if f.max_entry_date is not None:
            stmt = stmt.where(ListingRow.entry_date <= f.max_entry_date)

        # Feature filters
        if f.require_parking is True:
            stmt = stmt.where(ListingRow.has_parking == True)  # noqa: E712
        if f.require_elevator is True:
            stmt = stmt.where(ListingRow.has_elevator == True)  # noqa: E712
        if f.require_balcony is True:
            stmt = stmt.where(ListingRow.has_balcony == True)  # noqa: E712
        if f.require_air_conditioning is True:
            stmt = stmt.where(ListingRow.has_air_conditioning == True)  # noqa: E712
        if f.require_mamad is True:
            stmt = stmt.where(ListingRow.has_mamad == True)  # noqa: E712
        if f.require_pet_friendly is True:
            stmt = stmt.where(ListingRow.pet_friendly == True)  # noqa: E712
        if f.require_furnished is True:
            stmt = stmt.where(ListingRow.is_furnished == True)  # noqa: E712

        # Keyword search (title + description)
        for kw in f.keywords:
            pattern = f"%{kw}%"
            stmt = stmt.where(
                or_(
                    ListingRow.title.ilike(pattern),
                    ListingRow.description.ilike(pattern),
                )
            )
        for kw in f.exclude_keywords:
            pattern = f"%{kw}%"
            stmt = stmt.where(
                ~or_(
                    ListingRow.title.ilike(pattern),
                    ListingRow.description.ilike(pattern),
                )
            )

        return stmt

    async def set_rating(self, source: str, source_id: str, rating: str | None) -> bool:
        """Set or clear a rating on a listing. Returns True if listing was found."""
        result = await self._session.execute(
            select(ListingRow).where(
                ListingRow.source == source,
                ListingRow.source_id == source_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.rating = rating
        await self._session.flush()
        return True

    async def set_ratings_bulk(self, ratings: dict[str, str]) -> int:
        """Bulk set ratings. Keys are 'source-source_id', values are 'liked'/'disliked'.
        Returns count of updated listings."""
        count = 0
        for key, rating in ratings.items():
            parts = key.split("-", 1)
            if len(parts) != 2:
                continue
            result = await self._session.execute(
                select(ListingRow).where(
                    ListingRow.source == parts[0],
                    ListingRow.source_id == parts[1],
                )
            )
            row = result.scalar_one_or_none()
            if row and row.rating != rating:
                row.rating = rating
                count += 1
        await self._session.flush()
        return count

    async def mark_seen(self, source: str, source_id: str) -> bool:
        """Mark a listing as seen. Returns True if found."""
        result = await self._session.execute(
            select(ListingRow).where(
                ListingRow.source == source,
                ListingRow.source_id == source_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        if row.seen_at is None:
            row.seen_at = datetime.utcnow()
            await self._session.flush()
        return True

    async def get_all_ratings(self) -> dict[str, str]:
        """Get all listings that have a rating set. Returns {source-source_id: rating}."""
        result = await self._session.execute(
            select(ListingRow.source, ListingRow.source_id, ListingRow.rating).where(
                ListingRow.rating.isnot(None)
            )
        )
        return {f"{r[0]}-{r[1]}": r[2] for r in result.all()}

    async def get_distinct_neighborhoods(self, city: str) -> list[str]:
        """Get distinct neighborhoods for a given city."""
        result = await self._session.execute(
            select(ListingRow.neighborhood)
            .where(
                ListingRow.city == city.lower(),
                ListingRow.neighborhood.isnot(None),
                ListingRow.neighborhood != "",
                ListingRow.is_active == True,  # noqa: E712
            )
            .distinct()
            .order_by(ListingRow.neighborhood)
        )
        return [r[0] for r in result.all()]


class SearchProfileRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_profile(
        self, name: str, filter_json: dict, telegram_chat_id: str | None = None
    ) -> SearchProfileRow:
        row = SearchProfileRow(
            id=str(uuid.uuid4()),
            name=name,
            telegram_chat_id=telegram_chat_id,
            filter_json=filter_json,
            created_at=datetime.utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_active_profiles(self) -> list[SearchProfileRow]:
        result = await self._session.execute(
            select(SearchProfileRow).where(SearchProfileRow.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def update_last_notified(self, profile_id: str) -> None:
        await self._session.execute(
            update(SearchProfileRow)
            .where(SearchProfileRow.id == profile_id)
            .values(last_notified_at=datetime.utcnow())
        )
        await self._session.flush()


class ScrapeRunRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def start_run(self, source: str, method: str) -> ScrapeRunRow:
        row = ScrapeRunRow(
            id=str(uuid.uuid4()),
            source=source,
            method=method,
            started_at=datetime.utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def finish_run(
        self,
        run_id: str,
        listings_found: int,
        listings_new: int,
        status: str = "success",
        error_message: str | None = None,
    ) -> None:
        await self._session.execute(
            update(ScrapeRunRow)
            .where(ScrapeRunRow.id == run_id)
            .values(
                finished_at=datetime.utcnow(),
                listings_found=listings_found,
                listings_new=listings_new,
                status=status,
                error_message=error_message,
            )
        )
        await self._session.flush()


class FolderRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_all(self) -> list[FolderRow]:
        result = await self._session.execute(
            select(FolderRow).order_by(FolderRow.created_at)
        )
        return list(result.scalars().all())

    async def create(self, name: str, folder_id: str | None = None, listing_ids: list[str] | None = None) -> FolderRow:
        row = FolderRow(
            id=folder_id or str(uuid.uuid4()),
            name=name,
            listing_ids=listing_ids or [],
            created_at=datetime.utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def rename(self, folder_id: str, new_name: str) -> bool:
        result = await self._session.execute(
            select(FolderRow).where(FolderRow.id == folder_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        row.name = new_name
        await self._session.flush()
        return True

    async def delete(self, folder_id: str) -> bool:
        result = await self._session.execute(
            delete(FolderRow).where(FolderRow.id == folder_id)
        )
        await self._session.flush()
        return result.rowcount > 0

    async def add_listings(self, folder_id: str, listing_ids: list[str]) -> bool:
        result = await self._session.execute(
            select(FolderRow).where(FolderRow.id == folder_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        existing = set(row.listing_ids or [])
        new_ids = [lid for lid in listing_ids if lid not in existing]
        if new_ids:
            row.listing_ids = list(existing) + new_ids
        await self._session.flush()
        return True

    async def remove_listing(self, folder_id: str, listing_id: str) -> bool:
        result = await self._session.execute(
            select(FolderRow).where(FolderRow.id == folder_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        row.listing_ids = [lid for lid in (row.listing_ids or []) if lid != listing_id]
        await self._session.flush()
        return True

    async def clear(self, folder_id: str) -> bool:
        result = await self._session.execute(
            select(FolderRow).where(FolderRow.id == folder_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        row.listing_ids = []
        await self._session.flush()
        return True


class NoteRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_all(self) -> dict[str, list[dict]]:
        """Get all notes grouped by listing key."""
        result = await self._session.execute(
            select(NoteRow).order_by(NoteRow.created_at.desc())
        )
        notes: dict[str, list[dict]] = {}
        for row in result.scalars().all():
            entry = {"id": row.id, "text": row.text, "createdAt": str(row.created_at)}
            notes.setdefault(row.listing_key, []).append(entry)
        return notes

    async def get_for_listing(self, listing_key: str) -> list[NoteRow]:
        result = await self._session.execute(
            select(NoteRow)
            .where(NoteRow.listing_key == listing_key)
            .order_by(NoteRow.created_at.desc())
        )
        return list(result.scalars().all())

    async def add(self, listing_key: str, text: str, note_id: str | None = None) -> NoteRow:
        row = NoteRow(
            id=note_id or str(uuid.uuid4()),
            listing_key=listing_key,
            text=text,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def delete(self, note_id: str) -> bool:
        result = await self._session.execute(
            delete(NoteRow).where(NoteRow.id == note_id)
        )
        await self._session.flush()
        return result.rowcount > 0

    async def bulk_import(self, notes_map: dict[str, list[dict]]) -> int:
        count = 0
        for listing_key, notes in notes_map.items():
            for note in notes:
                row = NoteRow(
                    id=note.get("id", str(uuid.uuid4())),
                    listing_key=listing_key,
                    text=note.get("text", ""),
                )
                if note.get("createdAt"):
                    from datetime import datetime as dt
                    try:
                        row.created_at = dt.fromisoformat(note["createdAt"])
                    except (ValueError, TypeError):
                        pass
                self._session.add(row)
                count += 1
        await self._session.flush()
        return count


class FacebookCityRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_all(self) -> list[FacebookCityRow]:
        result = await self._session.execute(select(FacebookCityRow))
        return list(result.scalars().all())

    async def create(self, name: str, latitude: float, longitude: float, radius_km: float, city_id: str | None = None) -> FacebookCityRow:
        row = FacebookCityRow(
            id=city_id or str(uuid.uuid4()),
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(self, city_id: str, **kwargs) -> bool:
        result = await self._session.execute(
            select(FacebookCityRow).where(FacebookCityRow.id == city_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        for k, v in kwargs.items():
            if hasattr(row, k):
                setattr(row, k, v)
        await self._session.flush()
        return True

    async def delete(self, city_id: str) -> bool:
        result = await self._session.execute(
            delete(FacebookCityRow).where(FacebookCityRow.id == city_id)
        )
        await self._session.flush()
        return result.rowcount > 0

    async def bulk_import(self, cities: list[dict]) -> int:
        count = 0
        for c in cities:
            row = FacebookCityRow(
                id=c.get("id", str(uuid.uuid4())),
                name=c.get("name", ""),
                latitude=c.get("latitude", 0),
                longitude=c.get("longitude", 0),
                radius_km=c.get("radiusKm", c.get("radius_km", 5.0)),
            )
            self._session.add(row)
            count += 1
        await self._session.flush()
        return count
