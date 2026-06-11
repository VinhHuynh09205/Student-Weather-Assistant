import type { StudyDateMode, StudyShift, VehicleType } from "../../types/weather";
import { Card } from "../common/Card";
import { DateSelector } from "./DateSelector";
import { TimeRangeSelector } from "./TimeRangeSelector";
import { VehicleSelector } from "./VehicleSelector";

type StudyScheduleCardProps = {
  dateMode: StudyDateMode;
  studyDate: string;
  startTime: string;
  endTime: string;
  selectedVehicle: VehicleType;
  error?: string | null;
  onDateModeChange: (mode: StudyDateMode) => void;
  onDateChange: (value: string) => void;
  onStartTimeChange: (value: string) => void;
  onEndTimeChange: (value: string) => void;
  onPreset: (preset: StudyShift) => void;
  onVehicleChange: (vehicle: VehicleType) => void;
};

export function StudyScheduleCard({
  dateMode,
  endTime,
  error,
  onDateChange,
  onDateModeChange,
  onEndTimeChange,
  onPreset,
  onStartTimeChange,
  onVehicleChange,
  selectedVehicle,
  startTime,
  studyDate,
}: StudyScheduleCardProps) {
  return (
    <Card className="study-schedule-card" title="Lịch học của bạn">
      <div className="schedule-form">
        <DateSelector mode={dateMode} value={studyDate} onDateChange={onDateChange} onModeChange={onDateModeChange} />
        <TimeRangeSelector
          endTime={endTime}
          startTime={startTime}
          onEndTimeChange={onEndTimeChange}
          onPreset={onPreset}
          onStartTimeChange={onStartTimeChange}
        />
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="schedule-vehicle-block">
        <span className="field-label">Phương tiện di chuyển</span>
        <VehicleSelector framed={false} selectedVehicle={selectedVehicle} onChange={onVehicleChange} />
      </div>
    </Card>
  );
}
