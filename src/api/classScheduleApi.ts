import type {
  ClassScheduleForecast,
  DeleteClassScheduleResponse,
  WeeklyClassSchedule,
  WeeklyClassSchedulePayload,
  WeeklyClassScheduleUpdatePayload,
} from "../types/classSchedule";
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
    throw new Error(await readErrorMessage(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    return undefined as T;
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return "Một vài thông tin lịch học chưa hợp lệ. Vui lòng kiểm tra lại form.";
  } catch {
    // Fall through to a friendly generic message below.
  }

  if (response.status === 401) return "Bạn cần đăng nhập để quản lý lịch học hằng tuần.";
  if (response.status === 404) return "Không tìm thấy lịch học này hoặc bạn không có quyền truy cập.";
  return response.statusText || "Không thể xử lý lịch học lúc này.";
}

export function getClassSchedules(): Promise<WeeklyClassSchedule[]> {
  return requestJson<WeeklyClassSchedule[]>("/api/v1/class-schedules");
}

export function createClassSchedule(payload: WeeklyClassSchedulePayload): Promise<WeeklyClassSchedule> {
  return requestJson<WeeklyClassSchedule>("/api/v1/class-schedules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateClassSchedule(
  scheduleId: string,
  payload: WeeklyClassScheduleUpdatePayload,
): Promise<WeeklyClassSchedule> {
  return requestJson<WeeklyClassSchedule>(`/api/v1/class-schedules/${scheduleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteClassSchedule(scheduleId: string): Promise<DeleteClassScheduleResponse> {
  return requestJson<DeleteClassScheduleResponse>(`/api/v1/class-schedules/${scheduleId}`, {
    method: "DELETE",
  });
}

export function getNextForecast(scheduleId: string): Promise<ClassScheduleForecast> {
  return requestJson<ClassScheduleForecast>(`/api/v1/class-schedules/${scheduleId}/next-forecast`);
}

export function getUpcomingForecasts(limit = 10): Promise<ClassScheduleForecast[]> {
  return requestJson<ClassScheduleForecast[]>(`/api/v1/class-schedules/upcoming-forecasts?limit=${limit}`);
}
