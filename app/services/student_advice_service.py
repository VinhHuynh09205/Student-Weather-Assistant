from datetime import datetime, timedelta

from app.core.constants import (
    APPARENT_TEMPERATURE_HOT_C,
    APPARENT_TEMPERATURE_VERY_HOT_C,
    HUMIDITY_HIGH_PERCENT,
    RAIN_PROBABILITY_HIGH,
    RAIN_PROBABILITY_MEDIUM,
    TOTAL_RAIN_HEAVY_MM,
    UV_INDEX_HIGH,
    WIND_SPEED_STRONG_KMH,
)
from app.core.exceptions import InvalidWeatherDataError
from app.models.domain import (
    AdviceHourlyForecast,
    AdviceMetrics,
    BeforeAfterClassTimeline,
    DuringClassTimeline,
    LocalWeatherOverride,
    StudentAdviceReport,
    StudyTimeline,
    WeatherSnapshot,
)
from app.schemas.advice import StudentAdviceRequest
from app.services.local_weather_report_service import apply_local_weather_override_to_hourly, derive_condition
from app.services.weather_cache import (
    AsyncTTLCache,
    normalize_city_for_cache,
    round_coordinate_for_cache,
)
from app.services.weather_service import WeatherService
from app.utils.time_utils import parse_open_meteo_time

STUDENT_ADVICE_TTL_SECONDS = 10 * 60


class StudentAdviceService:
    """Builds commute-to-class advice from normalized hourly weather data."""

    def __init__(self, weather_service: WeatherService, cache: AsyncTTLCache | None = None) -> None:
        self._weather_service = weather_service
        self._cache = cache

    async def get_student_advice(
        self,
        request: StudentAdviceRequest,
        *,
        local_override: LocalWeatherOverride | None = None,
    ) -> StudentAdviceReport:
        provider_name = "open_meteo"
        if hasattr(self._weather_service, "active_provider"):
            provider_name = self._weather_service.active_provider.name
        if self._cache is not None:
            return await self._cache.get_or_create(
                _build_student_advice_cache_key(request, provider_name, local_override),
                ttl_seconds=STUDENT_ADVICE_TTL_SECONDS,
                factory=lambda: self._build_student_advice(request, local_override=local_override),
            )
        return await self._build_student_advice(request, local_override=local_override)

    async def _build_student_advice(
        self,
        request: StudentAdviceRequest,
        *,
        local_override: LocalWeatherOverride | None = None,
    ) -> StudentAdviceReport:
        if request.has_coordinates:
            if request.latitude is None or request.longitude is None:
                raise InvalidWeatherDataError("Thiếu tọa độ để lấy dự báo thời tiết.")
            forecast_report = await self._weather_service.get_hourly_forecast_by_coordinates(
                latitude=request.latitude,
                longitude=request.longitude,
                hours=72,
                accuracy_meters=request.accuracy_meters,
            )
        else:
            if request.city is None:
                raise InvalidWeatherDataError("Thiếu tên thành phố để lấy dự báo thời tiết.")
            forecast_report = await self._weather_service.get_hourly_forecast(request.city, hours=72)
        provider_forecast_report = forecast_report
        forecast_report = apply_local_weather_override_to_hourly(forecast_report, local_override)
        start_at, end_at = self._build_schedule_window(request)
        provider_schedule_forecasts = self._select_schedule_forecasts(
            provider_forecast_report.hourly,
            start_at=start_at,
            end_at=end_at,
        )
        schedule_forecasts = self._select_schedule_forecasts(
            forecast_report.hourly,
            start_at=start_at,
            end_at=end_at,
        )
        before_class = self._find_nearest_forecast(
            forecast_report.hourly,
            target=start_at - timedelta(minutes=45),
        )
        after_class = self._find_nearest_forecast(
            forecast_report.hourly,
            target=end_at,
            prefer_later=True,
        )
        metrics = self._calculate_metrics(schedule_forecasts)
        score = self._calculate_score(metrics)
        representative = self._pick_representative_forecast(schedule_forecasts)
        provider_representative = self._pick_representative_forecast(provider_schedule_forecasts)
        timeline = self._build_timeline(
            before_class=before_class,
            schedule_forecasts=schedule_forecasts,
            after_class=after_class,
            metrics=metrics,
            start_at=start_at,
            end_at=end_at,
        )

        return StudentAdviceReport(
            city=forecast_report.location.city,
            source=forecast_report.location.source,
            location_name=forecast_report.location.location_name or forecast_report.location.city,
            display_name=forecast_report.location.display_name
            or forecast_report.location.location_name
            or forecast_report.location.city,
            country=forecast_report.location.country,
            latitude=forecast_report.location.latitude,
            longitude=forecast_report.location.longitude,
            timezone=forecast_report.location.timezone,
            accuracy_meters=forecast_report.location.accuracy_meters,
            study_date=start_at.date().isoformat(),
            start_time=self._format_clock(start_at),
            end_time=self._format_clock(end_at),
            vehicle_type=request.vehicle_type,
            score=score,
            level=self._classify_level(score),
            summary=self._build_summary(
                metrics=metrics,
                score=score,
                start_at=start_at,
                end_at=end_at,
                after_class=after_class,
            ),
            timeline=timeline,
            metrics=metrics,
            recommendations=self._build_recommendations(
                vehicle_type=request.vehicle_type,
                metrics=metrics,
                score=score,
                before_class=before_class,
                after_class=after_class,
                local_override=local_override,
            ),
            warnings=self._build_warnings(
                metrics=metrics,
                before_class=before_class,
                after_class=after_class,
                local_override=local_override,
            ),
            hourly_forecast=[self._to_advice_hourly_forecast(item) for item in schedule_forecasts],
            weather_code=representative.weather_code,
            weather_description=representative.weather_description,
            is_day=representative.is_day,
            time=representative.time,
            wind_speed_kmh=representative.wind_speed_kmh,
            precipitation_probability_percent=metrics.max_precipitation_probability_percent,
            temperature_c=metrics.max_temperature_c,
            provider_condition=derive_condition(provider_representative),
            effective_condition=(
                local_override.reported_condition if local_override else derive_condition(representative)
            ),
            override_source=local_override.source if local_override else None,
            override_expires_at=local_override.expires_at if local_override else None,
            override_report_id=local_override.id if local_override else None,
            override_intensity=local_override.intensity if local_override else None,
        )

    def _build_schedule_window(self, request: StudentAdviceRequest) -> tuple[datetime, datetime]:
        if request.study_date is None or request.start_time is None or request.end_time is None:
            raise InvalidWeatherDataError("Thiếu ngày hoặc giờ học để tính dự báo.")

        start_at = datetime.combine(request.study_date, request.start_time)
        end_at = datetime.combine(request.study_date, request.end_time)
        if end_at <= start_at:
            raise ValueError("Giờ kết thúc phải lớn hơn giờ bắt đầu.")
        return start_at, end_at

    def _select_schedule_forecasts(
        self,
        hourly_forecasts: list[WeatherSnapshot],
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> list[WeatherSnapshot]:
        forecasts = [
            forecast for forecast in hourly_forecasts if start_at <= parse_open_meteo_time(forecast.time) <= end_at
        ]
        if forecasts:
            return forecasts

        midpoint = start_at + (end_at - start_at) / 2
        nearest = self._find_nearest_forecast(hourly_forecasts, target=midpoint)
        distance = abs(parse_open_meteo_time(nearest.time) - midpoint)
        if distance <= timedelta(minutes=90):
            return [nearest]

        raise InvalidWeatherDataError("Không có dữ liệu dự báo cho ngày và khung giờ đã chọn.")

    def _find_nearest_forecast(
        self,
        forecasts: list[WeatherSnapshot],
        *,
        target: datetime,
        prefer_later: bool = False,
    ) -> WeatherSnapshot:
        if not forecasts:
            raise InvalidWeatherDataError("Không có dữ liệu dự báo để phân tích.")
        return min(
            forecasts,
            key=lambda forecast: self._nearest_sort_key(
                forecast,
                target=target,
                prefer_later=prefer_later,
            ),
        )

    def _nearest_sort_key(
        self,
        forecast: WeatherSnapshot,
        *,
        target: datetime,
        prefer_later: bool,
    ) -> tuple[float, int]:
        forecast_time = parse_open_meteo_time(forecast.time)
        distance_seconds = abs((forecast_time - target).total_seconds())
        is_before_target = forecast_time < target
        if prefer_later:
            return distance_seconds, 1 if is_before_target else 0
        return distance_seconds, 0 if is_before_target else 1

    def _calculate_metrics(self, forecasts: list[WeatherSnapshot]) -> AdviceMetrics:
        if not forecasts:
            raise InvalidWeatherDataError("Không có dữ liệu dự báo để tính lời khuyên.")

        return AdviceMetrics(
            max_temperature_c=round(max(item.temperature_c for item in forecasts), 1),
            max_apparent_temperature_c=round(max(item.apparent_temperature_c for item in forecasts), 1),
            max_precipitation_probability_percent=max(
                item.precipitation_probability_percent or 0 for item in forecasts
            ),
            total_rain_mm=round(sum(item.rain_mm for item in forecasts), 1),
            max_wind_speed_kmh=round(max(item.wind_speed_kmh for item in forecasts), 1),
            max_uv_index=round(max(item.uv_index for item in forecasts), 1),
            average_humidity_percent=round(
                sum(item.relative_humidity_percent for item in forecasts) / len(forecasts),
                1,
            ),
        )

    def _calculate_score(self, metrics: AdviceMetrics) -> int:
        score = 100

        if metrics.max_precipitation_probability_percent >= RAIN_PROBABILITY_HIGH:
            score -= 30
        elif metrics.max_precipitation_probability_percent >= RAIN_PROBABILITY_MEDIUM:
            score -= 20

        if metrics.total_rain_mm >= TOTAL_RAIN_HEAVY_MM:
            score -= 20

        if metrics.max_apparent_temperature_c >= APPARENT_TEMPERATURE_VERY_HOT_C:
            score -= 20
        elif metrics.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C:
            score -= 10

        if metrics.max_wind_speed_kmh >= WIND_SPEED_STRONG_KMH:
            score -= 15

        if metrics.max_uv_index >= UV_INDEX_HIGH:
            score -= 10

        if metrics.average_humidity_percent >= HUMIDITY_HIGH_PERCENT:
            score -= 10

        return min(100, max(0, score))

    def _classify_level(self, score: int) -> str:
        if score >= 80:
            return "Tốt"
        if score >= 50:
            return "Bình thường"
        return "Không thuận lợi"

    def _build_timeline(
        self,
        *,
        before_class: WeatherSnapshot,
        schedule_forecasts: list[WeatherSnapshot],
        after_class: WeatherSnapshot,
        metrics: AdviceMetrics,
        start_at: datetime,
        end_at: datetime,
    ) -> StudyTimeline:
        return StudyTimeline(
            before_class=BeforeAfterClassTimeline(
                time=self._format_hour_from_snapshot(before_class),
                message=self._build_before_message(before_class),
                temperature_c=before_class.temperature_c,
                precipitation_probability_percent=before_class.precipitation_probability_percent or 0,
                weather_description=before_class.weather_description,
            ),
            during_class=DuringClassTimeline(
                time_range=f"{self._format_clock(start_at)} - {self._format_clock(end_at)}",
                message=self._build_during_message(metrics, schedule_forecasts),
                max_temperature_c=metrics.max_temperature_c,
                max_precipitation_probability_percent=metrics.max_precipitation_probability_percent,
            ),
            after_class=BeforeAfterClassTimeline(
                time=self._format_hour_from_snapshot(after_class),
                message=self._build_after_message(after_class, metrics),
                temperature_c=after_class.temperature_c,
                precipitation_probability_percent=after_class.precipitation_probability_percent or 0,
                weather_description=after_class.weather_description,
            ),
        )

    def _build_recommendations(
        self,
        *,
        vehicle_type: str,
        metrics: AdviceMetrics,
        score: int,
        before_class: WeatherSnapshot,
        after_class: WeatherSnapshot,
        local_override: LocalWeatherOverride | None = None,
    ) -> list[str]:
        recommendations: list[str] = []
        local_rain = local_override is not None and local_override.reported_condition in {"rain", "storm"}
        before_rain = self._rain_probability(before_class) >= RAIN_PROBABILITY_MEDIUM
        after_rain = self._rain_probability(after_class) >= RAIN_PROBABILITY_MEDIUM
        rain_risk = (
            metrics.max_precipitation_probability_percent >= RAIN_PROBABILITY_MEDIUM or before_rain or after_rain
        )
        strong_wind = metrics.max_wind_speed_kmh >= WIND_SPEED_STRONG_KMH
        hot_weather = metrics.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C

        if local_rain:
            recommendations.append(
                "Theo xác nhận thời tiết tại chỗ của bạn, khu vực đang mưa. "
                "Hãy ưu tiên chuẩn bị đồ chống mưa."
            )
        elif before_rain:
            recommendations.append("Nên đi sớm hơn và mang áo mưa trước khi đến lớp.")
        elif rain_risk:
            recommendations.append("Nên mang áo mưa hoặc dù.")

        if after_rain:
            recommendations.append("Lúc tan học có khả năng mưa, hãy chuẩn bị áo mưa khi về.")

        if hot_weather or metrics.max_uv_index >= UV_INDEX_HIGH:
            recommendations.append("Nên mang nước uống, nón hoặc áo khoác nhẹ.")

        vehicle_recommendation = self._build_vehicle_recommendation(
            vehicle_type=vehicle_type,
            rain_risk=rain_risk or local_rain,
            strong_wind=strong_wind,
            hot_weather=hot_weather,
            storm_risk=(
                local_override.reported_condition == "storm"
                if local_override
                else metrics.max_precipitation_probability_percent >= RAIN_PROBABILITY_HIGH and strong_wind
            ),
        )
        if vehicle_recommendation:
            recommendations.append(vehicle_recommendation)

        if score >= 80:
            recommendations.append("Thời tiết khá thuận lợi cho buổi học của bạn.")

        return list(dict.fromkeys(recommendations))

    def _build_vehicle_recommendation(
        self,
        *,
        vehicle_type: str,
        rain_risk: bool,
        strong_wind: bool,
        hot_weather: bool,
        storm_risk: bool,
    ) -> str:
        if vehicle_type == "motorbike":
            if storm_risk:
                return "Đi xe máy nên đi sớm, mang áo mưa, chạy chậm và tránh dông gió mạnh."
            if rain_risk or strong_wind:
                return "Đi xe máy nên đi sớm 10-15 phút, mang áo mưa và chú ý đường trơn, gió mạnh, tầm nhìn kém."
            return "Đi xe máy khá thuận tiện, vẫn nên kiểm tra áo mưa mỏng và tình trạng đường trước khi đi."

        if vehicle_type == "walking":
            if storm_risk:
                return "Đi bộ nên tránh mưa lớn hoặc dông, ưu tiên lối có mái che và chờ thời tiết dịu hơn."
            if rain_risk:
                return "Đi bộ nên mang dù, đi giày chống trượt và chọn tuyến đường có mái che nếu có."
            if hot_weather:
                return "Đi bộ nên tránh nắng lâu và mang thêm nước."
            return "Đi bộ phù hợp nếu quãng đường ngắn, nên chọn tuyến an toàn và đủ ánh sáng."

        if vehicle_type == "bus":
            if rain_risk or storm_risk:
                return "Đi xe buýt nên ra trạm sớm, kiểm tra thời gian chờ và chuẩn bị áo mưa cho đoạn đi bộ."
            return "Đi xe buýt nên kiểm tra lịch chuyến và ra trạm sớm vài phút để tránh lỡ xe."

        if vehicle_type == "car":
            if storm_risk:
                return "Đi ô tô cần lái chậm, bật đèn, giữ khoảng cách vì mưa dông làm giảm tầm nhìn."
            if rain_risk or strong_wind:
                return "Đi ô tô nên chú ý tầm nhìn, đường ngập, kẹt xe và lái chậm khi mưa hoặc gió mạnh."
            return "Đi ô tô khá an toàn, vẫn nên tính thêm thời gian nếu tuyến đường dễ kẹt xe."

        if vehicle_type == "bicycle":
            if storm_risk:
                return "Đi xe đạp không nên di chuyển khi có dông hoặc gió mạnh, hãy cân nhắc phương tiện khác."
            if rain_risk or strong_wind:
                return "Đi xe đạp nên dùng áo mưa gọn, tránh đường trơn và rất cẩn thận khi gió mạnh."
            return "Đi xe đạp thuận lợi nếu đường khô ráo, nên mang áo mưa gọn để dự phòng."

        return "Hãy kiểm tra thời tiết sát giờ đi học để chọn phương tiện phù hợp."

    def _build_warnings(
        self,
        *,
        metrics: AdviceMetrics,
        before_class: WeatherSnapshot,
        after_class: WeatherSnapshot,
        local_override: LocalWeatherOverride | None = None,
    ) -> list[str]:
        warnings: list[str] = []

        if local_override is not None and local_override.reported_condition == "rain":
            warnings.append("Mưa cục bộ theo xác nhận tại chỗ của bạn.")
        elif local_override is not None and local_override.reported_condition == "storm":
            warnings.append("Dông/sấm sét theo xác nhận tại chỗ của bạn.")

        if self._rain_probability(before_class) >= RAIN_PROBABILITY_MEDIUM:
            warnings.append("Có khả năng mưa trước giờ học.")

        if metrics.max_precipitation_probability_percent >= RAIN_PROBABILITY_HIGH:
            warnings.append("Khả năng mưa cao trong khung giờ học.")
        elif metrics.max_precipitation_probability_percent >= RAIN_PROBABILITY_MEDIUM:
            warnings.append("Có khả năng mưa trong khung giờ học.")

        if self._rain_probability(after_class) >= RAIN_PROBABILITY_MEDIUM:
            warnings.append("Có khả năng mưa lúc tan học.")

        if metrics.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C:
            warnings.append("Cảm giác nhiệt khá nóng trong buổi học.")

        if metrics.max_wind_speed_kmh >= WIND_SPEED_STRONG_KMH:
            warnings.append("Gió mạnh, cần cẩn thận khi di chuyển.")

        if metrics.max_uv_index >= UV_INDEX_HIGH:
            warnings.append("Chỉ số UV cao trong hoặc gần giờ học.")

        return list(dict.fromkeys(warnings))

    def _build_summary(
        self,
        *,
        metrics: AdviceMetrics,
        score: int,
        start_at: datetime,
        end_at: datetime,
        after_class: WeatherSnapshot,
    ) -> str:
        time_range = f"{self._format_clock(start_at)} - {self._format_clock(end_at)}"
        rain_risk = metrics.max_precipitation_probability_percent >= RAIN_PROBABILITY_MEDIUM
        after_rain = self._rain_probability(after_class) >= RAIN_PROBABILITY_MEDIUM
        hot_weather = metrics.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C

        if rain_risk or after_rain:
            return f"Buổi học {time_range} có khả năng mưa, bạn nên chuẩn bị áo mưa hoặc dù."
        if hot_weather:
            return f"Buổi học {time_range} khá nóng, nên mang nước uống và tránh nắng khi tan học."
        if score >= 80:
            return f"Buổi học {time_range} khá thuận lợi để di chuyển."
        return f"Buổi học {time_range} có một vài điểm cần chú ý trước khi đi học."

    def _build_before_message(self, forecast: WeatherSnapshot) -> str:
        if self._rain_probability(forecast) >= RAIN_PROBABILITY_MEDIUM:
            return "Trước giờ học có khả năng mưa, nên đi sớm và mang áo mưa."
        if forecast.apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C:
            return "Trước giờ học trời khá nóng, nên chuẩn bị nước uống."
        return "Trước giờ học thời tiết khá ổn để di chuyển."

    def _build_during_message(self, metrics: AdviceMetrics, forecasts: list[WeatherSnapshot]) -> str:
        if metrics.max_precipitation_probability_percent >= RAIN_PROBABILITY_MEDIUM:
            return "Trong giờ học có khả năng mưa, nên giữ áo mưa hoặc dù bên mình."
        if metrics.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C:
            return "Trong giờ học nhiệt độ tăng, nên mang nước uống."
        if any(item.wind_speed_kmh >= WIND_SPEED_STRONG_KMH for item in forecasts):
            return "Trong giờ học có gió mạnh, cần chú ý khi di chuyển."
        return "Trong giờ học thời tiết nhìn chung ổn định."

    def _build_after_message(self, forecast: WeatherSnapshot, metrics: AdviceMetrics) -> str:
        if self._rain_probability(forecast) >= RAIN_PROBABILITY_MEDIUM:
            return "Lúc tan học có khả năng mưa, nên chuẩn bị áo mưa khi về."
        if forecast.apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C or metrics.max_uv_index >= UV_INDEX_HIGH:
            return "Lúc tan học có thể nắng nóng hoặc UV cao, nên mang nước và che nắng."
        return "Lúc tan học thời tiết khá thuận lợi."

    def _pick_representative_forecast(self, forecasts: list[WeatherSnapshot]) -> WeatherSnapshot:
        return max(
            forecasts,
            key=lambda item: (
                item.precipitation_probability_percent or 0,
                item.wind_speed_kmh,
                item.apparent_temperature_c,
            ),
        )

    def _to_advice_hourly_forecast(self, item: WeatherSnapshot) -> AdviceHourlyForecast:
        return AdviceHourlyForecast(
            time=item.time,
            temperature_c=item.temperature_c,
            weather_code=item.weather_code,
            precipitation_probability_percent=item.precipitation_probability_percent or 0,
            weather_description=item.weather_description,
            wind_speed_kmh=item.wind_speed_kmh,
            is_day=item.is_day,
        )

    def _rain_probability(self, forecast: WeatherSnapshot) -> int:
        return forecast.precipitation_probability_percent or 0

    def _format_hour_from_snapshot(self, forecast: WeatherSnapshot) -> str:
        return self._format_clock(parse_open_meteo_time(forecast.time))

    def _format_clock(self, value: datetime) -> str:
        return value.strftime("%H:%M")


def _build_student_advice_cache_key(
    request: StudentAdviceRequest,
    provider_name: str,
    local_override: LocalWeatherOverride | None = None,
) -> tuple[object, ...]:
    if request.has_coordinates:
        location_key: tuple[object, ...] = (
            "coordinates",
            round_coordinate_for_cache(request.latitude or 0),
            round_coordinate_for_cache(request.longitude or 0),
        )
    else:
        location_key = ("city", normalize_city_for_cache(request.city or ""))

    return (
        "student-advice",
        *location_key,
        round(request.accuracy_meters or 0),
        str(request.study_date),
        request.start_time.strftime("%H:%M") if request.start_time else "",
        request.end_time.strftime("%H:%M") if request.end_time else "",
        request.vehicle_type,
        provider_name,
        _build_local_override_cache_key(local_override),
    )


def _build_local_override_cache_key(local_override: LocalWeatherOverride | None) -> str:
    if local_override is None:
        return "no-local-override"
    return ":".join(
        [
            local_override.id,
            local_override.reported_condition,
            local_override.intensity or "",
            local_override.expires_at.isoformat(),
        ]
    )
