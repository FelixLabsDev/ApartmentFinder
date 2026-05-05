from src.models.enums import Currency, PropertyType, Source
from src.models.filters import SearchFilter
from src.models.listing import ListingCreate
from src.pipeline.filter_engine import FilterEngine


def _make_listing(**overrides) -> ListingCreate:
    defaults = {
        "source": Source.YAD2,
        "source_id": "test123",
        "source_url": "https://example.com/test",
        "city": "tel-aviv",
        "price": 5000.0,
        "rooms": 3.0,
        "floor": 2,
        "area_sqm": 60.0,
    }
    defaults.update(overrides)
    return ListingCreate(**defaults)


class TestFilterEngine:
    # --- City ---

    def test_filter_by_city(self):
        listings = [
            _make_listing(city="tel-aviv"),
            _make_listing(city="jerusalem"),
        ]
        result = FilterEngine.apply(listings, SearchFilter(cities=["tel-aviv"]))
        assert len(result) == 1
        assert result[0].city == "tel-aviv"

    def test_filter_multiple_cities(self):
        listings = [
            _make_listing(city="tel-aviv"),
            _make_listing(city="jerusalem"),
            _make_listing(city="haifa"),
        ]
        result = FilterEngine.apply(listings, SearchFilter(cities=["tel-aviv", "haifa"]))
        assert len(result) == 2

    def test_no_city_filter_passes_all(self):
        listings = [
            _make_listing(city="tel-aviv"),
            _make_listing(city="jerusalem"),
        ]
        result = FilterEngine.apply(listings, SearchFilter())
        assert len(result) == 2

    # --- Price ---

    def test_filter_min_price(self):
        listings = [
            _make_listing(price=3000.0),
            _make_listing(price=5000.0),
            _make_listing(price=7000.0),
        ]
        result = FilterEngine.apply(listings, SearchFilter(min_price=4000))
        assert len(result) == 2

    def test_filter_max_price(self):
        listings = [
            _make_listing(price=3000.0),
            _make_listing(price=5000.0),
            _make_listing(price=7000.0),
        ]
        result = FilterEngine.apply(listings, SearchFilter(max_price=5000))
        assert len(result) == 2

    def test_filter_price_range(self):
        listings = [
            _make_listing(price=3000.0),
            _make_listing(price=5000.0),
            _make_listing(price=7000.0),
        ]
        result = FilterEngine.apply(listings, SearchFilter(min_price=4000, max_price=6000))
        assert len(result) == 1
        assert result[0].price == 5000.0

    # --- Rooms ---

    def test_filter_rooms_range(self):
        listings = [
            _make_listing(rooms=2.0),
            _make_listing(rooms=3.0),
            _make_listing(rooms=4.0),
            _make_listing(rooms=5.0),
        ]
        result = FilterEngine.apply(listings, SearchFilter(min_rooms=3, max_rooms=4))
        assert len(result) == 2

    # --- Area ---

    def test_filter_area_range(self):
        listings = [
            _make_listing(area_sqm=40.0),
            _make_listing(area_sqm=60.0),
            _make_listing(area_sqm=80.0),
        ]
        result = FilterEngine.apply(listings, SearchFilter(min_area_sqm=50, max_area_sqm=70))
        assert len(result) == 1
        assert result[0].area_sqm == 60.0

    # --- Floor ---

    def test_filter_floor_range(self):
        listings = [
            _make_listing(floor=1),
            _make_listing(floor=3),
            _make_listing(floor=5),
        ]
        result = FilterEngine.apply(listings, SearchFilter(min_floor=2, max_floor=4))
        assert len(result) == 1
        assert result[0].floor == 3

    # --- Property types ---

    def test_filter_property_type(self):
        listings = [
            _make_listing(property_type=PropertyType.APARTMENT),
            _make_listing(property_type=PropertyType.HOUSE),
            _make_listing(property_type=PropertyType.PENTHOUSE),
        ]
        result = FilterEngine.apply(listings, SearchFilter(property_types=["apartment", "penthouse"]))
        assert len(result) == 2

    def test_filter_property_type_excludes_none(self):
        listings = [
            _make_listing(property_type=PropertyType.APARTMENT),
            _make_listing(property_type=None),
        ]
        result = FilterEngine.apply(listings, SearchFilter(property_types=["apartment"]))
        assert len(result) == 1

    # --- Features ---

    def test_filter_require_parking(self):
        listings = [
            _make_listing(has_parking=True),
            _make_listing(has_parking=False),
            _make_listing(has_parking=None),
        ]
        result = FilterEngine.apply(listings, SearchFilter(require_parking=True))
        assert len(result) == 1
        assert result[0].has_parking is True

    def test_filter_require_elevator(self):
        listings = [
            _make_listing(has_elevator=True),
            _make_listing(has_elevator=False),
        ]
        result = FilterEngine.apply(listings, SearchFilter(require_elevator=True))
        assert len(result) == 1

    def test_filter_require_furnished(self):
        listings = [
            _make_listing(is_furnished=True),
            _make_listing(is_furnished=False),
        ]
        result = FilterEngine.apply(listings, SearchFilter(require_furnished=True))
        assert len(result) == 1

    def test_no_feature_filter_passes_all(self):
        listings = [
            _make_listing(has_parking=True),
            _make_listing(has_parking=False),
        ]
        result = FilterEngine.apply(listings, SearchFilter())
        assert len(result) == 2

    # --- Keywords ---

    def test_filter_keywords(self):
        listings = [
            _make_listing(title="Beautiful apartment in Florentin"),
            _make_listing(title="Cheap room in Ramat Gan"),
        ]
        result = FilterEngine.apply(listings, SearchFilter(keywords=["florentin"]))
        assert len(result) == 1
        assert "Florentin" in result[0].title

    def test_filter_keywords_in_description(self):
        listings = [
            _make_listing(description="Near the beach, renovated"),
            _make_listing(description="Old building, needs work"),
        ]
        result = FilterEngine.apply(listings, SearchFilter(keywords=["renovated"]))
        assert len(result) == 1

    def test_filter_exclude_keywords(self):
        listings = [
            _make_listing(title="Beautiful apartment"),
            _make_listing(title="Sublet only - beautiful apartment"),
        ]
        result = FilterEngine.apply(listings, SearchFilter(exclude_keywords=["sublet"]))
        assert len(result) == 1
        assert "Sublet" not in result[0].title

    # --- Combined filters ---

    def test_combined_filters(self):
        listings = [
            _make_listing(city="tel-aviv", price=5000.0, rooms=3.0, has_parking=True),
            _make_listing(city="tel-aviv", price=8000.0, rooms=3.0, has_parking=True),
            _make_listing(city="jerusalem", price=5000.0, rooms=3.0, has_parking=True),
            _make_listing(city="tel-aviv", price=5000.0, rooms=2.0, has_parking=True),
            _make_listing(city="tel-aviv", price=5000.0, rooms=3.0, has_parking=False),
        ]
        search_filter = SearchFilter(
            cities=["tel-aviv"],
            max_price=6000,
            min_rooms=3,
            require_parking=True,
        )
        result = FilterEngine.apply(listings, search_filter)
        assert len(result) == 1
        assert result[0].city == "tel-aviv"
        assert result[0].price == 5000.0
        assert result[0].rooms == 3.0
        assert result[0].has_parking is True

    def test_empty_listings(self):
        result = FilterEngine.apply([], SearchFilter())
        assert result == []

    def test_match_all_filter(self):
        """Default SearchFilter should pass everything."""
        listings = [_make_listing() for _ in range(5)]
        result = FilterEngine.apply(listings, SearchFilter())
        assert len(result) == 5
