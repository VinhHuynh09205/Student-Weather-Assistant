import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    APPARENT_TEMPERATURE_HOT_C,
    APPARENT_TEMPERATURE_VERY_HOT_C,
    HUMIDITY_HIGH_PERCENT,
    RAIN_PROBABILITY_HIGH,
    RAIN_PROBABILITY_MEDIUM,
    TOTAL_RAIN_HEAVY_MM,
    WIND_SPEED_STRONG_KMH,
)
from app.db.models import Notification, User, UserSettings, WeeklyClassSchedule
from app.models.domain import HourlyForecastReport, LocalWeatherOverride, WeatherSnapshot
from app.services.commute_advice_utils import (
    build_vehicle_commute_advice,
    build_vehicle_preparation_items,
    normalize_vehicle_type,
    score_label,
)
from app.services.local_weather_report_service import apply_local_weather_override_to_hourly, derive_condition
from app.services.schedule_occurrence_service import ScheduleOccurrence, ScheduleOccurrenceService
from app.services.weather_service import WeatherService
from app.utils.time_utils import parse_open_meteo_time

FORECAST_LOOKAHEAD = timedelta(days=5)
FORECAST_NEAREST_TOLERANCE = timedelta(minutes=90)
NOTIFICATION_TYPE = "weekly_class_forecast"
NOTIFICATION_ESCALATION_TYPE = "weekly_class_risk_escalation"

RAIN_CODES = {51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82}
HEAVY_RAIN_CODES = {65, 82}
STORM_CODES = {95, 96, 99}
RISK_ORDER = {"SAFE": 0, "NOTICE": 1, "PREPARE": 2, "DANGER": 3}


@dataclass(frozen=True)
class WeatherRiskEvaluation:
    risk_level: str
    recommendation_message: str
    weather_summary: str | None
    weather_code: int | None
    precipitation_probability_percent: int | None
    rain_mm: float | None
    wind_speed_kmh: float | None
    max_apparent_temperature_c: float
    average_humidity_percent: float
    has_storm: bool


@dataclass(frozen=True)
class WeeklyTimelineAdvice:
    before_class: str
    during_class: str
    after_class: str


@dataclass(frozen=True)
class WeeklyAdviceDetail:
    study_score: int
    score_label: str
    summary_message: str
    weather_warning: str | None
    commute_advice: str
    preparation_items: list[str]
    reason_factors: list[str]
    timeline_advice: WeeklyTimelineAdvice
    vehicle_type: str
    provider_condition: str | None = None
    effective_condition: str | None = None
    override_source: str | None = None
    override_expires_at: datetime | None = None
    override_report_id: str | None = None
    override_intensity: str | None = None


@dataclass(frozen=True)
class ClassScheduleForecastResult:
    schedule: WeeklyClassSchedule
    next_occurrence: ScheduleOccurrence | None
    forecast_status: str
    risk_level: str
    recommendation_message: str
    weather_summary: str | None = None
    weather_code: int | None = None
    precipitation_probability_percent: int | None = None
    rain_mm: float | None = None
    wind_speed_kmh: float | None = None
    provider: str | None = None
    advice_detail: WeeklyAdviceDetail | None = None


class ClassScheduleForecastService:
    def __init__(
        self,
        weather_service: WeatherService,
        occurrence_service: ScheduleOccurrenceService | None = None,
    ) -> None:
        self._weather_service = weather_service
        self._occurrence_service = occurrence_service or ScheduleOccurrenceService()

    def get_next_occurrence(
        self,
        schedule: WeeklyClassSchedule,
        now: datetime | None = None,
        timezone: str | None = None,
    ) -> ScheduleOccurrence | None:
        return self._occurrence_service.get_next_occurrence(schedule, now=now, timezone=timezone)

    def get_upcoming_occurrences(
        self,
        schedule: WeeklyClassSchedule,
        limit: int,
        now: datetime | None = None,
    ) -> list[ScheduleOccurrence]:
        return self._occurrence_service.get_upcoming_occurrences(schedule, limit=limit, now=now)

    async def get_forecast_for_next_occurrence(
        self,
        schedule: WeeklyClassSchedule,
        now: datetime | None = None,
        local_override: LocalWeatherOverride | None = None,
    ) -> ClassScheduleForecastResult:
        occurrence = self.get_next_occurrence(schedule, now=now)
        if occurrence is None:
            status = "expired" if self._occurrence_service.is_expired(schedule, now=now) else "pending"
            return _pending_result(schedule, None, status=status)

        local_now = _coerce_now_for_occurrence(now, occurrence)
        if occurrence.start_at > local_now + FORECAST_LOOKAHEAD:
            return _pending_result(schedule, occurrence)

        try:
            if schedule.latitude is None or schedule.longitude is None:
                if not schedule.location_name:
                    return _pending_result(schedule, occurrence, status="missing_location")
                report = await self._weather_service.get_hourly_forecast(schedule.location_name, hours=72)
            else:
                report = await self._weather_service.get_hourly_forecast_by_coordinates(
                    latitude=schedule.latitude,
                    longitude=schedule.longitude,
                    hours=72,
                )
        except Exception:
            return _pending_result(schedule, occurrence, status="error")

        provider_report = report
        effective_report = apply_local_weather_override_to_hourly(provider_report, local_override, now=local_now)
        provider_forecasts = _select_forecasts_for_occurrence(provider_report, occurrence)
        selected_forecasts = _select_forecasts_for_occurrence(effective_report, occurrence)
        if not selected_forecasts:
            return _pending_result(schedule, occurrence)

        risk = self.evaluate_weather_risk_for_class(schedule, occurrence, selected_forecasts)
        provider_representative = _pick_representative_forecast(provider_forecasts or selected_forecasts)
        effective_representative = _pick_representative_forecast(selected_forecasts)
        advice_detail = _build_advice_detail(
            schedule=schedule,
            occurrence=occurrence,
            risk=risk,
            selected_forecasts=selected_forecasts,
            provider_condition=derive_condition(provider_representative),
            effective_condition=(
                local_override.reported_condition
                if local_override
                else derive_condition(effective_representative)
            ),
            local_override=local_override,
        )
        return ClassScheduleForecastResult(
            schedule=schedule,
            next_occurrence=occurrence,
            forecast_status="available",
            risk_level=risk.risk_level,
            recommendation_message=risk.recommendation_message,
            weather_summary=risk.weather_summary,
            weather_code=risk.weather_code,
            precipitation_probability_percent=risk.precipitation_probability_percent,
            rain_mm=risk.rain_mm,
            wind_speed_kmh=risk.wind_speed_kmh,
            provider=report.provider,
            advice_detail=advice_detail,
        )

    async def get_upcoming_forecasts(
        self,
        schedules: list[WeeklyClassSchedule],
        limit: int = 5,
        now: datetime | None = None,
        local_overrides: dict[str, LocalWeatherOverride | None] | None = None,
    ) -> list[ClassScheduleForecastResult]:
        candidates: list[tuple[ScheduleOccurrence, WeeklyClassSchedule]] = []
        for schedule in schedules:
            occurrence = self.get_next_occurrence(schedule, now=now)
            if occurrence is not None:
                candidates.append((occurrence, schedule))

        candidates.sort(key=lambda item: item[0].start_at)
        results = []
        for _occurrence, schedule in candidates[:limit]:
            local_override = local_overrides.get(str(schedule.id)) if local_overrides else None
            results.append(
                await self.get_forecast_for_next_occurrence(
                    schedule,
                    now=now,
                    local_override=local_override,
                )
            )
        return results

    def evaluate_weather_risk_for_class(
        self,
        schedule: WeeklyClassSchedule,
        occurrence: ScheduleOccurrence,
        forecasts: list[WeatherSnapshot],
    ) -> WeatherRiskEvaluation:
        representative = _pick_representative_forecast(forecasts)
        max_probability = max((item.precipitation_probability_percent or 0 for item in forecasts), default=0)
        total_rain = round(sum(max(item.rain_mm or 0.0, item.precipitation_mm or 0.0) for item in forecasts), 1)
        max_wind = round(max((item.wind_speed_kmh or 0.0 for item in forecasts), default=0.0), 1)
        max_apparent = max((item.apparent_temperature_c or 0.0 for item in forecasts), default=0.0)
        average_humidity = round(
            sum(item.relative_humidity_percent for item in forecasts) / len(forecasts),
            1,
        )

        has_storm = schedule.storm_alert_enabled and any(item.weather_code in STORM_CODES for item in forecasts)
        has_heavy_rain_code = schedule.rain_alert_enabled and any(
            item.weather_code in HEAVY_RAIN_CODES for item in forecasts
        )
        has_rain_code = schedule.rain_alert_enabled and any(item.weather_code in RAIN_CODES for item in forecasts)

        if has_storm or total_rain >= 10.0 or max_wind >= 50:
            risk_level = "DANGER"
        elif (
            (schedule.rain_alert_enabled and (max_probability >= 70 or total_rain >= 2.0 or has_heavy_rain_code))
            or max_wind >= 35
            or max_apparent >= 38
        ):
            risk_level = "PREPARE"
        elif (
            (schedule.rain_alert_enabled and (max_probability >= 50 or total_rain >= 0.2 or has_rain_code))
            or max_wind >= 25
            or max_apparent >= 35
        ):
            risk_level = "NOTICE"
        else:
            risk_level = "SAFE"

        return WeatherRiskEvaluation(
            risk_level=risk_level,
            recommendation_message=_build_recommendation(schedule, occurrence, risk_level, has_storm),
            weather_summary=representative.weather_description,
            weather_code=representative.weather_code,
            precipitation_probability_percent=max_probability,
            rain_mm=total_rain,
            wind_speed_kmh=max_wind,
            max_apparent_temperature_c=round(max_apparent, 1),
            average_humidity_percent=average_humidity,
            has_storm=has_storm,
        )

    async def ensure_forecast_notification(
        self,
        db: AsyncSession,
        user: User,
        forecast: ClassScheduleForecastResult,
        now: datetime | None = None,
    ) -> int:
        if forecast.forecast_status != "available" or forecast.next_occurrence is None:
            return 0
        if forecast.risk_level == "SAFE":
            return 0

        settings_result = await db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
        user_settings = settings_result.scalars().first()
        if not user_settings or not user_settings.notification_enabled:
            return 0

        send_at = forecast.next_occurrence.start_at - timedelta(
            minutes=forecast.schedule.notify_before_minutes,
        )
        local_now = _coerce_now_for_occurrence(now, forecast.next_occurrence)
        if send_at < local_now:
            send_at = local_now
        send_at_utc = send_at.astimezone(UTC).replace(tzinfo=None)

        title = f"Class weather: {forecast.schedule.subject_name}"
        message = forecast.recommendation_message
        content_hash = hashlib.sha256(f"{title}|{message}|{forecast.risk_level}".encode()).hexdigest()
        channels = ["email"] if user.email else ["in_app", "browser"]
        created_count = 0

        for channel in channels:
            existing_result = await db.execute(
                select(Notification)
                .where(Notification.user_id == user.id)
                .where(Notification.occurrence_key == forecast.next_occurrence.occurrence_key)
                .where(Notification.channel == channel)
                .where(Notification.type.in_([NOTIFICATION_TYPE, NOTIFICATION_ESCALATION_TYPE]))
            )
            existing_notifications = list(existing_result.scalars().all())
            if _should_skip_notification(existing_notifications, forecast.risk_level, content_hash):
                continue

            notification_type = (
                NOTIFICATION_ESCALATION_TYPE
                if existing_notifications and forecast.risk_level == "DANGER"
                else NOTIFICATION_TYPE
            )
            db.add(
                Notification(
                    user_id=user.id,
                    type=notification_type,
                    title=title,
                    message=message,
                    channel=channel,
                    status="pending",
                    scheduled_for=send_at_utc,
                    occurrence_key=forecast.next_occurrence.occurrence_key,
                    risk_level=forecast.risk_level,
                    content_hash=content_hash,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )
            created_count += 1

        if created_count:
            await db.commit()
        return created_count


def _pending_result(
    schedule: WeeklyClassSchedule,
    occurrence: ScheduleOccurrence | None,
    *,
    status: str = "pending",
) -> ClassScheduleForecastResult:
    messages = {
        "pending": "Lịch đã được lưu. Dự báo sẽ được cập nhật khi gần đến ngày học.",
        "expired": "Lịch học đã hết thời gian học kỳ.",
        "missing_location": "Cần có địa điểm hoặc tọa độ để lấy dự báo.",
        "unavailable": "Chưa có dữ liệu dự báo phù hợp cho buổi học này.",
        "error": "Chưa thể tải dự báo cho buổi học này, nhưng lịch vẫn đã được lưu.",
    }
    pending_score = 50 if status == "error" else 70
    return ClassScheduleForecastResult(
        schedule=schedule,
        next_occurrence=occurrence,
        forecast_status=status,
        risk_level="SAFE",
        recommendation_message=messages.get(status, messages["pending"]),
        advice_detail=WeeklyAdviceDetail(
            study_score=pending_score,
            score_label=score_label(pending_score),
            summary_message=messages.get(status, messages["pending"]),
            weather_warning=None if status == "pending" else messages.get(status, messages["pending"]),
            commute_advice="Bạn có thể lưu lịch trước. Hệ thống sẽ tự cập nhật lời khuyên khi có dự báo phù hợp.",
            preparation_items=["Kiểm tra lại thời tiết trước khi xuất phát"],
            reason_factors=["Dữ liệu dự báo cho khung giờ này chưa sẵn sàng"],
            timeline_advice=WeeklyTimelineAdvice(
                before_class="Theo dõi lại dự báo khi gần đến giờ học.",
                during_class="Lịch học vẫn được giữ trong hệ thống.",
                after_class="Kiểm tra dự báo trước khi ra về nếu thời tiết thay đổi.",
            ),
            vehicle_type=normalize_vehicle_type(getattr(schedule, "vehicle_type", None)),
        ),
    )


def _select_forecasts_for_occurrence(
    report: HourlyForecastReport,
    occurrence: ScheduleOccurrence,
) -> list[WeatherSnapshot]:
    class_start = occurrence.start_at.replace(tzinfo=None)
    class_end = occurrence.end_at.replace(tzinfo=None)
    expanded_start = class_start - timedelta(minutes=45)
    expanded_end = class_end + timedelta(minutes=45)

    expanded = [
        item
        for item in report.hourly
        if expanded_start <= _parse_snapshot_time(item) <= expanded_end
    ]
    if expanded:
        return expanded

    midpoint = class_start + (class_end - class_start) / 2
    nearest = min(
        report.hourly,
        key=lambda item: abs(_parse_snapshot_time(item) - midpoint),
        default=None,
    )
    if nearest is None:
        return []
    if abs(_parse_snapshot_time(nearest) - midpoint) <= FORECAST_NEAREST_TOLERANCE:
        return [nearest]
    return []


def _pick_representative_forecast(forecasts: list[WeatherSnapshot]) -> WeatherSnapshot:
    return max(
        forecasts,
        key=lambda item: (
            1 if item.weather_code in STORM_CODES else 0,
            1 if item.weather_code in RAIN_CODES else 0,
            item.precipitation_probability_percent or 0,
            max(item.rain_mm or 0.0, item.precipitation_mm or 0.0),
            item.wind_speed_kmh,
            item.apparent_temperature_c,
        ),
    )


def _build_advice_detail(
    *,
    schedule: WeeklyClassSchedule,
    occurrence: ScheduleOccurrence,
    risk: WeatherRiskEvaluation,
    selected_forecasts: list[WeatherSnapshot],
    provider_condition: str | None,
    effective_condition: str | None,
    local_override: LocalWeatherOverride | None,
) -> WeeklyAdviceDetail:
    vehicle_type = normalize_vehicle_type(getattr(schedule, "vehicle_type", None))
    storm_risk = risk.has_storm
    rain_risk = bool(
        (risk.precipitation_probability_percent or 0) >= RAIN_PROBABILITY_MEDIUM
        or (risk.rain_mm or 0) >= 0.2
        or effective_condition == "rain"
        or effective_condition == "storm"
    )
    strong_wind = (risk.wind_speed_kmh or 0) >= WIND_SPEED_STRONG_KMH
    hot_weather = risk.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C
    score = _calculate_weekly_score(
        schedule=schedule,
        risk=risk,
        vehicle_type=vehicle_type,
        local_override=local_override,
    )

    weather_warning = _build_weather_warning(risk, local_override)
    commute_advice = build_vehicle_commute_advice(
        vehicle_type=vehicle_type,
        rain_risk=rain_risk,
        strong_wind=strong_wind,
        hot_weather=hot_weather,
        storm_risk=storm_risk,
    )
    reason_factors = _build_reason_factors(
        risk=risk,
        selected_forecasts=selected_forecasts,
        local_override=local_override,
        schedule=schedule,
    )

    return WeeklyAdviceDetail(
        study_score=score,
        score_label=score_label(score),
        summary_message=_build_summary_message(
            schedule=schedule,
            occurrence=occurrence,
            risk=risk,
            weather_summary=risk.weather_summary,
            local_override=local_override,
        ),
        weather_warning=weather_warning,
        commute_advice=commute_advice,
        preparation_items=build_vehicle_preparation_items(
            vehicle_type=vehicle_type,
            rain_risk=rain_risk,
            strong_wind=strong_wind,
            hot_weather=hot_weather,
            storm_risk=storm_risk,
        ),
        reason_factors=reason_factors,
        timeline_advice=_build_timeline_advice(risk=risk, local_override=local_override),
        vehicle_type=vehicle_type,
        provider_condition=provider_condition,
        effective_condition=effective_condition,
        override_source=local_override.source if local_override else None,
        override_expires_at=local_override.expires_at if local_override else None,
        override_report_id=local_override.id if local_override else None,
        override_intensity=local_override.intensity if local_override else None,
    )


def _calculate_weekly_score(
    *,
    schedule: WeeklyClassSchedule,
    risk: WeatherRiskEvaluation,
    vehicle_type: str,
    local_override: LocalWeatherOverride | None,
) -> int:
    score = 100
    probability = risk.precipitation_probability_percent or 0
    rain_mm = risk.rain_mm or 0.0
    wind = risk.wind_speed_kmh or 0.0

    if probability >= RAIN_PROBABILITY_HIGH:
        score -= 25
    elif probability >= RAIN_PROBABILITY_MEDIUM:
        score -= 15

    if rain_mm >= 10:
        score -= 25
    elif rain_mm >= TOTAL_RAIN_HEAVY_MM:
        score -= 18
    elif rain_mm >= 2:
        score -= 12
    elif rain_mm >= 0.2:
        score -= 6

    if risk.has_storm:
        score -= 35
    if wind >= 50:
        score -= 25
    elif wind >= WIND_SPEED_STRONG_KMH:
        score -= 15
    elif wind >= 25:
        score -= 8

    if risk.max_apparent_temperature_c >= APPARENT_TEMPERATURE_VERY_HOT_C:
        score -= 15
    elif risk.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C:
        score -= 8

    if risk.average_humidity_percent >= HUMIDITY_HIGH_PERCENT:
        score -= 7

    local_condition = local_override.reported_condition if local_override else None
    if local_condition == "storm":
        score -= 30
    elif local_condition == "rain":
        score -= 15

    rain_risk = probability >= RAIN_PROBABILITY_MEDIUM or rain_mm >= 0.2 or local_condition in {"rain", "storm"}
    if vehicle_type in {"motorbike", "bicycle"} and (rain_risk or wind >= 25):
        score -= 8
    elif vehicle_type == "walking" and rain_risk:
        score -= 10
    elif vehicle_type == "bus" and rain_risk:
        score -= 4
    elif vehicle_type == "car" and rain_mm >= 5:
        score -= 4

    if rain_risk and (6 <= schedule.start_time.hour <= 8 or 16 <= schedule.end_time.hour <= 19):
        score -= 5

    return min(100, max(0, score))


def _build_summary_message(
    *,
    schedule: WeeklyClassSchedule,
    occurrence: ScheduleOccurrence,
    risk: WeatherRiskEvaluation,
    weather_summary: str | None,
    local_override: LocalWeatherOverride | None,
) -> str:
    time_range = f"{occurrence.start_at.strftime('%H:%M')}–{occurrence.end_at.strftime('%H:%M')}"
    day_label = _day_label(schedule.day_of_week)
    weather_text = weather_summary or "thời tiết sẽ được cập nhật gần giờ học"
    base = f"Buổi học {schedule.subject_name} diễn ra lúc {time_range} {day_label}."

    if local_override and local_override.reported_condition == "rain":
        return f"{base} Theo xác nhận thời tiết tại chỗ của bạn, khu vực đang mưa nên cần chuẩn bị chống mưa."
    if local_override and local_override.reported_condition == "storm":
        return f"{base} Theo xác nhận thời tiết tại chỗ của bạn, khu vực có dông nên cần ưu tiên an toàn."
    if risk.has_storm:
        return f"{base} Dự báo gần giờ học có dấu hiệu dông hoặc thời tiết nguy hiểm."
    if (risk.precipitation_probability_percent or 0) >= RAIN_PROBABILITY_MEDIUM or (risk.rain_mm or 0) >= 0.2:
        return f"{base} Thời tiết gần giờ học có {weather_text.lower()} và có khả năng mưa cục bộ."
    if risk.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C:
        return f"{base} Thời tiết khá nóng, nên chuẩn bị nước uống và tránh nắng khi di chuyển."
    return f"{base} Thời tiết nhìn chung thuận lợi, vẫn nên kiểm tra lại trước khi xuất phát."


def _build_weather_warning(
    risk: WeatherRiskEvaluation,
    local_override: LocalWeatherOverride | None,
) -> str | None:
    if local_override and local_override.reported_condition == "rain":
        return "Theo xác nhận thời tiết tại chỗ của bạn, khu vực đang mưa."
    if local_override and local_override.reported_condition == "storm":
        return "Theo xác nhận thời tiết tại chỗ của bạn, khu vực có dông/sấm sét."
    if risk.has_storm:
        return "Có tín hiệu dông hoặc thời tiết nguy hiểm gần giờ học."
    if (risk.rain_mm or 0) >= TOTAL_RAIN_HEAVY_MM:
        return "Có khả năng mưa vừa đến mưa lớn trong khung giờ học."
    if (risk.precipitation_probability_percent or 0) >= RAIN_PROBABILITY_MEDIUM or (risk.rain_mm or 0) >= 0.2:
        return "Có khả năng mưa hoặc thời tiết xấu gần giờ học."
    if (risk.wind_speed_kmh or 0) >= WIND_SPEED_STRONG_KMH:
        return "Gió mạnh có thể ảnh hưởng việc di chuyển."
    if risk.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C:
        return "Cảm giác nhiệt khá nóng, cần chuẩn bị nước uống."
    return None


def _build_reason_factors(
    *,
    risk: WeatherRiskEvaluation,
    selected_forecasts: list[WeatherSnapshot],
    local_override: LocalWeatherOverride | None,
    schedule: WeeklyClassSchedule,
) -> list[str]:
    reasons: list[str] = []
    if local_override and local_override.reported_condition == "rain":
        reasons.append("Người dùng xác nhận đang mưa tại chỗ")
    elif local_override and local_override.reported_condition == "storm":
        reasons.append("Người dùng xác nhận có dông tại chỗ")

    if any((item.cloud_cover_percent or 0) >= 80 for item in selected_forecasts):
        reasons.append("Mây che phủ cao")
    if risk.average_humidity_percent >= HUMIDITY_HIGH_PERCENT:
        reasons.append("Độ ẩm cao")
    if (risk.precipitation_probability_percent or 0) >= RAIN_PROBABILITY_MEDIUM:
        reasons.append("Có xác suất mưa gần giờ học")
    if (risk.rain_mm or 0) > 0:
        reasons.append("Dự báo có lượng mưa trong khung giờ học")
    if risk.has_storm:
        reasons.append("Có mã thời tiết dông từ nhà cung cấp")
    if (risk.wind_speed_kmh or 0) >= WIND_SPEED_STRONG_KMH:
        reasons.append("Gió mạnh có thể ảnh hưởng di chuyển")
    if risk.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C:
        reasons.append("Cảm giác nhiệt cao")
    if 6 <= schedule.start_time.hour <= 8 or 16 <= schedule.end_time.hour <= 19:
        reasons.append("Khung giờ đi học dễ gặp đông xe nếu thời tiết xấu")

    if not reasons:
        reasons.append("Không có tín hiệu thời tiết xấu đáng kể trong khung giờ học")
    return list(dict.fromkeys(reasons))


def _build_timeline_advice(
    *,
    risk: WeatherRiskEvaluation,
    local_override: LocalWeatherOverride | None,
) -> WeeklyTimelineAdvice:
    rain_risk = (
        (risk.precipitation_probability_percent or 0) >= RAIN_PROBABILITY_MEDIUM
        or (risk.rain_mm or 0) >= 0.2
        or (local_override is not None and local_override.reported_condition in {"rain", "storm"})
    )

    if local_override and local_override.reported_condition == "storm":
        return WeeklyTimelineAdvice(
            before_class="Kiểm tra lại an toàn trước khi đi; nếu dông mạnh nên cân nhắc chờ thời tiết dịu hơn.",
            during_class="Theo dõi thời tiết nếu có kế hoạch ra ngoài giữa buổi.",
            after_class="Kiểm tra dự báo và tránh ra về ngay khi còn dông/gió mạnh.",
        )
    if rain_risk:
        return WeeklyTimelineAdvice(
            before_class="Chuẩn bị áo mưa hoặc ô trước khi đi học.",
            during_class="Giữ đồ chống mưa bên mình nếu cần ra ngoài giữa buổi.",
            after_class="Kiểm tra lại dự báo trước khi ra về.",
        )
    if risk.max_apparent_temperature_c >= APPARENT_TEMPERATURE_HOT_C:
        return WeeklyTimelineAdvice(
            before_class="Mang nước uống và tránh đi quá lâu dưới nắng.",
            during_class="Bổ sung nước nếu lớp học kéo dài.",
            after_class="Che nắng khi ra về nếu trời còn nóng.",
        )
    return WeeklyTimelineAdvice(
        before_class="Kiểm tra nhanh thời tiết trước khi xuất phát.",
        during_class="Thời tiết trong buổi học nhìn chung ổn định.",
        after_class="Theo dõi lại dự báo nếu có kế hoạch di chuyển xa.",
    )


def _build_recommendation(
    schedule: WeeklyClassSchedule,
    occurrence: ScheduleOccurrence,
    risk_level: str,
    has_storm: bool,
) -> str:
    class_time = occurrence.start_at.strftime("%H:%M")
    day_label = _day_label(schedule.day_of_week)
    prefix = f"Buổi học {schedule.subject_name} lúc {class_time} {day_label}"
    if risk_level == "DANGER" and has_storm:
        return f"{prefix} có tín hiệu dông gần giờ học. Nên đi sớm hoặc cân nhắc an toàn."
    if risk_level == "DANGER":
        return f"{prefix} có rủi ro thời tiết nguy hiểm. Nên kiểm tra lại trước khi đi."
    if risk_level == "PREPARE":
        return f"{prefix} có khả năng mưa hoặc thời tiết xấu. Nên chuẩn bị áo mưa và đi sớm."
    if risk_level == "NOTICE":
        return f"{prefix} có điểm cần lưu ý về thời tiết. Nên chuẩn bị trước khi đi."
    return f"{prefix} hiện không có cảnh báo thời tiết đáng chú ý."


def _day_label(day_of_week: int) -> str:
    if day_of_week == 6:
        return "Chủ nhật"
    return f"Thứ {day_of_week + 2}"


def _parse_snapshot_time(item: WeatherSnapshot) -> datetime:
    parsed = parse_open_meteo_time(item.time)
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed


def _coerce_now_for_occurrence(now: datetime | None, occurrence: ScheduleOccurrence) -> datetime:
    if now is None:
        return datetime.now(occurrence.start_at.tzinfo)
    if now.tzinfo is None:
        return now.replace(tzinfo=occurrence.start_at.tzinfo)
    return now.astimezone(occurrence.start_at.tzinfo)


def _should_skip_notification(
    existing_notifications: list[Notification],
    new_risk_level: str,
    content_hash: str,
) -> bool:
    if not existing_notifications:
        return False
    if any(item.content_hash == content_hash for item in existing_notifications):
        return True
    if new_risk_level != "DANGER":
        return True
    return any(RISK_ORDER.get(item.risk_level or "SAFE", 0) >= RISK_ORDER["DANGER"] for item in existing_notifications)
