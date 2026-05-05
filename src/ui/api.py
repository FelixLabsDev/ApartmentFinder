"""FastAPI backend for the ApartmentFinder React frontend."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import get_settings
from src.db.engine import get_async_engine, get_async_session
from src.db.repository import FacebookCityRepository, FolderRepository, ListingRepository, NoteRepository, ScrapeRunRepository, SearchProfileRepository
from src.db.tables import Base, SearchProfileRow
from src.models.filters import SearchFilter
from src.pipeline.deduplicator import ListingDeduplicator
from src.pipeline.pipeline import ScrapePipeline
from src.scrapers.orchestrator import ScraperOrchestrator
from src.scrapers.yad2.scraper import Yad2ApiScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ApartmentFinder API",
    version="0.1.0",
    description="API for apartment listing aggregation from Yad2, Facebook Marketplace, and Madlan",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Create tables on startup."""
    from sqlalchemy import text
    get_settings().ensure_data_dir()
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrate: add columns if they don't exist
        for migration in [
            "ALTER TABLE listings ADD COLUMN preset_city_name VARCHAR(100)",
            "ALTER TABLE listings ADD COLUMN ai_guessed_fields JSON DEFAULT '[]'",
            "ALTER TABLE listings ADD COLUMN rating VARCHAR(20)",
            "ALTER TABLE listings ADD COLUMN seen_at DATETIME",
        ]:
            try:
                await conn.execute(text(migration))
            except Exception:
                pass  # Column already exists


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ListingResponse(BaseModel):
    id: str | None = None
    source: str
    source_id: str
    source_url: str
    title: str
    city: str
    preset_city_name: str | None
    neighborhood: str | None
    street: str | None
    house_number: str | None
    description: str | None
    price: float | None
    currency: str
    rooms: float | None
    floor: int | None
    total_floors: int | None
    area_sqm: float | None
    property_type: str | None
    has_parking: bool | None
    has_elevator: bool | None
    has_balcony: bool | None
    has_air_conditioning: bool | None
    has_mamad: bool | None
    is_accessible: bool | None
    is_furnished: bool | None
    has_bars: bool | None
    has_storage: bool | None
    pet_friendly: bool | None
    image_urls: list[str]
    contact_name: str | None
    contact_phone: str | None
    entry_date: str | None
    latitude: float | None
    longitude: float | None
    posted_at: str | None
    first_seen_at: str | None
    is_active: bool | None
    ai_guessed_fields: list[str] = []
    rating: str | None = None
    seen_at: str | None = None


class ScrapeResponse(BaseModel):
    total_scraped: int
    total_after_dedup: int
    total_after_filter: int
    listings_stored: int
    new_listings: int
    stored_listing_keys: list[str] = []


class HealthResponse(BaseModel):
    sources: dict[str, bool]


class StatsResponse(BaseModel):
    total_listings: int
    active_listings: int
    sources: dict[str, int]
    cities: dict[str, int]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/listings", response_model=list[ListingResponse], tags=["Listings"])
async def get_listings(
    source: Optional[str] = Query(None, description="Comma-separated sources: yad2, facebook, telegram"),
    city: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rooms: Optional[float] = Query(None),
    max_rooms: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    property_type: Optional[str] = Query(None),
    require_parking: Optional[bool] = Query(None),
    require_elevator: Optional[bool] = Query(None),
    require_balcony: Optional[bool] = Query(None),
    require_ac: Optional[bool] = Query(None),
    require_furnished: Optional[bool] = Query(None),
    require_pet_friendly: Optional[bool] = Query(None),
    min_floor: Optional[int] = Query(None),
    max_floor: Optional[int] = Query(None),
    keywords: Optional[str] = Query(None, description="Comma-separated keywords to search in title/description"),
    min_entry_date: Optional[str] = Query(None, description="Earliest move-in date (YYYY-MM-DD)"),
    max_entry_date: Optional[str] = Query(None, description="Latest move-in date (YYYY-MM-DD)"),
    include_inactive: Optional[bool] = Query(None, description="Include inactive (possibly taken) listings"),
    sort_by: Optional[str] = Query("newest", description="newest, price_asc, price_desc, rooms_asc, area_desc, price_per_sqm_asc, price_per_sqm_desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get filtered listings from the database."""
    source_list = [s.strip() for s in source.split(",") if s.strip()] if source else []
    city_list = [c.strip() for c in city.split(",") if c.strip()] if city else []
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []
    parsed_min_entry = date.fromisoformat(min_entry_date) if min_entry_date else None
    parsed_max_entry = date.fromisoformat(max_entry_date) if max_entry_date else None
    search_filter = SearchFilter(
        sources=source_list,
        cities=city_list,
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        min_area_sqm=min_area,
        max_area_sqm=max_area,
        min_floor=min_floor,
        max_floor=max_floor,
        property_types=[property_type] if property_type else [],
        min_entry_date=parsed_min_entry,
        max_entry_date=parsed_max_entry,
        require_parking=require_parking,
        require_elevator=require_elevator,
        require_balcony=require_balcony,
        require_air_conditioning=require_ac,
        require_furnished=require_furnished,
        require_pet_friendly=require_pet_friendly,
        keywords=keyword_list,
    )

    async with get_async_session() as session:
        repo = ListingRepository(session)
        rows = await repo.get_listings(
            search_filter,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            active_only=not include_inactive if include_inactive else True,
        )

    return [_row_to_response(r) for r in rows]


@app.post("/api/listings/by-keys", response_model=list[ListingResponse], tags=["Listings"])
async def get_listings_by_keys(keys: list[str]):
    """Fetch specific listings by their source-source_id keys (e.g. 'facebook-123')."""
    if not keys:
        return []
    async with get_async_session() as session:
        repo = ListingRepository(session)
        rows = await repo.get_listings_by_keys(keys)
    return [_row_to_response(r) for r in rows]


@app.post("/api/scrape", response_model=ScrapeResponse, tags=["Scraping"])
async def trigger_scrape(
    source: str = Query("all", description="yad2, facebook, madlan, or all"),
    city: Optional[str] = Query(None),
    area: Optional[str] = Query(None, description="Yad2 area code"),
    neighborhood: Optional[str] = Query(None, description="Yad2 neighborhood code"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rooms: Optional[float] = Query(None),
    max_rooms: Optional[float] = Query(None),
    min_floor: Optional[int] = Query(None),
    max_floor: Optional[int] = Query(None),
    min_area: Optional[float] = Query(None, description="Min area in sqm"),
    max_area: Optional[float] = Query(None, description="Max area in sqm"),
    property_type: Optional[str] = Query(None, description="Property type filter"),
    city_name: Optional[str] = Query(None, description="Display name from city preset (for filtering)"),
    fb_latitude: Optional[float] = Query(None, description="Facebook search center latitude"),
    fb_longitude: Optional[float] = Query(None, description="Facebook search center longitude"),
    fb_radius_km: Optional[float] = Query(None, description="Facebook search radius in km"),
    headless: bool = Query(True, description="False opens a visible browser for Facebook login"),
):
    """Trigger an on-demand scrape and store results."""
    # Full filter passed to scrapers (they use city for API-level location lookup)
    search_filter = SearchFilter(
        cities=[city] if city else [],
        area_code=area,
        neighborhood_code=neighborhood,
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        min_floor=min_floor,
        max_floor=max_floor,
        min_area_sqm=min_area,
        max_area_sqm=max_area,
        property_types=[property_type] if property_type else [],
        fb_latitude=fb_latitude,
        fb_longitude=fb_longitude,
        fb_radius_km=fb_radius_km,
    )

    # Pipeline post-filter excludes city — scrapers already handle location
    # filtering at the API level, and city names differ across sources
    # (e.g. "herzliya" vs "הרצליה, M")
    pipeline_filter = SearchFilter(
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        min_floor=min_floor,
        max_floor=max_floor,
        min_area_sqm=min_area,
        max_area_sqm=max_area,
        property_types=[property_type] if property_type else [],
    )

    orchestrator = ScraperOrchestrator()
    if source in ("yad2", "all"):
        orchestrator.register("yad2", [Yad2ApiScraper()])
    if source in ("facebook", "all"):
        try:
            from src.scrapers.facebook.scraper import FacebookGraphQLScraper, FacebookPlaywrightScraper
            settings = get_settings()
            fb_cookies = settings.get_fb_cookies_dict()
            logger.info("Facebook cookies loaded: %d cookies", len(fb_cookies))
            scrapers = []
            if fb_cookies:
                scrapers.append(FacebookGraphQLScraper(
                    cookies=fb_cookies,
                    lsd_token=settings.fb_lsd_token or None,
                ))
            scrapers.append(FacebookPlaywrightScraper(headless=headless))
            orchestrator.register("facebook", scrapers)
        except Exception as exc:
            logger.error("Failed to initialize Facebook scraper: %s", exc)

    if source in ("madlan", "all"):
        try:
            from src.scrapers.madlan.scraper import MadlanPlaywrightScraper
            orchestrator.register("madlan", [MadlanPlaywrightScraper(headless=headless)])
        except Exception as exc:
            logger.error("Failed to initialize Madlan scraper: %s", exc)

    pipeline = ScrapePipeline(orchestrator)
    result = await pipeline.run(search_filter, post_filter=pipeline_filter)

    # Stamp preset city name on all listings for reliable filtering
    if result.listings and city_name:
        for listing in result.listings:
            listing.preset_city_name = city_name

    # Store results
    listings_stored = 0
    new_listings = 0
    stored_keys: list[str] = []
    if result.listings:
        dedup = ListingDeduplicator()
        fingerprints = [dedup.compute_fingerprint(l) for l in result.listings]
        async with get_async_session() as session:
            repo = ListingRepository(session)
            listings_stored, new_listings = await repo.upsert_listings(result.listings, fingerprints)
            await session.commit()
        # Collect listing keys (source-source_id) matching frontend's listingKey format
        stored_keys = [f"{l.source.value}-{l.source_id}" for l in result.listings]

    return ScrapeResponse(
        total_scraped=result.total_scraped,
        total_after_dedup=result.total_after_dedup,
        total_after_filter=result.total_after_filter,
        listings_stored=listings_stored,
        new_listings=new_listings,
        stored_listing_keys=stored_keys,
    )


@app.delete("/api/listings", tags=["Listings"])
async def delete_all_listings():
    """Delete all listings from the database."""
    async with get_async_session() as session:
        repo = ListingRepository(session)
        count = await repo.delete_all()
        await session.commit()
    return {"deleted": count}


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check connectivity to scraping sources."""
    orchestrator = ScraperOrchestrator()
    orchestrator.register("yad2", [Yad2ApiScraper()])
    try:
        from src.scrapers.facebook.scraper import FacebookGraphQLScraper, FacebookPlaywrightScraper
        settings = get_settings()
        fb_cookies = settings.get_fb_cookies_dict()
        scrapers = []
        if fb_cookies:
            scrapers.append(FacebookGraphQLScraper(
                cookies=fb_cookies,
                lsd_token=settings.fb_lsd_token or None,
            ))
        scrapers.append(FacebookPlaywrightScraper())
        orchestrator.register("facebook", scrapers)
    except Exception as exc:
        logger.error("Failed to initialize Facebook scraper for health check: %s", exc)

    try:
        from src.scrapers.madlan.scraper import MadlanPlaywrightScraper
        orchestrator.register("madlan", [MadlanPlaywrightScraper()])
    except Exception as exc:
        logger.error("Failed to initialize Madlan scraper for health check: %s", exc)

    results = await orchestrator.health_check_all()
    return HealthResponse(sources=results)


@app.get("/api/neighborhoods", response_model=list[str], tags=["Listings"])
async def get_neighborhoods(city: str = Query(..., description="City slug to get neighborhoods for")):
    """Get distinct neighborhoods for a given city."""
    async with get_async_session() as session:
        repo = ListingRepository(session)
        return await repo.get_distinct_neighborhoods(city)


@app.get("/api/listings/new", response_model=list[ListingResponse], tags=["Listings"])
async def get_new_listings(
    since: str = Query(..., description="ISO timestamp (e.g. 2025-01-01T00:00:00)"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get listings first seen after a given timestamp."""
    since_dt = datetime.fromisoformat(since)
    async with get_async_session() as session:
        repo = ListingRepository(session)
        rows = await repo.get_new_since(since_dt)
    return [_row_to_response(r) for r in rows[:limit]]


@app.get("/api/search-profiles", tags=["Search Profiles"])
async def list_search_profiles():
    """List all active search profiles."""
    async with get_async_session() as session:
        repo = SearchProfileRepository(session)
        profiles = await repo.get_active_profiles()
    return [
        {
            "id": p.id,
            "name": p.name,
            "filter_json": p.filter_json,
            "created_at": str(p.created_at),
        }
        for p in profiles
    ]


@app.post("/api/search-profiles", tags=["Search Profiles"])
async def create_search_profile(
    name: str = Query(...),
    filter_json: str = Query(..., description="JSON-encoded filter object"),
):
    """Create a new search profile."""
    import json
    parsed = json.loads(filter_json)
    async with get_async_session() as session:
        repo = SearchProfileRepository(session)
        profile = await repo.create_profile(name, parsed)
        await session.commit()
    return {"id": profile.id, "name": profile.name}


@app.delete("/api/search-profiles/{profile_id}", tags=["Search Profiles"])
async def delete_search_profile(profile_id: str):
    """Deactivate a search profile."""
    from sqlalchemy import update as sql_update
    async with get_async_session() as session:
        await session.execute(
            sql_update(SearchProfileRow)
            .where(SearchProfileRow.id == profile_id)
            .values(is_active=False)
        )
        await session.commit()
    return {"ok": True}


@app.get("/api/stats", response_model=StatsResponse, tags=["System"])
async def get_stats():
    """Get summary statistics about stored listings."""
    async with get_async_session() as session:
        repo = ListingRepository(session)
        all_listings = await repo.get_listings(SearchFilter(), limit=10000)

    total = len(all_listings)
    active = sum(1 for l in all_listings if getattr(l, "is_active", True))

    sources: dict[str, int] = {}
    cities: dict[str, int] = {}
    for l in all_listings:
        src = str(l.source)
        sources[src] = sources.get(src, 0) + 1
        c = l.city or "unknown"
        cities[c] = cities.get(c, 0) + 1

    return StatsResponse(
        total_listings=total,
        active_listings=active,
        sources=sources,
        cities=cities,
    )


CITY_SETTINGS_PATH = Path("data/city_settings.json")


@app.get("/api/city-settings", tags=["Settings"])
async def get_city_settings() -> list[dict[str, Any]]:
    """Read city settings from local JSON file."""
    if CITY_SETTINGS_PATH.exists():
        try:
            return json.loads(CITY_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


@app.put("/api/city-settings", tags=["Settings"])
async def save_city_settings(cities: list[dict[str, Any]]) -> dict[str, bool]:
    """Write city settings to local JSON file."""
    CITY_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CITY_SETTINGS_PATH.write_text(
        json.dumps(cities, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Seen / New tracking
# ---------------------------------------------------------------------------


@app.post("/api/listings/{source}/{source_id}/seen", tags=["Listings"])
async def mark_listing_seen(source: str, source_id: str):
    """Mark a listing as seen (opened in detail view)."""
    async with get_async_session() as session:
        repo = ListingRepository(session)
        found = await repo.mark_seen(source, source_id)
        await session.commit()
    return {"ok": found}


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


class AddNoteRequest(BaseModel):
    text: str
    id: str | None = None


class NoteResponse(BaseModel):
    id: str
    text: str
    createdAt: str


class BulkImportNotesRequest(BaseModel):
    notes: dict[str, list[dict]]  # {listing_key: [{id, text, createdAt}]}


@app.get("/api/notes", tags=["Notes"])
async def get_all_notes():
    """Get all notes grouped by listing key."""
    async with get_async_session() as session:
        repo = NoteRepository(session)
        return await repo.get_all()


@app.get("/api/notes/{listing_key:path}", response_model=list[NoteResponse], tags=["Notes"])
async def get_notes(listing_key: str):
    """Get notes for a specific listing."""
    async with get_async_session() as session:
        repo = NoteRepository(session)
        rows = await repo.get_for_listing(listing_key)
    return [NoteResponse(id=r.id, text=r.text, createdAt=str(r.created_at)) for r in rows]


@app.post("/api/notes/{listing_key:path}", response_model=NoteResponse, tags=["Notes"])
async def add_note(listing_key: str, body: AddNoteRequest):
    """Add a note to a listing."""
    async with get_async_session() as session:
        repo = NoteRepository(session)
        row = await repo.add(listing_key, body.text, note_id=body.id)
        await session.commit()
    return NoteResponse(id=row.id, text=row.text, createdAt=str(row.created_at))


@app.delete("/api/notes/{note_id}", tags=["Notes"])
async def delete_note(note_id: str):
    """Delete a note."""
    async with get_async_session() as session:
        repo = NoteRepository(session)
        found = await repo.delete(note_id)
        await session.commit()
    return {"ok": found}


@app.post("/api/notes-bulk-import", tags=["Notes"])
async def bulk_import_notes(body: BulkImportNotesRequest):
    """Bulk import notes (for localStorage migration)."""
    async with get_async_session() as session:
        repo = NoteRepository(session)
        count = await repo.bulk_import(body.notes)
        await session.commit()
    return {"imported": count}


# ---------------------------------------------------------------------------
# Facebook Cities
# ---------------------------------------------------------------------------


class FacebookCityResponse(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    radiusKm: float


class CreateFbCityRequest(BaseModel):
    id: str | None = None
    name: str
    latitude: float
    longitude: float
    radiusKm: float = 5.0


class UpdateFbCityRequest(BaseModel):
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radiusKm: float | None = None


class BulkImportFbCitiesRequest(BaseModel):
    cities: list[dict]


def _fb_city_to_response(row) -> FacebookCityResponse:
    return FacebookCityResponse(
        id=row.id, name=row.name,
        latitude=row.latitude, longitude=row.longitude,
        radiusKm=row.radius_km,
    )


@app.get("/api/facebook-cities", response_model=list[FacebookCityResponse], tags=["Facebook Cities"])
async def get_facebook_cities():
    async with get_async_session() as session:
        repo = FacebookCityRepository(session)
        rows = await repo.get_all()
    return [_fb_city_to_response(r) for r in rows]


@app.post("/api/facebook-cities", response_model=FacebookCityResponse, tags=["Facebook Cities"])
async def create_facebook_city(body: CreateFbCityRequest):
    async with get_async_session() as session:
        repo = FacebookCityRepository(session)
        row = await repo.create(body.name, body.latitude, body.longitude, body.radiusKm, city_id=body.id)
        await session.commit()
    return _fb_city_to_response(row)


@app.put("/api/facebook-cities/{city_id}", tags=["Facebook Cities"])
async def update_facebook_city(city_id: str, body: UpdateFbCityRequest):
    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.latitude is not None:
        updates["latitude"] = body.latitude
    if body.longitude is not None:
        updates["longitude"] = body.longitude
    if body.radiusKm is not None:
        updates["radius_km"] = body.radiusKm
    async with get_async_session() as session:
        repo = FacebookCityRepository(session)
        found = await repo.update(city_id, **updates)
        await session.commit()
    return {"ok": found}


@app.delete("/api/facebook-cities/{city_id}", tags=["Facebook Cities"])
async def delete_facebook_city(city_id: str):
    async with get_async_session() as session:
        repo = FacebookCityRepository(session)
        found = await repo.delete(city_id)
        await session.commit()
    return {"ok": found}


@app.post("/api/facebook-cities/bulk-import", tags=["Facebook Cities"])
async def bulk_import_facebook_cities(body: BulkImportFbCitiesRequest):
    async with get_async_session() as session:
        repo = FacebookCityRepository(session)
        count = await repo.bulk_import(body.cities)
        await session.commit()
    return {"imported": count}


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------


class FolderResponse(BaseModel):
    id: str
    name: str
    listingIds: list[str]
    createdAt: str


class CreateFolderRequest(BaseModel):
    name: str
    id: str | None = None
    listingIds: list[str] = []


class RenameFolderRequest(BaseModel):
    name: str


class AddListingsRequest(BaseModel):
    listingIds: list[str]


class BulkImportFoldersRequest(BaseModel):
    folders: list[dict]


def _folder_to_response(row) -> FolderResponse:
    return FolderResponse(
        id=row.id,
        name=row.name,
        listingIds=row.listing_ids or [],
        createdAt=str(row.created_at),
    )


@app.get("/api/folders", response_model=list[FolderResponse], tags=["Folders"])
async def get_folders():
    """Get all folders."""
    async with get_async_session() as session:
        repo = FolderRepository(session)
        rows = await repo.get_all()
    return [_folder_to_response(r) for r in rows]


@app.post("/api/folders", response_model=FolderResponse, tags=["Folders"])
async def create_folder(body: CreateFolderRequest):
    """Create a new folder."""
    async with get_async_session() as session:
        repo = FolderRepository(session)
        row = await repo.create(body.name, folder_id=body.id, listing_ids=body.listingIds)
        await session.commit()
    return _folder_to_response(row)


@app.put("/api/folders/{folder_id}/name", tags=["Folders"])
async def rename_folder(folder_id: str, body: RenameFolderRequest):
    """Rename a folder."""
    async with get_async_session() as session:
        repo = FolderRepository(session)
        found = await repo.rename(folder_id, body.name)
        await session.commit()
    return {"ok": found}


@app.delete("/api/folders/{folder_id}", tags=["Folders"])
async def delete_folder(folder_id: str):
    """Delete a folder."""
    async with get_async_session() as session:
        repo = FolderRepository(session)
        found = await repo.delete(folder_id)
        await session.commit()
    return {"ok": found}


@app.post("/api/folders/{folder_id}/listings", tags=["Folders"])
async def add_to_folder(folder_id: str, body: AddListingsRequest):
    """Add listings to a folder."""
    async with get_async_session() as session:
        repo = FolderRepository(session)
        found = await repo.add_listings(folder_id, body.listingIds)
        await session.commit()
    return {"ok": found}


@app.delete("/api/folders/{folder_id}/listings/{listing_id:path}", tags=["Folders"])
async def remove_from_folder(folder_id: str, listing_id: str):
    """Remove a listing from a folder."""
    async with get_async_session() as session:
        repo = FolderRepository(session)
        found = await repo.remove_listing(folder_id, listing_id)
        await session.commit()
    return {"ok": found}


@app.delete("/api/folders/{folder_id}/listings", tags=["Folders"])
async def clear_folder(folder_id: str):
    """Clear all listings from a folder."""
    async with get_async_session() as session:
        repo = FolderRepository(session)
        found = await repo.clear(folder_id)
        await session.commit()
    return {"ok": found}


@app.post("/api/folders/bulk-import", tags=["Folders"])
async def bulk_import_folders(body: BulkImportFoldersRequest):
    """Bulk import folders (used for migrating from localStorage)."""
    async with get_async_session() as session:
        repo = FolderRepository(session)
        count = 0
        for f in body.folders:
            await repo.create(
                name=f.get("name", ""),
                folder_id=f.get("id"),
                listing_ids=f.get("listingIds", []),
            )
            count += 1
        await session.commit()
    return {"imported": count}


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------


class RatingRequest(BaseModel):
    rating: str  # "liked" or "disliked"


class BulkRatingsRequest(BaseModel):
    ratings: dict[str, str]  # {"source-source_id": "liked"|"disliked"}


@app.put("/api/listings/{source}/{source_id}/rating", tags=["Ratings"])
async def set_rating(source: str, source_id: str, body: RatingRequest):
    """Set rating on a listing."""
    if body.rating not in ("liked", "disliked"):
        return {"ok": False, "error": "Rating must be 'liked' or 'disliked'"}
    async with get_async_session() as session:
        repo = ListingRepository(session)
        found = await repo.set_rating(source, source_id, body.rating)
        await session.commit()
    return {"ok": found}


@app.delete("/api/listings/{source}/{source_id}/rating", tags=["Ratings"])
async def clear_rating(source: str, source_id: str):
    """Clear rating on a listing."""
    async with get_async_session() as session:
        repo = ListingRepository(session)
        found = await repo.set_rating(source, source_id, None)
        await session.commit()
    return {"ok": found}


@app.get("/api/ratings", tags=["Ratings"])
async def get_all_ratings():
    """Get all ratings as a map of listing key -> rating."""
    async with get_async_session() as session:
        repo = ListingRepository(session)
        ratings = await repo.get_all_ratings()
    return ratings


@app.post("/api/ratings/bulk", tags=["Ratings"])
async def set_bulk_ratings(body: BulkRatingsRequest):
    """Bulk import ratings (used for migrating from localStorage)."""
    async with get_async_session() as session:
        repo = ListingRepository(session)
        count = await repo.set_ratings_bulk(body.ratings)
        await session.commit()
    return {"updated": count}


# ---------------------------------------------------------------------------
# Telegram Bot management
# ---------------------------------------------------------------------------

_bot_task: asyncio.Task | None = None


@app.post("/api/telegram-bot/start", tags=["Telegram Bot"])
async def start_telegram_bot():
    """Start the Telegram bot listener in the background."""
    global _bot_task
    if _bot_task and not _bot_task.done():
        return {"status": "already_running"}

    settings = get_settings()
    if not settings.telegram_bot_token:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN not configured"}

    from src.telegram_bot.bot import run_bot
    _bot_task = asyncio.create_task(run_bot())
    return {"status": "started"}


@app.post("/api/telegram-bot/stop", tags=["Telegram Bot"])
async def stop_telegram_bot():
    """Stop the Telegram bot listener."""
    global _bot_task
    if _bot_task and not _bot_task.done():
        _bot_task.cancel()
        try:
            await _bot_task
        except asyncio.CancelledError:
            pass
        _bot_task = None
        return {"status": "stopped"}
    return {"status": "not_running"}


@app.get("/api/telegram-bot/status", tags=["Telegram Bot"])
async def telegram_bot_status():
    """Check if the Telegram bot is running."""
    running = _bot_task is not None and not _bot_task.done()
    return {"running": running}


@app.post("/api/listings/{source}/{source_id}/ai-extract", response_model=ListingResponse, tags=["Listings"])
async def ai_extract_listing(source: str, source_id: str):
    """Rescrape a Facebook listing page and use AI to extract structured fields."""
    from sqlalchemy import select as sql_select

    from src.ai.extractor import extract_listing_fields
    from src.db.tables import ListingRow
    from src.scrapers.telegram_links.scraper import scrape_fb_listing

    # Look up the existing listing
    async with get_async_session() as session:
        result = await session.execute(
            sql_select(ListingRow).where(
                ListingRow.source == source,
                ListingRow.source_id == source_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Listing not found")

        source_url = row.source_url

    # Scrape the listing page
    try:
        scraped = await scrape_fb_listing(source_url)
    except Exception as exc:
        logger.error("AI extract: scrape failed for %s: %s", source_url, exc)
        raise HTTPException(status_code=502, detail=f"Failed to scrape listing: {exc}")

    if not scraped.text_content.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from listing page")

    # Run AI extraction
    try:
        ai_result = await extract_listing_fields(scraped.text_content, title=scraped.title)
    except Exception as exc:
        logger.error("AI extract: extraction failed for %s: %s", source_url, exc)
        raise HTTPException(status_code=502, detail=f"AI extraction failed: {exc}")

    fields = ai_result.extracted_fields

    # Update the listing in the database
    async with get_async_session() as session:
        result = await session.execute(
            sql_select(ListingRow).where(
                ListingRow.source == source,
                ListingRow.source_id == source_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Listing not found")

        # Apply extracted fields (only overwrite if AI provided a value)
        if fields.get("price") is not None:
            row.price = fields["price"]
        if fields.get("currency") == "USD":
            row.currency = "USD"
        if fields.get("rooms") is not None:
            row.rooms = fields["rooms"]
        if fields.get("city") and fields["city"] != "unknown":
            row.city = fields["city"]
        if fields.get("neighborhood"):
            row.neighborhood = fields["neighborhood"]
        if fields.get("street"):
            row.street = fields["street"]
        if fields.get("house_number"):
            row.house_number = fields["house_number"]
        if fields.get("floor") is not None:
            row.floor = fields["floor"]
        if fields.get("total_floors") is not None:
            row.total_floors = fields["total_floors"]
        if fields.get("area_sqm") is not None:
            row.area_sqm = fields["area_sqm"]
        if fields.get("description"):
            row.description = fields["description"]
        if fields.get("entry_date"):
            try:
                row.entry_date = date.fromisoformat(fields["entry_date"])
            except (ValueError, TypeError):
                pass
        if fields.get("property_type"):
            row.property_type = fields["property_type"]

        # Boolean features
        for feat in [
            "has_parking", "has_elevator", "has_balcony", "has_air_conditioning",
            "has_mamad", "is_accessible", "is_furnished", "has_bars",
            "has_storage", "pet_friendly",
        ]:
            if fields.get(feat) is not None:
                setattr(row, feat, fields[feat])

        if fields.get("contact_name"):
            row.contact_name = fields["contact_name"]
        if fields.get("contact_phone"):
            row.contact_phone = fields["contact_phone"]

        # Update images if scraper found more
        if scraped.image_urls:
            row.image_urls = scraped.image_urls

        row.ai_guessed_fields = ai_result.guessed_fields
        await session.commit()
        await session.refresh(row)

        return _row_to_response(row)


def _row_to_response(row) -> ListingResponse:
    """Convert a DB row to a ListingResponse."""
    return ListingResponse(
        id=str(row.id) if hasattr(row, "id") else None,
        source=str(row.source),
        source_id=row.source_id,
        source_url=row.source_url,
        title=row.title or "",
        city=row.city or "",
        preset_city_name=getattr(row, "preset_city_name", None),
        neighborhood=getattr(row, "neighborhood", None),
        street=getattr(row, "street", None),
        house_number=getattr(row, "house_number", None),
        description=getattr(row, "description", None),
        price=row.price,
        currency=str(getattr(row, "currency", "ILS")),
        rooms=getattr(row, "rooms", None),
        floor=getattr(row, "floor", None),
        total_floors=getattr(row, "total_floors", None),
        area_sqm=getattr(row, "area_sqm", None),
        property_type=str(getattr(row, "property_type", None)) if getattr(row, "property_type", None) else None,
        has_parking=getattr(row, "has_parking", None),
        has_elevator=getattr(row, "has_elevator", None),
        has_balcony=getattr(row, "has_balcony", None),
        has_air_conditioning=getattr(row, "has_air_conditioning", None),
        has_mamad=getattr(row, "has_mamad", None),
        is_accessible=getattr(row, "is_accessible", None),
        is_furnished=getattr(row, "is_furnished", None),
        has_bars=getattr(row, "has_bars", None),
        has_storage=getattr(row, "has_storage", None),
        pet_friendly=getattr(row, "pet_friendly", None),
        image_urls=row.image_urls if hasattr(row, "image_urls") and row.image_urls else [],
        contact_name=getattr(row, "contact_name", None),
        contact_phone=getattr(row, "contact_phone", None),
        entry_date=str(row.entry_date) if getattr(row, "entry_date", None) else None,
        latitude=getattr(row, "latitude", None),
        longitude=getattr(row, "longitude", None),
        posted_at=str(row.posted_at) if getattr(row, "posted_at", None) else None,
        first_seen_at=str(row.first_seen_at) if getattr(row, "first_seen_at", None) else None,
        is_active=getattr(row, "is_active", None),
        ai_guessed_fields=getattr(row, "ai_guessed_fields", None) or [],
        rating=getattr(row, "rating", None),
        seen_at=str(row.seen_at) if getattr(row, "seen_at", None) else None,
    )
