import { Trash2, BookOpen, Edit2 } from "lucide-react";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { AdviceSummaryCard } from "../components/student/AdviceSummaryCard";
import { RecommendationCard } from "../components/student/RecommendationCard";
import { StudentScoreCard } from "../components/student/StudentScoreCard";
import { StudyTimelineCard } from "../components/student/StudyTimelineCard";
import { WarningCard } from "../components/student/WarningCard";
import { StudyScheduleForm } from "../components/study/StudyScheduleForm";
import { StudyEmptyState } from "../components/study/StudyEmptyState";
import type {
  CurrentWeatherResponse,
  StudentAdviceResponse,
  StudyDateMode,
  StudyShift,
  VehicleType,
  StudyScheduleResponse,
} from "../types/weather";
import { formatPercent, formatTemperature, formatWind, formatScheduleRange, getVehicleLabel } from "../utils/formatters";
import { useAuth } from "../context/AuthContext";

type StudyAssistantPageProps = {
  advice: StudentAdviceResponse | null;
  adviceError: string | null;
  currentWeather: CurrentWeatherResponse | null;
  dateMode: StudyDateMode;
  endTime: string;
  isLoading: boolean;
  scheduleError: string | null;
  selectedVehicle: VehicleType;
  startTime: string;
  studyDate: string;
  onDateChange: (date: string) => void;
  onDateModeChange: (mode: StudyDateMode) => void;
  onEndTimeChange: (time: string) => void;
  onPreset: (preset: StudyShift) => void;
  onSaveSchedule: () => void;
  onStartTimeChange: (time: string) => void;
  onVehicleChange: (vehicle: VehicleType) => void;

  // Multi-schedule CRUD props
  title: string;
  onTitleChange: (val: string) => void;
  note: string;
  onNoteChange: (val: string) => void;
  locationId: string | null;
  onLocationIdChange: (val: string | null) => void;

  selectedScheduleId: string | null;
  onSelectScheduleId: (id: string | null) => void;
  editingScheduleId: string | null;
  onEditSchedule: (sched: StudyScheduleResponse) => void;
  onCancelEdit: () => void;
  onDeleteSchedule: (id: string) => void;
};

export function StudyAssistantPage({
  advice,
  adviceError,
  currentWeather,
  dateMode,
  endTime,
  isLoading,
  onDateChange,
  onDateModeChange,
  onEndTimeChange,
  onPreset,
  onSaveSchedule,
  onStartTimeChange,
  onVehicleChange,
  scheduleError,
  selectedVehicle,
  startTime,
  studyDate,

  title,
  onTitleChange,
  note,
  onNoteChange,
  locationId,
  onLocationIdChange,

  selectedScheduleId,
  onSelectScheduleId,
  editingScheduleId,
  onEditSchedule,
  onCancelEdit,
  onDeleteSchedule,
}: StudyAssistantPageProps) {
  const { currentUser, schedules, savedLocations } = useAuth();

  return (
    <section className="study-assistant-page">
      {!currentUser && (
        <div className="glass-card auth-reminder-banner" style={{ marginBottom: "1.25rem" }}>
          <h3>🔐 Đăng nhập để lưu lịch học lâu dài</h3>
          <p>
            Bạn đang lưu lịch học tạm ở trình duyệt này. Hãy đăng nhập để đồng bộ lịch học, thêm ghi chú môn học và nhận cảnh báo qua email (tài khoản Google).
          </p>
        </div>
      )}

      <div className="study-assistant-grid">
        <div className="study-form-column">
          <StudyScheduleForm
            title={title}
            onTitleChange={onTitleChange}
            note={note}
            onNoteChange={onNoteChange}
            locationId={locationId}
            onLocationIdChange={onLocationIdChange}
            dateMode={dateMode}
            endTime={endTime}
            error={scheduleError}
            selectedVehicle={selectedVehicle}
            startTime={startTime}
            studyDate={studyDate}
            onDateChange={onDateChange}
            onDateModeChange={onDateModeChange}
            onEndTimeChange={onEndTimeChange}
            onPreset={onPreset}
            onSave={onSaveSchedule}
            onStartTimeChange={onStartTimeChange}
            onVehicleChange={onVehicleChange}
            editingScheduleId={editingScheduleId}
            onCancelEdit={onCancelEdit}
          />

          {/* List of saved schedules for both logged in users and guests */}
          {schedules.length > 0 && (
            <div className="glass-card saved-schedules-assistant-card" style={{ marginTop: "1rem" }}>
              <h2>
                <BookOpen size={20} /> Lịch học của bạn ({schedules.length}/8)
              </h2>
              <div className="assistant-schedules-list" style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {schedules.map((sched) => {
                  const isSelected = sched.id === selectedScheduleId;
                  const schedLoc = savedLocations.find(l => l.id === sched.location_id);
                  const locationLabel = schedLoc ? schedLoc.label : "Vị trí mặc định";

                  return (
                    <div
                      key={sched.id}
                      className={`assistant-schedule-item ${isSelected ? "active" : ""}`}
                      onClick={() => onSelectScheduleId(sched.id)}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "0.75rem 1rem",
                        background: isSelected ? "rgba(139, 92, 246, 0.15)" : "rgba(255, 255, 255, 0.05)",
                        border: isSelected ? "1px solid rgba(139, 92, 246, 0.45)" : "1px solid rgba(255, 255, 255, 0.08)",
                        borderRadius: "0.8rem",
                        cursor: "pointer",
                        transition: "all 0.2s",
                      }}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.15rem", flex: 1, minWidth: 0 }}>
                        <strong style={{ fontSize: "0.85rem", color: "#ffffff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {sched.title}
                        </strong>
                        <span style={{ fontSize: "0.75rem", color: "rgba(255, 255, 255, 0.6)" }}>
                          {formatScheduleRange(sched.study_date || undefined, sched.start_time, sched.end_time)} · {getVehicleLabel(sched.vehicle_type)}
                        </span>
                        <span style={{ fontSize: "0.7rem", color: "rgba(255, 255, 255, 0.4)" }}>
                          📍 {locationLabel}
                        </span>
                      </div>
                      <div className="schedule-item-actions" style={{ display: "flex", gap: "0.35rem" }} onClick={(e) => e.stopPropagation()}>
                        <button
                          className="btn-icon-secondary"
                          type="button"
                          title="Sửa lịch học"
                          onClick={() => onEditSchedule(sched)}
                          style={{ padding: "0.35rem", borderRadius: "6px" }}
                        >
                          <Edit2 size={13} />
                        </button>
                        <button
                          className="btn-icon-danger"
                          type="button"
                          title="Xóa lịch học"
                          onClick={() => onDeleteSchedule(sched.id)}
                          style={{ padding: "0.35rem", borderRadius: "6px" }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="study-results-stack">
          {isLoading ? <LoadingState message="Đang phân tích thời tiết theo lịch học..." /> : null}
          {adviceError ? <ErrorState message={adviceError} onRetry={onSaveSchedule} /> : null}
          {advice ? (
            <>
              <AdviceSummaryCard
                advice={advice}
                endTime={endTime}
                selectedVehicle={selectedVehicle}
                startTime={startTime}
                studyDate={studyDate}
              />
              <StudentScoreCard advice={advice} compact />
              <WarningCard advice={advice} />
              <StudyTimelineCard advice={advice} />
              <RecommendationCard advice={advice} />
              <StudyWeatherReasonCard advice={advice} currentWeather={currentWeather} />
            </>
          ) : (
            !isLoading && !adviceError && <StudyEmptyState />
          )}
        </div>
      </div>
    </section>
  );
}

function StudyWeatherReasonCard({
  advice,
  currentWeather,
}: {
  advice: StudentAdviceResponse | null;
  currentWeather: CurrentWeatherResponse | null;
}) {
  const metrics = advice?.metrics;
  const current = currentWeather?.current;
  const rainProbability =
    typeof metrics?.max_precipitation_probability_percent === "number"
      ? metrics.max_precipitation_probability_percent
      : undefined;

  return (
    <section className="glass-card reason-card">
      <h2>Lý do gợi ý này</h2>
      <div className="reason-grid">
        <article>
          <span>🌧️</span>
          <strong>{formatPercent(rainProbability)}</strong>
          <small>Khả năng mưa cao nhất</small>
        </article>
        <article>
          <span>🌡️</span>
          <strong>{formatTemperature(metrics?.max_apparent_temperature_c ?? current?.apparent_temperature_c)}</strong>
          <small>Cảm giác nhiệt</small>
        </article>
        <article>
          <span>🌬️</span>
          <strong>{formatWind(metrics?.max_wind_speed_kmh ?? current?.wind_speed_kmh)}</strong>
          <small>Tốc độ gió</small>
        </article>
      </div>
    </section>
  );
}
