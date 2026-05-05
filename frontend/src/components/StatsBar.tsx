import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchStats, type Listing } from "../api";

interface StatsBarProps {
  folderListings?: Listing[];
  likedCount?: number;
}

export function StatsBar({ folderListings, likedCount }: StatsBarProps) {
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
    staleTime: 30_000,
  });

  const folderStats = useMemo(() => {
    if (!folderListings) return null;
    const sources: Record<string, number> = {};
    for (const l of folderListings) {
      sources[l.source] = (sources[l.source] || 0) + 1;
    }
    return { total: folderListings.length, sources };
  }, [folderListings]);

  const display = folderStats ?? (stats ? {
    total: stats.total_listings,
    sources: stats.sources,
  } : null);

  if (!display) return null;

  const sourceEntries = Object.entries(display.sources);

  return (
    <div className="stats-bar">
      <div className="stat">
        <span className="stat-value">{display.total}</span>
        <span className="stat-label">{folderStats ? "In Folder" : "Total Listings"}</span>
      </div>
      <div className="stat">
        <span className="stat-value">{sourceEntries.length}</span>
        <span className="stat-label">
          {sourceEntries.length <= 3
            ? sourceEntries.map(([s, n]) => `${s} (${n})`).join(", ")
            : "Sources"}
        </span>
      </div>
      <div className="stat">
        <span className="stat-value">{likedCount ?? 0}</span>
        <span className="stat-label">Liked</span>
      </div>
    </div>
  );
}
