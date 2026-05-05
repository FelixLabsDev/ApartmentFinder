from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

FB_URL_PATTERNS = [
    # Standard desktop: facebook.com/marketplace/item/123456
    re.compile(r"https?://(?:www\.)?facebook\.com/marketplace/item/(\d+)"),
    # Mobile: m.facebook.com/marketplace/item/123456
    re.compile(r"https?://m\.facebook\.com/marketplace/item/(\d+)"),
    # Mobile share links: facebook.com/share/1KfvTaERYE/
    re.compile(r"https?://(?:www\.)?facebook\.com/share/[\w]+/?"),
    # Shortened: fb.com or fb.me links
    re.compile(r"https?://(?:www\.)?fb\.(?:com|me)/[\w/]+"),
]

PROFILE_DIR = "data/fb_profile"


@dataclass
class ScrapedPage:
    url: str
    listing_id: str
    title: str
    text_content: str
    image_urls: list[str]


def extract_fb_url(text: str) -> str | None:
    """Extract a Facebook URL from message text (marketplace, share, or shortened links)."""
    for pattern in FB_URL_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def extract_fb_listing_id(url: str) -> str:
    """Extract the listing ID from a Facebook Marketplace URL.

    For share/redirect URLs where the ID isn't in the URL, returns the
    share token as a fallback ID.
    """
    # Standard marketplace item ID
    match = re.search(r"/marketplace/item/(\d+)", url)
    if match:
        return match.group(1)
    # Share link token (e.g. /share/1KfvTaERYE/)
    match = re.search(r"/share/([\w]+)", url)
    if match:
        return f"share-{match.group(1)}"
    # Fallback: hash the URL
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:16]


async def scrape_fb_listing(url: str) -> ScrapedPage:
    """Scrape a single Facebook Marketplace listing page using Playwright.

    Uses the persistent browser profile at data/fb_profile/ to maintain
    a logged-in Facebook session.
    """
    return await asyncio.to_thread(_scrape_sync, url)


def _scrape_sync(url: str) -> ScrapedPage:
    """Sync Playwright scrape of a single FB listing page."""
    from playwright.sync_api import sync_playwright

    listing_id = extract_fb_listing_id(url)
    profile_path = str(Path(PROFILE_DIR).resolve())
    Path(profile_path).mkdir(parents=True, exist_ok=True)

    pw = sync_playwright().start()
    try:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=True,
            locale="he-IL",
            viewport={"width": 1280, "height": 800},
        )
        page = context.pages[0] if context.pages else context.new_page()

        logger.info("Scraping FB listing: %s", url)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # Share/short links redirect — extract real listing ID from final URL
        final_url = page.url
        logger.info("Final URL after redirect: %s", final_url)
        resolved_id = extract_fb_listing_id(final_url)
        if resolved_id != listing_id and not resolved_id.startswith("share-"):
            listing_id = resolved_id

        # Dismiss login modal if it appears
        try:
            close_btn = page.query_selector('[aria-label="Close"]')
            if close_btn:
                close_btn.click()
                page.wait_for_timeout(500)
        except Exception:
            pass

        # Extract title
        title = ""
        try:
            title_el = page.query_selector("h1") or page.query_selector('[data-testid="marketplace_pdp_component"] span')
            if title_el:
                title = title_el.inner_text().strip()
        except Exception:
            pass

        # Extract all visible text from the listing page
        text_content = ""
        try:
            # Get the main content area text
            body_text = page.inner_text("body")
            text_content = body_text[:8000]  # Cap to avoid excessive text
        except Exception:
            pass

        # Extract image URLs
        image_urls = []
        try:
            images = page.query_selector_all("img")
            for img in images:
                src = img.get_attribute("src") or ""
                if src and "scontent" in src and "marketplace" not in src.lower():
                    # Facebook CDN images for the listing
                    image_urls.append(src)
                elif src and ("fbcdn" in src or "scontent" in src):
                    image_urls.append(src)
            # Deduplicate while preserving order
            seen = set()
            unique_images = []
            for u in image_urls:
                if u not in seen:
                    seen.add(u)
                    unique_images.append(u)
            image_urls = unique_images[:10]  # Limit to 10 images
        except Exception:
            pass

        context.close()
    finally:
        pw.stop()

    return ScrapedPage(
        url=url,
        listing_id=listing_id,
        title=title,
        text_content=text_content,
        image_urls=image_urls,
    )
