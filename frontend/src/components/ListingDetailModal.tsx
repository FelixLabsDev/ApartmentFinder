import { useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { Listing } from "../api";
import { aiExtractListing } from "../api";
import type { Rating } from "../hooks/useListingRatings";
import type { Folder } from "../hooks/useFolders";
import type { ListingNote } from "../hooks/useListingNotes";

export function ListingDetailModal({
  listing,
  rating,
  onToggleLike,
  onToggleDislike,
  folders,
  listingFolders,
  onAddToFolder,
  onRemoveFromFolder,
  onCreateFolder,
  notes,
  onAddNote,
  onDeleteNote,
  onClose,
  onListingUpdated,
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
  notes: ListingNote[];
  onAddNote: (text: string) => void;
  onDeleteNote: (noteId: string) => void;
  onClose: () => void;
  onListingUpdated?: (updated: Listing) => void;
}) {
  const [imgIdx, setImgIdx] = useState(0);
  const [newFolderName, setNewFolderName] = useState("");
  const [noteText, setNoteText] = useState("");
  const [notesOpen, setNotesOpen] = useState(false);
  const [lightbox, setLightbox] = useState(false);
  const [aiExtracting, setAiExtracting] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight" && listing.image_urls.length > 1)
        setImgIdx((i) => (i + 1) % listing.image_urls.length);
      if (e.key === "ArrowLeft" && listing.image_urls.length > 1)
        setImgIdx((i) => (i - 1 + listing.image_urls.length) % listing.image_urls.length);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, listing.image_urls.length]);

  const priceStr = listing.price
    ? `${listing.price.toLocaleString()} ${listing.currency === "ILS" ? "\u20aa" : "$"}`
    : "Price N/A";

  const priceSqm = listing.price && listing.area_sqm
    ? `${Math.round(listing.price / listing.area_sqm).toLocaleString()} \u20aa/m²`
    : null;

  const isTelegram = listing.source === "telegram";
  const hasLocation = listing.latitude != null && listing.longitude != null;

  const allFeatures = [
    listing.has_parking && "Parking",
    listing.has_elevator && "Elevator",
    listing.has_balcony && "Balcony",
    listing.has_air_conditioning && "A/C",
    listing.has_mamad && "Mamad (Safe Room)",
    listing.is_furnished && "Furnished",
    listing.pet_friendly && "Pet Friendly",
    listing.has_storage && "Storage Room",
    listing.has_bars && "Window Bars",
    listing.is_accessible && "Wheelchair Accessible",
  ].filter(Boolean);

  const inFolderIds = new Set(listingFolders.map((f) => f.id));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className={`modal-content modal-has-sidebar${hasLocation ? " modal-with-map" : ""}${notesOpen ? " modal-notes-open" : ""}`} onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>&times;</button>

        <button
          className={`notes-toggle-btn${notes.length > 0 ? " has-notes" : ""}`}
          onClick={() => setNotesOpen(!notesOpen)}
          title={notesOpen ? "Close notes" : "Open notes"}
        >
          {"\uD83D\uDCDD"}
          {notes.length > 0 && <span className="notes-toggle-count">{notes.length}</span>}
        </button>

        {notesOpen && (
          <div className="notes-sidebar">
            <div className="notes-sidebar-header">
              <h4>Notes</h4>
            </div>
            <div className="notes-sidebar-messages">
              {notes.length === 0 && (
                <div className="notes-empty">No notes yet. Add one below.</div>
              )}
              {[...notes].reverse().map((note) => (
                <div key={note.id} className="notes-message">
                  <div className="notes-message-bubble">
                    <p className="notes-message-text">{note.text}</p>
                    <button
                      className="notes-message-delete"
                      onClick={() => onDeleteNote(note.id)}
                      title="Delete note"
                    >
                      &times;
                    </button>
                  </div>
                  <span className="notes-message-time">
                    {new Date(note.createdAt).toLocaleDateString(undefined, {
                      day: "numeric", month: "short",
                    })}{" "}
                    {new Date(note.createdAt).toLocaleTimeString(undefined, {
                      hour: "2-digit", minute: "2-digit",
                    })}
                  </span>
                </div>
              ))}
            </div>
            <div className="notes-sidebar-input">
              <input
                type="text"
                placeholder="Write a note..."
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && noteText.trim()) {
                    onAddNote(noteText.trim());
                    setNoteText("");
                  }
                }}
              />
              <button
                onClick={() => {
                  if (noteText.trim()) {
                    onAddNote(noteText.trim());
                    setNoteText("");
                  }
                }}
              >
                Send
              </button>
            </div>
          </div>
        )}

        <div className="modal-left">
          {listing.image_urls.length > 0 && (
            <div className="modal-images" style={{ position: "relative" }}>
              <img
                src={listing.image_urls[imgIdx]}
                alt={`Listing ${imgIdx + 1}`}
                className="modal-main-image"
                style={{ cursor: "pointer" }}
                onClick={() => setImgIdx((i) => (i + 1) % listing.image_urls.length)}
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
              <button
                className="image-fullscreen-btn"
                onClick={() => setLightbox(true)}
                title="View fullscreen"
              >
                {"\u26F6"}
              </button>
              {listing.image_urls.length > 1 && (
                <div className="modal-image-nav">
                  <button onClick={() => setImgIdx((i) => (i - 1 + listing.image_urls.length) % listing.image_urls.length)}>&lt;</button>
                  <span>{imgIdx + 1} / {listing.image_urls.length}</span>
                  <button onClick={() => setImgIdx((i) => (i + 1) % listing.image_urls.length)}>&gt;</button>
                </div>
              )}
              <div className="modal-thumbnails">
                {listing.image_urls.slice(0, 8).map((url, i) => (
                  <img
                    key={i}
                    src={url}
                    alt={`Thumb ${i + 1}`}
                    className={`modal-thumb${i === imgIdx ? " active" : ""}`}
                    onClick={() => setImgIdx(i)}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                ))}
              </div>
            </div>
          )}

          <div className="modal-body">
            <div className="modal-header-row">
              <div>
                <h2 className="modal-title">
                  {listing.rooms && `${listing.rooms} rooms`}
                  {listing.rooms && listing.city && " in "}
                  {listing.city}
                </h2>
                <div className="modal-price-row">
                  <span className={`modal-price${isTelegram && !listing.price ? " field-missing" : ""}`}>{priceStr}</span>
                  {priceSqm && <span className="modal-price-sqm">{priceSqm}</span>}
                </div>
              </div>
              <div className="modal-rating-group">
                <button
                  className={`rating-btn like-btn${rating === "liked" ? " active" : ""}`}
                  onClick={onToggleLike}
                  title={rating === "liked" ? "Remove like" : "Like"}
                >
                  {"\uD83D\uDC4D"}
                </button>
                <button
                  className={`rating-btn dislike-btn${rating === "disliked" ? " active" : ""}`}
                  onClick={onToggleDislike}
                  title={rating === "disliked" ? "Remove dislike" : "Dislike"}
                >
                  {"\uD83D\uDC4E"}
                </button>
              </div>
            </div>

            <div className="modal-action-links">
              <a href={listing.source_url} target="_blank" rel="noopener noreferrer" className="btn-view-listing">
                View on {listing.source}
              </a>
              {hasLocation && (
                <a
                  href={`https://www.google.com/maps?q=${listing.latitude},${listing.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-view-listing btn-google-maps"
                >
                  Open on Google Maps
                </a>
              )}
              {listing.source === "facebook" && (
                <button
                  className="btn-view-listing btn-ai-extract"
                  disabled={aiExtracting}
                  onClick={async () => {
                    setAiExtracting(true);
                    setAiError(null);
                    try {
                      const updated = await aiExtractListing(listing.source, listing.source_id);
                      onListingUpdated?.(updated);
                    } catch (err: unknown) {
                      const msg = err instanceof Error ? err.message : "AI extraction failed";
                      setAiError(msg);
                    } finally {
                      setAiExtracting(false);
                    }
                  }}
                >
                  {aiExtracting ? "Extracting..." : "AI Extract Fields"}
                </button>
              )}
              {aiError && <span className="ai-extract-error">{aiError}</span>}
            </div>

            <div className="modal-folders">
              <div className="modal-folders-current">
                {listingFolders.map((f) => (
                  <span key={f.id} className="folder-chip">
                    {f.name}
                    <button
                      className="chip-delete"
                      onClick={() => onRemoveFromFolder(f.id)}
                      title="Remove from folder"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
              <div className="modal-folders-add">
                <select
                  value=""
                  onChange={(e) => {
                    if (e.target.value) onAddToFolder(e.target.value);
                  }}
                >
                  <option value="">Add to folder...</option>
                  {folders.filter((f) => !inFolderIds.has(f.id)).map((f) => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
                <div className="modal-folders-create">
                  <input
                    type="text"
                    placeholder="New folder..."
                    value={newFolderName}
                    onChange={(e) => setNewFolderName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && newFolderName.trim()) {
                        onCreateFolder(newFolderName.trim());
                        setNewFolderName("");
                      }
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="modal-info-grid">
              {listing.street ? (
                <div className="modal-info-item"><strong>Address</strong>{listing.street}{listing.house_number ? ` ${listing.house_number}` : ""}, {listing.city}</div>
              ) : isTelegram && (
                <div className="modal-info-item field-missing"><strong>Address</strong>N/A</div>
              )}
              {listing.neighborhood ? (
                <div className="modal-info-item"><strong>Neighborhood</strong>{listing.neighborhood}</div>
              ) : isTelegram && (
                <div className="modal-info-item field-missing"><strong>Neighborhood</strong>N/A</div>
              )}
              {listing.floor != null ? (
                <div className="modal-info-item"><strong>Floor</strong>{listing.floor}{listing.total_floors ? ` / ${listing.total_floors}` : ""}</div>
              ) : isTelegram && (
                <div className="modal-info-item field-missing"><strong>Floor</strong>N/A</div>
              )}
              {listing.area_sqm ? (
                <div className="modal-info-item"><strong>Area</strong>{listing.area_sqm} m²</div>
              ) : isTelegram && (
                <div className="modal-info-item field-missing"><strong>Area</strong>N/A</div>
              )}
              {listing.property_type && <div className="modal-info-item"><strong>Type</strong>{listing.property_type}</div>}
              {listing.entry_date ? (
                <div className="modal-info-item"><strong>Move-in Date</strong>{listing.entry_date}</div>
              ) : isTelegram && (
                <div className="modal-info-item field-missing"><strong>Move-in Date</strong>N/A</div>
              )}
              <div className="modal-info-item"><strong>Source</strong><span className={`source-badge source-${listing.source}`}>{listing.source}</span></div>
              {isTelegram && listing.ai_guessed_fields.length > 0 && (
                <div className="modal-info-item"><strong>AI Extracted</strong><span className="ai-badge">Fields: {listing.ai_guessed_fields.join(", ")}</span></div>
              )}
            </div>

            {allFeatures.length > 0 && (
              <div className="modal-section">
                <h4>Features</h4>
                <div className="modal-features">
                  {allFeatures.map((f) => (
                    <span key={f as string} className="feature-tag">{f}</span>
                  ))}
                </div>
              </div>
            )}

            {listing.description && (
              <div className="modal-section">
                <h4>Description</h4>
                <p className="modal-description">{listing.description}</p>
              </div>
            )}

            <div className="modal-section modal-contact-section">
              <h4>Contact</h4>
              {listing.contact_name && <p>{listing.contact_name}</p>}
              {listing.contact_phone && (
                <a href={`tel:${listing.contact_phone}`} className="modal-phone-link">
                  {listing.contact_phone}
                </a>
              )}
            </div>
          </div>
        </div>

        {hasLocation && (
          <div className="modal-map">
            <MapContainer
              center={[listing.latitude!, listing.longitude!]}
              zoom={15}
              style={{ height: "100%", width: "100%" }}
              scrollWheelZoom={true}
            >
              <TileLayer
                attribution='&copy; Google Maps'
                url="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
              />
              <Marker position={[listing.latitude!, listing.longitude!]} />
            </MapContainer>
          </div>
        )}
      </div>

      {lightbox && (
        <div className="lightbox-overlay" onClick={() => setLightbox(false)}>
          <button className="lightbox-close" onClick={() => setLightbox(false)}>&times;</button>
          <button
            className="lightbox-nav lightbox-prev"
            onClick={(e) => { e.stopPropagation(); setImgIdx((i) => (i - 1 + listing.image_urls.length) % listing.image_urls.length); }}
          >
            &lt;
          </button>
          <img
            src={listing.image_urls[imgIdx]}
            alt={`Listing ${imgIdx + 1}`}
            className="lightbox-image"
            onClick={(e) => { e.stopPropagation(); setImgIdx((i) => (i + 1) % listing.image_urls.length); }}
          />
          <button
            className="lightbox-nav lightbox-next"
            onClick={(e) => { e.stopPropagation(); setImgIdx((i) => (i + 1) % listing.image_urls.length); }}
          >
            &gt;
          </button>
          <span className="lightbox-counter">{imgIdx + 1} / {listing.image_urls.length}</span>
        </div>
      )}
    </div>
  );
}
