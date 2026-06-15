import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { searchLocations } from "../api/weatherApi";
import type { Coordinates, LocationMode, LocationQuery, SearchLocationCandidate, AdministrativeLevels } from "../types/weather";
import { useAuth } from "../context/AuthContext";

const defaultCity = "Ho Chi Minh";

export function useLocationSource() {
  const { currentUser, savedLocations, addLocation, settings } = useAuth();
  const hasRequestedInitialLocation = useRef(false);
  const hasLoadedDefaultDbLocation = useRef(false);
  
  const [city, setCity] = useState("");
  const [shortDisplayName, setShortDisplayName] = useState<string | null>(null);
  const [administrativeLevels, setAdministrativeLevels] = useState<AdministrativeLevels | null>(null);
  const [locationMode, setLocationMode] = useState<LocationMode>("current");
  const [currentCoordinates, setCurrentCoordinates] = useState<Coordinates | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  // Search candidates state
  const [searchCandidates, setSearchCandidates] = useState<SearchLocationCandidate[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const requestCurrentLocation = useCallback(() => {
    setLocationError(null);
    setSearchCandidates([]);
    setSearchError(null);
    setIsLocating(true);

    if (!canRequestPreciseLocation()) {
      setIsLocating(false);
      if (!currentCoordinates) {
        setLocationMode("search");
        setCity(defaultCity);
      }
      setLocationError(getInsecureGeolocationMessage());
      return;
    }

    if (!navigator.geolocation) {
      setIsLocating(false);
      if (!currentCoordinates) {
        setCurrentCoordinates(null);
        setLocationMode("search");
        setCity(defaultCity);
      }
      setLocationError("Trình duyệt không hỗ trợ định vị.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCurrentCoordinates({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
        setLocationMode("current");
        setLocationError(null);
        setIsLocating(false);
      },
      (positionError) => {
        setIsLocating(false);
        if (!currentCoordinates) {
          setCurrentCoordinates(null);
          setLocationMode("search");
          setCity(defaultCity);
        }
        setLocationError(getGeolocationErrorMessage(positionError));
      },
      {
        enableHighAccuracy: true,
        timeout: 20000,
        maximumAge: 0,
      },
    );
  }, [currentCoordinates]);

  // Check localStorage or default database location on mount/auth load
  useEffect(() => {
    // If logged in, prioritize default location from database settings/saved list
    if (currentUser) {
      if (hasLoadedDefaultDbLocation.current) return;
      
      const defaultLoc = savedLocations.find(
        (loc) => loc.is_default || loc.id === settings.default_location_id
      );
      if (defaultLoc) {
        hasLoadedDefaultDbLocation.current = true;
        setCurrentCoordinates({
          latitude: defaultLoc.latitude,
          longitude: defaultLoc.longitude,
        });
        setCity(defaultLoc.display_name);
        setShortDisplayName(defaultLoc.short_display_name);
        setAdministrativeLevels(defaultLoc.administrative_levels);
        setLocationMode("confirmed");
        return;
      }
      // If we already finished loading user locations and none is default, fallback to GPS
      if (savedLocations.length > 0) {
        hasLoadedDefaultDbLocation.current = true;
        requestCurrentLocation();
        return;
      }
    } else {
      // Guest mode: check localStorage
      if (hasRequestedInitialLocation.current) return;
      hasRequestedInitialLocation.current = true;

      try {
        const stored = window.localStorage.getItem("student_weather_confirmed_location");
        if (stored) {
          const parsed = JSON.parse(stored);
          if (parsed && typeof parsed.latitude === "number" && typeof parsed.longitude === "number" && parsed.display_name) {
            setCurrentCoordinates({
              latitude: parsed.latitude,
              longitude: parsed.longitude,
            });
            setCity(parsed.display_name);
            setShortDisplayName(parsed.short_display_name ?? null);
            setAdministrativeLevels(parsed.administrative_levels ?? null);
            setLocationMode("confirmed");
            return;
          }
        }
      } catch (e) {
        console.error("Error loading confirmed location:", e);
      }

      requestCurrentLocation();
    }
  }, [currentUser, savedLocations, settings.default_location_id, requestCurrentLocation]);

  // Reset default location load ref when logging out
  useEffect(() => {
    if (!currentUser) {
      hasLoadedDefaultDbLocation.current = false;
    }
  }, [currentUser]);

  const searchCity = useCallback(async (query: string) => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setCity(trimmed);
    setLocationMode("search");
    setIsSearching(true);
    setSearchError(null);
    setSearchCandidates([]);

    try {
      const results = await searchLocations(trimmed);
      setSearchCandidates(results);
      if (results.length === 0) {
        setSearchError("Không tìm thấy địa điểm nào khớp với tìm kiếm.");
      }
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Đã xảy ra lỗi khi tìm kiếm địa điểm.");
    } finally {
      setIsSearching(false);
    }
  }, []);

  const confirmLocation = useCallback((
    displayName: string,
    latitude: number,
    longitude: number,
    shortName?: string | null,
    adminLevels?: AdministrativeLevels | null
  ) => {
    const confirmedData = {
      display_name: displayName,
      short_display_name: shortName,
      administrative_levels: adminLevels,
      latitude,
      longitude,
      source: "user_confirmed",
      updated_at: new Date().toISOString(),
    };

    if (currentUser) {
      // Save location to backend
      addLocation({
        label: "Vị trí đã xác nhận",
        display_name: displayName,
        short_display_name: shortName,
        latitude,
        longitude,
        source: "user_confirmed",
        administrative_levels: adminLevels,
        is_default: true, // Mark confirmed as default
      }).catch(e => console.error("Failed to save location to backend:", e));
    } else {
      window.localStorage.setItem("student_weather_confirmed_location", JSON.stringify(confirmedData));
    }

    setCurrentCoordinates({ latitude, longitude });
    setCity(displayName);
    setShortDisplayName(shortName ?? null);
    setAdministrativeLevels(adminLevels ?? null);
    setLocationMode("confirmed");
    setSearchCandidates([]);
    setSearchError(null);
    setLocationError(null);
  }, [currentUser, addLocation]);

  const clearConfirmedLocation = useCallback(() => {
    if (currentUser) {
      // Instead of deleting from DB, we just clear our current session's confirmed state
      // but if the user wants they can manage locations in settings.
      // So we just clear the active state and request GPS.
    } else {
      window.localStorage.removeItem("student_weather_confirmed_location");
    }
    
    setCity("");
    setShortDisplayName(null);
    setAdministrativeLevels(null);
    setSearchCandidates([]);
    setSearchError(null);
    requestCurrentLocation();
  }, [currentUser, requestCurrentLocation]);

  const source = useMemo<LocationQuery | null>(() => {
    if (locationMode === "confirmed") {
      if (!currentCoordinates) return null;
      return {
        mode: "confirmed",
        latitude: currentCoordinates.latitude,
        longitude: currentCoordinates.longitude,
        displayName: city,
        shortDisplayName: shortDisplayName ?? undefined,
        administrativeLevels: administrativeLevels ?? undefined,
      };
    }

    if (locationMode === "current") {
      if (!currentCoordinates) return null;
      return {
        mode: "current",
        latitude: currentCoordinates.latitude,
        longitude: currentCoordinates.longitude,
        accuracy: currentCoordinates.accuracy,
      };
    }

    // search mode without selection yet
    if (!city) return null;
    return { mode: "search", city };
  }, [city, currentCoordinates, locationMode, shortDisplayName, administrativeLevels]);

  return {
    city,
    currentCoordinates,
    isLocating,
    locationError,
    locationMode,
    requestCurrentLocation,
    searchCity,
    source,
    useCurrentLocation: requestCurrentLocation,
    // Add confirmed location states and setters
    searchCandidates,
    isSearching,
    searchError,
    confirmLocation,
    clearConfirmedLocation,
  };
}

function getGeolocationErrorMessage(error: GeolocationPositionError): string {
  if (error.code === error.PERMISSION_DENIED) {
    return "Quyền vị trí đang bị chặn hoặc chưa được cấp. Hãy mở cài đặt trang web, cho phép truy cập vị trí, rồi bấm Cập nhật vị trí.";
  }
  if (error.code === error.POSITION_UNAVAILABLE) {
    return "Không thể lấy vị trí hiện tại. Vui lòng thử lại hoặc tìm thành phố thủ công.";
  }
  if (error.code === error.TIMEOUT) {
    return "Không thể lấy vị trí hiện tại. Vui lòng thử lại hoặc tìm thành phố thủ công.";
  }
  return "Không thể lấy vị trí hiện tại. Vui lòng thử lại hoặc tìm thành phố thủ công.";
}

function canRequestPreciseLocation(): boolean {
  return window.isSecureContext || isLocalDevelopmentHost(window.location.hostname);
}

function isLocalDevelopmentHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

function getInsecureGeolocationMessage(): string {
  return "Trình duyệt chỉ hiện yêu cầu cấp quyền vị trí khi web chạy bằng HTTPS hoặc localhost. Trang hiện tại đang ở chế độ không bảo mật, nên hãy mở bản HTTPS rồi bấm Cập nhật vị trí.";
}
