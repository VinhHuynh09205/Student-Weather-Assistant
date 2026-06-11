import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { DailyForecastCard } from "../components/weather/DailyForecastCard";
import { ForecastHighlightsCard } from "../components/weather/ForecastHighlightsCard";
import { HourlyForecastCard } from "../components/weather/HourlyForecastCard";
import { RainProbabilityCard } from "../components/weather/RainProbabilityCard";
import { TemperatureChart } from "../components/weather/TemperatureChart";
import { WeatherMetricGrid } from "../components/weather/WeatherMetricGrid";
import { WeatherTrendCards } from "../components/weather/WeatherTrendCards";
import type { CurrentWeatherResponse, DailyForecastItem, HourlyForecastItem } from "../types/weather";

type ForecastPageProps = {
  currentError: string | null;
  currentLoading: boolean;
  currentWeather: CurrentWeatherResponse | null;
  dailyError: string | null;
  dailyItems: DailyForecastItem[];
  dailyLoading: boolean;
  hourlyError: string | null;
  hourlyItems: HourlyForecastItem[];
  hourlyLoading: boolean;
  onRetry: () => void;
};

export function ForecastPage({
  currentError,
  currentLoading,
  currentWeather,
  dailyError,
  dailyItems,
  dailyLoading,
  hourlyError,
  hourlyItems,
  hourlyLoading,
  onRetry,
}: ForecastPageProps) {
  return (
    <section className="forecast-page">
      {currentLoading ? <LoadingState message="Đang tải thời tiết hiện tại..." /> : null}
      {currentError ? <ErrorState message={currentError} onRetry={onRetry} /> : null}
      <WeatherMetricGrid currentWeather={currentWeather} nearestHourly={hourlyItems[0]} />

      <div className="forecast-grid">
        <div className="weather-block-stack">
          {hourlyLoading ? <LoadingState message="Đang tải dự báo theo giờ..." /> : null}
          {hourlyError ? <ErrorState message={hourlyError} onRetry={onRetry} /> : null}
          <HourlyForecastCard items={hourlyItems} />
        </div>
        <TemperatureChart items={hourlyItems} />
        <RainProbabilityCard items={hourlyItems} />
        <WeatherTrendCards items={hourlyItems} />
        <div className="weather-block-stack full-row">
          <ForecastHighlightsCard hourlyItems={hourlyItems} dailyItems={dailyItems} />
        </div>
        <div className="weather-block-stack full-row">
          {dailyLoading ? <LoadingState message="Đang tải dự báo nhiều ngày..." /> : null}
          {dailyError ? <ErrorState message={dailyError} onRetry={onRetry} /> : null}
          <DailyForecastCard items={dailyItems} />
        </div>
      </div>
    </section>
  );
}
