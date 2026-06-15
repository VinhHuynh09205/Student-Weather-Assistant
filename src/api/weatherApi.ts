import type {
  CurrentWeatherResponse,
  DailyWeatherResponse,
  HourlyWeatherResponse,
  LocalWeatherReportPayload,
  LocalWeatherReportResponse,
  LocationQuery,
  StudentAdviceRequest,
  StudentAdviceResponse,
} from "../types/weather";
import { getStoredAuthToken } from "../utils/authToken";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://sw-alb-v7-1940911359.ap-southeast-1.elb.amazonaws.com";
const RATE_LIMIT_MESSAGE =
  "Dịch vụ thời tiết đang bị giới hạn tạm thời. Vui lòng thử lại sau ít phút.";
const pendingRequests = new Map<string, Promise<unknown>>();

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const requestKey = buildRequestKey(path, init);
  const pendingRequest = pendingRequests.get(requestKey);
  if (pendingRequest) return pendingRequest as Promise<T>;

  const token = getStoredAuthToken();
  const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const requestPromise = fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...init?.headers,
    },
  })
    .then(async (response) => {
      if (!response.ok) {
        let message = response.status === 429 ? RATE_LIMIT_MESSAGE : "Không thể tải dữ liệu thời tiết";
        try {
          const errorBody = (await response.json()) as { detail?: string };
          message = normalizeErrorMessage(errorBody.detail, response.status);
        } catch {
          message = response.status === 429 ? RATE_LIMIT_MESSAGE : response.statusText || message;
        }
        throw new Error(message);
      }

      return (await response.json()) as T;
    })
    .finally(() => {
      pendingRequests.delete(requestKey);
    });

  pendingRequests.set(requestKey, requestPromise);
  return requestPromise;
}

function buildRequestKey(path: string, init?: RequestInit): string {
  return JSON.stringify({
    path,
    method: init?.method ?? "GET",
    body: typeof init?.body === "string" ? init.body : "",
  });
}

function normalizeErrorMessage(detail: string | undefined, status: number): string {
  if (status === 429) return RATE_LIMIT_MESSAGE;
  if (!detail) return "Không thể tải dữ liệu thời tiết";
  if (detail.includes("Open-Meteo returned HTTP 429")) {
    return RATE_LIMIT_MESSAGE;
  }
  return detail;
}

export function getCurrentWeather(source: LocationQuery): Promise<CurrentWeatherResponse> {
  return requestJson<CurrentWeatherResponse>(`/api/v1/weather/current?${buildLocationParams(source)}`);
}

export function getHourlyWeather(source: LocationQuery, hours: number): Promise<HourlyWeatherResponse> {
  const params = buildLocationParams(source);
  params.set("hours", String(hours));
  return requestJson<HourlyWeatherResponse>(`/api/v1/weather/hourly?${params}`);
}

export function getDailyWeather(source: LocationQuery, days: number): Promise<DailyWeatherResponse> {
  const params = buildLocationParams(source);
  params.set("days", String(days));
  return requestJson<DailyWeatherResponse>(`/api/v1/weather/daily?${params}`);
}

export function getStudentAdvice(payload: StudentAdviceRequest): Promise<StudentAdviceResponse> {
  return requestJson<StudentAdviceResponse>("/api/v1/weather/student-advice", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

function buildLocationParams(source: LocationQuery): URLSearchParams {
  if (source.mode === "current" || source.mode === "confirmed") {
    const params = new URLSearchParams({
      latitude: String(source.latitude),
      longitude: String(source.longitude),
    });
    if (source.mode === "current" && typeof source.accuracy === "number") {
      params.set("accuracy_meters", String(source.accuracy));
    }
    return params;
  }
  return new URLSearchParams({ city: source.city });
}

export function searchLocations(query: string): Promise<SearchLocationCandidate[]> {
  return requestJson<SearchLocationCandidate[]>(`/api/v1/weather/search-location?query=${encodeURIComponent(query)}`);
}

export function createLocalWeatherReport(payload: LocalWeatherReportPayload): Promise<LocalWeatherReportResponse> {
  return requestJson<LocalWeatherReportResponse>("/api/v1/weather/local-report", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getActiveLocalWeatherReport(source?: LocationQuery): Promise<LocalWeatherReportResponse | null> {
  const params = source && (source.mode === "current" || source.mode === "confirmed")
    ? `?${new URLSearchParams({
        latitude: String(source.latitude),
        longitude: String(source.longitude),
      })}`
    : "";
  return requestJson<LocalWeatherReportResponse | null>(`/api/v1/weather/local-report/active${params}`);
}

export function clearActiveLocalWeatherReport(): Promise<{ cleared: boolean }> {
  return requestJson<{ cleared: boolean }>("/api/v1/weather/local-report/active", {
    method: "DELETE",
  });
}

import type { SearchLocationCandidate } from "../types/weather";
