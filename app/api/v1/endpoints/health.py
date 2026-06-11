from fastapi import APIRouter

from app.core.constants import APP_SERVICE_SLUG
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service=APP_SERVICE_SLUG)
