from __future__ import annotations

from datetime import date

from pydantic import BaseModel, field_validator


class SearchFilter(BaseModel):
    """User-defined search criteria. All fields optional = match-all."""

    name: str = "default"
    sources: list[str] = []
    cities: list[str] = []
    neighborhoods: list[str] = []
    area_code: str | None = None
    neighborhood_code: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_rooms: float | None = None
    max_rooms: float | None = None
    min_area_sqm: float | None = None
    max_area_sqm: float | None = None
    min_floor: int | None = None
    max_floor: int | None = None
    property_types: list[str] = []

    # Entry date range
    min_entry_date: date | None = None
    max_entry_date: date | None = None

    # Feature requirements (None = don't care, True = must have)
    require_parking: bool | None = None
    require_elevator: bool | None = None
    require_balcony: bool | None = None
    require_air_conditioning: bool | None = None
    require_mamad: bool | None = None
    require_pet_friendly: bool | None = None
    require_furnished: bool | None = None

    # Facebook location search
    fb_latitude: float | None = None
    fb_longitude: float | None = None
    fb_radius_km: float | None = None

    # Text search
    keywords: list[str] = []
    exclude_keywords: list[str] = []

    @field_validator("cities", "neighborhoods", mode="before")
    @classmethod
    def lowercase_list(cls, v: list[str]) -> list[str]:
        return [s.lower().strip() for s in v] if v else []
