from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Database
    database_path: str = "data/apartmentfinder.db"

    # Scraping intervals (minutes)
    scrape_interval_minutes: int = 30
    yad2_interval_minutes: int = 30
    fb_interval_minutes: int = 60

    # HTTP settings
    request_timeout: int = 30
    max_retries: int = 3
    scrape_delay_min: float = 3.0
    scrape_delay_max: float = 10.0

    # Telegram notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_default_chat_id: str = ""

    # Facebook authentication (required for GraphQL scraping)
    # Paste your browser cookie string from a logged-in Facebook session
    fb_cookies: str = ""
    # LSD token extracted from Facebook page source
    fb_lsd_token: str = ""

    # Proxy (optional)
    proxy_url: str | None = None

    # AI extraction (LiteLLM)
    ai_model: str = "gpt-4o-mini"
    openai_api_key: str = ""

    # Debug mode
    debug: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def database_url(self) -> str:
        """SQLAlchemy async database URL."""
        return f"sqlite+aiosqlite:///{self.database_path}"

    @property
    def database_url_sync(self) -> str:
        """SQLAlchemy sync database URL (for Alembic migrations)."""
        return f"sqlite:///{self.database_path}"

    def ensure_data_dir(self) -> None:
        """Create the data directory if it doesn't exist."""
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

    def get_fb_cookies_dict(self) -> dict[str, str]:
        """Parse the fb_cookies string (browser Cookie header format) into a dict."""
        if not self.fb_cookies:
            return {}
        cookies: dict[str, str] = {}
        for pair in self.fb_cookies.split(";"):
            pair = pair.strip()
            if "=" in pair:
                key, _, value = pair.partition("=")
                cookies[key.strip()] = value.strip()
        return cookies


@lru_cache
def get_settings() -> Settings:
    return Settings()
