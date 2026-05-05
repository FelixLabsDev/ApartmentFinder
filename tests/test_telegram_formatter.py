from src.models.enums import Currency, PropertyType, Source
from src.models.listing import ListingCreate
from src.notifications.formatter import TelegramFormatter


def _make_listing(**overrides) -> ListingCreate:
    defaults = {
        "source": Source.YAD2,
        "source_id": "test123",
        "source_url": "https://www.yad2.co.il/realestate/item/test123",
        "city": "tel-aviv",
        "price": 5200.0,
        "currency": Currency.ILS,
        "rooms": 3.0,
        "floor": 2,
        "total_floors": 5,
        "area_sqm": 60.0,
        "street": "Dizengoff",
        "house_number": "42",
        "neighborhood": "Center",
        "property_type": PropertyType.APARTMENT,
        "has_parking": True,
        "has_elevator": True,
        "has_balcony": True,
        "has_air_conditioning": True,
        "description": "Beautiful renovated apartment in the heart of Tel Aviv.",
    }
    defaults.update(overrides)
    return ListingCreate(**defaults)


class TestTelegramFormatter:
    def test_format_listing_basic(self):
        listing = _make_listing()
        result = TelegramFormatter.format_listing(listing)

        assert "<b>3.0r in tel-aviv</b>" in result
        assert "5,200" in result
        assert "Dizengoff 42" in result
        assert "Center" in result
        assert "floor 2/5" in result
        assert "60m\u00b2" in result

    def test_format_listing_features(self):
        listing = _make_listing()
        result = TelegramFormatter.format_listing(listing)

        assert "Parking" in result
        assert "Elevator" in result
        assert "Balcony" in result
        assert "A/C" in result

    def test_format_listing_no_features(self):
        listing = _make_listing(
            has_parking=False,
            has_elevator=False,
            has_balcony=False,
            has_air_conditioning=False,
        )
        result = TelegramFormatter.format_listing(listing)
        # No feature line should appear
        assert "Parking" not in result

    def test_format_listing_description_truncated(self):
        long_desc = "A" * 200
        listing = _make_listing(description=long_desc)
        result = TelegramFormatter.format_listing(listing)

        assert "..." in result
        # Should not contain the full 200 chars
        assert "A" * 101 not in result

    def test_format_listing_link(self):
        listing = _make_listing()
        result = TelegramFormatter.format_listing(listing)

        assert 'href="https://www.yad2.co.il/realestate/item/test123"' in result
        assert "View on yad2" in result

    def test_format_listing_minimal(self):
        listing = ListingCreate(
            source=Source.FACEBOOK,
            source_id="fb123",
            source_url="https://facebook.com/item/fb123",
            city="jerusalem",
        )
        result = TelegramFormatter.format_listing(listing)

        assert "<b>jerusalem</b>" in result
        assert "facebook.com" in result

    def test_format_price_ils(self):
        assert TelegramFormatter._format_price(5200.0, "ILS") == "5,200 \u20aa"

    def test_format_price_usd(self):
        assert TelegramFormatter._format_price(1500.0, "USD") == "$1,500"

    def test_format_price_none(self):
        assert TelegramFormatter._format_price(None, "ILS") == ""

    def test_format_batch(self):
        listings = [_make_listing(source_id=str(i)) for i in range(3)]
        result = TelegramFormatter.format_batch(listings, header="New Listings!")

        assert "<b>New Listings!</b>" in result
        assert result.count("---") == 2  # Separators between listings
        assert result.count("Dizengoff") == 3  # Each listing has the street

    def test_format_batch_no_header(self):
        listings = [_make_listing()]
        result = TelegramFormatter.format_batch(listings)

        assert "New Listings!" not in result

    def test_format_summary_with_listings(self):
        result = TelegramFormatter.format_summary(5, 2)
        assert "<b>5</b>" in result
        assert "2 sources" in result

    def test_format_summary_single(self):
        result = TelegramFormatter.format_summary(1, 1)
        assert "1</b> new listing " in result  # singular
        assert "1 source" in result

    def test_format_summary_none(self):
        result = TelegramFormatter.format_summary(0, 2)
        assert "No new listings" in result

    def test_format_listing_property_type(self):
        listing = _make_listing(property_type=PropertyType.PENTHOUSE)
        result = TelegramFormatter.format_listing(listing)
        assert "penthouse" in result

    def test_format_listing_pet_friendly(self):
        listing = _make_listing(pet_friendly=True)
        result = TelegramFormatter.format_listing(listing)
        assert "Pet OK" in result

    def test_format_listing_furnished(self):
        listing = _make_listing(is_furnished=True)
        result = TelegramFormatter.format_listing(listing)
        assert "Furnished" in result
