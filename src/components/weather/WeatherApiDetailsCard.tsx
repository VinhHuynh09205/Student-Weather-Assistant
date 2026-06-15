import { ChevronDown, ChevronUp, CloudRain, Database, MapPin, Sun, Wind } from "lucide-react";
import { useState } from "react";

import type { CurrentWeatherResponse, DailyForecastItem, HourlyForecastItem } from "../../types/weather";
import {
  formatCoordinates,
  formatOptionalNumber,
  formatOptionalPercent,
  formatPercent,
  formatTemperature,
  formatWind,
} from "../../utils/formatters";
import { formatWeatherUpdatedAt } from "../../utils/timeHelpers";
import { Card } from "../common/Card";

type WeatherApiDetailsCardProps = {
  currentWeather: CurrentWeatherResponse | null;
  hourlyItems: HourlyForecastItem[];
  dailyItems: DailyForecastItem[];
};

export function WeatherApiDetailsCard({ currentWeather, hourlyItems, dailyItems }: WeatherApiDetailsCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const current = currentWeather?.current;
  const visibleHourly = hourlyItems.slice(0, 8);
  const visibleDaily = dailyItems.slice(0, 7);

  return (
    <Card className="weather-api-details-card">
      <button className="weather-details-toggle" type="button" onClick={() => setIsOpen((value) => !value)}>
        <span className="details-toggle-icon">
          <Database size={20} aria-hidden="true" />
        </span>
        <span>
          <strong>Chi tiết dữ liệu dự báo</strong>
          <small>Xem toàn bộ thông tin vị trí, hiện tại, theo giờ và nhiều ngày mà API trả về.</small>
        </span>
        {isOpen ? <ChevronUp size={20} aria-hidden="true" /> : <ChevronDown size={20} aria-hidden="true" />}
      </button>

      {isOpen ? (
        <div className="weather-details-content animate-slide-up">
          <section className="weather-details-section">
            <h3>
              <MapPin size={18} aria-hidden="true" />
              Vị trí & nguồn dữ liệu
            </h3>
            <div className="weather-details-grid">
              <DetailItem label="Tên hiển thị" value={currentWeather?.display_name || currentWeather?.location_name || currentWeather?.city} />
              <DetailItem label="Tên ngắn" value={currentWeather?.short_display_name} />
              <DetailItem label="Quốc gia" value={currentWeather?.country} />
              <DetailItem label="Tọa độ" value={formatCoordinates(currentWeather?.latitude, currentWeather?.longitude)} mono />
              <DetailItem label="Múi giờ" value={currentWeather?.timezone} />
              <DetailItem label="Độ chính xác GPS" value={formatOptionalNumber(currentWeather?.accuracy_meters ?? null, "m")} />
              <DetailItem label="Độ tin cậy vị trí" value={currentWeather?.location_confidence} />
              <DetailItem label="Provider vị trí" value={currentWeather?.location_provider} />
              <DetailItem label="Nguồn thời tiết" value={formatProvider(currentWeather)} />
              <DetailItem label="Cần xác nhận vị trí" value={currentWeather?.needs_user_confirmation ? "Có" : "Không"} />
              <DetailItem
                label="Gợi ý vị trí"
                value={currentWeather?.location_candidates?.length ? currentWeather.location_candidates.join(" · ") : "Không có"}
              />
            </div>
          </section>

          <section className="weather-details-section">
            <h3>
              <Sun size={18} aria-hidden="true" />
              Thời tiết hiện tại
            </h3>
            <div className="weather-details-grid">
              <DetailItem label="Cập nhật lúc" value={formatWeatherUpdatedAt(current?.time, currentWeather?.timezone)} />
              <DetailItem label="Mô tả" value={current?.weather_description} />
              <DetailItem label="Mã thời tiết" value={current?.weather_code} />
              <DetailItem label="Ngày/đêm" value={current?.is_day === false ? "Ban đêm" : current?.is_day === true ? "Ban ngày" : "Chưa rõ"} />
              <DetailItem label="Nhiệt độ" value={formatTemperature(current?.temperature_c)} />
              <DetailItem label="Cảm giác như" value={formatTemperature(current?.apparent_temperature_c)} />
              <DetailItem label="Độ ẩm" value={formatOptionalPercent(current?.relative_humidity_percent)} />
              <DetailItem label="Khả năng mưa" value={formatOptionalPercent(current?.precipitation_probability_percent)} />
              <DetailItem label="Mưa tổng" value={formatOptionalNumber(current?.precipitation_mm ?? null, "mm")} />
              <DetailItem label="Mưa rain_mm" value={formatOptionalNumber(current?.rain_mm ?? null, "mm")} />
              <DetailItem label="Mưa rào" value={formatOptionalNumber(current?.showers_mm ?? null, "mm")} />
              <DetailItem label="Tốc độ gió" value={formatWind(current?.wind_speed_kmh)} />
              <DetailItem label="Hướng gió" value={formatWindDirection(current?.wind_direction_degrees)} />
              <DetailItem label="UV" value={formatOptionalNumber(current?.uv_index ?? null)} />
              <DetailItem label="Áp suất" value={formatOptionalNumber(current?.pressure_hpa ?? null, "hPa")} />
              <DetailItem label="Tầm nhìn" value={formatVisibility(current?.visibility_meters)} />
              <DetailItem label="Mây che phủ" value={formatOptionalPercent(current?.cloud_cover_percent)} />
            </div>
          </section>

          <section className="weather-details-section">
            <h3>
              <CloudRain size={18} aria-hidden="true" />
              Dự báo theo giờ
            </h3>
            {visibleHourly.length ? (
              <div className="weather-details-table-wrap">
                <table className="weather-details-table">
                  <thead>
                    <tr>
                      <th>Giờ</th>
                      <th>Mô tả</th>
                      <th>Nhiệt độ</th>
                      <th>Cảm giác</th>
                      <th>Ẩm</th>
                      <th>Mưa</th>
                      <th>mm</th>
                      <th>Gió</th>
                      <th>UV</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleHourly.map((item) => (
                      <tr key={item.time}>
                        <td>{formatHourLabel(item.time)}</td>
                        <td>{item.weather_description || `Mã ${item.weather_code ?? "--"}`}</td>
                        <td>{formatTemperature(item.temperature_c)}</td>
                        <td>{formatTemperature(item.apparent_temperature_c)}</td>
                        <td>{formatOptionalPercent(item.relative_humidity_percent)}</td>
                        <td>{formatOptionalPercent(item.precipitation_probability_percent)}</td>
                        <td>{formatHourlyRain(item)}</td>
                        <td>{formatWind(item.wind_speed_kmh)}</td>
                        <td>{formatOptionalNumber(item.uv_index ?? null)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="empty-copy">Chưa có dữ liệu theo giờ.</p>
            )}
          </section>

          <section className="weather-details-section">
            <h3>
              <Wind size={18} aria-hidden="true" />
              Dự báo nhiều ngày
            </h3>
            {visibleDaily.length ? (
              <div className="weather-details-table-wrap">
                <table className="weather-details-table">
                  <thead>
                    <tr>
                      <th>Ngày</th>
                      <th>Mô tả</th>
                      <th>Max/Min</th>
                      <th>Mưa</th>
                      <th>Tổng mưa</th>
                      <th>Gió max</th>
                      <th>UV max</th>
                      <th>Mặt trời</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleDaily.map((item) => (
                      <tr key={item.date}>
                        <td>{formatDailyLabel(item.date)}</td>
                        <td>{item.weather_description || `Mã ${item.weather_code}`}</td>
                        <td>
                          {formatTemperature(item.temperature_max_c)} / {formatTemperature(item.temperature_min_c)}
                        </td>
                        <td>{formatPercent(item.precipitation_probability_max_percent)}</td>
                        <td>{formatOptionalNumber(item.rain_sum_mm, "mm")}</td>
                        <td>{formatWind(item.wind_speed_max_kmh)}</td>
                        <td>{formatOptionalNumber(item.uv_index_max)}</td>
                        <td>
                          {formatHourLabel(item.sunrise)} - {formatHourLabel(item.sunset)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="empty-copy">Chưa có dữ liệu nhiều ngày.</p>
            )}
          </section>
        </div>
      ) : null}
    </Card>
  );
}

function DetailItem({
  label,
  mono = false,
  value,
}: {
  label: string;
  mono?: boolean;
  value?: number | string | null;
}) {
  const displayValue = value === undefined || value === null || value === "" ? "Chưa có dữ liệu" : String(value);
  return (
    <div className="weather-detail-item">
      <span>{label}</span>
      <strong className={mono ? "mono-value" : ""}>{displayValue}</strong>
    </div>
  );
}

function formatProvider(currentWeather: CurrentWeatherResponse | null): string {
  if (!currentWeather?.provider) return "Chưa có dữ liệu";
  if (currentWeather.fallback_provider_used) {
    return `${currentWeather.provider} · fallback ${currentWeather.fallback_provider || "khác"}`;
  }
  return currentWeather.provider;
}

function formatWindDirection(value?: number | null): string {
  if (typeof value !== "number") return "Chưa có dữ liệu";
  return `${Math.round(value)}° ${directionLabel(value)}`;
}

function directionLabel(degrees: number): string {
  const labels = ["Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc"];
  return labels[Math.round((((degrees % 360) + 360) % 360) / 45) % 8];
}

function formatVisibility(value?: number | null): string {
  if (typeof value !== "number") return "Chưa có dữ liệu";
  if (value >= 1000) return `${Number((value / 1000).toFixed(1))} km`;
  return `${Math.round(value)} m`;
}

function formatHourlyRain(item: HourlyForecastItem): string {
  const values = [item.precipitation_mm, item.rain_mm].filter((value): value is number => typeof value === "number");
  if (!values.length) return "Chưa có";
  return `${Number(Math.max(...values).toFixed(1))} mm`;
}

function formatHourLabel(value?: string | null): string {
  if (!value) return "--:--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.slice(11, 16) || value.slice(0, 5) || value;
  }
  return date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function formatDailyLabel(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("vi-VN", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  });
}
