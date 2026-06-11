import type { HourlyForecastItem } from "../../types/weather";
import { formatHour } from "../../utils/formatters";
import { Card } from "../common/Card";

type TemperatureChartProps = {
  items: HourlyForecastItem[];
};

export function TemperatureChart({ items }: TemperatureChartProps) {
  const points = items.slice(0, 7).filter((item) => typeof item.temperature_c === "number");
  const temperatures = points.map((item) => item.temperature_c ?? 0);
  const maxTemperature = Math.max(...temperatures, 1);
  const minTemperature = Math.min(...temperatures, maxTemperature);
  const range = Math.max(maxTemperature - minTemperature, 1);
  const path = points
    .map((item, index) => {
      const x = 9 + index * (82 / Math.max(points.length - 1, 1));
      const y = 72 - (((item.temperature_c ?? 0) - minTemperature) / range) * 46;
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  return (
    <Card className="chart-card" title="Nhiệt độ theo giờ">
      {points.length > 1 ? (
        <>
          <svg className="temperature-chart" viewBox="0 0 100 82" role="img" aria-label="Biểu đồ nhiệt độ theo giờ">
            <path d={`${path} L 91 78 L 9 78 Z`} className="chart-fill" />
            <path d={path} className="chart-line" />
            {points.map((item, index) => {
              const x = 9 + index * (82 / Math.max(points.length - 1, 1));
              const y = 72 - (((item.temperature_c ?? 0) - minTemperature) / range) * 46;
              return <circle cx={x} cy={y} key={item.time} r="1.9" />;
            })}
          </svg>
          <div className="chart-labels">
            {points.map((item) => (
              <span key={item.time}>{formatHour(item.time).replace(":00", "h")}</span>
            ))}
          </div>
        </>
      ) : (
        <p className="muted">Chưa đủ dữ liệu để vẽ biểu đồ.</p>
      )}
    </Card>
  );
}
