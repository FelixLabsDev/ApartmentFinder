import React, { useState } from "react";
import { createPortal } from "react-dom";
import { MapContainer, TileLayer, Marker, Circle, useMapEvents } from "react-leaflet";
import { clearAllListings } from "../api";
import type { CityConfig } from "../hooks/useCitySettings";
import { parseYad2Url } from "../hooks/useCitySettings";
import type { FacebookCityConfig } from "../hooks/useFacebookCities";

type SettingsCategory = "cities" | "facebook" | "data";

function CityCard({
  city,
  onUpdate,
  onRemove,
}: {
  city: CityConfig;
  onUpdate: (updates: Partial<Omit<CityConfig, "id">>) => void;
  onRemove: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(city.name);
  const [editRegion, setEditRegion] = useState(city.region);
  const [editAreaCode, setEditAreaCode] = useState(city.areaCode);
  const [editCityCode, setEditCityCode] = useState(city.cityCode);
  const [editNhCode, setEditNhCode] = useState(city.neighborhoodCode);

  const saveEdit = () => {
    if (editName.trim() && editRegion.trim() && editAreaCode.trim() && editCityCode.trim()) {
      onUpdate({
        name: editName.trim(),
        region: editRegion.trim(),
        areaCode: editAreaCode.trim(),
        cityCode: editCityCode.trim(),
        neighborhoodCode: editNhCode.trim(),
      });
      setEditing(false);
    }
  };

  const startEdit = () => {
    setEditName(city.name);
    setEditRegion(city.region);
    setEditAreaCode(city.areaCode);
    setEditCityCode(city.cityCode);
    setEditNhCode(city.neighborhoodCode);
    setEditing(true);
  };

  return (
    <div className="city-card">
      {editing ? (
        <div className="city-card-edit">
          <div className="city-edit-fields">
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              placeholder="City name"
              autoFocus
            />
            <input
              type="text"
              value={editRegion}
              onChange={(e) => setEditRegion(e.target.value)}
              placeholder="Region (e.g. tel-aviv-area)"
            />
            <input
              type="text"
              value={editAreaCode}
              onChange={(e) => setEditAreaCode(e.target.value)}
              placeholder="Area code"
              className="code-input"
            />
            <input
              type="text"
              value={editCityCode}
              onChange={(e) => setEditCityCode(e.target.value)}
              placeholder="City code"
              className="code-input"
            />
            <input
              type="text"
              value={editNhCode}
              onChange={(e) => setEditNhCode(e.target.value)}
              placeholder="Neighborhood code"
              className="code-input"
            />
          </div>
          <div className="city-edit-actions">
            <button className="btn-sm btn-save" onClick={saveEdit}>Save</button>
            <button className="btn-sm btn-cancel" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <div className="city-card-header">
          <div className="city-card-info">
            <span className="city-card-name">{city.name}</span>
            <span className="city-card-codes">
              {city.region} · area={city.areaCode} · city={city.cityCode}
              {city.neighborhoodCode && ` · nh=${city.neighborhoodCode}`}
            </span>
            <a
              className="city-card-link"
              href={`https://www.yad2.co.il/realestate/rent/${city.region}?area=${city.areaCode}&city=${city.cityCode}${city.neighborhoodCode ? `&neighborhood=${city.neighborhoodCode}` : ""}`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              Open on Yad2
            </a>
          </div>
          <div className="city-card-actions">
            <button
              className="btn-sm btn-edit"
              onClick={startEdit}
              title="Edit"
            >
              {"\u270F\uFE0F"}
            </button>
            <button
              className="btn-sm btn-delete"
              onClick={onRemove}
              title="Delete"
            >
              {"\uD83D\uDDD1\uFE0F"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MapClickHandler({ onClick }: { onClick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

function FacebookCityCard({
  city,
  onUpdate,
  onRemove,
}: {
  city: FacebookCityConfig;
  onUpdate: (updates: Partial<Omit<FacebookCityConfig, "id">>) => void;
  onRemove: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(city.name);
  const [editLat, setEditLat] = useState(String(city.latitude));
  const [editLng, setEditLng] = useState(String(city.longitude));
  const [editRadius, setEditRadius] = useState(city.radiusKm);

  const saveEdit = () => {
    const lat = parseFloat(editLat);
    const lng = parseFloat(editLng);
    if (editName.trim() && !isNaN(lat) && !isNaN(lng) && editRadius > 0) {
      onUpdate({ name: editName.trim(), latitude: lat, longitude: lng, radiusKm: editRadius });
      setEditing(false);
    }
  };

  const startEdit = () => {
    setEditName(city.name);
    setEditLat(String(city.latitude));
    setEditLng(String(city.longitude));
    setEditRadius(city.radiusKm);
    setEditing(true);
  };

  return (
    <div className="city-card">
      {editing ? (
        <div className="city-card-edit">
          <div className="city-edit-fields">
            <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)} placeholder="Name" autoFocus />
            <input type="text" value={editLat} onChange={(e) => setEditLat(e.target.value)} placeholder="Latitude" className="code-input" />
            <input type="text" value={editLng} onChange={(e) => setEditLng(e.target.value)} placeholder="Longitude" className="code-input" />
            <div className="fb-radius-edit">
              <label>Radius: {editRadius} km</label>
              <input type="range" min={1} max={50} value={editRadius} onChange={(e) => setEditRadius(+e.target.value)} />
            </div>
          </div>
          <div className="city-edit-actions">
            <button className="btn-sm btn-save" onClick={saveEdit}>Save</button>
            <button className="btn-sm btn-cancel" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <div className="city-card-header">
          <div className="city-card-info">
            <span className="city-card-name">{city.name}</span>
            <span className="city-card-codes">
              {city.latitude.toFixed(4)}, {city.longitude.toFixed(4)} · {city.radiusKm} km radius
            </span>
          </div>
          <div className="city-card-actions">
            <button className="btn-sm btn-edit" onClick={startEdit} title="Edit">{"\u270F\uFE0F"}</button>
            <button className="btn-sm btn-delete" onClick={onRemove} title="Delete">{"\uD83D\uDDD1\uFE0F"}</button>
          </div>
        </div>
      )}
    </div>
  );
}

export function SettingsModal({
  cities,
  onAddCity,
  onUpdateCity,
  onRemoveCity,
  fbCities,
  onAddFbCity,
  onUpdateFbCity,
  onRemoveFbCity,
  onClearListings,
  onClose,
}: {
  cities: CityConfig[];
  onAddCity: (city: Omit<CityConfig, "id">) => CityConfig;
  onUpdateCity: (id: string, updates: Partial<Omit<CityConfig, "id">>) => void;
  onRemoveCity: (id: string) => void;
  fbCities: FacebookCityConfig[];
  onAddFbCity: (city: Omit<FacebookCityConfig, "id">) => FacebookCityConfig;
  onUpdateFbCity: (id: string, updates: Partial<Omit<FacebookCityConfig, "id">>) => void;
  onRemoveFbCity: (id: string) => void;
  onClearListings: () => void;
  onClose: () => void;
}) {
  const [activeCategory, setActiveCategory] = useState<SettingsCategory>("cities");
  const [newName, setNewName] = useState("");
  const [newRegion, setNewRegion] = useState("");
  const [newAreaCode, setNewAreaCode] = useState("");
  const [newCityCode, setNewCityCode] = useState("");
  const [newNhCode, setNewNhCode] = useState("");
  const [urlInput, setUrlInput] = useState("");
  const [urlError, setUrlError] = useState("");

  // Facebook city form state
  const [fbName, setFbName] = useState("");
  const [fbLat, setFbLat] = useState<number | null>(null);
  const [fbLng, setFbLng] = useState<number | null>(null);
  const [fbRadius, setFbRadius] = useState(10);

  const canAdd = newName.trim() && newRegion.trim() && newAreaCode.trim() && newCityCode.trim();
  const canAddFb = fbName.trim() && fbLat !== null && fbLng !== null;

  const handleAddCity = () => {
    if (canAdd) {
      onAddCity({
        name: newName.trim(),
        region: newRegion.trim(),
        areaCode: newAreaCode.trim(),
        cityCode: newCityCode.trim(),
        neighborhoodName: "",
        neighborhoodCode: newNhCode.trim(),
      });
      setNewName("");
      setNewRegion("");
      setNewAreaCode("");
      setNewCityCode("");
      setNewNhCode("");
      setUrlInput("");
      setUrlError("");
    }
  };

  const handleUrlPaste = (url: string) => {
    setUrlInput(url);
    setUrlError("");
    if (!url.trim()) return;

    const parsed = parseYad2Url(url.trim());
    if (parsed) {
      setNewRegion(parsed.region);
      setNewAreaCode(parsed.areaCode);
      setNewCityCode(parsed.cityCode);
      if (parsed.neighborhoodCode) {
        setNewNhCode(parsed.neighborhoodCode);
      }
    } else {
      setUrlError("Could not parse Yad2 URL. Expected format: https://www.yad2.co.il/realestate/rent/{region}?area=...&city=...");
    }
  };

  return createPortal(
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-content" onClick={(e) => e.stopPropagation()}>
        <button className="settings-close" onClick={onClose}>
          {"\u00D7"}
        </button>

        <div className="settings-sidebar">
          <h3 className="settings-sidebar-title">Settings</h3>
          <button
            className={`settings-category-btn${activeCategory === "cities" ? " active" : ""}`}
            onClick={() => setActiveCategory("cities")}
          >
            Cities
          </button>
          <button
            className={`settings-category-btn${activeCategory === "facebook" ? " active" : ""}`}
            onClick={() => setActiveCategory("facebook")}
          >
            Facebook Cities
          </button>
          <button
            className={`settings-category-btn${activeCategory === "data" ? " active" : ""}`}
            onClick={() => setActiveCategory("data")}
          >
            Data
          </button>
        </div>

        <div className="settings-body">
          {activeCategory === "cities" && (
            <>
              <h3 className="settings-section-title">Cities</h3>
              <p className="settings-hint">
                Paste a Yad2 URL to auto-fill, or enter codes manually.
              </p>

              <div className="city-url-input">
                <label>Paste Yad2 URL</label>
                <input
                  type="text"
                  value={urlInput}
                  onChange={(e) => handleUrlPaste(e.target.value)}
                  placeholder="https://www.yad2.co.il/realestate/rent/tel-aviv-area?area=11&city=0565&neighborhood=1252"
                />
                {urlError && <span className="url-error">{urlError}</span>}
              </div>

              <div className="city-add-form">
                <div className="city-add-row">
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="City name *"
                    onKeyDown={(e) => e.key === "Enter" && handleAddCity()}
                  />
                  <input
                    type="text"
                    value={newRegion}
                    onChange={(e) => setNewRegion(e.target.value)}
                    placeholder="Region *"
                    onKeyDown={(e) => e.key === "Enter" && handleAddCity()}
                  />
                  <input
                    type="text"
                    value={newAreaCode}
                    onChange={(e) => setNewAreaCode(e.target.value)}
                    placeholder="Area *"
                    onKeyDown={(e) => e.key === "Enter" && handleAddCity()}
                    className="code-input"
                  />
                  <input
                    type="text"
                    value={newCityCode}
                    onChange={(e) => setNewCityCode(e.target.value)}
                    placeholder="City code *"
                    onKeyDown={(e) => e.key === "Enter" && handleAddCity()}
                    className="code-input"
                  />
                </div>
                <div className="city-add-row">
                  <input
                    type="text"
                    value={newNhCode}
                    onChange={(e) => setNewNhCode(e.target.value)}
                    placeholder="Neighborhood code"
                    onKeyDown={(e) => e.key === "Enter" && handleAddCity()}
                    className="code-input"
                  />
                  <button
                    className="btn-sm btn-add"
                    onClick={handleAddCity}
                    disabled={!canAdd}
                  >
                    Add City
                  </button>
                </div>
              </div>

              <div className="city-list">
                {cities.map((city) => (
                  <CityCard
                    key={city.id}
                    city={city}
                    onUpdate={(updates) => onUpdateCity(city.id, updates)}
                    onRemove={() => onRemoveCity(city.id)}
                  />
                ))}
                {cities.length === 0 && (
                  <div className="settings-empty">
                    <p>No cities configured yet.</p>
                    <p>Paste a Yad2 URL above or enter codes manually.</p>
                  </div>
                )}
              </div>
            </>
          )}

          {activeCategory === "facebook" && (
            <>
              <h3 className="settings-section-title">Facebook Cities</h3>
              <p className="settings-hint">
                Click on the map to place a pin, then give it a name and set a search radius.
              </p>

              <div className="fb-map-picker">
                <MapContainer
                  center={[31.5, 34.8]}
                  zoom={8}
                  style={{ height: 280, width: "100%", borderRadius: 8 }}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <MapClickHandler onClick={(lat, lng) => { setFbLat(lat); setFbLng(lng); }} />
                  {fbLat !== null && fbLng !== null && (
                    <>
                      <Marker position={[fbLat, fbLng]} />
                      <Circle
                        center={[fbLat, fbLng]}
                        radius={fbRadius * 1000}
                        pathOptions={{ color: "#3182ce", fillColor: "#3182ce", fillOpacity: 0.12, weight: 2 }}
                      />
                    </>
                  )}
                  {fbCities.map((c) => (
                    <React.Fragment key={c.id}>
                      <Marker position={[c.latitude, c.longitude]} />
                      <Circle
                        center={[c.latitude, c.longitude]}
                        radius={c.radiusKm * 1000}
                        pathOptions={{ color: "#718096", fillColor: "#718096", fillOpacity: 0.08, weight: 1, dashArray: "4 4" }}
                      />
                    </React.Fragment>
                  ))}
                </MapContainer>
              </div>

              <div className="fb-add-form">
                <div className="city-add-row">
                  <input
                    type="text"
                    value={fbName}
                    onChange={(e) => setFbName(e.target.value)}
                    placeholder="Location name *"
                  />
                  <input
                    type="text"
                    value={fbLat !== null ? fbLat.toFixed(4) : ""}
                    onChange={(e) => { const v = parseFloat(e.target.value); if (!isNaN(v)) setFbLat(v); }}
                    placeholder="Latitude"
                    className="code-input"
                  />
                  <input
                    type="text"
                    value={fbLng !== null ? fbLng.toFixed(4) : ""}
                    onChange={(e) => { const v = parseFloat(e.target.value); if (!isNaN(v)) setFbLng(v); }}
                    placeholder="Longitude"
                    className="code-input"
                  />
                </div>
                <div className="city-add-row">
                  <div className="fb-radius-control">
                    <label>Radius: {fbRadius} km</label>
                    <input
                      type="range"
                      min={1}
                      max={50}
                      value={fbRadius}
                      onChange={(e) => setFbRadius(+e.target.value)}
                    />
                  </div>
                  <button
                    className="btn-sm btn-add"
                    disabled={!canAddFb}
                    onClick={() => {
                      if (canAddFb) {
                        onAddFbCity({ name: fbName.trim(), latitude: fbLat!, longitude: fbLng!, radiusKm: fbRadius });
                        setFbName("");
                        setFbLat(null);
                        setFbLng(null);
                        setFbRadius(10);
                      }
                    }}
                  >
                    Add Location
                  </button>
                </div>
              </div>

              <div className="city-list">
                {fbCities.map((city) => (
                  <FacebookCityCard
                    key={city.id}
                    city={city}
                    onUpdate={(updates) => onUpdateFbCity(city.id, updates)}
                    onRemove={() => onRemoveFbCity(city.id)}
                  />
                ))}
                {fbCities.length === 0 && (
                  <div className="settings-empty">
                    <p>No Facebook locations configured yet.</p>
                    <p>Click on the map above to place a pin.</p>
                  </div>
                )}
              </div>
            </>
          )}

          {activeCategory === "data" && (
            <>
              <h3 className="settings-section-title">Data Management</h3>
              <div className="data-section">
                <p className="settings-hint">
                  Clear all stored listings to start fresh. This cannot be undone.
                </p>
                <button
                  className="btn-danger"
                  onClick={async () => {
                    if (window.confirm("Are you sure you want to delete ALL listings? This cannot be undone.")) {
                      try {
                        const result = await clearAllListings();
                        alert(`Deleted ${result.deleted} listings.`);
                        onClearListings();
                      } catch (err) {
                        alert(`Failed to clear listings: ${err}`);
                      }
                    }
                  }}
                >
                  Clear All Listings
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
