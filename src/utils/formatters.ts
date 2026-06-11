import type { StudyShift, VehicleType } from "../types/weather";

const noDataLabel = "Chưa có dữ liệu";

export const shiftLabels: Record<StudyShift, string> = {
  morning: "Ca sáng",
  afternoon: "Ca chiều",
  evening: "Ca tối",
};

export const shiftTimes: Record<StudyShift, string> = {
  morning: "07:00 - 11:00",
  afternoon: "13:00 - 17:00",
  evening: "18:00 - 21:00",
};

export const vehicleLabels: Record<VehicleType, string> = {
  motorbike: "Xe máy",
  bus: "Xe buýt",
  walking: "Đi bộ",
  bicycle: "Xe đạp",
};

export function formatTemperature(value?: number, unit?: "celsius" | "fahrenheit"): string {
  if (typeof value !== "number") return "--";
  const activeUnit = unit || (window as unknown as { __temperature_unit?: string }).__temperature_unit || "celsius";
  if (activeUnit === "fahrenheit") {
    const f = Math.round((value * 9) / 5 + 32);
    return `${f}°F`;
  }
  return `${Math.round(value)}°C`;
}

export function formatPercent(value?: number): string {
  return typeof value === "number" ? `${Math.round(value)}%` : "--";
}

export function formatWind(value?: number): string {
  return typeof value === "number" ? `${Math.round(value)} km/h` : "--";
}

export function formatMillimeters(value?: number): string {
  return typeof value === "number" ? `${Number(value.toFixed(1))} mm` : "--";
}

export function formatRainAmount(value?: number | null): string {
  if (typeof value !== "number") return noDataLabel;
  if (value <= 0) return "Không có mưa";
  return `${Number(value.toFixed(1))} mm`;
}

export function formatUvIndex(value?: number | null, isDay?: boolean | null): string {
  if (isDay === false) return "Không đáng kể";
  if (typeof value !== "number") return noDataLabel;
  return `${Math.round(value)}`;
}

export function formatOptionalPercent(value?: number | null): string {
  return typeof value === "number" ? `${Math.round(value)}%` : noDataLabel;
}

export function formatOptionalNumber(value?: number | null, unit = ""): string {
  if (typeof value !== "number") return noDataLabel;
  return `${Number(value.toFixed(1))}${unit ? ` ${unit}` : ""}`;
}

export function formatLocationDisplay(location?: {
  city?: string | null;
  display_name?: string | null;
  latitude?: number;
  location_name?: string | null;
  longitude?: number;
  location_confidence?: string | null;
} | null): string {
  if (!location) return "";
  const confidence = location.location_confidence;
  if (confidence === "coordinates" || confidence === "uncertain") {
    return "Vị trí hiện tại chưa xác định rõ";
  }
  if (location.display_name) {
    if (location.display_name.includes("Vị trí GPS hiện tại")) {
      return "Vị trí hiện tại chưa xác định rõ";
    }
    return location.display_name;
  }
  if (location.location_name && location.location_name !== "Vị trí hiện tại") {
    return location.location_name;
  }
  if (location.city) {
    return location.city;
  }
  return "";
}

export function formatAccuracy(value?: number | null, compact = false): string | null {
  if (typeof value !== "number") return null;
  const rounded = Math.round(value);
  return compact ? `GPS ±${rounded}m` : `Độ chính xác khoảng ${rounded} mét`;
}

export function formatCoordinates(latitude?: number, longitude?: number): string {
  if (typeof latitude !== "number" || typeof longitude !== "number") return "";
  return `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
}

export function formatWeatherAlert(value: string): string {
  return value;
}

export function formatHour(value?: string): string {
  if (!value) return "--:--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.slice(11, 16) || "--:--";
  }
  return date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

export function formatShortDate(date = new Date(), timeZone?: string): string {
  const options: Intl.DateTimeFormatOptions = {
    weekday: "long",
    day: "numeric",
    month: "numeric",
    ...(timeZone ? { timeZone } : {}),
  };
  try {
    return date.toLocaleDateString("vi-VN", options);
  } catch {
    return date.toLocaleDateString("vi-VN", {
      weekday: "long",
      day: "numeric",
      month: "numeric",
    });
  }
}

export function formatStudyDate(value?: string): string {
  if (!value) return "--";
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;

  const date = new Date(year, month - 1, day);
  const today = startOfDay(new Date());
  const tomorrow = addDays(today, 1);
  const target = startOfDay(date);

  if (target.getTime() === today.getTime()) return "Hôm nay";
  if (target.getTime() === tomorrow.getTime()) return "Ngày mai";

  return date.toLocaleDateString("vi-VN", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  });
}

export function formatScheduleRange(studyDate?: string, startTime?: string, endTime?: string): string {
  const dateLabel = formatStudyDate(studyDate);
  if (!startTime || !endTime) return dateLabel;
  return `${dateLabel}, ${startTime} - ${endTime}`;
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function addDays(date: Date, days: number): Date {
  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + days);
  return nextDate;
}
