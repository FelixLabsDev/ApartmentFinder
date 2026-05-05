import { useState, useCallback, useEffect, useRef } from "react";
import { setListingRating, clearListingRating, fetchAllRatings, bulkImportRatings } from "../api";

export type Rating = "liked" | "disliked";
type RatingsMap = Record<string, Rating>;

const OLD_STORAGE_KEY = "apartmentfinder_ratings";
const OLD_FAVORITES_KEY = "apartmentfinder_favorites";
const MIGRATED_KEY = "apartmentfinder_ratings_migrated";

export function useListingRatings() {
  const [ratings, setRatings] = useState<RatingsMap>({});
  const pendingOps = useRef<Map<string, Rating | null>>(new Map());
  const flushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load ratings from API on mount, and migrate localStorage if needed
  useEffect(() => {
    let cancelled = false;

    async function init() {
      // First, check if we need to migrate localStorage ratings
      const migrated = localStorage.getItem(MIGRATED_KEY);
      if (!migrated) {
        const localRatings = loadLocalStorageRatings();
        if (Object.keys(localRatings).length > 0) {
          try {
            await bulkImportRatings(localRatings);
          } catch {
            // API may not be available yet; we'll retry next load
          }
        }
        localStorage.setItem(MIGRATED_KEY, "1");
        // Clean up old keys
        localStorage.removeItem(OLD_STORAGE_KEY);
        localStorage.removeItem(OLD_FAVORITES_KEY);
      }

      // Load all ratings from server
      try {
        const serverRatings = await fetchAllRatings();
        if (!cancelled) {
          setRatings(serverRatings as RatingsMap);
        }
      } catch {
        // API unavailable — start with empty
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

  const isLiked = useCallback(
    (id: string) => ratings[id] === "liked",
    [ratings],
  );

  const isDisliked = useCallback(
    (id: string) => ratings[id] === "disliked",
    [ratings],
  );

  const toggleLike = useCallback((id: string) => {
    setRatings((prev) => {
      const next = { ...prev };
      if (prev[id] === "liked") {
        delete next[id];
        pendingOps.current.set(id, null);
      } else {
        next[id] = "liked";
        pendingOps.current.set(id, "liked");
      }
      return next;
    });
    scheduleFlush();
  }, [scheduleFlush]);

  const toggleDislike = useCallback((id: string) => {
    setRatings((prev) => {
      const next = { ...prev };
      if (prev[id] === "disliked") {
        delete next[id];
        pendingOps.current.set(id, null);
      } else {
        next[id] = "disliked";
        pendingOps.current.set(id, "disliked");
      }
      return next;
    });
    scheduleFlush();
  }, [scheduleFlush]);

  return { ratings, getRating, isLiked, isDisliked, toggleLike, toggleDislike };
}

/** Read legacy localStorage ratings for one-time migration */
function loadLocalStorageRatings(): RatingsMap {
  // Try new ratings format first
  try {
    const raw = localStorage.getItem(OLD_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  // Fallback: old favorites format
  try {
    const raw = localStorage.getItem(OLD_FAVORITES_KEY);
    if (raw) {
      const ids: string[] = JSON.parse(raw);
      const migrated: RatingsMap = {};
      for (const id of ids) migrated[id] = "liked";
      return migrated;
    }
  } catch {}
  return {};
}
