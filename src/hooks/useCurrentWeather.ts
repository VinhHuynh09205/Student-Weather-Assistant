import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getCurrentWeather } from "../api/weatherApi";
import type { CurrentWeatherResponse, LocationQuery, WeatherDisplayState } from "../types/weather";
import { useAutoRefresh } from "./useAutoRefresh";
import { useAuth } from "../context/AuthContext";

export function useCurrentWeather(source: LocationQuery | null) {
  const [data, setData] = useState<CurrentWeatherResponse | null>(null);
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

    getCurrentWeather(source)
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
          const err = unknownError instanceof Error ? unknownError : new Error("Không thể tải thời tiết hiện tại");
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
  }, [source, sourceKey, refetchTrigger]);

  const { settings } = useAuth();

  useAutoRefresh(
    lastFetchedAt,
    5 * 60 * 1000, // 5 minutes
    refresh,
    Boolean(source) && !loading && settings.auto_refresh_enabled
  );

  const weatherForTheme = useMemo<WeatherDisplayState>(() => {
    const current = data?.current;
    return {
      weather_code: current?.weather_code,
      weather_description: current?.weather_description,
      is_day: current?.is_day,
      time: current?.time,
      wind_speed_kmh: current?.wind_speed_kmh,
      precipitation_probability_percent: current?.precipitation_probability_percent ?? undefined,
      temperature_c: current?.temperature_c,
    };
  }, [data]);

  return { data, error, loading, weatherForTheme, lastFetchedAt, refresh };
}

function getSourceKey(source: LocationQuery | null): string {
  if (!source) return "none";
  if (source.mode === "current" || source.mode === "confirmed") {
    return `${source.mode}:${source.latitude}:${source.longitude}`;
  }
  return `city:${source.city}`;
}
