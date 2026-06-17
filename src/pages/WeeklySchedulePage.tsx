import {
  AlertTriangle,
  CalendarClock,
  CalendarDays,
  CloudSun,
  ListChecks,
  Plus,
  RefreshCw,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import * as classScheduleApi from "../api/classScheduleApi";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { WeeklyForecastDetailModal } from "../components/classSchedule/WeeklyForecastDetailModal";
import { UpcomingForecastList } from "../components/classSchedule/UpcomingForecastList";
import { WeeklyScheduleCard } from "../components/classSchedule/WeeklyScheduleCard";
import { WeeklyScheduleForm } from "../components/classSchedule/WeeklyScheduleForm";
import { useAuth } from "../context/AuthContext";
import type { ClassScheduleForecast, WeeklyClassSchedule, WeeklyClassSchedulePayload } from "../types/classSchedule";
import type { CurrentWeatherResponse } from "../types/weather";
import { formatOccurrenceDateTime } from "../utils/classScheduleFormatters";
import { showErrorToast, showSuccessToast } from "../utils/toast";

type WeeklySchedulePageProps = {
  currentWeather: CurrentWeatherResponse | null;
  locationName: string;
  onOpenLogin: () => void;
};

type ScheduleTab = "weekly" | "upcoming";

export function WeeklySchedulePage({ currentWeather, locationName, onOpenLogin }: WeeklySchedulePageProps) {
  const { currentUser, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<ScheduleTab>("weekly");
  const [schedules, setSchedules] = useState<WeeklyClassSchedule[]>([]);
  const [upcomingForecasts, setUpcomingForecasts] = useState<ClassScheduleForecast[]>([]);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<WeeklyClassSchedule | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [busyScheduleId, setBusyScheduleId] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [detailTarget, setDetailTarget] = useState<{
    forecast?: ClassScheduleForecast;
    schedule: WeeklyClassSchedule;
  } | null>(null);
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scheduleListRef = useRef<HTMLDivElement>(null);

  const refreshData = useCallback(async (notify = false) => {
    if (!currentUser) {
      setSchedules([]);
      setUpcomingForecasts([]);
      setPageError(null);
      setForecastError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setPageError(null);
    setForecastError(null);
    try {
      const scheduleList = await classScheduleApi.getClassSchedules();
      setSchedules(scheduleList.filter((schedule) => schedule.is_active));
      if (notify) {
        showSuccessToast("Đã làm mới lịch học", "Dữ liệu lịch học và dự báo sắp tới đã được cập nhật.");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Không thể tải lịch học hằng tuần.";
      setPageError(message);
      if (notify) {
        showErrorToast("Không thể làm mới", message);
      }
      setLoading(false);
      return;
    }

    try {
      const forecastList = await classScheduleApi.getUpcomingForecasts(20);
      setUpcomingForecasts(forecastList);
      setForecastError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Không thể tải dự báo thời tiết cho lịch học.";
      setUpcomingForecasts([]);
      setForecastError(message);
      if (notify) {
        showErrorToast("Không thể tải dự báo", message);
      }
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  useEffect(() => {
    void refreshData();
  }, [refreshData]);

  useEffect(() => {
    return () => {
      if (flashTimerRef.current) window.clearTimeout(flashTimerRef.current);
    };
  }, []);

  const forecastByScheduleId = useMemo(() => {
    return new Map(upcomingForecasts.map((forecast) => [forecast.schedule.id, forecast]));
  }, [upcomingForecasts]);

  const activeCount = useMemo(() => schedules.filter((schedule) => schedule.is_active).length, [schedules]);
  const alertCount = useMemo(
    () => upcomingForecasts.filter((forecast) => forecast.risk_level !== "SAFE").length,
    [upcomingForecasts],
  );
  const nearestForecast = upcomingForecasts[0];

  const currentClassLocation = useMemo(() => {
    if (currentWeather) {
      return {
        name: currentWeather.display_name || currentWeather.location_name || locationName,
        latitude: currentWeather.latitude,
        longitude: currentWeather.longitude,
      };
    }
    if (locationName) return { name: locationName };
    return undefined;
  }, [currentWeather, locationName]);

  const openCreateForm = () => {
    setEditingSchedule(null);
    setMutationError(null);
    setIsFormOpen(true);
  };

  const openEditForm = (schedule: WeeklyClassSchedule) => {
    setEditingSchedule(schedule);
    setMutationError(null);
    setIsFormOpen(true);
  };

  const closeForm = () => {
    if (isSubmitting) return;
    setIsFormOpen(false);
    setEditingSchedule(null);
    setMutationError(null);
  };

  const handleRefreshClick = () => {
    void refreshData(true);
  };

  const handleViewScheduleList = () => {
    if (isSubmitting) return;
    setIsFormOpen(false);
    setEditingSchedule(null);
    setMutationError(null);
    setActiveTab("weekly");
    window.setTimeout(() => {
      scheduleListRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
  };

  const handleSubmit = async (payload: WeeklyClassSchedulePayload) => {
    setIsSubmitting(true);
    setMutationError(null);
    try {
      if (editingSchedule) {
        const savedSchedule = await classScheduleApi.updateClassSchedule(editingSchedule.id, payload);
        setSchedules((current) =>
          current.map((schedule) => (schedule.id === savedSchedule.id ? savedSchedule : schedule)),
        );
        showFlash("Đã cập nhật lịch học.", "Đã lưu thay đổi");
        setIsFormOpen(false);
        setEditingSchedule(null);
      } else {
        const savedSchedule = await classScheduleApi.createClassSchedule(payload);
        setSchedules((current) =>
          current.some((schedule) => schedule.id === savedSchedule.id) ? current : [...current, savedSchedule],
        );
        showFlash("Đã tạo lịch học mới. Bạn có thể tạo tiếp ngay.", "Đã thêm lịch học");
      }
      await refreshData();
      setActiveTab("weekly");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Không thể lưu lịch học.";
      setMutationError(message);
      showErrorToast("Không thể lưu lịch học", message);
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleActive = async (schedule: WeeklyClassSchedule) => {
    setBusyScheduleId(schedule.id);
    setPageError(null);
    try {
      await classScheduleApi.updateClassSchedule(schedule.id, { is_active: !schedule.is_active });
      showFlash(
        schedule.is_active ? "Đã tắt theo dõi lịch học." : "Đã bật lại lịch học.",
        schedule.is_active ? "Đã tắt lịch học" : "Đã bật lịch học",
      );
      await refreshData();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Không thể đổi trạng thái lịch học.";
      setPageError(message);
      showErrorToast("Không thể đổi trạng thái", message);
    } finally {
      setBusyScheduleId(null);
    }
  };

  const handleDelete = async (schedule: WeeklyClassSchedule) => {
    const confirmed = window.confirm(`Xóa lịch học "${schedule.subject_name}"? Lịch sẽ không còn hiển thị trong danh sách chính.`);
    if (!confirmed) return;

    setBusyScheduleId(schedule.id);
    setPageError(null);
    try {
      const deleteResult = await classScheduleApi.deleteClassSchedule(schedule.id);
      setSchedules((current) => current.filter((item) => item.id !== schedule.id));
      setUpcomingForecasts((current) => current.filter((forecast) => forecast.schedule.id !== schedule.id));
      showFlash(deleteResult.message || "Đã xóa lịch học", "Đã xóa lịch học");
      await refreshData();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Không thể xóa lịch học.";
      setPageError(message);
      showErrorToast("Không thể xóa lịch học", message);
    } finally {
      setBusyScheduleId(null);
    }
  };

  const handleViewDetails = (forecast: ClassScheduleForecast | undefined, schedule: WeeklyClassSchedule) => {
    setDetailTarget({ forecast, schedule });
  };

  const showFlash = (message: string, toastTitle = "Đã cập nhật") => {
    setFlashMessage(message);
    showSuccessToast(toastTitle, message);
    if (flashTimerRef.current) window.clearTimeout(flashTimerRef.current);
    flashTimerRef.current = window.setTimeout(() => setFlashMessage(null), 3600);
  };

  if (authLoading) {
    return <LoadingState message="Đang kiểm tra phiên đăng nhập..." />;
  }

  if (!currentUser) {
    return (
      <section className="weekly-schedule-page">
        <div className="weekly-login-card glass-card">
          <div className="weekly-login-icon">
            <CalendarDays size={36} aria-hidden="true" />
          </div>
          <div>
            <span>Lịch học hằng tuần</span>
            <h2>Đăng nhập để đồng bộ lịch học và xem dự báo theo từng buổi</h2>
            <p>
              Chức năng này lưu lịch theo tài khoản để backend có thể tính buổi học kế tiếp,
              mức rủi ro mưa/dông và lời nhắc trước giờ học.
            </p>
          </div>
          <button className="class-primary-button" type="button" onClick={onOpenLogin}>
            Đăng nhập
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="weekly-schedule-page">
      <div className="weekly-page-toolbar glass-card">
        <div>
          <span className="weekly-page-kicker">Lịch học thời tiết</span>
          <h2>Lịch học & Dự báo thời tiết</h2>
          <p>Theo dõi thời tiết cho các buổi học hằng tuần của bạn.</p>
        </div>
        <div className="weekly-toolbar-actions">
          <button className="class-secondary-button" type="button" onClick={handleRefreshClick} disabled={loading}>
            <RefreshCw size={17} aria-hidden="true" />
            Làm mới
          </button>
          <button className="class-primary-button" type="button" onClick={openCreateForm}>
            <Plus size={18} aria-hidden="true" />
            Thêm lịch học
          </button>
        </div>
      </div>

      {flashMessage ? <div className="weekly-flash-message">{flashMessage}</div> : null}

      <div className="weekly-summary-grid">
        <SummaryCard
          icon={<CalendarClock size={22} aria-hidden="true" />}
          label="Buổi học gần nhất"
          value={nearestForecast ? nearestForecast.schedule.subject_name : "Chưa có"}
          detail={
            nearestForecast
              ? formatOccurrenceDateTime(nearestForecast.next_occurrence_datetime)
              : "Thêm lịch để hệ thống theo dõi."
          }
        />
        <SummaryCard
          icon={<ListChecks size={22} aria-hidden="true" />}
          label="Lịch đang hoạt động"
          value={String(activeCount)}
          detail={`${schedules.length} lịch đã tạo`}
        />
        <SummaryCard
          icon={<AlertTriangle size={22} aria-hidden="true" />}
          label="Cảnh báo cần chú ý"
          value={String(alertCount)}
          detail="Tính trên các buổi học sắp tới"
          tone={alertCount > 0 ? "warning" : "safe"}
        />
      </div>

      {pageError ? <ErrorState message={pageError} onRetry={refreshData} /> : null}
      {forecastError && !pageError ? (
        <div className="weekly-forecast-warning" role="status">
          <AlertTriangle size={17} aria-hidden="true" />
          <span>{forecastError}</span>
        </div>
      ) : null}

      <div className="weekly-tabs" role="tablist" aria-label="Lịch học và dự báo">
        <button
          className={activeTab === "weekly" ? "selected" : ""}
          type="button"
          role="tab"
          aria-selected={activeTab === "weekly"}
          onClick={() => setActiveTab("weekly")}
        >
          Lịch hằng tuần
        </button>
        <button
          className={activeTab === "upcoming" ? "selected" : ""}
          type="button"
          role="tab"
          aria-selected={activeTab === "upcoming"}
          onClick={() => setActiveTab("upcoming")}
        >
          Dự báo sắp tới
        </button>
      </div>

      {loading && schedules.length === 0 ? <LoadingState message="Đang tải lịch học hằng tuần..." /> : null}

      <div className="weekly-tab-content" ref={scheduleListRef}>
        {activeTab === "weekly" ? (
          schedules.length > 0 ? (
            <div className="weekly-schedule-grid">
              {schedules.map((schedule) => (
                <WeeklyScheduleCard
                  key={schedule.id}
                  schedule={schedule}
                  forecast={forecastByScheduleId.get(schedule.id)}
                  isBusy={busyScheduleId === schedule.id}
                  onDelete={handleDelete}
                  onEdit={openEditForm}
                  onToggleActive={handleToggleActive}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          ) : (
            !loading && <WeeklyEmptyState onCreate={openCreateForm} />
          )
        ) : (
          <UpcomingForecastList forecasts={upcomingForecasts} />
        )}
      </div>

      {isFormOpen ? (
        <div className="class-modal-overlay" role="dialog" aria-modal="true" aria-label="Tạo hoặc sửa lịch học">
          <div className="class-modal-panel">
            <div className="class-modal-header">
              <div>
                <span>{editingSchedule ? "Chỉnh sửa lịch học" : "Lịch học hằng tuần"}</span>
                <h2>{editingSchedule ? "Cập nhật lịch học" : "Thêm lịch học mới"}</h2>
              </div>
              <button type="button" onClick={closeForm} aria-label="Đóng form">
                <X size={18} aria-hidden="true" />
              </button>
            </div>
            <WeeklyScheduleForm
              schedule={editingSchedule}
              apiError={mutationError}
              currentLocation={currentClassLocation}
              isSubmitting={isSubmitting}
              onCancel={closeForm}
              onViewScheduleList={handleViewScheduleList}
              onSubmit={handleSubmit}
            />
          </div>
        </div>
      ) : null}

      {detailTarget ? (
        <WeeklyForecastDetailModal
          forecast={detailTarget.forecast}
          schedule={detailTarget.schedule}
          onClose={() => setDetailTarget(null)}
        />
      ) : null}
    </section>
  );
}

function SummaryCard({
  detail,
  icon,
  label,
  tone,
  value,
}: {
  detail: string;
  icon: ReactNode;
  label: string;
  tone?: "safe" | "warning";
  value: string;
}) {
  return (
    <article className={`weekly-summary-card ${tone ? `tone-${tone}` : ""}`}>
      <span className="weekly-summary-icon">{icon}</span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
    </article>
  );
}

function WeeklyEmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="weekly-empty-state glass-card">
      <CloudSun size={42} aria-hidden="true" />
      <h3>Chưa có lịch học hằng tuần</h3>
      <p>Thêm môn học, giờ học và địa điểm để hệ thống tự tìm buổi học kế tiếp và cảnh báo thời tiết.</p>
      <button className="class-primary-button" type="button" onClick={onCreate}>
        <Plus size={18} aria-hidden="true" />
        Thêm lịch đầu tiên
      </button>
    </div>
  );
}
