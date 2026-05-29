import { useQuery } from "@tanstack/react-query";
import { type Filters, fetchNeighborhoods } from "../api";
import type { CityConfig } from "../hooks/useCitySettings";
import { RATING_LEVELS } from "../hooks/useListingRatings";
import type { Tag } from "../hooks/useListingTags";
import { MultiSelect } from "./MultiSelect";

export function DisplayFilters({
  filters,
  setFilters,
  minRatingFilter,
  onSetMinRatingFilter,
  hiddenRatings,
  onSetHiddenRatings,
  hiddenTagIds,
  onSetHiddenTagIds,
  tags,
  cityConfigs,
}: {
  filters: Filters;
  setFilters: (f: Filters) => void;
  minRatingFilter: number;
  onSetMinRatingFilter: (n: number) => void;
  hiddenRatings: string[];
  onSetHiddenRatings: (v: string[]) => void;
  hiddenTagIds: string[];
  onSetHiddenTagIds: (v: string[]) => void;
  tags: Tag[];
  cityConfigs: CityConfig[];
}) {
  // Parse selected city names from comma-separated filter string
  const selectedCityNames = filters.city ? filters.city.split(",") : [];
  const selectedCityIds = cityConfigs
    .filter((c) => selectedCityNames.includes(c.name))
    .map((c) => c.id);

  const singleCity = selectedCityNames.length === 1 ? selectedCityNames[0] : undefined;

  const { data: neighborhoods } = useQuery({
    queryKey: ["neighborhoods", singleCity],
    queryFn: () => fetchNeighborhoods(singleCity!),
    enabled: !!singleCity,
    staleTime: 60_000,
  });

  return (
    <div className="display-filters-section">
      <h3 className="panel-title">Filters</h3>

      <label>Source</label>
      <div className="checkbox-group">
        {[
          { value: "yad2", label: "Yad2" },
          { value: "facebook", label: "Facebook" },
          { value: "telegram", label: "Telegram" },
        ].map(({ value, label }) => {
          const selected = filters.source ? filters.source.split(",") : [];
          const isChecked = selected.includes(value);
          return (
            <label key={value} className="checkbox-label">
              <input
                type="checkbox"
                checked={isChecked}
                onChange={(e) => {
                  let next: string[];
                  if (e.target.checked) {
                    next = [...selected, value];
                  } else {
                    next = selected.filter((s) => s !== value);
                  }
                  setFilters({ ...filters, source: next.length > 0 ? next.join(",") : undefined });
                }}
              />
              {label}
            </label>
          );
        })}
      </div>

      <label>City</label>
      <MultiSelect
        options={cityConfigs.map((c) => ({ id: c.id, label: c.name }))}
        selectedIds={selectedCityIds}
        onChange={(ids) => {
          const names = cityConfigs
            .filter((c) => ids.includes(c.id))
            .map((c) => c.name);
          setFilters({ ...filters, city: names.length > 0 ? names.join(",") : undefined });
        }}
        placeholder="All cities"
      />

      {neighborhoods && neighborhoods.length > 0 && (
        <>
          <label>Neighborhood</label>
          <select
            value=""
            onChange={(e) => {
              if (e.target.value) {
                const kw = filters.keywords || "";
                const updated = kw ? `${kw},${e.target.value}` : e.target.value;
                setFilters({ ...filters, keywords: updated });
              }
            }}
          >
            <option value="">Filter by neighborhood...</option>
            {neighborhoods.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </>
      )}

      <label>Price Range (ILS)</label>
      <div className="range-row">
        <input type="number" placeholder="Min" value={filters.min_price || ""}
          onChange={(e) => setFilters({ ...filters, min_price: e.target.value ? +e.target.value : undefined })} />
        <span>—</span>
        <input type="number" placeholder="Max" value={filters.max_price || ""}
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
        {["apartment", "house", "penthouse", "garden_apartment", "studio", "duplex", "roof_apartment"].map((t) => (
          <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
        ))}
      </select>

      <label>Move-in Date Range</label>
      <div className="range-row">
        <input type="date" className="date-input" value={filters.min_entry_date || ""}
          onChange={(e) => setFilters({ ...filters, min_entry_date: e.target.value || undefined })} />
        <span>—</span>
        <input type="date" className="date-input" value={filters.max_entry_date || ""}
          onChange={(e) => setFilters({ ...filters, max_entry_date: e.target.value || undefined })} />
      </div>

      <label>Keyword Search</label>
      <input
        type="text"
        className="keyword-input"
        placeholder='e.g. "renovated", "quiet"'
        value={filters.keywords || ""}
        onChange={(e) => setFilters({ ...filters, keywords: e.target.value || undefined })}
      />

      <label>Features</label>
      <div className="checkbox-group">
        {[
          { key: "require_parking" as const, label: "Parking" },
          { key: "require_elevator" as const, label: "Elevator" },
          { key: "require_balcony" as const, label: "Balcony" },
          { key: "require_ac" as const, label: "A/C" },
          { key: "require_furnished" as const, label: "Furnished" },
          { key: "require_pet_friendly" as const, label: "Pet Friendly" },
        ].map(({ key, label }) => (
          <label key={key} className="checkbox-label">
            <input
              type="checkbox"
              checked={!!filters[key]}
              onChange={(e) => setFilters({ ...filters, [key]: e.target.checked || undefined })}
            />
            {label}
          </label>
        ))}
      </div>

      {/* Hide by rating level */}
      <label>Hide by Status</label>
      <div className="checkbox-group">
        {RATING_LEVELS.map(({ level, label, symbol }) => (
          <label key={level} className="checkbox-label">
            <input
              type="checkbox"
              checked={hiddenRatings.includes(level)}
              onChange={(e) => {
                if (e.target.checked) {
                  onSetHiddenRatings([...hiddenRatings, level]);
                } else {
                  onSetHiddenRatings(hiddenRatings.filter((r) => r !== level));
                }
              }}
            />
            <span style={{ marginRight: 4 }}>{symbol}</span>{label}
          </label>
        ))}
      </div>

      {/* Hide by tag */}
      {tags.length > 0 && (
        <>
          <label>Hide by Tag</label>
          <div className="checkbox-group">
            {tags.map((tag) => (
              <label key={tag.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={hiddenTagIds.includes(tag.id)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onSetHiddenTagIds([...hiddenTagIds, tag.id]);
                    } else {
                      onSetHiddenTagIds(hiddenTagIds.filter((id) => id !== tag.id));
                    }
                  }}
                />
                <span className="tag-chip-mini" style={{ background: tag.color }} />
                {tag.name}
              </label>
            ))}
          </div>
        </>
      )}

      <div className="filter-actions">
        <label className="sidebar" style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#4a5568", margin: "0 0 4px" }}>
          Min Rating
        </label>
        <select
          style={{ width: "100%", padding: "6px 8px", border: "1px solid #e2e8f0", borderRadius: "6px", fontSize: "0.85rem", background: "#fff", marginBottom: "8px" }}
          value={minRatingFilter}
          onChange={(e) => onSetMinRatingFilter(parseInt(e.target.value))}
        >
          <option value={0}>Show all ratings</option>
          <option value={3}>Maybe or better (\u2265 3)</option>
          <option value={4}>Interested or better (\u2265 4)</option>
          <option value={5}>Perfect Match only (5)</option>
        </select>
        <label className="checkbox-label inactive-toggle">
          <input
            type="checkbox"
            checked={!!filters.include_inactive}
            onChange={(e) => setFilters({ ...filters, include_inactive: e.target.checked || undefined })}
          />
          Show Taken/Inactive
        </label>
        <button className="btn-clear" onClick={() => setFilters({})}>
          Clear Filters
        </button>
      </div>
    </div>
  );
}
