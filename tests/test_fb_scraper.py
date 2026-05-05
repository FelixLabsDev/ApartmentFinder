import json
from pathlib import Path

import httpx
import pytest

from src.models.filters import SearchFilter
from src.scrapers.facebook.scraper import FacebookGraphQLScraper

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestFacebookGraphQLScraper:
    async def test_scrape_with_mocked_response(self, httpx_mock):
        """Test scraper with mocked GraphQL response."""
        with open(FIXTURES_DIR / "fb_graphql_sample.json", "r", encoding="utf-8") as f:
            fixture = json.load(f)

        # First request returns listings, second returns empty (no more pages)
        httpx_mock.add_response(json=fixture)
        httpx_mock.add_response(json={
            "data": {
                "marketplace_search": {
                    "feed_units": {
                        "edges": [],
                        "page_info": {"has_next_page": False, "end_cursor": None},
                    }
                }
            }
        })

        scraper = FacebookGraphQLScraper()
        search_filter = SearchFilter(
            cities=["tel-aviv"],
            min_price=3000,
            max_price=8000,
        )

        listings = await scraper.scrape(search_filter)
        assert len(listings) > 0
        assert all(listing.source == "facebook" for listing in listings)
        assert all(listing.city for listing in listings)

        await scraper.close()

    async def test_scrape_no_matching_cities(self, httpx_mock):
        """Cities with no location ID should return empty list."""
        scraper = FacebookGraphQLScraper()
        search_filter = SearchFilter(cities=["nonexistent-city"])

        listings = await scraper.scrape(search_filter)
        assert listings == []

        await scraper.close()

    async def test_scrape_default_city(self, httpx_mock):
        """Empty cities list should default to Tel Aviv."""
        with open(FIXTURES_DIR / "fb_graphql_sample.json", "r", encoding="utf-8") as f:
            fixture = json.load(f)

        httpx_mock.add_response(json=fixture)
        httpx_mock.add_response(json={
            "data": {
                "marketplace_search": {
                    "feed_units": {
                        "edges": [],
                        "page_info": {"has_next_page": False, "end_cursor": None},
                    }
                }
            }
        })

        scraper = FacebookGraphQLScraper()
        search_filter = SearchFilter()  # No cities

        listings = await scraper.scrape(search_filter)
        assert len(listings) > 0

        await scraper.close()

    async def test_health_check_success(self, httpx_mock):
        httpx_mock.add_response(json={"data": {"marketplace_search": {}}})

        scraper = FacebookGraphQLScraper()
        result = await scraper.health_check()
        assert result is True

        await scraper.close()

    @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
    async def test_health_check_failure(self, httpx_mock):
        httpx_mock.add_response(status_code=500)

        scraper = FacebookGraphQLScraper()
        result = await scraper.health_check()
        assert result is False

        await scraper.close()

    async def test_graphql_error_tries_next_doc_id(self, httpx_mock):
        """If first doc_id returns an error, scraper should try the next one."""
        with open(FIXTURES_DIR / "fb_graphql_sample.json", "r", encoding="utf-8") as f:
            fixture = json.load(f)

        # First doc_id returns error
        httpx_mock.add_response(json={"errors": [{"message": "Invalid doc_id"}]})
        # Second doc_id succeeds
        httpx_mock.add_response(json=fixture)
        # End of pagination
        httpx_mock.add_response(json={
            "data": {
                "marketplace_search": {
                    "feed_units": {
                        "edges": [],
                        "page_info": {"has_next_page": False, "end_cursor": None},
                    }
                }
            }
        })

        scraper = FacebookGraphQLScraper()
        listings = await scraper.scrape(SearchFilter(cities=["tel-aviv"]))
        assert len(listings) > 0

        await scraper.close()

    def test_build_variables(self):
        scraper = FacebookGraphQLScraper()
        f = SearchFilter(min_price=3000, max_price=7000)
        variables = scraper._build_variables(f, "110884905606138")

        browse_params = variables["params"]["browse_request_params"]
        assert browse_params["filter_price_lower_bound"] == 3000
        assert browse_params["filter_price_upper_bound"] == 7000

    def test_build_variables_with_cursor(self):
        scraper = FacebookGraphQLScraper()
        variables = scraper._build_variables(
            SearchFilter(), "110884905606138", cursor="AQHRbG9..."
        )
        assert variables["cursor"] == "AQHRbG9..."

    def test_resolve_location_ids(self):
        scraper = FacebookGraphQLScraper()
        ids = scraper._resolve_location_ids(SearchFilter(cities=["tel-aviv", "jerusalem"]))
        assert len(ids) == 2

    def test_resolve_location_ids_default(self):
        scraper = FacebookGraphQLScraper()
        ids = scraper._resolve_location_ids(SearchFilter())
        assert len(ids) == 1  # Defaults to Tel Aviv
