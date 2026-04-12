import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.core.logging import setup_logging
from src.api.v1.endpoints import router as api_router
from src.services.queue import analysis_queue_service

# 앱 초기화 전 로깅 설정 적용
setup_logging()

@asynccontextmanager
async def lifespan(_: FastAPI):
    await analysis_queue_service.startup()
    try:
        yield
    finally:
        await analysis_queue_service.shutdown()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API 라우터 등록
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.APP_VERSION,
            "capabilities": [
                "Structured Logging",
                "Fail-over",
                "Prompt Auto-Reload",
                "Circuit Breaker",
                "Async Redis Queue",
            ],
        }

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8001, reload=True)
