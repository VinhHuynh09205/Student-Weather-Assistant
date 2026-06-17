from dataclasses import replace
from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LocalWeatherReport
from app.models.domain import (
    CurrentWeatherReport,
    HourlyForecastReport,
    LocalWeatherOverride,
    WeatherSnapshot,
)
from app.schemas.local_weather_report import LocalWeatherReportCreate
from app.services.weather_service import RAIN_WEATHER_CODES, STORM_WEATHER_CODES

LOCAL_REPORT_RADIUS_KM = 8.0
LOCAL_REPORT_PAST_TOLERANCE = timedelta(minutes=20)


async def create_local_weather_report(
    db: AsyncSession,
    *,
    user_id: UUID,
    payload: LocalWeatherReportCreate,
) -> LocalWeatherReport:
    now = datetime.utcnow()
    await deactivate_active_local_reports(db, user_id=user_id)
    report = LocalWeatherReport(
        user_id=user_id,
        location_name=payload.location_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        reported_condition=payload.reported_condition,
        intensity=payload.intensity if payload.reported_condition != "no_rain" else None,
        source="user_report",
        is_active=True,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(minutes=payload.expires_in_minutes),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def deactivate_active_local_reports(db: AsyncSession, *, user_id: UUID) -> int:
    result = await db.execute(
        update(LocalWeatherReport)
        .where(LocalWeatherReport.user_id == user_id)
        .where(LocalWeatherReport.is_active.is_(True))
        .values(is_active=False, updated_at=datetime.utcnow())
    )
    await db.commit()
    return int(result.rowcount or 0)


async def get_active_local_weather_report(
    db: AsyncSession,
    *,
    user_id: UUID,
    latitude: float | None = None,
    longitude: float | None = None,
    max_distance_km: float = LOCAL_REPORT_RADIUS_KM,
) -> LocalWeatherReport | None:
    now = datetime.utcnow()
    result = await db.execute(
        select(LocalWeatherReport)
        .where(LocalWeatherReport.user_id == user_id)
        .where(LocalWeatherReport.is_active.is_(True))
        .where(LocalWeatherReport.expires_at > now)
        .order_by(LocalWeatherReport.created_at.desc())
    )
    reports = list(result.scalars().all())
    if latitude is None or longitude is None:
        return reports[0] if reports else None

    for report in reports:
        distance = _distance_km(latitude, longitude, float(report.latitude), float(report.longitude))
        if distance <= max_distance_km:
            return report
    return None


def to_local_weather_override(report: LocalWeatherReport | None) -> LocalWeatherOverride | None:
    if report is None:
        return None
    return LocalWeatherOverride(
        id=str(report.id),
        user_id=str(report.user_id),
        location_name=report.location_name,
        latitude=float(report.latitude),
        longitude=float(report.longitude),
        reported_condition=report.reported_condition,
        intensity=report.intensity,
        source=report.source,
        created_at=report.created_at,
        expires_at=report.expires_at,
    )


def apply_local_weather_override_to_current(
    report: CurrentWeatherReport,
    override: LocalWeatherOverride | None,
) -> CurrentWeatherReport:
    provider_condition = derive_condition(report.current)
    provider_weather_code = report.current.weather_code
    provider_weather_description = report.current.weather_description

    if override is None or override.expires_at <= datetime.utcnow():
        return replace(
            report,
            provider_condition=provider_condition,
            effective_condition=provider_condition,
            provider_weather_code=provider_weather_code,
            provider_weather_description=provider_weather_description,
        )

    adjusted_current = _apply_override_to_snapshot(report.current, override)
    return replace(
        report,
        current=adjusted_current,
        provider_condition=provider_condition,
        effective_condition=override.reported_condition,
        override_source=override.source,
        override_expires_at=override.expires_at,
        override_report_id=override.id,
        override_intensity=override.intensity,
        provider_weather_code=provider_weather_code,
        provider_weather_description=provider_weather_description,
    )


def apply_local_weather_override_to_hourly(
    report: HourlyForecastReport,
    override: LocalWeatherOverride | None,
    *,
    now: datetime | None = None,
) -> HourlyForecastReport:
    if override is None or _as_naive_datetime(override.expires_at) <= datetime.utcnow():
        return report

    current_time = now or datetime.utcnow()
    hourly = [
        _apply_override_to_snapshot(item, override)
        if _is_within_override_window(item, override, current_time)
        else item
        for item in report.hourly
    ]
    return replace(report, hourly=hourly)


def derive_condition(snapshot: WeatherSnapshot) -> str:
    if snapshot.weather_code in STORM_WEATHER_CODES:
        return "storm"
    if snapshot.weather_code in RAIN_WEATHER_CODES:
        return "rain"
    if max(snapshot.rain_mm or 0.0, snapshot.precipitation_mm or 0.0) > 0:
        return "rain"
    if (snapshot.precipitation_probability_percent or 0) >= 70:
        return "rain"
    return "cloudy" if snapshot.weather_code == 3 else "clear"


def _apply_override_to_snapshot(snapshot: WeatherSnapshot, override: LocalWeatherOverride) -> WeatherSnapshot:
    if override.reported_condition == "storm":
        return replace(
            snapshot,
            weather_code=95,
            weather_description="Có dông/sấm sét theo xác nhận tại chỗ của bạn",
            precipitation_probability_percent=max(snapshot.precipitation_probability_percent or 0, 95),
            precipitation_mm=max(snapshot.precipitation_mm or 0.0, _rain_amount_for_intensity(override.intensity)),
            rain_mm=max(snapshot.rain_mm or 0.0, _rain_amount_for_intensity(override.intensity)),
        )

    if override.reported_condition == "rain":
        rain_amount = _rain_amount_for_intensity(override.intensity)
        return replace(
            snapshot,
            weather_code=_rain_code_for_intensity(override.intensity),
            weather_description=_rain_description_for_intensity(override.intensity),
            precipitation_probability_percent=max(snapshot.precipitation_probability_percent or 0, 90),
            precipitation_mm=max(snapshot.precipitation_mm or 0.0, rain_amount),
            rain_mm=max(snapshot.rain_mm or 0.0, rain_amount),
        )

    return replace(
        snapshot,
        weather_code=3,
        weather_description="Không mưa tại vị trí của bạn theo xác nhận tại chỗ",
        precipitation_probability_percent=min(snapshot.precipitation_probability_percent or 0, 20),
        precipitation_mm=0.0,
        rain_mm=0.0,
    )


def _is_within_override_window(
    snapshot: WeatherSnapshot,
    override: LocalWeatherOverride,
    now: datetime,
) -> bool:
    snapshot_time = _parse_weather_time(snapshot.time)
    if snapshot_time is None:
        return False
    created_at = _as_naive_datetime(override.created_at)
    expires_at = _as_naive_datetime(override.expires_at)
    current_time = _as_naive_datetime(now)
    starts_at = max(created_at - LOCAL_REPORT_PAST_TOLERANCE, current_time - LOCAL_REPORT_PAST_TOLERANCE)
    return starts_at <= snapshot_time <= expires_at


def _as_naive_datetime(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _rain_code_for_intensity(intensity: str | None) -> int:
    if intensity == "heavy":
        return 65
    if intensity == "light":
        return 61
    return 63


def _rain_amount_for_intensity(intensity: str | None) -> float:
    if intensity == "heavy":
        return 6.0
    if intensity == "light":
        return 0.7
    return 2.5


def _rain_description_for_intensity(intensity: str | None) -> str:
    if intensity == "heavy":
        return "Đang mưa lớn tại vị trí của bạn"
    if intensity == "light":
        return "Đang mưa nhẹ tại vị trí của bạn"
    return "Đang mưa tại vị trí của bạn"


def _parse_weather_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed


def _distance_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius_km = 6371.0
    d_lat = radians(lat_b - lat_a)
    d_lon = radians(lon_b - lon_a)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat_a)) * cos(radians(lat_b)) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius_km * c
