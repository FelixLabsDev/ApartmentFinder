import json
from pathlib import Path

import pytest

from src.scrapers.madlan.parser import MadlanParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestMadlanParserApi:
    """Test parsing of API-intercepted listing data."""

    @pytest.fixture
    def sample_listings(self) -> list[dict]:
        with open(FIXTURES_DIR / "madlan_api_sample.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["data"]["searchResults"]

    def test_parse_basic_listing(self, sample_listings):
        raw = sample_listings[0]
        listing = MadlanParser.parse_api_listing(raw)
        assert listing is not None
        assert listing.source == "madlan"
        assert listing.source_id == "4gcfn1mafPq"
        assert listing.price == 4500
        assert listing.rooms == 3
        assert listing.floor == 2
        assert listing.total_floors == 5
        assert listing.area_sqm == 75
        assert listing.city == "בת ים"
        assert listing.neighborhood == "רמת הנשיא"
        assert listing.street == "הרצל"
        assert listing.house_number == "15"
        assert listing.latitude == pytest.approx(32.0171, abs=0.001)
        assert listing.longitude == pytest.approx(34.7505, abs=0.001)
        assert "madlan.co.il/listings/4gcfn1mafPq" in listing.source_url

    def test_parse_images(self, sample_listings):
        listing = MadlanParser.parse_api_listing(sample_listings[0])
        assert listing is not None
        assert len(listing.image_urls) == 2
        assert "photo1.jpg" in listing.image_urls[0]

    def test_parse_features(self, sample_listings):
        listing = MadlanParser.parse_api_listing(sample_listings[0])
        assert listing is not None
        assert listing.has_parking is True
        assert listing.has_elevator is True
        assert listing.has_air_conditioning is True
        assert listing.has_mamad is True
        assert listing.has_balcony is None  # Not in amenities

    def test_parse_dates(self, sample_listings):
        listing = MadlanParser.parse_api_listing(sample_listings[0])
        assert listing is not None
        assert listing.posted_at is not None
        assert listing.posted_at.year == 2026
        assert listing.posted_at.month == 3
        assert listing.entry_date is not None
        assert listing.entry_date.month == 4

    def test_parse_property_type(self, sample_listings):
        listing = MadlanParser.parse_api_listing(sample_listings[0])
        assert listing is not None
        assert listing.property_type == "apartment"

        studio = MadlanParser.parse_api_listing(sample_listings[2])
        assert studio is not None
        assert studio.property_type == "studio"

    def test_parse_all_listings(self, sample_listings):
        listings = [MadlanParser.parse_api_listing(raw) for raw in sample_listings]
        parsed = [l for l in listings if l is not None]
        assert len(parsed) == 3
        assert all(l.source == "madlan" for l in parsed)
        assert all(l.city for l in parsed)

    def test_parse_empty_dict(self):
        result = MadlanParser.parse_api_listing({})
        assert result is None

    def test_parse_missing_fields(self):
        """Listing with only ID and city should still parse."""
        raw = {"listingId": "test123", "city": "תל אביב", "price": 3000}
        listing = MadlanParser.parse_api_listing(raw)
        assert listing is not None
        assert listing.source_id == "test123"
        assert listing.price == 3000


class TestMadlanParserDom:
    """Test parsing of DOM-extracted listing data."""

    def test_parse_dom_listing(self):
        card = {
            "id": "abc123",
            "price": "4500",
            "rooms": 3,
            "floor": 2,
            "area_sqm": 75,
            "city": "בת ים",
            "street": "הרצל",
            "title": "דירה ברמת הנשיא",
            "image_urls": ["https://example.com/img.jpg"],
        }
        listing = MadlanParser.parse_dom_listing(card)
        assert listing is not None
        assert listing.source == "madlan"
        assert listing.source_id == "abc123"
        assert listing.price == 4500
        assert listing.rooms == 3

    def test_parse_dom_empty_id(self):
        card = {"price": "4500"}
        result = MadlanParser.parse_dom_listing(card)
        assert result is None


class TestMadlanParserHelpers:
    def test_parse_price_str(self):
        assert MadlanParser._parse_price_str("₪4,000") == 4000
        assert MadlanParser._parse_price_str("4,500 ₪/חודש") == 4500
        assert MadlanParser._parse_price_str("$1,200") == 1200
        assert MadlanParser._parse_price_str("") is None
        assert MadlanParser._parse_price_str(None) is None

    def test_parse_property_type(self):
        assert MadlanParser._parse_property_type("דירה").value == "apartment"
        assert MadlanParser._parse_property_type("פנטהאוז").value == "penthouse"
        assert MadlanParser._parse_property_type("סטודיו").value == "studio"
        assert MadlanParser._parse_property_type("") is None

    def test_safe_float(self):
        assert MadlanParser._safe_float(3.5) == 3.5
        assert MadlanParser._safe_float("75") == 75.0
        assert MadlanParser._safe_float(None) is None
        assert MadlanParser._safe_float("abc") is None

    def test_safe_int(self):
        assert MadlanParser._safe_int(3) == 3
        assert MadlanParser._safe_int("5") == 5
        assert MadlanParser._safe_int("3.5") == 3
        assert MadlanParser._safe_int(None) is None
