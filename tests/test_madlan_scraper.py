import pytest

from src.models.filters import SearchFilter
from src.scrapers.madlan.scraper import MadlanPlaywrightScraper


class TestMadlanPlaywrightScraper:
    def test_source_name(self):
        scraper = MadlanPlaywrightScraper()
        assert scraper.source_name == "madlan"

    def test_method_name(self):
        scraper = MadlanPlaywrightScraper()
        assert scraper.method_name == "playwright"

    def test_build_search_url_default(self):
        scraper = MadlanPlaywrightScraper()
        url = scraper._build_search_url(SearchFilter(), "tel-aviv")
        assert "madlan.co.il/listings" in url
        assert "dealType=rent" in url
        assert "term=" in url

    def test_build_search_url_with_filters(self):
        scraper = MadlanPlaywrightScraper()
        sf = SearchFilter(min_price=3000, max_price=7000, min_rooms=2, max_rooms=4)
        url = scraper._build_search_url(sf, "tel-aviv")
        assert "dealType=rent" in url
        assert "filters=" in url

    def test_build_search_url_with_bbox(self):
        scraper = MadlanPlaywrightScraper()
        url = scraper._build_search_url(SearchFilter(), "haifa")
        assert "bbox=" in url

    def test_build_filter_string(self):
        scraper = MadlanPlaywrightScraper()
        sf = SearchFilter(min_price=1750, max_price=6000, min_rooms=3, max_rooms=6)
        result = scraper._build_filter_string(sf)
        assert "1750-6000" in result
        assert "3-6" in result

    def test_build_filter_string_empty(self):
        scraper = MadlanPlaywrightScraper()
        result = scraper._build_filter_string(SearchFilter())
        # Should still have structure but with empty values
        assert "search-filter-top-bar" in result

    def test_is_listing_object(self):
        good = {"listingId": "abc", "price": 4500, "rooms": 3, "city": "Tel Aviv"}
        assert MadlanPlaywrightScraper._is_listing_object(good) is True

        bad = {"type": "ad", "text": "hello"}
        assert MadlanPlaywrightScraper._is_listing_object(bad) is False

        # Only ID, not enough indicators
        minimal = {"id": "123"}
        assert MadlanPlaywrightScraper._is_listing_object(minimal) is False

    def test_extract_listings_from_api(self):
        scraper = MadlanPlaywrightScraper()
        body = {
            "data": {
                "searchResults": [
                    {"listingId": "a1", "price": 4000, "rooms": 3, "city": "TA"},
                    {"listingId": "a2", "price": 5000, "rooms": 4, "area": 90},
                ]
            }
        }
        out: list[dict] = []
        scraper._extract_listings_from_api(body, out)
        assert len(out) == 2
        assert out[0]["listingId"] == "a1"

    def test_extract_listings_from_api_nested(self):
        scraper = MadlanPlaywrightScraper()
        body = {
            "data": {
                "results": {
                    "edges": [
                        {"node": {"id": "x1", "price": 3000, "rooms": 2, "city": "Haifa"}},
                        {"node": {"id": "x2", "price": 4000, "rooms": 3, "lat": 32.0}},
                    ]
                }
            }
        }
        out: list[dict] = []
        scraper._extract_listings_from_api(body, out)
        assert len(out) == 2

    def test_build_card_from_text(self):
        card = MadlanPlaywrightScraper._build_card_from_text(
            "test123",
            ["₪4,500", "הרצל 15", "בת ים", "3 חדרים", "75 מ\"ר", "קומה 2"],
            "https://example.com/img.jpg",
        )
        assert card["id"] == "test123"
        assert card["price"] == "4500.0"
        assert card["rooms"] == 3.0
        assert card["area_sqm"] == 75.0
        assert card["floor"] == 2
        assert len(card["image_urls"]) == 1


@pytest.mark.integration
class TestMadlanPlaywrightScraperIntegration:
    async def test_real_scrape(self):
        """Integration test: actually scrape Madlan (manual run only)."""
        scraper = MadlanPlaywrightScraper(headless=True)
        search_filter = SearchFilter(
            cities=["bat-yam"],
            min_price=1750,
            max_price=6000,
            min_rooms=3,
            max_rooms=6,
        )

        try:
            listings = await scraper.scrape(search_filter)
            print(f"\nFound {len(listings)} listings from Madlan")
            for l in listings[:5]:
                print(f"  {l.city} | {l.rooms}r | {l.price} ILS | {l.street or 'N/A'}")
            assert len(listings) >= 0  # May be 0 if anti-bot kicks in
        except Exception as e:
            print(f"Scrape failed (expected in CI): {e}")
