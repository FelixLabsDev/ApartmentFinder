import json
from pathlib import Path

import pytest

from src.models.enums import Currency, PropertyType, Source
from src.scrapers.facebook.parser import FacebookParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def graphql_response():
    with open(FIXTURES_DIR / "fb_graphql_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def single_item():
    with open(FIXTURES_DIR / "fb_single_item.json", "r", encoding="utf-8") as f:
        return json.load(f)


class TestFacebookParser:
    # ------------------------------------------------------------------
    # Feed extraction
    # ------------------------------------------------------------------

    def test_extract_feed_items(self, graphql_response):
        items = FacebookParser.extract_feed_items(graphql_response)
        assert len(items) == 4  # 5 edges, 1 has null listing
        for item in items:
            assert item.get("id") is not None

    def test_extract_feed_items_filters_null_listings(self, graphql_response):
        """Sponsored/null listings should be filtered out."""
        items = FacebookParser.extract_feed_items(graphql_response)
        ids = [item["id"] for item in items]
        assert all(id_ is not None for id_ in ids)

    def test_extract_feed_items_empty_response(self):
        items = FacebookParser.extract_feed_items({})
        assert items == []

    def test_extract_feed_items_malformed_response(self):
        items = FacebookParser.extract_feed_items({"data": None})
        assert items == []

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def test_get_pagination(self, graphql_response):
        pagination = FacebookParser.get_pagination(graphql_response)
        assert pagination["has_next_page"] is True
        assert pagination["end_cursor"] is not None

    def test_get_pagination_empty(self):
        pagination = FacebookParser.get_pagination({})
        assert pagination["has_next_page"] is False
        assert pagination["end_cursor"] is None

    # ------------------------------------------------------------------
    # Single listing parsing
    # ------------------------------------------------------------------

    def test_parse_listing_basic(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.source == Source.FACEBOOK
        assert listing.source_id == "1234567890111"
        assert "facebook.com/marketplace/item/1234567890111" in listing.source_url
        assert listing.city == "Tel Aviv"

    def test_parse_listing_title(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        # custom_title is null, falls back to marketplace_listing_title
        assert "פלורנטין" in listing.title

    def test_parse_listing_price(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.price == 5200.0
        assert listing.currency == Currency.ILS

    def test_parse_listing_usd_price(self, graphql_response):
        """The Haifa penthouse listing has USD price."""
        items = FacebookParser.extract_feed_items(graphql_response)
        # Find the USD listing (Haifa penthouse)
        usd_item = next(i for i in items if i["id"] == "1111222233344")
        listing = FacebookParser.parse_listing(usd_item)
        assert listing is not None
        assert listing.price == 2500.0
        assert listing.currency == Currency.USD

    def test_parse_listing_rooms(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.rooms == 3.0

    def test_parse_listing_floor(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.floor == 2
        assert listing.total_floors == 5

    def test_parse_listing_area(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.area_sqm == 50.0

    def test_parse_listing_property_type(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.property_type == PropertyType.APARTMENT

    def test_parse_listing_property_type_studio(self, graphql_response):
        items = FacebookParser.extract_feed_items(graphql_response)
        studio_item = next(i for i in items if i["id"] == "5555666677733")
        listing = FacebookParser.parse_listing(studio_item)
        assert listing is not None
        assert listing.property_type == PropertyType.STUDIO

    def test_parse_listing_property_type_penthouse(self, graphql_response):
        items = FacebookParser.extract_feed_items(graphql_response)
        ph_item = next(i for i in items if i["id"] == "1111222233344")
        listing = FacebookParser.parse_listing(ph_item)
        assert listing is not None
        assert listing.property_type == PropertyType.PENTHOUSE

    def test_parse_listing_features_from_attributes(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.is_furnished is True
        assert listing.has_parking is True
        assert listing.has_air_conditioning is True

    def test_parse_listing_features_from_description(self, single_item):
        """Description mentions מרפסת (balcony) which should be picked up."""
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.has_balcony is True

    def test_parse_listing_unfurnished(self, graphql_response):
        """The Haifa penthouse is UNFURNISHED."""
        items = FacebookParser.extract_feed_items(graphql_response)
        ph_item = next(i for i in items if i["id"] == "1111222233344")
        listing = FacebookParser.parse_listing(ph_item)
        assert listing is not None
        assert listing.is_furnished is False

    def test_parse_listing_coordinates(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.latitude is not None
        assert listing.longitude is not None
        assert 31 < listing.latitude < 34  # Israel bounds
        assert 34 < listing.longitude < 36

    def test_parse_listing_images(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert len(listing.image_urls) == 3
        assert all(url.startswith("https://") for url in listing.image_urls)

    def test_parse_listing_contact(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.contact_name == "דוד כהן"

    def test_parse_listing_dates(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.posted_at is not None
        assert listing.posted_at.year == 2024

    def test_parse_listing_description(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert "פלורנטין" in listing.description

    def test_parse_listing_missing_id(self):
        result = FacebookParser.parse_listing({})
        assert result is None

    def test_parse_listing_sold_skipped(self, single_item):
        single_item["is_sold"] = True
        result = FacebookParser.parse_listing(single_item)
        assert result is None

    def test_parse_listing_pending_skipped(self, single_item):
        single_item["is_pending"] = True
        result = FacebookParser.parse_listing(single_item)
        assert result is None

    def test_raw_data_preserved(self, single_item):
        listing = FacebookParser.parse_listing(single_item)
        assert listing is not None
        assert listing.raw_data == single_item

    # ------------------------------------------------------------------
    # Bulk parse from API response
    # ------------------------------------------------------------------

    def test_parse_all_items_from_graphql(self, graphql_response):
        """Parse all items from GraphQL response — none should crash."""
        items = FacebookParser.extract_feed_items(graphql_response)
        parsed = [FacebookParser.parse_listing(item) for item in items]
        successful = [p for p in parsed if p is not None]
        assert len(successful) == 4
        # All should parse successfully
        assert len(successful) / len(items) >= 0.8

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def test_parse_price_ils(self):
        price, currency = FacebookParser._parse_price({"amount": "5200", "currency": "ILS"})
        assert price == 5200.0
        assert currency == Currency.ILS

    def test_parse_price_usd(self):
        price, currency = FacebookParser._parse_price({"amount": "1500", "currency": "USD"})
        assert price == 1500.0
        assert currency == Currency.USD

    def test_parse_price_none(self):
        price, currency = FacebookParser._parse_price(None)
        assert price is None
        assert currency == Currency.ILS

    def test_parse_timestamp(self):
        dt = FacebookParser._parse_timestamp(1706198400)
        assert dt is not None
        assert dt.year == 2024

    def test_parse_timestamp_none(self):
        assert FacebookParser._parse_timestamp(None) is None

    def test_parse_rooms_from_subtitles(self):
        raw = {"custom_sub_titles_with_rendering_flags": [
            {"subtitle": "3 חדרים"},
            {"subtitle": "50 מ\"ר"},
        ]}
        assert FacebookParser._parse_rooms_from_subtitles(raw) == 3.0

    def test_parse_area_from_subtitles(self):
        raw = {"custom_sub_titles_with_rendering_flags": [
            {"subtitle": "3 חדרים"},
            {"subtitle": "50 מ\"ר"},
        ]}
        assert FacebookParser._parse_area_from_subtitles(raw) == 50.0

    def test_parse_floor_from_subtitles(self):
        raw = {"custom_sub_titles_with_rendering_flags": [
            {"subtitle": "קומה 5"},
        ]}
        assert FacebookParser._parse_floor_from_subtitles(raw) == 5

    def test_parse_property_type_mapping(self):
        assert FacebookParser._parse_property_type("APARTMENT") == PropertyType.APARTMENT
        assert FacebookParser._parse_property_type("HOUSE") == PropertyType.HOUSE
        assert FacebookParser._parse_property_type("PENTHOUSE") == PropertyType.PENTHOUSE
        assert FacebookParser._parse_property_type("STUDIO") == PropertyType.STUDIO
        assert FacebookParser._parse_property_type("UNKNOWN_TYPE") == PropertyType.OTHER
        assert FacebookParser._parse_property_type(None) is None
