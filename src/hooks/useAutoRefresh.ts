import { useEffect, useRef } from "react";

export function useAutoRefresh(
  lastFetchedAt: number,
  intervalMs: number,
  onRefresh: () => void,
  enabled = true
) {
  const onRefreshRef = useRef(onRefresh);
  onRefreshRef.current = onRefresh;

  useEffect(() => {
    if (!enabled) return;

    const checkRefresh = () => {
      if (document.visibilityState === "visible" && lastFetchedAt > 0) {
        const elapsed = Date.now() - lastFetchedAt;
        if (elapsed >= intervalMs) {
          onRefreshRef.current();
        }
      }
    };

    const timer = setInterval(checkRefresh, 10000);

    const handleVisibilityChange = () => {
      checkRefresh();
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [lastFetchedAt, intervalMs, enabled]);
}
