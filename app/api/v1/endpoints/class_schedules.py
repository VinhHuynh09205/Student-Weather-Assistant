from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.endpoints.weather import get_weather_service
from app.db.models import User
from app.db.session import get_db
from app.schemas.weekly_class_schedule import (
    ClassScheduleForecastResponse,
    ClassScheduleOccurrenceResponse,
    DeleteWeeklyClassScheduleResponse,
    WeeklyClassScheduleCreate,
    WeeklyClassScheduleResponse,
    WeeklyClassScheduleUpdate,
)
from app.services.class_schedule_forecast_service import ClassScheduleForecastResult, ClassScheduleForecastService
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
    forecasts = await forecast_service.get_upcoming_forecasts(active_schedules, limit=limit)
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
    forecast = await forecast_service.get_forecast_for_next_occurrence(schedule)
    return _forecast_response(forecast)


def _forecast_response(result: ClassScheduleForecastResult) -> ClassScheduleForecastResponse:
    occurrence = _occurrence_response(result.next_occurrence)
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
