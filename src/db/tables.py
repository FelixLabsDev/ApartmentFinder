from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class ListingRow(Base):
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(500), default="")
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(5), default="ILS")
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    preset_city_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    house_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rooms: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_urls: Mapped[str] = mapped_column(JSON, default="[]")
    property_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Features as individual columns for efficient SQL filtering
    has_parking: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_elevator: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_balcony: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_air_conditioning: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_mamad: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_accessible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_furnished: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_bars: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_storage: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pet_friendly: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Contact
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Dates
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Geo
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # AI extraction metadata
    ai_guessed_fields: Mapped[str] = mapped_column(JSON, default="[]")

    # User rating: "liked", "disliked", or null
    rating: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # User has opened/viewed this listing
    seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Internal
    raw_data: Mapped[str] = mapped_column(JSON, default="{}")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_source_listing"),
        Index("ix_city_price", "city", "price"),
        Index("ix_city_rooms", "city", "rooms"),
        Index("ix_fingerprint", "fingerprint"),
        Index("ix_first_seen", "first_seen_at"),
    )


class SearchProfileRow(Base):
    __tablename__ = "search_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    filter_json: Mapped[str] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class NoteRow(Base):
    __tablename__ = "listing_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_key: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FacebookCityRow(Base):
    __tablename__ = "facebook_cities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_km: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)


class FolderRow(Base):
    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    listing_ids: Mapped[str] = mapped_column(JSON, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScrapeRunRow(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    listings_found: Mapped[int] = mapped_column(Integer, default=0)
    listings_new: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
