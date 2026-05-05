from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.config import get_settings
from src.db.engine import get_async_session
from src.db.repository import ListingRepository, ScrapeRunRepository, SearchProfileRepository
from src.models.filters import SearchFilter
from src.notifications.telegram_bot import TelegramNotifier
from src.pipeline.deduplicator import ListingDeduplicator
from src.pipeline.filter_engine import FilterEngine
from src.pipeline.pipeline import ScrapePipeline
from src.scrapers.orchestrator import ScraperOrchestrator
from src.scrapers.yad2.scraper import Yad2ApiScraper

logger = logging.getLogger(__name__)


async def scrape_job() -> None:
    """Main scraping job — called by the scheduler on each interval.

    1. Build orchestrator with registered scrapers
    2. Run pipeline for each active search profile
    3. Store results in DB
    4. Notify via Telegram for new listings
    """
    settings = get_settings()
    logger.info("=== Scrape job started ===")

    # Build orchestrator
    orchestrator = ScraperOrchestrator()
    orchestrator.register("yad2", [Yad2ApiScraper()])

    # Facebook scrapers require auth — register only if configured
    try:
        from src.scrapers.facebook.scraper import FacebookGraphQLScraper
        orchestrator.register("facebook", [FacebookGraphQLScraper()])
    except Exception:
        logger.warning("Facebook scraper not available, skipping")

    pipeline = ScrapePipeline(orchestrator)
    notifier = TelegramNotifier()

    async with get_async_session() as session:
        listing_repo = ListingRepository(session)
        profile_repo = SearchProfileRepository(session)
        run_repo = ScrapeRunRepository(session)

        # Get active search profiles
        profiles = await profile_repo.get_active_profiles()
        if not profiles:
            logger.info("No active search profiles, using default filter")
            profiles = [None]  # Will use default empty filter

        for profile in profiles:
            if profile:
                search_filter = SearchFilter.model_validate_json(profile.filter_json)
                profile_name = profile.name
                chat_id = profile.telegram_chat_id
            else:
                search_filter = SearchFilter()
                profile_name = "default"
                chat_id = settings.telegram_chat_id

            # Record scrape run
            run = await run_repo.start_run(source="all", method="pipeline")

            try:
                result = await pipeline.run(search_filter)

                if result.listings:
                    # Compute fingerprints and upsert
                    dedup = ListingDeduplicator()
                    fingerprints = [dedup.compute_fingerprint(l) for l in result.listings]
                    total, new_count = await listing_repo.upsert_listings(
                        result.listings, fingerprints
                    )

                    logger.info(
                        "Profile '%s': stored %d listings (%d new)",
                        profile_name, total, new_count,
                    )

                    # Notify about new listings
                    if new_count > 0 and chat_id:
                        # Get listings added since last notification
                        new_listings = result.listings[:new_count]  # Approximate
                        await notifier.send_listings(
                            chat_id=chat_id,
                            listings=new_listings,
                            header=f"New listings for '{profile_name}'",
                        )

                    await run_repo.finish_run(
                        run.id,
                        listings_found=result.total_scraped,
                        listings_new=new_count,
                        status="success",
                    )
                else:
                    await run_repo.finish_run(
                        run.id,
                        listings_found=0,
                        listings_new=0,
                        status="success",
                    )

            except Exception as exc:
                logger.exception("Scrape job failed for profile '%s'", profile_name)
                await run_repo.finish_run(
                    run.id,
                    listings_found=0,
                    listings_new=0,
                    status="error",
                    error_message=str(exc),
                )

        await session.commit()

    logger.info("=== Scrape job finished ===")


async def cleanup_job() -> None:
    """Daily cleanup: mark old listings as inactive."""
    logger.info("Running cleanup job")
    # Placeholder for future cleanup logic
    # e.g., mark listings older than 30 days as inactive
    pass
