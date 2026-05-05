from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from src.models.filters import SearchFilter
from src.models.listing import ListingCreate
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Result of a single scraper run."""
    source: str
    method: str
    listings: list[ListingCreate] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0


class ScraperOrchestrator:
    """Run multiple scrapers with fallback chains per source.

    Each source (yad2, facebook) can have multiple scraper implementations.
    The orchestrator tries them in priority order and uses the first one
    that succeeds.
    """

    def __init__(self):
        self._chains: dict[str, list[BaseScraper]] = {}

    def register(self, source: str, scrapers: list[BaseScraper]) -> None:
        """Register a fallback chain for a source.

        Scrapers are tried in list order.  The first one that returns results
        (or doesn't raise) wins.
        """
        self._chains[source] = scrapers

    async def scrape_all(self, search_filter: SearchFilter) -> list[ScrapeResult]:
        """Run all registered scraper chains and return results."""
        results: list[ScrapeResult] = []

        for source, scrapers in self._chains.items():
            result = await self._run_chain(source, scrapers, search_filter)
            results.append(result)

        return results

    async def _run_chain(
        self,
        source: str,
        scrapers: list[BaseScraper],
        search_filter: SearchFilter,
    ) -> ScrapeResult:
        """Try each scraper in the chain until one succeeds."""
        last_error: str | None = None

        for scraper in scrapers:
            method = scraper.method_name
            start = time.monotonic()

            try:
                logger.info("Trying %s/%s scraper...", source, method)
                listings = await scraper.scrape(search_filter)
                duration = time.monotonic() - start

                if listings:
                    logger.info(
                        "%s/%s: got %d listings in %.1fs",
                        source, method, len(listings), duration,
                    )
                    return ScrapeResult(
                        source=source,
                        method=method,
                        listings=listings,
                        duration_seconds=duration,
                    )
                else:
                    logger.info("%s/%s: returned 0 listings in %.1fs", source, method, duration)
                    last_error = f"{method}: returned 0 listings"

            except Exception as exc:
                duration = time.monotonic() - start
                logger.error(
                    "%s/%s scraper failed after %.1fs: %s",
                    source, method, duration, exc,
                )
                last_error = f"{method}: {exc}"

        return ScrapeResult(source=source, method="none", error=last_error)

    async def health_check_all(self) -> dict[str, bool]:
        """Run health checks on the primary scraper of each chain."""
        results: dict[str, bool] = {}
        for source, scrapers in self._chains.items():
            if scrapers:
                try:
                    results[source] = await scrapers[0].health_check()
                except Exception:
                    results[source] = False
            else:
                results[source] = False
        return results
