export type StudyShift = "morning" | "afternoon" | "evening";
export type VehicleType = "motorbike" | "bus" | "walking" | "car" | "bicycle";
export type AppView = "home" | "forecast" | "study" | "schedule" | "settings" | "auth";
export type StudyDateMode = "today" | "tomorrow" | "custom";
export type LocationMode = "current" | "search" | "confirmed";

export interface AdministrativeLevels {
  hamlet?: string | null;
  ward_or_commune?: string | null;
  district?: string | null;
  province?: string | null;
  country?: string | null;
}

export interface Coordinates {
  latitude: number;
  longitude: number;
  accuracy?: number;
}

export type LocationQuery =
  | { mode: "search"; city: string }
  | { mode: "current"; latitude: number; longitude: number; accuracy?: number }
  | { mode: "confirmed"; latitude: number; longitude: number; displayName: string; shortDisplayName?: string; administrativeLevels?: AdministrativeLevels };

export interface StudySchedule {
  study_date: string;
  start_time: string;
  end_time: string;
  vehicle_type: VehicleType;
}

type BaseStudentAdviceRequest = StudySchedule;

export interface CityBasedAdviceRequest extends BaseStudentAdviceRequest {
  city: string;
  latitude?: never;
  longitude?: never;
}

export interface CoordinateBasedAdviceRequest extends BaseStudentAdviceRequest {
  city?: never;
  latitude: number;
  longitude: number;
  accuracy_meters?: number;
}

export type StudentAdviceRequest = CityBasedAdviceRequest | CoordinateBasedAdviceRequest;

export interface WeatherMetric {
  max_temperature_c: number;
  max_apparent_temperature_c: number;
  max_precipitation_probability_percent: number;
  total_rain_mm: number;
  max_wind_speed_kmh: number;
  max_uv_index: number;
  average_humidity_percent: number;
}

export interface HourlyForecastItem {
  time: string;
  temperature_c?: number;
  apparent_temperature_c?: number;
  relative_humidity_percent?: number;
  precipitation_probability_percent?: number;
  precipitation_mm?: number;
  rain_mm?: number;
  weather_code?: number;
  weather_description?: string;
  wind_speed_kmh?: number;
  uv_index?: number;
  is_day?: boolean | null;
}

export interface DailyForecastItem {
  date: string;
  weather_code: number;
  weather_description: string;
  temperature_max_c: number;
  temperature_min_c: number;
  precipitation_probability_max_percent: number;
  rain_sum_mm: number;
  wind_speed_max_kmh: number;
  uv_index_max: number;
  sunrise: string;
  sunset: string;
}

export interface StudentAdviceResponse {
  city: string;
  source?: "city" | "coordinates" | string;
  location_name: string;
  display_name?: string;
  short_display_name?: string | null;
  administrative_levels?: AdministrativeLevels | null;
  country: string;
  latitude: number;
  longitude: number;
  timezone?: string | null;
  accuracy_meters?: number | null;
  location_confidence?: "exact" | "district" | "province" | "coordinates" | string;
  location_provider?: string;
  provider?: string;
  fallback_provider_used?: boolean;
  fallback_provider?: string | null;
  provider_condition?: string | null;
  effective_condition?: string | null;
  override_source?: string | null;
  override_expires_at?: string | null;
  override_report_id?: string | null;
  override_intensity?: string | null;
  needs_user_confirmation?: boolean;
  location_candidates?: string[];
  study_date: string;
  start_time: string;
  end_time: string;
  vehicle_type: VehicleType;
  score: number;
  level: string;
  summary: string;
  timeline: StudyTimeline;
  metrics: WeatherMetric;
  recommendations: string[];
  warnings: string[];
  hourly_forecast: HourlyForecastItem[];
  weather_code: number;
  weather_description: string;
  is_day?: boolean | null;
  time: string;
  wind_speed_kmh: number;
  precipitation_probability_percent: number;
  temperature_c: number;
}

export interface BeforeAfterClassTimeline {
  time: string;
  message: string;
  temperature_c: number;
  precipitation_probability_percent: number;
  weather_description: string;
}

export interface DuringClassTimeline {
  time_range: string;
  message: string;
  max_temperature_c: number;
  max_precipitation_probability_percent: number;
}

export interface StudyTimeline {
  before_class: BeforeAfterClassTimeline;
  during_class: DuringClassTimeline;
  after_class: BeforeAfterClassTimeline;
}

export interface CurrentWeatherItem {
  temperature_c?: number;
  apparent_temperature_c?: number;
  relative_humidity_percent?: number;
  precipitation_probability_percent?: number | null;
  precipitation_mm?: number;
  rain_mm?: number;
  showers_mm?: number | null;
  weather_code?: number;
  weather_description?: string;
  wind_speed_kmh?: number;
  wind_direction_degrees?: number | null;
  uv_index?: number;
  pressure_hpa?: number | null;
  visibility_meters?: number | null;
  cloud_cover_percent?: number | null;
  time?: string;
  is_day?: boolean | null;
}

export interface CurrentWeatherResponse {
  city: string;
  source?: "city" | "coordinates" | string;
  location_name?: string;
  display_name?: string;
  short_display_name?: string | null;
  administrative_levels?: AdministrativeLevels | null;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
  accuracy_meters?: number | null;
  location_confidence?: "exact" | "district" | "province" | "coordinates" | string;
  location_provider?: string;
  provider?: string;
  fallback_provider_used?: boolean;
  fallback_provider?: string | null;
  provider_condition?: string | null;
  effective_condition?: string | null;
  override_source?: string | null;
  override_expires_at?: string | null;
  override_report_id?: string | null;
  override_intensity?: string | null;
  provider_weather_code?: number | null;
  provider_weather_description?: string | null;
  needs_user_confirmation?: boolean;
  location_candidates?: string[];
  current: CurrentWeatherItem;
}

export type LocalWeatherCondition = "rain" | "no_rain" | "storm";
export type LocalWeatherIntensity = "light" | "moderate" | "heavy";

export interface LocalWeatherReportPayload {
  location_name: string;
  latitude: number;
  longitude: number;
  reported_condition: LocalWeatherCondition;
  intensity?: LocalWeatherIntensity | null;
  expires_in_minutes?: number;
}

export interface LocalWeatherReportResponse {
  id: string;
  user_id: string;
  location_name: string;
  latitude: number;
  longitude: number;
  reported_condition: LocalWeatherCondition;
  intensity: LocalWeatherIntensity | null;
  source: "user_report" | string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  expires_at: string;
}

export interface HourlyWeatherResponse {
  city: string;
  source?: "city" | "coordinates" | string;
  location_name?: string;
  display_name?: string;
  short_display_name?: string | null;
  administrative_levels?: AdministrativeLevels | null;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
  accuracy_meters?: number | null;
  location_confidence?: "exact" | "district" | "province" | "coordinates" | string;
  location_provider?: string;
  provider?: string;
  fallback_provider_used?: boolean;
  fallback_provider?: string | null;
  needs_user_confirmation?: boolean;
  location_candidates?: string[];
  hourly: HourlyForecastItem[];
}

export interface DailyWeatherResponse {
  city: string;
  source?: "city" | "coordinates" | string;
  location_name?: string;
  display_name?: string;
  short_display_name?: string | null;
  administrative_levels?: AdministrativeLevels | null;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
  accuracy_meters?: number | null;
  location_confidence?: "exact" | "district" | "province" | "coordinates" | string;
  location_provider?: string;
  provider?: string;
  fallback_provider_used?: boolean;
  fallback_provider?: string | null;
  needs_user_confirmation?: boolean;
  location_candidates?: string[];
  daily: DailyForecastItem[];
}

export interface WeatherDisplayState {
  weather_code?: number;
  weather_description?: string;
  is_day?: boolean | null;
  time?: string;
  wind_speed_kmh?: number;
  precipitation_probability_percent?: number;
  temperature_c?: number;
}

export interface SearchLocationCandidate {
  city: string;
  country: string;
  latitude: number;
  longitude: number;
  timezone: string;
  display_name: string;
  short_display_name?: string | null;
  administrative_levels?: AdministrativeLevels | null;
  location_confidence: string;
  location_provider: string;
}

export interface User {
  id: string;
  email: string | null;
  username: string | null;
  full_name: string | null;
  avatar_url: string | null;
  auth_provider: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserLocationResponse {
  id: string;
  user_id: string;
  label: string;
  display_name: string;
  short_display_name: string | null;
  latitude: number;
  longitude: number;
  source: string;
  administrative_levels: AdministrativeLevels | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudyScheduleResponse {
  id: string;
  user_id: string;
  title: string;
  study_date: string | null;
  start_time: string;
  end_time: string;
  vehicle_type: VehicleType;
  location_id: string | null;
  repeat_type: string;
  repeat_days: string[] | null;
  note: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserSettingsResponse {
  id: string;
  user_id: string;
  temperature_unit: "celsius" | "fahrenheit";
  theme_mode: "auto" | "light" | "dark";
  auto_refresh_enabled: boolean;
  notification_enabled: boolean;
  default_vehicle_type: VehicleType;
  default_location_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserNotification {
  id: string;
  user_id: string;
  schedule_id: string | null;
  type: string;
  title: string;
  message: string;
  channel: string; // email | in_app | browser
  status: string; // pending | sent | failed | read
  error_message: string | null;
  scheduled_for: string | null;
  sent_at: string | null;
  read_at: string | null;
  occurrence_key?: string | null;
  risk_level?: string | null;
  content_hash?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TestNotificationResponse {
  notification_id: string;
  channels_attempted: string[];
  channels_succeeded: string[];
  channels_failed: string[];
  message: string;
}
