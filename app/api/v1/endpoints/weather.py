from enum import IntEnum
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_current_user_optional
from app.clients.open_meteo_client import OpenMeteoClient
from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_db
from app.schemas.advice import StudentAdviceRequest, StudentAdviceResponse
from app.schemas.local_weather_report import (
    ClearLocalWeatherReportResponse,
    LocalWeatherReportCreate,
    LocalWeatherReportResponse,
)
from app.schemas.weather import (
    CurrentWeatherResponse,
    DailyForecastResponse,
    HourlyForecastResponse,
    SearchLocationResponse,
)
from app.services.geocoding_service import GeocodingService
from app.services.local_weather_report_service import (
    apply_local_weather_override_to_current,
    create_local_weather_report,
    deactivate_active_local_reports,
    get_active_local_weather_report,
    to_local_weather_override,
)
from app.services.location_display_service import LocationDisplayService
from app.services.student_advice_service import StudentAdviceService
from app.services.weather_cache import AsyncTTLCache
from app.services.weather_service import WeatherService


class ForecastHours(IntEnum):
    SIX = 6
    TWELVE = 12
    TWENTY_FOUR = 24
    FORTY_EIGHT = 48


LocationSourceKind = Literal["city", "coordinates"]


router = APIRouter(prefix="/weather", tags=["weather"])
_open_meteo_cache = AsyncTTLCache()
_weather_report_cache = AsyncTTLCache()
_location_display_service = LocationDisplayService()


def get_open_meteo_cache() -> AsyncTTLCache:
    return _open_meteo_cache


def get_weather_report_cache() -> AsyncTTLCache:
    return _weather_report_cache


def get_location_display_service() -> LocationDisplayService:
    return _location_display_service


def get_open_meteo_client(
    settings: Annotated[Settings, Depends(get_settings)],
    cache: Annotated[AsyncTTLCache, Depends(get_open_meteo_cache)],
) -> OpenMeteoClient:
    return OpenMeteoClient(settings, cache=cache)


def get_geocoding_service(
    client: Annotated[OpenMeteoClient, Depends(get_open_meteo_client)],
) -> GeocodingService:
    return GeocodingService(client)


def get_weather_service(
    geocoding_service: Annotated[GeocodingService, Depends(get_geocoding_service)],
    client: Annotated[OpenMeteoClient, Depends(get_open_meteo_client)],
    cache: Annotated[AsyncTTLCache, Depends(get_weather_report_cache)],
    location_display_service: Annotated[LocationDisplayService, Depends(get_location_display_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WeatherService:
    from app.providers.weather.open_meteo import OpenMeteoProvider
    from app.providers.weather.open_weather import OpenWeatherProvider

    if settings.weather_provider == "openweather":
        active = OpenWeatherProvider(settings)
    else:
        active = OpenMeteoProvider(client)

    fallback = None
    if settings.weather_fallback_provider == "open_meteo":
        if not isinstance(active, OpenMeteoProvider):
            fallback = OpenMeteoProvider(client)

    return WeatherService(
        geocoding_service=geocoding_service,
        active_provider=active,
        fallback_provider=fallback,
        cache=cache,
        location_display_service=location_display_service,
    )


def get_student_advice_service(
    weather_service: Annotated[WeatherService, Depends(get_weather_service)],
    cache: Annotated[AsyncTTLCache, Depends(get_weather_report_cache)],
) -> StudentAdviceService:
    return StudentAdviceService(weather_service, cache=cache)


@router.get("/current", response_model=CurrentWeatherResponse)
async def get_current_weather(
    service: Annotated[WeatherService, Depends(get_weather_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
    city: Annotated[str | None, Query(min_length=1)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    accuracy_meters: Annotated[float | None, Query(ge=0)] = None,
) -> CurrentWeatherResponse:
    source = _resolve_location_source(city, latitude, longitude)
    if source == "coordinates":
        report = await service.get_current_weather_by_coordinates(
            latitude=latitude,  # type: ignore[arg-type]
            longitude=longitude,  # type: ignore[arg-type]
            accuracy_meters=accuracy_meters,
        )
    else:
        report = await service.get_current_weather(city or "")
    if current_user is not None:
        active_report = await get_active_local_weather_report(
            db,
            user_id=current_user.id,
            latitude=report.location.latitude,
            longitude=report.location.longitude,
        )
        report = apply_local_weather_override_to_current(report, to_local_weather_override(active_report))
    else:
        report = apply_local_weather_override_to_current(report, None)
    return CurrentWeatherResponse.from_domain(report)


@router.get("/hourly", response_model=HourlyForecastResponse)
async def get_hourly_forecast(
    service: Annotated[WeatherService, Depends(get_weather_service)],
    city: Annotated[str | None, Query(min_length=1)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    accuracy_meters: Annotated[float | None, Query(ge=0)] = None,
    hours: Annotated[ForecastHours, Query()] = ForecastHours.TWENTY_FOUR,
) -> HourlyForecastResponse:
    source = _resolve_location_source(city, latitude, longitude)
    if source == "coordinates":
        report = await service.get_hourly_forecast_by_coordinates(
            latitude=latitude,  # type: ignore[arg-type]
            longitude=longitude,  # type: ignore[arg-type]
            hours=int(hours),
            accuracy_meters=accuracy_meters,
        )
    else:
        report = await service.get_hourly_forecast(city or "", hours=int(hours))
    return HourlyForecastResponse.from_domain(report)


@router.get("/daily", response_model=DailyForecastResponse)
async def get_daily_forecast(
    service: Annotated[WeatherService, Depends(get_weather_service)],
    city: Annotated[str | None, Query(min_length=1)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    accuracy_meters: Annotated[float | None, Query(ge=0)] = None,
    days: Annotated[int, Query(ge=1, le=7)] = 7,
) -> DailyForecastResponse:
    source = _resolve_location_source(city, latitude, longitude)
    if source == "coordinates":
        report = await service.get_daily_forecast_by_coordinates(
            latitude=latitude,  # type: ignore[arg-type]
            longitude=longitude,  # type: ignore[arg-type]
            days=days,
            accuracy_meters=accuracy_meters,
        )
    else:
        report = await service.get_daily_forecast(city or "", days=days)
    return DailyForecastResponse.from_domain(report)


@router.get("/search-location", response_model=list[SearchLocationResponse])
async def search_location(
    query: str,
    geocoding_service: Annotated[GeocodingService, Depends(get_geocoding_service)],
) -> list[SearchLocationResponse]:
    locations = await geocoding_service.search_locations(query)
    return [
        SearchLocationResponse(
            city=loc.city,
            country=loc.country,
            latitude=loc.latitude,
            longitude=loc.longitude,
            timezone=loc.timezone,
            display_name=loc.display_name or loc.city,
            short_display_name=loc.short_display_name,
            administrative_levels=loc.administrative_levels,
            location_confidence=loc.location_confidence,
            location_provider=loc.location_provider,
        )
        for loc in locations
    ]


@router.post("/local-report", response_model=LocalWeatherReportResponse)
async def create_weather_local_report(
    payload: LocalWeatherReportCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LocalWeatherReportResponse:
    report = await create_local_weather_report(db, user_id=current_user.id, payload=payload)
    return LocalWeatherReportResponse.model_validate(report)


@router.get("/local-report/active", response_model=LocalWeatherReportResponse | None)
async def get_active_weather_local_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> LocalWeatherReportResponse | None:
    source = "none" if latitude is None and longitude is None else _resolve_location_source(None, latitude, longitude)
    report = await get_active_local_weather_report(
        db,
        user_id=current_user.id,
        latitude=latitude if source == "coordinates" else None,
        longitude=longitude if source == "coordinates" else None,
    )
    return LocalWeatherReportResponse.model_validate(report) if report else None


@router.delete("/local-report/active", response_model=ClearLocalWeatherReportResponse)
async def clear_active_weather_local_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ClearLocalWeatherReportResponse:
    cleared_count = await deactivate_active_local_reports(db, user_id=current_user.id)
    return ClearLocalWeatherReportResponse(cleared=cleared_count > 0)


@router.post("/student-advice", response_model=StudentAdviceResponse)
async def get_student_advice(
    request: StudentAdviceRequest,
    service: Annotated[StudentAdviceService, Depends(get_student_advice_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
) -> StudentAdviceResponse:
    local_override = None
    if current_user is not None and request.has_coordinates:
        active_report = await get_active_local_weather_report(
            db,
            user_id=current_user.id,
            latitude=request.latitude,
            longitude=request.longitude,
        )
        local_override = to_local_weather_override(active_report)
    report = await service.get_student_advice(request, local_override=local_override)
    return StudentAdviceResponse.from_domain(report)


def _resolve_location_source(city: str | None, latitude: float | None, longitude: float | None) -> LocationSourceKind:
    has_latitude = latitude is not None
    has_longitude = longitude is not None
    if has_latitude != has_longitude:
        raise HTTPException(
            status_code=422,
            detail="latitude và longitude phải được cung cấp cùng nhau.",
        )
    if has_latitude and has_longitude:
        return "coordinates"
    if city and city.strip():
        return "city"
    raise HTTPException(
        status_code=422,
        detail="Vui lòng cung cấp vị trí hiện tại hoặc tên thành phố.",
    )


@router.get("/debug-location")
async def debug_location(
    latitude: float,
    longitude: float,
    service: Annotated[WeatherService, Depends(get_weather_service)],
    client: Annotated[OpenMeteoClient, Depends(get_open_meteo_client)],
    location_display_service: Annotated[LocationDisplayService, Depends(get_location_display_service)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    if not settings.debug_weather_compare:
        raise HTTPException(status_code=404, detail="Debug endpoint is disabled.")

    from app.models.domain import Location

    # 1. Resolve coordinates
    resolved_loc = await location_display_service.resolve_coordinates(
        latitude=latitude,
        longitude=longitude,
        timezone="auto",
    )

    # 2. Get raw responses from providers
    raw_nominatim = {}
    try:
        raw_nominatim_res = await location_display_service._nominatim_provider.reverse_geocode(latitude, longitude)
        raw_nominatim = {
            "locality": raw_nominatim_res[0],
            "province": raw_nominatim_res[1],
            "api_names": raw_nominatim_res[2],
            "admin_levels": raw_nominatim_res[3],
        }
    except Exception as e:
        raw_nominatim = {"error": str(e)}

    raw_openweather = {}
    try:
        raw_ow_res = await location_display_service._openweather_provider.reverse_geocode(latitude, longitude)
        raw_openweather = {
            "locality": raw_ow_res[0],
            "province": raw_ow_res[1],
            "api_names": raw_ow_res[2],
            "admin_levels": raw_ow_res[3],
        }
    except Exception as e:
        raw_openweather = {"error": str(e)}

    raw_bigdatacloud = {}
    try:
        raw_bdc_res = await location_display_service._bigdatacloud_provider.reverse_geocode(latitude, longitude)
        raw_bigdatacloud = {
            "locality": raw_bdc_res[0],
            "province": raw_bdc_res[1],
            "api_names": raw_bdc_res[2],
            "admin_levels": raw_bdc_res[3],
        }
    except Exception as e:
        raw_bigdatacloud = {"error": str(e)}

    # 3. Call actual weather endpoint via service (which handles fallback automatically)
    report = await service.get_current_weather_by_coordinates(latitude=latitude, longitude=longitude)

    # 4. Fetch from OWM directly
    from app.providers.weather.open_weather import OpenWeatherProvider

    ow_weather = {}
    ow_provider = OpenWeatherProvider(settings)
    try:
        loc_obj = Location(
            city=resolved_loc.city,
            country=resolved_loc.country,
            latitude=latitude,
            longitude=longitude,
            timezone=resolved_loc.timezone,
        )
        ow_rep = await ow_provider.get_current_weather(loc_obj)
        ow_weather = {
            "temperature_c": ow_rep.current.temperature_c,
            "weather_description": ow_rep.current.weather_description,
            "weather_code": ow_rep.current.weather_code,
            "time": ow_rep.current.time,
        }
    except Exception as e:
        ow_weather = {"error": str(e)}

    # 5. Fetch from OpenMeteo directly
    from app.providers.weather.open_meteo import OpenMeteoProvider

    om_weather = {}
    om_provider = OpenMeteoProvider(client)
    try:
        loc_obj = Location(
            city=resolved_loc.city,
            country=resolved_loc.country,
            latitude=latitude,
            longitude=longitude,
            timezone=resolved_loc.timezone,
        )
        om_rep = await om_provider.get_current_weather(loc_obj)
        om_weather = {
            "temperature_c": om_rep.current.temperature_c,
            "weather_description": om_rep.current.weather_description,
            "weather_code": om_rep.current.weather_code,
            "time": om_rep.current.time,
        }
    except Exception as e:
        om_weather = {"error": str(e)}

    # 6. Build warnings
    warnings = []
    if resolved_loc.location_confidence in ("uncertain", "coordinates"):
        warnings.append("Location confidence is low")

    if "temperature_c" in ow_weather and "temperature_c" in om_weather:
        has_ow_temp = isinstance(ow_weather.get("temperature_c"), (int, float))
        has_om_temp = isinstance(om_weather.get("temperature_c"), (int, float))
        diff = (
            float(ow_weather["temperature_c"]) - float(om_weather["temperature_c"])
            if has_ow_temp and has_om_temp
            else 0.0
        )
        if abs(diff) >= 3.0:
            warnings.append("Provider values differ significantly")

    return {
        "input": {"latitude": latitude, "longitude": longitude},
        "location_resolution": {
            "selected_display_name": resolved_loc.display_name,
            "short_display_name": resolved_loc.short_display_name,
            "administrative_levels": resolved_loc.administrative_levels,
            "location_confidence": resolved_loc.location_confidence,
            "provider": resolved_loc.location_provider,
            "needs_user_confirmation": resolved_loc.needs_user_confirmation,
            "confidence_reasoning": (
                "Location confidence is low: needs user confirmation"
                if resolved_loc.needs_user_confirmation
                else "Location confidence is high: exact/commune/district match"
            ),
            "candidates": resolved_loc.location_candidates or [],
        },
        "raw_provider_responses": {
            "nominatim": raw_nominatim,
            "openweather": raw_openweather,
            "bigdatacloud": raw_bigdatacloud,
        },
        "weather": {
            "active_provider": settings.weather_provider,
            "fallback_provider_used": report.fallback_provider_used,
            "openweather": ow_weather,
            "open_meteo": om_weather,
        },
        "warnings": warnings,
    }
