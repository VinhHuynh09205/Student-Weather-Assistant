from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, notifications, schedules, user_locations, user_settings, weather

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(weather.router)
api_router.include_router(auth.router)
api_router.include_router(user_locations.router)
api_router.include_router(schedules.router)
api_router.include_router(user_settings.router)
api_router.include_router(notifications.router)

