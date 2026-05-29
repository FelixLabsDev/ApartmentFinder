import { useState, useCallback } from "react";

/**
 * Drop-in replacement for useState that persists the value to localStorage.
 * On mount the stored value is restored; on every update it is saved.
 * Falls back to defaultValue if nothing is stored or the stored JSON is invalid.
 */
export function usePersistedState<T>(
  key: string,
  defaultValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [state, setState] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored !== null ? (JSON.parse(stored) as T) : defaultValue;
    } catch {
      return defaultValue;
    }
  });

  const setPersistedState = useCallback(
    (value: T | ((prev: T) => T)) => {
      setState((prev) => {
        const next = typeof value === "function" ? (value as (prev: T) => T)(prev) : value;
        try {
          localStorage.setItem(key, JSON.stringify(next));
        } catch {
          // Storage quota exceeded or unavailable — continue without persisting
        }
        return next;
      });
    },
    [key],
  );

  return [state, setPersistedState];
}
