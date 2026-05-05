import { useState, useRef, useEffect } from "react";

export interface MultiSelectOption {
  id: string;
  label: string;
}

export function MultiSelect({
  options,
  selectedIds,
  onChange,
  placeholder = "Select...",
}: {
  options: MultiSelectOption[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggle = (id: string) => {
    onChange(
      selectedIds.includes(id)
        ? selectedIds.filter((x) => x !== id)
        : [...selectedIds, id],
    );
  };

  const label =
    selectedIds.length === 0
      ? placeholder
      : selectedIds.length === options.length
        ? "All selected"
        : options
            .filter((o) => selectedIds.includes(o.id))
            .map((o) => o.label)
            .join(", ");

  return (
    <div className="multi-select" ref={ref}>
      <button
        type="button"
        className="multi-select-trigger"
        onClick={() => setOpen(!open)}
      >
        <span className="multi-select-label">{label}</span>
        <span className="multi-select-arrow">{open ? "\u25B2" : "\u25BC"}</span>
      </button>
      {open && (
        <div className="multi-select-dropdown">
          <div className="multi-select-options">
            {options.map((o) => (
              <label key={o.id} className="multi-select-option">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(o.id)}
                  onChange={() => toggle(o.id)}
                />
                {o.label}
              </label>
            ))}
            {options.length === 0 && (
              <span className="multi-select-empty">No options available</span>
            )}
          </div>
          <button
            type="button"
            className="multi-select-ok"
            onClick={() => setOpen(false)}
          >
            OK
          </button>
        </div>
      )}
    </div>
  );
}
