import { ArrowRight, CalendarClock, CloudRain, MapPin, RefreshCw, Wind } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import * as classScheduleApi from "../../api/classScheduleApi";
import type { ClassScheduleForecast } from "../../types/classSchedule";
import {
  forecastStatusLabels,
  formatOccurrenceRange,
  riskLevelLabels,
} from "../../utils/classScheduleFormatters";
import { formatMillimeters, formatPercent, formatWind } from "../../utils/formatters";
import { Card } from "../common/Card";
import { RiskBadge } from "./RiskBadge";
import { useAuth } from "../../context/AuthContext";

type WeeklyQuickSuggestionCardProps = {
  onOpenWeeklySchedule: () => void;
};

export function WeeklyQuickSuggestionCard({ onOpenWeeklySchedule }: WeeklyQuickSuggestionCardProps) {
  const { currentUser } = useAuth();
  const [forecasts, setForecasts] = useState<ClassScheduleForecast[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadForecasts = useCallback(async () => {
    if (!currentUser) {
      setForecasts([]);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const nextForecasts = await classScheduleApi.getUpcomingForecasts(1);
      setForecasts(nextForecasts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tải gợi ý lịch học hằng tuần.");
      setForecasts([]);
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  useEffect(() => {
    void loadForecasts();
  }, [loadForecasts]);

  const forecast = forecasts[0];

  return (
    <Card className="weekly-quick-card">
      <div className="section-title-row weekly-quick-title-row">
        <h2>
          <CalendarClock size={22} />
          Gợi ý lịch tuần
        </h2>
        {currentUser ? (
          <button
            type="button"
            className="weekly-quick-refresh-btn"
            onClick={() => void loadForecasts()}
            disabled={loading}
            title="Làm mới gợi ý lịch tuần"
          >
            <RefreshCw size={15} aria-hidden="true" />
          </button>
        ) : null}
      </div>

      {loading ? <p className="weekly-quick-muted">Đang tải buổi học hằng tuần gần nhất...</p> : null}
      {error ? <p className="weekly-quick-error">{error}</p> : null}

      {!loading && !error && forecast ? (
        <div className="weekly-quick-content">
          <div className="weekly-quick-main">
            <div>
              <span>Môn học gần nhất</span>
              <strong>{forecast.schedule.subject_name}</strong>
            </div>
            <RiskBadge riskLevel={forecast.risk_level} compact />
          </div>

          <div className="weekly-quick-meta-grid">
            <span>
              <CalendarClock size={15} aria-hidden="true" />
              {formatOccurrenceRange(
                forecast.next_occurrence?.start_datetime,
                forecast.next_occurrence?.end_datetime,
              )}
            </span>
            <span>
              <MapPin size={15} aria-hidden="true" />
              {forecast.schedule.location_name || "Chưa có địa điểm"}
            </span>
            <span>{forecastStatusLabels[forecast.forecast_status] ?? forecast.forecast_status}</span>
            <span>{riskLevelLabels[forecast.risk_level]}</span>
          </div>

          {forecast.forecast_status === "available" ? (
            <div className="weekly-quick-weather-row">
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
      ) : null}

      {!loading && !error && !forecast ? (
        <div className="weekly-quick-empty">
          <strong>Bạn chưa có lịch học hằng tuần</strong>
          <p>Tạo lịch tuần để hệ thống tự nhắc buổi học kế tiếp và cảnh báo mưa/dông.</p>
        </div>
      ) : null}

      <button className="inline-action-button weekly-quick-action" type="button" onClick={onOpenWeeklySchedule}>
        <span>{forecast ? "Xem lịch tuần" : "Tạo lịch tuần"}</span>
        <ArrowRight size={18} aria-hidden="true" />
      </button>
    </Card>
  );
}
