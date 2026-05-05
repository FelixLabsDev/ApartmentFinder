from __future__ import annotations

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.ai.extractor import REQUIRED_FIELDS, extract_listing_fields
from src.config import get_settings
from src.db.engine import get_async_session
from src.db.repository import ListingRepository
from src.models.enums import Currency, PropertyType, Source
from src.models.listing import ListingCreate
from src.pipeline.deduplicator import ListingDeduplicator
from src.pipeline.normalizer import ListingNormalizer
from src.scrapers.telegram_links.scraper import extract_fb_url, scrape_fb_listing

logger = logging.getLogger(__name__)

_normalizer = ListingNormalizer()
_deduplicator = ListingDeduplicator()


async def _start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "Welcome to ApartmentFinder Bot!\n\n"
        "Send me a Facebook Marketplace apartment listing link and I'll:\n"
        "1. Scrape the listing details\n"
        "2. Use AI to extract structured information\n"
        "3. Add it to your apartment database\n\n"
        "Just paste the link and I'll handle the rest!"
    )


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages — detect FB Marketplace links and process them."""
    if not update.message or not update.message.text:
        return

    text = update.message.text
    url = extract_fb_url(text)

    if not url:
        await update.message.reply_text(
            "I didn't find a Facebook Marketplace link in your message.\n"
            "Please send a link like: https://www.facebook.com/marketplace/item/123456789"
        )
        return

    await _process_listing_link(update, url)


async def _process_listing_link(update: Update, url: str) -> None:
    """Scrape, extract, and store a listing from a Facebook Marketplace link."""
    status_msg = await update.message.reply_text("Processing link... Scraping the listing page.")

    # Step 1: Scrape the page
    try:
        scraped = await scrape_fb_listing(url)
    except Exception as exc:
        logger.error("Failed to scrape %s: %s", url, exc)
        await status_msg.edit_text(f"Failed to scrape the listing: {exc}")
        return

    if not scraped.text_content.strip():
        await status_msg.edit_text("Could not extract any text from the listing page. The page may require login.")
        return

    await status_msg.edit_text("Scraping complete. Running AI extraction...")

    # Step 2: AI extraction
    try:
        result = await extract_listing_fields(scraped.text_content, title=scraped.title)
    except Exception as exc:
        logger.error("AI extraction failed for %s: %s", url, exc)
        await status_msg.edit_text(f"AI extraction failed: {exc}")
        return

    fields = result.extracted_fields

    # Step 3: Build ListingCreate
    # Determine which fields the AI successfully extracted
    ai_guessed = result.guessed_fields

    # Parse property type
    prop_type = None
    if fields.get("property_type"):
        try:
            prop_type = PropertyType(fields["property_type"])
        except ValueError:
            prop_type = PropertyType.OTHER

    # Parse currency
    currency = Currency.ILS
    if fields.get("currency") == "USD":
        currency = Currency.USD

    # Parse entry date
    entry_date = None
    if fields.get("entry_date"):
        try:
            from datetime import date
            entry_date = date.fromisoformat(fields["entry_date"])
        except (ValueError, TypeError):
            pass

    listing = ListingCreate(
        source=Source.TELEGRAM,
        source_id=scraped.listing_id,
        source_url=url,
        title=scraped.title or fields.get("description", "")[:100] or "Facebook Listing",
        price=fields.get("price"),
        currency=currency,
        city=fields.get("city") or "unknown",
        neighborhood=fields.get("neighborhood"),
        street=fields.get("street"),
        house_number=fields.get("house_number"),
        rooms=fields.get("rooms"),
        floor=fields.get("floor"),
        total_floors=fields.get("total_floors"),
        area_sqm=fields.get("area_sqm"),
        description=fields.get("description"),
        image_urls=scraped.image_urls,
        property_type=prop_type,
        has_parking=fields.get("has_parking"),
        has_elevator=fields.get("has_elevator"),
        has_balcony=fields.get("has_balcony"),
        has_air_conditioning=fields.get("has_air_conditioning"),
        has_mamad=fields.get("has_mamad"),
        is_accessible=fields.get("is_accessible"),
        is_furnished=fields.get("is_furnished"),
        has_bars=fields.get("has_bars"),
        has_storage=fields.get("has_storage"),
        pet_friendly=fields.get("pet_friendly"),
        contact_name=fields.get("contact_name"),
        contact_phone=fields.get("contact_phone"),
        entry_date=entry_date,
        posted_at=datetime.utcnow(),
        ai_guessed_fields=ai_guessed,
    )

    # Step 4: Normalize and store
    normalized = _normalizer.normalize_batch([listing])
    listing = normalized[0] if normalized else listing

    fingerprint = _deduplicator.compute_fingerprint(listing)

    try:
        async with get_async_session() as session:
            repo = ListingRepository(session)
            total, new_count = await repo.upsert_listings([listing], [fingerprint])
            await session.commit()
    except Exception as exc:
        logger.error("Failed to store listing: %s", exc)
        await status_msg.edit_text(f"Failed to save listing to database: {exc}")
        return

    # Step 5: Reply with summary
    summary_lines = ["Listing processed and saved!"]
    summary_lines.append("")

    if listing.price:
        summary_lines.append(f"Price: {listing.price:,.0f} {listing.currency}")
    if listing.rooms:
        summary_lines.append(f"Rooms: {listing.rooms}")
    if listing.city and listing.city != "unknown":
        summary_lines.append(f"City: {listing.city}")
    if listing.area_sqm:
        summary_lines.append(f"Area: {listing.area_sqm} m²")
    if listing.street:
        summary_lines.append(f"Street: {listing.street}")
    if listing.floor is not None:
        summary_lines.append(f"Floor: {listing.floor}")

    if result.missing_required:
        summary_lines.append("")
        summary_lines.append(f"Missing fields: {', '.join(result.missing_required)}")

    status = "new" if new_count > 0 else "updated"
    summary_lines.append(f"\nStatus: {status}")

    await status_msg.edit_text("\n".join(summary_lines))


def build_bot_application(token: str | None = None) -> Application:
    """Build and configure the Telegram bot Application."""
    bot_token = token or get_settings().telegram_bot_token
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not configured in .env")

    app = Application.builder().token(bot_token).build()
    app.add_handler(CommandHandler("start", _start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

    return app


async def run_bot(token: str | None = None) -> None:
    """Run the Telegram bot with long-polling (blocking)."""
    app = build_bot_application(token)
    logger.info("Starting Telegram bot (long-polling)...")
    await app.initialize()
    # Clear any existing webhook/polling connections before starting
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Keep running until stopped
    import asyncio
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
