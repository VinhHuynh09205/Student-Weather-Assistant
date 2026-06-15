import type { ClassScheduleForecastStatus, ClassScheduleRiskLevel } from "../types/classSchedule";

export const dayOfWeekOptions = [
  { value: 0, label: "Thứ 2", shortLabel: "T2" },
  { value: 1, label: "Thứ 3", shortLabel: "T3" },
  { value: 2, label: "Thứ 4", shortLabel: "T4" },
  { value: 3, label: "Thứ 5", shortLabel: "T5" },
  { value: 4, label: "Thứ 6", shortLabel: "T6" },
  { value: 5, label: "Thứ 7", shortLabel: "T7" },
  { value: 6, label: "Chủ nhật", shortLabel: "CN" },
];

export const riskLevelLabels: Record<ClassScheduleRiskLevel, string> = {
  SAFE: "An toàn",
  NOTICE: "Cần chú ý",
  PREPARE: "Nên chuẩn bị",
  DANGER: "Nguy hiểm",
};

export const forecastStatusLabels: Record<ClassScheduleForecastStatus, string> = {
  available: "Đã có dự báo",
  pending: "Đợi gần ngày học",
  expired: "Hết hiệu lực",
  missing_location: "Thiếu địa điểm",
  unavailable: "Chưa khả dụng",
  error: "Chưa thể cập nhật",
};

export function formatDayOfWeek(dayOfWeek?: number | null): string {
  return dayOfWeekOptions.find((item) => item.value === dayOfWeek)?.label ?? "--";
}

export function formatClassTime(value?: string | null): string {
  if (!value) return "--:--";
  return value.slice(0, 5);
}

export function formatOccurrenceDateTime(value?: string | null): string {
  if (!value) return "Chưa xác định";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("vi-VN", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  }) + `, ${date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`;
}

export function formatOccurrenceRange(start?: string | null, end?: string | null): string {
  if (!start) return "Chưa có buổi học kế tiếp";
  const startDate = new Date(start);
  const endDate = end ? new Date(end) : null;
  if (Number.isNaN(startDate.getTime())) return start;

  const dateLabel = startDate.toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
  });
  const startLabel = startDate.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  const endLabel =
    endDate && !Number.isNaN(endDate.getTime())
      ? endDate.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })
      : "--:--";

  return `${dateLabel}, ${startLabel} - ${endLabel}`;
}

export function normalizeTimeForInput(value?: string | null): string {
  if (!value) return "";
  return value.slice(0, 5);
}

export function formatSemesterRange(start?: string | null, end?: string | null): string {
  if (!start && !end) return "Không giới hạn học kỳ";
  if (start && end) return `${formatDate(start)} - ${formatDate(end)}`;
  if (start) return `Từ ${formatDate(start)}`;
  return `Đến ${formatDate(end)}`;
}

function formatDate(value?: string | null): string {
  if (!value) return "--";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}
