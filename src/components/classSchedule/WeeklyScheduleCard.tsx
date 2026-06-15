import {
  Bell,
  CalendarDays,
  Clock3,
  CloudRain,
  Edit3,
  MapPin,
  MoreVertical,
  Power,
  Trash2,
  Wind,
  Zap,
} from "lucide-react";

import type { ClassScheduleForecast, WeeklyClassSchedule } from "../../types/classSchedule";
import {
  forecastStatusLabels,
  formatClassTime,
  formatDayOfWeek,
  formatOccurrenceRange,
  formatSemesterRange,
} from "../../utils/classScheduleFormatters";
import { formatMillimeters, formatPercent, formatWind } from "../../utils/formatters";
import { RiskBadge } from "./RiskBadge";

type WeeklyScheduleCardProps = {
  schedule: WeeklyClassSchedule;
  forecast?: ClassScheduleForecast;
  isBusy?: boolean;
  onDelete: (schedule: WeeklyClassSchedule) => void;
  onEdit: (schedule: WeeklyClassSchedule) => void;
  onToggleActive: (schedule: WeeklyClassSchedule) => void;
};

export function WeeklyScheduleCard({
  schedule,
  forecast,
  isBusy = false,
  onDelete,
  onEdit,
  onToggleActive,
}: WeeklyScheduleCardProps) {
  const isForecastAvailable = forecast?.forecast_status === "available";
  const nextOccurrence = forecast?.next_occurrence;

  return (
    <article className={`weekly-schedule-card ${schedule.is_active ? "" : "inactive"}`}>
      <div className="weekly-card-main">
        <div className="weekly-subject-row">
          <div className="weekly-subject-icon">
            <CalendarDays size={22} aria-hidden="true" />
          </div>
          <div>
            <span>{formatDayOfWeek(schedule.day_of_week)}</span>
            <h3>{schedule.subject_name}</h3>
          </div>
        </div>

        <div className="weekly-card-actions">
          <button type="button" title="Sửa lịch" onClick={() => onEdit(schedule)} disabled={isBusy}>
            <Edit3 size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            title={schedule.is_active ? "Tắt lịch" : "Bật lịch"}
            onClick={() => onToggleActive(schedule)}
            disabled={isBusy}
          >
            <Power size={16} aria-hidden="true" />
          </button>
          <button type="button" title="Xóa lịch học" onClick={() => onDelete(schedule)} disabled={isBusy}>
            <Trash2 size={16} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="weekly-meta-grid">
        <span>
          <Clock3 size={16} aria-hidden="true" />
          {formatClassTime(schedule.start_time)} - {formatClassTime(schedule.end_time)}
        </span>
        <span>
          <MapPin size={16} aria-hidden="true" />
          {schedule.location_name || "Chưa có địa điểm"}
        </span>
        <span>
          <Bell size={16} aria-hidden="true" />
          Nhắc trước {schedule.notify_before_minutes} phút
        </span>
      </div>

      <div className="weekly-forecast-panel">
        <div className="weekly-forecast-header">
          <div>
            <span>Buổi học kế tiếp</span>
            <strong>{formatOccurrenceRange(nextOccurrence?.start_datetime, nextOccurrence?.end_datetime)}</strong>
          </div>
          <RiskBadge riskLevel={forecast?.risk_level ?? "SAFE"} />
        </div>

        <div className="weekly-status-line">
          <span className={`forecast-status-pill status-${forecast?.forecast_status ?? "pending"}`}>
            {forecastStatusLabels[forecast?.forecast_status ?? "pending"] ?? "Đang cập nhật"}
          </span>
          {forecast?.weather_summary ? <span>{forecast.weather_summary}</span> : null}
        </div>

        {isForecastAvailable ? (
          <div className="weekly-weather-metrics">
            <span>
              <CloudRain size={15} aria-hidden="true" />
              {formatPercent(forecast.precipitation_probability_percent ?? undefined)}
            </span>
            <span>
              <MoreVertical size={15} aria-hidden="true" />
              {formatMillimeters(forecast.rain_mm ?? undefined)}
            </span>
            <span>
              <Wind size={15} aria-hidden="true" />
              {formatWind(forecast.wind_speed_kmh ?? undefined)}
            </span>
          </div>
        ) : null}

        <p>{forecast?.recommendation_message ?? getFallbackRecommendation(schedule)}</p>
      </div>

      <div className="weekly-card-footer">
        <span className={schedule.is_active ? "active-dot" : "inactive-dot"}>
          {schedule.is_active ? "Đang theo dõi" : "Đã tắt"}
        </span>
        <span>
          <CloudRain size={14} aria-hidden="true" />
          {schedule.rain_alert_enabled ? "Mưa bật" : "Mưa tắt"}
        </span>
        <span>
          <Zap size={14} aria-hidden="true" />
          {schedule.storm_alert_enabled ? "Dông bật" : "Dông tắt"}
        </span>
        <span>{formatSemesterRange(schedule.semester_start_date, schedule.semester_end_date)}</span>
      </div>
    </article>
  );
}

function getFallbackRecommendation(schedule: WeeklyClassSchedule): string {
  if (!schedule.is_active) {
    return "Lịch đang tắt nên hệ thống chưa theo dõi dự báo cho buổi học này.";
  }
  if (!schedule.location_name) {
    return "Thêm địa điểm hoặc tọa độ để hệ thống lấy dự báo chính xác hơn.";
  }
  return "Dự báo sẽ được cập nhật khi gần đến ngày học.";
}
