import { Droplets, Eye, MapPin, Thermometer, Wind } from "lucide-react";

import type { CurrentWeatherResponse, StudentAdviceResponse, WeatherDisplayState } from "../../types/weather";
import { formatLocationDisplay, formatPercent, formatTemperature, formatUvIndex, formatWind } from "../../utils/formatters";
import { getWeatherIcon } from "../../utils/weatherTheme";
import { Card } from "../common/Card";

type WeatherMainCardProps = {
  currentWeather: CurrentWeatherResponse | null;
  advice: StudentAdviceResponse | null;
  weatherForTheme: WeatherDisplayState;
};

export function WeatherMainCard({ advice, currentWeather, weatherForTheme }: WeatherMainCardProps) {
  const current = currentWeather?.current;
  const displayName = advice?.display_name || formatLocationDisplay(currentWeather) || "Vị trí hiện tại";
  const description = current?.weather_description ?? weatherForTheme.weather_description ?? "Không rõ";
  const temperature = current?.temperature_c ?? weatherForTheme.temperature_c;
  const apparentTemperature = current?.apparent_temperature_c ?? advice?.metrics.max_apparent_temperature_c;
  const humidity = current?.relative_humidity_percent ?? advice?.metrics.average_humidity_percent;
  const windSpeed = current?.wind_speed_kmh ?? weatherForTheme.wind_speed_kmh;
  const uvIndex = current?.uv_index ?? advice?.metrics.max_uv_index;

  return (
    <Card className="main-weather-card">
      <div className="location-line">
        <MapPin size={20} />
        <span>{displayName}</span>
      </div>
      <div className="temperature-row">
        <div>
          <strong>{formatTemperature(temperature)}</strong>
          <p>{description}</p>
        </div>
        <div className="big-weather-icon" aria-hidden="true">
          {getWeatherIcon({
            weather_code: current?.weather_code ?? weatherForTheme.weather_code,
            is_day: current?.is_day ?? weatherForTheme.is_day,
            wind_speed_kmh: windSpeed,
            temperature_c: temperature,
          })}
        </div>
      </div>

      <div className="mini-metrics">
        <div>
          <Thermometer size={18} />
          <span>Cảm giác</span>
          <strong>{formatTemperature(apparentTemperature)}</strong>
        </div>
        <div>
          <Droplets size={18} />
          <span>Độ ẩm</span>
          <strong>{formatPercent(humidity)}</strong>
        </div>
        <div>
          <Wind size={18} />
          <span>Gió</span>
          <strong>{formatWind(windSpeed)}</strong>
        </div>
        <div>
          <Eye size={18} />
          <span>UV Index</span>
          <strong>{formatUvIndex(uvIndex, current?.is_day ?? advice?.is_day)}</strong>
        </div>
      </div>
    </Card>
  );
}
