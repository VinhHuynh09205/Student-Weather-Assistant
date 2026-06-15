import { AlertTriangle, CheckCircle2, ShieldCheck, Umbrella, Zap } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { ClassScheduleRiskLevel } from "../../types/classSchedule";
import { riskLevelLabels } from "../../utils/classScheduleFormatters";

const riskIcons: Record<ClassScheduleRiskLevel, LucideIcon> = {
  SAFE: ShieldCheck,
  NOTICE: CheckCircle2,
  PREPARE: Umbrella,
  DANGER: Zap,
};

type RiskBadgeProps = {
  riskLevel: ClassScheduleRiskLevel;
  compact?: boolean;
};

export function RiskBadge({ riskLevel, compact = false }: RiskBadgeProps) {
  const Icon = riskIcons[riskLevel] ?? AlertTriangle;

  return (
    <span className={`class-risk-badge risk-${riskLevel.toLowerCase()} ${compact ? "compact" : ""}`}>
      <Icon size={compact ? 14 : 16} aria-hidden="true" />
      {riskLevelLabels[riskLevel] ?? riskLevel}
    </span>
  );
}
