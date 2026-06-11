import { ArrowRight, CalendarClock } from "lucide-react";

import type { StudentAdviceResponse, StudySchedule } from "../../types/weather";
import { formatScheduleRange, vehicleLabels } from "../../utils/formatters";
import { Card } from "../common/Card";

type UpcomingStudyPreviewCardProps = {
  advice: StudentAdviceResponse | null;
  hasSavedSchedule: boolean;
  onOpenStudyAssistant: () => void;
  schedule: StudySchedule;
};

export function UpcomingStudyPreviewCard({
  advice,
  hasSavedSchedule,
  onOpenStudyAssistant,
  schedule,
}: UpcomingStudyPreviewCardProps) {
  return (
    <Card className="upcoming-study-card">
      <div className="section-title-row">
        <h2>
          <CalendarClock size={22} />
          Buổi học sắp tới
        </h2>
      </div>

      {hasSavedSchedule ? (
        <>
          <div className="study-preview-main">
            <strong>{formatScheduleRange(schedule.study_date, schedule.start_time, schedule.end_time)}</strong>
            <span>{vehicleLabels[schedule.vehicle_type]}</span>
          </div>
          <div className="study-preview-score">
            <span>Điểm thuận lợi</span>
            <strong>{advice ? `${advice.score}/100` : "--"}</strong>
          </div>
          <p>{advice?.summary ?? "Đang phân tích thời tiết cho lịch học của bạn."}</p>
        </>
      ) : (
        <p>Bạn chưa thiết lập lịch học.</p>
      )}

      <button className="inline-action-button" type="button" onClick={onOpenStudyAssistant}>
        <span>{hasSavedSchedule ? "Xem chi tiết" : "Thiết lập lịch học"}</span>
        <ArrowRight size={18} />
      </button>
    </Card>
  );
}
