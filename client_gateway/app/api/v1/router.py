from fastapi import APIRouter

from app.api.v1.endpoints import analyze, health

router = APIRouter()
router.include_router(analyze.router, tags=["Analyze", "RequestHistory"])
router.include_router(health.router, tags=["Health"])
