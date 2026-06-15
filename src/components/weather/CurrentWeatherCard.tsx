import { MapPin, CalendarClock, ArrowRight, CloudRain, RotateCcw } from "lucide-react";
import { useState } from "react";

import type { Coordinates, CurrentWeatherResponse, WeatherDisplayState, StudentAdviceResponse, StudyScheduleResponse } from "../../types/weather";
import { useAuth } from "../../context/AuthContext";
import { formatTemperature, formatScheduleRange } from "../../utils/formatters";
import { formatWeatherUpdatedAt } from "../../utils/timeHelpers";
import { getWeatherIcon } from "../../utils/weatherTheme";
import { Card } from "../common/Card";

type CurrentWeatherCardProps = {
  coordinates: Coordinates | null;
  currentWeather: CurrentWeatherResponse | null;
  locationMode: "current" | "search" | "confirmed";
  locationName: string;
  studySchedule?: StudyScheduleResponse | null;
  studyAdvice?: StudentAdviceResponse | null;
  hasSavedSchedule?: boolean;
  isUpdatingLocalWeather?: boolean;
  onClearLocalWeatherReport?: () => Promise<void>;
  onOpenStudyAssistant?: () => void;
  onOpenLogin?: () => void;
  onReportLocalRain?: () => Promise<void>;
};

export function CurrentWeatherCard({
  coordinates,
  currentWeather,
  locationMode,
  locationName,
  studySchedule,
  studyAdvice,
  hasSavedSchedule,
  isUpdatingLocalWeather,
  onClearLocalWeatherReport,
  onOpenStudyAssistant,
  onOpenLogin,
  onReportLocalRain,
}: CurrentWeatherCardProps) {
  const { currentUser } = useAuth();
  const current = currentWeather?.current;
  const display = resolveWeatherLocationDisplay(currentWeather, coordinates, locationMode, locationName);
  const weatherForIcon: WeatherDisplayState = {
    weather_code: current?.weather_code,
    is_day: current?.is_day,
    wind_speed_kmh: current?.wind_speed_kmh,
    temperature_c: current?.temperature_c,
  };

  const confidence = currentWeather?.location_confidence;
  const isConfirmed = locationMode === "confirmed";

  let displayTitle = display.title;
  let showBtn = false;
  let btnText = "";
  let isUncertain = false;

  if (!isConfirmed && locationMode === "current") {
    if (confidence === "province") {
      displayTitle = `Vị trí gần đúng: ${currentWeather?.display_name || locationName}`;
      showBtn = true;
      btnText = "Chọn chính xác hơn";
    } else if (confidence === "coordinates" || confidence === "uncertain") {
      displayTitle = "Vị trí hiện tại chưa xác định rõ";
      showBtn = true;
      btnText = "Chọn vị trí";
      isUncertain = true;
    }
  }

  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [dismissedLocalPromptKey, setDismissedLocalPromptKey] = useState<string | null>(null);
  const localPromptKey = buildLocalPromptKey(currentWeather);
  const hasLocalWeatherOverride = currentWeather?.override_source === "user_report";
  const shouldShowLocalRainPrompt =
    !hasLocalWeatherOverride &&
    shouldSuggestLocalRainCheck(currentWeather) &&
    dismissedLocalPromptKey !== localPromptKey;

  const handleRefineClick = () => {
    const card = document.querySelector(".location-confirmation-card");
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      const input = card.querySelector("input");
      if (input) {
        (input as HTMLInputElement).focus();
      }
    }
  };

  return (
    <Card className="current-weather-card main-weather-card">
      <div className="location-line-container">
        <div className="location-line">
          <MapPin size={20} />
          <span>{displayTitle}</span>
        </div>
        {showBtn && (
          <button
            type="button"
            onClick={handleRefineClick}
            className={`refine-location-btn ${isUncertain ? "uncertain-btn" : "province-btn"}`}
          >
            {btnText}
          </button>
        )}
      </div>
      <p className="muted-line">{display.subtitle}</p>

      <div className="temperature-row">
        <div>
          <strong>{formatTemperature(current?.temperature_c)}</strong>
          <div className="weather-desc-apparent-row">
            <span className="weather-desc">{current?.weather_description ?? "Đang chờ dữ liệu thời tiết"}</span>
            {current?.apparent_temperature_c !== undefined && (
              <span className="apparent-temp">
                (Cảm giác {formatTemperature(current.apparent_temperature_c)})
              </span>
            )}
          </div>
        </div>
        <div className="big-weather-icon" aria-hidden="true">
          {getWeatherIcon(weatherForIcon)}
        </div>
      </div>

      {hasLocalWeatherOverride ? (
        <div className="local-weather-report-card active">
          <div className="local-weather-report-icon">
            <CloudRain size={20} />
          </div>
          <div className="local-weather-report-copy">
            <strong>Đang ưu tiên thời tiết bạn xác nhận</strong>
            <p>
              {current?.weather_description ?? "Đang mưa tại vị trí của bạn"} · Theo xác nhận của bạn
              {currentWeather?.override_expires_at ? ` đến ${formatLocalReportExpiry(currentWeather.override_expires_at)}` : ""}.
            </p>
            {currentWeather?.provider_weather_description ? (
              <small>Dữ liệu gốc {resolveProviderLabel(currentWeather)}: {currentWeather.provider_weather_description}</small>
            ) : null}
          </div>
          {onClearLocalWeatherReport ? (
            <button
              type="button"
              className="local-weather-report-secondary"
              disabled={isUpdatingLocalWeather}
              onClick={() => void onClearLocalWeatherReport()}
            >
              <RotateCcw size={15} />
              Quay lại dự báo
            </button>
          ) : null}
        </div>
      ) : shouldShowLocalRainPrompt ? (
        <div className="local-weather-report-card">
          <div className="local-weather-report-icon">
            <CloudRain size={20} />
          </div>
          <div className="local-weather-report-copy">
            <strong>Thời tiết thực tế khác dự báo?</strong>
            <p>Khu vực bạn có đang mưa không? Xác nhận này chỉ áp dụng tạm thời cho vị trí hiện tại.</p>
          </div>
          <div className="local-weather-report-actions">
            <button
              type="button"
              className="local-weather-report-primary"
              disabled={isUpdatingLocalWeather}
              onClick={() => {
                if (!currentUser) {
                  onOpenLogin?.();
                  return;
                }
                void onReportLocalRain?.();
              }}
            >
              {currentUser ? "Đang mưa tại chỗ tôi" : "Đăng nhập để xác nhận"}
            </button>
            <button
              type="button"
              className="local-weather-report-secondary"
              disabled={isUpdatingLocalWeather}
              onClick={() => setDismissedLocalPromptKey(localPromptKey)}
            >
              Không mưa
            </button>
          </div>
        </div>
      ) : null}

      {/* Quick Study Preview Block */}
      <div className="quick-study-preview-container">
        <h3 className="quick-study-title">
          <CalendarClock size={18} style={{ marginRight: "0.45rem" }} />
          <span>Gợi ý nhanh đi học</span>
        </h3>
        {hasSavedSchedule && studySchedule ? (
          <div className="quick-study-content">
            <div className="quick-study-row">
              <span className="label">Buổi học:</span>
              <span className="value highlight">
                {formatScheduleRange(studySchedule.study_date || undefined, studySchedule.start_time, studySchedule.end_time)}
              </span>
            </div>
            <div className="quick-study-row">
              <span className="label">Mức thuận lợi:</span>
              <span className={`value convenience-tag ${getConvenienceClass(studyAdvice?.score)}`}>
                {getConvenienceLabel(studyAdvice?.score)}
                {studyAdvice?.score !== undefined && ` (${studyAdvice.score}/100)`}
              </span>
            </div>
            {studyAdvice?.summary && (
              <p className="quick-study-advice">💡 {studyAdvice.summary}</p>
            )}
          </div>
        ) : (
          <div className="quick-study-empty">
            <p>Bạn chưa thiết lập lịch học để nhận gợi ý thời tiết đi học.</p>
            {onOpenStudyAssistant && (
              <button type="button" className="quick-study-cta-btn" onClick={onOpenStudyAssistant}>
                <span>Thiết lập lịch học</span>
                <ArrowRight size={13} style={{ marginLeft: "0.25rem", verticalAlign: "middle" }} />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Collapsible Technical Details Section */}
      <div className="weather-technical-details-section">
        <button
          type="button"
          className="tech-details-toggle-btn"
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
        >
          {showTechnicalDetails ? "Ẩn thông tin kỹ thuật ▲" : "Xem thông tin kỹ thuật ▼"}
        </button>
        {showTechnicalDetails && (
          <div className="tech-details-expanded-content animate-slide-up">
            <div className="tech-details-item">
              <span>Cập nhật lúc:</span>
              <strong>{formatWeatherUpdatedAt(current?.time, currentWeather?.timezone)}</strong>
            </div>
            <div className="tech-details-item">
              <span>Nguồn dữ liệu:</span>
              <strong>{resolveProviderLabel(currentWeather)}</strong>
            </div>
            {coordinates && (
              <div className="tech-details-item">
                <span>Tọa độ GPS:</span>
                <strong>{coordinates.latitude.toFixed(4)}, {coordinates.longitude.toFixed(4)}</strong>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

const rainWeatherCodes = new Set([51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82]);
const stormWeatherCodes = new Set([95, 96, 99]);

function shouldSuggestLocalRainCheck(currentWeather: CurrentWeatherResponse | null): boolean {
  const current = currentWeather?.current;
  if (!current) return false;
  const weatherCode = current.weather_code;
  if (weatherCode !== undefined && (rainWeatherCodes.has(weatherCode) || stormWeatherCodes.has(weatherCode))) {
    return false;
  }
  const rainAmount = Math.max(current.rain_mm ?? 0, current.precipitation_mm ?? 0);
  if (rainAmount > 0) return false;

  const cloudCover = current.cloud_cover_percent ?? 0;
  const humidity = current.relative_humidity_percent ?? 0;
  const rainProbability = current.precipitation_probability_percent ?? 0;
  return cloudCover >= 85 || humidity >= 70 || rainProbability >= 15;
}

function buildLocalPromptKey(currentWeather: CurrentWeatherResponse | null): string {
  if (!currentWeather) return "no-weather";
  return [
    currentWeather.latitude.toFixed(3),
    currentWeather.longitude.toFixed(3),
    currentWeather.current.time ?? "",
  ].join(":");
}

function formatLocalReportExpiry(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "khi hết hiệu lực";
  return date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function getConvenienceClass(score?: number): string {
  if (score === undefined) return "convenience-loading";
  if (score >= 80) return "convenience-good";
  if (score >= 50) return "convenience-medium";
  return "convenience-bad";
}

function getConvenienceLabel(score?: number): string {
  if (score === undefined) return "Đang phân tích...";
  if (score >= 80) return "Tốt";
  if (score >= 50) return "Trung bình";
  return "Cần lưu ý";
}

function resolveProviderLabel(currentWeather: CurrentWeatherResponse | null): string {
  const provider = currentWeather?.provider;
  if (!provider) return "OpenWeather";
  
  const nameMap: Record<string, string> = {
    openweather: "OpenWeather",
    open_meteo: "Open-Meteo",
  };
  
  const activeLabel = nameMap[provider.toLowerCase()] || provider;
  if (currentWeather?.fallback_provider_used) {
    return `${activeLabel} (fallback)`;
  }
  
  return activeLabel;
}

function resolveWeatherLocationDisplay(
  currentWeather: CurrentWeatherResponse | null,
  coordinates: Coordinates | null,
  locationMode: "current" | "search" | "confirmed",
  locationName: string,
): { subtitle: string; title: string } {
  if (locationMode === "confirmed") {
    return {
      title: locationName,
      subtitle: "Đang dùng vị trí đã lưu",
    };
  }

  if (locationMode === "search") {
    return {
      title: locationName,
      subtitle: "Đang xem theo tìm kiếm",
    };
  }

  return {
    title: locationName,
    subtitle: "Đang dùng vị trí hiện tại",
  };
}
