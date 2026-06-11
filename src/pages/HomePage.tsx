import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { CurrentWeatherCard } from "../components/weather/CurrentWeatherCard";
import { DailyForecastCard } from "../components/weather/DailyForecastCard";
import { HourlyForecastCard } from "../components/weather/HourlyForecastCard";
import { WeatherAlertCard } from "../components/weather/WeatherAlertCard";
import { WeatherMetricGrid } from "../components/weather/WeatherMetricGrid";
import { WeatherTrendCards } from "../components/weather/WeatherTrendCards";
import type {
  Coordinates,
  CurrentWeatherResponse,
  DailyForecastItem,
  HourlyForecastItem,
  LocationMode,
  StudentAdviceResponse,
  StudyScheduleResponse,
} from "../types/weather";

type HomePageProps = {
  coordinates: Coordinates | null;
  currentError: string | null;
  currentLoading: boolean;
  currentWeather: CurrentWeatherResponse | null;
  dailyError: string | null;
  dailyItems: DailyForecastItem[];
  dailyLoading: boolean;
  hasSavedSchedule: boolean;
  hourlyError: string | null;
  hourlyItems: HourlyForecastItem[];
  hourlyLoading: boolean;
  locationMode: LocationMode;
  locationName: string;
  studyAdvice: StudentAdviceResponse | null;
  studySchedule: StudyScheduleResponse | null;
  onOpenStudyAssistant: () => void;
  onRetry: () => void;
  onRefresh?: () => Promise<void>;
  isRefreshing?: boolean;
};

export function HomePage({
  coordinates,
  currentError,
  currentLoading,
  currentWeather,
  dailyError,
  dailyItems,
  dailyLoading,
  hasSavedSchedule,
  hourlyError,
  hourlyItems,
  hourlyLoading,
  locationMode,
  locationName,
  onOpenStudyAssistant,
  onRetry,
  studyAdvice,
  studySchedule,
}: HomePageProps) {
  return (
    <section className="home-page">
      <div className="home-main-layout">
        <div className="home-left-col">
          <div className="weather-block-stack home-current-weather">
            {currentLoading ? <LoadingState message="Đang tải thời tiết hiện tại..." /> : null}
            {currentError ? <ErrorState message={currentError} onRetry={onRetry} /> : null}
            <CurrentWeatherCard
              coordinates={coordinates}
              currentWeather={currentWeather}
              locationMode={locationMode}
              locationName={locationName}
              studySchedule={studySchedule}
              studyAdvice={studyAdvice}
              hasSavedSchedule={hasSavedSchedule}
              onOpenStudyAssistant={onOpenStudyAssistant}
            />
          </div>

          <div className="home-metrics">
            <WeatherMetricGrid currentWeather={currentWeather} nearestHourly={hourlyItems[0]} />
          </div>

          <div className="weather-block-stack home-hourly-forecast">
            {hourlyLoading ? <LoadingState message="Đang tải dự báo theo giờ..." /> : null}
            {hourlyError ? <ErrorState message={hourlyError} onRetry={onRetry} /> : null}
            <HourlyForecastCard items={hourlyItems} />
          </div>

          <div className="home-trends">
            <WeatherTrendCards items={hourlyItems} />
          </div>
        </div>

        <div className="home-right-col">
          <div className="weather-block-stack home-alerts">
            <WeatherAlertCard currentWeather={currentWeather} daily={dailyItems[0]} hourlyItems={hourlyItems} />
          </div>
          <div className="weather-block-stack home-daily-forecast">
            {dailyLoading ? <LoadingState message="Đang tải dự báo nhiều ngày..." /> : null}
            {dailyError ? <ErrorState message={dailyError} onRetry={onRetry} /> : null}
            <DailyForecastCard items={dailyItems} />
          </div>
        </div>
      </div>
    </section>
  );
}

