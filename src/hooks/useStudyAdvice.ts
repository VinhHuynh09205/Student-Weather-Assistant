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
} from "../types/weather";
import { useAutoRefresh } from "./useAutoRefresh";
import { useAuth } from "../context/AuthContext";

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

  const activeLocationQuery = useMemo<LocationQuery | null>(() => {
    if (!activeSchedule) return null;
    if (activeSchedule.location_id) {
      const loc = savedLocations.find((l) => l.id === activeSchedule.location_id);
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
    return source;
  }, [activeSchedule, savedLocations, source]);

  const sourceKey = useMemo(() => {
    if (!activeLocationQuery) return "none";
    if (activeLocationQuery.mode === "current" || activeLocationQuery.mode === "confirmed") {
      return `${activeLocationQuery.mode}:${activeLocationQuery.latitude}:${activeLocationQuery.longitude}`;
    }
    return `city:${activeLocationQuery.city}`;
  }, [activeLocationQuery]);

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

    const mappedSchedule = {
      study_date: activeSchedule.study_date || formatInputDate(addDays(new Date(), 1)),
      start_time: activeSchedule.start_time.slice(0, 5),
      end_time: activeSchedule.end_time.slice(0, 5),
      vehicle_type: activeSchedule.vehicle_type,
    };

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

  useAutoRefresh(
    lastFetchedAt,
    10 * 60 * 1000,
    refresh,
    Boolean(activeSchedule) && Boolean(activeLocationQuery) && !loading && settings.auto_refresh_enabled
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
    setSelectedVehicle(sched.vehicle_type);
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
    await removeSchedule(id);
  }, [schedules, selectedScheduleId, editingScheduleId, removeSchedule, cancelEdit]);

  const handleSaveSchedule = useCallback(async () => {
    if (scheduleError) return;

    // Enforce 8 schedule limit when adding new
    if (!editingScheduleId && schedules.length >= 8) {
      setScheduleError("Bạn chỉ được lưu tối đa 8 lịch học.");
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
      setScheduleError("Lịch học này đã tồn tại.");
      return;
    }

    const schedPayload = {
      title: title.trim() || "Lịch học của tôi",
      study_date: studyDate,
      start_time: startTime,
      end_time: endTime,
      vehicle_type: selectedVehicle,
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
      } else {
        await addSchedule(schedPayload);
      }
      cancelEdit();
    } catch (err) {
      setScheduleError(err instanceof Error ? err.message : "Đã xảy ra lỗi khi lưu lịch học.");
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
  const vehicleStr = schedule.vehicle_type as string;
  const mappedVehicle = (vehicleStr === "walk" ? "walking" : vehicleStr) as VehicleType;


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
