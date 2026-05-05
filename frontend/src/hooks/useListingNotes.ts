import { useState, useCallback, useEffect } from "react";
import { fetchAllNotes, addNoteApi, deleteNoteApi, bulkImportNotes, type NoteData } from "../api";

export interface ListingNote {
  id: string;
  text: string;
  createdAt: string;
}

type NotesMap = Record<string, ListingNote[]>;

const OLD_STORAGE_KEY = "apartmentfinder_notes";
const MIGRATED_KEY = "apartmentfinder_notes_migrated";

export function useListingNotes() {
  const [notesMap, setNotesMap] = useState<NotesMap>({});

  // Load from API on mount, migrate localStorage if needed
  useEffect(() => {
    let cancelled = false;

    async function init() {
      const migrated = localStorage.getItem(MIGRATED_KEY);
      if (!migrated) {
        const localNotes = loadLocalStorageNotes();
        if (Object.keys(localNotes).length > 0) {
          try {
            await bulkImportNotes(localNotes);
          } catch {}
        }
        localStorage.setItem(MIGRATED_KEY, "1");
        localStorage.removeItem(OLD_STORAGE_KEY);
      }

      try {
        const serverNotes = await fetchAllNotes();
        if (!cancelled) setNotesMap(serverNotes);
      } catch {}
    }

    init();
    return () => { cancelled = true; };
  }, []);

  const getNotes = useCallback(
    (listingKey: string): ListingNote[] => notesMap[listingKey] ?? [],
    [notesMap],
  );

  const addNote = useCallback((listingKey: string, text: string) => {
    const id = crypto.randomUUID();
    const note: ListingNote = {
      id,
      text,
      createdAt: new Date().toISOString(),
    };
    setNotesMap((prev) => ({
      ...prev,
      [listingKey]: [note, ...(prev[listingKey] ?? [])],
    }));
    addNoteApi(listingKey, text, id).catch(() => {});
  }, []);

  const deleteNote = useCallback((listingKey: string, noteId: string) => {
    setNotesMap((prev) => {
      const notes = (prev[listingKey] ?? []).filter((n) => n.id !== noteId);
      const next = { ...prev };
      if (notes.length === 0) delete next[listingKey];
      else next[listingKey] = notes;
      return next;
    });
    deleteNoteApi(noteId).catch(() => {});
  }, []);

  return { getNotes, addNote, deleteNote };
}

function loadLocalStorageNotes(): Record<string, NoteData[]> {
  try {
    const raw = localStorage.getItem(OLD_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return {};
}
