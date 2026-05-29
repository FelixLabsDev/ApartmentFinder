import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { fetchListings, fetchListingsByKeys, markListingSeen, type Listing, type Filters } from "./api";
import { Sidebar } from "./components/Sidebar";
import { ListingCard } from "./components/ListingCard";
import { ListingDetailModal } from "./components/ListingDetailModal";
import { StatsBar } from "./components/StatsBar";
import { MapView } from "./components/MapView";
import { CompareView } from "./components/CompareView";
import { useListingRatings } from "./hooks/useListingRatings";
import { useFolders } from "./hooks/useFolders";
import { useCitySettings } from "./hooks/useCitySettings";
import { useListingNotes } from "./hooks/useListingNotes";
import { useFacebookCities } from "./hooks/useFacebookCities";
import { useNewListings } from "./hooks/useNewListings";
import { useListingTags, type Tag } from "./hooks/useListingTags";
import { usePersistedState } from "./hooks/usePersistedState";
import "./App.css";

const queryClient = new QueryClient();
const PAGE_SIZE = 50;
export const UNCATEGORIZED_FOLDER = "__uncategorized__";

type ViewMode = "grid" | "map";

function Dashboard() {
  const [filters, setFilters] = usePersistedState<Filters>("af_filters", {});
  const [offset, setOffset] = useState(0);
  const [allListings, setAllListings] = useState<Listing[]>([]);
  // minRatingFilter: 0 = show all, 1-5 = show only listings rated >= this value
  const [minRatingFilter, setMinRatingFilter] = usePersistedState<number>("af_min_rating_filter", 0);
  const [activeFolder, setActiveFolder] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [viewMode, setViewMode] = usePersistedState<ViewMode>("af_view_mode", "grid");
  const [showCompare, setShowCompare] = useState(false);
  // Hidden ratings: array of rating levels (1-5) to suppress from view; defaults to hiding Hard Nos
  const [hiddenRatings, setHiddenRatings] = usePersistedState<string[]>("af_hidden_ratings", ["1"]);
  // Hidden tag IDs: listings tagged with any of these are suppressed
  const [hiddenTagIds, setHiddenTagIds] = usePersistedState<string[]>("af_hidden_tag_ids", []);
  const { ratings, getRating, seedFromListings, setRating } = useListingRatings();
  const {
    folders, foldersLoaded, createFolder, renameFolder, deleteFolder,
    addToFolder, addMultipleToFolder, removeFromFolder, clearFolder, getFoldersForListing,
  } = useFolders();
  const {
    cities: cityConfigs, addCity, updateCity, removeCity,
  } = useCitySettings();
  const { getNotes, addNote, deleteNote } = useListingNotes();
  const { fbCities, addFbCity, updateFbCity, removeFbCity } = useFacebookCities();
  const { newCount, dismiss, requestPermission } = useNewListings();
  const { tags, createTag, addToTag, removeFromTag, getTagsForListing } = useListingTags();

  // Priority sort state: rated-first toggle + ordered list of tag IDs to sort by
  const [prioritizeLiked, setPrioritizeLiked] = usePersistedState<boolean>("af_prioritize_liked", true);
  const [tagPriorityIds, setTagPriorityIds] = usePersistedState<string[]>("af_tag_priority_ids", []);
  const [priorityOpen, setPriorityOpen] = useState(false);
  const priorityRef = useRef<HTMLDivElement>(null);

  useEffect(() => { requestPermission(); }, [requestPermission]);

  const { data: freshListings, isLoading, error, refetch } = useQuery({
    queryKey: ["listings", filters, offset],
    queryFn: () => fetchListings(filters, PAGE_SIZE, offset),
    staleTime: 10_000,
  });

  // Seed ratings from each batch of fetched listings so like/dislike buttons
  // paint immediately without waiting for the separate GET /api/ratings call
  useEffect(() => {
    if (freshListings?.length) seedFromListings(freshListings);
  }, [freshListings]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-add telegram-sourced listings to a "Telegram" folder
  useEffect(() => {
    if (!foldersLoaded || !freshListings || freshListings.length === 0) return;
    const telegramListings = freshListings.filter((l) => l.source === "telegram");
    if (telegramListings.length === 0) return;

    const telegramKeys = telegramListings.map((l) => `${l.source}-${l.source_id}`);
    let folder = folders.find((f) => f.name === "Telegram");
    if (!folder) {
      folder = createFolder("Telegram");
    }
    // Only add keys not already in the folder
    const existing = new Set(folder.listingIds);
    const newKeys = telegramKeys.filter((k) => !existing.has(k));
    if (newKeys.length > 0) {
      addMultipleToFolder(folder.id, newKeys);
    }
  }, [freshListings, foldersLoaded]); // eslint-disable-line react-hooks/exhaustive-deps

  // When a folder is active, fetch its listings directly by keys
  const isRealFolder = !!activeFolder && activeFolder !== UNCATEGORIZED_FOLDER;
  const activeFolderObj = isRealFolder ? folders.find((f) => f.id === activeFolder) : null;
  const folderKeys = activeFolderObj?.listingIds ?? [];
  const { data: folderListings, isLoading: folderLoading } = useQuery({
    queryKey: ["folder-listings", activeFolder, folderKeys],
    queryFn: () => fetchListingsByKeys(folderKeys),
    enabled: isRealFolder && folderKeys.length > 0,
    staleTime: 30_000,
  });

  // Seed folder listing ratings immediately once they arrive
  useEffect(() => {
    if (folderListings?.length) seedFromListings(folderListings);
  }, [folderListings]); // eslint-disable-line react-hooks/exhaustive-deps

  const updateFilters = useCallback((newFilters: Filters) => {
    setFilters(newFilters);
    setOffset(0);
    setAllListings([]);
  }, []);

  // Debounce the search input so we only fire a query 400ms after the user stops typing
  const handleSearchChange = useCallback((value: string) => {
    setSearchInput(value);
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      setFilters((prev) => ({ ...prev, search_query: value || undefined }));
      setOffset(0);
      setAllListings([]);
    }, 400);
  }, []);

  const listings = offset === 0
    ? (freshListings ?? [])
    : [...allListings, ...(freshListings ?? [])];

  const loadMore = () => {
    setAllListings(listings);
    setOffset(offset + PAGE_SIZE);
  };

  const listingKey = (l: Listing) => `${l.source}-${l.source_id}`;

  // Close priority panel when clicking outside
  useEffect(() => {
    if (!priorityOpen) return;
    const onDown = (e: MouseEvent) => {
      if (priorityRef.current && !priorityRef.current.contains(e.target as Node)) setPriorityOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [priorityOpen]);

  // Map of tagId → priority index (0 = highest) for O(1) sort lookups
  const tagPriorityMap = useMemo(() => {
    const map = new Map<string, number>();
    tagPriorityIds.forEach((id, i) => map.set(id, i));
    return map;
  }, [tagPriorityIds]);

  // Resolved tag objects in priority order (filters out deleted tags)
  const priorityTagObjs = useMemo(
    () => tagPriorityIds.map((id) => tags.find((t) => t.id === id)).filter((t): t is Tag => !!t),
    [tagPriorityIds, tags],
  );
  const unprioritizedTags = useMemo(() => tags.filter((t) => !tagPriorityMap.has(t.id)), [tags, tagPriorityMap]);
  const activePriorityCount = (prioritizeLiked ? 1 : 0) + tagPriorityIds.length;

  const movePriorityTag = (idx: number, dir: -1 | 1) => {
    setTagPriorityIds((prev) => {
      const next = [...prev];
      const swap = idx + dir;
      if (swap < 0 || swap >= next.length) return prev;
      [next[idx], next[swap]] = [next[swap], next[idx]];
      return next;
    });
  };
  const removePriorityTag = (id: string) => setTagPriorityIds((prev) => prev.filter((x) => x !== id));
  const addPriorityTag = (id: string) => setTagPriorityIds((prev) => [...prev, id]);

  // All listing keys that belong to at least one folder
  const allFolderKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const f of folders) {
      for (const id of f.listingIds) keys.add(id);
    }
    return keys;
  }, [folders]);

  // Sort-tier lookup: higher rating = lower sort number (appears first); unrated = middle
  const SORT_TIER_MAP: Record<string, number> = { "5": 0, "4": 1, "3": 2, "2": 4, "1": 5 };

  // Client-side sort and filter
  const displayListings = useMemo(() => {
    // Use folder listings when a real folder is active, otherwise use paginated listings
    const source = isRealFolder && folderListings ? folderListings : listings;

    // Returns a sort tier: rated-high listings surface first, rated-low last, unrated in middle
    const tier = (key: string) => {
      const r = getRating(key);
      return r ? (SORT_TIER_MAP[r] ?? 3) : 3;
    };

    // Returns the best (lowest) tag-priority index for a listing, or Infinity if none match
    const tagScore = (key: string) => {
      let min = Infinity;
      for (const t of getTagsForListing(key)) {
        const s = tagPriorityMap.get(t.id);
        if (s !== undefined && s < min) min = s;
      }
      return min;
    };

    let result = [...source].sort((a, b) => {
      const keyA = listingKey(a);
      const keyB = listingKey(b);

      // Rated-first: higher-rated listings bubble to top, lower-rated sink to bottom
      if (prioritizeLiked) {
        const td = tier(keyA) - tier(keyB);
        if (td !== 0) return td;
      }

      // Tag priority within the same tier
      if (tagPriorityIds.length > 0) {
        const sa = tagScore(keyA);
        const sb = tagScore(keyB);
        if (sa !== sb) {
          if (sa === Infinity) return 1;
          if (sb === Infinity) return -1;
          return sa - sb;
        }
      }

      return 0;
    });

    // Uncategorized: only show listings not in any folder
    if (activeFolder === UNCATEGORIZED_FOLDER) {
      result = result.filter((l) => !allFolderKeys.has(listingKey(l)));
    }

    // Show only listings rated >= minRatingFilter (when active)
    if (minRatingFilter > 0) {
      result = result.filter((l) => {
        const r = getRating(listingKey(l));
        return r !== null && parseInt(r) >= minRatingFilter;
      });
    }

    // Hide listings by rating level or tag membership
    if (hiddenRatings.length > 0 || hiddenTagIds.length > 0) {
      result = result.filter((l) => {
        const key = listingKey(l);
        if (hiddenRatings.length > 0) {
          const r = getRating(key);
          if (r !== null && hiddenRatings.includes(r)) return false;
        }
        if (hiddenTagIds.length > 0) {
          const ltIds = getTagsForListing(key).map((t) => t.id);
          if (hiddenTagIds.some((id) => ltIds.includes(id))) return false;
        }
        return true;
      });
    }

    return result;
  }, [listings, folderListings, ratings, minRatingFilter, hiddenRatings, hiddenTagIds, activeFolder, isRealFolder, allFolderKeys, getRating, prioritizeLiked, tagPriorityIds, tagPriorityMap, getTagsForListing]);

  // Track locally-seen listing keys (optimistic, before server round-trip)
  const [localSeen, setLocalSeen] = useState<Set<string>>(new Set());

  const isUnseen = useCallback((l: Listing) => {
    if (l.seen_at) return false;
    if (localSeen.has(listingKey(l))) return false;
    return true;
  }, [localSeen]);

  // True when a previously-seen listing has new content since the user last opened it
  const isUpdated = useCallback((l: Listing) => {
    if (!l.content_updated_at) return false;
    if (!l.seen_at) return false; // unseen listings show NEW instead
    return new Date(l.content_updated_at) > new Date(l.seen_at);
  }, []);

  const unseenCount = useMemo(
    () => displayListings.filter(isUnseen).length,
    [displayListings, isUnseen],
  );

  // Listings rated 4 or 5 are eligible for comparison
  const likedListings = listings.filter((l) => {
    const r = getRating(listingKey(l));
    return r === "4" || r === "5";
  });

  const handleScrapeComplete = () => {
    setOffset(0);
    setAllListings([]);
    refetch();
    queryClient.invalidateQueries({ queryKey: ["stats"] });
  };

  const handleNewListingsClick = () => {
    dismiss();
    setOffset(0);
    setAllListings([]);
    refetch();
  };

  const activeFolderName = activeFolder === UNCATEGORIZED_FOLDER
    ? "Uncategorized"
    : activeFolder
      ? folders.find((f) => f.id === activeFolder)?.name
      : null;

  return (
    <div className="layout">
      <Sidebar
        filters={filters}
        setFilters={updateFilters}
        minRatingFilter={minRatingFilter}
        onSetMinRatingFilter={setMinRatingFilter}
        hiddenRatings={hiddenRatings}
        onSetHiddenRatings={(v) => setHiddenRatings(v)}
        hiddenTagIds={hiddenTagIds}
        onSetHiddenTagIds={(v) => setHiddenTagIds(v)}
        tags={tags}
        folders={folders}
        activeFolder={activeFolder}
        onSetActiveFolder={setActiveFolder}
        onCreateFolder={createFolder}
        onRenameFolder={renameFolder}
        onDeleteFolder={deleteFolder}
        onRemoveFromFolder={removeFromFolder}
        onClearFolder={clearFolder}
        listings={listings}
        onScrapeComplete={handleScrapeComplete}
        onLoadProfile={updateFilters}
        cityConfigs={cityConfigs}
        onAddCity={addCity}
        onUpdateCity={updateCity}
        onRemoveCity={removeCity}
        fbCities={fbCities}
        onAddFbCity={addFbCity}
        onUpdateFbCity={updateFbCity}
        onRemoveFbCity={removeFbCity}
        onClearListings={handleScrapeComplete}
        onAddMultipleToFolder={addMultipleToFolder}
      />

      <main className="main-content">
        <div className="toolbar">
          <h1>Listings</h1>
          {/* Global search bar: searches URL, title, description, address, and contact fields */}
          <div className="search-bar-wrapper">
            <input
              className="search-bar"
              type="text"
              placeholder="Search by link, address, contact..."
              value={searchInput}
              onChange={(e) => handleSearchChange(e.target.value)}
            />
            {searchInput && (
              <button className="search-clear" onClick={() => handleSearchChange("")} title="Clear search">
                ×
              </button>
            )}
          </div>
          <div className="toolbar-actions">
            {unseenCount > 0 && (
              <span className="unseen-counter">
                {unseenCount} unseen
              </span>
            )}
            {newCount > 0 && (
              <button className="notification-badge" onClick={handleNewListingsClick}>
                {newCount} new listing{newCount !== 1 ? "s" : ""}
              </button>
            )}
            {likedListings.length >= 2 && (
              <button
                className="btn-compare"
                onClick={() => setShowCompare(true)}
              >
                Compare ({likedListings.length})
              </button>
            )}
            <div className="view-toggle">
              <button
                className={`view-btn${viewMode === "grid" ? " active" : ""}`}
                onClick={() => setViewMode("grid")}
              >
                Grid
              </button>
              <button
                className={`view-btn${viewMode === "map" ? " active" : ""}`}
                onClick={() => setViewMode("map")}
              >
                Map
              </button>
            </div>
            {/* Priority sort panel: liked-first toggle + tag priority ordering */}
            <div className="priority-wrap" ref={priorityRef}>
              <button
                className={`priority-btn${activePriorityCount > 0 ? " active" : ""}`}
                onClick={() => setPriorityOpen(!priorityOpen)}
                title="Sort Priority"
              >
                ↑ Priority
                {activePriorityCount > 0 && <span className="priority-count">{activePriorityCount}</span>}
              </button>
              {priorityOpen && (
                <div className="priority-panel" onClick={(e) => e.stopPropagation()}>
                  <label className="priority-toggle">
                    <input type="checkbox" checked={prioritizeLiked} onChange={(e) => setPrioritizeLiked(e.target.checked)} />
                    Rated First
                  </label>
                  <div className="priority-divider" />
                  <div className="priority-section-title">Tag Priority</div>
                  {priorityTagObjs.length === 0 && <div className="priority-empty">No tags prioritized yet</div>}
                  {priorityTagObjs.map((t, i) => (
                    <div key={t.id} className="priority-tag-item">
                      <span className="priority-rank">{i + 1}</span>
                      <span className="tag-chip" style={{ background: t.color }}>{t.name}</span>
                      <div className="priority-reorder">
                        <button onClick={() => movePriorityTag(i, -1)} disabled={i === 0} title="Move up">↑</button>
                        <button onClick={() => movePriorityTag(i, 1)} disabled={i === priorityTagObjs.length - 1} title="Move down">↓</button>
                        <button onClick={() => removePriorityTag(t.id)} title="Remove">×</button>
                      </div>
                    </div>
                  ))}
                  {unprioritizedTags.length > 0 && (
                    <select className="priority-tag-add" value="" onChange={(e) => { if (e.target.value) addPriorityTag(e.target.value); }}>
                      <option value="">+ Add tag to sort...</option>
                      {unprioritizedTags.map((t) => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  )}
                </div>
              )}
            </div>

            <select
              className="sort-select"
              value={filters.sort_by || "newest"}
              onChange={(e) => updateFilters({ ...filters, sort_by: e.target.value })}
            >
              <option value="newest">Newest First</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="rooms_asc">Rooms: Fewest First</option>
              <option value="area_desc">Area: Largest First</option>
              <option value="price_per_sqm_asc">Price/m²: Low to High</option>
              <option value="price_per_sqm_desc">Price/m²: High to Low</option>
            </select>
            <button className="btn-refresh" onClick={() => refetch()}>
              Refresh
            </button>
          </div>
        </div>

        <StatsBar
          folderListings={isRealFolder && folderListings ? folderListings : activeFolder === UNCATEGORIZED_FOLDER ? displayListings : undefined}
          likedCount={likedListings.length}
        />

        <div className="results-info">
          {displayListings.length > 0 && (
            <span>Showing {displayListings.length} listing{displayListings.length !== 1 ? "s" : ""}
              {minRatingFilter > 0 ? ` (rated \u2265 ${minRatingFilter})` : ""}
              {activeFolderName ? ` in "${activeFolderName}"` : ""}
            </span>
          )}
        </div>

        {(isLoading && offset === 0 || folderLoading) && <div className="loading">Loading listings...</div>}
        {error && <div className="error">Failed to load listings. Is the API running?</div>}

        {viewMode === "grid" ? (
          <>
            <div className="listings-grid">
              {displayListings.map((listing) => (
                <ListingCard
                  key={listingKey(listing)}
                  listing={listing}
                  rating={getRating(listingKey(listing))}
                  onSetRating={(level) => setRating(listingKey(listing), level)}
                  folders={folders}
                  listingFolders={getFoldersForListing(listingKey(listing))}
                  onAddToFolder={(fid) => addToFolder(fid, listingKey(listing))}
                  onRemoveFromFolder={(fid) => removeFromFolder(fid, listingKey(listing))}
                  onCreateFolder={createFolder}
                  allTags={tags}
                  listingTags={getTagsForListing(listingKey(listing))}
                  onAddToTag={(tid) => addToTag(tid, listingKey(listing))}
                  onRemoveFromTag={(tid) => removeFromTag(tid, listingKey(listing))}
                  onCreateTag={(name, color) => { createTag(name, color).then((t) => addToTag(t.id, listingKey(listing))); }}
                  noteCount={getNotes(listingKey(listing)).length}
                  isNew={isUnseen(listing)}
                  isUpdated={isUpdated(listing)}
                  onOpenDetail={() => {
                    setSelectedListing(listing);
                    if (isUnseen(listing) || isUpdated(listing)) {
                      setLocalSeen((prev) => new Set(prev).add(listingKey(listing)));
                      markListingSeen(listing.source, listing.source_id).catch(() => { });
                    }
                  }}
                />
              ))}
            </div>

            {!isRealFolder && freshListings && freshListings.length === PAGE_SIZE && (
              <div className="load-more-container">
                <button className="btn-load-more" onClick={loadMore} disabled={isLoading}>
                  {isLoading ? "Loading..." : "Load More"}
                </button>
              </div>
            )}
          </>
        ) : (
          <MapView
            listings={displayListings.filter((l) => getRating(listingKey(l)) !== "1")}
            onSelectListing={(l) => {
              setSelectedListing(l);
              if (isUnseen(l)) {
                setLocalSeen((prev) => new Set(prev).add(listingKey(l)));
                markListingSeen(l.source, l.source_id).catch(() => { });
              }
            }}
          />
        )}

        {listings.length === 0 && !isLoading && (
          <div className="empty-state">
            <p>No listings found. Try adjusting your filters or run a scrape.</p>
          </div>
        )}

        {selectedListing && (
          <ListingDetailModal
            listing={selectedListing}
            rating={getRating(listingKey(selectedListing))}
            onSetRating={(level) => setRating(listingKey(selectedListing), level)}
            folders={folders}
            listingFolders={getFoldersForListing(listingKey(selectedListing))}
            onAddToFolder={(fid) => addToFolder(fid, listingKey(selectedListing))}
            onRemoveFromFolder={(fid) => removeFromFolder(fid, listingKey(selectedListing))}
            onCreateFolder={createFolder}
            allTags={tags}
            listingTags={getTagsForListing(listingKey(selectedListing))}
            onAddToTag={(tid) => addToTag(tid, listingKey(selectedListing))}
            onRemoveFromTag={(tid) => removeFromTag(tid, listingKey(selectedListing))}
            onCreateTag={(name, color) => { createTag(name, color).then((t) => addToTag(t.id, listingKey(selectedListing))); }}
            notes={getNotes(listingKey(selectedListing))}
            onAddNote={(text) => addNote(listingKey(selectedListing), text)}
            onDeleteNote={(noteId) => deleteNote(listingKey(selectedListing), noteId)}
            onClose={() => setSelectedListing(null)}
            onListingUpdated={(updated) => {
              setSelectedListing(updated);
              queryClient.invalidateQueries({ queryKey: ["listings"] });
            }}
          />
        )}

        {showCompare && (
          <CompareView
            listings={likedListings}
            onClose={() => setShowCompare(false)}
          />
        )}
      </main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}

export default App;
