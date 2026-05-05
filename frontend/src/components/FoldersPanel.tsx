import { useState } from "react";
import type { Listing } from "../api";
import type { Folder } from "../hooks/useFolders";

function FolderContents({
  folder,
  listings,
  onRemove,
  onClear,
  onBack,
}: {
  folder: Folder;
  listings: Listing[];
  onRemove: (listingId: string) => void;
  onClear: () => void;
  onBack: () => void;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const listingMap = new Map(
    listings.map((l) => [`${l.source}-${l.source_id}`, l]),
  );

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setSelected(new Set(folder.listingIds));
  };

  const selectNone = () => setSelected(new Set());

  const removeSelected = () => {
    for (const id of selected) onRemove(id);
    setSelected(new Set());
  };

  return (
    <div className="folder-contents">
      <div className="folder-contents-header">
        <button className="folder-back-btn" onClick={onBack}>
          {"← Back"}
        </button>
        <h3 className="folder-contents-title">{folder.name}</h3>
        <span className="folder-contents-count">
          {folder.listingIds.length} listing{folder.listingIds.length !== 1 ? "s" : ""}
        </span>
      </div>

      {folder.listingIds.length > 0 && (
        <div className="folder-contents-toolbar">
          <div className="folder-select-actions">
            <button className="folder-toolbar-btn" onClick={selectAll}>Select All</button>
            {selected.size > 0 && (
              <button className="folder-toolbar-btn" onClick={selectNone}>Deselect</button>
            )}
          </div>
          <div className="folder-bulk-actions">
            {selected.size > 0 && (
              <button className="folder-toolbar-btn danger" onClick={removeSelected}>
                Remove ({selected.size})
              </button>
            )}
            <button className="folder-toolbar-btn danger" onClick={onClear}>
              Delete All
            </button>
          </div>
        </div>
      )}

      <div className="folder-contents-list">
        {folder.listingIds.map((listingId) => {
          const listing = listingMap.get(listingId);
          const isSelected = selected.has(listingId);

          return (
            <div
              key={listingId}
              className={`folder-listing-row${isSelected ? " selected" : ""}`}
            >
              <label className="folder-listing-checkbox">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleSelect(listingId)}
                />
              </label>

              {listing ? (
                <div className="folder-listing-info">
                  <div className="folder-listing-main">
                    <span className="folder-listing-price">
                      {listing.price
                        ? `${listing.price.toLocaleString()} \u20aa`
                        : "N/A"}
                    </span>
                    <span className="folder-listing-desc">
                      {listing.rooms && `${listing.rooms}r`}
                      {listing.city && ` ${listing.city}`}
                      {listing.neighborhood && ` · ${listing.neighborhood}`}
                    </span>
                  </div>
                  <div className="folder-listing-meta">
                    {listing.area_sqm && <span>{listing.area_sqm}m²</span>}
                    {listing.floor != null && <span>Floor {listing.floor}</span>}
                    <span className={`source-badge source-${listing.source}`}>
                      {listing.source}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="folder-listing-info">
                  <span className="folder-listing-unknown">{listingId}</span>
                </div>
              )}

              <button
                className="folder-listing-remove"
                onClick={() => onRemove(listingId)}
                title="Remove from folder"
              >
                {"×"}
              </button>
            </div>
          );
        })}
      </div>

      {folder.listingIds.length === 0 && (
        <div className="folder-empty">
          <p>This folder is empty.</p>
          <p>Add listings from the card or detail view.</p>
        </div>
      )}
    </div>
  );
}

export function FoldersPanel({
  folders,
  activeFolder,
  onSetActiveFolder,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  onRemoveFromFolder,
  onClearFolder,
  listings,
}: {
  folders: Folder[];
  activeFolder: string | null;
  onSetActiveFolder: (id: string | null) => void;
  onCreateFolder: (name: string) => void;
  onRenameFolder: (id: string, name: string) => void;
  onDeleteFolder: (id: string) => void;
  onRemoveFromFolder: (folderId: string, listingId: string) => void;
  onClearFolder: (folderId: string) => void;
  listings: Listing[];
}) {
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [viewingFolderId, setViewingFolderId] = useState<string | null>(null);

  const handleCreate = () => {
    if (newName.trim()) {
      onCreateFolder(newName.trim());
      setNewName("");
    }
  };

  const viewingFolder = viewingFolderId
    ? folders.find((f) => f.id === viewingFolderId)
    : null;

  // Show folder contents list view
  if (viewingFolder) {
    return (
      <FolderContents
        folder={viewingFolder}
        listings={listings}
        onRemove={(listingId) => onRemoveFromFolder(viewingFolder.id, listingId)}
        onClear={() => onClearFolder(viewingFolder.id)}
        onBack={() => setViewingFolderId(null)}
      />
    );
  }

  // Show folder list view
  return (
    <div className="folders-panel">
      <h3 className="panel-title">Folders</h3>

      <div className="folder-create-form">
        <input
          type="text"
          placeholder="Create new folder..."
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
        />
        <button onClick={handleCreate} disabled={!newName.trim()}>
          Create
        </button>
      </div>

      <div className="folder-list">
        <button
          className={`folder-card${activeFolder === null ? " active" : ""}`}
          onClick={() => onSetActiveFolder(null)}
        >
          <span className="folder-card-icon">{"📋"}</span>
          <div className="folder-card-info">
            <span className="folder-card-name">All Listings</span>
            <span className="folder-card-meta">No filter applied</span>
          </div>
        </button>

        <button
          className={`folder-card${activeFolder === "__uncategorized__" ? " active" : ""}`}
          onClick={() => onSetActiveFolder(activeFolder === "__uncategorized__" ? null : "__uncategorized__")}
        >
          <span className="folder-card-icon">{"📭"}</span>
          <div className="folder-card-info">
            <span className="folder-card-name">Uncategorized</span>
            <span className="folder-card-meta">Not in any folder</span>
          </div>
        </button>

        {folders.map((f) => (
          <div
            key={f.id}
            className={`folder-card${activeFolder === f.id ? " active" : ""}`}
          >
            {editingId === f.id ? (
              <div className="folder-card-edit">
                <input
                  type="text"
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && editingName.trim()) {
                      onRenameFolder(f.id, editingName.trim());
                      setEditingId(null);
                    }
                    if (e.key === "Escape") setEditingId(null);
                  }}
                  autoFocus
                />
                <div className="folder-card-edit-actions">
                  <button
                    className="folder-action-btn save"
                    onClick={() => {
                      if (editingName.trim()) {
                        onRenameFolder(f.id, editingName.trim());
                        setEditingId(null);
                      }
                    }}
                  >
                    Save
                  </button>
                  <button
                    className="folder-action-btn cancel"
                    onClick={() => setEditingId(null)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div
                  className="folder-card-main"
                  onClick={() => onSetActiveFolder(f.id === activeFolder ? null : f.id)}
                >
                  <span className="folder-card-icon">{"\uD83D\uDCC2"}</span>
                  <div className="folder-card-info">
                    <span className="folder-card-name">{f.name}</span>
                    <span className="folder-card-meta">
                      {f.listingIds.length} listing{f.listingIds.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
                <div className="folder-card-actions">
                  <button
                    className="folder-action-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setViewingFolderId(f.id);
                    }}
                    title="View listings"
                  >
                    {"👁️"}
                  </button>
                  <button
                    className="folder-action-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingId(f.id);
                      setEditingName(f.name);
                    }}
                    title="Rename"
                  >
                    {"✏️"}
                  </button>
                  <button
                    className="folder-action-btn delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteFolder(f.id);
                    }}
                    title="Delete"
                  >
                    {"🗑️"}
                  </button>
                </div>
              </>
            )}
          </div>
        ))}

        {folders.length === 0 && (
          <div className="folder-empty">
            <p>No folders yet.</p>
            <p>Create one above to start organizing your listings.</p>
          </div>
        )}
      </div>
    </div>
  );
}
