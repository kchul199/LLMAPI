from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analyze import (
    ClientAnalyzeRequest,
    ClientAnalyzeResponse,
    ClientAsyncEnqueueResponse,
    ClientAsyncStatusResponse,
    RequestDetailResponse,
    RequestListResponse,
)
from app.schemas.common import RequestStatus
from app.schemas.health import HealthResponse
from app.services.analyze_service import AnalyzeService
from app.services.health_service import collect_health
from app.ui.schemas import DashboardSummaryResponse
from app.ui.services import UIService

router = APIRouter(prefix="/ui", tags=["UI"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

analyze_service = AnalyzeService()
ui_service = UIService()


def _render(request: Request, template_name: str, **context: object) -> HTMLResponse:
    base_context = {
        "request": request,
        "path": request.url.path,
    }
    base_context.update(context)
    return templates.TemplateResponse(request, template_name, base_context)


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request) -> HTMLResponse:
    return _render(
        request,
        "dashboard.html",
        page_title="Client Gateway Dashboard",
        page_name="dashboard",
    )


@router.get("/test", response_class=HTMLResponse, include_in_schema=False)
async def test_page(request: Request) -> HTMLResponse:
    return _render(
        request,
        "test.html",
        page_title="Analyze Test",
        page_name="test",
    )


@router.get("/history", response_class=HTMLResponse, include_in_schema=False)
async def history_page(request: Request) -> HTMLResponse:
    return _render(
        request,
        "history_list.html",
        page_title="Request History",
        page_name="history",
    )


@router.get("/history/{request_uid}", response_class=HTMLResponse, include_in_schema=False)
async def history_detail_page(request: Request, request_uid: str) -> HTMLResponse:
    return _render(
        request,
        "history_detail.html",
        page_title="Request Detail",
        page_name="history-detail",
        request_uid=request_uid,
    )


@router.get("/api/health", response_model=HealthResponse, include_in_schema=False)
async def ui_health() -> HealthResponse:
    return await collect_health()


@router.get("/api/dashboard-summary", response_model=DashboardSummaryResponse, include_in_schema=False)
def ui_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummaryResponse:
    return ui_service.get_dashboard_summary(db)


@router.post("/api/analyze", response_model=ClientAnalyzeResponse, include_in_schema=False)
async def ui_analyze_sync(payload: ClientAnalyzeRequest, db: Session = Depends(get_db)) -> ClientAnalyzeResponse:
    return await analyze_service.analyze_sync(db, payload)


@router.post("/api/analyze/async", response_model=ClientAsyncEnqueueResponse, status_code=202, include_in_schema=False)
async def ui_analyze_async_enqueue(payload: ClientAnalyzeRequest, db: Session = Depends(get_db)) -> ClientAsyncEnqueueResponse:
    return await analyze_service.analyze_async_enqueue(db, payload)


@router.get("/api/analyze/async/{job_id}", response_model=ClientAsyncStatusResponse, include_in_schema=False)
async def ui_analyze_async_status(job_id: str, db: Session = Depends(get_db)) -> ClientAsyncStatusResponse:
    return await analyze_service.analyze_async_status(db, job_id)


@router.get("/api/requests", response_model=RequestListResponse, include_in_schema=False)
def ui_list_requests(
    source_system: str | None = Query(default=None),
    status: RequestStatus | None = Query(default=None),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> RequestListResponse:
    return analyze_service.list_requests(
        db,
        source_system=source_system,
        status=status,
        from_dt=from_dt,
        to_dt=to_dt,
        page=page,
        size=size,
    )


@router.get("/api/requests/{request_uid}", response_model=RequestDetailResponse, include_in_schema=False)
def ui_get_request_detail(request_uid: str, db: Session = Depends(get_db)) -> RequestDetailResponse:
    return analyze_service.get_request_detail(db, request_uid)
