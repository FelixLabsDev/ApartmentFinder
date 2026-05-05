from unittest.mock import AsyncMock

import pytest

from src.models.enums import Currency, Source
from src.models.filters import SearchFilter
from src.models.listing import ListingCreate
from src.pipeline.pipeline import ScrapePipeline
from src.scrapers.orchestrator import ScraperOrchestrator, ScrapeResult


def _make_listing(**overrides) -> ListingCreate:
    defaults = {
        "source": Source.YAD2,
        "source_id": "test123",
        "source_url": "https://example.com/test",
        "city": "תל אביב יפו",
        "price": 5000.0,
        "rooms": 3.0,
    }
    defaults.update(overrides)
    return ListingCreate(**defaults)


class TestScrapePipeline:
    async def test_full_pipeline_run(self):
        """Pipeline: scrape → normalize → dedup → filter."""
        listings = [
            _make_listing(source_id="1", city="תל אביב יפו", price=5000.0),
            _make_listing(source_id="2", city="ירושלים", price=3000.0),
        ]

        orchestrator = ScraperOrchestrator()
        orchestrator.scrape_all = AsyncMock(return_value=[
            ScrapeResult(source="yad2", method="api", listings=listings),
        ])

        pipeline = ScrapePipeline(orchestrator)
        result = await pipeline.run(SearchFilter())

        assert result.total_scraped == 2
        assert result.total_after_dedup == 2  # Different cities, no dedup
        assert result.total_after_filter == 2
        assert len(result.listings) == 2
        # Cities should be normalized
        cities = {l.city for l in result.listings}
        assert "tel-aviv" in cities
        assert "jerusalem" in cities

    async def test_pipeline_deduplication(self):
        """Duplicate listings across sources should be deduped."""
        yad2_listing = _make_listing(
            source=Source.YAD2, source_id="y1", city="tel-aviv",
            street="dizengoff", house_number="100", rooms=3.0, floor=2, price=5000.0,
        )
        fb_listing = _make_listing(
            source=Source.FACEBOOK, source_id="f1", city="tel-aviv",
            street="dizengoff", house_number="100", rooms=3.0, floor=2, price=5000.0,
        )

        orchestrator = ScraperOrchestrator()
        orchestrator.scrape_all = AsyncMock(return_value=[
            ScrapeResult(source="yad2", method="api", listings=[yad2_listing]),
            ScrapeResult(source="facebook", method="graphql", listings=[fb_listing]),
        ])

        pipeline = ScrapePipeline(orchestrator)
        result = await pipeline.run(SearchFilter())

        assert result.total_scraped == 2
        assert result.total_after_dedup == 1  # Deduped to 1

    async def test_pipeline_filtering(self):
        """Pipeline should apply search filter after normalization."""
        listings = [
            _make_listing(source_id="1", city="tel-aviv", price=5000.0),
            _make_listing(source_id="2", city="tel-aviv", price=10000.0),
        ]

        orchestrator = ScraperOrchestrator()
        orchestrator.scrape_all = AsyncMock(return_value=[
            ScrapeResult(source="yad2", method="api", listings=listings),
        ])

        pipeline = ScrapePipeline(orchestrator)
        result = await pipeline.run(SearchFilter(max_price=7000))

        assert result.total_scraped == 2
        assert result.total_after_filter == 1
        assert result.listings[0].price == 5000.0

    async def test_pipeline_empty_scrape(self):
        """Pipeline handles no results gracefully."""
        orchestrator = ScraperOrchestrator()
        orchestrator.scrape_all = AsyncMock(return_value=[
            ScrapeResult(source="yad2", method="api", listings=[]),
        ])

        pipeline = ScrapePipeline(orchestrator)
        result = await pipeline.run(SearchFilter())

        assert result.total_scraped == 0
        assert result.listings == []

    async def test_pipeline_usd_conversion(self):
        """USD prices should be converted to ILS during normalization."""
        listings = [
            _make_listing(source_id="1", city="tel-aviv", price=1000.0, currency=Currency.USD),
        ]

        orchestrator = ScraperOrchestrator()
        orchestrator.scrape_all = AsyncMock(return_value=[
            ScrapeResult(source="facebook", method="graphql", listings=listings),
        ])

        pipeline = ScrapePipeline(orchestrator)
        result = await pipeline.run(SearchFilter())

        assert len(result.listings) == 1
        assert result.listings[0].currency == Currency.ILS
        assert result.listings[0].price == 3700.0  # 1000 * 3.7


class TestScraperOrchestrator:
    async def test_orchestrator_runs_scrapers(self):
        listings = [_make_listing(source_id="1")]

        scraper = AsyncMock()
        scraper.source_name = "yad2"
        scraper.method_name = "api"
        scraper.scrape = AsyncMock(return_value=listings)

        orchestrator = ScraperOrchestrator()
        orchestrator.register("yad2", [scraper])

        results = await orchestrator.scrape_all(SearchFilter())
        assert len(results) == 1
        assert results[0].source == "yad2"
        assert len(results[0].listings) == 1

    async def test_orchestrator_fallback_on_failure(self):
        """If primary scraper fails, fallback should be tried."""
        primary = AsyncMock()
        primary.source_name = "facebook"
        primary.method_name = "graphql"
        primary.scrape = AsyncMock(side_effect=Exception("Auth failed"))

        fallback = AsyncMock()
        fallback.source_name = "facebook"
        fallback.method_name = "playwright"
        fallback.scrape = AsyncMock(return_value=[_make_listing(source_id="fb1")])

        orchestrator = ScraperOrchestrator()
        orchestrator.register("facebook", [primary, fallback])

        results = await orchestrator.scrape_all(SearchFilter())
        assert len(results) == 1
        assert results[0].method == "playwright"
        assert len(results[0].listings) == 1

    async def test_orchestrator_all_fail(self):
        """If all scrapers fail, result should have error."""
        scraper = AsyncMock()
        scraper.source_name = "yad2"
        scraper.method_name = "api"
        scraper.scrape = AsyncMock(side_effect=Exception("Network error"))

        orchestrator = ScraperOrchestrator()
        orchestrator.register("yad2", [scraper])

        results = await orchestrator.scrape_all(SearchFilter())
        assert len(results) == 1
        assert results[0].error is not None
        assert results[0].listings == []

    async def test_health_check_all(self):
        scraper = AsyncMock()
        scraper.health_check = AsyncMock(return_value=True)

        orchestrator = ScraperOrchestrator()
        orchestrator.register("yad2", [scraper])

        checks = await orchestrator.health_check_all()
        assert checks["yad2"] is True
