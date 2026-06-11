import { CloudRain, Droplets, Eye, Sun, Thermometer, Umbrella, Wind } from "lucide-react";

import type { CurrentWeatherResponse, HourlyForecastItem } from "../../types/weather";
import {
  formatOptionalNumber,
  formatOptionalPercent,
  formatPercent,
  formatRainAmount,
  formatTemperature,
  formatUvIndex,
  formatWind,
} from "../../utils/formatters";

type WeatherMetricGridProps = {
  currentWeather: CurrentWeatherResponse | null;
  nearestHourly?: HourlyForecastItem;
};

export function WeatherMetricGrid({ currentWeather, nearestHourly }: WeatherMetricGridProps) {
  const current = currentWeather?.current;
  const rainProbability = current?.precipitation_probability_percent ?? nearestHourly?.precipitation_probability_percent;
  const rainAmount = current?.rain_mm ?? current?.precipitation_mm;
  const cloudPressureValue = resolveCloudPressureValue(current);
  const metrics = [
    {
      icon: <Thermometer />,
      label: "Nhiệt độ",
      value: typeof current?.temperature_c === "number" ? formatTemperature(current.temperature_c) : "Chưa có dữ liệu",
      hint: "Hiện tại",
      tone: "warm",
    },
    {
      icon: <Thermometer />,
      label: "Cảm giác như",
      value:
        typeof current?.apparent_temperature_c === "number"
          ? formatTemperature(current.apparent_temperature_c)
          : "Chưa có dữ liệu",
      hint: "Theo độ ẩm và gió",
      tone: "hot",
    },
    {
      icon: <Droplets />,
      label: "Độ ẩm",
      value:
        typeof current?.relative_humidity_percent === "number"
          ? formatPercent(current.relative_humidity_percent)
          : "Chưa có dữ liệu",
      hint: "Hiện tại",
      tone: "blue",
    },
    {
      icon: <Wind />,
      label: "Tốc độ gió",
      value: typeof current?.wind_speed_kmh === "number" ? formatWind(current.wind_speed_kmh) : "Chưa có dữ liệu",
      hint: "Gió tại vị trí đang xem",
      tone: "purple",
    },
    {
      icon: <Umbrella />,
      label: "Khả năng mưa",
      value: formatOptionalPercent(rainProbability),
      hint: current?.precipitation_probability_percent !== undefined ? "Hiện tại" : "Giờ gần nhất",
      tone: "green",
    },
    {
      icon: <CloudRain />,
      label: "Lượng mưa",
      value: formatRainAmount(rainAmount),
      hint: "Hiện tại",
      tone: "indigo",
    },
    {
      icon: <Sun />,
      label: "Chỉ số UV",
      value: formatUvIndex(current?.uv_index, current?.is_day),
      hint: "Tia UV hiện tại",
      tone: "sun",
    },
    {
      icon: <Eye />,
      label: "Mây/áp suất",
      value: cloudPressureValue.value,
      hint: cloudPressureValue.hint,
      tone: "muted",
    },
  ];

  return (
    <div className="metric-grid">
      {metrics.map((metric) => (
        <article className={`metric-tile tone-${metric.tone}`} key={metric.label}>
          <div className="metric-icon">{metric.icon}</div>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
          <small>{metric.hint}</small>
        </article>
      ))}
    </div>
  );
}

function resolveCloudPressureValue(current: CurrentWeatherResponse["current"] | undefined): { hint: string; value: string } {
  if (typeof current?.cloud_cover_percent === "number") {
    return {
      value: `${Math.round(current.cloud_cover_percent)}% mây`,
      hint:
        typeof current.pressure_hpa === "number"
          ? `${formatOptionalNumber(current.pressure_hpa, "hPa")}`
          : "Độ che phủ mây",
    };
  }

  if (typeof current?.pressure_hpa === "number") {
    return {
      value: `${formatOptionalNumber(current.pressure_hpa, "hPa")}`,
      hint: "Áp suất bề mặt",
    };
  }

  return {
    value: "Chưa có dữ liệu",
    hint: "Open-Meteo chưa trả field này",
  };
}
