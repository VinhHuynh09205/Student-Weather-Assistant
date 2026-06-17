import {
  Bell,
  CheckCircle2,
  ChevronDown,
  CloudRain,
  Crosshair,
  ListChecks,
  MapPin,
  NotebookPen,
  Power,
  RotateCcw,
  Search,
  SlidersHorizontal,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import { searchLocations } from "../../api/weatherApi";
import type { WeeklyClassSchedule, WeeklyClassSchedulePayload } from "../../types/classSchedule";
import type { SearchLocationCandidate, VehicleType } from "../../types/weather";
import { normalizeTimeForInput } from "../../utils/classScheduleFormatters";
import { normalizeVehicleType, vehicleOptions } from "../../utils/formatters";
import { DatePickerField } from "./DatePickerField";
import { DayOfWeekSelector } from "./DayOfWeekSelector";
import { TimeRangeInput } from "./TimeRangeInput";

type WeeklyScheduleFormValues = {
  subject_name: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  vehicle_type: VehicleType;
  location_name: string;
  latitude: string;
  longitude: string;
  notify_before_minutes: string;
  rain_alert_enabled: boolean;
  storm_alert_enabled: boolean;
  semester_start_date: string;
  semester_end_date: string;
  is_active: boolean;
};

type WeeklyScheduleFormErrors = Partial<Record<keyof WeeklyScheduleFormValues, string>>;

type CurrentClassLocation = {
  name: string;
  latitude?: number | null;
  longitude?: number | null;
};

type WeeklyScheduleFormProps = {
  schedule: WeeklyClassSchedule | null;
  apiError?: string | null;
  currentLocation?: CurrentClassLocation;
  isSubmitting: boolean;
  onCancel: () => void;
  onViewScheduleList: () => void;
  onSubmit: (payload: WeeklyClassSchedulePayload) => Promise<void>;
};

const reminderQuickOptions = [30, 60, 120, 180];
const locationSearchDebounceMs = 420;

const defaultValues: WeeklyScheduleFormValues = {
  subject_name: "",
  day_of_week: 0,
  start_time: "07:00",
  end_time: "09:00",
  vehicle_type: "motorbike",
  location_name: "",
  latitude: "",
  longitude: "",
  notify_before_minutes: "120",
  rain_alert_enabled: true,
  storm_alert_enabled: true,
  semester_start_date: "",
  semester_end_date: "",
  is_active: true,
};

export function WeeklyScheduleForm({
  schedule,
  apiError,
  currentLocation,
  isSubmitting,
  onCancel,
  onViewScheduleList,
  onSubmit,
}: WeeklyScheduleFormProps) {
  const [values, setValues] = useState<WeeklyScheduleFormValues>(() => getInitialValues(schedule));
  const [errors, setErrors] = useState<WeeklyScheduleFormErrors>({});
  const [createSuccess, setCreateSuccess] = useState(false);
  const [showAdvancedLocation, setShowAdvancedLocation] = useState(false);
  const [locationSearchQuery, setLocationSearchQuery] = useState("");
  const [locationCandidates, setLocationCandidates] = useState<SearchLocationCandidate[]>([]);
  const [isLocationSearching, setIsLocationSearching] = useState(false);
  const [locationSearchError, setLocationSearchError] = useState<string | null>(null);
  const [isLocationDropdownOpen, setIsLocationDropdownOpen] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const locationSearchRef = useRef<HTMLDivElement>(null);
  const locationSearchRequestRef = useRef(0);

  const isEditing = Boolean(schedule);
  const hasCurrentCoordinates =
    currentLocation &&
    typeof currentLocation.latitude === "number" &&
    typeof currentLocation.longitude === "number";

  const resetLocationSearch = useCallback(() => {
    locationSearchRequestRef.current += 1;
    setLocationSearchQuery("");
    setLocationCandidates([]);
    setLocationSearchError(null);
    setIsLocationSearching(false);
    setIsLocationDropdownOpen(false);
  }, []);

  const keepLocationSearchVisible = useCallback(() => {
    const alignLocationSearch = () => {
      const scrollArea = scrollAreaRef.current;
      const searchField = locationSearchRef.current;
      if (!scrollArea || !searchField) return;

      const scrollAreaRect = scrollArea.getBoundingClientRect();
      const searchFieldRect = searchField.getBoundingClientRect();
      const preferredOffset = Math.min(220, Math.max(140, scrollAreaRect.height * 0.36));
      const safeTop = scrollAreaRect.top + 16;
      const safeBottom = scrollAreaRect.bottom - Math.min(180, Math.max(120, scrollAreaRect.height * 0.28));

      if (searchFieldRect.top >= safeTop && searchFieldRect.bottom <= safeBottom) return;

      const targetTop = scrollArea.scrollTop + searchFieldRect.top - scrollAreaRect.top - preferredOffset;
      scrollArea.scrollTo({ top: Math.max(0, targetTop), behavior: "auto" });
    };

    window.requestAnimationFrame(alignLocationSearch);
    window.setTimeout(alignLocationSearch, 80);
  }, []);

  useEffect(() => {
    setValues(getInitialValues(schedule));
    setErrors({});
    setCreateSuccess(false);
    setShowAdvancedLocation(false);
    resetLocationSearch();
  }, [resetLocationSearch, schedule]);

  useEffect(() => {
    const requestId = locationSearchRequestRef.current + 1;
    locationSearchRequestRef.current = requestId;
    const trimmed = locationSearchQuery.trim();

    if (trimmed.length < 2) {
      setLocationCandidates([]);
      setLocationSearchError(null);
      setIsLocationSearching(false);
      return undefined;
    }

    setIsLocationSearching(true);
    setLocationSearchError(null);
    setIsLocationDropdownOpen(true);

    const timeoutId = window.setTimeout(async () => {
      try {
        const results = await searchLocations(trimmed);
        if (locationSearchRequestRef.current !== requestId) return;
        setLocationCandidates(prioritizeLocationCandidates(results, currentLocation));
      } catch {
        if (locationSearchRequestRef.current !== requestId) return;
        setLocationCandidates([]);
        setLocationSearchError("Không thể tìm địa điểm lúc này. Bạn vẫn có thể nhập địa chỉ thủ công.");
      } finally {
        if (locationSearchRequestRef.current === requestId) {
          setIsLocationSearching(false);
        }
      }
    }, locationSearchDebounceMs);

    return () => window.clearTimeout(timeoutId);
  }, [currentLocation, locationSearchQuery]);

  useEffect(() => {
    if (!isLocationDropdownOpen) return undefined;

    const handlePointerDown = (event: PointerEvent) => {
      if (locationSearchRef.current?.contains(event.target as Node)) return;
      setIsLocationDropdownOpen(false);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsLocationDropdownOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isLocationDropdownOpen]);

  const semesterHint = useMemo(() => {
    if (!values.semester_start_date && !values.semester_end_date) {
      return "Bỏ trống nếu lịch học không giới hạn theo học kỳ.";
    }
    return "Hệ thống chỉ hiện buổi học nằm trong khoảng học kỳ này.";
  }, [values.semester_end_date, values.semester_start_date]);

  const updateValue = <K extends keyof WeeklyScheduleFormValues>(key: K, value: WeeklyScheduleFormValues[K]) => {
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
    setCreateSuccess(false);
  };

  const handleLocationInputChange = (value: string) => {
    if (value.trim().length >= 2) {
      keepLocationSearchVisible();
    }

    setValues((current) => ({
      ...current,
      location_name: value,
      latitude: "",
      longitude: "",
    }));
    setErrors((current) => ({
      ...current,
      location_name: undefined,
      latitude: undefined,
      longitude: undefined,
    }));
    setLocationSearchQuery(value);
    setIsLocationDropdownOpen(value.trim().length >= 2);
    setCreateSuccess(false);
  };

  const handleSelectLocationCandidate = (candidate: SearchLocationCandidate) => {
    const displayName = candidate.display_name || candidate.short_display_name || candidate.city;
    setValues((current) => ({
      ...current,
      location_name: displayName,
      latitude: String(candidate.latitude),
      longitude: String(candidate.longitude),
    }));
    setErrors((current) => ({
      ...current,
      location_name: undefined,
      latitude: undefined,
      longitude: undefined,
    }));
    setCreateSuccess(false);
    resetLocationSearch();
  };

  const handleUseCurrentLocation = () => {
    if (!currentLocation) return;
    const friendlyLocationName = currentLocation.name.trim() || "Vị trí thời tiết hiện tại";
    setValues((current) => ({
      ...current,
      location_name: friendlyLocationName,
      latitude: typeof currentLocation.latitude === "number" ? String(currentLocation.latitude) : current.latitude,
      longitude: typeof currentLocation.longitude === "number" ? String(currentLocation.longitude) : current.longitude,
    }));
    setErrors((current) => ({
      ...current,
      location_name: undefined,
      latitude: undefined,
      longitude: undefined,
    }));
    setCreateSuccess(false);
    resetLocationSearch();
  };

  const handleCreateNext = () => {
    setValues((current) => ({
      ...defaultValues,
      location_name: current.location_name,
      latitude: current.latitude,
      longitude: current.longitude,
      vehicle_type: current.vehicle_type,
      notify_before_minutes: current.notify_before_minutes,
      rain_alert_enabled: current.rain_alert_enabled,
      storm_alert_enabled: current.storm_alert_enabled,
    }));
    setErrors({});
    setCreateSuccess(false);
    setShowAdvancedLocation(false);
    window.setTimeout(() => {
      scrollAreaRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    }, 0);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = validateForm(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    try {
      await onSubmit(toPayload(values));
      if (!isEditing) {
        setCreateSuccess(true);
      }
    } catch {
      // Parent page owns the API error message and toast.
    }
  };

  const trimmedLocationSearch = locationSearchQuery.trim();
  const shouldShowLocationDropdown = isLocationDropdownOpen && trimmedLocationSearch.length >= 2;

  return (
    <form className="class-schedule-form" onSubmit={handleSubmit}>
      <div className="class-form-scroll-area" ref={scrollAreaRef}>
      <div className="class-form-section">
        <div className="class-form-section-title">
          <NotebookPen size={18} aria-hidden="true" />
          <span>Thông tin môn học</span>
        </div>

        <label className="class-form-group">
          <span className="class-field-label">Tên môn học</span>
          <span className="class-input-shell">
            <NotebookPen size={18} aria-hidden="true" />
            <input
              type="text"
              value={values.subject_name}
              placeholder="Ví dụ: Cấu trúc dữ liệu"
              onChange={(event) => updateValue("subject_name", event.target.value)}
            />
          </span>
          {errors.subject_name ? <p className="class-field-error">{errors.subject_name}</p> : null}
        </label>

        <DayOfWeekSelector
          value={values.day_of_week}
          error={errors.day_of_week}
          onChange={(value) => updateValue("day_of_week", value)}
        />

        <TimeRangeInput
          startTime={values.start_time}
          endTime={values.end_time}
          startError={errors.start_time}
          endError={errors.end_time}
          onStartTimeChange={(value) => updateValue("start_time", value)}
          onEndTimeChange={(value) => updateValue("end_time", value)}
        />

        <div className="class-form-group">
          <span className="class-field-label">Phương tiện di chuyển</span>
          <div className="class-vehicle-choice-grid" aria-label="Chọn phương tiện đi học">
            {vehicleOptions.map((vehicle) => (
              <button
                key={vehicle.id}
                className={values.vehicle_type === vehicle.id ? "selected" : ""}
                type="button"
                onClick={() => updateValue("vehicle_type", vehicle.id)}
              >
                <span>{vehicle.icon}</span>
                {vehicle.label}
              </button>
            ))}
          </div>
          <span className="class-form-hint">
            Hệ thống dùng phương tiện để gợi ý áo mưa, thời gian đi sớm, kẹt xe hoặc đường trơn phù hợp hơn.
          </span>
        </div>
      </div>

      <div className="class-form-section">
        <div className="class-form-section-title">
          <MapPin size={18} aria-hidden="true" />
          <span>Địa điểm học</span>
        </div>

        <div className="class-form-group class-location-search-field" ref={locationSearchRef}>
          <label className="class-field-label" htmlFor="weekly-class-location-input">
            Tên trường / Cơ sở / Địa chỉ học
          </label>
          <div className="class-location-autocomplete">
            <span className="class-input-shell class-location-input-shell">
              <Search size={18} aria-hidden="true" />
              <input
                id="weekly-class-location-input"
                type="text"
                value={values.location_name}
                placeholder="Ví dụ: Đại học Công Thương TP.HCM, cơ sở 140 Lê Trọng Tấn"
                autoComplete="off"
                aria-autocomplete="list"
                aria-expanded={shouldShowLocationDropdown}
                aria-controls="weekly-class-location-suggestions"
                onFocus={() => {
                  keepLocationSearchVisible();
                  if (trimmedLocationSearch.length >= 2) {
                    setIsLocationDropdownOpen(true);
                  }
                }}
                onChange={(event) => handleLocationInputChange(event.target.value)}
              />
            </span>

            {shouldShowLocationDropdown ? (
              <div
                className="class-location-suggestion-panel"
                id="weekly-class-location-suggestions"
                role="listbox"
                aria-label="Gợi ý địa điểm học"
              >
                {isLocationSearching ? (
                  <div className="class-location-search-state">Đang tìm địa điểm phù hợp...</div>
                ) : locationSearchError ? (
                  <div className="class-location-search-state error">{locationSearchError}</div>
                ) : locationCandidates.length > 0 ? (
                  <ul className="class-location-suggestion-list">
                    {locationCandidates.map((candidate, index) => (
                      <li key={`${candidate.latitude}-${candidate.longitude}-${index}`}>
                        <button type="button" onClick={() => handleSelectLocationCandidate(candidate)}>
                          <MapPin size={16} aria-hidden="true" />
                          <span>
                            <strong>{getLocationPrimaryText(candidate)}</strong>
                            {getLocationSecondaryText(candidate) ? <small>{getLocationSecondaryText(candidate)}</small> : null}
                            {getLocationAreaText(candidate) ? <em>{getLocationAreaText(candidate)}</em> : null}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="class-location-search-state">
                    Không tìm thấy địa điểm phù hợp. Bạn có thể nhập địa chỉ thủ công.
                  </div>
                )}
              </div>
            ) : null}
          </div>
          <span className="class-form-hint">
            Bạn có thể nhập tên trường, cơ sở, phòng học hoặc địa chỉ quen thuộc. Tọa độ chỉ dùng khi cần dự báo
            chính xác hơn.
          </span>
          {errors.location_name ? <p className="class-field-error">{errors.location_name}</p> : null}
        </div>

        {currentLocation ? (
          <button className="class-use-current-location" type="button" onClick={handleUseCurrentLocation}>
            <Crosshair size={16} aria-hidden="true" />
            <span>{hasCurrentCoordinates ? "Dùng vị trí thời tiết hiện tại" : "Dùng tên khu vực hiện tại"}</span>
          </button>
        ) : null}

        <div className="class-advanced-location">
          <button
            className={`class-advanced-toggle ${showAdvancedLocation ? "open" : ""}`}
            type="button"
            aria-expanded={showAdvancedLocation}
            onClick={() => setShowAdvancedLocation((current) => !current)}
          >
            <SlidersHorizontal size={16} aria-hidden="true" />
            <span>Tùy chọn nâng cao</span>
            <ChevronDown className="class-picker-chevron" size={16} aria-hidden="true" />
          </button>

          {showAdvancedLocation ? (
            <div className="class-advanced-location-panel">
              <p className="class-form-hint">
                Chỉ nhập vĩ độ/kinh độ khi bạn biết tọa độ chính xác. Nếu không, hệ thống vẫn dùng tên địa điểm học
                để lưu lịch bình thường.
              </p>
              <div className="class-coordinates-grid">
                <label className="class-form-group">
                  <span className="class-field-label">Vĩ độ</span>
                  <input
                    className="class-plain-input"
                    type="text"
                    inputMode="decimal"
                    value={values.latitude}
                    placeholder="Ví dụ: 10.806"
                    onChange={(event) => updateValue("latitude", event.target.value)}
                  />
                  {errors.latitude ? <p className="class-field-error">{errors.latitude}</p> : null}
                </label>

                <label className="class-form-group">
                  <span className="class-field-label">Kinh độ</span>
                  <input
                    className="class-plain-input"
                    type="text"
                    inputMode="decimal"
                    value={values.longitude}
                    placeholder="Ví dụ: 106.628"
                    onChange={(event) => updateValue("longitude", event.target.value)}
                  />
                  {errors.longitude ? <p className="class-field-error">{errors.longitude}</p> : null}
                </label>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="class-form-section">
        <div className="class-form-section-title">
          <Bell size={18} aria-hidden="true" />
          <span>Cảnh báo & học kỳ</span>
        </div>

        <label className="class-form-group">
          <span className="class-field-label">Nhắc trước giờ học</span>
          <span className="class-input-shell class-number-input-shell">
            <Bell size={18} aria-hidden="true" />
            <input
              type="number"
              min="0"
              max="1440"
              step="5"
              inputMode="numeric"
              value={values.notify_before_minutes}
              placeholder="120"
              onChange={(event) => updateValue("notify_before_minutes", event.target.value)}
            />
            <span className="class-input-suffix">phút</span>
          </span>
          <span className="class-form-hint">
            Ví dụ: 120 phút = 2 giờ trước buổi học. Nhập 0 nếu muốn nhắc đúng giờ học.
          </span>
          <div className="class-reminder-chip-grid" aria-label="Chọn nhanh thời gian nhắc trước">
            {reminderQuickOptions.map((minutes) => (
              <button
                key={minutes}
                className={values.notify_before_minutes === String(minutes) ? "selected" : ""}
                type="button"
                onClick={() => updateValue("notify_before_minutes", String(minutes))}
              >
                {minutes} phút
              </button>
            ))}
          </div>
          {errors.notify_before_minutes ? <p className="class-field-error">{errors.notify_before_minutes}</p> : null}
        </label>

        <div className="class-switch-stack">
          <SwitchRow
            checked={values.rain_alert_enabled}
            icon={<CloudRain size={18} aria-hidden="true" />}
            label="Cảnh báo mưa"
            description="Hiện mức rủi ro khi buổi học có khả năng mưa."
            onChange={(checked) => updateValue("rain_alert_enabled", checked)}
          />
          <SwitchRow
            checked={values.storm_alert_enabled}
            icon={<Zap size={18} aria-hidden="true" />}
            label="Cảnh báo dông"
            description="Ưu tiên cảnh báo mạnh khi có dấu hiệu dông gần giờ học."
            onChange={(checked) => updateValue("storm_alert_enabled", checked)}
          />
          <SwitchRow
            checked={values.is_active}
            icon={<Power size={18} aria-hidden="true" />}
            label="Lịch đang hoạt động"
            description="Tắt khi bạn muốn giữ lịch nhưng chưa cần theo dõi."
            onChange={(checked) => updateValue("is_active", checked)}
          />
        </div>

        <div className="class-semester-grid">
          <DatePickerField
            label="Ngày bắt đầu học kỳ"
            value={values.semester_start_date}
            error={errors.semester_start_date}
            onChange={(value) => updateValue("semester_start_date", value)}
          />
          <DatePickerField
            label="Ngày kết thúc học kỳ"
            value={values.semester_end_date}
            onChange={(value) => updateValue("semester_end_date", value)}
          />
        </div>
        <p className="class-form-hint">{semesterHint}</p>
      </div>

      {apiError ? <p className="class-form-api-error">{apiError}</p> : null}
      {createSuccess && !isEditing ? (
        <div className="class-create-success-panel" role="status">
          <CheckCircle2 size={22} aria-hidden="true" />
          <div>
            <strong>Đã tạo lịch học thành công</strong>
            <p>Danh sách phía sau đã được cập nhật. Bạn có thể tạo thêm lịch khác ngay trong form này.</p>
          </div>
        </div>
      ) : null}
      </div>

      {createSuccess && !isEditing ? (
        <div className="class-form-actions success">
          <button className="class-secondary-button" type="button" onClick={onCancel} disabled={isSubmitting}>
            Đóng
          </button>
          <button className="class-secondary-button" type="button" onClick={onViewScheduleList} disabled={isSubmitting}>
            <ListChecks size={17} aria-hidden="true" />
            Xem danh sách
          </button>
          <button className="class-primary-button" type="button" onClick={handleCreateNext} disabled={isSubmitting}>
            <RotateCcw size={17} aria-hidden="true" />
            Tạo tiếp
          </button>
        </div>
      ) : (
        <div className="class-form-actions">
          <button className="class-secondary-button" type="button" onClick={onCancel} disabled={isSubmitting}>
            Hủy
          </button>
          <button className="class-primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Đang lưu..." : isEditing ? "Cập nhật lịch" : "Tạo lịch học"}
          </button>
        </div>
      )}
    </form>
  );
}

function SwitchRow({
  checked,
  description,
  icon,
  label,
  onChange,
}: {
  checked: boolean;
  description: string;
  icon: ReactNode;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="class-switch-row">
      <span className="class-switch-icon">{icon}</span>
      <span className="class-switch-copy">
        <strong>{label}</strong>
        <small>{description}</small>
      </span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span className="class-switch-track" aria-hidden="true" />
    </label>
  );
}

function prioritizeLocationCandidates(
  candidates: SearchLocationCandidate[],
  currentLocation?: CurrentClassLocation,
): SearchLocationCandidate[] {
  const currentLatitude =
    currentLocation &&
    typeof currentLocation.latitude === "number" &&
    typeof currentLocation.longitude === "number"
      ? currentLocation.latitude
      : null;
  const currentLongitude =
    currentLocation &&
    typeof currentLocation.latitude === "number" &&
    typeof currentLocation.longitude === "number"
      ? currentLocation.longitude
      : null;

  return [...candidates].sort((left, right) => {
    const vietnamDiff = Number(isVietnamLocation(right)) - Number(isVietnamLocation(left));
    if (vietnamDiff !== 0) return vietnamDiff;

    if (currentLatitude !== null && currentLongitude !== null) {
      const leftDistance = calculateDistanceKm(
        currentLatitude,
        currentLongitude,
        left.latitude,
        left.longitude,
      );
      const rightDistance = calculateDistanceKm(
        currentLatitude,
        currentLongitude,
        right.latitude,
        right.longitude,
      );
      return leftDistance - rightDistance;
    }

    return 0;
  });
}

function getLocationPrimaryText(candidate: SearchLocationCandidate): string {
  return candidate.short_display_name || candidate.city || candidate.display_name;
}

function getLocationSecondaryText(candidate: SearchLocationCandidate): string {
  const primary = getLocationPrimaryText(candidate);
  return candidate.display_name && candidate.display_name !== primary ? candidate.display_name : "";
}

function getLocationAreaText(candidate: SearchLocationCandidate): string {
  const admin = candidate.administrative_levels;
  return joinUniqueParts([
    admin?.ward_or_commune,
    admin?.district,
    admin?.province,
    candidate.country,
  ]);
}

function isVietnamLocation(candidate: SearchLocationCandidate): boolean {
  const normalized = normalizeForCompare(candidate.country);
  return normalized === "viet nam" || normalized === "vietnam" || normalized === "vn";
}

function joinUniqueParts(parts: Array<string | null | undefined>): string {
  const seen = new Set<string>();
  const result: string[] = [];

  for (const part of parts) {
    const trimmed = part?.trim();
    if (!trimmed) continue;

    const key = normalizeForCompare(trimmed);
    if (seen.has(key)) continue;

    seen.add(key);
    result.push(trimmed);
  }

  return result.join(" • ");
}

function normalizeForCompare(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function calculateDistanceKm(fromLat: number, fromLon: number, toLat: number, toLon: number): number {
  const earthRadiusKm = 6371;
  const dLat = toRadians(toLat - fromLat);
  const dLon = toRadians(toLon - fromLon);
  const lat1 = toRadians(fromLat);
  const lat2 = toRadians(toLat);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return 2 * earthRadiusKm * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function toRadians(value: number): number {
  return (value * Math.PI) / 180;
}

function getInitialValues(schedule: WeeklyClassSchedule | null): WeeklyScheduleFormValues {
  if (!schedule) return defaultValues;
  return {
    subject_name: schedule.subject_name,
    day_of_week: schedule.day_of_week,
    start_time: normalizeTimeForInput(schedule.start_time),
    end_time: normalizeTimeForInput(schedule.end_time),
    vehicle_type: normalizeVehicleType(schedule.vehicle_type),
    location_name: schedule.location_name ?? "",
    latitude: typeof schedule.latitude === "number" ? String(schedule.latitude) : "",
    longitude: typeof schedule.longitude === "number" ? String(schedule.longitude) : "",
    notify_before_minutes: String(schedule.notify_before_minutes),
    rain_alert_enabled: schedule.rain_alert_enabled,
    storm_alert_enabled: schedule.storm_alert_enabled,
    semester_start_date: schedule.semester_start_date ?? "",
    semester_end_date: schedule.semester_end_date ?? "",
    is_active: schedule.is_active,
  };
}

function validateForm(values: WeeklyScheduleFormValues): WeeklyScheduleFormErrors {
  const errors: WeeklyScheduleFormErrors = {};
  const subject = values.subject_name.trim();
  const location = values.location_name.trim();
  const notifyRaw = values.notify_before_minutes.trim();
  const notifyBefore = Number(values.notify_before_minutes);

  if (!subject) errors.subject_name = "Tên môn học không được để trống.";
  if (!Number.isInteger(values.day_of_week) || values.day_of_week < 0 || values.day_of_week > 6) {
    errors.day_of_week = "Vui lòng chọn thứ học hợp lệ.";
  }
  if (!values.start_time) errors.start_time = "Vui lòng chọn giờ bắt đầu.";
  if (!values.end_time) errors.end_time = "Vui lòng chọn giờ kết thúc.";
  if (values.start_time && values.end_time && values.start_time >= values.end_time) {
    errors.end_time = "Giờ kết thúc phải sau giờ bắt đầu.";
  }
  if (!location) errors.location_name = "Địa điểm học không được để trống.";
  if (!notifyRaw || !Number.isInteger(notifyBefore) || notifyBefore < 0 || notifyBefore > 1440) {
    errors.notify_before_minutes = "Số phút nhắc trước phải từ 0 đến 1440 phút.";
  }

  const hasLatitude = values.latitude.trim() !== "";
  const hasLongitude = values.longitude.trim() !== "";
  const latitude = Number(values.latitude);
  const longitude = Number(values.longitude);
  if (hasLatitude !== hasLongitude) {
    errors.latitude = "Vĩ độ và kinh độ cần được nhập cùng nhau.";
    errors.longitude = "Vĩ độ và kinh độ cần được nhập cùng nhau.";
  } else if (hasLatitude && (Number.isNaN(latitude) || latitude < -90 || latitude > 90)) {
    errors.latitude = "Vĩ độ phải là số từ -90 đến 90.";
  } else if (hasLongitude && (Number.isNaN(longitude) || longitude < -180 || longitude > 180)) {
    errors.longitude = "Kinh độ phải là số từ -180 đến 180.";
  }

  if (
    values.semester_start_date &&
    values.semester_end_date &&
    values.semester_start_date > values.semester_end_date
  ) {
    errors.semester_start_date = "Ngày bắt đầu học kỳ không được sau ngày kết thúc.";
  }

  return errors;
}

function toPayload(values: WeeklyScheduleFormValues): WeeklyClassSchedulePayload {
  const latitude = values.latitude.trim() ? Number(values.latitude) : null;
  const longitude = values.longitude.trim() ? Number(values.longitude) : null;

  return {
    subject_name: values.subject_name.trim(),
    day_of_week: values.day_of_week,
    start_time: values.start_time,
    end_time: values.end_time,
    vehicle_type: values.vehicle_type,
    location_name: values.location_name.trim(),
    latitude,
    longitude,
    timezone: "Asia/Ho_Chi_Minh",
    is_active: values.is_active,
    notify_before_minutes: Number(values.notify_before_minutes),
    rain_alert_enabled: values.rain_alert_enabled,
    storm_alert_enabled: values.storm_alert_enabled,
    semester_start_date: values.semester_start_date || null,
    semester_end_date: values.semester_end_date || null,
  };
}
