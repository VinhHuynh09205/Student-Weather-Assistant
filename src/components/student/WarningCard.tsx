import { TriangleAlert, Zap } from "lucide-react";

import type { StudentAdviceResponse } from "../../types/weather";
import { Card } from "../common/Card";

type WarningCardProps = {
  advice: StudentAdviceResponse | null;
};

export function WarningCard({ advice }: WarningCardProps) {
  const warnings = advice?.warnings.length ? advice.warnings : ["Không có cảnh báo đáng chú ý."];

  return (
    <Card className={`warning-card ${advice?.warnings.length ? "has-warning" : ""}`}>
      <h2>
        <Zap size={22} />
        Cảnh báo thời tiết
      </h2>
      <ul>
        {warnings.map((warning) => (
          <li key={warning}>
            <TriangleAlert size={16} />
            <span>{warning}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
