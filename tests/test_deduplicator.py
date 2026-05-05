from src.models.enums import Currency, PropertyType, Source
from src.models.listing import ListingCreate
from src.pipeline.deduplicator import ListingDeduplicator


def _make_listing(**overrides) -> ListingCreate:
    defaults = {
        "source": Source.YAD2,
        "source_id": "test123",
        "source_url": "https://example.com/test",
        "city": "tel-aviv",
        "street": "dizengoff",
        "house_number": "100",
        "rooms": 3.0,
        "floor": 2,
        "price": 5000.0,
    }
    defaults.update(overrides)
    return ListingCreate(**defaults)


class TestListingDeduplicator:
    def setup_method(self):
        self.dedup = ListingDeduplicator()

    def test_same_listing_same_fingerprint(self):
        l1 = _make_listing()
        l2 = _make_listing()
        fp1 = self.dedup.compute_fingerprint(l1)
        fp2 = self.dedup.compute_fingerprint(l2)
        assert fp1 == fp2

    def test_different_city_different_fingerprint(self):
        l1 = _make_listing(city="tel-aviv")
        l2 = _make_listing(city="jerusalem")
        assert self.dedup.compute_fingerprint(l1) != self.dedup.compute_fingerprint(l2)

    def test_different_street_different_fingerprint(self):
        l1 = _make_listing(street="dizengoff")
        l2 = _make_listing(street="rothschild")
        assert self.dedup.compute_fingerprint(l1) != self.dedup.compute_fingerprint(l2)

    def test_different_rooms_different_fingerprint(self):
        l1 = _make_listing(rooms=3.0)
        l2 = _make_listing(rooms=4.0)
        assert self.dedup.compute_fingerprint(l1) != self.dedup.compute_fingerprint(l2)

    def test_similar_price_same_fingerprint(self):
        """Prices within the same 200 ILS bucket should match."""
        l1 = _make_listing(price=5000.0)
        l2 = _make_listing(price=5100.0)
        assert self.dedup.compute_fingerprint(l1) == self.dedup.compute_fingerprint(l2)

    def test_different_price_bucket_different_fingerprint(self):
        """Prices in different 200 ILS buckets should not match."""
        l1 = _make_listing(price=5000.0)
        l2 = _make_listing(price=5300.0)
        assert self.dedup.compute_fingerprint(l1) != self.dedup.compute_fingerprint(l2)

    def test_cross_source_same_fingerprint(self):
        """Same apartment on different sources should have same fingerprint."""
        l1 = _make_listing(source=Source.YAD2, source_id="yad2_123")
        l2 = _make_listing(source=Source.FACEBOOK, source_id="fb_456")
        assert self.dedup.compute_fingerprint(l1) == self.dedup.compute_fingerprint(l2)

    def test_deduplicate_batch_removes_duplicates(self):
        listings = [
            _make_listing(source_id="1"),
            _make_listing(source_id="2"),  # Same apt, different id
            _make_listing(source_id="3", city="jerusalem"),  # Different apt
        ]
        result = self.dedup.deduplicate_batch(listings)
        assert len(result) == 2

    def test_deduplicate_keeps_most_complete(self):
        """When deduplicating, keep the listing with more filled fields."""
        sparse = _make_listing(source_id="sparse", description=None, neighborhood=None)
        complete = _make_listing(
            source_id="complete",
            description="Great apartment",
            neighborhood="florentin",
            contact_name="David",
            image_urls=["https://img.com/1.jpg", "https://img.com/2.jpg"],
        )
        result = self.dedup.deduplicate_batch([sparse, complete])
        assert len(result) == 1
        assert result[0].source_id == "complete"

    def test_deduplicate_no_duplicates(self):
        """Batch with no duplicates should return all."""
        listings = [
            _make_listing(source_id="1", city="tel-aviv"),
            _make_listing(source_id="2", city="jerusalem"),
            _make_listing(source_id="3", city="haifa"),
        ]
        result = self.dedup.deduplicate_batch(listings)
        assert len(result) == 3

    def test_deduplicate_empty_batch(self):
        result = self.dedup.deduplicate_batch([])
        assert result == []

    def test_missing_fields_handled(self):
        """Listings with None fields should still produce a fingerprint."""
        l = _make_listing(street=None, house_number=None, price=None, rooms=None, floor=None)
        fp = self.dedup.compute_fingerprint(l)
        assert isinstance(fp, str)
        assert len(fp) == 64  # SHA256 hex length
