from __future__ import annotations

from abc import ABC, abstractmethod

from src.models.filters import SearchFilter
from src.models.listing import ListingCreate


class BaseScraper(ABC):
    """Protocol that all scrapers must implement."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return 'yad2' or 'facebook'."""

    @property
    @abstractmethod
    def method_name(self) -> str:
        """Return the scraping method name (e.g. 'next_data', 'graphql', 'playwright')."""

    @abstractmethod
    async def scrape(self, search_filter: SearchFilter) -> list[ListingCreate]:
        """Fetch listings matching filter. Returns normalized ListingCreate objects."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Quick connectivity check. Returns True if source is reachable."""
