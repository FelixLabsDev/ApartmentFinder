import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type Filters,
  fetchSearchProfiles,
  createSearchProfile,
  deleteSearchProfile,
} from "../api";

export function SearchProfiles({
  currentFilters,
  onLoadProfile,
}: {
  currentFilters: Filters;
  onLoadProfile: (filters: Filters) => void;
}) {
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const queryClient = useQueryClient();

  const { data: profiles } = useQuery({
    queryKey: ["search-profiles"],
    queryFn: fetchSearchProfiles,
    staleTime: 30_000,
  });

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await createSearchProfile(name.trim(), currentFilters);
      setName("");
      queryClient.invalidateQueries({ queryKey: ["search-profiles"] });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    await deleteSearchProfile(id);
    queryClient.invalidateQueries({ queryKey: ["search-profiles"] });
  };

  return (
    <div className="search-profiles">
      <h4>Saved Searches</h4>

      {profiles && profiles.length > 0 && (
        <div className="profile-chips">
          {profiles.map((p) => (
            <span
              key={p.id}
              className="profile-chip"
              onClick={() => onLoadProfile(p.filter_json as unknown as Filters)}
              title="Click to load this search"
            >
              {p.name}
              <button
                className="chip-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(p.id);
                }}
                title="Delete"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="save-profile-row">
        <input
          type="text"
          placeholder="Save current search as..."
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSave()}
        />
        <button onClick={handleSave} disabled={saving || !name.trim()}>
          Save
        </button>
      </div>
    </div>
  );
}
