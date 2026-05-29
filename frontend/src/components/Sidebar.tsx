import { useState } from "react";
import { ScrapeTabSwitcher } from "./ScrapePanel";
import { DisplayFilters } from "./DisplayFilters";
import { FoldersPanel } from "./FoldersPanel";
import { SearchProfiles } from "./SearchProfiles";
import { SettingsModal } from "./SettingsModal";
import { TelegramBotPanel } from "./TelegramBotPanel";
import type { Filters, Listing } from "../api";
import type { Folder } from "../hooks/useFolders";
import type { CityConfig } from "../hooks/useCitySettings";
import type { FacebookCityConfig } from "../hooks/useFacebookCities";
import type { Tag } from "../hooks/useListingTags";

type SidebarTab = "scrape" | "filters" | "folders" | "saved";

const tabs: { id: SidebarTab; icon: string; label: string }[] = [
  { id: "scrape", icon: "\uD83D\uDD0D", label: "Scrape" },
  { id: "filters", icon: "\u2699", label: "Filters" },
  { id: "folders", icon: "\uD83D\uDCC1", label: "Folders" },
  { id: "saved", icon: "\uD83D\uDCBE", label: "Saved" },
];

export function Sidebar({
  filters,
  setFilters,
  minRatingFilter,
  onSetMinRatingFilter,
  hiddenRatings,
  onSetHiddenRatings,
  hiddenTagIds,
  onSetHiddenTagIds,
  tags,
  folders,
  activeFolder,
  onSetActiveFolder,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  onRemoveFromFolder,
  onClearFolder,
  listings,
  onScrapeComplete,
  onLoadProfile,
  cityConfigs,
  onAddCity,
  onUpdateCity,
  onRemoveCity,
  fbCities,
  onAddFbCity,
  onUpdateFbCity,
  onRemoveFbCity,
  onClearListings,
  onAddMultipleToFolder,
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
  folders: Folder[];
  activeFolder: string | null;
  onSetActiveFolder: (id: string | null) => void;
  onCreateFolder: (name: string) => Folder;
  onRenameFolder: (id: string, name: string) => void;
  onDeleteFolder: (id: string) => void;
  onRemoveFromFolder: (folderId: string, listingId: string) => void;
  onClearFolder: (folderId: string) => void;
  listings: Listing[];
  onScrapeComplete: () => void;
  onLoadProfile: (filters: Filters) => void;
  cityConfigs: CityConfig[];
  onAddCity: (city: Omit<CityConfig, "id">) => CityConfig;
  onUpdateCity: (id: string, updates: Partial<Omit<CityConfig, "id">>) => void;
  onRemoveCity: (id: string) => void;
  fbCities: FacebookCityConfig[];
  onAddFbCity: (city: Omit<FacebookCityConfig, "id">) => FacebookCityConfig;
  onUpdateFbCity: (id: string, updates: Partial<Omit<FacebookCityConfig, "id">>) => void;
  onRemoveFbCity: (id: string) => void;
  onClearListings: () => void;
  onAddMultipleToFolder: (folderId: string, listingIds: string[]) => void;
}) {
  const [activeTab, setActiveTab] = useState<SidebarTab>("filters");
  const [showSettings, setShowSettings] = useState(false);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">AF</span>
        <span className="sidebar-title">ApartmentFinder</span>
        <button
          className="sidebar-settings-btn"
          onClick={() => setShowSettings(true)}
          title="Settings"
        >
          {"\u2699\uFE0F"}
        </button>
      </div>

      <nav className="sidebar-nav">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`nav-tab nav-tab-${tab.id}${activeTab === tab.id ? " active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
            title={tab.label}
          >
            <span className="nav-tab-icon">{tab.icon}</span>
            <span className="nav-tab-label">{tab.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-panel">
        {activeTab === "scrape" && (
          <div className="panel-content">
            <ScrapeTabSwitcher
              onScrapeComplete={onScrapeComplete}
              cityConfigs={cityConfigs}
              fbCities={fbCities}
              folders={folders}
              onCreateFolder={onCreateFolder}
              onAddToFolder={onAddMultipleToFolder}
            />
          </div>
        )}

        {activeTab === "filters" && (
          <div className="panel-content">
            <DisplayFilters
              filters={filters}
              setFilters={setFilters}
              minRatingFilter={minRatingFilter}
              onSetMinRatingFilter={onSetMinRatingFilter}
              hiddenRatings={hiddenRatings}
              onSetHiddenRatings={onSetHiddenRatings}
              hiddenTagIds={hiddenTagIds}
              onSetHiddenTagIds={onSetHiddenTagIds}
              tags={tags}
              cityConfigs={cityConfigs}
            />
          </div>
        )}

        {activeTab === "folders" && (
          <div className="panel-content">
            <FoldersPanel
              folders={folders}
              activeFolder={activeFolder}
              onSetActiveFolder={onSetActiveFolder}
              onCreateFolder={onCreateFolder}
              onRenameFolder={onRenameFolder}
              onDeleteFolder={onDeleteFolder}
              onRemoveFromFolder={onRemoveFromFolder}
              onClearFolder={onClearFolder}
              listings={listings}
            />
          </div>
        )}

        {activeTab === "saved" && (
          <div className="panel-content">
            <SearchProfiles
              currentFilters={filters}
              onLoadProfile={onLoadProfile}
            />
          </div>
        )}
      </div>

      <TelegramBotPanel />

      {showSettings && (
        <SettingsModal
          cities={cityConfigs}
          onAddCity={onAddCity}
          onUpdateCity={onUpdateCity}
          onRemoveCity={onRemoveCity}
          fbCities={fbCities}
          onAddFbCity={onAddFbCity}
          onUpdateFbCity={onUpdateFbCity}
          onRemoveFbCity={onRemoveFbCity}
          onClearListings={onClearListings}
          onClose={() => setShowSettings(false)}
        />
      )}
    </aside>
  );
}
