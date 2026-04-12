from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        error_code = detail.get("error_code") if detail else None
        error_message = detail.get("error_message") if detail else None
        trace_id = detail.get("trace_id") if detail else None

        if not error_code:
            if exc.status_code == 401:
                error_code = "UNAUTHORIZED"
            elif exc.status_code == 404:
                error_code = "NOT_FOUND"
            elif exc.status_code == 409:
                error_code = "CONFLICT"
            elif exc.status_code == 422:
                error_code = "VALIDATION_ERROR"
            elif exc.status_code >= 500:
                error_code = "INTERNAL_ERROR"
            else:
                error_code = "HTTP_ERROR"

        if not error_message:
            if isinstance(exc.detail, str):
                error_message = exc.detail
            else:
                error_message = "요청 처리 중 오류가 발생했습니다."

        extra_fields = {}
        if detail:
            for key, value in detail.items():
                if key not in {"error_code", "error_message", "trace_id"}:
                    extra_fields[key] = value

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": error_code,
                "error_message": error_message,
                "trace_id": trace_id,
                **extra_fields,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        first_error = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first_error.get("loc", []))
        message = first_error.get("msg", "요청 값이 올바르지 않습니다.")
        if location:
            message = f"{location}: {message}"
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "error_message": message,
                "trace_id": None,
            },
        )

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
