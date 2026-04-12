from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.services.analyze_service import AnalyzeService

router = APIRouter()
service = AnalyzeService()


def verify_auth(x_client_key: str | None = Header(default=None)) -> None:
    # Optional shared-key auth. If AUTH_SHARED_KEY is empty, auth is disabled.
    if not settings.AUTH_SHARED_KEY:
        return
    if x_client_key != settings.AUTH_SHARED_KEY:
        raise HTTPException(status_code=401, detail={"error_code": "UNAUTHORIZED", "error_message": "인증에 실패했습니다."})


@router.post("/analyze", response_model=ClientAnalyzeResponse, dependencies=[Depends(verify_auth)])
async def analyze_sync(request: ClientAnalyzeRequest, db: Session = Depends(get_db)):
    return await service.analyze_sync(db, request)


@router.post("/analyze/async", response_model=ClientAsyncEnqueueResponse, status_code=202, dependencies=[Depends(verify_auth)])
async def analyze_async_enqueue(request: ClientAnalyzeRequest, db: Session = Depends(get_db)):
    return await service.analyze_async_enqueue(db, request)


@router.get("/analyze/async/{job_id}", response_model=ClientAsyncStatusResponse, dependencies=[Depends(verify_auth)])
async def analyze_async_status(job_id: str, db: Session = Depends(get_db)):
    return await service.analyze_async_status(db, job_id)


@router.get("/requests/{request_uid}", response_model=RequestDetailResponse, dependencies=[Depends(verify_auth)])
def get_request_detail(request_uid: str, db: Session = Depends(get_db)):
    return service.get_request_detail(db, request_uid)


@router.get("/requests", response_model=RequestListResponse, dependencies=[Depends(verify_auth)])
def list_requests(
    source_system: str | None = Query(default=None),
    status: RequestStatus | None = Query(default=None),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return service.list_requests(
        db,
        source_system=source_system,
        status=status,
        from_dt=from_dt,
        to_dt=to_dt,
        page=page,
        size=size,
    )
