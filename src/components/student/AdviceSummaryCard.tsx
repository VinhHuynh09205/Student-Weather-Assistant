import { Info } from "lucide-react";

import type { StudentAdviceResponse, VehicleType } from "../../types/weather";
import { formatScheduleRange, formatTemperature, getVehicleIcon, getVehicleLabel } from "../../utils/formatters";
import { Card } from "../common/Card";

type AdviceSummaryCardProps = {
  advice: StudentAdviceResponse | null;
  selectedVehicle: VehicleType;
  studyDate: string;
  startTime: string;
  endTime: string;
};

export function AdviceSummaryCard({
  advice,
  endTime,
  selectedVehicle,
  startTime,
  studyDate,
}: AdviceSummaryCardProps) {
  const scheduleLabel = formatScheduleRange(advice?.study_date ?? studyDate, advice?.start_time ?? startTime, advice?.end_time ?? endTime);

  return (
    <>
      <Card className="advice-hero">
        <div className="advice-context">
          <article>
            <span>📚</span>
            <strong>{scheduleLabel}</strong>
            <small>Lịch học</small>
          </article>
          <article>
            <span>{getVehicleIcon(selectedVehicle)}</span>
            <strong>{getVehicleLabel(selectedVehicle)}</strong>
            <small>Phương tiện</small>
          </article>
          <article>
            <span>🌡️</span>
            <strong>{formatTemperature(advice?.metrics.max_temperature_c)}</strong>
            <small>Nhiệt độ cao nhất</small>
          </article>
        </div>
      </Card>

      <Card className="summary-card">
        <h2>
          <Info size={22} />
          Tóm tắt buổi học
        </h2>
        <p>{advice?.summary ?? "Đang cá nhân hóa gợi ý theo lịch học của bạn."}</p>
      </Card>
    </>
  );
}
