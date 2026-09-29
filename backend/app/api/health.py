from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.connectivity import check_database, check_redis

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    details: dict[str, str] | None = None


@router.get("/health", response_model=HealthResponse)
async def health_check() -> JSONResponse:
    settings = get_settings()
    database = await check_database(settings.database_url)
    redis = await check_redis(settings.redis_url)
    healthy = database.status == "ok" and redis.status == "ok"
    response = HealthResponse(
        status="ok" if healthy else "degraded",
        database=database.status,
        redis=redis.status,
        details=None
        if healthy
        else {
            "database": database.detail or "Database connectivity check failed.",
            "redis": redis.detail or "Redis connectivity check failed.",
        },
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )