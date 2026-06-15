import { MapPin, Navigation } from "lucide-react";

import type { Coordinates, LocationMode, SearchLocationCandidate } from "../../types/weather";

type LocationSourcePanelProps = {
  city: string;
  coordinates: Coordinates | null;
  disabled?: boolean;
  isLocating: boolean;
  locationError: string | null;
  locationMode: LocationMode;
  locationName?: string;
  locationConfidence?: string;
  accuracyMeters?: number | null;
  onSearch: (city: string) => void;
  onUseCurrentLocation: () => void;
  // Confirmed location features
  searchCandidates?: SearchLocationCandidate[];
  isSearchingCandidates?: boolean;
  searchCandidatesError?: string | null;
  onSelectCandidate?: (candidate: SearchLocationCandidate) => void;
  onClearConfirmed?: () => void;
};

export function LocationSourcePanel({
  city,
  isLocating,
  locationError,
  locationMode,
  locationName,
  locationConfidence,
  accuracyMeters,
  onUseCurrentLocation,
  searchCandidates = [],
  isSearchingCandidates = false,
  searchCandidatesError = null,
  onSelectCandidate,
  onClearConfirmed,
}: LocationSourcePanelProps) {
  const status = resolveStatus({
    city,
    isLocating,
    locationError,
    locationMode,
    locationName,
    locationConfidence,
    accuracyMeters,
  });

  return (
    <section className="location-source-panel" aria-label="Nguồn vị trí">
      <div className={`location-status ${locationError ? "has-error" : ""}`}>
        <span>
          <MapPin size={20} />
        </span>
        <div>
          <strong>{status.title}</strong>
          <p>{status.description}</p>
        </div>
      </div>

      <div className="location-actions">
        <button className="current-location-button" type="button" disabled={isLocating} onClick={onUseCurrentLocation}>
          <Navigation size={18} />
          <span>Cập nhật vị trí</span>
        </button>
        <button className="change-location-button" type="button" onClick={onClearConfirmed}>
          <MapPin size={18} />
          <span>Đổi vị trí</span>
        </button>
      </div>

      {isSearchingCandidates && (
        <div className="candidates-status loading">
          <span>Đang tìm kiếm các địa điểm phù hợp...</span>
        </div>
      )}

      {searchCandidatesError && (
        <div className="candidates-status error">
          <span>{searchCandidatesError}</span>
        </div>
      )}

      {searchCandidates.length > 0 && (
        <div className="search-candidates-box">
          <p className="candidates-hint">Có {searchCandidates.length} kết quả tìm thấy. Vui lòng chọn địa điểm chính xác:</p>
          <ul className="candidates-list">
            {searchCandidates.map((candidate, idx) => (
              <li key={`${candidate.latitude}-${candidate.longitude}-${idx}`}>
                <button
                  type="button"
                  className="candidate-select-btn"
                  onClick={() => onSelectCandidate?.(candidate)}
                >
                  <MapPin size={14} />
                  <span>{candidate.display_name}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function resolveStatus({
  city,
  isLocating,
  locationError,
  locationMode,
  locationName,
  locationConfidence,
}: {
  city: string;
  isLocating: boolean;
  locationError: string | null;
  locationMode: LocationMode;
  locationName?: string;
  locationConfidence?: string;
  accuracyMeters?: number | null;
}): { title: string; description: string } {
  if (isLocating) {
    return {
      title: "Đang lấy vị trí hiện tại...",
      description: "Trình duyệt có thể hỏi quyền truy cập vị trí.",
    };
  }

  if (locationError) {
    return {
      title: "Chưa dùng được vị trí hiện tại",
      description: locationError,
    };
  }

  if (locationMode === "confirmed") {
    return {
      title: "Đang dùng vị trí đã lưu",
      description: locationName || city || "Vị trí đã xác nhận",
    };
  }

  if (locationMode === "current") {
    const isUncertain = locationConfidence === "coordinates" || locationConfidence === "uncertain" || !locationName || locationName === "Vị trí hiện tại" || locationName.includes("Vị trí GPS hiện tại") || locationName.includes("chưa xác định");
    const friendlyName = isUncertain ? "Vị trí hiện tại chưa xác định rõ" : locationName;
    return {
      title: "Đang dùng vị trí hiện tại",
      description: friendlyName,
    };
  }

  if (locationMode === "search") {
    return {
      title: "Đang xem theo tìm kiếm",
      description: locationName || city || "Địa điểm tìm kiếm",
    };
  }

  return {
    title: "Dự báo theo vị trí của bạn",
    description: "Cho phép vị trí để nhận dự báo gần nơi bạn đang ở.",
  };
}

