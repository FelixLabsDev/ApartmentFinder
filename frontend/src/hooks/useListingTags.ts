import { useState, useCallback, useEffect } from "react";
import { fetchTags, createTagApi, deleteTagApi, renameTagApi, addListingToTagApi, removeFromTagApi } from "../api";

export interface Tag {
  id: string;
  name: string;
  color: string;
  listingIds: string[];
  createdAt: string;
}

export function useListingTags() {
  const [tags, setTags] = useState<Tag[]>([]);

  // Load tags from server on mount
  useEffect(() => {
    fetchTags().then(setTags).catch(() => {});
  }, []);

  // Returns the created tag after the backend confirms it, so callers can
  // safely chain addToTag without hitting a race condition
  const createTag = useCallback(async (name: string, color: string): Promise<Tag> => {
    const id = crypto.randomUUID();
    const tag: Tag = { id, name, color, listingIds: [], createdAt: new Date().toISOString() };
    setTags((prev) => [...prev, tag]);
    await createTagApi(name, color, id);
    return tag;
  }, []);

  const renameTag = useCallback((tagId: string, newName: string) => {
    setTags((prev) => prev.map((t) => (t.id === tagId ? { ...t, name: newName } : t)));
    renameTagApi(tagId, newName).catch(() => {});
  }, []);

  const deleteTag = useCallback((tagId: string) => {
    setTags((prev) => prev.filter((t) => t.id !== tagId));
    deleteTagApi(tagId).catch(() => {});
  }, []);

  const addToTag = useCallback((tagId: string, listingId: string) => {
    setTags((prev) =>
      prev.map((t) =>
        t.id === tagId && !t.listingIds.includes(listingId)
          ? { ...t, listingIds: [...t.listingIds, listingId] }
          : t,
      ),
    );
    addListingToTagApi(tagId, listingId).catch(() => {});
  }, []);

  const removeFromTag = useCallback((tagId: string, listingId: string) => {
    setTags((prev) =>
      prev.map((t) =>
        t.id === tagId
          ? { ...t, listingIds: t.listingIds.filter((id) => id !== listingId) }
          : t,
      ),
    );
    removeFromTagApi(tagId, listingId).catch(() => {});
  }, []);

  const getTagsForListing = useCallback(
    (listingId: string): Tag[] => tags.filter((t) => t.listingIds.includes(listingId)),
    [tags],
  );

  return { tags, createTag, renameTag, deleteTag, addToTag, removeFromTag, getTagsForListing };
}
