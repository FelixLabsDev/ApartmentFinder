# Architecture

## Overview

ApartmentFinder Frontend is a single-page React application that displays, filters, organizes, and compares apartment listings fetched from a backend API. It is built with React 19, TypeScript, and Vite. All state that needs to persist across page reloads (ratings, folders, notes, city configs) is stored in `localStorage`.

---

## Technology Stack

| Concern | Choice | Rationale |
|---|---|---|
| UI framework | React 19 | Concurrent features, latest hooks behavior |
| Language | TypeScript 5.9 | Type safety across API contracts and component props |
| Build tool | Vite 7 | Fast HMR, ES module output |
| Server state | TanStack Query v5 | Caching, background refetch, query invalidation |
| HTTP client | Axios | Used inside `api.ts` for all backend calls |
| Maps | Leaflet + react-leaflet | Embedded map view for geolocated listings |
| Linting | ESLint 9 + typescript-eslint | Enforced via `npm run lint` |

---

## Directory Structure

```
frontend/
  src/
    App.tsx               # Root dashboard component; orchestrates all state and layout
    App.css               # Global styles for the dashboard layout
    api.ts                # All backend API calls (fetchListings, fetchListingsByKeys, etc.)
    main.tsx              # React entry point; mounts App inside QueryClientProvider
    index.css             # Base/reset CSS
    components/
      CompareView.tsx     # Side-by-side comparison modal for liked listings
      DisplayFilters.tsx  # Filter panel (price, rooms, city, etc.)
      FoldersPanel.tsx    # Folder management tab in the sidebar
      ListingCard.tsx     # Individual listing card (grid view)
      ListingDetailModal.tsx  # Full-detail modal when a listing is clicked
      MapView.tsx         # Leaflet map showing listing pins
      MultiSelect.tsx     # Reusable multi-select dropdown
      ScrapePanel.tsx     # Controls for triggering scrape jobs
      SearchProfiles.tsx  # Save/load named filter configurations
      SettingsModal.tsx   # City/Facebook city config and data management
      Sidebar.tsx         # Tab-based sidebar shell (Scrape, Filters, Folders, Saved)
      StatsBar.tsx        # Summary statistics bar above the listing grid
      TelegramBotPanel.tsx # Telegram bot status/config display
    hooks/
      useCitySettings.ts  # localStorage CRUD for city scrape configurations
      useFacebookCities.ts # localStorage CRUD for Facebook city configurations
      useFolders.ts       # localStorage CRUD for listing folders
      useListingNotes.ts  # localStorage CRUD for per-listing notes
      useListingRatings.ts # localStorage CRUD for liked/disliked ratings
      useNewListings.ts   # Polls the API every 60s for new listings; shows badge + browser notification
    assets/               # Static assets (images, icons)
```

---

## Component Architecture

### `App.tsx` (Dashboard)

The central orchestration component. It:

- Owns all top-level state: filters, pagination offset, active folder, selected listing, view mode (grid/map), liked-only toggle, hide-disliked toggle.
- Instantiates all custom hooks.
- Runs two TanStack Query queries:
  1. **`listings`** — paginated, filter-driven fetch of all listings.
  2. **`folder-listings`** — fetches listings by key when a real user folder is active.
- Derives `displayListings` with a single `useMemo` that sorts by rating then applies active folder filters.
- Passes handlers down to `Sidebar` and renders the main content area.

**Key constants / helpers in `App.tsx`:**

- `UNCATEGORIZED_FOLDER = "__uncategorized__"` — sentinel value used as `activeFolder` to indicate the virtual uncategorized view. Exported so components can import it if needed.
- `allFolderKeys` — a `Set<string>` memoized from all real folder `listingIds`. Used to compute the uncategorized filter without any extra API call.
- `isRealFolder` — boolean: `!!activeFolder && activeFolder !== UNCATEGORIZED_FOLDER`. Controls whether the folder-listings query fires.
- `listingKey(l)` — pure function: `${l.source}-${l.source_id}`. The canonical composite key used everywhere.

### `Sidebar.tsx`

Tab-shell with four tabs: Scrape, Filters, Folders, Saved. Renders one panel component per tab. Has no state of its own beyond the active tab and settings modal visibility.

### `FoldersPanel.tsx`

Renders the Folders tab. Has two sub-views:
1. **Folder list** — shows "All Listings", "Uncategorized" (virtual), and user-created folders. Clicking a folder calls `onSetActiveFolder`.
2. **Folder contents** — rendered by the inner `FolderContents` component when a user drills into a folder. Supports select-all, bulk remove, and clear.

The "Uncategorized" button uses the sentinel string `"__uncategorized__"` directly. Toggling it (clicking when already active) resets the folder to `null` (All Listings).

### `ListingCard.tsx`

Renders a single listing in the grid. Contains:
- `ImageCarousel` — internal stateful carousel with error handling per image index.
- `FolderDropdown` — checkbox dropdown for adding/removing the listing from folders.
- Visual indicators: `isNew` badge, rating state (liked/disliked), inactive badge, freshness badge, source badge.
- Missing-field highlights (red) for Telegram-sourced listings.

### `useNewListings.ts`

- Polls `fetchNewListings` every 60 seconds.
- Tracks the timestamp of the last check in a `useRef` (initialized to the current ISO timestamp on mount).
- Increments `newCount` when new listings arrive; shows a browser notification if permission is granted.
- `dismiss()` resets `newCount` to 0.
- `requestPermission()` triggers the browser notification permission dialog.

---

## Data Flow

```
Backend API
    |
    | fetchListings (paginated, filtered)
    | fetchListingsByKeys (for real folder views)
    v
TanStack Query cache
    |
    v
App.tsx (Dashboard)
    |-- displayListings (useMemo: sort + uncategorized/folder filter + liked/disliked filter)
    |
    |-- Sidebar --> FoldersPanel, DisplayFilters, ScrapePanel, SearchProfiles
    |
    |-- ListingCard (grid) / MapView / CompareView
    |
    |-- ListingDetailModal (when a listing is selected)
```

---

## Folder System

Folders are stored in `localStorage` via `useFolders`. Each folder has an `id`, `name`, and `listingIds: string[]`. The listing key format is `${source}-${source_id}`.

**Virtual folders** (not stored in localStorage):
- `null` — "All Listings" (no folder filter).
- `"__uncategorized__"` — shows only listings not present in any real folder, computed client-side from `allFolderKeys`.

**Real folders:** When active, the `folder-listings` TanStack Query fires `fetchListingsByKeys` to load the exact listing objects for the stored keys.

**Auto-folder:** Telegram-sourced listings are automatically added to a "Telegram" folder on load (see `useEffect` in `App.tsx`).

---

## State Persistence

All user data is stored in `localStorage`. Nothing is persisted to the backend:

| Data | Hook | localStorage key(s) |
|---|---|---|
| Ratings (liked/disliked) | `useListingRatings` | `listing-ratings` |
| Folders | `useFolders` | `listing-folders` |
| Notes | `useListingNotes` | `listing-notes` |
| City scrape configs | `useCitySettings` | `city-settings` |
| Facebook city configs | `useFacebookCities` | `facebook-cities` |

---

## Design Patterns

- **Optimistic UI for seen state:** When a listing is opened, its key is added to a local `Set<string>` (`localSeen`) immediately, before the server round-trip to `markListingSeen`. The `isUnseen` callback checks `localSeen` first so the "NEW" badge disappears instantly.
- **Derived display list:** All filtering and sorting happens in a single `displayListings` memo, keeping the rendering path simple. The API is never called to apply sort/filter changes that can be done client-side.
- **Sentinel constants for virtual views:** Virtual folder modes use an exported string constant rather than a separate state enum, keeping the `activeFolder: string | null` type simple and backward-compatible.
