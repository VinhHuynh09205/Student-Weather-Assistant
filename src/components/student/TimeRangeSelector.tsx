import { useState } from "react";
import { Clock } from "lucide-react";
import type { StudyShift } from "../../types/weather";
import { TimePickerPopover } from "./TimePickerPopover";

type TimeRangeSelectorProps = {
  startTime: string;
  endTime: string;
  onStartTimeChange: (value: string) => void;
  onEndTimeChange: (value: string) => void;
  onPreset: (preset: StudyShift) => void;
};

const presets: Array<{ id: StudyShift; label: string; range: string; startTime: string; endTime: string }> = [
  { id: "morning", label: "Ca sáng", range: "07:00 - 11:00", startTime: "07:00", endTime: "11:00" },
  { id: "afternoon", label: "Ca chiều", range: "13:00 - 17:00", startTime: "13:00", endTime: "17:00" },
  { id: "evening", label: "Ca tối", range: "18:00 - 21:00", startTime: "18:00", endTime: "21:00" },
];

export function TimeRangeSelector({
  endTime,
  onEndTimeChange,
  onPreset,
  onStartTimeChange,
  startTime,
}: TimeRangeSelectorProps) {
  const [activePicker, setActivePicker] = useState<"start" | "end" | null>(null);

  const isPresetActive = (presetStartTime: string, presetEndTime: string) => {
    return startTime === presetStartTime && endTime === presetEndTime;
  };

  const handlePresetClick = (presetId: StudyShift) => {
    onPreset(presetId);
    setActivePicker(null);
  };

  return (
    <div className="time-range-selector">
      <span className="field-label">Giờ học</span>
      <div className="time-input-grid">
        <div className="field-control time-input-wrapper" style={{ position: "relative" }}>
          <span className="time-sub-label">Bắt đầu</span>
          <button
            type="button"
            className={`time-select-btn ${activePicker === "start" ? "active" : ""}`}
            onClick={() => setActivePicker(activePicker === "start" ? null : "start")}
          >
            <Clock size={16} className="time-icon" />
            <span>{startTime}</span>
          </button>
          {activePicker === "start" && (
            <TimePickerPopover
              value={startTime}
              onChange={onStartTimeChange}
              onClose={() => setActivePicker(null)}
              align="left"
            />
          )}
        </div>
        <div className="field-control time-input-wrapper" style={{ position: "relative" }}>
          <span className="time-sub-label">Kết thúc</span>
          <button
            type="button"
            className={`time-select-btn ${activePicker === "end" ? "active" : ""}`}
            onClick={() => setActivePicker(activePicker === "end" ? null : "end")}
          >
            <Clock size={16} className="time-icon" />
            <span>{endTime}</span>
          </button>
          {activePicker === "end" && (
            <TimePickerPopover
              value={endTime}
              onChange={onEndTimeChange}
              onClose={() => setActivePicker(null)}
              align="right"
            />
          )}
        </div>
      </div>

      <span className="field-label preset-label">Phím tắt ca học</span>
      <div className="schedule-presets">
        {presets.map((preset) => (
          <button
            className={isPresetActive(preset.startTime, preset.endTime) ? "selected" : ""}
            key={preset.id}
            type="button"
            onClick={() => handlePresetClick(preset.id)}
          >
            <strong>{preset.label}</strong>
            <span>{preset.range}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
