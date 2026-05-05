import axios from "axios";

const API_BASE = "http://localhost:8080";

export interface Listing {
  id: string | null;
  source: string;
  source_id: string;
  source_url: string;
  title: string;
  city: string;
  preset_city_name: string | null;
  neighborhood: string | null;
  street: string | null;
  house_number: string | null;
  description: string | null;
  price: number | null;
  currency: string;
  rooms: number | null;
  floor: number | null;
  total_floors: number | null;
  area_sqm: number | null;
  property_type: string | null;
  has_parking: boolean | null;
  has_elevator: boolean | null;
  has_balcony: boolean | null;
  has_air_conditioning: boolean | null;
  has_mamad: boolean | null;
  is_accessible: boolean | null;
  is_furnished: boolean | null;
  has_bars: boolean | null;
  has_storage: boolean | null;
  pet_friendly: boolean | null;
  image_urls: string[];
  contact_name: string | null;
  contact_phone: string | null;
  entry_date: string | null;
  latitude: number | null;
  longitude: number | null;
  posted_at: string | null;
  first_seen_at: string | null;
  is_active: boolean | null;
  ai_guessed_fields: string[];
  rating: string | null;
  seen_at: string | null;
}

export interface Filters {
  source?: string;
  city?: string;
  min_price?: number;
  max_price?: number;
  min_rooms?: number;
  max_rooms?: number;
  min_area?: number;
  max_area?: number;
  property_type?: string;
  require_parking?: boolean;
  require_elevator?: boolean;
  require_balcony?: boolean;
  require_ac?: boolean;
  require_furnished?: boolean;
  require_pet_friendly?: boolean;
  min_floor?: number;
  max_floor?: number;
  keywords?: string;
  min_entry_date?: string;
  max_entry_date?: string;
  include_inactive?: boolean;
  sort_by?: string;
}

export interface ScrapeResult {
  total_scraped: number;
  total_after_dedup: number;
  total_after_filter: number;
  listings_stored: number;
  new_listings: number;
  stored_listing_keys: string[];
}

export interface Stats {
  total_listings: number;
  active_listings: number;
  sources: Record<string, number>;
  cities: Record<string, number>;
}

const api = axios.create({ baseURL: API_BASE });

export async function fetchListings(filters: Filters, limit = 50, offset = 0): Promise<Listing[]> {
  const params: Record<string, string | number | boolean> = { limit, offset };
  if (filters.source) params.source = filters.source;
  if (filters.city) params.city = filters.city;
  if (filters.min_price) params.min_price = filters.min_price;
  if (filters.max_price) params.max_price = filters.max_price;
  if (filters.min_rooms) params.min_rooms = filters.min_rooms;
  if (filters.max_rooms) params.max_rooms = filters.max_rooms;
  if (filters.min_area) params.min_area = filters.min_area;
  if (filters.max_area) params.max_area = filters.max_area;
  if (filters.property_type) params.property_type = filters.property_type;
  if (filters.require_parking) params.require_parking = true;
  if (filters.require_elevator) params.require_elevator = true;
  if (filters.require_balcony) params.require_balcony = true;
  if (filters.require_ac) params.require_ac = true;
  if (filters.require_furnished) params.require_furnished = true;
  if (filters.require_pet_friendly) params.require_pet_friendly = true;
  if (filters.min_floor) params.min_floor = filters.min_floor;
  if (filters.max_floor) params.max_floor = filters.max_floor;
  if (filters.keywords) params.keywords = filters.keywords;
  if (filters.min_entry_date) params.min_entry_date = filters.min_entry_date;
  if (filters.max_entry_date) params.max_entry_date = filters.max_entry_date;
  if (filters.include_inactive) params.include_inactive = true;
  if (filters.sort_by) params.sort_by = filters.sort_by;

  const { data } = await api.get<Listing[]>("/api/listings", { params });
  return data;
}

export async function fetchListingsByKeys(keys: string[]): Promise<Listing[]> {
  if (keys.length === 0) return [];
  const { data } = await api.post<Listing[]>("/api/listings/by-keys", keys);
  return data;
}

export interface ScrapeParams {
  source: "yad2" | "facebook";
  city?: string;
  area?: string;
  neighborhood?: string;
  min_price?: number;
  max_price?: number;
  min_rooms?: number;
  max_rooms?: number;
  min_floor?: number;
  max_floor?: number;
  min_area?: number;
  max_area?: number;
  property_type?: string;
  city_name?: string;
  headless?: boolean;
  fb_latitude?: number;
  fb_longitude?: number;
  fb_radius_km?: number;
}

export async function triggerScrape(scrapeParams: ScrapeParams): Promise<ScrapeResult> {
  const params: Record<string, string | number | boolean> = { source: scrapeParams.source };
  if (scrapeParams.city) params.city = scrapeParams.city;
  if (scrapeParams.area) params.area = scrapeParams.area;
  if (scrapeParams.neighborhood) params.neighborhood = scrapeParams.neighborhood;
  if (scrapeParams.city_name) params.city_name = scrapeParams.city_name;
  if (scrapeParams.min_price) params.min_price = scrapeParams.min_price;
  if (scrapeParams.max_price) params.max_price = scrapeParams.max_price;
  if (scrapeParams.min_rooms) params.min_rooms = scrapeParams.min_rooms;
  if (scrapeParams.max_rooms) params.max_rooms = scrapeParams.max_rooms;
  if (scrapeParams.min_floor) params.min_floor = scrapeParams.min_floor;
  if (scrapeParams.max_floor) params.max_floor = scrapeParams.max_floor;
  if (scrapeParams.min_area) params.min_area = scrapeParams.min_area;
  if (scrapeParams.max_area) params.max_area = scrapeParams.max_area;
  if (scrapeParams.property_type) params.property_type = scrapeParams.property_type;
  if (scrapeParams.fb_latitude != null) params.fb_latitude = scrapeParams.fb_latitude;
  if (scrapeParams.fb_longitude != null) params.fb_longitude = scrapeParams.fb_longitude;
  if (scrapeParams.fb_radius_km != null) params.fb_radius_km = scrapeParams.fb_radius_km;
  if (scrapeParams.headless === false) params.headless = false;
  const { data } = await api.post<ScrapeResult>("/api/scrape", null, { params, timeout: 300000 });
  return data;
}

export async function clearAllListings(): Promise<{ deleted: number }> {
  const { data } = await api.delete<{ deleted: number }>("/api/listings");
  return data;
}

export async function fetchStats(): Promise<Stats> {
  const { data } = await api.get<Stats>("/api/stats");
  return data;
}

export async function fetchHealth(): Promise<Record<string, boolean>> {
  const { data } = await api.get<{ sources: Record<string, boolean> }>("/api/health");
  return data.sources;
}

export async function fetchNeighborhoods(city: string): Promise<string[]> {
  const { data } = await api.get<string[]>("/api/neighborhoods", { params: { city } });
  return data;
}

export async function fetchNewListings(since: string): Promise<Listing[]> {
  const { data } = await api.get<Listing[]>("/api/listings/new", { params: { since } });
  return data;
}

export interface SearchProfile {
  id: string;
  name: string;
  filter_json: Filters;
  created_at: string;
}

export async function fetchSearchProfiles(): Promise<SearchProfile[]> {
  const { data } = await api.get<SearchProfile[]>("/api/search-profiles");
  return data;
}

export async function createSearchProfile(name: string, filters: Filters): Promise<{ id: string; name: string }> {
  const { data } = await api.post<{ id: string; name: string }>("/api/search-profiles", null, {
    params: { name, filter_json: JSON.stringify(filters) },
  });
  return data;
}

export async function deleteSearchProfile(profileId: string): Promise<void> {
  await api.delete(`/api/search-profiles/${profileId}`);
}

export async function fetchCitySettings(): Promise<unknown[]> {
  const { data } = await api.get<unknown[]>("/api/city-settings");
  return data;
}

export async function saveCitySettings(cities: unknown[]): Promise<void> {
  await api.put("/api/city-settings", cities);
}

// Telegram Bot
export async function startTelegramBot(): Promise<{ status: string; message?: string }> {
  const { data } = await api.post<{ status: string; message?: string }>("/api/telegram-bot/start");
  return data;
}

export async function stopTelegramBot(): Promise<{ status: string }> {
  const { data } = await api.post<{ status: string }>("/api/telegram-bot/stop");
  return data;
}

export async function getTelegramBotStatus(): Promise<{ running: boolean }> {
  const { data } = await api.get<{ running: boolean }>("/api/telegram-bot/status");
  return data;
}

// Seen tracking
export async function markListingSeen(source: string, sourceId: string): Promise<void> {
  await api.post(`/api/listings/${source}/${sourceId}/seen`);
}

// Ratings
export async function setListingRating(source: string, sourceId: string, rating: string): Promise<void> {
  await api.put(`/api/listings/${source}/${sourceId}/rating`, { rating });
}

export async function clearListingRating(source: string, sourceId: string): Promise<void> {
  await api.delete(`/api/listings/${source}/${sourceId}/rating`);
}

export async function fetchAllRatings(): Promise<Record<string, string>> {
  const { data } = await api.get<Record<string, string>>("/api/ratings");
  return data;
}

export async function bulkImportRatings(ratings: Record<string, string>): Promise<{ updated: number }> {
  const { data } = await api.post<{ updated: number }>("/api/ratings/bulk", { ratings });
  return data;
}

// Folders
export interface FolderData {
  id: string;
  name: string;
  listingIds: string[];
  createdAt: string;
}

export async function fetchFolders(): Promise<FolderData[]> {
  const { data } = await api.get<FolderData[]>("/api/folders");
  return data;
}

export async function createFolderApi(name: string, id?: string, listingIds?: string[]): Promise<FolderData> {
  const { data } = await api.post<FolderData>("/api/folders", { name, id, listingIds: listingIds ?? [] });
  return data;
}

export async function renameFolderApi(folderId: string, name: string): Promise<void> {
  await api.put(`/api/folders/${folderId}/name`, { name });
}

export async function deleteFolderApi(folderId: string): Promise<void> {
  await api.delete(`/api/folders/${folderId}`);
}

export async function addListingsToFolderApi(folderId: string, listingIds: string[]): Promise<void> {
  await api.post(`/api/folders/${folderId}/listings`, { listingIds });
}

export async function removeFromFolderApi(folderId: string, listingId: string): Promise<void> {
  await api.delete(`/api/folders/${folderId}/listings/${listingId}`);
}

export async function clearFolderApi(folderId: string): Promise<void> {
  await api.delete(`/api/folders/${folderId}/listings`);
}

export async function bulkImportFolders(folders: FolderData[]): Promise<{ imported: number }> {
  const { data } = await api.post<{ imported: number }>("/api/folders/bulk-import", { folders });
  return data;
}

// Notes
export interface NoteData {
  id: string;
  text: string;
  createdAt: string;
}

export async function fetchAllNotes(): Promise<Record<string, NoteData[]>> {
  const { data } = await api.get<Record<string, NoteData[]>>("/api/notes");
  return data;
}

export async function addNoteApi(listingKey: string, text: string, id?: string): Promise<NoteData> {
  const { data } = await api.post<NoteData>(`/api/notes/${listingKey}`, { text, id });
  return data;
}

export async function deleteNoteApi(noteId: string): Promise<void> {
  await api.delete(`/api/notes/${noteId}`);
}

export async function bulkImportNotes(notes: Record<string, NoteData[]>): Promise<{ imported: number }> {
  const { data } = await api.post<{ imported: number }>("/api/notes-bulk-import", { notes });
  return data;
}

// AI Extract
export async function aiExtractListing(source: string, sourceId: string): Promise<Listing> {
  const { data } = await api.post<Listing>(`/api/listings/${source}/${sourceId}/ai-extract`, null, {
    timeout: 120000,
  });
  return data;
}

// Facebook Cities
export interface FacebookCityData {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  radiusKm: number;
}

export async function fetchFacebookCities(): Promise<FacebookCityData[]> {
  const { data } = await api.get<FacebookCityData[]>("/api/facebook-cities");
  return data;
}

export async function createFacebookCityApi(city: Omit<FacebookCityData, "id"> & { id?: string }): Promise<FacebookCityData> {
  const { data } = await api.post<FacebookCityData>("/api/facebook-cities", city);
  return data;
}

export async function updateFacebookCityApi(id: string, updates: Partial<Omit<FacebookCityData, "id">>): Promise<void> {
  await api.put(`/api/facebook-cities/${id}`, updates);
}

export async function deleteFacebookCityApi(id: string): Promise<void> {
  await api.delete(`/api/facebook-cities/${id}`);
}

export async function bulkImportFacebookCities(cities: FacebookCityData[]): Promise<{ imported: number }> {
  const { data } = await api.post<{ imported: number }>("/api/facebook-cities/bulk-import", { cities });
  return data;
}
