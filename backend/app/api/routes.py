from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.core.settings import get_settings

api_router = APIRouter()


@api_router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )
