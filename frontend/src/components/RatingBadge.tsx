import { useState, useRef, useEffect } from "react";
import type { Rating } from "../hooks/useListingRatings";
import { RATING_LEVELS } from "../hooks/useListingRatings";

/**
 * Compact rating badge: shows the current tier as a colored pill.
 * Clicking opens a 5-option popover for setting or clearing the rating.
 * `large` mode uses bigger text/padding, suitable for the detail modal.
 */
export function RatingBadge({
  rating,
  onSetRating,
  large = false,
}: {
  rating: Rating | null;
  onSetRating: (level: Rating) => void;
  large?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Close popover when clicking outside
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const current = rating ? RATING_LEVELS.find((r) => r.level === rating) : null;

  return (
    <div ref={wrapRef} className="rating-badge-wrap" onClick={(e) => e.stopPropagation()}>
      <button
        className={`rating-badge${rating ? ` rating-badge-${rating}` : ""}${large ? " rating-badge-lg" : ""}`}
        onClick={() => setOpen(!open)}
        title="Set rating"
      >
        {current ? `${current.symbol} ${current.label}` : "\u2605 Rate"}
      </button>
      {open && (
        <div className="rating-popover">
          {RATING_LEVELS.map(({ level, label, symbol }) => (
            <button
              key={level}
              className={`rating-popover-item tier-color-${level}${rating === level ? " active" : ""}`}
              onClick={() => { onSetRating(level); setOpen(false); }}
            >
              <span className="rating-popover-symbol">{symbol}</span>
              <span>{label}</span>
              {rating === level && <span className="rating-popover-clear">click to clear</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
