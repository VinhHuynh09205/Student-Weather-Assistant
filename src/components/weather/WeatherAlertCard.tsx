import { AlertTriangle } from "lucide-react";

import type { CurrentWeatherResponse, DailyForecastItem, HourlyForecastItem } from "../../types/weather";
import { buildWeatherAlerts } from "../../utils/weatherAlerts";
import { Card } from "../common/Card";

type WeatherAlertCardProps = {
  currentWeather: CurrentWeatherResponse | null;
  daily?: DailyForecastItem;
  hourlyItems: HourlyForecastItem[];
};

export function WeatherAlertCard({ currentWeather, daily, hourlyItems }: WeatherAlertCardProps) {
  const alerts = buildWeatherAlerts(currentWeather, hourlyItems, daily);

  return (
    <Card className={`weather-alert-card ${alerts.length ? "has-alerts" : ""}`}>
      <h2>
        <AlertTriangle size={22} />
        Cảnh báo thời tiết
      </h2>
      {alerts.length ? (
        <ul>
          {alerts.map((alert) => (
            <li key={alert}>{alert}</li>
          ))}
        </ul>
      ) : (
        <p>Không có cảnh báo thời tiết đáng chú ý.</p>
      )}
    </Card>
  );
}
