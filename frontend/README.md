# ApartmentFinder — Frontend

A React dashboard for browsing, filtering, organizing, and comparing apartment listings scraped from multiple sources (Yad2, Facebook Marketplace, Telegram).

Requires the ApartmentFinder backend API to be running.

---

## Quick Start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The backend API must be running on port 8080 (or as configured in `src/api.ts`).

---

## Build for Production

```bash
npm run build    # outputs to dist/
npm run preview  # serve the built output locally
```

---

## Advanced Usage

### Linting

```bash
npm run lint
```

### Environment / API URL

The backend base URL is set in `src/api.ts`. Change the `BASE_URL` constant there if your API runs on a different host or port.

### Adding a New City for Scraping

1. Open the app and click the gear icon in the sidebar header.
2. Go to the Cities section in Settings.
3. Add a city with a name and Yad2 URL fragment. The scraper will use this on the next run.

---

## Features

### Listings

- **Grid view** — listing cards with image carousel, price, rooms, area, floor, features, and freshness badge.
- **Map view** — Leaflet map showing pins for all currently displayed listings.
- **Pagination** — "Load More" button (50 listings per page) in grid mode.
- **Auto-refresh** — manual Refresh button; new-listing polling every 60 seconds with browser notification support.
- **Unseen counter** — tracks which listings have been opened; shows a count of unseen listings in the toolbar.

### Filtering & Sorting

- Filter by price range, rooms, city, area, floor, property type, source, features (parking, elevator, balcony, etc.).
- Sort by newest, price, rooms, area, price-per-m².
- "Liked only" toggle.
- "Hide disliked" toggle (on by default).

### Ratings

- Like or dislike any listing. Liked listings are sorted to the top; disliked listings are hidden (configurable).
- Ratings persist in `localStorage`.

### Folders

- Create named folders and add listings to them from the card or detail modal.
- **All Listings** — no folder filter (default).
- **Uncategorized** — virtual folder that shows only listings not present in any user-created folder. Useful for finding unreviewed listings.
- User folders — filter the main grid to show only listings in that folder.
- Folder contents view — drill into a folder to see, select, and bulk-remove its listings.
- Telegram-sourced listings are automatically added to a "Telegram" folder on load.

### Compare

- When two or more listings are liked, a "Compare (N)" button appears. Opens a side-by-side comparison view.

### Notes

- Add freeform text notes to any listing. Note count is shown on the card and in the detail modal. Notes persist in `localStorage`.

### Saved Searches

- Save the current filter configuration as a named profile.
- Reload any saved profile with one click.
- Delete profiles you no longer need.

### Scraping

- Trigger Yad2 and Facebook Marketplace scrapes from the Scrape tab.
- Configure per-city scrape targets in Settings.

### Settings

- Manage city scrape configurations (Yad2).
- Manage Facebook city scrape configurations.
- Clear all listing data from the database.

### Telegram Bot

- Telegram bot status and configuration shown in the sidebar footer via `TelegramBotPanel`.
