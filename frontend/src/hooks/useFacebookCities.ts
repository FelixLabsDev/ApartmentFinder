import { useState, useCallback, useEffect } from "react";
import {
  fetchFacebookCities,
  createFacebookCityApi,
  updateFacebookCityApi,
  deleteFacebookCityApi,
  bulkImportFacebookCities,
  type FacebookCityData,
} from "../api";

export interface FacebookCityConfig {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  radiusKm: number;
}

const OLD_STORAGE_KEY = "apartmentfinder_fb_city_settings";
const MIGRATED_KEY = "apartmentfinder_fb_cities_migrated";

export function useFacebookCities() {
  const [fbCities, setFbCities] = useState<FacebookCityConfig[]>([]);

  // Load from API on mount, migrate localStorage if needed
  useEffect(() => {
    let cancelled = false;

    async function init() {
      const migrated = localStorage.getItem(MIGRATED_KEY);
      if (!migrated) {
        const localCities = loadLocalStorageFbCities();
        if (localCities.length > 0) {
          try {
            await bulkImportFacebookCities(localCities);
          } catch {}
        }
        localStorage.setItem(MIGRATED_KEY, "1");
        localStorage.removeItem(OLD_STORAGE_KEY);
      }

      try {
        const serverCities = await fetchFacebookCities();
        if (!cancelled) setFbCities(serverCities);
      } catch {}
    }

    init();
    return () => { cancelled = true; };
  }, []);

  const addFbCity = useCallback((city: Omit<FacebookCityConfig, "id">): FacebookCityConfig => {
    const id = crypto.randomUUID();
    const full: FacebookCityConfig = { id, ...city };
    setFbCities((prev) => [...prev, full]);
    createFacebookCityApi({ id, ...city }).catch(() => {});
    return full;
  }, []);

  const updateFbCity = useCallback((id: string, updates: Partial<Omit<FacebookCityConfig, "id">>) => {
    setFbCities((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...updates } : c)),
    );
    updateFacebookCityApi(id, updates).catch(() => {});
  }, []);

  const removeFbCity = useCallback((id: string) => {
    setFbCities((prev) => prev.filter((c) => c.id !== id));
    deleteFacebookCityApi(id).catch(() => {});
  }, []);

  return { fbCities, addFbCity, updateFbCity, removeFbCity };
}

function loadLocalStorageFbCities(): FacebookCityData[] {
  try {
    const raw = localStorage.getItem(OLD_STORAGE_KEY);
    if (raw) return JSON.parse(raw) as FacebookCityData[];
  } catch {}
  return [];
}
