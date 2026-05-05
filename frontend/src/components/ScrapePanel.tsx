import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { triggerScrape, type ScrapeResult } from "../api";
import type { CityConfig } from "../hooks/useCitySettings";
import type { FacebookCityConfig } from "../hooks/useFacebookCities";
import type { Folder } from "../hooks/useFolders";
import { MultiSelect } from "./MultiSelect";

interface Yad2Filters {
  selectedCityIds: string[];
  min_price?: number;
  max_price?: number;
  min_rooms?: number;
  max_rooms?: number;
  min_floor?: number;
  max_floor?: number;
  min_area?: number;
  max_area?: number;
  property_type?: string;
}

interface FacebookFilters {
  selectedCityId?: string;
  min_price?: number;
  max_price?: number;
}

const NEW_FOLDER_VALUE = "__new__";

function FolderSelector({
  folders,
  selectedFolderId,
  onChange,
  onCreateFolder,
}: {
  folders: Folder[];
  selectedFolderId: string;
  onChange: (id: string) => void;
  onCreateFolder: (name: string) => Folder;
}) {
  const handleChange = (value: string) => {
    if (value === NEW_FOLDER_VALUE) {
      const name = window.prompt("New folder name:");
      if (name?.trim()) {
        const folder = onCreateFolder(name.trim());
        onChange(folder.id);
      }
    } else {
      onChange(value);
    }
  };

  return (
    <>
      <label>Add to Folder</label>
      <select
        value={selectedFolderId}
        onChange={(e) => handleChange(e.target.value)}
      >
        <option value="">No folder</option>
        {folders.map((f) => (
          <option key={f.id} value={f.id}>{f.name}</option>
        ))}
        <option value={NEW_FOLDER_VALUE}>+ New folder...</option>
      </select>
    </>
  );
}

function ScrapeYad2Section({
  onScrapeComplete,
  cityConfigs,
  folders,
  onCreateFolder,
  onAddToFolder,
}: {
  onScrapeComplete: () => void;
  cityConfigs: CityConfig[];
  folders: Folder[];
  onCreateFolder: (name: string) => Folder;
  onAddToFolder: (folderId: string, keys: string[]) => void;
}) {
  const [filters, setFilters] = useState<Yad2Filters>({ selectedCityIds: [] });
  const [targetFolderId, setTargetFolderId] = useState("");

  const mutation = useMutation({
    mutationFn: async () => {
      const cities = filters.selectedCityIds.length > 0
        ? cityConfigs.filter((c) => filters.selectedCityIds.includes(c.id))
        : [undefined]; // one run with no city filter

      const totals: ScrapeResult = {
        total_scraped: 0, total_after_dedup: 0, total_after_filter: 0,
        listings_stored: 0, new_listings: 0, stored_listing_keys: [],
      };

      for (const city of cities) {
        const result = await triggerScrape({
          source: "yad2",
          city: city?.cityCode,
          area: city?.areaCode,
          neighborhood: city?.neighborhoodCode || undefined,
          city_name: city?.name,
          min_price: filters.min_price,
          max_price: filters.max_price,
          min_rooms: filters.min_rooms,
          max_rooms: filters.max_rooms,
          min_floor: filters.min_floor,
          max_floor: filters.max_floor,
          min_area: filters.min_area,
          max_area: filters.max_area,
          property_type: filters.property_type,
        });
        totals.total_scraped += result.total_scraped;
        totals.total_after_dedup += result.total_after_dedup;
        totals.total_after_filter += result.total_after_filter;
        totals.listings_stored += result.listings_stored;
        totals.new_listings += result.new_listings;
        totals.stored_listing_keys.push(...result.stored_listing_keys);
      }
      return totals;
    },
    onSuccess: (result) => {
      if (targetFolderId && result.stored_listing_keys.length > 0) {
        onAddToFolder(targetFolderId, result.stored_listing_keys);
      }
      alert(`Yad2: Scraped ${result.total_scraped} listings.\n${result.new_listings} new listings stored.`);
      onScrapeComplete();
    },
    onError: (err) => { alert(`Yad2 scrape failed: ${err}`); },
  });

  return (
    <div className="scrape-section scrape-section-yad2">
      <h3>Scrape Yad2</h3>

      <label>Cities</label>
      <MultiSelect
        options={cityConfigs.map((c) => ({ id: c.id, label: c.name }))}
        selectedIds={filters.selectedCityIds}
        onChange={(ids) => setFilters((prev) => ({ ...prev, selectedCityIds: ids }))}
        placeholder="Select cities..."
      />

      <label>Price Range (ILS)</label>
      <div className="range-row">
        <input type="number" placeholder="Min" step={500} value={filters.min_price || ""}
          onChange={(e) => setFilters({ ...filters, min_price: e.target.value ? +e.target.value : undefined })} />
        <span>—</span>
        <input type="number" placeholder="Max" step={500} value={filters.max_price || ""}
          onChange={(e) => setFilters({ ...filters, max_price: e.target.value ? +e.target.value : undefined })} />
      </div>

      <label>Rooms</label>
      <div className="range-row">
        <input type="number" placeholder="Min" step="0.5" value={filters.min_rooms || ""}
          onChange={(e) => setFilters({ ...filters, min_rooms: e.target.value ? +e.target.value : undefined })} />
        <span>—</span>
        <input type="number" placeholder="Max" step="0.5" value={filters.max_rooms || ""}
          onChange={(e) => setFilters({ ...filters, max_rooms: e.target.value ? +e.target.value : undefined })} />
      </div>

      <label>Area (m²)</label>
      <div className="range-row">
        <input type="number" placeholder="Min" value={filters.min_area || ""}
          onChange={(e) => setFilters({ ...filters, min_area: e.target.value ? +e.target.value : undefined })} />
        <span>—</span>
        <input type="number" placeholder="Max" value={filters.max_area || ""}
          onChange={(e) => setFilters({ ...filters, max_area: e.target.value ? +e.target.value : undefined })} />
      </div>

      <label>Floor</label>
      <div className="range-row">
        <input type="number" placeholder="Min" value={filters.min_floor || ""}
          onChange={(e) => setFilters({ ...filters, min_floor: e.target.value ? +e.target.value : undefined })} />
        <span>—</span>
        <input type="number" placeholder="Max" value={filters.max_floor || ""}
          onChange={(e) => setFilters({ ...filters, max_floor: e.target.value ? +e.target.value : undefined })} />
      </div>

      <label>Property Type</label>
      <select
        value={filters.property_type || ""}
        onChange={(e) => setFilters({ ...filters, property_type: e.target.value || undefined })}
      >
        <option value="">All Types</option>
        {[
          { value: "apartment", label: "Apartment" },
          { value: "garden_apartment", label: "Garden Apartment" },
          { value: "house", label: "House / Cottage" },
          { value: "penthouse", label: "Penthouse" },
          { value: "studio", label: "Studio / Loft" },
          { value: "duplex", label: "Duplex" },
          { value: "roof_apartment", label: "Roof Apartment" },
          { value: "unit", label: "Housing Unit" },
        ].map((t) => (
          <option key={t.value} value={t.value}>{t.label}</option>
        ))}
      </select>

      <FolderSelector
        folders={folders}
        selectedFolderId={targetFolderId}
        onChange={setTargetFolderId}
        onCreateFolder={onCreateFolder}
      />

      <button className="btn-scrape btn-scrape-yad2" onClick={() => {
        if (!targetFolderId && !window.confirm("No folder selected. Scrape without adding to a folder?")) return;
        mutation.mutate();
      }} disabled={mutation.isPending}>
        {mutation.isPending ? "Scraping..." : "Scrape Yad2"}
      </button>
    </div>
  );
}

function ScrapeFacebookSection({
  onScrapeComplete,
  fbCities,
  folders,
  onCreateFolder,
  onAddToFolder,
}: {
  onScrapeComplete: () => void;
  fbCities: FacebookCityConfig[];
  folders: Folder[];
  onCreateFolder: (name: string) => Folder;
  onAddToFolder: (folderId: string, keys: string[]) => void;
}) {
  const [filters, setFilters] = useState<FacebookFilters>({});
  const [openBrowser, setOpenBrowser] = useState(true);
  const [targetFolderId, setTargetFolderId] = useState("");

  const selectedCity = fbCities.find((c) => c.id === filters.selectedCityId);

  const mutation = useMutation({
    mutationFn: () => triggerScrape({
      source: "facebook",
      fb_latitude: selectedCity?.latitude,
      fb_longitude: selectedCity?.longitude,
      fb_radius_km: selectedCity?.radiusKm,
      min_price: filters.min_price,
      max_price: filters.max_price,
      headless: !openBrowser,
    }),
    onSuccess: (result) => {
      if (targetFolderId && result.stored_listing_keys.length > 0) {
        onAddToFolder(targetFolderId, result.stored_listing_keys);
      }
      alert(`Facebook: Scraped ${result.total_scraped} listings.\n${result.new_listings} new listings stored.`);
      onScrapeComplete();
    },
    onError: (err) => { alert(`Facebook scrape failed: ${err}`); },
  });

  return (
    <div className="scrape-section scrape-section-facebook">
      <h3>Scrape Facebook</h3>

      <label>Location</label>
      <select
        value={filters.selectedCityId || ""}
        onChange={(e) => setFilters({ ...filters, selectedCityId: e.target.value || undefined })}
      >
        <option value="">Select a location...</option>
        {fbCities.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} ({c.radiusKm} km)
          </option>
        ))}
      </select>
      {fbCities.length === 0 && (
        <p className="helper-text">
          No Facebook locations configured. Add them in Settings &gt; Facebook Cities.
        </p>
      )}

      <label>Price Range (ILS)</label>
      <div className="range-row">
        <input type="number" placeholder="Min" step={500} value={filters.min_price || ""}
          onChange={(e) => setFilters({ ...filters, min_price: e.target.value ? +e.target.value : undefined })} />
        <span>—</span>
        <input type="number" placeholder="Max" step={500} value={filters.max_price || ""}
          onChange={(e) => setFilters({ ...filters, max_price: e.target.value ? +e.target.value : undefined })} />
      </div>

      <label className="checkbox-label browser-toggle">
        <input
          type="checkbox"
          checked={openBrowser}
          onChange={(e) => setOpenBrowser(e.target.checked)}
        />
        Open browser for login
      </label>
      {openBrowser && (
        <p className="helper-text">
          A Chrome window will open. Log in to Facebook, then scraping starts automatically.
        </p>
      )}

      <FolderSelector
        folders={folders}
        selectedFolderId={targetFolderId}
        onChange={setTargetFolderId}
        onCreateFolder={onCreateFolder}
      />

      <button className="btn-scrape btn-scrape-facebook" onClick={() => {
        if (!selectedCity && !window.confirm("No location selected. Scrape with default location?")) return;
        if (!targetFolderId && !window.confirm("No folder selected. Scrape without adding to a folder?")) return;
        mutation.mutate();
      }} disabled={mutation.isPending}>
        {mutation.isPending ? (openBrowser ? "Waiting for login..." : "Scraping...") : "Scrape Facebook"}
      </button>
    </div>
  );
}

type ScrapeTab = "yad2" | "facebook";

export function ScrapeTabSwitcher({
  onScrapeComplete,
  cityConfigs,
  fbCities,
  folders,
  onCreateFolder,
  onAddToFolder,
}: {
  onScrapeComplete: () => void;
  cityConfigs: CityConfig[];
  fbCities: FacebookCityConfig[];
  folders: Folder[];
  onCreateFolder: (name: string) => Folder;
  onAddToFolder: (folderId: string, keys: string[]) => void;
}) {
  const [activeTab, setActiveTab] = useState<ScrapeTab>("yad2");

  return (
    <div>
      <div className="scrape-tabs">
        <button
          className={`scrape-tab scrape-tab-yad2${activeTab === "yad2" ? " active" : ""}`}
          onClick={() => setActiveTab("yad2")}
        >
          Yad2
        </button>
        <button
          className={`scrape-tab scrape-tab-facebook${activeTab === "facebook" ? " active" : ""}`}
          onClick={() => setActiveTab("facebook")}
        >
          Facebook
        </button>
      </div>

      {activeTab === "yad2" && (
        <ScrapeYad2Section
          onScrapeComplete={onScrapeComplete}
          cityConfigs={cityConfigs}
          folders={folders}
          onCreateFolder={onCreateFolder}
          onAddToFolder={onAddToFolder}
        />
      )}
      {activeTab === "facebook" && (
        <ScrapeFacebookSection
          onScrapeComplete={onScrapeComplete}
          fbCities={fbCities}
          folders={folders}
          onCreateFolder={onCreateFolder}
          onAddToFolder={onAddToFolder}
        />
      )}
    </div>
  );
}
