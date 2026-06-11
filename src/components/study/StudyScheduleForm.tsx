import { Save, FileText, X } from "lucide-react";
import type { StudyDateMode, StudyShift, VehicleType } from "../../types/weather";
import { DateSelector } from "../student/DateSelector";
import { TimeRangeSelector } from "../student/TimeRangeSelector";
import { VehicleSelector } from "../student/VehicleSelector";
import { CustomSelect } from "../common/CustomSelect";
import { useAuth } from "../../context/AuthContext";
import { Card } from "../common/Card";

type StudyScheduleFormProps = {
  title: string;
  onTitleChange: (val: string) => void;
  note: string;
  onNoteChange: (val: string) => void;
  locationId: string | null;
  onLocationIdChange: (val: string | null) => void;
  
  dateMode: StudyDateMode;
  endTime: string;
  error: string | null;
  onDateChange: (date: string) => void;
  onDateModeChange: (mode: StudyDateMode) => void;
  onEndTimeChange: (time: string) => void;
  onPreset: (preset: StudyShift) => void;
  onSave: () => void;
  onStartTimeChange: (time: string) => void;
  onVehicleChange: (vehicle: VehicleType) => void;
  selectedVehicle: VehicleType;
  startTime: string;
  studyDate: string;
  
  editingScheduleId: string | null;
  onCancelEdit: () => void;
};

export function StudyScheduleForm({
  title,
  onTitleChange,
  note,
  onNoteChange,
  locationId,
  onLocationIdChange,
  
  dateMode,
  endTime,
  error,
  onDateChange,
  onDateModeChange,
  onEndTimeChange,
  onPreset,
  onSave,
  onStartTimeChange,
  onVehicleChange,
  selectedVehicle,
  startTime,
  studyDate,
  
  editingScheduleId,
  onCancelEdit,
}: StudyScheduleFormProps) {
  const { savedLocations } = useAuth();

  const locationOptions = [
    { value: "default", label: "📍 Vị trí hiện tại / Mặc định" },
    ...savedLocations.map((loc) => ({
      value: loc.id,
      label: `📍 ${loc.label} (${loc.display_name.slice(0, 20)}...)`,
    })),
  ];

  const handleLocationChange = (val: string) => {
    if (val === "default") {
      onLocationIdChange(null);
    } else {
      onLocationIdChange(val);
    }
  };

  return (
    <Card className="study-schedule-card" title={editingScheduleId ? "Sửa lịch học" : "Thêm lịch học mới"}>
      {editingScheduleId && (
        <div className="editing-banner animate-slide-up">
          <span>Đang chỉnh sửa lịch học</span>
          <button type="button" onClick={onCancelEdit} className="cancel-edit-btn">
            <X size={14} />
            <span>Hủy sửa</span>
          </button>
        </div>
      )}

      <form className="schedule-form" onSubmit={(e) => { e.preventDefault(); onSave(); }}>
        {/* Title / Môn học */}
        <div className="form-group">
          <label className="field-label">Tên lịch học / Môn học</label>
          <div className="input-group-with-icon" style={{ background: "rgba(255,255,255,0.05)", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.12)" }}>
            <FileText size={18} className="input-field-icon" style={{ left: "12px", color: "rgba(255,255,255,0.4)" }} />
            <input
              type="text"
              placeholder="Ví dụ: Toán Giải Tích 1, Lập trình Web..."
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              className="auth-input-field"
              style={{ paddingLeft: "42px", height: "45px" }}
            />
          </div>
        </div>

        {/* Date Selector */}
        <DateSelector
          mode={dateMode}
          value={studyDate}
          onDateChange={onDateChange}
          onModeChange={onDateModeChange}
        />

        {/* Time Selector */}
        <TimeRangeSelector
          endTime={endTime}
          startTime={startTime}
          onEndTimeChange={onEndTimeChange}
          onPreset={onPreset}
          onStartTimeChange={onStartTimeChange}
        />

        {/* Location Selector */}
        <div className="form-group">
          <label className="field-label">Địa điểm học</label>
          <CustomSelect
            value={locationId || "default"}
            onChange={handleLocationChange}
            options={locationOptions}
          />
        </div>

        {/* Vehicle Selector */}
        <div className="schedule-vehicle-block">
          <span className="field-label">Phương tiện di chuyển</span>
          <VehicleSelector framed={false} selectedVehicle={selectedVehicle} onChange={onVehicleChange} />
        </div>

        {/* Notes */}
        <div className="form-group">
          <label className="field-label">Ghi chú (Tùy chọn)</label>
          <textarea
            placeholder="Nhập ghi chú như phòng học, kiểm tra..."
            value={note}
            onChange={(e) => onNoteChange(e.target.value)}
            className="modal-text-input"
            style={{ minHeight: "80px", resize: "vertical" }}
          />
        </div>

        {error && <p className="inline-error" style={{ marginTop: "0.5rem" }}>{error}</p>}

        <button
          className="save-schedule-button btn-primary"
          type="submit"
          disabled={Boolean(error)}
          style={{ marginTop: "1rem", width: "100%", height: "48px", borderRadius: "10px" }}
        >
          <Save size={18} />
          <span>{editingScheduleId ? "Cập nhật lịch học" : "Lưu lịch học"}</span>
        </button>
      </form>
    </Card>
  );
}
