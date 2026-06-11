export function getNowForTimezone(timezone?: string): Date {
  if (!timezone || timezone === "auto") {
    return new Date();
  }
  try {
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: timezone,
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
      second: "numeric",
      hour12: false,
    });
    const parts = formatter.formatToParts(new Date());
    const dict: Record<string, number> = {};
    for (const part of parts) {
      if (part.type !== "literal") {
        dict[part.type] = parseInt(part.value, 10);
      }
    }
    return new Date(
      dict.year,
      dict.month - 1,
      dict.day,
      dict.hour,
      dict.minute,
      dict.second
    );
  } catch (e) {
    console.error("Error formatting timezone now:", e);
    return new Date();
  }
}

export function formatClockTime(date: Date, timezone?: string): string {
  const options: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    ...(timezone && timezone !== "auto" ? { timeZone: timezone } : {}),
  };
  try {
    return date.toLocaleTimeString("vi-VN", options);
  } catch {
    return date.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }
}

export function formatDateLabel(date: Date, timezone?: string): string {
  const options: Intl.DateTimeFormatOptions = {
    weekday: "long",
    day: "numeric",
    month: "numeric",
    ...(timezone && timezone !== "auto" ? { timeZone: timezone } : {}),
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

export function formatWeatherUpdatedAt(weatherTime?: string, timezone?: string): string {
  if (!weatherTime) return "--:--";

  if (weatherTime.includes("T")) {
    const parts = weatherTime.split("T");
    if (parts.length > 1 && parts[1].length >= 5) {
      return parts[1].slice(0, 5);
    }
  }

  const date = new Date(weatherTime);
  if (Number.isNaN(date.getTime())) {
    return "--:--";
  }

  const options: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    ...(timezone && timezone !== "auto" ? { timeZone: timezone } : {}),
  };
  try {
    return date.toLocaleTimeString("vi-VN", options);
  } catch {
    return date.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }
}
