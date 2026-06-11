import { Droplets, Umbrella, Wind } from "lucide-react";
import type { ReactNode } from "react";

import type { HourlyForecastItem } from "../../types/weather";
import { formatHour, formatPercent, formatWind } from "../../utils/formatters";
import { Card } from "../common/Card";

type WeatherTrendCardsProps = {
  items: HourlyForecastItem[];
};

export function WeatherTrendCards({ items }: WeatherTrendCardsProps) {
  const visibleItems = items.slice(0, 7);

  return (
    <div className="trend-grid">
      <TrendCard
        icon={<Umbrella size={20} />}
        items={visibleItems.map((item) => ({
          label: formatHour(item.time),
          value: item.precipitation_probability_percent ?? 0,
          text: formatPercent(item.precipitation_probability_percent),
        }))}
        title="Khả năng mưa"
      />
      <TrendCard
        icon={<Wind size={20} />}
        items={visibleItems.map((item) => ({
          label: formatHour(item.time),
          value: item.wind_speed_kmh ?? 0,
          text: formatWind(item.wind_speed_kmh),
        }))}
        title="Gió theo giờ"
      />
      <TrendCard
        icon={<Droplets size={20} />}
        items={visibleItems.map((item) => ({
          label: formatHour(item.time),
          value: item.relative_humidity_percent ?? 0,
          text: formatPercent(item.relative_humidity_percent),
        }))}
        title="Độ ẩm"
      />
    </div>
  );
}

function TrendCard({
  icon,
  items,
  title,
}: {
  icon: ReactNode;
  items: Array<{ label: string; value: number; text: string }>;
  title: string;
}) {
  const maxValue = Math.max(1, ...items.map((item) => item.value));

  return (
    <Card className="trend-card">
      <h2>
        {icon}
        {title}
      </h2>
      <div className="trend-list">
        {items.length ? (
          items.map((item) => (
            <div className="trend-row" key={`${title}-${item.label}`}>
              <span>{item.label}</span>
              <div aria-label={`${title} ${item.text}`}>
                <i style={{ width: `${Math.max(6, (item.value / maxValue) * 100)}%` }} />
              </div>
              <strong>{item.text}</strong>
            </div>
          ))
        ) : (
          <p className="empty-copy">Chưa có dữ liệu.</p>
        )}
      </div>
    </Card>
  );
}
