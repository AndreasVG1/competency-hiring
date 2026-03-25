from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.core.settings import get_settings
from app.modules.auth.router import router as auth_router
from app.modules.catalog.router import router as catalog_router
from app.modules.recruiter.router import router as recruiter_router
from app.modules.seeker.router import router as seeker_router

api_router = APIRouter()


@api_router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )


api_router.include_router(auth_router)
api_router.include_router(catalog_router)
api_router.include_router(seeker_router)
api_router.include_router(recruiter_router)
