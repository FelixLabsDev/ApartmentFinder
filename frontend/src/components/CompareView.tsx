import type { Listing } from "../api";

function bestValue(listings: Listing[], getter: (l: Listing) => number | null | undefined, lower = true): number {
  const values = listings.map(getter).filter((v): v is number => v != null);
  if (values.length === 0) return -1;
  return lower ? Math.min(...values) : Math.max(...values);
}

export function CompareView({
  listings,
  onClose,
}: {
  listings: Listing[];
  onClose: () => void;
}) {
  if (listings.length < 2) {
    return (
      <div className="compare-overlay" onClick={onClose}>
        <div className="compare-content" onClick={(e) => e.stopPropagation()}>
          <button className="modal-close" onClick={onClose}>&times;</button>
          <div className="compare-empty">
            Select at least 2 liked listings to compare (max 4).
          </div>
        </div>
      </div>
    );
  }

  const items = listings.slice(0, 4);
  const bestPrice = bestValue(items, (l) => l.price, true);
  const bestRooms = bestValue(items, (l) => l.rooms, false);
  const bestArea = bestValue(items, (l) => l.area_sqm, false);
  const bestPriceSqm = bestValue(
    items,
    (l) => (l.price && l.area_sqm ? l.price / l.area_sqm : null),
    true
  );

  const rows: { label: string; values: (string | null)[]; highlights: boolean[] }[] = [
    {
      label: "Price",
      values: items.map((l) => l.price ? `${l.price.toLocaleString()} \u20aa` : "N/A"),
      highlights: items.map((l) => l.price === bestPrice),
    },
    {
      label: "Rooms",
      values: items.map((l) => l.rooms?.toString() ?? "N/A"),
      highlights: items.map((l) => l.rooms === bestRooms),
    },
    {
      label: "Area",
      values: items.map((l) => l.area_sqm ? `${l.area_sqm} m\u00b2` : "N/A"),
      highlights: items.map((l) => l.area_sqm === bestArea),
    },
    {
      label: "Price/m\u00b2",
      values: items.map((l) =>
        l.price && l.area_sqm
          ? `${Math.round(l.price / l.area_sqm).toLocaleString()} \u20aa`
          : "N/A"
      ),
      highlights: items.map(
        (l) =>
          l.price != null &&
          l.area_sqm != null &&
          Math.round(l.price / l.area_sqm) === Math.round(bestPriceSqm)
      ),
    },
    {
      label: "Floor",
      values: items.map((l) =>
        l.floor != null
          ? `${l.floor}${l.total_floors ? ` / ${l.total_floors}` : ""}`
          : "N/A"
      ),
      highlights: items.map(() => false),
    },
    {
      label: "City",
      values: items.map((l) => l.city || "N/A"),
      highlights: items.map(() => false),
    },
    {
      label: "Neighborhood",
      values: items.map((l) => l.neighborhood || "N/A"),
      highlights: items.map(() => false),
    },
    {
      label: "Type",
      values: items.map((l) => l.property_type || "N/A"),
      highlights: items.map(() => false),
    },
    {
      label: "Move-in",
      values: items.map((l) => l.entry_date || "N/A"),
      highlights: items.map(() => false),
    },
    {
      label: "Parking",
      values: items.map((l) => l.has_parking ? "\u2713" : "\u2717"),
      highlights: items.map((l) => !!l.has_parking),
    },
    {
      label: "Elevator",
      values: items.map((l) => l.has_elevator ? "\u2713" : "\u2717"),
      highlights: items.map((l) => !!l.has_elevator),
    },
    {
      label: "Balcony",
      values: items.map((l) => l.has_balcony ? "\u2713" : "\u2717"),
      highlights: items.map((l) => !!l.has_balcony),
    },
    {
      label: "A/C",
      values: items.map((l) => l.has_air_conditioning ? "\u2713" : "\u2717"),
      highlights: items.map((l) => !!l.has_air_conditioning),
    },
    {
      label: "Furnished",
      values: items.map((l) => l.is_furnished ? "\u2713" : "\u2717"),
      highlights: items.map((l) => !!l.is_furnished),
    },
    {
      label: "Pet Friendly",
      values: items.map((l) => l.pet_friendly ? "\u2713" : "\u2717"),
      highlights: items.map((l) => !!l.pet_friendly),
    },
  ];

  return (
    <div className="compare-overlay" onClick={onClose}>
      <div className="compare-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>&times;</button>
        <h2 className="compare-title">Compare Listings</h2>

        <div className="compare-table-wrap">
          <table className="compare-table">
            <thead>
              <tr>
                <th></th>
                {items.map((l, i) => (
                  <th key={i}>
                    <div className="compare-header-cell">
                      {l.image_urls.length > 0 && (
                        <img src={l.image_urls[0]} alt="" className="compare-thumb" />
                      )}
                      <div className="compare-header-info">
                        <span className="compare-header-price">
                          {l.price ? `${l.price.toLocaleString()} \u20aa` : "N/A"}
                        </span>
                        <span className="compare-header-loc">
                          {l.rooms && `${l.rooms}r`} {l.city}
                        </span>
                      </div>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.label}>
                  <td className="compare-label">{row.label}</td>
                  {row.values.map((val, i) => (
                    <td key={i} className={row.highlights[i] ? "compare-best" : ""}>
                      {val}
                    </td>
                  ))}
                </tr>
              ))}
              <tr>
                <td className="compare-label">Source</td>
                {items.map((l, i) => (
                  <td key={i}>
                    <a href={l.source_url} target="_blank" rel="noopener noreferrer" className="btn-view">
                      {l.source}
                    </a>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
