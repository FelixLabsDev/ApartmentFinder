import { useState, useCallback, useEffect, useMemo } from "react";
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
import "./App.css";

const queryClient = new QueryClient();
const PAGE_SIZE = 50;
export const UNCATEGORIZED_FOLDER = "__uncategorized__";

type ViewMode = "grid" | "map";

function Dashboard() {
  const [filters, setFilters] = useState<Filters>({});
  const [offset, setOffset] = useState(0);
  const [allListings, setAllListings] = useState<Listing[]>([]);
  const [showLikedOnly, setShowLikedOnly] = useState(false);
  const [activeFolder, setActiveFolder] = useState<string | null>(null);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [showCompare, setShowCompare] = useState(false);
  const [hideDisliked, setHideDisliked] = useState(true);
  const { ratings, getRating, isLiked, toggleLike, toggleDislike } = useListingRatings();
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

  useEffect(() => { requestPermission(); }, [requestPermission]);

  const { data: freshListings, isLoading, error, refetch } = useQuery({
    queryKey: ["listings", filters, offset],
    queryFn: () => fetchListings(filters, PAGE_SIZE, offset),
    staleTime: 10_000,
  });

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

  const updateFilters = useCallback((newFilters: Filters) => {
    setFilters(newFilters);
    setOffset(0);
    setAllListings([]);
  }, []);

  const listings = offset === 0
    ? (freshListings ?? [])
    : [...allListings, ...(freshListings ?? [])];

  const loadMore = () => {
    setAllListings(listings);
    setOffset(offset + PAGE_SIZE);
  };

  const listingKey = (l: Listing) => `${l.source}-${l.source_id}`;

  // All listing keys that belong to at least one folder
  const allFolderKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const f of folders) {
      for (const id of f.listingIds) keys.add(id);
    }
    return keys;
  }, [folders]);

  // Client-side sort and filter
  const displayListings = useMemo(() => {
    // Use folder listings when a real folder is active, otherwise use paginated listings
    const source = isRealFolder && folderListings ? folderListings : listings;

    let result = [...source].sort((a, b) => {
      const ra = getRating(listingKey(a));
      const rb = getRating(listingKey(b));
      const oa = ra === "liked" ? -1 : ra === "disliked" ? 1 : 0;
      const ob = rb === "liked" ? -1 : rb === "disliked" ? 1 : 0;
      return oa - ob;
    });

    // Uncategorized: only show listings not in any folder
    if (activeFolder === UNCATEGORIZED_FOLDER) {
      result = result.filter((l) => !allFolderKeys.has(listingKey(l)));
    }

    if (showLikedOnly) {
      result = result.filter((l) => isLiked(listingKey(l)));
    }

    if (hideDisliked) {
      result = result.filter((l) => getRating(listingKey(l)) !== "disliked");
    }

    return result;
  }, [listings, folderListings, ratings, showLikedOnly, hideDisliked, activeFolder, isRealFolder, allFolderKeys, getRating, isLiked]);

  // Track locally-seen listing keys (optimistic, before server round-trip)
  const [localSeen, setLocalSeen] = useState<Set<string>>(new Set());

  const isUnseen = useCallback((l: Listing) => {
    if (l.seen_at) return false;
    if (localSeen.has(listingKey(l))) return false;
    return true;
  }, [localSeen]);

  const unseenCount = useMemo(
    () => displayListings.filter(isUnseen).length,
    [displayListings, isUnseen],
  );

  const likedListings = listings.filter((l) => isLiked(listingKey(l)));

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
        showLikedOnly={showLikedOnly}
        onToggleLikedOnly={() => setShowLikedOnly(!showLikedOnly)}
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
            <label className="toolbar-checkbox">
              <input
                type="checkbox"
                checked={hideDisliked}
                onChange={(e) => setHideDisliked(e.target.checked)}
              />
              Hide disliked
            </label>
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
              {showLikedOnly ? " (liked)" : ""}
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
                  onToggleLike={() => toggleLike(listingKey(listing))}
                  onToggleDislike={() => toggleDislike(listingKey(listing))}
                  folders={folders}
                  listingFolders={getFoldersForListing(listingKey(listing))}
                  onAddToFolder={(fid) => addToFolder(fid, listingKey(listing))}
                  onRemoveFromFolder={(fid) => removeFromFolder(fid, listingKey(listing))}
                  onCreateFolder={createFolder}
                  noteCount={getNotes(listingKey(listing)).length}
                  isNew={isUnseen(listing)}
                  onOpenDetail={() => {
                    setSelectedListing(listing);
                    if (isUnseen(listing)) {
                      setLocalSeen((prev) => new Set(prev).add(listingKey(listing)));
                      markListingSeen(listing.source, listing.source_id).catch(() => {});
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
            listings={displayListings.filter((l) => getRating(listingKey(l)) !== "disliked")}
            onSelectListing={(l) => {
              setSelectedListing(l);
              if (isUnseen(l)) {
                setLocalSeen((prev) => new Set(prev).add(listingKey(l)));
                markListingSeen(l.source, l.source_id).catch(() => {});
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
            onToggleLike={() => toggleLike(listingKey(selectedListing))}
            onToggleDislike={() => toggleDislike(listingKey(selectedListing))}
            folders={folders}
            listingFolders={getFoldersForListing(listingKey(selectedListing))}
            onAddToFolder={(fid) => addToFolder(fid, listingKey(selectedListing))}
            onRemoveFromFolder={(fid) => removeFromFolder(fid, listingKey(selectedListing))}
            onCreateFolder={createFolder}
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
