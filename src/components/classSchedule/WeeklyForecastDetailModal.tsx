import { AlertTriangle, CheckCircle2, Clock3, CloudRain, ListChecks, MapPin, Navigation, X } from "lucide-react";
import type { ReactNode } from "react";

import type { ClassScheduleForecast, WeeklyClassSchedule } from "../../types/classSchedule";
import {
  forecastStatusLabels,
  formatClassTime,
  formatDayOfWeek,
  formatOccurrenceRange,
} from "../../utils/classScheduleFormatters";
import { formatMillimeters, formatPercent, formatWind, getVehicleIcon, getVehicleLabel } from "../../utils/formatters";
import { RiskBadge } from "./RiskBadge";

type WeeklyForecastDetailModalProps = {
  forecast?: ClassScheduleForecast;
  onClose: () => void;
  schedule: WeeklyClassSchedule;
};

export function WeeklyForecastDetailModal({ forecast, onClose, schedule }: WeeklyForecastDetailModalProps) {
  const score = forecast?.study_score ?? null;
  const timeline = forecast?.timeline_advice;
  const summary =
    forecast?.summary_message ??
    "Lịch đã được lưu. Dự báo sẽ được cập nhật khi gần đến ngày học.";
  const warning = forecast?.weather_warning ?? "Chưa có cảnh báo thời tiết đáng chú ý cho buổi học này.";
  const commuteAdvice =
    forecast?.commute_advice ??
    "Hãy kiểm tra thời tiết sát giờ đi học để chọn phương tiện phù hợp.";

  return (
    <div className="weekly-detail-overlay" role="dialog" aria-modal="true" aria-label="Chi tiết gợi ý thời tiết">
      <div className="weekly-detail-modal">
        <header className="weekly-detail-header">
          <div>
            <span>Trợ lý đi học hằng tuần</span>
            <h2>{schedule.subject_name}</h2>
            <p>
              {formatDayOfWeek(schedule.day_of_week)} • {formatClassTime(schedule.start_time)} -{" "}
              {formatClassTime(schedule.end_time)}
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Đóng chi tiết">
            <X size={18} aria-hidden="true" />
          </button>
        </header>

        <div className="weekly-detail-body">
          <section className="weekly-detail-score-card">
            <div className="weekly-score-orb">
              <strong>{score ?? "--"}</strong>
              <span>/100</span>
            </div>
            <div>
              <span>{forecast?.score_label ?? "Chờ dự báo"}</span>
              <h3>Điểm thuận lợi đi học</h3>
              <p>{summary}</p>
            </div>
            <RiskBadge riskLevel={forecast?.risk_level ?? "SAFE"} />
          </section>

          <section className="weekly-detail-grid">
            <InfoPanel icon={<Clock3 size={18} />} title="Tóm tắt buổi học">
              <p>{forecast?.next_occurrence ? formatOccurrenceRange(forecast.next_occurrence.start_datetime, forecast.next_occurrence.end_datetime) : summary}</p>
              <p>{schedule.location_name || "Chưa có địa điểm học"}</p>
            </InfoPanel>

            <InfoPanel icon={<AlertTriangle size={18} />} title="Cảnh báo thời tiết">
              <p>{warning}</p>
            </InfoPanel>

            <InfoPanel icon={<Navigation size={18} />} title={`Gợi ý cho ${getVehicleLabel(schedule.vehicle_type)}`}>
              <p>
                <span aria-hidden="true">{getVehicleIcon(schedule.vehicle_type)} </span>
                {commuteAdvice}
              </p>
            </InfoPanel>

            <InfoPanel icon={<CloudRain size={18} />} title="Dữ liệu thời tiết">
              <div className="weekly-weather-detail-metrics">
                <span>Mưa {formatPercent(forecast?.precipitation_probability_percent ?? undefined)}</span>
                <span>Lượng mưa {formatMillimeters(forecast?.rain_mm ?? undefined)}</span>
                <span>Gió {formatWind(forecast?.wind_speed_kmh ?? undefined)}</span>
              </div>
              <p>{forecastStatusLabels[forecast?.forecast_status ?? "pending"] ?? "Đang cập nhật"}</p>
            </InfoPanel>
          </section>

          <section className="weekly-detail-section">
            <h3>
              <ListChecks size={18} aria-hidden="true" />
              Danh sách chuẩn bị
            </h3>
            <div className="weekly-check-list">
              {(forecast?.preparation_items?.length ? forecast.preparation_items : ["Kiểm tra lại thời tiết trước khi đi học"]).map(
                (item) => (
                  <span key={item}>
                    <CheckCircle2 size={16} aria-hidden="true" />
                    {item}
                  </span>
                ),
              )}
            </div>
          </section>

          <section className="weekly-detail-section">
            <h3>
              <MapPin size={18} aria-hidden="true" />
              Lý do gợi ý
            </h3>
            <div className="weekly-reason-list">
              {(forecast?.reason_factors?.length ? forecast.reason_factors : ["Dữ liệu dự báo sẽ được cập nhật khi gần giờ học"]).map(
                (reason) => (
                  <span key={reason}>{reason}</span>
                ),
              )}
            </div>
          </section>

          <section className="weekly-detail-section">
            <h3>
              <Clock3 size={18} aria-hidden="true" />
              Timeline trước / trong / sau buổi học
            </h3>
            <div className="weekly-timeline-advice-grid">
              <TimelineItem label="Trước buổi học" value={timeline?.before_class ?? "Theo dõi lại dự báo khi gần đến giờ học."} />
              <TimelineItem label="Trong buổi học" value={timeline?.during_class ?? "Lịch học vẫn được giữ trong hệ thống."} />
              <TimelineItem label="Sau buổi học" value={timeline?.after_class ?? "Kiểm tra dự báo trước khi ra về."} />
            </div>
          </section>

          <section className="weekly-detail-provider-note">
            <span>Dữ liệu gốc: {formatCondition(forecast?.provider_condition)}</span>
            <span>Đang dùng: {formatCondition(forecast?.effective_condition)}</span>
            {forecast?.override_source ? <strong>Theo xác nhận thời tiết tại chỗ của bạn</strong> : null}
          </section>
        </div>
      </div>
    </div>
  );
}

function InfoPanel({ children, icon, title }: { children: ReactNode; icon: ReactNode; title: string }) {
  return (
    <article className="weekly-detail-info-panel">
      <h3>
        {icon}
        {title}
      </h3>
      {children}
    </article>
  );
}

function TimelineItem({ label, value }: { label: string; value: string }) {
  return (
    <article>
      <span>{label}</span>
      <p>{value}</p>
    </article>
  );
}

function formatCondition(value?: string | null): string {
  if (value === "rain") return "Mưa";
  if (value === "storm") return "Dông";
  if (value === "clear") return "Trời quang";
  if (value === "cloudy") return "Nhiều mây";
  return "Chưa có dữ liệu";
}
