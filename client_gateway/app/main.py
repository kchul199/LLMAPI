from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import init_db
from app.ui.router import router as ui_router

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # For scaffold stage, auto-create tables on startup.
    init_db()
    yield


def create_app() -> FastAPI:
    static_dir = Path(__file__).resolve().parent / "ui" / "static"

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
    )

    app.include_router(v1_router, prefix=settings.API_PREFIX)
    app.include_router(ui_router)
    app.mount("/ui/static", StaticFiles(directory=str(static_dir)), name="ui-static")

    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": f"{settings.API_PREFIX}/docs",
            "ui": "/ui",
        }

    return app


app = create_app()
