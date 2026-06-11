import type { HourlyForecastItem, WeatherDisplayState } from "../../types/weather";
import { formatHour, formatTemperature } from "../../utils/formatters";
import { getWeatherIcon } from "../../utils/weatherTheme";
import { Card } from "../common/Card";

type HourlyForecastProps = {
  items: HourlyForecastItem[];
  title?: string;
};

export function HourlyForecast({ items, title = "Dự báo theo giờ" }: HourlyForecastProps) {
  const visibleItems = items.slice(0, 8);

  return (
    <Card className="hourly-card" title={title}>
      {visibleItems.length > 0 ? (
        <div className="hourly-scroll">
          {visibleItems.map((item) => {
            const weather: WeatherDisplayState = {
              weather_code: item.weather_code,
              is_day: item.is_day,
              wind_speed_kmh: item.wind_speed_kmh,
              temperature_c: item.temperature_c,
            };
            return (
              <article className="hourly-item" key={`${item.time}-${item.temperature_c}`}>
                <span>{formatHour(item.time)}</span>
                <strong aria-hidden="true">{getWeatherIcon(weather)}</strong>
                <b>{formatTemperature(item.temperature_c)}</b>
                <small>{item.weather_description ?? "Không rõ"}</small>
              </article>
            );
          })}
        </div>
      ) : (
        <p className="muted">Chưa có dữ liệu dự báo theo giờ.</p>
      )}
    </Card>
  );
}
