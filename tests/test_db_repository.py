from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repository import ListingRepository, ScrapeRunRepository, SearchProfileRepository
from src.models import ListingCreate, SearchFilter, Source


def _make_listing(**kwargs) -> ListingCreate:
    defaults = {
        "source": Source.YAD2,
        "source_id": "test-1",
        "source_url": "https://yad2.co.il/test-1",
        "city": "tel-aviv",
    }
    defaults.update(kwargs)
    return ListingCreate(**defaults)


class TestListingRepository:
    @pytest.fixture
    def repo(self, async_session: AsyncSession):
        return ListingRepository(async_session)

    async def test_upsert_new_listings(self, repo: ListingRepository, async_session: AsyncSession):
        listings = [
            _make_listing(source_id="a1", price=5000, rooms=3),
            _make_listing(source_id="a2", price=6000, rooms=4),
            _make_listing(source_id="a3", price=4500, rooms=2),
        ]
        fingerprints = ["fp1", "fp2", "fp3"]

        total, new_count = await repo.upsert_listings(listings, fingerprints)
        await async_session.commit()

        assert total == 3
        assert new_count == 3

    async def test_upsert_updates_existing(self, repo: ListingRepository, async_session: AsyncSession):
        listing = _make_listing(source_id="x1", price=5000)
        await repo.upsert_listings([listing], ["fp-x1"])
        await async_session.commit()

        # Upsert same source+source_id with new price
        listing_updated = _make_listing(source_id="x1", price=5500)
        total, new_count = await repo.upsert_listings([listing_updated], ["fp-x1"])
        await async_session.commit()

        assert total == 1
        assert new_count == 0  # Not new, was updated

        # Verify updated price
        rows = await repo.get_listings()
        assert len(rows) == 1
        assert rows[0].price == 5500

    async def test_get_listings_with_filter(self, repo: ListingRepository, async_session: AsyncSession):
        listings = [
            _make_listing(source_id="ta1", city="tel-aviv", price=5000, rooms=3),
            _make_listing(source_id="jm1", city="jerusalem", price=4000, rooms=2),
            _make_listing(source_id="ta2", city="tel-aviv", price=8000, rooms=4),
        ]
        await repo.upsert_listings(listings, ["f1", "f2", "f3"])
        await async_session.commit()

        # Filter by city
        f = SearchFilter(cities=["tel-aviv"])
        results = await repo.get_listings(search_filter=f)
        assert len(results) == 2
        assert all(r.city == "tel-aviv" for r in results)

    async def test_get_listings_price_range(self, repo: ListingRepository, async_session: AsyncSession):
        listings = [
            _make_listing(source_id="p1", price=3000),
            _make_listing(source_id="p2", price=5000),
            _make_listing(source_id="p3", price=8000),
        ]
        await repo.upsert_listings(listings, ["f1", "f2", "f3"])
        await async_session.commit()

        f = SearchFilter(min_price=4000, max_price=6000)
        results = await repo.get_listings(search_filter=f)
        assert len(results) == 1
        assert results[0].price == 5000

    async def test_get_new_since(self, repo: ListingRepository, async_session: AsyncSession):
        listings = [
            _make_listing(source_id="n1", price=5000),
            _make_listing(source_id="n2", price=6000),
        ]
        await repo.upsert_listings(listings, ["f1", "f2"])
        await async_session.commit()

        # All listings should be newer than yesterday
        since = datetime.utcnow() - timedelta(hours=1)
        results = await repo.get_new_since(since)
        assert len(results) == 2

        # None should be newer than tomorrow
        future = datetime.utcnow() + timedelta(hours=1)
        results = await repo.get_new_since(future)
        assert len(results) == 0

    async def test_mark_inactive(self, repo: ListingRepository, async_session: AsyncSession):
        listings = [
            _make_listing(source_id="m1"),
            _make_listing(source_id="m2"),
            _make_listing(source_id="m3"),
        ]
        await repo.upsert_listings(listings, ["f1", "f2", "f3"])
        await async_session.commit()

        # Only m1 is still active on the platform
        count = await repo.mark_inactive("yad2", {"m1"})
        await async_session.commit()

        assert count == 2

        active = await repo.get_listings(active_only=True)
        assert len(active) == 1
        assert active[0].source_id == "m1"

    async def test_feature_filter(self, repo: ListingRepository, async_session: AsyncSession):
        listings = [
            _make_listing(source_id="f1", has_parking=True, has_elevator=True),
            _make_listing(source_id="f2", has_parking=True, has_elevator=False),
            _make_listing(source_id="f3", has_parking=False, has_elevator=True),
        ]
        await repo.upsert_listings(listings, ["fp1", "fp2", "fp3"])
        await async_session.commit()

        f = SearchFilter(require_parking=True, require_elevator=True)
        results = await repo.get_listings(search_filter=f)
        assert len(results) == 1
        assert results[0].source_id == "f1"


class TestSearchProfileRepository:
    async def test_create_and_get_profiles(self, async_session: AsyncSession):
        repo = SearchProfileRepository(async_session)

        profile = await repo.create_profile(
            name="My Search",
            filter_json={"cities": ["tel-aviv"], "max_price": 6000},
            telegram_chat_id="12345",
        )
        await async_session.commit()

        assert profile.name == "My Search"
        assert profile.is_active is True

        profiles = await repo.get_active_profiles()
        assert len(profiles) == 1


class TestScrapeRunRepository:
    async def test_start_and_finish_run(self, async_session: AsyncSession):
        repo = ScrapeRunRepository(async_session)

        run = await repo.start_run(source="yad2", method="next_data")
        await async_session.commit()

        assert run.status == "running"
        assert run.started_at is not None

        await repo.finish_run(run.id, listings_found=50, listings_new=10)
        await async_session.commit()
