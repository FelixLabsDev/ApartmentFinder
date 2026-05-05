import json
from pathlib import Path

import httpx
import pytest

from src.models.filters import SearchFilter
from src.scrapers.yad2.scraper import Yad2ApiScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestYad2ApiScraper:
    async def test_scrape_with_mocked_response(self, httpx_mock):
        """Test scraper with mocked HTTP response."""
        with open(FIXTURES_DIR / "yad2_api_sample.json", "r", encoding="utf-8") as f:
            fixture = json.load(f)

        # Mock the API response — match any request to the Yad2 API
        httpx_mock.add_response(
            url=httpx.URL("https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/rent").copy_with(
                params={"city": "5000", "price": "3000-7000", "rooms": "2.0-4.0", "page": "1"}
            ),
            json=fixture,
        )
        # Second page returns empty feed
        httpx_mock.add_response(json={"feed": {"feed_items": [], "total_pages": 1, "current_page": 2}})

        scraper = Yad2ApiScraper()
        search_filter = SearchFilter(
            cities=["tel-aviv"],
            min_price=3000,
            max_price=7000,
            min_rooms=2,
            max_rooms=4,
        )

        listings = await scraper.scrape(search_filter)
        assert len(listings) > 0
        assert all(listing.source == "yad2" for listing in listings)
        assert all(listing.city for listing in listings)

        # Cleanup
        await scraper._client.close()

    async def test_health_check_success(self, httpx_mock):
        httpx_mock.add_response(json={"feed": {"feed_items": []}})

        scraper = Yad2ApiScraper()
        result = await scraper.health_check()
        assert result is True
        await scraper._client.close()

    async def test_health_check_failure(self, httpx_mock):
        httpx_mock.add_response(status_code=500)

        scraper = Yad2ApiScraper()
        result = await scraper.health_check()
        assert result is False
        await scraper._client.close()

    def test_build_params(self):
        scraper = Yad2ApiScraper()
        f = SearchFilter(cities=["tel-aviv"], min_price=3000, max_price=7000, min_rooms=2, max_rooms=4)
        params = scraper._build_params(f)
        assert params["city"] == "5000"
        assert params["price"] == "3000-7000"
        assert params["rooms"] == "2.0-4.0"

    def test_build_params_empty_filter(self):
        scraper = Yad2ApiScraper()
        params = scraper._build_params(SearchFilter())
        assert params == {}


@pytest.mark.integration
class TestYad2ApiScraperIntegration:
    async def test_real_scrape(self):
        """Integration test: actually hit Yad2 API (manual run only)."""
        scraper = Yad2ApiScraper()
        search_filter = SearchFilter(cities=["tel-aviv"], max_price=7000, min_rooms=2, max_rooms=3)

        try:
            listings = await scraper.scrape(search_filter)
            print(f"\nFound {len(listings)} listings")
            for l in listings[:3]:
                print(f"  {l.city} | {l.rooms}r | {l.price} ILS | {l.street or 'N/A'}")
            assert len(listings) > 0
        finally:
            await scraper._client.close()
