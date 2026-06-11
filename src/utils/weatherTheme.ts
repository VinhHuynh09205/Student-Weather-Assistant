import type { WeatherDisplayState } from "../types/weather";

const rainCodes = new Set([51, 53, 55, 61, 63, 65, 80, 81, 82]);
const stormCodes = new Set([95, 96, 99]);
const clearCodes = new Set([0, 1, 2]);
const cloudyCodes = new Set([3]);

export type WeatherThemeKey =
  | "night"
  | "rain-night"
  | "storm-night"
  | "wind-night"
  | "rain"
  | "storm"
  | "wind"
  | "hot"
  | "day"
  | "cloudy-day"
  | "cloudy";

export interface WeatherTheme {
  key: WeatherThemeKey;
  label: string;
  icon: string;
  accent: string;
  scoreTone: "good" | "medium" | "bad";
  isWindy: boolean;
}

export function resolveWeatherTheme(weather: WeatherDisplayState): WeatherTheme {
  const weatherCode = weather.weather_code;
  const isDay = weather.is_day ?? deriveIsDayFromBackendTime(weather.time);
  const windSpeed = weather.wind_speed_kmh ?? 0;
  const temperature = weather.temperature_c ?? 0;
  const precipitationProbability = weather.precipitation_probability_percent ?? 0;
  const isWindy = windSpeed >= 30;
  const isStorm = weatherCode !== undefined && stormCodes.has(weatherCode);
  const isRain = (weatherCode !== undefined && rainCodes.has(weatherCode)) || precipitationProbability >= 70;

  if (isDay === false) {
    if (isStorm) {
      return createTheme("storm-night", "Dông đêm", "⛈️", "#60a5fa", "bad", isWindy);
    }
    if (isRain) {
      return createTheme("rain-night", "Mưa đêm", "🌧️", "#7dd3fc", "medium", isWindy);
    }
    if (isWindy) {
      return createTheme("wind-night", "Đêm có gió", "🌬️", "#93c5fd", "medium", true);
    }
    return createTheme("night", "Ban đêm", "🌙", "#a78bfa", "good", false);
  }
  if (isStorm) {
    return createTheme("storm", "Dông", "⛈️", "#60a5fa", "bad", isWindy);
  }
  if (isRain) {
    return createTheme("rain", "Mưa", "🌧️", "#7dd3fc", "medium", isWindy);
  }
  if (isWindy) {
    return createTheme("wind", "Gió", "🌬️", "#93c5fd", "medium", true);
  }
  if (isDay === true && temperature >= 34) {
    return createTheme("hot", "Nắng gắt", "☀️", "#fbbf24", "medium", false);
  }
  if (isDay === true && (weatherCode === undefined || clearCodes.has(weatherCode))) {
    return createTheme("day", "Trời đẹp", "🌤️", "#5eead4", "good", false);
  }
  if (isDay === true && weatherCode !== undefined && cloudyCodes.has(weatherCode)) {
    return createTheme("cloudy-day", "Có mây ban ngày", "☁️", "#93c5fd", "good", false);
  }
  return createTheme("cloudy", "Có mây", "☁️", "#c4b5fd", "good", false);
}

export function getWeatherIcon(weather: WeatherDisplayState): string {
  const code = weather.weather_code;
  if (weather.is_day === false) return "🌙";
  if (code !== undefined && stormCodes.has(code)) return "⛈️";
  if (code !== undefined && rainCodes.has(code)) return "🌧️";
  if ((weather.wind_speed_kmh ?? 0) >= 30) return "🌬️";
  if ((weather.temperature_c ?? 0) >= 34) return "☀️";
  if (code !== undefined && clearCodes.has(code)) return "🌤️";
  return "☁️";
}

export function getScoreTone(score?: number): "good" | "medium" | "bad" {
  if (typeof score !== "number") return "medium";
  if (score >= 80) return "good";
  if (score >= 50) return "medium";
  return "bad";
}

function createTheme(
  key: WeatherThemeKey,
  label: string,
  icon: string,
  accent: string,
  scoreTone: "good" | "medium" | "bad",
  isWindy: boolean,
): WeatherTheme {
  return { key, label, icon, accent, scoreTone, isWindy };
}

function deriveIsDayFromBackendTime(time?: string): boolean | null {
  if (!time || time.length < 13) return null;
  const hour = Number(time.slice(11, 13));
  if (Number.isNaN(hour)) return null;
  return hour >= 6 && hour < 18;
}
