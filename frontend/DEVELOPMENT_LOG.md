# Development Log

Entries in reverse chronological order (newest first).

---

## 2026-03-05 — Bug Fixes + "Uncategorized" Virtual Folder Feature

### What Changed

**Files modified:** `src/components/ListingCard.tsx`, `src/hooks/useNewListings.ts`, `src/components/SearchProfiles.tsx`, `src/App.tsx`, `src/components/FoldersPanel.tsx`

### Bug Fix 1: `ListingCard.tsx` — `isNew` ReferenceError (white screen)

**Problem:** The `isNew` prop was declared in the component's TypeScript type annotation but was missing from the destructured parameter list. At runtime, referencing `isNew` in JSX threw a `ReferenceError`, causing a white screen.

**Fix:** Added `isNew` to the destructured function parameters so it is in scope.

**Lesson:** TypeScript type annotations on function parameters do not automatically destructure the values — both the type block and the destructuring list must include the prop.

---

### Bug Fix 2: `useNewListings.ts` — `useRef` without initial value fails in React 19

**Problem:** `useRef()` was called without an argument for `timerRef`. React 19 changed the behavior of `useRef` to require an explicit initial value (the type `ReturnType<typeof setInterval> | undefined` implies the value may be `undefined`, but React 19's strict types reject a call with no argument).

**Fix:** Changed `useRef()` to `useRef<ReturnType<typeof setInterval> | undefined>(undefined)`, passing `undefined` explicitly as the initial value.

**Lesson:** In React 19, always pass an explicit initial value to `useRef`. Omitting it is no longer accepted without a type assertion.

---

### Bug Fix 3: `SearchProfiles.tsx` — Unused `SearchProfile` type import

**Problem:** A `SearchProfile` type was imported from `../api` but was not used anywhere in the component. This caused a TypeScript lint warning.

**Fix:** Removed the unused import.

---

### New Feature: "Uncategorized" Virtual Folder

**Motivation:** Users had no way to quickly see listings that had not yet been placed into any folder. Without this view, unreviewed listings could be buried among already-organized ones.

**Approach (succeeded):**

- Added `UNCATEGORIZED_FOLDER = "__uncategorized__"` constant to `App.tsx`, exported so other modules can reference it without hardcoding the sentinel string.
- Added `allFolderKeys` memo in `App.tsx` — a `Set<string>` built by iterating all real folders and collecting every `listingId`. This is recomputed only when the `folders` array changes.
- In the `displayListings` memo: when `activeFolder === UNCATEGORIZED_FOLDER`, the result is filtered to only listings whose key is **not** in `allFolderKeys`. This uses the existing paginated listing data (not a separate API call), so uncategorized mode works like "All Listings" with a client-side exclusion filter.
- Updated `activeFolderName` derivation to return `"Uncategorized"` for the sentinel value.
- Updated `StatsBar` props: `folderListings` now also passes `displayListings` when the uncategorized view is active, so the stats bar shows stats for uncategorized listings.
- Updated `isRealFolder` helper to be `true` only when `activeFolder` is set **and** is not the sentinel. This ensures the folder-based `fetchListingsByKeys` query is not triggered for the uncategorized view.
- In `FoldersPanel.tsx`: added a new "Uncategorized" button between "All Listings" and the user folder list. It uses the `__uncategorized__` sentinel directly (hardcoded string in the component; the exported constant is in `App.tsx`). Clicking it toggles the uncategorized view on/off.

**No failed approaches to document for this feature.**

---
