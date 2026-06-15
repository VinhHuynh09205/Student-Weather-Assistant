import type {
  UserLocationResponse,
  StudyScheduleResponse,
  UserSettingsResponse,
  VehicleType,
  AdministrativeLevels,
  UserNotification,
  TestNotificationResponse,
} from "../types/weather";
import { getStoredAuthToken } from "../utils/authToken";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://sw-alb-v7-1940911359.ap-southeast-1.elb.amazonaws.com";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredAuthToken();
  const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = "Đã xảy ra lỗi hệ thống";
    try {
      const err = await response.json();
      errorDetail = err.detail || errorDetail;
    } catch {
      errorDetail = response.statusText || errorDetail;
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) { // No Content
    return {} as T;
  }
  
  try {
    return (await response.json()) as T;
  } catch {
    return {} as T;
  }
}

// User Settings API
export function getUserSettings(): Promise<UserSettingsResponse> {
  return requestJson<UserSettingsResponse>("/api/v1/settings");
}

export function updateUserSettings(settings: {
  temperature_unit?: "celsius" | "fahrenheit";
  theme_mode?: "auto" | "light" | "dark";
  auto_refresh_enabled?: boolean;
  notification_enabled?: boolean;
  default_vehicle_type?: VehicleType;
  default_location_id?: string | null;
}): Promise<UserSettingsResponse> {
  return requestJson<UserSettingsResponse>("/api/v1/settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

// User Locations API
export function getUserLocations(): Promise<UserLocationResponse[]> {
  return requestJson<UserLocationResponse[]>("/api/v1/locations");
}

export function createUserLocation(location: {
  label: string;
  display_name: string;
  short_display_name?: string | null;
  latitude: number;
  longitude: number;
  source: string;
  administrative_levels?: AdministrativeLevels | null;
  is_default?: boolean;
}): Promise<UserLocationResponse> {
  return requestJson<UserLocationResponse>("/api/v1/locations", {
    method: "POST",
    body: JSON.stringify(location),
  });
}

export function deleteUserLocation(locationId: string): Promise<void> {
  return requestJson<void>(`/api/v1/locations/${locationId}`, {
    method: "DELETE",
  });
}

export function setDefaultLocation(locationId: string): Promise<UserLocationResponse> {
  return requestJson<UserLocationResponse>(`/api/v1/locations/${locationId}/set-default`, {
    method: "POST",
  });
}

// Study Schedules API
export function getUserSchedules(): Promise<StudyScheduleResponse[]> {
  return requestJson<StudyScheduleResponse[]>("/api/v1/schedules");
}

export function getUpcomingSchedule(): Promise<StudyScheduleResponse | null> {
  return requestJson<StudyScheduleResponse | null>("/api/v1/schedules/upcoming");
}

export function createStudySchedule(schedule: {
  title: string;
  study_date?: string | null;
  start_time: string;
  end_time: string;
  vehicle_type: VehicleType;
  location_id?: string | null;
  repeat_type: string; // none, weekly
  repeat_days?: string[] | null;
  note?: string | null;
  is_active?: boolean;
}): Promise<StudyScheduleResponse> {
  return requestJson<StudyScheduleResponse>("/api/v1/schedules", {
    method: "POST",
    body: JSON.stringify(schedule),
  });
}

export function updateStudySchedule(
  scheduleId: string,
  schedule: {
    title?: string;
    study_date?: string | null;
    start_time?: string;
    end_time?: string;
    vehicle_type?: VehicleType;
    location_id?: string | null;
    repeat_type?: string;
    repeat_days?: string[] | null;
    note?: string | null;
    is_active?: boolean;
  }
): Promise<StudyScheduleResponse> {
  return requestJson<StudyScheduleResponse>(`/api/v1/schedules/${scheduleId}`, {
    method: "PUT",
    body: JSON.stringify(schedule),
  });
}

export function deleteStudySchedule(scheduleId: string): Promise<void> {
  return requestJson<void>(`/api/v1/schedules/${scheduleId}`, {
    method: "DELETE",
  });
}

// User Notifications API
export function getUserNotifications(): Promise<UserNotification[]> {
  return requestJson<UserNotification[]>("/api/v1/notifications");
}

export function markNotificationAsRead(notificationId: string): Promise<UserNotification> {
  return requestJson<UserNotification>(`/api/v1/notifications/${notificationId}/read`, {
    method: "PATCH",
  });
}

export function deleteNotification(notificationId: string): Promise<void> {
  return requestJson<void>(`/api/v1/notifications/${notificationId}`, {
    method: "DELETE",
  });
}

export function deleteAllNotifications(): Promise<{ deleted_count: number }> {
  return requestJson<{ deleted_count: number }>("/api/v1/notifications", {
    method: "DELETE",
  });
}

export function sendTestNotification(): Promise<TestNotificationResponse> {
  return requestJson<TestNotificationResponse>("/api/v1/notifications/test", {
    method: "POST",
  });
}
