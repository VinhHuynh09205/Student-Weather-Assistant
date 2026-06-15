import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification, User, UserSettings, WeeklyClassSchedule
from app.models.domain import HourlyForecastReport, WeatherSnapshot
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

        selected_forecasts = _select_forecasts_for_occurrence(report, occurrence)
        if not selected_forecasts:
            return _pending_result(schedule, occurrence)

        risk = self.evaluate_weather_risk_for_class(schedule, occurrence, selected_forecasts)
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
        )

    async def get_upcoming_forecasts(
        self,
        schedules: list[WeeklyClassSchedule],
        limit: int = 5,
        now: datetime | None = None,
    ) -> list[ClassScheduleForecastResult]:
        candidates: list[tuple[ScheduleOccurrence, WeeklyClassSchedule]] = []
        for schedule in schedules:
            occurrence = self.get_next_occurrence(schedule, now=now)
            if occurrence is not None:
                candidates.append((occurrence, schedule))

        candidates.sort(key=lambda item: item[0].start_at)
        results = []
        for _occurrence, schedule in candidates[:limit]:
            results.append(await self.get_forecast_for_next_occurrence(schedule, now=now))
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
        "pending": "Dự báo sẽ được cập nhật khi gần đến ngày học.",
        "expired": "Lịch học đã hết thời gian học kỳ.",
        "missing_location": "Cần có địa điểm hoặc tọa độ để lấy dự báo.",
        "unavailable": "Chưa có dữ liệu dự báo phù hợp cho buổi học này.",
        "error": "Lịch đã được lưu. Dự báo sẽ được cập nhật khi có dữ liệu phù hợp.",
    }
    return ClassScheduleForecastResult(
        schedule=schedule,
        next_occurrence=occurrence,
        forecast_status=status,
        risk_level="SAFE",
        recommendation_message=messages.get(status, messages["pending"]),
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
