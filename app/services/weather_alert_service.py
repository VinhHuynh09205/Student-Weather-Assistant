from app.models.domain import DailyForecast, WeatherSnapshot

STORM_WEATHER_CODES = {95, 96, 99}
RAIN_PROBABILITY_ALERT_PERCENT = 60
RAIN_AMOUNT_ALERT_MM = 0.2
WIND_ALERT_KMH = 30.0
UV_ALERT_INDEX = 8.0
HOT_TEMPERATURE_C = 35.0
HOT_APPARENT_TEMPERATURE_C = 37.0


def build_weather_alerts(
    *,
    current: WeatherSnapshot | None,
    hourly: list[WeatherSnapshot] | None = None,
    daily: DailyForecast | None = None,
) -> list[str]:
    if current is None:
        return []

    alerts: list[str] = []

    # Current/hourly checks (near current)
    # Let's consider current and next few hourly forecasts (e.g., next 6 hours)
    nearby_hourly = (hourly or [])[:6]

    current_rain_prob = current.precipitation_probability_percent or 0
    current_rain_amount = max(current.rain_mm or 0.0, current.precipitation_mm or 0.0)

    nearby_rain_prob = max([current_rain_prob] + [h.precipitation_probability_percent or 0 for h in nearby_hourly])
    nearby_rain_amount = max(
        [current_rain_amount] + [max(h.rain_mm or 0.0, h.precipitation_mm or 0.0) for h in nearby_hourly]
    )

    # 1. Storm (Thunderstorm)
    # "Dông: chỉ khi weather condition thật sự thunderstorm/storm."
    if current.weather_code in STORM_WEATHER_CODES or any(h.weather_code in STORM_WEATHER_CODES for h in nearby_hourly):
        alerts.append("Đang có khả năng dông (dong), hạn chế ra ngoài khi có sấm sét.")

    # 2. Rain
    # "Mưa: khi precipitation probability cao hoặc rain/precipitation đáng kể."
    if nearby_rain_prob >= RAIN_PROBABILITY_ALERT_PERCENT or nearby_rain_amount >= RAIN_AMOUNT_ALERT_MM:
        # Check if heavy rain
        if nearby_rain_amount >= 5.0:
            alerts.append("Đang có khả năng mưa lớn, nên tránh di chuyển lúc này.")
        else:
            alerts.append("Đang có khả năng mưa, nên chuẩn bị áo mưa hoặc dù.")

    # 3. Strong Wind
    # "Gió mạnh: wind_speed_kmh >= 30 hoặc 35."
    max_wind = max([current.wind_speed_kmh or 0.0] + [h.wind_speed_kmh or 0.0 for h in nearby_hourly])
    if max_wind >= WIND_ALERT_KMH:
        alerts.append("Gió mạnh, cần cẩn thận khi di chuyển.")

    # 4. High UV
    # "UV cao: chỉ khi is_day=true và uv_index >= 8. Ban đêm: không cảnh báo UV cao."
    # Let's check current UV and if it's day
    if current.is_day is True and current.uv_index >= UV_ALERT_INDEX:
        alerts.append("Chỉ số UV cao, nên che nắng khi ra ngoài.")

    # 5. Heat warning (apparent_temp >= 37 or temp >= 35)
    max_temp = max([current.temperature_c or 0.0] + [h.temperature_c or 0.0 for h in nearby_hourly])
    max_apparent = max(
        [current.apparent_temperature_c or 0.0] + [h.apparent_temperature_c or 0.0 for h in nearby_hourly]
    )
    if max_apparent >= HOT_APPARENT_TEMPERATURE_C or max_temp >= HOT_TEMPERATURE_C:
        alerts.append("Thời tiết nắng nóng, nhớ uống đủ nước.")

    # 6. Daily forecast alerts (future daily chance)
    # "Nếu alert dựa trên daily forecast, ghi rõ “Trong hôm nay có khả năng...”, không ghi như đang xảy ra hiện tại."
    if daily is not None:
        # Thunderstorm in daily, but not currently happening
        if daily.weather_code in STORM_WEATHER_CODES and current.weather_code not in STORM_WEATHER_CODES:
            alerts.append("Trong hôm nay có khả năng dông (dong).")

        # Rain probability in daily, but not near current
        daily_rain_prob = daily.precipitation_probability_max_percent or 0
        if daily_rain_prob >= 70 and nearby_rain_prob < RAIN_PROBABILITY_ALERT_PERCENT:
            alerts.append("Trong hôm nay có khả năng mưa cao.")

    # Remove duplicates preserving order
    unique_alerts = list(dict.fromkeys(alerts))

    if not unique_alerts:
        return ["Không có cảnh báo thời tiết đáng chú ý."]

    return unique_alerts
