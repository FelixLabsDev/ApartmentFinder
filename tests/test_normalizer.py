from src.models.enums import Currency, PropertyType, Source
from src.models.listing import ListingCreate
from src.pipeline.normalizer import ListingNormalizer


def _make_listing(**overrides) -> ListingCreate:
    defaults = {
        "source": Source.YAD2,
        "source_id": "test123",
        "source_url": "https://example.com/test",
        "city": "תל אביב יפו",
    }
    defaults.update(overrides)
    return ListingCreate(**defaults)


class TestListingNormalizer:
    def setup_method(self):
        self.normalizer = ListingNormalizer()

    # --- City normalization ---

    def test_hebrew_city_to_slug(self):
        listing = _make_listing(city="תל אביב יפו")
        result = self.normalizer.normalize(listing)
        assert result.city == "tel-aviv"

    def test_hebrew_jerusalem(self):
        listing = _make_listing(city="ירושלים")
        result = self.normalizer.normalize(listing)
        assert result.city == "jerusalem"

    def test_english_city_normalized(self):
        listing = _make_listing(city="Tel Aviv")
        result = self.normalizer.normalize(listing)
        assert result.city == "tel-aviv"

    def test_city_with_spaces_trimmed(self):
        listing = _make_listing(city="  חיפה  ")
        result = self.normalizer.normalize(listing)
        assert result.city == "haifa"

    def test_unknown_city_kept_lowercase(self):
        listing = _make_listing(city="Some Unknown City")
        result = self.normalizer.normalize(listing)
        assert result.city == "some unknown city"

    def test_empty_city_unchanged(self):
        listing = _make_listing(city="")
        result = self.normalizer.normalize(listing)
        assert result.city == ""

    # --- Price normalization ---

    def test_ils_price_unchanged(self):
        listing = _make_listing(price=5000.0, currency=Currency.ILS)
        result = self.normalizer.normalize(listing)
        assert result.price == 5000.0
        assert result.currency == Currency.ILS

    def test_usd_converted_to_ils(self):
        listing = _make_listing(price=1000.0, currency=Currency.USD)
        result = self.normalizer.normalize(listing)
        assert result.price == 3700.0  # 1000 * 3.7
        assert result.currency == Currency.ILS

    def test_none_price_unchanged(self):
        listing = _make_listing(price=None)
        result = self.normalizer.normalize(listing)
        assert result.price is None

    # --- Phone normalization ---

    def test_phone_with_leading_zero(self):
        listing = _make_listing(contact_phone="054-1234567")
        result = self.normalizer.normalize(listing)
        assert result.contact_phone == "+972541234567"

    def test_phone_with_972_prefix(self):
        listing = _make_listing(contact_phone="+972-54-123-4567")
        result = self.normalizer.normalize(listing)
        assert result.contact_phone == "+972541234567"

    def test_phone_none(self):
        listing = _make_listing(contact_phone=None)
        result = self.normalizer.normalize(listing)
        assert result.contact_phone is None

    def test_phone_empty_string(self):
        listing = _make_listing(contact_phone="")
        result = self.normalizer.normalize(listing)
        assert result.contact_phone is None

    # --- Property type normalization ---

    def test_property_type_enum_passthrough(self):
        listing = _make_listing(property_type=PropertyType.APARTMENT)
        result = self.normalizer.normalize(listing)
        assert result.property_type == PropertyType.APARTMENT

    def test_property_type_none(self):
        listing = _make_listing(property_type=None)
        result = self.normalizer.normalize(listing)
        assert result.property_type is None

    # --- Text cleanup ---

    def test_title_whitespace_cleaned(self):
        listing = _make_listing(title="  דירה   יפה   מאוד  ")
        result = self.normalizer.normalize(listing)
        assert result.title == "דירה יפה מאוד"

    def test_description_whitespace_cleaned(self):
        listing = _make_listing(description="line1\n\n  line2  \n  line3")
        result = self.normalizer.normalize(listing)
        assert result.description == "line1 line2 line3"

    def test_empty_description_becomes_none(self):
        listing = _make_listing(description="")
        result = self.normalizer.normalize(listing)
        assert result.description is None

    # --- Batch normalization ---

    def test_normalize_batch(self):
        listings = [
            _make_listing(city="תל אביב יפו", price=5000.0),
            _make_listing(city="ירושלים", price=3000.0),
            _make_listing(city="חיפה", price=4000.0),
        ]
        results = self.normalizer.normalize_batch(listings)
        assert len(results) == 3
        assert results[0].city == "tel-aviv"
        assert results[1].city == "jerusalem"
        assert results[2].city == "haifa"
