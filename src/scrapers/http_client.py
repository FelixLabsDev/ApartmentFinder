from __future__ import annotations

import asyncio
import logging
import random

import httpx
from fake_useragent import UserAgent

from src.config import get_settings

logger = logging.getLogger(__name__)


class ScraperHttpClient:
    """Shared async HTTP client with anti-bot headers and retry logic."""

    def __init__(self, proxy_url: str | None = None):
        self._ua = UserAgent()
        self._proxy = proxy_url
        self._client: httpx.AsyncClient | None = None

    def _build_headers(self) -> dict[str, str]:
        """Full browser-like headers with randomized User-Agent."""
        return {
            "User-Agent": self._ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
            "Cache-Control": "max-age=0",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            settings = get_settings()
            transport = None
            if self._proxy:
                transport = httpx.AsyncHTTPTransport(proxy=self._proxy)
            self._client = httpx.AsyncClient(
                transport=transport,
                timeout=httpx.Timeout(settings.request_timeout),
                follow_redirects=True,
            )
        return self._client

    async def get(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        max_retries: int | None = None,
    ) -> httpx.Response:
        """GET with exponential backoff retry."""
        settings = get_settings()
        retries = max_retries if max_retries is not None else settings.max_retries
        request_headers = self._build_headers()
        if headers:
            request_headers.update(headers)

        client = await self._get_client()
        last_exc: Exception | None = None

        for attempt in range(retries):
            try:
                response = await client.get(url, params=params, headers=request_headers)
                logger.debug(
                    "GET %s → %d (final_url=%s, content-type=%s)",
                    url, response.status_code, response.url,
                    response.headers.get("content-type", "?"),
                )
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                wait = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    "GET %s attempt %d/%d failed: %s. Retrying in %.1fs",
                    url, attempt + 1, retries, exc, wait,
                )
                if attempt < retries - 1:
                    await asyncio.sleep(wait)

        raise last_exc  # type: ignore[misc]

    async def post(
        self,
        url: str,
        data: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
        cookies: dict[str, str] | None = None,
        max_retries: int | None = None,
    ) -> httpx.Response:
        """POST with exponential backoff retry."""
        settings = get_settings()
        retries = max_retries if max_retries is not None else settings.max_retries
        request_headers = self._build_headers()
        if headers:
            request_headers.update(headers)

        client = await self._get_client()
        last_exc: Exception | None = None

        for attempt in range(retries):
            try:
                response = await client.post(
                    url, data=data, json=json, headers=request_headers,
                    cookies=cookies,
                )
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                wait = (2**attempt) + random.uniform(0, 1)
                logger.warning(
                    "POST %s attempt %d/%d failed: %s. Retrying in %.1fs",
                    url, attempt + 1, retries, exc, wait,
                )
                if attempt < retries - 1:
                    await asyncio.sleep(wait)

        raise last_exc  # type: ignore[misc]

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def random_delay(self) -> None:
        """Sleep a random duration between configured min/max."""
        settings = get_settings()
        delay = random.uniform(settings.scrape_delay_min, settings.scrape_delay_max)
        await asyncio.sleep(delay)
