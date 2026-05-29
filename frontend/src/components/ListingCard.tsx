import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import type { Listing } from "../api";
import type { Rating } from "../hooks/useListingRatings";
import { RatingBadge } from "./RatingBadge";
import type { Folder } from "../hooks/useFolders";
import type { Tag } from "../hooks/useListingTags";

function timeAgo(dateStr: string): { text: string; stale: boolean } {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 60) return { text: `${diffMin}m ago`, stale: false };
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return { text: `${diffHrs}h ago`, stale: false };
  const diffDays = Math.floor(diffHrs / 24);
  return { text: `${diffDays}d ago`, stale: diffDays > 7 };
}

function ImageCarousel({ images, onClick }: { images: string[]; onClick?: () => void }) {
  const [idx, setIdx] = useState(0);
  const [errored, setErrored] = useState<Set<number>>(new Set());

  if (images.length === 0) return null;

  const validImages = images.filter((_, i) => !errored.has(i));
  if (validImages.length === 0) return null;

  const currentSrc = images[idx];
  const hasMultiple = validImages.length > 1;

  const goNext = () => {
    let next = (idx + 1) % images.length;
    while (errored.has(next) && next !== idx) next = (next + 1) % images.length;
    setIdx(next);
  };

  const goPrev = () => {
    let prev = (idx - 1 + images.length) % images.length;
    while (errored.has(prev) && prev !== idx) prev = (prev - 1 + images.length) % images.length;
    setIdx(prev);
  };

  return (
    <div className="image-carousel">
      {errored.has(idx) ? (
        <div className="carousel-placeholder">No image</div>
      ) : (
        <img
          src={currentSrc}
          alt="Listing"
          className="carousel-image"
          style={onClick ? { cursor: "pointer" } : undefined}
          onClick={onClick}
          onError={() => setErrored((prev) => new Set(prev).add(idx))}
        />
      )}
      {hasMultiple && (
        <>
          <button className="carousel-btn carousel-prev" onClick={(e) => { e.stopPropagation(); goPrev(); }}>&lt;</button>
          <button className="carousel-btn carousel-next" onClick={(e) => { e.stopPropagation(); goNext(); }}>&gt;</button>
          <span className="carousel-counter">{idx + 1}/{images.length}</span>
        </>
      )}
    </div>
  );
}

function FolderDropdown({
  folders,
  listingFolders,
  onAddToFolder,
  onRemoveFromFolder,
  onCreateFolder,
}: {
  folders: Folder[];
  listingFolders: Folder[];
  onAddToFolder: (folderId: string) => void;
  onRemoveFromFolder: (folderId: string) => void;
  onCreateFolder: (name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");

  const inFolderIds = new Set(listingFolders.map((f) => f.id));

  return (
    <div className="folder-dropdown-wrap">
      <button
        className={`folder-btn${listingFolders.length > 0 ? " has-folders" : ""}`}
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
        title="Add to folder"
      >
        {"\uD83D\uDCC1"}
        {listingFolders.length > 0 && (
          <span className="folder-count">{listingFolders.length}</span>
        )}
      </button>
      {open && (
        <div className="folder-dropdown" onClick={(e) => e.stopPropagation()}>
          {folders.length === 0 && (
            <div className="folder-dropdown-empty">No folders yet</div>
          )}
          {folders.map((f) => (
            <label key={f.id} className="folder-dropdown-item">
              <input
                type="checkbox"
                checked={inFolderIds.has(f.id)}
                onChange={() =>
                  inFolderIds.has(f.id)
                    ? onRemoveFromFolder(f.id)
                    : onAddToFolder(f.id)
                }
              />
              {f.name}
            </label>
          ))}
          <div className="folder-dropdown-create">
            <input
              type="text"
              placeholder="New folder..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newName.trim()) {
                  onCreateFolder(newName.trim());
                  setNewName("");
                }
              }}
            />
          </div>
          <button className="folder-dropdown-done" onClick={() => setOpen(false)}>
            Done
          </button>
        </div>
      )}
    </div>
  );
}

// Available colors for new tags
const TAG_PALETTE = ["#fc8181", "#f6ad55", "#68d391", "#63b3ed", "#b794f4", "#fbb6ce", "#81e6d9", "#faf089"];

function TagDropdown({
  allTags,
  listingTags,
  onAddToTag,
  onRemoveFromTag,
  onCreateTag,
}: {
  allTags: Tag[];
  listingTags: Tag[];
  onAddToTag: (tagId: string) => void;
  onRemoveFromTag: (tagId: string) => void;
  onCreateTag: (name: string, color: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [pickedColor, setPickedColor] = useState(TAG_PALETTE[0]);
  // Viewport-fixed position captured when the dropdown opens so it never shifts
  const [dropPos, setDropPos] = useState<{ top: number; right: number }>({ top: 0, right: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);
  const inTagIds = new Set(listingTags.map((t) => t.id));

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (
        dropRef.current && !dropRef.current.contains(e.target as Node) &&
        btnRef.current && !btnRef.current.contains(e.target as Node)
      ) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  // Recompute position on any scroll so the dropdown tracks the button
  useEffect(() => {
    if (!open) return;
    const onScroll = () => {
      if (!btnRef.current) return;
      const rect = btnRef.current.getBoundingClientRect();
      // Close if the button has scrolled entirely out of view
      if (rect.bottom < 0 || rect.top > window.innerHeight) { setOpen(false); return; }
      setDropPos({ top: rect.bottom + 4, right: window.innerWidth - rect.right });
    };
    // Capture phase catches scroll on any nested scrollable element too
    window.addEventListener("scroll", onScroll, true);
    return () => window.removeEventListener("scroll", onScroll, true);
  }, [open]);

  const handleOpen = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!open && btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      // Anchor the dropdown's top-right corner to the button's bottom-right
      setDropPos({ top: rect.bottom + 4, right: window.innerWidth - rect.right });
    }
    setOpen((v) => !v);
  };

  const submitNew = () => {
    if (!newName.trim()) return;
    onCreateTag(newName.trim(), pickedColor);
    setNewName("");
    setPickedColor(TAG_PALETTE[0]);
  };

  return (
    <div className="tag-dropdown-wrap">
      <button ref={btnRef} className="tag-add-btn" onClick={handleOpen} title="Add tag">
        {"\uD83C\uDFF7"}
      </button>
      {open && createPortal(
        <div
          ref={dropRef}
          className="tag-dropdown"
          style={{ position: "fixed", top: dropPos.top, right: dropPos.right, left: "auto" }}
          onClick={(e) => e.stopPropagation()}
        >
          {allTags.length === 0 && <div className="tag-dropdown-empty">No tags yet</div>}
          {allTags.map((t) => (
            <label key={t.id} className="tag-dropdown-item">
              <input
                type="checkbox"
                checked={inTagIds.has(t.id)}
                onChange={() => inTagIds.has(t.id) ? onRemoveFromTag(t.id) : onAddToTag(t.id)}
              />
              <span className="tag-swatch" style={{ background: t.color }} />
              {t.name}
            </label>
          ))}
          {/* New tag creation: color palette + name input */}
          <div className="tag-dropdown-create">
            <div className="tag-color-picker">
              {TAG_PALETTE.map((c) => (
                <button
                  key={c}
                  className={`tag-palette-btn${pickedColor === c ? " selected" : ""}`}
                  style={{ background: c }}
                  onClick={() => setPickedColor(c)}
                  title={c}
                />
              ))}
            </div>
            <div className="tag-create-row">
              <span className="tag-preview" style={{ background: pickedColor }} />
              <input
                type="text"
                placeholder="New tag name..."
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") submitNew(); }}
              />
              <button className="tag-create-btn" onClick={submitNew} disabled={!newName.trim()}>+</button>
            </div>
          </div>
          <button className="tag-dropdown-done" onClick={() => setOpen(false)}>Done</button>
        </div>,
        document.body,
      )}
    </div>
  );
}

// Fields that should be highlighted red when missing on AI-extracted listings
const REQUIRED_DISPLAY_FIELDS: Record<string, { label: string; getValue: (l: Listing) => unknown }> = {
  price: { label: "Price", getValue: (l) => l.price },
  rooms: { label: "Rooms", getValue: (l) => l.rooms },
  city: { label: "City", getValue: (l) => l.city && l.city !== "unknown" ? l.city : null },
  area_sqm: { label: "Area", getValue: (l) => l.area_sqm },
  floor: { label: "Floor", getValue: (l) => l.floor },
  street: { label: "Street", getValue: (l) => l.street },
  neighborhood: { label: "Neighborhood", getValue: (l) => l.neighborhood },
  entry_date: { label: "Move-in date", getValue: (l) => l.entry_date },
};

function isMissingField(listing: Listing, field: string): boolean {
  if (listing.source !== "telegram") return false;
  const def = REQUIRED_DISPLAY_FIELDS[field];
  if (!def) return false;
  return def.getValue(listing) == null;
}

export function ListingCard({
  listing,
  rating,
  onSetRating,
  folders,
  listingFolders,
  onAddToFolder,
  onRemoveFromFolder,
  onCreateFolder,
  allTags,
  listingTags,
  onAddToTag,
  onRemoveFromTag,
  onCreateTag,
  noteCount,
  isNew,
  isUpdated = false,
  onOpenDetail,
}: {
  listing: Listing;
  rating: Rating | null;
  onSetRating: (level: Rating) => void;
  folders: Folder[];
  listingFolders: Folder[];
  onAddToFolder: (folderId: string) => void;
  onRemoveFromFolder: (folderId: string) => void;
  onCreateFolder: (name: string) => void;
  allTags: Tag[];
  listingTags: Tag[];
  onAddToTag: (tagId: string) => void;
  onRemoveFromTag: (tagId: string) => void;
  onCreateTag: (name: string, color: string) => void;
  noteCount: number;
  isNew: boolean;
  isUpdated?: boolean;
  onOpenDetail: () => void;
}) {
  const isTelegram = listing.source === "telegram";
  const features = [
    listing.has_parking && "Parking",
    listing.has_elevator && "Elevator",
    listing.has_balcony && "Balcony",
    listing.has_air_conditioning && "A/C",
    listing.has_mamad && "Mamad",
    listing.is_furnished && "Furnished",
    listing.pet_friendly && "Pet OK",
    listing.has_storage && "Storage",
    listing.has_bars && "Bars",
    listing.is_accessible && "Accessible",
  ].filter(Boolean);

  const priceStr = listing.price
    ? `${listing.price.toLocaleString()} ${listing.currency === "ILS" ? "\u20aa" : "$"}`
    : "Price N/A";

  const priceSqm = listing.price && listing.area_sqm
    ? `${Math.round(listing.price / listing.area_sqm).toLocaleString()} \u20aa/m²`
    : null;

  const freshness = listing.posted_at
    ? timeAgo(listing.posted_at)
    : listing.first_seen_at
      ? timeAgo(listing.first_seen_at)
      : null;

  const isInactive = listing.is_active === false;

  const cardClasses = [
    "listing-card",
    isNew && "listing-new",
    isUpdated && !isNew && "listing-updated",
    isInactive && "listing-inactive",
    rating && `listing-rating-${rating}`,
  ].filter(Boolean).join(" ");

  return (
    <div className={cardClasses} onClick={onOpenDetail} style={{ cursor: "pointer" }}>
      <div className="card-image-wrapper">
        <ImageCarousel images={listing.image_urls} />
        {isNew && <span className="new-badge">NEW</span>}
        {isUpdated && !isNew && <span className="updated-badge">UPDATED</span>}
      </div>

      <div className="card-header">
        <div className="card-price-group">
          <div className={`card-price${isMissingField(listing, "price") ? " field-missing" : ""}`}>{priceStr}</div>
          {priceSqm && <span className="price-per-sqm">{priceSqm}</span>}
        </div>
        <div className="card-header-right">
          <RatingBadge rating={rating} onSetRating={onSetRating} />
          <FolderDropdown
            folders={folders}
            listingFolders={listingFolders}
            onAddToFolder={onAddToFolder}
            onRemoveFromFolder={onRemoveFromFolder}
            onCreateFolder={onCreateFolder}
          />
          {noteCount > 0 && (
            <span className="note-badge" title={`${noteCount} note${noteCount !== 1 ? "s" : ""}`}>
              {"\uD83D\uDCDD"}{noteCount}
            </span>
          )}
          {isInactive && <span className="inactive-badge">May be taken</span>}
          {freshness && (
            <span className={`freshness-badge${freshness.stale ? " stale" : ""}`}>
              {freshness.text}
            </span>
          )}
          <span className={`source-badge source-${listing.source}`}>{listing.source}</span>
        </div>
      </div>

      <div className="card-title-row">
        <h3 className="card-title">
          {listing.rooms ? `${listing.rooms} rooms` : isTelegram ? <span className="field-missing">Rooms N/A</span> : null}
          {listing.rooms && listing.city && listing.city !== "unknown" && " in "}
          {listing.city && listing.city !== "unknown" ? listing.city : isTelegram ? <span className="field-missing"> City N/A</span> : null}
        </h3>
        {/* Tag chips + dropdown button, aligned right of title */}
        <div className="card-tags-area">
          {listingTags.map((t) => (
            <span key={t.id} className="tag-chip" style={{ background: t.color }}>{t.name}</span>
          ))}
          <TagDropdown
            allTags={allTags}
            listingTags={listingTags}
            onAddToTag={onAddToTag}
            onRemoveFromTag={onRemoveFromTag}
            onCreateTag={onCreateTag}
          />
        </div>
      </div>

      {isTelegram && (
        <div className="card-missing-fields">
          {Object.entries(REQUIRED_DISPLAY_FIELDS)
            .filter(([key]) => isMissingField(listing, key))
            .map(([key, def]) => (
              <span key={key} className="missing-field-tag">{def.label}</span>
            ))}
        </div>
      )}

      <div className="card-details">
        {listing.area_sqm ? <span>{listing.area_sqm} m²</span> : isTelegram && <span className="field-missing">Area N/A</span>}
        {listing.street && (
          <span>{listing.street}{listing.house_number ? ` ${listing.house_number}` : ""}</span>
        )}
        {listing.neighborhood && <span>{listing.neighborhood}</span>}
        {listing.floor != null ? (
          <span>Floor {listing.floor}{listing.total_floors ? `/${listing.total_floors}` : ""}</span>
        ) : isTelegram && <span className="field-missing">Floor N/A</span>}
        {listing.property_type && <span>{listing.property_type}</span>}
        {listing.entry_date && <span>Move in: {listing.entry_date}</span>}
      </div>

      {listingFolders.length > 0 && (
        <div className="card-folders">
          {listingFolders.map((f) => (
            <span key={f.id} className="folder-chip">{f.name}</span>
          ))}
        </div>
      )}

      {features.length > 0 && (
        <div className="card-features">
          {features.map((f) => (
            <span key={f as string} className="feature-tag">{f}</span>
          ))}
        </div>
      )}

      {listing.description && (
        <p className="card-description">
          {listing.description.length > 150
            ? listing.description.slice(0, 150) + "..."
            : listing.description}
        </p>
      )}

      <div className="card-footer">
        <div className="card-contact" onClick={(e) => e.stopPropagation()}>
          {listing.contact_name && <span>{listing.contact_name}</span>}
          {listing.contact_phone && (
            <a href={`tel:${listing.contact_phone}`} className="contact-phone">
              {listing.contact_phone}
            </a>
          )}
        </div>
        <div className="card-footer-actions">
          {/* Build Google Maps URL: prefer coordinates, fall back to address string */}
          {(listing.latitude && listing.longitude
            ? `https://www.google.com/maps?q=${listing.latitude},${listing.longitude}`
            : listing.street || listing.city
              ? `https://www.google.com/maps/search/${encodeURIComponent([listing.street, listing.city].filter(Boolean).join(", "))}`
              : null
          ) && (
            <a
              href={
                listing.latitude && listing.longitude
                  ? `https://www.google.com/maps?q=${listing.latitude},${listing.longitude}`
                  : `https://www.google.com/maps/search/${encodeURIComponent([listing.street, listing.city].filter(Boolean).join(", "))}`
              }
              target="_blank"
              rel="noopener noreferrer"
              className="btn-maps"
              onClick={(e) => e.stopPropagation()}
            >
              Maps
            </a>
          )}
          <a
            href={listing.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-view"
            onClick={(e) => {
              e.stopPropagation();
              if (!e.ctrlKey && !e.metaKey && e.button === 0) {
                e.preventDefault();
                window.open(listing.source_url, "_blank", "noopener,noreferrer");
                window.focus();
              }
            }}
          >
            View Listing
          </a>
        </div>
      </div>
    </div>
  );
}
