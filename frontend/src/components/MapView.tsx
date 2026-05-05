import { useState } from "react";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Listing } from "../api";

// Fix Leaflet default marker icons in bundled environments
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});
L.Marker.prototype.options.icon = defaultIcon;

function timeAgo(dateStr: string): string {
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  return `${diffDays}d ago`;
}

function MapPreviewSidebar({
  listing,
  onOpen,
}: {
  listing: Listing;
  onOpen: () => void;
}) {
  const priceStr = listing.price
    ? `${listing.price.toLocaleString()} ${listing.currency === "ILS" ? "\u20aa" : "$"}`
    : "Price N/A";

  const priceSqm = listing.price && listing.area_sqm
    ? `${Math.round(listing.price / listing.area_sqm).toLocaleString()} \u20aa/m\u00b2`
    : null;

  const postedAgo = listing.posted_at
    ? timeAgo(listing.posted_at)
    : listing.first_seen_at
      ? timeAgo(listing.first_seen_at)
      : null;

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

  return (
    <div className="map-preview-sidebar">
      {listing.image_urls.length > 0 && (
        <img
          src={listing.image_urls[0]}
          alt="Listing"
          className="map-preview-image"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
      )}
      <div className="map-preview-body">
        <div className="map-preview-top-row">
          <div className="map-preview-price">{priceStr}</div>
          <div className="map-preview-badges">
            {postedAgo && <span className="freshness-badge">{postedAgo}</span>}
            <span className={`source-badge source-${listing.source}`}>{listing.source}</span>
          </div>
        </div>
        {priceSqm && <div className="map-preview-price-sqm">{priceSqm}</div>}

        <h4 className="map-preview-title">
          {listing.rooms && `${listing.rooms} rooms`}
          {listing.rooms && listing.city && " in "}
          {listing.city}
        </h4>

        <div className="map-preview-details">
          {listing.area_sqm && <span>{listing.area_sqm} m\u00b2</span>}
          {listing.street && (
            <span>{listing.street}{listing.house_number ? ` ${listing.house_number}` : ""}</span>
          )}
          {listing.neighborhood && <span>{listing.neighborhood}</span>}
          {listing.floor != null && (
            <span>Floor {listing.floor}{listing.total_floors ? `/${listing.total_floors}` : ""}</span>
          )}
          {listing.property_type && <span>{listing.property_type}</span>}
          {listing.entry_date && <span>Move in: {listing.entry_date}</span>}
        </div>

        {features.length > 0 && (
          <div className="map-preview-features">
            {features.map((f) => (
              <span key={f as string} className="feature-tag">{f}</span>
            ))}
          </div>
        )}

        {listing.description && (
          <p className="map-preview-description">
            {listing.description.length > 200
              ? listing.description.slice(0, 200) + "..."
              : listing.description}
          </p>
        )}

        <div className="map-preview-contact">
          {listing.contact_name && <span>{listing.contact_name}</span>}
          {listing.contact_phone && (
            <a href={`tel:${listing.contact_phone}`} className="contact-phone">
              {listing.contact_phone}
            </a>
          )}
        </div>

        <div className="map-preview-actions">
          <button className="map-preview-open" onClick={onOpen}>
            View Details
          </button>
          {listing.latitude != null && listing.longitude != null && (
            <a
              href={`https://www.google.com/maps?q=${listing.latitude},${listing.longitude}`}
              target="_blank"
              rel="noopener noreferrer"
              className="map-preview-gmaps"
            >
              Open on Google Maps
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

export function MapView({
  listings,
  onSelectListing,
}: {
  listings: Listing[];
  onSelectListing: (listing: Listing) => void;
}) {
  const [hoveredListing, setHoveredListing] = useState<Listing | null>(null);
  const geoListings = listings.filter((l) => l.latitude && l.longitude);

  if (geoListings.length === 0) {
    return (
      <div className="map-empty">
        No listings with location data to display on map.
      </div>
    );
  }

  const center: [number, number] = [
    geoListings.reduce((s, l) => s + l.latitude!, 0) / geoListings.length,
    geoListings.reduce((s, l) => s + l.longitude!, 0) / geoListings.length,
  ];

  return (
    <div className="map-container">
      <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; Google Maps'
          url="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
        />
        {geoListings.map((listing) => (
          <Marker
            key={`${listing.source}-${listing.source_id}`}
            position={[listing.latitude!, listing.longitude!]}
            eventHandlers={{
              mouseover: () => setHoveredListing(listing),
              click: () => onSelectListing(listing),
            }}
          />
        ))}
      </MapContainer>
      {hoveredListing && (
        <MapPreviewSidebar
          listing={hoveredListing}
          onOpen={() => onSelectListing(hoveredListing)}
        />
      )}
    </div>
  );
}
