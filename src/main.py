"""ApartmentFinder CLI — scrape, search, and manage apartment listings."""
from __future__ import annotations

import asyncio
import logging
import sys
from typing import Optional

import typer

app = typer.Typer(
    name="apartmentfinder",
    help="Scrape apartment listings from Yad2, Facebook Marketplace, and Madlan.",
)


def _setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


# ---------------------------------------------------------------------------
# scrape command
# ---------------------------------------------------------------------------

@app.command()
def scrape(
    source: str = typer.Option("all", help="Source to scrape: yad2, facebook, madlan, or all"),
    city: Optional[str] = typer.Option(None, help="City to search (e.g., tel-aviv)"),
    min_price: Optional[int] = typer.Option(None, help="Minimum price (ILS)"),
    max_price: Optional[int] = typer.Option(None, help="Maximum price (ILS)"),
    min_rooms: Optional[float] = typer.Option(None, help="Minimum rooms"),
    max_rooms: Optional[float] = typer.Option(None, help="Maximum rooms"),
    debug: bool = typer.Option(False, help="Enable debug logging"),
) -> None:
    """Scrape apartment listings from one or all sources."""
    _setup_logging(debug)
    asyncio.run(_scrape_async(source, city, min_price, max_price, min_rooms, max_rooms))


async def _scrape_async(
    source: str,
    city: str | None,
    min_price: int | None,
    max_price: int | None,
    min_rooms: float | None,
    max_rooms: float | None,
) -> None:
    from src.models.filters import SearchFilter
    from src.pipeline.pipeline import ScrapePipeline
    from src.scrapers.orchestrator import ScraperOrchestrator

    search_filter = SearchFilter(
        cities=[city] if city else [],
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
    )

    orchestrator = ScraperOrchestrator()

    if source in ("yad2", "all"):
        from src.scrapers.yad2.scraper import Yad2ApiScraper
        orchestrator.register("yad2", [Yad2ApiScraper()])

    if source in ("facebook", "all"):
        from src.scrapers.facebook.scraper import FacebookGraphQLScraper
        orchestrator.register("facebook", [FacebookGraphQLScraper()])

    if source in ("madlan", "all"):
        from src.scrapers.madlan.scraper import MadlanPlaywrightScraper
        orchestrator.register("madlan", [MadlanPlaywrightScraper()])

    pipeline = ScrapePipeline(orchestrator)
    result = await pipeline.run(search_filter)

    typer.echo(f"\nScraped {result.total_scraped} listings total")
    typer.echo(f"After dedup: {result.total_after_dedup}")
    typer.echo(f"After filter: {result.total_after_filter}")

    if result.listings:
        typer.echo(f"\nTop results:")
        for listing in result.listings[:10]:
            price_str = f"{listing.price:,.0f} {listing.currency}" if listing.price else "N/A"
            rooms_str = f"{listing.rooms}r" if listing.rooms else ""
            typer.echo(
                f"  [{listing.source}] {listing.city} | {rooms_str} | {price_str} | "
                f"{listing.street or 'N/A'}"
            )

    # Store results in DB
    if result.listings:
        from src.config import get_settings
        from src.db.engine import get_async_session
        from src.db.repository import ListingRepository
        from src.pipeline.deduplicator import ListingDeduplicator

        get_settings().ensure_data_dir()

        # Create tables if they don't exist
        from src.db.engine import get_async_engine
        from src.db.tables import Base
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        dedup = ListingDeduplicator()
        fingerprints = [dedup.compute_fingerprint(l) for l in result.listings]

        async with get_async_session() as session:
            repo = ListingRepository(session)
            total, new_count = await repo.upsert_listings(result.listings, fingerprints)
            await session.commit()
            typer.echo(f"\nStored: {total} total, {new_count} new")


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------

@app.command(name="list")
def list_listings(
    city: Optional[str] = typer.Option(None, help="Filter by city"),
    min_price: Optional[int] = typer.Option(None, help="Minimum price"),
    max_price: Optional[int] = typer.Option(None, help="Maximum price"),
    min_rooms: Optional[float] = typer.Option(None, help="Minimum rooms"),
    max_rooms: Optional[float] = typer.Option(None, help="Maximum rooms"),
    limit: int = typer.Option(20, help="Max results to show"),
    debug: bool = typer.Option(False, help="Enable debug logging"),
) -> None:
    """List stored listings from the database."""
    _setup_logging(debug)
    asyncio.run(_list_async(city, min_price, max_price, min_rooms, max_rooms, limit))


async def _list_async(
    city: str | None,
    min_price: int | None,
    max_price: int | None,
    min_rooms: float | None,
    max_rooms: float | None,
    limit: int,
) -> None:
    from src.config import get_settings
    from src.db.engine import get_async_session
    from src.db.repository import ListingRepository
    from src.models.filters import SearchFilter

    get_settings().ensure_data_dir()

    search_filter = SearchFilter(
        cities=[city] if city else [],
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
    )

    async with get_async_session() as session:
        repo = ListingRepository(session)
        listings = await repo.get_listings(search_filter, limit=limit)

    if not listings:
        typer.echo("No listings found matching your criteria.")
        return

    typer.echo(f"Found {len(listings)} listings:\n")
    for listing in listings:
        price_str = f"{listing.price:,.0f} ILS" if listing.price else "N/A"
        rooms_str = f"{listing.rooms}r" if listing.rooms else ""
        typer.echo(
            f"  [{listing.source}] {listing.city} | {rooms_str} | {price_str} | "
            f"{listing.street or 'N/A'} | {listing.source_url}"
        )


# ---------------------------------------------------------------------------
# run-scheduler command
# ---------------------------------------------------------------------------

@app.command()
def run_scheduler(
    debug: bool = typer.Option(False, help="Enable debug logging"),
) -> None:
    """Start the background scheduler for periodic scraping."""
    _setup_logging(debug)
    from src.scheduler.runner import run_scheduler as _run
    asyncio.run(_run())


# ---------------------------------------------------------------------------
# add-search command
# ---------------------------------------------------------------------------

@app.command()
def add_search(
    name: str = typer.Option(..., help="Profile name"),
    city: Optional[str] = typer.Option(None, help="City filter"),
    max_price: Optional[int] = typer.Option(None, help="Maximum price"),
    min_rooms: Optional[float] = typer.Option(None, help="Minimum rooms"),
    max_rooms: Optional[float] = typer.Option(None, help="Maximum rooms"),
    telegram_chat_id: Optional[str] = typer.Option(None, help="Telegram chat ID for notifications"),
    debug: bool = typer.Option(False, help="Enable debug logging"),
) -> None:
    """Create a search profile for scheduled scraping."""
    _setup_logging(debug)
    asyncio.run(_add_search_async(name, city, max_price, min_rooms, max_rooms, telegram_chat_id))


async def _add_search_async(
    name: str,
    city: str | None,
    max_price: int | None,
    min_rooms: float | None,
    max_rooms: float | None,
    telegram_chat_id: str | None,
) -> None:
    from src.config import get_settings
    from src.db.engine import get_async_engine, get_async_session
    from src.db.repository import SearchProfileRepository
    from src.db.tables import Base
    from src.models.filters import SearchFilter

    get_settings().ensure_data_dir()

    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    search_filter = SearchFilter(
        cities=[city] if city else [],
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
    )

    async with get_async_session() as session:
        repo = SearchProfileRepository(session)
        profile = await repo.create_profile(
            name=name,
            filter_json=search_filter.model_dump_json(),
            telegram_chat_id=telegram_chat_id or "",
        )
        await session.commit()
        typer.echo(f"Created search profile '{name}' (ID: {profile.id})")


# ---------------------------------------------------------------------------
# test-telegram command
# ---------------------------------------------------------------------------

@app.command()
def test_telegram(
    chat_id: Optional[str] = typer.Option(None, help="Chat ID (uses default from .env if not given)"),
    debug: bool = typer.Option(False, help="Enable debug logging"),
) -> None:
    """Send a test message to verify Telegram bot setup."""
    _setup_logging(debug)
    asyncio.run(_test_telegram_async(chat_id))


async def _test_telegram_async(chat_id: str | None) -> None:
    from src.config import get_settings
    from src.notifications.telegram_bot import TelegramNotifier

    settings = get_settings()
    target = chat_id or settings.telegram_chat_id or settings.telegram_default_chat_id

    if not target:
        typer.echo("Error: No chat ID provided and none configured in .env")
        raise typer.Exit(1)

    notifier = TelegramNotifier()
    ok = await notifier.test_connection(target)

    if ok:
        typer.echo("Telegram bot is working! Check your chat.")
    else:
        typer.echo("Failed to send test message. Check your bot token and chat ID.")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# health command
# ---------------------------------------------------------------------------

@app.command()
def health(
    debug: bool = typer.Option(False, help="Enable debug logging"),
) -> None:
    """Check connectivity to all scraping sources."""
    _setup_logging(debug)
    asyncio.run(_health_async())


async def _health_async() -> None:
    from src.scrapers.orchestrator import ScraperOrchestrator
    from src.scrapers.yad2.scraper import Yad2ApiScraper
    from src.scrapers.facebook.scraper import FacebookGraphQLScraper
    from src.scrapers.madlan.scraper import MadlanPlaywrightScraper

    orchestrator = ScraperOrchestrator()
    orchestrator.register("yad2", [Yad2ApiScraper()])
    orchestrator.register("facebook", [FacebookGraphQLScraper()])
    orchestrator.register("madlan", [MadlanPlaywrightScraper()])

    results = await orchestrator.health_check_all()

    for source, healthy in results.items():
        status = "OK" if healthy else "FAIL"
        typer.echo(f"  {source}: {status}")


# ---------------------------------------------------------------------------
# telegram-bot command
# ---------------------------------------------------------------------------

@app.command(name="telegram-bot")
def telegram_bot(
    debug: bool = typer.Option(False, help="Enable debug logging"),
) -> None:
    """Start the Telegram bot listener for receiving Facebook Marketplace links."""
    _setup_logging(debug)
    asyncio.run(_telegram_bot_async())


async def _telegram_bot_async() -> None:
    from src.config import get_settings
    from src.db.engine import get_async_engine
    from src.db.tables import Base

    settings = get_settings()
    settings.ensure_data_dir()

    # Ensure tables exist
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from src.telegram_bot.bot import run_bot
    await run_bot()


if __name__ == "__main__":
    app()
