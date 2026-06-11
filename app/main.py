import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    CityNotFoundError,
    InvalidWeatherDataError,
    WeatherProviderError,
)

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
async def root_health_check():
    from app.core.constants import APP_SERVICE_SLUG
    return {"status": "ok", "service": APP_SERVICE_SLUG}



async def run_notification_worker():
    logger.info("Starting background notification worker loop...")
    await asyncio.sleep(5)  # Let the app initialize first

    from app.clients.open_meteo_client import OpenMeteoClient
    from app.db.session import async_session
    from app.providers.weather.open_meteo import OpenMeteoProvider
    from app.providers.weather.open_weather import OpenWeatherProvider
    from app.services.geocoding_service import GeocodingService
    from app.services.location_display_service import LocationDisplayService
    from app.services.notification_service import NotificationService
    from app.services.student_advice_service import StudentAdviceService
    from app.services.weather_cache import AsyncTTLCache
    from app.services.weather_service import WeatherService

    client = OpenMeteoClient(settings, cache=AsyncTTLCache())
    geo = GeocodingService(client)
    loc_display = LocationDisplayService()

    if settings.weather_provider == "openweather":
        active = OpenWeatherProvider(settings)
    else:
        active = OpenMeteoProvider(client)

    fallback = None
    if settings.weather_fallback_provider == "open_meteo" and not isinstance(active, OpenMeteoProvider):
        fallback = OpenMeteoProvider(client)

    weather_service = WeatherService(
        geocoding_service=geo,
        active_provider=active,
        fallback_provider=fallback,
        cache=AsyncTTLCache(),
        location_display_service=loc_display
    )

    advice_service = StudentAdviceService(weather_service, cache=AsyncTTLCache())
    notification_service = NotificationService(advice_service)

    while True:
        try:
            async with async_session() as db:
                scheduled_count = await notification_service.check_and_schedule_study_notifications(db)
                if scheduled_count > 0:
                    logger.info("Scheduled %d new study notifications.", scheduled_count)

                sent_count = await notification_service.send_pending_notifications(db)
                if sent_count > 0:
                    logger.info("Dispatched %d notifications.", sent_count)
        except Exception as e:
            logger.exception("Error in background notification worker: %s", e)

        await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_notification_worker())



@app.exception_handler(CityNotFoundError)
async def city_not_found_handler(_: Request, exc: CityNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(WeatherProviderError)
async def weather_provider_handler(_: Request, exc: WeatherProviderError) -> JSONResponse:
    logger.warning("Weather provider error: %s", exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.public_message},
    )


@app.exception_handler(InvalidWeatherDataError)
async def invalid_weather_data_handler(_: Request, exc: InvalidWeatherDataError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unexpected backend error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Lỗi hệ thống không mong muốn."})
