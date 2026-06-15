import { AlertTriangle, MapPin, Navigation, Search } from "lucide-react";
import { useState, useEffect } from "react";
import type { SearchLocationCandidate } from "../../types/weather";

type LocationConfirmationCardProps = {
  accuracyMeters?: number | null;
  needsConfirmation: boolean;
  searchCandidates: SearchLocationCandidate[];
  isSearching: boolean;
  searchError: string | null;
  onSearch: (query: string) => void;
  onConfirmLocation: (displayName: string, latitude: number, longitude: number) => void;
  onUseCurrentLocation: () => void;
};

export function LocationConfirmationCard({
  accuracyMeters,
  needsConfirmation,
  searchCandidates,
  isSearching,
  searchError,
  onSearch,
  onConfirmLocation,
  onUseCurrentLocation,
}: LocationConfirmationCardProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState<{
    display_name: string;
    latitude: number;
    longitude: number;
  } | null>(null);

  // Default suggestions if no search candidates are available
  const defaultSuggestions = [
    {
      display_name: "Long Tiên, Cai Lậy, Tiền Giang",
      latitude: 10.3502,
      longitude: 106.1406,
    },
    {
      display_name: "Cai Lậy, Tiền Giang",
      latitude: 10.4072,
      longitude: 106.1912,
    },
    {
      display_name: "Tiền Giang",
      latitude: 10.3600,
      longitude: 106.3600,
    },
  ];

  // Reset selected candidate when search candidates change
  useEffect(() => {
    setSelectedCandidate(null);
  }, [searchCandidates]);

  if (!needsConfirmation) return null;

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onSearch(searchQuery.trim());
    }
  };

  const displayCandidates = searchCandidates.length > 0 ? searchCandidates : defaultSuggestions;

  return (
    <div className="location-confirmation-card">
      <div className="card-header">
        <AlertTriangle className="warning-icon" size={22} />
        <h3>Chọn vị trí chính xác hơn</h3>
      </div>

      <p className="card-message">
        Hệ thống chỉ xác định được vị trí gần đúng. Hãy chọn xã/phường hoặc quận/huyện để dự báo chính xác hơn.
      </p>

      {accuracyMeters && accuracyMeters > 500 ? (
        <p className="accuracy-warning">
          Lưu ý: Độ sai lệch định vị của thiết bị khá lớn ({Math.round(accuracyMeters)}m). Bạn nên chọn vị trí thủ công.
        </p>
      ) : null}

      <form className="inline-search-form" onSubmit={handleSearchSubmit}>
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Nhập xã, huyện, tỉnh hoặc thành phố..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <button type="submit" disabled={isSearching} className="search-submit-btn">
          Tìm kiếm
        </button>
      </form>
      <p className="search-hint-text">Ví dụ: &ldquo;Long Tiên, Cai Lậy, Tiền Giang&rdquo;</p>

      {isSearching && (
        <div className="confirmation-search-status loading">
          Đang tìm địa điểm...
        </div>
      )}

      {searchError && (
        <div className="confirmation-search-status error">
          {searchError}
        </div>
      )}

      <div className="confirmation-candidates-box">
        <p className="candidates-title">Danh sách gợi ý:</p>
        <ul className="candidates-list">
          {displayCandidates.map((candidate, idx) => {
            const isSelected =
              selectedCandidate &&
              Math.abs(selectedCandidate.latitude - candidate.latitude) < 0.0001 &&
              Math.abs(selectedCandidate.longitude - candidate.longitude) < 0.0001;

            return (
              <li key={`${candidate.latitude}-${candidate.longitude}-${idx}`}>
                <button
                  type="button"
                  className={`candidate-item-btn ${isSelected ? "selected" : ""}`}
                  onClick={() => setSelectedCandidate(candidate)}
                >
                  <MapPin size={14} />
                  <span>{candidate.display_name}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="confirmation-options">
        <button
          type="button"
          className="option-btn confirm-btn"
          disabled={!selectedCandidate}
          onClick={() => {
            if (selectedCandidate) {
              onConfirmLocation(
                selectedCandidate.display_name,
                selectedCandidate.latitude,
                selectedCandidate.longitude
              );
            }
          }}
        >
          Dùng vị trí này
        </button>
        <button
          type="button"
          className="option-btn gps-retry-btn"
          onClick={onUseCurrentLocation}
        >
          <Navigation size={16} />
          <span>Cập nhật vị trí</span>
        </button>
      </div>
    </div>
  );
}
