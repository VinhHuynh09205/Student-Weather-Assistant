import React, { useState, useEffect, useRef } from "react";
import { X, Search, MapPin, Check, Save } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { searchLocations } from "../../api/weatherApi";
import type { SearchLocationCandidate } from "../../types/weather";
import { CustomSelect } from "../common/CustomSelect";

interface LocationSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectLocation: (candidate: SearchLocationCandidate) => void;
}

export function LocationSearchModal({
  isOpen,
  onClose,
  onSelectLocation,
}: LocationSearchModalProps) {
  const { savedLocations, addLocation, currentUser } = useAuth();
  const [query, setQuery] = useState("");
  const [candidates, setCandidates] = useState<SearchLocationCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Selected candidate state
  const [selectedCandidate, setSelectedCandidate] = useState<SearchLocationCandidate | null>(null);
  const [saveLabel, setSaveLabel] = useState("Trường học");
  const [customLabel, setCustomLabel] = useState("");
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      // Reset state
      setQuery("");
      setCandidates([]);
      setSelectedCandidate(null);
      setSaveSuccess(null);
      setSaveError(null);
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    setCandidates([]);
    setSelectedCandidate(null);
    setSaveSuccess(null);
    setSaveError(null);

    try {
      const results = await searchLocations(trimmed);
      setCandidates(results);
      if (results.length === 0) {
        setError("Không tìm thấy địa điểm nào khớp với tìm kiếm.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đã xảy ra lỗi khi tìm kiếm.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCandidate = (candidate: SearchLocationCandidate) => {
    setSelectedCandidate(candidate);
    setSaveSuccess(null);
    setSaveError(null);
  };

  // Helper to check distance between coordinates (Haversine formula)
  const isDuplicateLocation = (lat1: number, lon1: number) => {
    const R = 6371000; // Earth's radius in meters
    for (const loc of savedLocations) {
      const dLat = ((loc.latitude - lat1) * Math.PI) / 180;
      const dLon = ((loc.longitude - lon1) * Math.PI) / 180;
      const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos((lat1 * Math.PI) / 180) *
          Math.cos((loc.latitude * Math.PI) / 180) *
          Math.sin(dLon / 2) *
          Math.sin(dLon / 2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      const distance = R * c;

      if (distance < 200 || loc.display_name.trim().toLowerCase() === selectedCandidate?.display_name.trim().toLowerCase()) {
        return true;
      }
    }
    return false;
  };

  const handleSaveLocation = async () => {
    if (!selectedCandidate) return;

    setSaveError(null);
    setSaveSuccess(null);

    // Validate duplicate
    if (isDuplicateLocation(selectedCandidate.latitude, selectedCandidate.longitude)) {
      setSaveError("Vị trí này đã được lưu.");
      return;
    }

    const label = saveLabel === "Tùy chỉnh" ? customLabel.trim() || "Vị trí của tôi" : saveLabel;
    
    try {
      await addLocation({
        label,
        display_name: selectedCandidate.display_name,
        short_display_name: selectedCandidate.short_display_name || label,
        latitude: selectedCandidate.latitude,
        longitude: selectedCandidate.longitude,
        source: "user_confirmed",
        administrative_levels: selectedCandidate.administrative_levels,
        is_default: false,
      });

      setSaveSuccess("Đã lưu vị trí thành công!");
      setTimeout(() => {
        // Trigger active location selection
        onSelectLocation(selectedCandidate);
        onClose();
      }, 1000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Không thể lưu vị trí.");
    }
  };

  const handleSelectWithoutSaving = () => {
    if (!selectedCandidate) return;
    onSelectLocation(selectedCandidate);
    onClose();
  };

  const labelOptions = [
    { value: "Trường học", label: "Trường học" },
    { value: "Nhà", label: "Nhà" },
    { value: "Ký túc xá", label: "Ký túc xá" },
    { value: "Phòng trọ", label: "Phòng trọ" },
    { value: "Tùy chỉnh", label: "Tùy chỉnh..." },
  ];

  return (
    <div className="auth-modal-overlay location-modal-overlay">
      <div className="auth-modal-container location-modal-container glass-effect" ref={modalRef}>
        <button type="button" className="auth-modal-close" onClick={onClose} aria-label="Đóng">
          <X size={20} />
        </button>

        <h2 className="modal-title">Tìm kiếm vị trí mới</h2>
        <p className="modal-description">
          Nhập tên trường học, xã, phường, quận, huyện hoặc tỉnh/thành phố để xem dự báo thời tiết.
        </p>

        <form onSubmit={handleSearch} className="modal-search-form inline-search-form">
          <div className="search-input-wrapper">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Nhập tên trường, địa điểm, xã/phường..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
          </div>
          <button type="submit" disabled={loading} className="search-submit-btn">
            {loading ? "Đang tìm..." : "Tìm kiếm"}
          </button>
        </form>

        {loading && <div className="modal-status loading">Đang tìm kiếm địa điểm...</div>}
        {error && <div className="modal-status error">{error}</div>}

        {candidates.length > 0 && (
          <div className="modal-candidates-box">
            <p className="candidates-title">Kết quả tìm kiếm ({candidates.length}):</p>
            <ul className="candidates-list custom-scrollbar">
              {candidates.map((candidate, idx) => {
                const isSelected =
                  selectedCandidate &&
                  selectedCandidate.latitude === candidate.latitude &&
                  selectedCandidate.longitude === candidate.longitude;

                return (
                  <li key={`${candidate.latitude}-${candidate.longitude}-${idx}`}>
                    <button
                      type="button"
                      className={`candidate-item-btn ${isSelected ? "selected" : ""}`}
                      onClick={() => handleSelectCandidate(candidate)}
                    >
                      <MapPin size={14} />
                      <span className="candidate-name">{candidate.display_name}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {selectedCandidate && (
          <div className="selected-candidate-preview glass-card animate-slide-up">
            <h3>📍 Địa điểm đã chọn</h3>
            <p className="display-name">{selectedCandidate.display_name}</p>
            <p className="coords-sub">
              Tọa độ: {selectedCandidate.latitude.toFixed(4)}, {selectedCandidate.longitude.toFixed(4)}
            </p>

            {saveSuccess && <div className="inline-success-banner">{saveSuccess}</div>}
            {saveError && <div className="inline-error-banner">{saveError}</div>}

            <div className="save-location-form">
              <div className="form-group">
                <label className="field-label">Loại vị trí để lưu (Tùy chọn)</label>
                <CustomSelect
                  value={saveLabel}
                  onChange={setSaveLabel}
                  options={labelOptions}
                />
              </div>

              {saveLabel === "Tùy chỉnh" && (
                <div className="form-group animate-slide-up">
                  <label className="field-label">Tên nhãn tùy chỉnh</label>
                  <input
                    type="text"
                    placeholder="Ví dụ: Thư viện, Quán cafe..."
                    value={customLabel}
                    onChange={(e) => setCustomLabel(e.target.value)}
                    className="modal-text-input"
                  />
                </div>
              )}

              <div className="modal-actions-row">
                <button
                  type="button"
                  className="btn-secondary flex-1"
                  onClick={handleSelectWithoutSaving}
                >
                  <Check size={16} />
                  <span>Xem thời tiết ngay</span>
                </button>
                <button
                  type="button"
                  className="btn-primary flex-1"
                  onClick={handleSaveLocation}
                >
                  <Save size={16} />
                  <span>Lưu vị trí này</span>
                </button>
              </div>
              {!currentUser && (
                <p className="guest-reminder">
                  💡 Bạn đang dùng chế độ Khách. Vị trí sẽ lưu tạm ở trình duyệt này. Đăng nhập để lưu lâu dài.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
