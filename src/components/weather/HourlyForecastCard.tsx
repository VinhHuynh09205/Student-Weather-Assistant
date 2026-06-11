import type { HourlyForecastItem } from "../../types/weather";
import { formatHour, formatPercent, formatTemperature } from "../../utils/formatters";
import { getWeatherIcon } from "../../utils/weatherTheme";
import { Card } from "../common/Card";

type HourlyForecastCardProps = {
  items: HourlyForecastItem[];
};

export function HourlyForecastCard({ items }: HourlyForecastCardProps) {
  return (
    <Card className="hourly-card">
      <h2>Dự báo hôm nay</h2>
      {items.length ? (
        <div className="hourly-strip">
          {items.slice(0, 12).map((item) => (
            <article className="hourly-item" key={item.time}>
              <span>{formatHour(item.time)}</span>
              <strong>
                {getWeatherIcon({
                  weather_code: item.weather_code,
                  is_day: item.is_day,
                  wind_speed_kmh: item.wind_speed_kmh,
                  temperature_c: item.temperature_c,
                })}
              </strong>
              <b>{formatTemperature(item.temperature_c)}</b>
              <small>{formatPercent(item.precipitation_probability_percent)}</small>
            </article>
          ))}
        </div>
      ) : (
        <p className="empty-copy">Chưa có dữ liệu dự báo theo giờ.</p>
      )}
    </Card>
  );
}
