import { useState, useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { Listing, WhatsappMessage } from "../api";
import { aiExtractListing, setListingWhatsappPhone, removeListingWhatsappPhone, fetchWhatsappHistory, sendWhatsappMessage } from "../api";
import type { Rating } from "../hooks/useListingRatings";
import { RatingBadge } from "./RatingBadge";
import type { Folder } from "../hooks/useFolders";
import type { ListingNote } from "../hooks/useListingNotes";
import type { Tag } from "../hooks/useListingTags";

const TAG_PALETTE = ["#fc8181", "#f6ad55", "#68d391", "#63b3ed", "#b794f4", "#fbb6ce", "#81e6d9", "#faf089"];

export function ListingDetailModal({
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
  notes,
  onAddNote,
  onDeleteNote,
  onClose,
  onListingUpdated,
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
  notes: ListingNote[];
  onAddNote: (text: string) => void;
  onDeleteNote: (noteId: string) => void;
  onClose: () => void;
  onListingUpdated?: (updated: Listing) => void;
}) {
  const [imgIdx, setImgIdx] = useState(0);
  const [newFolderName, setNewFolderName] = useState("");
  const [newTagName, setNewTagName] = useState("");
  const [newTagColor, setNewTagColor] = useState(TAG_PALETTE[0]);
  const [noteText, setNoteText] = useState("");
  const [notesOpen, setNotesOpen] = useState(false);
  const [lightbox, setLightbox] = useState(false);
  const [aiExtracting, setAiExtracting] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  // WhatsApp panel state
  const [whatsappOpen, setWhatsappOpen] = useState(false);
  const [whatsappPhone, setWhatsappPhone] = useState<string | null>(listing.whatsapp_phone);
  const [phoneInput, setPhoneInput] = useState("");
  const [whatsappHistory, setWhatsappHistory] = useState<WhatsappMessage[]>([]);
  const [whatsappLoading, setWhatsappLoading] = useState(false);
  const [whatsappError, setWhatsappError] = useState<string | null>(null);
  const [whatsappMessage, setWhatsappMessage] = useState("");
  const [sendingMessage, setSendingMessage] = useState(false);
  const [editingPhone, setEditingPhone] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Close lightbox first on Escape, then the modal on a second Escape
      if (e.key === "Escape") { if (lightbox) setLightbox(false); else onClose(); }
      if (e.key === "ArrowRight" && listing.image_urls.length > 1)
        setImgIdx((i) => (i + 1) % listing.image_urls.length);
      if (e.key === "ArrowLeft" && listing.image_urls.length > 1)
        setImgIdx((i) => (i - 1 + listing.image_urls.length) % listing.image_urls.length);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, listing.image_urls.length, lightbox]);

  // Refresh WhatsApp chat every time the panel is opened or the listing changes
  useEffect(() => {
    if (!whatsappOpen || !whatsappPhone) return;
    const loadHistory = async () => {
      setWhatsappLoading(true);
      setWhatsappError(null);
      try {
        const history = await fetchWhatsappHistory(listing.source, listing.source_id);
        setWhatsappHistory(history);
      } catch (err: unknown) {
        setWhatsappError(err instanceof Error ? err.message : "Failed to load chat history");
      } finally {
        setWhatsappLoading(false);
      }
    };
    loadHistory();
  }, [whatsappOpen, whatsappPhone, listing.source, listing.source_id]);

  // Scroll to the bottom of chat when history updates
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [whatsappHistory]);

  const handleSetPhone = async () => {
    if (!phoneInput.trim()) return;
    try {
      const updated = await setListingWhatsappPhone(listing.source, listing.source_id, phoneInput.trim());
      setWhatsappPhone(updated.whatsapp_phone);
      setPhoneInput("");
      setEditingPhone(false);
      onListingUpdated?.(updated);
    } catch (err: unknown) {
      setWhatsappError(err instanceof Error ? err.message : "Failed to set phone");
    }
  };

  const handleRemovePhone = async () => {
    try {
      const updated = await removeListingWhatsappPhone(listing.source, listing.source_id);
      setWhatsappPhone(null);
      setWhatsappHistory([]);
      onListingUpdated?.(updated);
    } catch (err: unknown) {
      setWhatsappError(err instanceof Error ? err.message : "Failed to remove phone");
    }
  };

  const handleSendMessage = async () => {
    if (!whatsappMessage.trim()) return;
    setSendingMessage(true);
    try {
      await sendWhatsappMessage(listing.source, listing.source_id, whatsappMessage.trim());
      setWhatsappMessage("");
      // Refresh history after sending
      const history = await fetchWhatsappHistory(listing.source, listing.source_id);
      setWhatsappHistory(history);
    } catch (err: unknown) {
      setWhatsappError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setSendingMessage(false);
    }
  };

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
      <div className={`modal-content modal-has-sidebar${hasLocation ? " modal-with-map" : ""}${notesOpen ? " modal-notes-open" : ""}${whatsappOpen ? " modal-whatsapp-open" : ""}`} onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>&times;</button>

        <button
          className={`notes-toggle-btn${notes.length > 0 ? " has-notes" : ""}`}
          onClick={() => setNotesOpen(!notesOpen)}
          title={notesOpen ? "Close notes" : "Open notes"}
        >
          {"\uD83D\uDCDD"}
          {notes.length > 0 && <span className="notes-toggle-count">{notes.length}</span>}
        </button>

        {/* WhatsApp toggle button — only rendered when the sidebar is closed, so it never overlaps the sidebar */}
        {!whatsappOpen && (
          <button
            className={`whatsapp-toggle-btn${whatsappPhone ? " has-whatsapp" : ""}`}
            onClick={() => setWhatsappOpen(true)}
            title="Open WhatsApp chat"
          >
            {"\uD83D\uDCAC"}
          </button>
        )}

        {/* WhatsApp sidebar panel */}
        {whatsappOpen && (
          <div className="whatsapp-sidebar">
            <div className="whatsapp-sidebar-header">
              {/* Close button lives inside the header so it moves with the sidebar */}
              <div className="whatsapp-header-top">
                <h4>WhatsApp</h4>
                <button className="whatsapp-sidebar-close-btn" onClick={() => setWhatsappOpen(false)} title="Close WhatsApp">
                  {"\u00D7"}
                </button>
              </div>
              {whatsappPhone && !editingPhone && (
                <div className="whatsapp-phone-row">
                  <span className="whatsapp-phone-number">{whatsappPhone}</span>
                  <button className="whatsapp-phone-edit-btn" onClick={() => { setEditingPhone(true); setPhoneInput(whatsappPhone); }} title="Change number">✎</button>
                  <button className="whatsapp-phone-remove-btn" onClick={handleRemovePhone} title="Remove number">✕</button>
                </div>
              )}
            </div>

            {/* Phone number setup / edit form */}
            {(!whatsappPhone || editingPhone) && (
              <div className="whatsapp-phone-setup">
                <p className="whatsapp-setup-hint">Enter the contact's WhatsApp number (with country code, e.g. 972501234567)</p>
                <div className="whatsapp-phone-input-row">
                  <input
                    type="tel"
                    placeholder="e.g. 972501234567"
                    value={phoneInput}
                    onChange={(e) => setPhoneInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") handleSetPhone(); }}
                    autoFocus
                  />
                  <button onClick={handleSetPhone} disabled={!phoneInput.trim()}>Save</button>
                  {editingPhone && <button className="whatsapp-cancel-btn" onClick={() => setEditingPhone(false)}>Cancel</button>}
                </div>
              </div>
            )}

            {/* Chat history */}
            {whatsappPhone && !editingPhone && (
              <>
                <div className="whatsapp-sidebar-messages">
                  {whatsappLoading && <div className="whatsapp-loading">Loading chat...</div>}
                  {whatsappError && <div className="whatsapp-error">{whatsappError}</div>}
                  {!whatsappLoading && !whatsappError && whatsappHistory.length === 0 && (
                    <div className="whatsapp-empty">No messages yet.</div>
                  )}
                  {[...whatsappHistory].reverse().map((msg) => (
                    <div key={msg.idMessage} className={`whatsapp-message whatsapp-message-${msg.type}`}>
                      <div className="whatsapp-message-bubble">
                        <p className="whatsapp-message-text">{msg.textMessage || msg.caption || "(media)"}</p>
                      </div>
                      <span className="whatsapp-message-time">
                        {new Date(msg.timestamp * 1000).toLocaleDateString(undefined, { day: "numeric", month: "short" })}{" "}
                        {new Date(msg.timestamp * 1000).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>
                <div className="whatsapp-sidebar-input">
                  <input
                    type="text"
                    placeholder="Write a message..."
                    value={whatsappMessage}
                    onChange={(e) => setWhatsappMessage(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && whatsappMessage.trim()) handleSendMessage(); }}
                    disabled={sendingMessage}
                  />
                  <button onClick={handleSendMessage} disabled={!whatsappMessage.trim() || sendingMessage}>
                    {sendingMessage ? "..." : "Send"}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

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
                <RatingBadge rating={rating} onSetRating={onSetRating} large />
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

            {/* Two-column split: details on left, tags+folders stacked on right */}
            <div className="modal-body-split">
              <div className="modal-body-details">
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

              {/* Right column: tags then folders stacked */}
              <div className="modal-body-organizers">
                {/* Tags section */}
                <div className="modal-tags">
                  <div className="modal-tags-chips">
                    {listingTags.map((t) => (
                      <span key={t.id} className="tag-chip" style={{ background: t.color }}>
                        {t.name}
                        <button className="chip-delete" onClick={() => onRemoveFromTag(t.id)} title="Remove tag">&times;</button>
                      </span>
                    ))}
                  </div>
                  {allTags.filter((t) => !listingTags.find((lt) => lt.id === t.id)).length > 0 && (
                    <select
                      className="modal-tags-select"
                      value=""
                      onChange={(e) => { if (e.target.value) onAddToTag(e.target.value); }}
                    >
                      <option value="">Add tag...</option>
                      {allTags
                        .filter((t) => !listingTags.find((lt) => lt.id === t.id))
                        .map((t) => (
                          <option key={t.id} value={t.id}>{t.name}</option>
                        ))}
                    </select>
                  )}
                  {/* Create new tag: color swatches + name input */}
                  <div className="modal-tags-create">
                    <div className="tag-color-picker">
                      {TAG_PALETTE.map((c) => (
                        <button
                          key={c}
                          className={`tag-palette-btn${newTagColor === c ? " selected" : ""}`}
                          style={{ background: c }}
                          onClick={() => setNewTagColor(c)}
                          title={c}
                        />
                      ))}
                    </div>
                    <div className="tag-create-row">
                      <span className="tag-preview" style={{ background: newTagColor }} />
                      <input
                        type="text"
                        placeholder="New tag name..."
                        value={newTagName}
                        onChange={(e) => setNewTagName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && newTagName.trim()) {
                            onCreateTag(newTagName.trim(), newTagColor);
                            setNewTagName("");
                            setNewTagColor(TAG_PALETTE[0]);
                          }
                        }}
                      />
                      <button
                        className="tag-create-btn"
                        disabled={!newTagName.trim()}
                        onClick={() => {
                          if (newTagName.trim()) {
                            onCreateTag(newTagName.trim(), newTagColor);
                            setNewTagName("");
                            setNewTagColor(TAG_PALETTE[0]);
                          }
                        }}
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>

                {/* Folders section */}
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
              </div>
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
        <div className="lightbox-overlay" onClick={(e) => { e.stopPropagation(); setLightbox(false); }}>
          <button className="lightbox-close" onClick={(e) => { e.stopPropagation(); setLightbox(false); }}>&times;</button>
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
