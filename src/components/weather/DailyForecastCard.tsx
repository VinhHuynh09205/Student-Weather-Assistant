import type { DailyForecastItem } from "../../types/weather";
import { formatPercent, formatTemperature } from "../../utils/formatters";
import { getWeatherIcon } from "../../utils/weatherTheme";
import { Card } from "../common/Card";

type DailyForecastCardProps = {
  items: DailyForecastItem[];
};

export function DailyForecastCard({ items }: DailyForecastCardProps) {
  return (
    <Card className="daily-card">
      <h2>Dự báo nhiều ngày</h2>
      <div className="daily-list">
        {items.length ? (
          items.map((item) => (
            <article className="daily-row" key={item.date}>
              <div>
                <strong>{formatDailyLabel(item.date)}</strong>
                <span>{item.weather_description}</span>
              </div>
              <span className="daily-icon" aria-hidden="true">
                {getWeatherIcon({ weather_code: item.weather_code, is_day: true })}
              </span>
              <div>
                <strong>
                  {formatTemperature(item.temperature_max_c)} / {formatTemperature(item.temperature_min_c)}
                </strong>
                <span>Mưa {formatPercent(item.precipitation_probability_max_percent)}</span>
              </div>
            </article>
          ))
        ) : (
          <p className="empty-copy">Chưa có dữ liệu dự báo nhiều ngày.</p>
        )}
      </div>
    </Card>
  );
}

function formatDailyLabel(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  const date = new Date(year, month - 1, day);
  return date.toLocaleDateString("vi-VN", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  });
}
