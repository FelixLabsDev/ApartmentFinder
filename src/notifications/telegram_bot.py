from __future__ import annotations

import asyncio
import logging

from src.config import get_settings
from src.models.listing import ListingCreate

from .formatter import TelegramFormatter

logger = logging.getLogger(__name__)

# Max listings per Telegram message to avoid hitting character limits
LISTINGS_PER_MESSAGE = 3

# Rate limit: 1 message per second per chat (Telegram's limit is ~30/sec globally)
MESSAGE_DELAY_SECONDS = 1.0


class TelegramNotifier:
    """Send apartment listing notifications via Telegram bot."""

    def __init__(self, bot_token: str | None = None, formatter: TelegramFormatter | None = None):
        self._token = bot_token or get_settings().telegram_bot_token
        self._formatter = formatter or TelegramFormatter()
        self._bot = None

    async def _get_bot(self):
        """Lazy-init the telegram Bot."""
        if self._bot is None:
            try:
                from telegram import Bot
                self._bot = Bot(token=self._token)
            except ImportError:
                raise ImportError(
                    "python-telegram-bot not installed. "
                    "Run: uv add python-telegram-bot"
                )
        return self._bot

    async def send_listings(
        self,
        chat_id: str | int,
        listings: list[ListingCreate],
        header: str | None = None,
    ) -> int:
        """Send listings to a Telegram chat in batches.

        Returns the number of messages sent.
        """
        if not listings:
            return 0

        if not self._token:
            logger.warning("Telegram bot token not configured — skipping notification")
            return 0

        bot = await self._get_bot()
        messages_sent = 0

        # Send in batches of LISTINGS_PER_MESSAGE
        for i in range(0, len(listings), LISTINGS_PER_MESSAGE):
            batch = listings[i:i + LISTINGS_PER_MESSAGE]
            batch_header = header if i == 0 else None
            text = self._formatter.format_batch(batch, header=batch_header)

            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                messages_sent += 1
            except Exception as exc:
                logger.error("Failed to send Telegram message to %s: %s", chat_id, exc)

            # Rate limiting
            if i + LISTINGS_PER_MESSAGE < len(listings):
                await asyncio.sleep(MESSAGE_DELAY_SECONDS)

        logger.info("Sent %d Telegram messages to %s (%d listings)", messages_sent, chat_id, len(listings))
        return messages_sent

    async def send_summary(self, chat_id: str | int, total_new: int, total_sources: int) -> None:
        """Send a summary message about the scan results."""
        if not self._token:
            return

        text = self._formatter.format_summary(total_new, total_sources)
        bot = await self._get_bot()

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.error("Failed to send summary to %s: %s", chat_id, exc)

    async def test_connection(self, chat_id: str | int) -> bool:
        """Send a test message to verify the bot is configured correctly."""
        if not self._token:
            logger.error("No Telegram bot token configured")
            return False

        try:
            bot = await self._get_bot()
            await bot.send_message(
                chat_id=chat_id,
                text="ApartmentFinder bot is connected and working!",
            )
            return True
        except Exception as exc:
            logger.error("Telegram test failed: %s", exc)
            return False
