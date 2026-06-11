import type { HourlyForecastItem } from "../../types/weather";
import { formatHour, formatPercent } from "../../utils/formatters";
import { Card } from "../common/Card";

type RainProbabilityCardProps = {
  items: HourlyForecastItem[];
};

export function RainProbabilityCard({ items }: RainProbabilityCardProps) {
  const visibleItems = items
    .filter((item) => typeof item.precipitation_probability_percent === "number")
    .slice(0, 7);

  if (visibleItems.length === 0) {
    return (
      <Card title="Khả năng mưa theo giờ">
        <p className="muted">Chưa có dữ liệu khả năng mưa.</p>
      </Card>
    );
  }

  return (
    <Card className="rain-card" title="Khả năng mưa theo giờ">
      <div className="rain-list">
        {visibleItems.map((item) => {
          const value = item.precipitation_probability_percent ?? 0;
          return (
            <div className="rain-row" key={`${item.time}-${value}`}>
              <span>{formatHour(item.time)}</span>
              <div className="rain-bar" aria-label={`Khả năng mưa ${formatPercent(value)}`}>
                <span style={{ width: `${Math.min(value, 100)}%` }} />
              </div>
              <strong>{formatPercent(value)}</strong>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
