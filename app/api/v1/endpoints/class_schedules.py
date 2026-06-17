from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.endpoints.weather import get_weather_service
from app.db.models import User
from app.db.session import get_db
from app.models.domain import LocalWeatherOverride
from app.schemas.weekly_class_schedule import (
    ClassScheduleForecastResponse,
    ClassScheduleOccurrenceResponse,
    ClassScheduleTimelineAdviceResponse,
    DeleteWeeklyClassScheduleResponse,
    WeeklyClassScheduleCreate,
    WeeklyClassScheduleResponse,
    WeeklyClassScheduleUpdate,
)
from app.services.class_schedule_forecast_service import ClassScheduleForecastResult, ClassScheduleForecastService
from app.services.local_weather_report_service import get_active_local_weather_report, to_local_weather_override
from app.services.schedule_occurrence_service import ScheduleOccurrence
from app.services.weather_service import WeatherService
from app.services.weekly_schedule_service import WeeklyScheduleService

router = APIRouter(prefix="/class-schedules", tags=["class-schedules"])


def get_weekly_schedule_service() -> WeeklyScheduleService:
    return WeeklyScheduleService()


def get_class_schedule_forecast_service(
    weather_service: Annotated[WeatherService, Depends(get_weather_service)],
) -> ClassScheduleForecastService:
    return ClassScheduleForecastService(weather_service)


@router.post("", response_model=WeeklyClassScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_weekly_schedule(
    payload: WeeklyClassScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: WeeklyScheduleService = Depends(get_weekly_schedule_service),
):
    return await service.create_weekly_schedule(db, current_user, payload)


@router.get("", response_model=list[WeeklyClassScheduleResponse])
async def list_weekly_schedules(
    include_inactive: Annotated[bool, Query()] = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: WeeklyScheduleService = Depends(get_weekly_schedule_service),
):
    return await service.list_weekly_schedules(db, current_user.id, include_inactive=include_inactive)


@router.get("/upcoming-forecasts", response_model=list[ClassScheduleForecastResponse])
async def get_upcoming_forecasts(
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    schedule_service: WeeklyScheduleService = Depends(get_weekly_schedule_service),
    forecast_service: ClassScheduleForecastService = Depends(get_class_schedule_forecast_service),
):
    schedules = await schedule_service.list_weekly_schedules(db, current_user.id)
    active_schedules = [schedule for schedule in schedules if schedule.is_active]
    local_overrides = {
        str(schedule.id): await _get_local_override_for_schedule(db, current_user, schedule)
        for schedule in active_schedules
    }
    forecasts = await forecast_service.get_upcoming_forecasts(
        active_schedules,
        limit=limit,
        local_overrides=local_overrides,
    )
    return [_forecast_response(result) for result in forecasts]


@router.get("/{schedule_id}", response_model=WeeklyClassScheduleResponse)
async def get_weekly_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: WeeklyScheduleService = Depends(get_weekly_schedule_service),
):
    schedule = await service.get_weekly_schedule(db, current_user, schedule_id)
    if schedule is None:
        raise _not_found()
    return schedule


@router.patch("/{schedule_id}", response_model=WeeklyClassScheduleResponse)
async def update_weekly_schedule(
    schedule_id: UUID,
    payload: WeeklyClassScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: WeeklyScheduleService = Depends(get_weekly_schedule_service),
):
    try:
        schedule = await service.update_weekly_schedule(db, current_user, schedule_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if schedule is None:
        raise _not_found()
    return schedule


@router.delete("/{schedule_id}", response_model=DeleteWeeklyClassScheduleResponse)
async def delete_weekly_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: WeeklyScheduleService = Depends(get_weekly_schedule_service),
):
    schedule = await service.delete_or_disable_weekly_schedule(db, current_user, schedule_id)
    if schedule is None:
        raise _not_found()
    return DeleteWeeklyClassScheduleResponse(
        message="Đã xóa lịch học",
        schedule_id=schedule.id,
        is_active=schedule.is_active,
    )


@router.get("/{schedule_id}/next-forecast", response_model=ClassScheduleForecastResponse)
async def get_next_forecast(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    schedule_service: WeeklyScheduleService = Depends(get_weekly_schedule_service),
    forecast_service: ClassScheduleForecastService = Depends(get_class_schedule_forecast_service),
):
    schedule = await schedule_service.get_weekly_schedule(db, current_user, schedule_id)
    if schedule is None:
        raise _not_found()
    local_override = await _get_local_override_for_schedule(db, current_user, schedule)
    forecast = await forecast_service.get_forecast_for_next_occurrence(schedule, local_override=local_override)
    return _forecast_response(forecast)


def _forecast_response(result: ClassScheduleForecastResult) -> ClassScheduleForecastResponse:
    occurrence = _occurrence_response(result.next_occurrence)
    advice = result.advice_detail
    return ClassScheduleForecastResponse(
        schedule=WeeklyClassScheduleResponse.model_validate(result.schedule),
        next_occurrence=occurrence,
        next_occurrence_datetime=occurrence.start_datetime if occurrence else None,
        forecast_status=result.forecast_status,
        weather_summary=result.weather_summary,
        risk_level=result.risk_level,  # type: ignore[arg-type]
        recommendation_message=result.recommendation_message,
        weather_code=result.weather_code,
        precipitation_probability_percent=result.precipitation_probability_percent,
        rain_mm=result.rain_mm,
        wind_speed_kmh=result.wind_speed_kmh,
        provider=result.provider,
        study_score=advice.study_score if advice else None,
        commute_score=advice.study_score if advice else None,
        score_label=advice.score_label if advice else None,
        summary_message=advice.summary_message if advice else None,
        weather_warning=advice.weather_warning if advice else None,
        commute_advice=advice.commute_advice if advice else None,
        preparation_items=advice.preparation_items if advice else [],
        reason_factors=advice.reason_factors if advice else [],
        timeline_advice=(
            ClassScheduleTimelineAdviceResponse(
                before_class=advice.timeline_advice.before_class,
                during_class=advice.timeline_advice.during_class,
                after_class=advice.timeline_advice.after_class,
            )
            if advice
            else None
        ),
        vehicle_type=advice.vehicle_type if advice else result.schedule.vehicle_type,
        provider_condition=advice.provider_condition if advice else None,
        effective_condition=advice.effective_condition if advice else None,
        override_source=advice.override_source if advice else None,
        override_expires_at=advice.override_expires_at if advice else None,
        override_report_id=advice.override_report_id if advice else None,
        override_intensity=advice.override_intensity if advice else None,
    )


def _occurrence_response(occurrence: ScheduleOccurrence | None) -> ClassScheduleOccurrenceResponse | None:
    if occurrence is None:
        return None
    return ClassScheduleOccurrenceResponse(
        occurrence_key=occurrence.occurrence_key,
        start_datetime=occurrence.start_at,
        end_datetime=occurrence.end_at,
        status="scheduled",
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Khong tim thay lich hoc hang tuan hoac ban khong co quyen truy cap.",
    )


async def _get_local_override_for_schedule(db: AsyncSession, user: User, schedule) -> LocalWeatherOverride | None:
    if schedule.latitude is None or schedule.longitude is None:
        return None
    report = await get_active_local_weather_report(
        db,
        user_id=user.id,
        latitude=float(schedule.latitude),
        longitude=float(schedule.longitude),
    )
    return to_local_weather_override(report)
