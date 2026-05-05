import json
from pathlib import Path

import pytest

from src.models.enums import Currency, PropertyType, Source
from src.scrapers.yad2.parser import Yad2Parser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def api_response():
    with open(FIXTURES_DIR / "yad2_api_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def single_item():
    with open(FIXTURES_DIR / "yad2_single_item.json", "r", encoding="utf-8") as f:
        return json.load(f)


class TestYad2Parser:
    def test_extract_feed_items(self, api_response):
        items = Yad2Parser.extract_feed_items(api_response)
        assert len(items) > 0
        # All items should be actual listings
        for item in items:
            assert item["type"] in ("ad", "advanced_ad")

    def test_get_pagination(self, api_response):
        pagination = Yad2Parser.get_pagination(api_response)
        assert "current_page" in pagination
        assert "total_pages" in pagination
        assert "total_items" in pagination
        assert pagination["total_items"] > 0

    def test_parse_listing_basic(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.source == Source.YAD2
        assert listing.source_id == "2sdaa2j2"
        assert "yad2.co.il" in listing.source_url
        assert listing.city == "תל אביב יפו"
        assert listing.neighborhood == "פלורנטין"
        assert listing.street == "הרצל"

    def test_parse_listing_price(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.price == 4000.0
        assert listing.currency == Currency.ILS

    def test_parse_listing_rooms(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.rooms == 2.0

    def test_parse_listing_floor(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.floor == 1

    def test_parse_listing_area(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.area_sqm == 50.0

    def test_parse_listing_property_type(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.property_type == PropertyType.APARTMENT

    def test_parse_listing_features(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.has_air_conditioning is True
        assert listing.has_bars is True
        assert listing.is_furnished is True
        assert listing.pet_friendly is True
        # Balcony is "אין" (no)
        assert listing.has_balcony is False

    def test_parse_listing_coordinates(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.latitude is not None
        assert listing.longitude is not None
        assert 31 < listing.latitude < 34  # Israel bounds
        assert 34 < listing.longitude < 36

    def test_parse_listing_images(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert len(listing.image_urls) == 4
        assert all(url.startswith("https://") for url in listing.image_urls)

    def test_parse_listing_contact(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.contact_name is not None

    def test_parse_listing_dates(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.posted_at is not None
        assert listing.updated_at is not None
        assert listing.entry_date is not None

    def test_parse_all_items_from_api(self, api_response):
        """Parse all items from the API response — none should crash."""
        items = Yad2Parser.extract_feed_items(api_response)
        parsed = [Yad2Parser.parse_listing(item) for item in items]
        successful = [p for p in parsed if p is not None]
        assert len(successful) > 0
        # At least 80% should parse successfully
        assert len(successful) / len(items) >= 0.8

    def test_parse_price_formats(self):
        assert Yad2Parser._parse_price("4,000 ₪") == 4000.0
        assert Yad2Parser._parse_price("12,500 ₪") == 12500.0
        assert Yad2Parser._parse_price("3000") == 3000.0
        assert Yad2Parser._parse_price("") is None
        assert Yad2Parser._parse_price(None) is None

    def test_parse_listing_missing_id(self):
        """Listing with no id should return None."""
        result = Yad2Parser.parse_listing({"type": "ad"})
        assert result is None

    def test_raw_data_preserved(self, single_item):
        listing = Yad2Parser.parse_listing(single_item)
        assert listing is not None
        assert listing.raw_data == single_item
