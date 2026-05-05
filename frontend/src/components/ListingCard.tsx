import { useState } from "react";
import type { Listing } from "../api";
import type { Rating } from "../hooks/useListingRatings";
import type { Folder } from "../hooks/useFolders";

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
          <button className="carousel-btn carousel-prev" onClick={goPrev}>&lt;</button>
          <button className="carousel-btn carousel-next" onClick={goNext}>&gt;</button>
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
  onToggleLike,
  onToggleDislike,
  folders,
  listingFolders,
  onAddToFolder,
  onRemoveFromFolder,
  onCreateFolder,
  noteCount,
  isNew,
  onOpenDetail,
}: {
  listing: Listing;
  rating: Rating | null;
  onToggleLike: () => void;
  onToggleDislike: () => void;
  folders: Folder[];
  listingFolders: Folder[];
  onAddToFolder: (folderId: string) => void;
  onRemoveFromFolder: (folderId: string) => void;
  onCreateFolder: (name: string) => void;
  noteCount: number;
  isNew: boolean;
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
    isInactive && "listing-inactive",
    rating === "liked" && "listing-liked",
    rating === "disliked" && "listing-disliked",
  ].filter(Boolean).join(" ");

  return (
    <div className={cardClasses}>
      <div className="card-image-wrapper">
        <ImageCarousel images={listing.image_urls} onClick={onOpenDetail} />
        {isNew && <span className="new-badge">NEW</span>}
      </div>

      <div className="card-header">
        <div className="card-price-group">
          <div className={`card-price${isMissingField(listing, "price") ? " field-missing" : ""}`}>{priceStr}</div>
          {priceSqm && <span className="price-per-sqm">{priceSqm}</span>}
        </div>
        <div className="card-header-right">
          <div className="rating-btns">
            <button
              className={`rating-btn like-btn${rating === "liked" ? " active" : ""}`}
              onClick={(e) => { e.stopPropagation(); onToggleLike(); }}
              title={rating === "liked" ? "Remove like" : "Like"}
            >
              {"\uD83D\uDC4D"}
            </button>
            <button
              className={`rating-btn dislike-btn${rating === "disliked" ? " active" : ""}`}
              onClick={(e) => { e.stopPropagation(); onToggleDislike(); }}
              title={rating === "disliked" ? "Remove dislike" : "Dislike"}
            >
              {"\uD83D\uDC4E"}
            </button>
          </div>
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

      <h3 className="card-title" onClick={onOpenDetail} style={{ cursor: "pointer" }}>
        {listing.rooms ? `${listing.rooms} rooms` : isTelegram ? <span className="field-missing">Rooms N/A</span> : null}
        {listing.rooms && listing.city && listing.city !== "unknown" && " in "}
        {listing.city && listing.city !== "unknown" ? listing.city : isTelegram ? <span className="field-missing"> City N/A</span> : null}
      </h3>

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
        <p className="card-description" onClick={onOpenDetail} style={{ cursor: "pointer" }}>
          {listing.description.length > 150
            ? listing.description.slice(0, 150) + "..."
            : listing.description}
        </p>
      )}

      <div className="card-footer">
        <div className="card-contact">
          {listing.contact_name && <span>{listing.contact_name}</span>}
          {listing.contact_phone && (
            <a href={`tel:${listing.contact_phone}`} className="contact-phone">
              {listing.contact_phone}
            </a>
          )}
        </div>
        <a
          href={listing.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-view"
          onClick={(e) => {
            if (!e.ctrlKey && !e.metaKey && e.button === 0) {
              e.preventDefault();
              window.open(listing.source_url, "_blank", "noopener,noreferrer");
              window.focus();
              onOpenDetail();
            }
          }}
        >
          View Listing
        </a>
      </div>
    </div>
  );
}
