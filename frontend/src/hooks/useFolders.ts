import { useState, useCallback, useEffect, useRef } from "react";
import {
  fetchFolders,
  createFolderApi,
  renameFolderApi,
  deleteFolderApi,
  addListingsToFolderApi,
  removeFromFolderApi,
  clearFolderApi,
  bulkImportFolders,
  type FolderData,
} from "../api";

export interface Folder {
  id: string;
  name: string;
  listingIds: string[];
  createdAt: string;
}

const OLD_STORAGE_KEY = "apartmentfinder_folders";
const MIGRATED_KEY = "apartmentfinder_folders_migrated";

export function useFolders() {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [foldersLoaded, setFoldersLoaded] = useState(false);
  const loadedRef = useRef(false);

  // Load folders from API on mount, migrate localStorage if needed
  useEffect(() => {
    let cancelled = false;

    async function init() {
      // One-time migration from localStorage
      const migrated = localStorage.getItem(MIGRATED_KEY);
      if (!migrated) {
        const localFolders = loadLocalStorageFolders();
        if (localFolders.length > 0) {
          try {
            await bulkImportFolders(localFolders);
          } catch {
            // API may not be available; retry next load
          }
        }
        localStorage.setItem(MIGRATED_KEY, "1");
        localStorage.removeItem(OLD_STORAGE_KEY);
      }

      // Load from server
      try {
        const serverFolders = await fetchFolders();
        if (!cancelled) {
          setFolders(serverFolders);
          loadedRef.current = true;
          setFoldersLoaded(true);
        }
      } catch {
        // API unavailable — mark as loaded with empty
        if (!cancelled) {
          loadedRef.current = true;
          setFoldersLoaded(true);
        }
      }
    }

    init();
    return () => { cancelled = true; };
  }, []);

  const createFolder = useCallback((name: string): Folder => {
    const id = crypto.randomUUID();
    const folder: Folder = {
      id,
      name,
      listingIds: [],
      createdAt: new Date().toISOString(),
    };
    setFolders((prev) => [...prev, folder]);
    createFolderApi(name, id).catch(() => {});
    return folder;
  }, []);

  const renameFolder = useCallback((folderId: string, newName: string) => {
    setFolders((prev) =>
      prev.map((f) => (f.id === folderId ? { ...f, name: newName } : f)),
    );
    renameFolderApi(folderId, newName).catch(() => {});
  }, []);

  const deleteFolder = useCallback((folderId: string) => {
    setFolders((prev) => prev.filter((f) => f.id !== folderId));
    deleteFolderApi(folderId).catch(() => {});
  }, []);

  const addToFolder = useCallback((folderId: string, listingId: string) => {
    setFolders((prev) =>
      prev.map((f) =>
        f.id === folderId && !f.listingIds.includes(listingId)
          ? { ...f, listingIds: [...f.listingIds, listingId] }
          : f,
      ),
    );
    addListingsToFolderApi(folderId, [listingId]).catch(() => {});
  }, []);

  const addMultipleToFolder = useCallback((folderId: string, listingIds: string[]) => {
    setFolders((prev) =>
      prev.map((f) => {
        if (f.id !== folderId) return f;
        const existing = new Set(f.listingIds);
        const newIds = listingIds.filter((id) => !existing.has(id));
        return newIds.length > 0
          ? { ...f, listingIds: [...f.listingIds, ...newIds] }
          : f;
      }),
    );
    addListingsToFolderApi(folderId, listingIds).catch(() => {});
  }, []);

  const removeFromFolder = useCallback((folderId: string, listingId: string) => {
    setFolders((prev) =>
      prev.map((f) =>
        f.id === folderId
          ? { ...f, listingIds: f.listingIds.filter((id) => id !== listingId) }
          : f,
      ),
    );
    removeFromFolderApi(folderId, listingId).catch(() => {});
  }, []);

  const clearFolder = useCallback((folderId: string) => {
    setFolders((prev) =>
      prev.map((f) => (f.id === folderId ? { ...f, listingIds: [] } : f)),
    );
    clearFolderApi(folderId).catch(() => {});
  }, []);

  const getFoldersForListing = useCallback(
    (listingId: string): Folder[] =>
      folders.filter((f) => f.listingIds.includes(listingId)),
    [folders],
  );

  return {
    folders,
    foldersLoaded,
    createFolder,
    renameFolder,
    deleteFolder,
    addToFolder,
    addMultipleToFolder,
    removeFromFolder,
    clearFolder,
    getFoldersForListing,
  };
}

/** Read legacy localStorage folders for one-time migration */
function loadLocalStorageFolders(): FolderData[] {
  try {
    const raw = localStorage.getItem(OLD_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return [];
}
