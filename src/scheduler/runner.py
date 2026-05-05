from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import get_settings

from .jobs import cleanup_job, scrape_job

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    Jobs:
    - scrape_job: runs every `scrape_interval_minutes` (default: 30 min)
    - cleanup_job: runs once daily
    """
    settings = get_settings()
    scheduler = AsyncIOScheduler()

    # Main scraping job
    scheduler.add_job(
        scrape_job,
        trigger=IntervalTrigger(minutes=settings.scrape_interval_minutes),
        id="scrape_job",
        name="Apartment scraping pipeline",
        replace_existing=True,
        max_instances=1,  # Don't overlap
    )

    # Daily cleanup
    scheduler.add_job(
        cleanup_job,
        trigger=IntervalTrigger(hours=24),
        id="cleanup_job",
        name="Daily cleanup",
        replace_existing=True,
    )

    logger.info(
        "Scheduler configured: scrape every %d min, cleanup every 24h",
        settings.scrape_interval_minutes,
    )

    return scheduler


async def run_scheduler() -> None:
    """Start the scheduler and run until interrupted."""
    import asyncio

    scheduler = create_scheduler()
    scheduler.start()

    logger.info("Scheduler started. Press Ctrl+C to stop.")

    try:
        # Run the first scrape immediately
        await scrape_job()

        # Keep running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Scheduler shutting down...")
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
