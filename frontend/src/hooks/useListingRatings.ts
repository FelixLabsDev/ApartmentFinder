import { useState, useCallback, useEffect, useRef } from "react";
import { setListingRating, clearListingRating, fetchAllRatings, bulkImportRatings, type Listing } from "../api";

// 1 = Hard No, 2 = Not Interested, 3 = Maybe, 4 = Interested, 5 = Perfect Match
export type Rating = "1" | "2" | "3" | "4" | "5";
type RatingsMap = Record<string, Rating>;

export const RATING_LEVELS: Array<{ level: Rating; label: string; symbol: string }> = [
  { level: "1", label: "Hard No", symbol: "\u2717" },
  { level: "2", label: "Not Interested", symbol: "\u2193" },
  { level: "3", label: "Maybe", symbol: "\u007e" },
  { level: "4", label: "Interested", symbol: "\u2713" },
  { level: "5", label: "Perfect Match", symbol: "\u2605" },
];

const OLD_STORAGE_KEY = "apartmentfinder_ratings";
const OLD_FAVORITES_KEY = "apartmentfinder_favorites";
const MIGRATED_KEY = "apartmentfinder_ratings_migrated";

// Map legacy binary values ("liked"/"disliked") to the new 5-tier scale
function normalizeLegacyRating(value: string): Rating {
  if (value === "liked") return "4";
  if (value === "disliked") return "1";
  if ((["1", "2", "3", "4", "5"] as string[]).includes(value)) return value as Rating;
  return "3";
}

export function useListingRatings() {
  const [ratings, setRatings] = useState<RatingsMap>({});
  const pendingOps = useRef<Map<string, Rating | null>>(new Map());
  const flushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load ratings from API on mount, and migrate localStorage if needed
  useEffect(() => {
    let cancelled = false;

    async function init() {
      // One-time migration of any legacy localStorage ratings to the server
      const migrated = localStorage.getItem(MIGRATED_KEY);
      if (!migrated) {
        const localRatings = loadLocalStorageRatings();
        if (Object.keys(localRatings).length > 0) {
          try {
            await bulkImportRatings(localRatings);
            // Only mark done and remove local data once the import succeeds
            localStorage.setItem(MIGRATED_KEY, "1");
            localStorage.removeItem(OLD_STORAGE_KEY);
            localStorage.removeItem(OLD_FAVORITES_KEY);
          } catch {
            // API unavailable — leave localStorage intact and retry next load
          }
        } else {
          // Nothing to migrate; mark done immediately
          localStorage.setItem(MIGRATED_KEY, "1");
        }
      }

      // Load all ratings, normalizing any legacy "liked"/"disliked" values to the new scale
      try {
        const serverRatings = await fetchAllRatings();
        if (!cancelled) {
          const normalized: RatingsMap = {};
          for (const [k, v] of Object.entries(serverRatings)) {
            normalized[k] = normalizeLegacyRating(v as string);
          }
          setRatings(normalized);
        }
      } catch {
        // API unavailable — ratings already seeded from listing data
      }
    }

    init();
    return () => { cancelled = true; };
  }, []);

  // Flush pending operations to the API
  const flushPending = useCallback(() => {
    const ops = new Map(pendingOps.current);
    pendingOps.current.clear();

    for (const [key, rating] of ops) {
      const [source, ...rest] = key.split("-");
      const sourceId = rest.join("-");
      if (rating) {
        setListingRating(source, sourceId, rating).catch(() => {});
      } else {
        clearListingRating(source, sourceId).catch(() => {});
      }
    }
  }, []);

  const scheduleFlush = useCallback(() => {
    if (flushTimer.current) clearTimeout(flushTimer.current);
    flushTimer.current = setTimeout(flushPending, 300);
  }, [flushPending]);

  const getRating = useCallback(
    (id: string): Rating | null => ratings[id] ?? null,
    [ratings],
  );

  // Seed rating state directly from fetched listing objects (avoids extra round-trip on initial render)
  const seedFromListings = useCallback((listings: Listing[]) => {
    setRatings((prev) => {
      const updates: RatingsMap = {};
      for (const l of listings) {
        if (!l.rating) continue;
        const key = `${l.source}-${l.source_id}`;
        // Don't overwrite — pending optimistic updates take priority over stale seeds
        if (!(key in prev)) updates[key] = normalizeLegacyRating(l.rating);
      }
      return Object.keys(updates).length ? { ...prev, ...updates } : prev;
    });
  }, []);

  // Set a rating level (1-5); calling with the already-active level clears it (toggle off)
  const setRating = useCallback((id: string, level: Rating) => {
    setRatings((prev) => {
      const next = { ...prev };
      if (prev[id] === level) {
        delete next[id];
        pendingOps.current.set(id, null);
      } else {
        next[id] = level;
        pendingOps.current.set(id, level);
      }
      return next;
    });
    scheduleFlush();
  }, [scheduleFlush]);

  return { ratings, getRating, seedFromListings, setRating };
}

/** Read legacy localStorage ratings for one-time migration, normalizing old binary values */
function loadLocalStorageRatings(): Record<string, string> {
  // Try new ratings format first
  try {
    const raw = localStorage.getItem(OLD_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Record<string, string>;
      const normalized: Record<string, string> = {};
      for (const [k, v] of Object.entries(parsed)) normalized[k] = normalizeLegacyRating(v);
      return normalized;
    }
  } catch {}
  // Fallback: old favorites format — treat all as "Interested" (level 4)
  try {
    const raw = localStorage.getItem(OLD_FAVORITES_KEY);
    if (raw) {
      const ids: string[] = JSON.parse(raw);
      const migrated: Record<string, string> = {};
      for (const id of ids) migrated[id] = "4";
      return migrated;
    }
  } catch {}
  return {};
}
