export type ClassScheduleRiskLevel = "SAFE" | "NOTICE" | "PREPARE" | "DANGER";
export type ClassScheduleForecastStatus = "available" | "pending" | "expired" | "missing_location" | "unavailable" | "error";

export interface WeeklyClassSchedule {
  id: string;
  user_id: string;
  subject_name: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
  timezone: string;
  is_active: boolean;
  notify_before_minutes: number;
  rain_alert_enabled: boolean;
  storm_alert_enabled: boolean;
  semester_start_date: string | null;
  semester_end_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface WeeklyClassSchedulePayload {
  subject_name: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
  timezone?: string;
  is_active?: boolean;
  notify_before_minutes?: number;
  rain_alert_enabled?: boolean;
  storm_alert_enabled?: boolean;
  semester_start_date?: string | null;
  semester_end_date?: string | null;
}

export type WeeklyClassScheduleUpdatePayload = Partial<WeeklyClassSchedulePayload>;

export interface DeleteClassScheduleResponse {
  success: boolean;
  message: string;
  schedule_id: string;
  is_active: boolean;
}

export interface ClassScheduleOccurrence {
  occurrence_key: string;
  start_datetime: string;
  end_datetime: string;
  status: "scheduled" | "expired";
}

export interface ClassScheduleForecast {
  schedule: WeeklyClassSchedule;
  next_occurrence: ClassScheduleOccurrence | null;
  next_occurrence_datetime: string | null;
  forecast_status: ClassScheduleForecastStatus;
  weather_summary: string | null;
  risk_level: ClassScheduleRiskLevel;
  recommendation_message: string;
  weather_code: number | null;
  precipitation_probability_percent: number | null;
  rain_mm: number | null;
  wind_speed_kmh: number | null;
  provider: string | null;
}
