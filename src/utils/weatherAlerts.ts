import type { CurrentWeatherResponse, DailyForecastItem, HourlyForecastItem } from "../types/weather";
import { formatWeatherAlert } from "./formatters";

const stormCodes = new Set([95, 96, 99]);
const rainProbabilityAlertPercent = 60;
const dailyRainProbabilityAlertPercent = 70;
const rainAmountAlertMillimeters = 0.2;
const heavyRainAlertMillimeters = 5;
const windAlertKmh = 30;
const uvAlertIndex = 8;
const hotTemperatureC = 35;
const hotApparentTemperatureC = 37;

export function buildWeatherAlerts(
  currentWeather: CurrentWeatherResponse | null,
  hourlyItems: HourlyForecastItem[],
  daily?: DailyForecastItem,
): string[] {
  const current = currentWeather?.current;
  if (!current) return [];

  const nearbyHourly = hourlyItems.slice(0, 6);
  const currentRainProbability = current.precipitation_probability_percent ?? 0;
  const nearbyRainProbability = Math.max(
    currentRainProbability,
    ...nearbyHourly.map((item) => item.precipitation_probability_percent ?? 0),
  );
  const currentRainAmount = Math.max(current.rain_mm ?? 0, current.precipitation_mm ?? 0);
  const nearbyRainAmount = Math.max(
    currentRainAmount,
    ...nearbyHourly.map((item) => Math.max(item.rain_mm ?? 0, item.precipitation_mm ?? 0)),
  );
  const alerts: string[] = [];

  if (isStormCode(current.weather_code)) {
    alerts.push("Đang có khả năng dông, hạn chế ra ngoài khi có sấm chớp.");
  }

  if (nearbyRainAmount >= heavyRainAlertMillimeters) {
    alerts.push("Đang có khả năng mưa lớn, nên tránh di chuyển lúc này.");
  } else if (nearbyRainProbability >= rainProbabilityAlertPercent || nearbyRainAmount >= rainAmountAlertMillimeters) {
    alerts.push("Đang có khả năng mưa, nên chuẩn bị áo mưa hoặc dù.");
  }

  if ((current.wind_speed_kmh ?? 0) >= windAlertKmh) {
    alerts.push("Gió mạnh, cần cẩn thận khi di chuyển.");
  }

  if (current.is_day === true && (current.uv_index ?? 0) >= uvAlertIndex) {
    alerts.push("Chỉ số UV cao, nên che nắng khi ra ngoài.");
  }

  if ((current.apparent_temperature_c ?? 0) >= hotApparentTemperatureC || (current.temperature_c ?? 0) >= hotTemperatureC) {
    alerts.push("Thời tiết nắng nóng, nhớ uống đủ nước.");
  }

  if (daily) {
    if (isStormCode(daily.weather_code) && !isStormCode(current.weather_code)) {
      alerts.push("Trong hôm nay có khả năng dông.");
    }
    if (
      daily.precipitation_probability_max_percent >= dailyRainProbabilityAlertPercent &&
      nearbyRainProbability < rainProbabilityAlertPercent &&
      nearbyRainAmount < rainAmountAlertMillimeters
    ) {
      alerts.push("Trong hôm nay có khả năng mưa cao.");
    }
  }

  return Array.from(new Set(alerts)).map(formatWeatherAlert);
}

function isStormCode(weatherCode?: number): boolean {
  return typeof weatherCode === "number" && stormCodes.has(weatherCode);
}
