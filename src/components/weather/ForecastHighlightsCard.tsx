import { CloudRain, Sun, Thermometer, Wind } from "lucide-react";
import type { DailyForecastItem, HourlyForecastItem } from "../../types/weather";
import { formatHour, formatPercent, formatTemperature, formatWind } from "../../utils/formatters";
import { Card } from "../common/Card";

type ForecastHighlightsCardProps = {
  hourlyItems: HourlyForecastItem[];
  dailyItems: DailyForecastItem[];
};

export function ForecastHighlightsCard({ hourlyItems, dailyItems }: ForecastHighlightsCardProps) {
  const maxTempDaily = dailyItems[0]?.temperature_max_c;
  const minTempDaily = dailyItems[0]?.temperature_min_c;
  
  let maxRainItem: HourlyForecastItem | null = null;
  let maxRainVal = -1;
  
  let maxWindItem: HourlyForecastItem | null = null;
  let maxWindVal = -1;

  let maxUvVal = 0;
  let maxUvHour = "";

  hourlyItems.forEach((item) => {
    const rain = item.precipitation_probability_percent ?? 0;
    if (rain > maxRainVal) {
      maxRainVal = rain;
      maxRainItem = item;
    }
    const wind = item.wind_speed_kmh ?? 0;
    if (wind > maxWindVal) {
      maxWindVal = wind;
      maxWindItem = item;
    }
    const uv = item.uv_index ?? 0;
    if (uv > maxUvVal) {
      maxUvVal = uv;
      maxUvHour = formatHour(item.time);
    }
  });

  const rainItem = maxRainItem as HourlyForecastItem | null;
  const windItem = maxWindItem as HourlyForecastItem | null;

  const rainLabel = rainItem && maxRainVal > 0
    ? `Khả năng mưa đạt ${formatPercent(maxRainVal)} lúc ${formatHour(rainItem.time)}.`
    : "Khả năng mưa thấp trong suốt các khung giờ.";

  const windLabel = windItem && maxWindVal >= 15
    ? `Gió mạnh nhất ${formatWind(maxWindVal)} lúc ${formatHour(windItem.time)}.`
    : "Sức gió nhẹ nhàng, lặng gió.";

  const tempLabel = typeof maxTempDaily === "number" && typeof minTempDaily === "number"
    ? `Nhiệt độ dao động từ ${formatTemperature(minTempDaily)} đến ${formatTemperature(maxTempDaily)}.`
    : "Nhiệt độ ổn định.";

  const uvLabel = maxUvVal >= 8
    ? `Chỉ số UV cực đại là ${maxUvVal} (${maxUvVal >= 11 ? "Cực kỳ nguy hiểm" : "Rất cao"}) lúc ${maxUvHour}.`
    : maxUvVal >= 3
    ? `Chỉ số UV đạt mức trung bình/cao (${maxUvVal}) lúc ${maxUvHour}.`
    : "Chỉ số bức xạ UV thấp.";

  return (
    <Card className="forecast-highlights-card" title="Điểm nổi bật trong ngày">
      <div className="highlights-grid">
        <div className="highlight-item">
          <div className="highlight-icon icon-temp">
            <Thermometer size={20} />
          </div>
          <div>
            <strong>Nhiệt độ ngày</strong>
            <p>{tempLabel}</p>
          </div>
        </div>

        <div className="highlight-item">
          <div className="highlight-icon icon-rain">
            <CloudRain size={20} />
          </div>
          <div>
            <strong>Khả năng có mưa</strong>
            <p>{rainLabel}</p>
          </div>
        </div>

        <div className="highlight-item">
          <div className="highlight-icon icon-wind">
            <Wind size={20} />
          </div>
          <div>
            <strong>Sức gió & Lưu thông</strong>
            <p>{windLabel}</p>
          </div>
        </div>

        <div className="highlight-item">
          <div className="highlight-icon icon-uv">
            <Sun size={20} />
          </div>
          <div>
            <strong>Chỉ số tia cực tím (UV)</strong>
            <p>{uvLabel}</p>
          </div>
        </div>
      </div>
    </Card>
  );
}
