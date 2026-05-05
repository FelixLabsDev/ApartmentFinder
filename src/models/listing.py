from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .enums import Currency, PropertyType, Source


class ListingCreate(BaseModel):
    """Input schema — what scrapers produce before DB insertion."""

    source: Source
    source_id: str
    source_url: str
    title: str = ""
    price: float | None = None
    currency: Currency = Currency.ILS
    city: str
    preset_city_name: str | None = None
    neighborhood: str | None = None
    street: str | None = None
    house_number: str | None = None
    rooms: float | None = None  # 2.5 rooms is common in Israel
    floor: int | None = None
    total_floors: int | None = None
    area_sqm: float | None = None
    description: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    property_type: PropertyType | None = None

    # Features
    has_parking: bool | None = None
    has_elevator: bool | None = None
    has_balcony: bool | None = None
    has_air_conditioning: bool | None = None
    has_mamad: bool | None = None  # Safe room
    is_accessible: bool | None = None
    is_furnished: bool | None = None
    has_bars: bool | None = None
    has_storage: bool | None = None
    pet_friendly: bool | None = None

    # Contact
    contact_name: str | None = None
    contact_phone: str | None = None

    # Dates
    entry_date: date | None = None
    posted_at: datetime | None = None
    updated_at: datetime | None = None

    # Geo
    latitude: float | None = None
    longitude: float | None = None

    # AI extraction metadata — which fields were guessed by AI
    ai_guessed_fields: list[str] = Field(default_factory=list)

    # Raw data for debugging
    raw_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("city", mode="before")
    @classmethod
    def strip_city(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class Listing(ListingCreate):
    """Full listing as stored in DB — adds internal tracking fields."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fingerprint: str = ""
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    model_config = {"from_attributes": True}
