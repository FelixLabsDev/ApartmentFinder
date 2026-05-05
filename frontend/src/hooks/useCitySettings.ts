import { useState, useCallback, useEffect, useRef } from "react";
import { fetchCitySettings, saveCitySettings } from "../api";

export interface CityConfig {
  id: string;
  name: string;
  region: string;
  areaCode: string;
  cityCode: string;
  neighborhoodName: string;
  neighborhoodCode: string;
}

export interface ParsedYad2Url {
  region: string;
  areaCode: string;
  cityCode: string;
  neighborhoodCode?: string;
}

/**
 * Parse a Yad2 URL like:
 * https://www.yad2.co.il/realestate/rent/tel-aviv-area?zoom=12&area=11&city=0565&neighborhood=1252
 * Returns { region: "tel-aviv-area", areaCode: "11", cityCode: "0565", neighborhoodCode: "1252" }
 */
export function parseYad2Url(url: string): ParsedYad2Url | null {
  try {
    const parsed = new URL(url);
    if (!parsed.hostname.includes("yad2.co.il")) return null;

    const pathParts = parsed.pathname.split("/").filter(Boolean);
    const region = pathParts.length >= 3 ? pathParts[pathParts.length - 1] : null;
    if (!region) return null;

    const areaCode = parsed.searchParams.get("area");
    const cityCode = parsed.searchParams.get("city");
    if (!areaCode || !cityCode) return null;

    const neighborhoodCode = parsed.searchParams.get("neighborhood") || undefined;

    return { region, areaCode, cityCode, neighborhoodCode };
  } catch {
    return null;
  }
}

/** Migrate old format (neighborhoods array) to flat fields. */
function migrateCity(c: Record<string, unknown>): CityConfig {
  if (Array.isArray(c.neighborhoods)) {
    const nh = c.neighborhoods[0] as Record<string, string> | undefined;
    return {
      id: c.id as string,
      name: c.name as string,
      region: c.region as string,
      areaCode: c.areaCode as string,
      cityCode: c.cityCode as string,
      neighborhoodName: nh?.name || "",
      neighborhoodCode: nh?.code || "",
    };
  }
  return {
    id: c.id as string,
    name: c.name as string,
    region: c.region as string,
    areaCode: c.areaCode as string,
    cityCode: c.cityCode as string,
    neighborhoodName: (c.neighborhoodName as string) || "",
    neighborhoodCode: (c.neighborhoodCode as string) || "",
  };
}

export function useCitySettings() {
  const [cities, setCities] = useState<CityConfig[]>([]);
  const loaded = useRef(false);

  // Load from backend on mount
  useEffect(() => {
    fetchCitySettings()
      .then((data) => {
        const raw = data as Record<string, unknown>[];
        if (raw && raw.length > 0) {
          setCities(raw.map(migrateCity));
        }
        loaded.current = true;
      })
      .catch(() => {
        loaded.current = true;
      });
  }, []);

  // Save to backend on every change (skip initial load)
  useEffect(() => {
    if (loaded.current) {
      saveCitySettings(cities).catch(() => {});
    }
  }, [cities]);

  const addCity = useCallback(
    (city: Omit<CityConfig, "id">): CityConfig => {
      const full: CityConfig = { id: crypto.randomUUID(), ...city };
      setCities((prev) => [...prev, full]);
      return full;
    },
    [],
  );

  const updateCity = useCallback(
    (id: string, updates: Partial<Omit<CityConfig, "id">>) => {
      setCities((prev) =>
        prev.map((c) => (c.id === id ? { ...c, ...updates } : c)),
      );
    },
    [],
  );

  const removeCity = useCallback((id: string) => {
    setCities((prev) => prev.filter((c) => c.id !== id));
  }, []);

  return { cities, addCity, updateCity, removeCity };
}
