import type { Coordinates, CurrentWeatherResponse, LocationMode } from "../../types/weather";

type LocationDebugPanelProps = {
  gpsCoordinates: Coordinates | null;
  locationMode: LocationMode;
  currentWeather: CurrentWeatherResponse | null;
};

export function LocationDebugPanel({
  gpsCoordinates,
  locationMode,
  currentWeather,
}: LocationDebugPanelProps) {
  const isDebug =
    import.meta.env.VITE_DEBUG_LOCATION === "true" ||
    (window as unknown as { DEBUG_LOCATION?: boolean }).DEBUG_LOCATION === true;

  if (!isDebug) return null;

  const isLowAccuracy = gpsCoordinates && gpsCoordinates.accuracy !== undefined && gpsCoordinates.accuracy > 500;
  const isBackendUncertain = currentWeather?.location_confidence === "uncertain" || currentWeather?.location_confidence === "coordinates";
  const needsConfirmation = locationMode !== "confirmed" && (isLowAccuracy || isBackendUncertain || currentWeather?.needs_user_confirmation);

  return (
    <div className="location-debug-panel">
      <h4>[DEV] Location Debug Tool</h4>
      <div className="debug-grid">
        <div className="debug-item">
          <strong>GPS Coordinates:</strong>{" "}
          {gpsCoordinates
            ? `${gpsCoordinates.latitude.toFixed(6)}, ${gpsCoordinates.longitude.toFixed(6)}`
            : "N/A"}
        </div>
        <div className="debug-item">
          <strong>GPS Accuracy:</strong>{" "}
          {gpsCoordinates && gpsCoordinates.accuracy !== undefined
            ? `±${Math.round(gpsCoordinates.accuracy)} meters`
            : "N/A"}
        </div>
        <div className="debug-item">
          <strong>Location Mode:</strong> {locationMode}
        </div>
        <div className="debug-item">
          <strong>Backend resolved name:</strong>{" "}
          {currentWeather?.display_name || currentWeather?.location_name || "N/A"}
        </div>
        <div className="debug-item">
          <strong>Location Confidence:</strong>{" "}
          {currentWeather?.location_confidence || "N/A"}
        </div>
        <div className="debug-item">
          <strong>Needs Confirmation:</strong>{" "}
          {needsConfirmation ? "True" : "False"} (Low Acc: {isLowAccuracy ? "Yes" : "No"}, Backend Uncertain: {isBackendUncertain ? "Yes" : "No"}, Backend Needs Conf: {currentWeather?.needs_user_confirmation ? "Yes" : "No"})
        </div>
        <div className="debug-item">
          <strong>Geocoding candidates:</strong>{" "}
          {currentWeather?.location_candidates && currentWeather.location_candidates.length > 0
            ? currentWeather.location_candidates.join(" | ")
            : "None"}
        </div>
        <div className="debug-item">
          <strong>Active Weather Provider:</strong>{" "}
          {currentWeather?.provider || "N/A"}
        </div>
        <div className="debug-item">
          <strong>Fallback Provider Used:</strong>{" "}
          {currentWeather?.fallback_provider_used ? "Yes" : "No"}
        </div>
      </div>
    </div>
  );
}
