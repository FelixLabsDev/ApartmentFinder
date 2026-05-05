import { useState, useEffect, useCallback, useRef } from "react";
import { fetchNewListings } from "../api";

const POLL_INTERVAL = 60_000; // 60 seconds

export function useNewListings() {
  const [newCount, setNewCount] = useState(0);
  const lastCheckRef = useRef<string>(new Date().toISOString());
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const checkForNew = useCallback(async () => {
    try {
      const listings = await fetchNewListings(lastCheckRef.current);
      if (listings.length > 0) {
        setNewCount((prev) => prev + listings.length);

        // Browser notification
        if (Notification.permission === "granted") {
          new Notification("ApartmentFinder", {
            body: `${listings.length} new listing${listings.length > 1 ? "s" : ""} found!`,
            icon: "/favicon.ico",
          });
        }
      }
      lastCheckRef.current = new Date().toISOString();
    } catch {
      // Silently ignore polling errors
    }
  }, []);

  const requestPermission = useCallback(async () => {
    if ("Notification" in window && Notification.permission === "default") {
      await Notification.requestPermission();
    }
  }, []);

  const dismiss = useCallback(() => {
    setNewCount(0);
  }, []);

  useEffect(() => {
    timerRef.current = setInterval(checkForNew, POLL_INTERVAL);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [checkForNew]);

  return { newCount, dismiss, requestPermission };
}
