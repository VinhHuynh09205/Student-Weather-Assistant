import { useState, useEffect } from "react";
import {
  Bell,
  CircleGauge,
  Info,
  MapPin,
  Check,
  Trash2,
  Plus,
  Thermometer,
  Eye,
  Tv,
  Calendar,
  Compass,
  Search,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import type { ReactNode } from "react";
import { useAuth } from "../context/AuthContext";
import { formatLocationDisplay } from "../utils/formatters";
import { searchLocations } from "../api/weatherApi";
import type { CurrentWeatherResponse, SearchLocationCandidate, UserNotification } from "../types/weather";
import { CustomSelect } from "../components/common/CustomSelect";
import * as userApi from "../api/userApi";


type SettingsPageProps = {
  currentWeather: CurrentWeatherResponse | null;
  hasSavedSchedule: boolean;
  onOpenLogin?: () => void;
  onOpenStudyAssistant?: () => void;
};

export function SettingsPage({ currentWeather, onOpenLogin, onOpenStudyAssistant }: SettingsPageProps) {
  const {
    currentUser,
    settings,
    updateSettings,
    savedLocations,
    addLocation,
    removeLocation,
    setDefaultLoc,
    logout,
  } = useAuth();

  // Notification states
  const [notificationSuccessMsg, setNotificationSuccessMsg] = useState("");
  const [notificationErrorMsg, setNotificationErrorMsg] = useState("");
  const [notificationsList, setNotificationsList] = useState<UserNotification[]>([]);

  useEffect(() => {
    if (currentUser && settings.notification_enabled) {
      userApi.getUserNotifications()
        .then(setNotificationsList)
        .catch(err => console.error("Failed to load notifications:", err));
    }
  }, [currentUser, settings.notification_enabled]);

  const handleNotificationToggle = async (checked: boolean) => {
    setNotificationSuccessMsg("");
    setNotificationErrorMsg("");

    if (checked) {
      if (!("Notification" in window)) {
        setNotificationErrorMsg("Trình duyệt này không hỗ trợ thông báo.");
        updateSettings({ notification_enabled: false });
        return;
      }

      try {
        const permission = await Notification.requestPermission();
        if (permission === "granted") {
          await updateSettings({ notification_enabled: true });
          setNotificationSuccessMsg("Đã bật thông báo thành công. Nếu muốn thay đổi, hãy vào Cài đặt.");
          setTimeout(() => setNotificationSuccessMsg(""), 5000);
        } else {
          await updateSettings({ notification_enabled: false });
          setNotificationErrorMsg("Trình duyệt đã chặn thông báo. Hãy bật lại trong cài đặt trình duyệt.");
          setTimeout(() => setNotificationErrorMsg(""), 6000);
        }
      } catch (err) {
        console.error("Error requesting notification permission:", err);
        setNotificationErrorMsg("Không thể yêu cầu quyền thông báo.");
      }
    } else {
      await updateSettings({ notification_enabled: false });
    }
  };

  const handleSendTestNotification = async () => {
    setNotificationSuccessMsg("");
    setNotificationErrorMsg("");
    try {
      const res = await userApi.sendTestNotification();
      
      // Refresh list
      const list = await userApi.getUserNotifications();
      setNotificationsList(list);

      // Trigger local browser notification if permission granted and latest test exists
      const latestTest = list.find(n => n.type === "test_alert");
      if (latestTest && Notification.permission === "granted" && (latestTest.channel === "browser" || latestTest.channel === "in_app")) {
        try {
          new Notification(latestTest.title, {
            body: latestTest.message,
          });
        } catch (err) {
          console.error("Error showing local test notification:", err);
        }
      }

      // Check for failures
      if (res.channels_failed.includes("email")) {
        setNotificationErrorMsg(`Thất bại: ${res.message}`);
      } else if (res.channels_failed.length > 0) {
        setNotificationErrorMsg(`Gửi thử nghiệm thất bại trên kênh: ${res.channels_failed.join(", ")}. ${res.message}`);
      } else {
        setNotificationSuccessMsg(res.message);
      }
      
      setTimeout(() => {
        setNotificationSuccessMsg("");
        setNotificationErrorMsg("");
      }, 8000);
    } catch (err) {
      setNotificationErrorMsg(err instanceof Error ? err.message : "Gửi thông báo thử nghiệm thất bại.");
    }
  };


  // Location Form State
  const [newLocLabel, setNewLocLabel] = useState("Trường học");
  const [newLocCustomLabel, setNewLocCustomLabel] = useState("");
  const [newLocDisplayName, setNewLocDisplayName] = useState("");
  const [addLocError, setAddLocError] = useState("");
  const [addLocSuccess, setAddLocSuccess] = useState("");

  // Geocoding states in form
  const [locSearchQuery, setLocSearchQuery] = useState("");
  const [locSearchCandidates, setLocSearchCandidates] = useState<SearchLocationCandidate[]>([]);
  const [isLocSearching, setIsLocSearching] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<SearchLocationCandidate | null>(null);

  // Advanced coordinates options
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [newLocLat, setNewLocLat] = useState("");
  const [newLocLon, setNewLocLon] = useState("");

  const currentLocationName = formatLocationDisplay(currentWeather) || "thành phố đã tìm";

  const handleLocSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = locSearchQuery.trim();
    if (!trimmed) return;

    setIsLocSearching(true);
    setAddLocError("");
    setLocSearchCandidates([]);
    setSelectedCandidate(null);

    try {
      const results = await searchLocations(trimmed);
      setLocSearchCandidates(results);
      if (results.length === 0) {
        setAddLocError("Không tìm thấy địa điểm nào khớp với tìm kiếm.");
      }
    } catch (err) {
      setAddLocError(err instanceof Error ? err.message : "Đã xảy ra lỗi khi tìm kiếm địa điểm.");
    } finally {
      setIsLocSearching(false);
    }
  };

  const handleSelectCandidate = (candidate: SearchLocationCandidate) => {
    setSelectedCandidate(candidate);
    setNewLocLat(String(candidate.latitude));
    setNewLocLon(String(candidate.longitude));
    setNewLocDisplayName(candidate.display_name);
  };

  // Proximity check (Haversine formula) to prevent duplicate locations within 200m
  const isDuplicateLocation = (lat: number, lon: number, displayName: string) => {
    const R = 6371000; // Earth's radius in meters
    for (const loc of savedLocations) {
      const dLat = ((loc.latitude - lat) * Math.PI) / 180;
      const dLon = ((loc.longitude - lon) * Math.PI) / 180;
      const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos((lat * Math.PI) / 180) *
          Math.cos((loc.latitude * Math.PI) / 180) *
          Math.sin(dLon / 2) *
          Math.sin(dLon / 2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      const distance = R * c;

      if (distance < 200 || loc.display_name.trim().toLowerCase() === displayName.trim().toLowerCase()) {
        return true;
      }
    }
    return false;
  };

  const handleAddLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddLocError("");
    setAddLocSuccess("");

    let lat = parseFloat(newLocLat);
    let lon = parseFloat(newLocLon);

    if (selectedCandidate && isNaN(lat)) {
      lat = selectedCandidate.latitude;
      lon = selectedCandidate.longitude;
    }

    if (isNaN(lat) || isNaN(lon)) {
      setAddLocError("Vui lòng tìm và chọn địa điểm hoặc nhập tọa độ hợp lệ.");
      return;
    }

    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      setAddLocError("Vĩ độ phải từ -90 đến 90. Kinh độ phải từ -180 đến 180.");
      return;
    }

    const label = newLocLabel === "Tùy chỉnh" ? newLocCustomLabel.trim() || "Vị trí của tôi" : newLocLabel;
    const displayName = newLocDisplayName.trim() || selectedCandidate?.display_name || `${label} (${lat.toFixed(3)}, ${lon.toFixed(3)})`;

    // Validate duplicate
    if (isDuplicateLocation(lat, lon, displayName)) {
      setAddLocError("Vị trí này đã được lưu.");
      return;
    }

    try {
      await addLocation({
        label,
        display_name: displayName,
        short_display_name: selectedCandidate?.short_display_name || label,
        latitude: lat,
        longitude: lon,
        source: "user_confirmed",
        administrative_levels: selectedCandidate?.administrative_levels || null,
        is_default: savedLocations.length === 0,
      });

      setAddLocSuccess("Đã lưu vị trí thành công!");
      
      // Reset form
      setNewLocLat("");
      setNewLocLon("");
      setNewLocDisplayName("");
      setNewLocCustomLabel("");
      setLocSearchQuery("");
      setLocSearchCandidates([]);
      setSelectedCandidate(null);
      
      setTimeout(() => setAddLocSuccess(""), 3000);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Không thể lưu vị trí.";
      setAddLocError(errorMsg);
    }
  };

  const prefillWithCurrent = () => {
    if (currentWeather) {
      const curLat = currentWeather.latitude;
      const curLon = currentWeather.longitude;
      const curName = currentWeather.display_name || currentWeather.city || "";

      setNewLocLat(String(curLat));
      setNewLocLon(String(curLon));
      setNewLocDisplayName(curName);
      
      setSelectedCandidate({
        city: currentWeather.city,
        country: currentWeather.country,
        latitude: curLat,
        longitude: curLon,
        timezone: currentWeather.timezone,
        display_name: curName,
        short_display_name: currentWeather.short_display_name,
        administrative_levels: currentWeather.administrative_levels,
        location_confidence: currentWeather.location_confidence || "exact",
        location_provider: currentWeather.location_provider || "fallback",
      });
      setLocSearchQuery(curName);
    }
  };

  const labelOptions = [
    { value: "Trường học", label: "Trường học" },
    { value: "Nhà", label: "Nhà" },
    { value: "Ký túc xá", label: "Ký túc xá" },
    { value: "Phòng trọ", label: "Phòng trọ" },
    { value: "Tùy chỉnh", label: "Tùy chỉnh..." },
  ];

  return (
    <section className="settings-page">
      {!currentUser ? (
        <div className="glass-card auth-reminder-banner">
          <div className="auth-reminder-content">
            <h3>🔐 Đăng nhập để đồng bộ dữ liệu</h3>
            <p>
              Lưu lịch học, danh sách vị trí đã lưu và cài đặt của bạn đồng bộ trên mọi thiết bị.
            </p>
          </div>
          <button type="button" className="btn-primary auth-reminder-btn" onClick={onOpenLogin}>
            Đăng nhập ngay
          </button>
        </div>
      ) : (
        <div className="glass-card settings-account-panel">
          <h2>Tài khoản sinh viên</h2>
          <div className="settings-account-info">
            <img
              src={currentUser.avatar_url || "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"}
              alt="Avatar"
              className="user-profile-avatar"
            />
            <div className="user-profile-info">
              <span className="user-profile-name">{currentUser.full_name || "Sinh viên"}</span>
              <span className="user-profile-email">
                {currentUser.auth_provider === "local" ? currentUser.username : (currentUser.email || "Google Account")}
              </span>
            </div>
            <button type="button" className="btn-secondary settings-logout-btn" onClick={logout}>
              Đăng xuất
            </button>
          </div>
        </div>
      )}

      {/* 1. General App Settings */}
      <section className="glass-card settings-panel">
        <h2>
          <CircleGauge size={22} /> Cài đặt ứng dụng
        </h2>

        {/* Temperature Unit Setting */}
        <div className="setting-control-row">
          <SettingRow
            description="Lựa chọn đơn vị hiển thị nhiệt độ trên toàn bộ ứng dụng."
            icon={<Thermometer size={20} />}
            title="Đơn vị nhiệt độ"
          />
          <div className="segmented-control settings-control">
            <button
              className={settings.temperature_unit === "celsius" ? "active" : ""}
              onClick={() => updateSettings({ temperature_unit: "celsius" })}
            >
              °C (Celsius)
            </button>
            <button
              className={settings.temperature_unit === "fahrenheit" ? "active" : ""}
              onClick={() => updateSettings({ temperature_unit: "fahrenheit" })}
            >
              °F (Fahrenheit)
            </button>
          </div>
        </div>

        {/* Theme Mode Setting */}
        <div className="setting-control-row">
          <SettingRow
            description="Thay đổi giao diện ứng dụng phù hợp với thời gian hoặc sở thích."
            icon={<Eye size={20} />}
            title="Giao diện"
          />
          <div className="segmented-control settings-control">
            <button
              className={settings.theme_mode === "auto" ? "active" : ""}
              onClick={() => updateSettings({ theme_mode: "auto" })}
            >
              Tự động
            </button>
            <button
              className={settings.theme_mode === "dark" ? "active" : ""}
              onClick={() => updateSettings({ theme_mode: "dark" })}
            >
              Tối
            </button>
          </div>
        </div>

        {/* Auto Refresh Toggle */}
        <div className="setting-control-row">
          <SettingRow
            description="Tự động tải lại thời tiết định kỳ khi bạn mở ứng dụng."
            icon={<Tv size={20} />}
            title="Tự động cập nhật thời tiết"
          />
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.auto_refresh_enabled}
              onChange={(e) => updateSettings({ auto_refresh_enabled: e.target.checked })}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        {/* Notification Toggle */}
        <div className="setting-control-row-container" style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <div className="setting-control-row">
            <SettingRow
              description={
                currentUser?.auth_provider === "google"
                  ? "Bạn có thể nhận thông báo qua email Google và trong web."
                  : currentUser?.email
                  ? "Bạn có thể nhận thông báo qua email và trong web."
                  : "Bạn sẽ nhận thông báo trong web. Thêm email nếu muốn nhận qua email."
              }
              icon={<Bell size={20} />}
              title="Thông báo thời tiết"
            />
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.notification_enabled}
                onChange={(e) => handleNotificationToggle(e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
          {notificationSuccessMsg && <div className="inline-success-banner animate-slide-up" style={{ margin: "0.25rem 0" }}>{notificationSuccessMsg}</div>}
          {notificationErrorMsg && <div className="inline-error-banner animate-slide-up" style={{ margin: "0.25rem 0" }}>{notificationErrorMsg}</div>}
        </div>
      </section>

      {/* Collapsible Notification History */}
      {currentUser && settings.notification_enabled && (
        <section className="glass-card settings-panel animate-slide-up">
          <h2 style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Bell size={22} /> Lịch sử thông báo
            </span>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleSendTestNotification}
              style={{ fontSize: "0.8rem", height: "32px", padding: "0 0.75rem", borderRadius: "6px" }}
            >
              Gửi thử nghiệm
            </button>
          </h2>
          <p className="description-text">
            Xem lại các thông báo thời tiết lớp học hoặc thử nghiệm đã nhận.
          </p>

          {notificationsList.length > 0 ? (
            <div className="notifications-history-list" style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "1rem" }}>
              {notificationsList.slice(0, 5).map((n) => {
                const channelLabels: Record<string, string> = {
                  email: "Email",
                  browser: "Web",
                  in_app: "In-app",
                };

                const statusLabels: Record<string, string> = {
                  pending: "Đang chờ",
                  sent: "Đã gửi",
                  failed: "Thất bại",
                  read: "Đã đọc",
                };

                return (
                  <div key={n.id} className="notification-history-item" style={{
                    padding: "0.75rem",
                    background: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                    borderRadius: "0.6rem",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.25rem" }}>
                      <strong style={{ fontSize: "0.85rem", color: "#ffffff" }}>{n.title}</strong>
                      <span className={`status-badge status-${n.status}`} style={{
                        fontSize: "0.65rem",
                        padding: "0.15rem 0.4rem",
                        borderRadius: "4px",
                        fontWeight: "bold",
                        background: n.status === "read" ? "rgba(74, 222, 128, 0.15)" :
                                    n.status === "sent" ? "rgba(59, 130, 246, 0.15)" :
                                    n.status === "failed" ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)",
                        color: n.status === "read" ? "#4ade80" :
                               n.status === "sent" ? "#3b82f6" :
                               n.status === "failed" ? "#ef4444" : "#f59e0b",
                      }}>
                        {statusLabels[n.status] || n.status}
                      </span>
                    </div>
                    <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.7)", margin: "0.25rem 0", whiteSpace: "pre-line" }}>{n.message}</p>
                    {n.status === "failed" && n.error_message && (
                      <p style={{ fontSize: "0.7rem", color: "#ef4444", margin: "0.25rem 0", background: "rgba(239, 68, 68, 0.05)", padding: "0.25rem 0.5rem", borderRadius: "4px" }}>
                        ⚠️ Lỗi: {n.error_message}
                      </p>
                    )}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem 1rem", fontSize: "0.65rem", color: "rgba(255,255,255,0.4)", marginTop: "0.4rem" }}>
                      <span>Kênh: <strong style={{ color: "rgba(255,255,255,0.6)" }}>{channelLabels[n.channel] || n.channel}</strong></span>
                      <span>Tạo lúc: {new Date(n.created_at).toLocaleString("vi-VN")}</span>
                      {n.sent_at && <span>Gửi lúc: {new Date(n.sent_at).toLocaleString("vi-VN")}</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="empty-copy" style={{ marginTop: "0.5rem" }}>Chưa có thông báo nào được lưu.</p>
          )}
        </section>
      )}


      {/* 2. Saved Locations Section */}
      <section className="glass-card settings-panel">
        <h2>
          <MapPin size={22} /> Danh sách vị trí đã lưu
        </h2>
        <p className="description-text">
          Lưu lại tọa độ của Trường, Nhà hoặc KTX để dễ dàng chuyển nhanh vị trí xem thời tiết.
        </p>

        {savedLocations.length > 0 ? (
          <div className="locations-list">
            {savedLocations.map((loc) => (
              <div key={loc.id} className={`location-item-row ${loc.is_default ? "is-default" : ""}`}>
                <div className="location-info">
                  <span className="location-label-badge">{loc.label}</span>
                  <strong>{loc.display_name}</strong>
                  <span className="coords-text">
                    ({loc.latitude.toFixed(4)}, {loc.longitude.toFixed(4)})
                  </span>
                </div>
                <div className="location-actions-row">
                  {loc.is_default ? (
                    <span className="default-badge">
                      <Check size={14} /> Mặc định
                    </span>
                  ) : (
                    <button
                      className="btn-text-action"
                      type="button"
                      onClick={() => setDefaultLoc(loc.id)}
                    >
                      Đặt mặc định
                    </button>
                  )}
                  <button
                    className="btn-icon-danger"
                    type="button"
                    title="Xóa vị trí"
                    onClick={() => removeLocation(loc.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-copy">Chưa có vị trí nào được lưu.</p>
        )}

        {/* Form to add location */}
        <form className="add-location-form" onSubmit={handleAddLocation}>
          <h3>Thêm vị trí mới</h3>
          {addLocError && <div className="inline-error-banner">{addLocError}</div>}
          {addLocSuccess && <div className="inline-success-banner">{addLocSuccess}</div>}
          
          <div className="form-grid-2">
            <div className="form-group">
              <label className="field-label">Loại vị trí</label>
              <CustomSelect
                value={newLocLabel}
                onChange={setNewLocLabel}
                options={labelOptions}
              />
            </div>
            {newLocLabel === "Tùy chỉnh" && (
              <div className="form-group">
                <label className="field-label">Tên nhãn tùy chỉnh</label>
                <input
                  type="text"
                  placeholder="Ví dụ: Thư viện"
                  value={newLocCustomLabel}
                  onChange={(e) => setNewLocCustomLabel(e.target.value)}
                  className="modal-text-input"
                  required
                />
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="field-label">Tìm kiếm địa điểm</label>
            <div className="inline-search-form" style={{ marginTop: 0 }} onClick={(e) => e.stopPropagation()}>
              <div className="search-input-wrapper">
                <Search size={18} className="search-icon" />
                <input
                  type="text"
                  placeholder="Nhập tên trường, địa chỉ, xã/phường, quận/huyện..."
                  value={locSearchQuery}
                  onChange={(e) => setLocSearchQuery(e.target.value)}
                />
              </div>
              <button type="button" onClick={handleLocSearch} disabled={isLocSearching} className="search-submit-btn">
                {isLocSearching ? "Đang tìm..." : "Tìm kiếm"}
              </button>
            </div>
          </div>

          {locSearchCandidates.length > 0 && (
            <div className="modal-candidates-box" style={{ marginBottom: "1.5rem" }}>
              <p className="candidates-title">Chọn vị trí chính xác từ kết quả tìm kiếm:</p>
              <ul className="candidates-list custom-scrollbar">
                {locSearchCandidates.map((candidate, idx) => {
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
            <div className="selected-candidate-preview animate-slide-up" style={{ marginTop: 0, marginBottom: "1rem" }}>
              <p className="display-name" style={{ fontSize: "0.9rem" }}>📍 {selectedCandidate.display_name}</p>
              <span className="coords-text" style={{ fontSize: "0.8rem", color: "rgba(255, 255, 255, 0.45)" }}>
                Tọa độ: {selectedCandidate.latitude.toFixed(4)}, {selectedCandidate.longitude.toFixed(4)}
              </span>
            </div>
          )}

          {/* Advanced options for coordinate editing */}
          <div className="advanced-coords-container">
            <button
              type="button"
              className="tech-details-toggle-btn"
              onClick={() => setShowAdvanced(!showAdvanced)}
              style={{ display: "flex", alignItems: "center", gap: "0.25rem", margin: "0.5rem 0" }}
            >
              <span>{showAdvanced ? "Ẩn tùy chọn nâng cao" : "Hiện tùy chọn nâng cao"}</span>
              {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showAdvanced && (
              <div className="tech-details-expanded-content animate-slide-up" style={{ background: "rgba(0, 0, 0, 0.12)" }}>
                <div className="form-grid-2">
                  <div className="form-group">
                    <label className="field-label" style={{ fontSize: "0.85rem" }}>Vĩ độ (Latitude)</label>
                    <input
                      type="text"
                      placeholder="Ví dụ: 10.334"
                      value={newLocLat}
                      onChange={(e) => setNewLocLat(e.target.value)}
                      className="modal-text-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="field-label" style={{ fontSize: "0.85rem" }}>Kinh độ (Longitude)</label>
                    <input
                      type="text"
                      placeholder="Ví dụ: 106.353"
                      value={newLocLon}
                      onChange={(e) => setNewLocLon(e.target.value)}
                      className="modal-text-input"
                    />
                  </div>
                </div>
                <div className="form-group" style={{ marginTop: "0.5rem" }}>
                  <label className="field-label" style={{ fontSize: "0.85rem" }}>Tên hiển thị tùy chọn</label>
                  <input
                    type="text"
                    placeholder="Ví dụ: Đại học Bách Khoa TP.HCM"
                    value={newLocDisplayName}
                    onChange={(e) => setNewLocDisplayName(e.target.value)}
                    className="modal-text-input"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="form-buttons-row" style={{ marginTop: "1rem" }}>
            <button className="btn-secondary" type="button" onClick={prefillWithCurrent}>
              <Compass size={16} /> Lấy vị trí đang xem ({currentLocationName.split("·")[0].trim()})
            </button>
            <button className="btn-primary" type="submit">
              <Plus size={16} /> Thêm vị trí
            </button>
          </div>
        </form>
      </section>

      {/* 3. Schedules navigation redirect instead of list */}
      <section className="glass-card settings-panel">
        <h2>
          <Calendar size={22} /> Lịch học của bạn
        </h2>
        <p className="description-text">
          Thiết lập lịch đi học của bạn để trợ lý tự động phân tích độ thuận lợi, cảnh báo thời tiết và đưa ra lời khuyên chuẩn bị đi học.
        </p>
        <div className="form-buttons-row" style={{ marginTop: "1.25rem" }}>
          <button
            type="button"
            className="btn-primary"
            onClick={onOpenStudyAssistant}
            style={{ width: "100%", justifyContent: "center" }}
          >
            <Calendar size={16} />
            <span>Quản lý lịch học tại Trợ lý đi học</span>
          </button>
        </div>
      </section>

      {/* 4. About App */}
      <section className="glass-card about-card">
        <h2>
          <Info size={22} /> Về ứng dụng
        </h2>
        <p>
          <strong>Student Weather Assistant</strong> là ứng dụng hỗ trợ học sinh, sinh viên theo dõi thời tiết thực
          tế tại địa phương, dự báo thời tiết hàng ngày và tự động phân tích độ thuận lợi cho lịch đi học của bạn.
        </p>
        <div>
          <span>Phiên bản</span>
          <strong>2.0.0</strong>
        </div>
      </section>
    </section>
  );
}

function SettingRow({
  description,
  icon,
  title,
}: {
  description: string;
  icon: ReactNode;
  title: string;
}) {
  return (
    <div className="setting-row-inner">
      <span className="setting-icon-box">{icon}</span>
      <div className="setting-text-box">
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
    </div>
  );
}
