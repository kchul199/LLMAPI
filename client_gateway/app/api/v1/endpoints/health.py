from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health_service import collect_health

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return await collect_health()
