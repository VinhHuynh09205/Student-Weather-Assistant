import { CalendarClock, CloudRain, MapPin, Wind } from "lucide-react";

import type { ClassScheduleForecast } from "../../types/classSchedule";
import { forecastStatusLabels, formatOccurrenceDateTime } from "../../utils/classScheduleFormatters";
import { formatMillimeters, formatPercent, formatWind } from "../../utils/formatters";
import { RiskBadge } from "./RiskBadge";

type UpcomingForecastListProps = {
  forecasts: ClassScheduleForecast[];
};

export function UpcomingForecastList({ forecasts }: UpcomingForecastListProps) {
  if (forecasts.length === 0) {
    return (
      <div className="weekly-empty-state glass-card">
        <CalendarClock size={38} aria-hidden="true" />
        <h3>Chưa có buổi học sắp tới</h3>
        <p>Khi lịch hằng tuần đang hoạt động và còn trong học kỳ, các dự báo gần nhất sẽ xuất hiện tại đây.</p>
      </div>
    );
  }

  return (
    <div className="upcoming-forecast-list">
      {forecasts.map((forecast, index) => (
        <article className="upcoming-forecast-item" key={forecast.schedule.id}>
          <div className="upcoming-timeline-node">
            <span>{index + 1}</span>
          </div>

          <div className="upcoming-forecast-card">
            <div className="upcoming-forecast-top">
              <div>
                <span>{forecast.schedule.subject_name}</span>
                <h3>{formatOccurrenceDateTime(forecast.next_occurrence_datetime)}</h3>
              </div>
              <RiskBadge riskLevel={forecast.risk_level} compact />
            </div>

            <div className="upcoming-meta-line">
              <span>
                <MapPin size={15} aria-hidden="true" />
                {forecast.schedule.location_name || "Chưa có địa điểm"}
              </span>
              <span>{forecastStatusLabels[forecast.forecast_status] ?? forecast.forecast_status}</span>
            </div>

            {forecast.forecast_status === "available" ? (
              <div className="upcoming-weather-row">
                <span>
                  <CloudRain size={15} aria-hidden="true" />
                  {formatPercent(forecast.precipitation_probability_percent ?? undefined)}
                </span>
                <span>{formatMillimeters(forecast.rain_mm ?? undefined)}</span>
                <span>
                  <Wind size={15} aria-hidden="true" />
                  {formatWind(forecast.wind_speed_kmh ?? undefined)}
                </span>
              </div>
            ) : null}

            <p>{forecast.recommendation_message}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
