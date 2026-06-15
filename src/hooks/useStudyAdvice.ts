import { useCallback, useEffect, useMemo, useState } from "react";
import { getStudentAdvice } from "../api/weatherApi";
import type {
  LocationQuery,
  StudentAdviceRequest,
  StudentAdviceResponse,
  StudyDateMode,
  StudyShift,
  VehicleType,
  StudyScheduleResponse,
  UserLocationResponse,
} from "../types/weather";
import { useAutoRefresh } from "./useAutoRefresh";
import { useAuth } from "../context/AuthContext";
import { showAppToast, showErrorToast, showSuccessToast } from "../utils/toast";
import { normalizeVehicleType } from "../utils/formatters";

const defaultStartTime = "07:30";
const defaultEndTime = "11:00";

const studyTimePresets: Record<StudyShift, { startTime: string; endTime: string }> = {
  morning: { startTime: "07:00", endTime: "11:00" },
  afternoon: { startTime: "13:00", endTime: "17:00" },
  evening: { startTime: "18:00", endTime: "21:00" },
};

export function useStudyAdvice(source: LocationQuery | null) {
  const {
    schedules,
    savedLocations,
    addSchedule,
    editSchedule,
    removeSchedule,
    settings,
  } = useAuth();


  // Selection states
  const [selectedScheduleId, setSelectedScheduleId] = useState<string | null>(null);
  const [editingScheduleId, setEditingScheduleId] = useState<string | null>(null);

  // Form states
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [locationId, setLocationId] = useState<string | null>(null);
  const [studyDate, setStudyDate] = useState(() => formatInputDate(addDays(new Date(), 1)));
  const [startTime, setStartTime] = useState(defaultStartTime);
  const [endTime, setEndTime] = useState(defaultEndTime);
  const [selectedVehicle, setSelectedVehicle] = useState<VehicleType>("motorbike");

  const [advice, setAdvice] = useState<StudentAdviceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<number>(0);
  const [refetchTrigger, setRefetchTrigger] = useState(0);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [upcomingAdvice, setUpcomingAdvice] = useState<StudentAdviceResponse | null>(null);
  const [upcomingLastFetchedAt, setUpcomingLastFetchedAt] = useState<number>(0);

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 60 * 1000);
    return () => window.clearInterval(timer);
  }, []);

  // Auto-select first schedule on load or when list changes
  useEffect(() => {
    if (schedules.length > 0) {
      if (!selectedScheduleId || !schedules.some(s => s.id === selectedScheduleId)) {
        setSelectedScheduleId(schedules[0].id);
      }
    } else {
      setSelectedScheduleId(null);
    }
  }, [schedules, selectedScheduleId]);

  // Find active schedule and its resolved location
  const activeSchedule = useMemo(() => {
    return schedules.find((s) => s.id === selectedScheduleId) || null;
  }, [schedules, selectedScheduleId]);

  const upcomingSchedule = useMemo(() => {
    return findNextRelevantSchedule(schedules, new Date(nowMs));
  }, [schedules, nowMs]);

  const upcomingScheduleKey = useMemo(() => {
    return getScheduleAdviceKey(upcomingSchedule);
  }, [upcomingSchedule]);

  const activeLocationQuery = useMemo<LocationQuery | null>(() => {
    return resolveScheduleLocationQuery(activeSchedule, savedLocations, source);
  }, [activeSchedule, savedLocations, source]);

  const upcomingLocationQuery = useMemo<LocationQuery | null>(() => {
    return resolveScheduleLocationQuery(upcomingSchedule, savedLocations, source);
  }, [upcomingSchedule, savedLocations, source]);

  const sourceKey = useMemo(() => {
    return getLocationQueryKey(activeLocationQuery);
  }, [activeLocationQuery]);

  const upcomingSourceKey = useMemo(() => {
    return getLocationQueryKey(upcomingLocationQuery);
  }, [upcomingLocationQuery]);

  const studyDateMode = useMemo<StudyDateMode>(
    () => resolveDateMode(studyDate),
    [studyDate]
  );

  const refresh = useCallback(() => {
    setRefetchTrigger((prev) => prev + 1);
  }, []);

  // Fetch advice when active schedule details change
  useEffect(() => {
    if (!activeSchedule || !activeLocationQuery) {
      setAdvice(null);
      setLoading(false);
      return;
    }

    let ignore = false;
    setLoading(true);
    setError(null);

    const mappedSchedule = mapScheduleForAdvice(activeSchedule);

    getStudentAdvice(buildAdviceRequest(activeLocationQuery, mappedSchedule))
      .then((nextAdvice) => {
        if (!ignore) {
          setAdvice(nextAdvice);
          setLastFetchedAt(Date.now());
        }
      })
      .catch((unknownError) => {
        if (!ignore) {
          const err = unknownError instanceof Error ? unknownError : new Error("Không thể tải trợ lý đi học");
          setError(err.message);
          setAdvice(null);
        }
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [activeSchedule, activeLocationQuery, sourceKey, refetchTrigger]);

  useEffect(() => {
    if (!upcomingSchedule || !upcomingLocationQuery) {
      setUpcomingAdvice(null);
      setUpcomingLastFetchedAt(0);
      return;
    }

    let ignore = false;
    const mappedSchedule = mapScheduleForAdvice(upcomingSchedule);

    getStudentAdvice(buildAdviceRequest(upcomingLocationQuery, mappedSchedule))
      .then((nextAdvice) => {
        if (!ignore) {
          setUpcomingAdvice(nextAdvice);
          setUpcomingLastFetchedAt(Date.now());
        }
      })
      .catch(() => {
        if (!ignore) {
          setUpcomingAdvice(null);
        }
      });

    return () => {
      ignore = true;
    };
  }, [upcomingSchedule, upcomingScheduleKey, upcomingLocationQuery, upcomingSourceKey, refetchTrigger]);

  useAutoRefresh(
    lastFetchedAt,
    10 * 60 * 1000,
    refresh,
    Boolean(activeSchedule) && Boolean(activeLocationQuery) && !loading && settings.auto_refresh_enabled
  );

  useAutoRefresh(
    upcomingLastFetchedAt,
    10 * 60 * 1000,
    refresh,
    Boolean(upcomingSchedule) && Boolean(upcomingLocationQuery) && settings.auto_refresh_enabled
  );

  // Validate form schedule parameters on change
  useEffect(() => {
    setScheduleError(null);
    if (!studyDate) {
      setScheduleError("Vui lòng chọn ngày học.");
      return;
    }
    if (!isDateInRange(studyDate)) {
      setScheduleError("Ngày học phải nằm trong khoảng từ hôm nay đến 8 ngày tới.");
      return;
    }
    if (!startTime || !endTime) {
      setScheduleError("Vui lòng chọn giờ bắt đầu và kết thúc.");
      return;
    }
    if (endTime <= startTime) {
      setScheduleError("Giờ kết thúc phải lớn hơn giờ bắt đầu.");
      return;
    }
  }, [studyDate, startTime, endTime]);

  const changeStudyDateMode = useCallback((mode: StudyDateMode) => {
    if (mode === "today") {
      setStudyDate(formatInputDate(new Date()));
    } else if (mode === "tomorrow") {
      setStudyDate(formatInputDate(addDays(new Date(), 1)));
    }
  }, []);

  const changeStudyDate = useCallback((date: string) => {
    setStudyDate(date);
  }, []);

  const changeTimeRange = useCallback((start: string, end: string) => {
    setStartTime(start);
    setEndTime(end);
  }, []);

  const applyStudyPreset = useCallback((preset: StudyShift) => {
    const presetTimes = studyTimePresets[preset];
    changeTimeRange(presetTimes.startTime, presetTimes.endTime);
  }, [changeTimeRange]);

  const handleEditSchedule = useCallback((sched: StudyScheduleResponse) => {
    setEditingScheduleId(sched.id);
    setTitle(sched.title || "");
    setNote(sched.note || "");
    setLocationId(sched.location_id || null);
    setStudyDate(sched.study_date || formatInputDate(addDays(new Date(), 1)));
    setStartTime(sched.start_time.slice(0, 5));
    setEndTime(sched.end_time.slice(0, 5));
    setSelectedVehicle(normalizeVehicleType(sched.vehicle_type));
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingScheduleId(null);
    setTitle("");
    setNote("");
    setLocationId(null);
    setStudyDate(formatInputDate(addDays(new Date(), 1)));
    setStartTime(defaultStartTime);
    setEndTime(defaultEndTime);
    setSelectedVehicle("motorbike");
  }, []);

  const handleDeleteSchedule = useCallback(async (id: string) => {
    if (!window.confirm("Bạn có chắc chắn muốn xóa lịch học này không?")) return;

    if (selectedScheduleId === id) {
      const remaining = schedules.filter(s => s.id !== id);
      if (remaining.length > 0) {
        setSelectedScheduleId(remaining[0].id);
      } else {
        setSelectedScheduleId(null);
      }
    }
    if (editingScheduleId === id) {
      cancelEdit();
    }
    try {
      await removeSchedule(id);
      showSuccessToast("Đã xóa lịch học", "Lịch học đã được gỡ khỏi Trợ lý đi học.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Không thể xóa lịch học.";
      setScheduleError(message);
      showErrorToast("Không thể xóa lịch học", message);
    }
  }, [schedules, selectedScheduleId, editingScheduleId, removeSchedule, cancelEdit]);

  const handleSaveSchedule = useCallback(async () => {
    if (scheduleError) {
      showAppToast({ title: "Chưa thể lưu lịch học", message: scheduleError, variant: "warning" });
      return;
    }

    // Enforce 8 schedule limit when adding new
    if (!editingScheduleId && schedules.length >= 8) {
      const message = "Bạn chỉ được lưu tối đa 8 lịch học.";
      setScheduleError(message);
      showAppToast({ title: "Đã đạt giới hạn lịch", message, variant: "warning" });
      return;
    }

    // Check duplication (same date and same start/end times)
    const isDuplicate = schedules.some((s) => {
      if (editingScheduleId && s.id === editingScheduleId) return false;
      return (
        s.study_date === studyDate &&
        s.start_time.slice(0, 5) === startTime &&
        s.end_time.slice(0, 5) === endTime
      );
    });

    if (isDuplicate) {
      const message = "Lịch học này đã tồn tại.";
      setScheduleError(message);
      showAppToast({ title: "Lịch học bị trùng", message, variant: "warning" });
      return;
    }

    const schedPayload = {
      title: title.trim() || "Lịch học của tôi",
      study_date: studyDate,
      start_time: startTime,
      end_time: endTime,
      vehicle_type: normalizeVehicleType(selectedVehicle),
      location_id: locationId,
      repeat_type: "none",
      repeat_days: null,
      note: note.trim() || null,
      is_active: true,
    };

    try {
      if (editingScheduleId) {
        await editSchedule(editingScheduleId, schedPayload);
        // Retain selection
        setSelectedScheduleId(editingScheduleId);
        showSuccessToast("Đã cập nhật lịch học", "Thay đổi lịch học đã được lưu.");
      } else {
        await addSchedule(schedPayload);
        showSuccessToast("Đã lưu lịch học", "Trợ lý sẽ dùng lịch này để phân tích thời tiết đi học.");
      }
      cancelEdit();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Đã xảy ra lỗi khi lưu lịch học.";
      setScheduleError(message);
      showErrorToast("Không thể lưu lịch học", message);
    }
  }, [
    editingScheduleId,
    schedules,
    studyDate,
    startTime,
    endTime,
    title,
    selectedVehicle,
    locationId,
    note,
    scheduleError,
    addSchedule,
    editSchedule,
    cancelEdit,
  ]);

  return {
    advice,
    applyStudyPreset,
    changeStudyDate,
    changeStudyDateMode,
    changeTimeRange,
    changeVehicle: setSelectedVehicle,
    endTime,
    error,
    hasSavedSchedule: schedules.length > 0,
    loading,
    saveSchedule: handleSaveSchedule,
    scheduleError,
    selectedVehicle,
    setEndTime,
    setStartTime,
    startTime,
    studyDate,
    studyDateMode,
    lastFetchedAt,
    refresh,
    schedule: activeSchedule,
    upcomingAdvice,
    upcomingSchedule,


    // Multi-schedule enhancements
    selectedScheduleId,
    setSelectedScheduleId,
    editingScheduleId,
    handleEditSchedule,
    cancelEdit,
    handleDeleteSchedule,
    title,
    setTitle,
    note,
    setNote,
    locationId,
    setLocationId,
  };
}

function buildAdviceRequest(
  source: LocationQuery,
  schedule: { study_date: string; start_time: string; end_time: string; vehicle_type: VehicleType }
): StudentAdviceRequest {
  const mappedVehicle = normalizeVehicleType(schedule.vehicle_type);


  if (source.mode === "current" || source.mode === "confirmed") {
    return {
      latitude: source.latitude,
      longitude: source.longitude,
      ...(source.mode === "current" && typeof source.accuracy === "number"
        ? { accuracy_meters: source.accuracy }
        : {}),
      study_date: schedule.study_date,
      start_time: schedule.start_time,
      end_time: schedule.end_time,
      vehicle_type: mappedVehicle,
    };
  }

  return {
    city: source.city,
    study_date: schedule.study_date,
    start_time: schedule.start_time,
    end_time: schedule.end_time,
    vehicle_type: mappedVehicle,
  };
}

function resolveScheduleLocationQuery(
  schedule: StudyScheduleResponse | null,
  savedLocations: UserLocationResponse[],
  fallbackSource: LocationQuery | null,
): LocationQuery | null {
  if (!schedule) return null;

  if (schedule.location_id) {
    const loc = savedLocations.find((savedLocation) => savedLocation.id === schedule.location_id);
    if (loc) {
      return {
        mode: "confirmed",
        latitude: loc.latitude,
        longitude: loc.longitude,
        displayName: loc.display_name,
        shortDisplayName: loc.short_display_name ?? undefined,
        administrativeLevels: loc.administrative_levels ?? undefined,
      };
    }
  }

  return fallbackSource;
}

function getLocationQueryKey(source: LocationQuery | null): string {
  if (!source) return "none";
  if (source.mode === "current" || source.mode === "confirmed") {
    return `${source.mode}:${source.latitude}:${source.longitude}`;
  }
  return `city:${source.city}`;
}

function mapScheduleForAdvice(schedule: StudyScheduleResponse): {
  study_date: string;
  start_time: string;
  end_time: string;
  vehicle_type: VehicleType;
} {
  return {
    study_date: schedule.study_date || formatInputDate(addDays(new Date(), 1)),
    start_time: schedule.start_time.slice(0, 5),
    end_time: schedule.end_time.slice(0, 5),
    vehicle_type: normalizeVehicleType(schedule.vehicle_type),
  };
}

function getScheduleAdviceKey(schedule: StudyScheduleResponse | null): string {
  if (!schedule) return "none";
  return [
    schedule.id,
    schedule.study_date ?? "",
    schedule.start_time,
    schedule.end_time,
    schedule.vehicle_type,
    schedule.location_id ?? "",
  ].join(":");
}

function findNextRelevantSchedule(schedules: StudyScheduleResponse[], now: Date): StudyScheduleResponse | null {
  const candidates = schedules
    .map((schedule) => getNextScheduleOccurrence(schedule, now))
    .filter((candidate): candidate is { schedule: StudyScheduleResponse; startAt: Date; endAt: Date } => Boolean(candidate))
    .sort((a, b) => {
      const startDiff = a.startAt.getTime() - b.startAt.getTime();
      if (startDiff !== 0) return startDiff;
      return a.endAt.getTime() - b.endAt.getTime();
    });

  return candidates[0]?.schedule ?? null;
}

function getNextScheduleOccurrence(
  schedule: StudyScheduleResponse,
  now: Date,
): { schedule: StudyScheduleResponse; startAt: Date; endAt: Date } | null {
  if (!schedule.is_active) return null;

  if (schedule.repeat_type === "weekly" && schedule.repeat_days?.length) {
    const weekdayMap: Record<string, number> = {
      sun: 0,
      mon: 1,
      tue: 2,
      wed: 3,
      thu: 4,
      fri: 5,
      sat: 6,
    };
    const repeatWeekdays = new Set(schedule.repeat_days.map((day) => weekdayMap[day.toLowerCase()]));

    for (let offset = 0; offset <= 7; offset += 1) {
      const date = addDays(now, offset);
      if (!repeatWeekdays.has(date.getDay())) continue;

      const occurrence = buildOccurrence(schedule, formatInputDate(date), now);
      if (occurrence) return occurrence;
    }

    return null;
  }

  if (!schedule.study_date) return null;
  return buildOccurrence(schedule, schedule.study_date, now);
}

function buildOccurrence(
  schedule: StudyScheduleResponse,
  studyDate: string,
  now: Date,
): { schedule: StudyScheduleResponse; startAt: Date; endAt: Date } | null {
  const startAt = combineLocalDateAndTime(studyDate, schedule.start_time);
  const endAt = combineLocalDateAndTime(studyDate, schedule.end_time);
  if (!startAt || !endAt || endAt <= startAt) return null;
  if (endAt <= now) return null;

  return {
    schedule: schedule.study_date === studyDate ? schedule : { ...schedule, study_date: studyDate },
    startAt,
    endAt,
  };
}

function combineLocalDateAndTime(dateStr: string, timeStr: string): Date | null {
  const [year, month, day] = dateStr.split("-").map(Number);
  const [hour, minute] = timeStr.slice(0, 5).split(":").map(Number);
  if (![year, month, day, hour, minute].every(Number.isFinite)) return null;
  return new Date(year, month - 1, day, hour, minute, 0, 0);
}

function isDateInRange(dateStr: string): boolean {
  try {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const maxDate = new Date(today);
    maxDate.setDate(today.getDate() + 8);

    const [year, month, day] = dateStr.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    date.setHours(0, 0, 0, 0);

    return date >= today && date <= maxDate;
  } catch {
    return false;
  }
}

function resolveDateMode(value: string): StudyDateMode {
  if (value === formatInputDate(new Date())) return "today";
  if (value === formatInputDate(addDays(new Date(), 1))) return "tomorrow";
  return "custom";
}

function addDays(date: Date, days: number): Date {
  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + days);
  return nextDate;
}

function formatInputDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
