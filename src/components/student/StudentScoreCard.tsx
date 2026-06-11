import type { CSSProperties } from "react";

import type { StudentAdviceResponse } from "../../types/weather";
import { formatScheduleRange } from "../../utils/formatters";
import { getScoreTone } from "../../utils/weatherTheme";
import { Card } from "../common/Card";

type StudentScoreCardProps = {
  advice: StudentAdviceResponse | null;
  compact?: boolean;
};

export function StudentScoreCard({ advice, compact = false }: StudentScoreCardProps) {
  const score = advice?.score ?? 0;
  const tone = getScoreTone(score);
  const rainProbability = advice?.metrics.max_precipitation_probability_percent ?? 0;

  return (
    <Card className={`score-card tone-${tone} ${compact ? "compact-score" : ""}`}>
      <div className="score-ring" style={{ "--score": score } as CSSProperties}>
        <div>
          <strong>{advice ? score : "--"}</strong>
          <span>/100</span>
        </div>
      </div>
      <div className="score-copy">
        <h2>Điểm thuận lợi đi học</h2>
        <strong>{advice?.level ?? "Đang tính"}</strong>
        <span>{formatScheduleRange(advice?.study_date, advice?.start_time, advice?.end_time)}</span>
        <span>Khả năng mưa: {rainProbability}%</span>
      </div>
    </Card>
  );
}
