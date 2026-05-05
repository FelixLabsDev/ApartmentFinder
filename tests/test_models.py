from datetime import date

import pytest
from pydantic import ValidationError

from src.models import Currency, Listing, ListingCreate, PropertyType, SearchFilter, Source


class TestListingCreate:
    def test_minimal_fields(self):
        listing = ListingCreate(
            source=Source.YAD2,
            source_id="abc123",
            source_url="https://www.yad2.co.il/realestate/item/abc123",
            city="tel-aviv",
        )
        assert listing.source == Source.YAD2
        assert listing.source_id == "abc123"
        assert listing.city == "tel-aviv"
        assert listing.price is None
        assert listing.rooms is None
        assert listing.image_urls == []
        assert listing.has_parking is None

    def test_full_fields(self):
        listing = ListingCreate(
            source=Source.FACEBOOK,
            source_id="fb-999",
            source_url="https://facebook.com/marketplace/item/999",
            title="3 room apartment in center",
            price=5200.0,
            currency=Currency.ILS,
            city="tel-aviv",
            neighborhood="center",
            street="Dizengoff",
            house_number="42",
            rooms=3.0,
            floor=5,
            total_floors=10,
            area_sqm=80.0,
            description="Beautiful apartment with sea view",
            image_urls=["https://img1.jpg", "https://img2.jpg"],
            property_type=PropertyType.APARTMENT,
            has_parking=True,
            has_elevator=True,
            has_balcony=True,
            has_air_conditioning=True,
            has_mamad=False,
            contact_name="John",
            contact_phone="+972541234567",
            entry_date=date(2026, 4, 1),
            latitude=32.0853,
            longitude=34.7818,
        )
        assert listing.price == 5200.0
        assert listing.rooms == 3.0
        assert listing.has_parking is True
        assert listing.has_mamad is False
        assert len(listing.image_urls) == 2

    def test_half_rooms(self):
        """2.5 rooms is common in Israel."""
        listing = ListingCreate(
            source=Source.YAD2,
            source_id="x",
            source_url="https://yad2.co.il/x",
            city="haifa",
            rooms=2.5,
        )
        assert listing.rooms == 2.5

    def test_city_stripped(self):
        listing = ListingCreate(
            source=Source.YAD2,
            source_id="x",
            source_url="https://yad2.co.il/x",
            city="  tel-aviv  ",
        )
        assert listing.city == "tel-aviv"

    def test_invalid_source_raises(self):
        with pytest.raises(ValidationError):
            ListingCreate(
                source="invalid_source",
                source_id="x",
                source_url="https://example.com",
                city="test",
            )

    def test_raw_data_default(self):
        listing = ListingCreate(
            source=Source.YAD2,
            source_id="x",
            source_url="https://yad2.co.il/x",
            city="test",
        )
        assert listing.raw_data == {}


class TestListing:
    def test_has_internal_fields(self):
        listing = Listing(
            source=Source.YAD2,
            source_id="abc",
            source_url="https://yad2.co.il/abc",
            city="jerusalem",
        )
        assert listing.id  # UUID string generated
        assert listing.fingerprint == ""
        assert listing.is_active is True
        assert listing.first_seen_at is not None
        assert listing.last_seen_at is not None

    def test_unique_ids(self):
        l1 = Listing(source=Source.YAD2, source_id="a", source_url="u", city="c")
        l2 = Listing(source=Source.YAD2, source_id="b", source_url="u", city="c")
        assert l1.id != l2.id


class TestSearchFilter:
    def test_default_match_all(self):
        f = SearchFilter()
        assert f.name == "default"
        assert f.cities == []
        assert f.min_price is None
        assert f.max_price is None

    def test_cities_lowercased(self):
        f = SearchFilter(cities=["Tel-Aviv", "JERUSALEM", " Haifa "])
        assert f.cities == ["tel-aviv", "jerusalem", "haifa"]

    def test_neighborhoods_lowercased(self):
        f = SearchFilter(neighborhoods=["Florentin", "OLD CITY"])
        assert f.neighborhoods == ["florentin", "old city"]

    def test_full_filter(self):
        f = SearchFilter(
            name="My Search",
            cities=["tel-aviv"],
            min_price=3000,
            max_price=6000,
            min_rooms=2,
            max_rooms=3.5,
            property_types=["apartment", "studio"],
            require_parking=True,
            require_elevator=True,
            keywords=["renovated"],
            exclude_keywords=["sublet"],
        )
        assert f.min_price == 3000
        assert f.max_price == 6000
        assert f.require_parking is True
        assert "renovated" in f.keywords
        assert "sublet" in f.exclude_keywords
