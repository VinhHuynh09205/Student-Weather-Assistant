import { useCallback, useEffect, useRef, useState } from "react";

import { getDailyWeather } from "../api/weatherApi";
import type { DailyWeatherResponse, LocationQuery } from "../types/weather";
import { useAutoRefresh } from "./useAutoRefresh";
import { useAuth } from "../context/AuthContext";

export function useDailyForecast(source: LocationQuery | null, days = 7) {
  const [data, setData] = useState<DailyWeatherResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<number>(0);
  const [refetchTrigger, setRefetchTrigger] = useState(0);
  const fetchCallbacksRef = useRef<{ resolve: () => void; reject: (err: Error) => void }[]>([]);

  const sourceKey = getSourceKey(source);

  const refresh = useCallback(() => {
    return new Promise<void>((resolve, reject) => {
      fetchCallbacksRef.current.push({ resolve, reject });
      setRefetchTrigger((prev) => prev + 1);
    });
  }, []);

  useEffect(() => {
    if (!source) {
      setLoading(false);
      const callbacks = fetchCallbacksRef.current;
      fetchCallbacksRef.current = [];
      callbacks.forEach((cb) => cb.resolve());
      return;
    }

    let ignore = false;
    setLoading(true);
    setError(null);

    getDailyWeather(source, days)
      .then((nextData) => {
        if (!ignore) {
          setData(nextData);
          setLastFetchedAt(Date.now());
          const callbacks = fetchCallbacksRef.current;
          fetchCallbacksRef.current = [];
          callbacks.forEach((cb) => cb.resolve());
        }
      })
      .catch((unknownError) => {
        if (!ignore) {
          const err = unknownError instanceof Error ? unknownError : new Error("Không thể tải dự báo nhiều ngày");
          setError(err.message);
          setLastFetchedAt(Date.now());
          const callbacks = fetchCallbacksRef.current;
          fetchCallbacksRef.current = [];
          callbacks.forEach((cb) => cb.reject(err));
        }
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [days, source, sourceKey, refetchTrigger]);

  const { settings } = useAuth();

  useAutoRefresh(
    lastFetchedAt,
    30 * 60 * 1000, // 30 minutes
    refresh,
    Boolean(source) && !loading && settings.auto_refresh_enabled
  );

  return { data, error, loading, lastFetchedAt, refresh };
}

function getSourceKey(source: LocationQuery | null): string {
  if (!source) return "none";
  if (source.mode === "current" || source.mode === "confirmed") {
    return `${source.mode}:${source.latitude}:${source.longitude}`;
  }
  return `city:${source.city}`;
}
