# ApartmentFinder

Aggregates apartment rental listings from **Yad2**, **Facebook Marketplace**, and **Madlan.co.il** with filtering, deduplication, 5-tier quality ratings, custom listing tags, priority sorting, WhatsApp messaging per listing, and Telegram notifications.

> For detailed architecture and design decisions, see [ARCHITECTURE.md](ARCHITECTURE.md).
> For the full development history, see [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md).

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for the React frontend)

## Setup

```bash
# Install Python dependencies
uv sync --dev

# Copy env file and configure
cp .env.example .env

# Run database migrations
uv run alembic upgrade head

# Install Playwright for Facebook browser scraping
uv run playwright install chromium

# Install frontend dependencies
cd frontend && npm install && cd ..
```

## Running

### API Backend + React Frontend

```bash
# Terminal 1 — Start the API server (0.0.0.0 makes it reachable on the LAN)
uv run uvicorn src.ui.api:app --reload --port 8080 --host 0.0.0.0

# Terminal 2 — Start the React dev server (also exposed on LAN via vite.config.ts)
cd frontend && npm run dev
```

- **React UI**: http://localhost:3000 (or http://\<your-lan-ip\>:3000 from phone)
- **API docs (Swagger)**: http://localhost:8080/docs
- **API stats**: http://localhost:8080/api/stats

### Facebook Marketplace Setup

Facebook requires a one-time login to save your session:

1. Open the React UI at http://localhost:3000
2. In the sidebar, switch to the **Facebook** tab
3. Check **"Open browser for login"** (checked by default)
4. Click **"Scrape Facebook"** — a Chrome window opens
5. Log in to Facebook in that window — scraping starts automatically
6. Your session is saved to `data/fb_profile/` for future runs

After the first login, you can uncheck "Open browser for login" to scrape headless using the saved session.

### CLI

```bash
# Scrape Yad2 listings for Tel Aviv under 7000 ILS
uv run python -m src.main scrape --source yad2 --city tel-aviv --max-price 7000

# Scrape Madlan listings for Tel Aviv under 7000 ILS
uv run python -m src.main scrape --source madlan --city tel-aviv --max-price 7000

# List stored listings
uv run python -m src.main list --city tel-aviv --max-price 6000

# Check source connectivity
uv run python -m src.main health

# Create a saved search profile
uv run python -m src.main add-search --name "TLV Budget" --city tel-aviv --max-price 5000

# Start the background scheduler (scrapes periodically)
uv run python -m src.main run-scheduler
```

### WhatsApp Integration (Optional)

Attach a WhatsApp number to any listing and chat directly from the detail modal via [Green API](https://green-api.com/):

1. Sign up at green-api.com and get your Instance ID and token
2. Add to `.env`:
   ```
   GREEN_API_INSTANCE_ID=your_instance_id
   GREEN_API_TOKEN=your_token
   ```
3. Open any listing detail modal, click the chat-bubble button, enter a phone number (with country code, e.g. `972501234567`), and start messaging

### Telegram Notifications

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
3. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```
4. Test: `uv run python -m src.main test-telegram`

## Tests

```bash
# Run all unit tests (194 tests)
uv run pytest tests/ -m "not integration" -v

# Run only Facebook parser tests
uv run pytest tests/test_fb_parser.py -v

# Run only Madlan parser tests
uv run pytest tests/test_madlan_parser.py -v

# Run with integration tests (hits real APIs)
uv run pytest tests/ -v
```

## Project Structure

```
src/
  config.py              # Settings from .env
  main.py                # Typer CLI (7 commands)
  models/                # Pydantic models (listing, filters, enums)
  db/                    # SQLAlchemy tables, repository, async engine
  scrapers/
    base.py              # Abstract scraper interface
    http_client.py       # Shared HTTP client with retry/anti-bot
    orchestrator.py      # Multi-source scraper with fallback chains
    yad2/                # Yad2 API scraper + parser
    facebook/            # Facebook GraphQL + Playwright scrapers
    madlan/              # Madlan Playwright scraper + parser (XHR intercept + DOM fallback)
  pipeline/
    normalizer.py        # Hebrew city names, USD→ILS, phone normalization
    deduplicator.py      # SHA256 fingerprint cross-source dedup
    filter_engine.py     # In-memory filter application
    pipeline.py          # End-to-end: scrape → normalize → AI enrich → dedup → filter
  notifications/         # Telegram formatter + notifier
  scheduler/             # APScheduler jobs + runner
  ui/api.py              # FastAPI backend (12 endpoints incl. tags)
  hooks/useListingTags.ts  # Tag state management hook
  # Priority sort panel (liked-first + tag priority ordering) is in App.tsx
frontend/                # React + TypeScript + Vite
data/
  apartmentfinder.db     # SQLite database (git-ignored)
  fb_profile/            # Facebook browser session (git-ignored)
  madlan_profile/        # Madlan browser session (git-ignored)
```

