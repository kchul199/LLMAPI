import hashlib
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.request_repository import RequestRepository
from app.schemas.analyze import (
    ClientAnalyzeRequest,
    ClientAnalyzeResponse,
    ClientAnalyzeUsage,
    ClientAsyncEnqueueResponse,
    ClientAsyncStatusResponse,
    RequestDetailResponse,
    RequestListResponse,
    RequestSummaryItem,
)
from app.schemas.common import RequestStatus
from app.services.llmapi_client import LLMAPIClient

TERMINAL_STATUSES = {
    RequestStatus.COMPLETED,
    RequestStatus.FAILED,
    RequestStatus.TIMEOUT,
}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _to_llmapi_payload(req: ClientAnalyzeRequest) -> dict[str, Any]:
    return {
        "request_id": req.client_request_id,
        "text": req.text,
        "tasks": req.tasks,
        "target_speakers": req.target_speakers,
        "options": {
            "language": req.options.language,
            "prompt_version": req.options.prompt_version,
        },
    }


def _map_async_status(raw_status: str | None) -> RequestStatus | None:
    normalized = (raw_status or "").strip().lower()
    status_map = {
        "queued": RequestStatus.QUEUED,
        "pending": RequestStatus.QUEUED,
        "processing": RequestStatus.PROCESSING,
        "completed": RequestStatus.COMPLETED,
        "failed": RequestStatus.FAILED,
        "timeout": RequestStatus.TIMEOUT,
    }
    return status_map.get(normalized)


def _coerce_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


def _coerce_result_json(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if payload is None:
        return {}
    return {"raw_result": payload}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_request_status(raw_status: str | None) -> RequestStatus:
    try:
        return RequestStatus(raw_status or RequestStatus.RECEIVED.value)
    except ValueError:
        return RequestStatus.RECEIVED


def _raise_duplicate_client_request(existing_status: str, request_uid: str) -> None:
    raise HTTPException(
        status_code=409,
        detail={
            "error_code": "DUPLICATE_CLIENT_REQUEST_ID",
            "error_message": "동일한 source_system + client_request_id 요청이 이미 존재합니다.",
            "request_uid": request_uid,
            "status": existing_status,
        },
    )


def _build_completed_response(existing: Any, stored_result: Any) -> ClientAnalyzeResponse:
    return ClientAnalyzeResponse(
        request_uid=existing.request_uid,
        trace_id=existing.trace_id,
        status=RequestStatus.COMPLETED,
        result=stored_result.result_json if stored_result else {},
        usage=ClientAnalyzeUsage(
            total_tokens=stored_result.usage_total_tokens if stored_result else 0,
            latency_ms=stored_result.usage_latency_ms if stored_result else 0,
        ),
    )


def _build_async_status_response(request_row: Any, job_id: str, result_row: Any) -> ClientAsyncStatusResponse:
    return ClientAsyncStatusResponse(
        request_uid=request_row.request_uid,
        trace_id=request_row.trace_id,
        job_id=job_id,
        status=_to_request_status(request_row.status),
        result=result_row.result_json if result_row else None,
        error_code=request_row.error_code,
        error_message=request_row.error_message,
    )


class AnalyzeService:
    def __init__(self):
        self.llmapi = LLMAPIClient()

    async def analyze_sync(self, db: Session, req: ClientAnalyzeRequest) -> ClientAnalyzeResponse:
        existing = RequestRepository.find_by_idempotency_key(db, req.source_system, req.client_request_id)
        if existing:
            if existing.status == "COMPLETED":
                stored_result = RequestRepository.get_result(db, existing.id)
                return _build_completed_response(existing, stored_result)
            _raise_duplicate_client_request(existing.status, existing.request_uid)

        request_uid = str(uuid.uuid4())
        trace_id = request_uid

        try:
            request_row = RequestRepository.create_request(
                db,
                request_uid=request_uid,
                source_system=req.source_system,
                client_request_id=req.client_request_id,
                trace_id=trace_id,
                mode="sync",
                text_masked=req.text,
                text_sha256=_hash_text(req.text),
                tasks=list(req.tasks),
                target_speakers=req.target_speakers,
                prompt_version=req.options.prompt_version,
            )
        except IntegrityError:
            db.rollback()
            existing = RequestRepository.find_by_idempotency_key(db, req.source_system, req.client_request_id)
            if existing:
                if existing.status == "COMPLETED":
                    stored_result = RequestRepository.get_result(db, existing.id)
                    return _build_completed_response(existing, stored_result)
                _raise_duplicate_client_request(existing.status, existing.request_uid)
            raise

        RequestRepository.update_status(db, request_row=request_row, new_status="PROCESSING")

        try:
            status_code, payload = await self.llmapi.analyze_sync(_to_llmapi_payload(req))
        except Exception as exc:
            RequestRepository.update_status(
                db,
                request_row=request_row,
                new_status="FAILED",
                reason_code="UPSTREAM_UNAVAILABLE",
                reason_message=str(exc),
            )
            raise HTTPException(status_code=502, detail={"error_code": "UPSTREAM_UNAVAILABLE", "error_message": "LLMAPI 호출 실패"})

        RequestRepository.update_llmapi_meta(db, request_row=request_row, llmapi_request_id=req.client_request_id, llmapi_http_status=status_code)

        if status_code != 200:
            RequestRepository.update_status(
                db,
                request_row=request_row,
                new_status="FAILED",
                reason_code="UPSTREAM_UNAVAILABLE",
                reason_message=str(payload),
            )
            raise HTTPException(status_code=502, detail={"error_code": "UPSTREAM_UNAVAILABLE", "error_message": "LLMAPI 호출 실패"})

        usage = _coerce_dict(payload.get("usage"))
        result_json = _coerce_result_json(payload.get("results"))

        RequestRepository.save_result(
            db,
            request_id=request_row.id,
            result_json=result_json,
            summary=result_json.get("summary"),
            sentiment=result_json.get("sentiment"),
            category=result_json.get("category"),
            total_tokens=_safe_int(usage.get("total_tokens")),
            latency_ms=_safe_int(usage.get("latency_ms")),
            llm_model=usage.get("model"),
            is_fallback=bool(payload.get("is_fallback", False)),
            prompt_version_applied=req.options.prompt_version,
            result_status="SUCCESS",
        )

        RequestRepository.update_status(db, request_row=request_row, new_status="COMPLETED")

        return ClientAnalyzeResponse(
            request_uid=request_row.request_uid,
            trace_id=request_row.trace_id,
            status=RequestStatus.COMPLETED,
            result=result_json,
            usage=ClientAnalyzeUsage(
                total_tokens=_safe_int(usage.get("total_tokens")),
                latency_ms=_safe_int(usage.get("latency_ms")),
            ),
        )

    async def analyze_async_enqueue(self, db: Session, req: ClientAnalyzeRequest) -> ClientAsyncEnqueueResponse:
        existing = RequestRepository.find_by_idempotency_key(db, req.source_system, req.client_request_id)
        if existing:
            if existing.llmapi_request_id:
                return ClientAsyncEnqueueResponse(
                    request_uid=existing.request_uid,
                    trace_id=existing.trace_id,
                    job_id=existing.llmapi_request_id,
                    status=_to_request_status(existing.status),
                    idempotent_replay=True,
                )
            _raise_duplicate_client_request(existing.status, existing.request_uid)

        request_uid = str(uuid.uuid4())
        trace_id = request_uid

        try:
            request_row = RequestRepository.create_request(
                db,
                request_uid=request_uid,
                source_system=req.source_system,
                client_request_id=req.client_request_id,
                trace_id=trace_id,
                mode="async",
                text_masked=req.text,
                text_sha256=_hash_text(req.text),
                tasks=list(req.tasks),
                target_speakers=req.target_speakers,
                prompt_version=req.options.prompt_version,
            )
        except IntegrityError:
            db.rollback()
            existing = RequestRepository.find_by_idempotency_key(db, req.source_system, req.client_request_id)
            if existing and existing.llmapi_request_id:
                return ClientAsyncEnqueueResponse(
                    request_uid=existing.request_uid,
                    trace_id=existing.trace_id,
                    job_id=existing.llmapi_request_id,
                    status=_to_request_status(existing.status),
                    idempotent_replay=True,
                )
            if existing:
                _raise_duplicate_client_request(existing.status, existing.request_uid)
            raise

        try:
            status_code, payload = await self.llmapi.analyze_async_enqueue(_to_llmapi_payload(req))
        except Exception as exc:
            RequestRepository.update_status(
                db,
                request_row=request_row,
                new_status="FAILED",
                reason_code="QUEUE_UNAVAILABLE",
                reason_message=str(exc),
            )
            raise HTTPException(status_code=503, detail={"error_code": "QUEUE_UNAVAILABLE", "error_message": "비동기 큐 사용 불가"})

        if status_code not in (200, 202):
            RequestRepository.update_status(
                db,
                request_row=request_row,
                new_status="FAILED",
                reason_code="QUEUE_UNAVAILABLE",
                reason_message=str(payload),
            )
            raise HTTPException(status_code=503, detail={"error_code": "QUEUE_UNAVAILABLE", "error_message": "비동기 큐 사용 불가"})

        job_id = str(payload.get("job_id", "")).strip()
        if not job_id:
            RequestRepository.update_status(
                db,
                request_row=request_row,
                new_status="FAILED",
                reason_code="UPSTREAM_INVALID_RESPONSE",
                reason_message="LLMAPI 비동기 접수 응답에 job_id가 없습니다.",
            )
            raise HTTPException(
                status_code=502,
                detail={"error_code": "UPSTREAM_INVALID_RESPONSE", "error_message": "LLMAPI 응답 형식이 올바르지 않습니다."},
            )

        RequestRepository.update_llmapi_meta(db, request_row=request_row, llmapi_request_id=job_id, llmapi_http_status=status_code)
        RequestRepository.update_status(db, request_row=request_row, new_status="QUEUED")

        return ClientAsyncEnqueueResponse(
            request_uid=request_row.request_uid,
            trace_id=request_row.trace_id,
            job_id=job_id,
            status=RequestStatus.QUEUED,
            idempotent_replay=False,
        )

    async def analyze_async_status(self, db: Session, job_id: str) -> ClientAsyncStatusResponse:
        request_row = RequestRepository.find_by_job_id(db, job_id)
        if not request_row:
            raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "error_message": "job_id를 찾을 수 없습니다."})

        current_status = _to_request_status(request_row.status)
        if current_status in TERMINAL_STATUSES:
            result_row = RequestRepository.get_result(db, request_row.id)
            return _build_async_status_response(request_row, job_id, result_row)

        try:
            status_code, payload = await self.llmapi.analyze_async_status(job_id)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail={"error_code": "UPSTREAM_UNAVAILABLE", "error_message": f"LLMAPI 상태조회 실패: {exc}"},
            )

        RequestRepository.update_llmapi_meta(db, request_row=request_row, llmapi_request_id=job_id, llmapi_http_status=status_code)

        if status_code == 404:
            request_row = RequestRepository.update_status(
                db,
                request_row=request_row,
                new_status=RequestStatus.FAILED.value,
                reason_code="UPSTREAM_NOT_FOUND",
                reason_message="LLMAPI 비동기 작업(job_id)을 찾을 수 없습니다.",
            )
            result_row = RequestRepository.get_result(db, request_row.id)
            return _build_async_status_response(request_row, job_id, result_row)
        if status_code >= 500:
            raise HTTPException(status_code=502, detail={"error_code": "UPSTREAM_UNAVAILABLE", "error_message": "LLMAPI 상태조회 실패"})
        if status_code >= 400:
            request_row = RequestRepository.update_status(
                db,
                request_row=request_row,
                new_status=RequestStatus.FAILED.value,
                reason_code="UPSTREAM_INVALID_RESPONSE",
                reason_message=f"LLMAPI 상태조회 응답 오류({status_code}): {payload}",
            )
            result_row = RequestRepository.get_result(db, request_row.id)
            return _build_async_status_response(request_row, job_id, result_row)

        mapped_status = _map_async_status(payload.get("status"))
        if mapped_status is None:
            mapped_status = current_status

        if current_status in TERMINAL_STATUSES and mapped_status != current_status:
            mapped_status = current_status

        if mapped_status == RequestStatus.QUEUED and current_status == RequestStatus.RECEIVED:
            request_row = RequestRepository.update_status(db, request_row=request_row, new_status="QUEUED")
            current_status = RequestStatus.QUEUED

        if mapped_status == RequestStatus.PROCESSING and current_status in (RequestStatus.RECEIVED, RequestStatus.QUEUED):
            request_row = RequestRepository.update_status(db, request_row=request_row, new_status="PROCESSING")
            current_status = RequestStatus.PROCESSING

        if mapped_status == RequestStatus.COMPLETED and current_status not in TERMINAL_STATUSES:
            response_payload = _coerce_dict(payload.get("response"))
            result_json = _coerce_result_json(response_payload.get("results"))
            usage = _coerce_dict(response_payload.get("usage"))
            RequestRepository.save_result(
                db,
                request_id=request_row.id,
                result_json=result_json,
                summary=result_json.get("summary"),
                sentiment=result_json.get("sentiment"),
                category=result_json.get("category"),
                total_tokens=_safe_int(usage.get("total_tokens")),
                latency_ms=_safe_int(usage.get("latency_ms")),
                llm_model=usage.get("model"),
                is_fallback=bool(response_payload.get("is_fallback", False)),
                prompt_version_applied=request_row.prompt_version,
                result_status="SUCCESS",
            )
            request_row = RequestRepository.update_status(db, request_row=request_row, new_status="COMPLETED")
            current_status = RequestStatus.COMPLETED

        if mapped_status in (RequestStatus.FAILED, RequestStatus.TIMEOUT) and current_status not in TERMINAL_STATUSES:
            error_message = str(payload.get("error") or payload.get("detail") or "비동기 처리 실패")
            request_row = RequestRepository.update_status(
                db,
                request_row=request_row,
                new_status=mapped_status.value,
                reason_code="UPSTREAM_UNAVAILABLE" if mapped_status == RequestStatus.FAILED else "UPSTREAM_TIMEOUT",
                reason_message=error_message,
            )
            current_status = mapped_status

        result_row = RequestRepository.get_result(db, request_row.id)
        return _build_async_status_response(request_row, job_id, result_row)

    def get_request_detail(self, db: Session, request_uid: str) -> RequestDetailResponse:
        request_row = RequestRepository.find_by_request_uid(db, request_uid)
        if not request_row:
            raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "error_message": "요청을 찾을 수 없습니다."})

        result_row = RequestRepository.get_result(db, request_row.id)
        status_rows = RequestRepository.get_status_history(db, request_row.id)

        request_payload = {
            "request_uid": request_row.request_uid,
            "source_system": request_row.source_system,
            "client_request_id": request_row.client_request_id,
            "trace_id": request_row.trace_id,
            "mode": request_row.mode,
            "status": request_row.status,
            "text_masked": request_row.text_masked,
            "tasks": request_row.tasks,
            "target_speakers": request_row.target_speakers,
            "prompt_version": request_row.prompt_version,
            "llmapi_request_id": request_row.llmapi_request_id,
            "llmapi_http_status": request_row.llmapi_http_status,
            "error_code": request_row.error_code,
            "error_message": request_row.error_message,
            "created_at": request_row.created_at.isoformat() if request_row.created_at else None,
            "updated_at": request_row.updated_at.isoformat() if request_row.updated_at else None,
        }

        status_history = [
            {
                "prev_status": row.prev_status,
                "new_status": row.new_status,
                "reason_code": row.reason_code,
                "reason_message": row.reason_message,
                "actor": row.actor,
                "changed_at": row.changed_at.isoformat() if row.changed_at else None,
            }
            for row in status_rows
        ]

        return RequestDetailResponse(
            request=request_payload,
            result=result_row.result_json if result_row else None,
            status_history=status_history,
        )

    def list_requests(
        self,
        db: Session,
        *,
        source_system: str | None,
        status: RequestStatus | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
        page: int,
        size: int,
    ) -> RequestListResponse:
        total, rows = RequestRepository.list_requests(
            db,
            source_system=source_system,
            status=status.value if status else None,
            from_dt=from_dt,
            to_dt=to_dt,
            page=page,
            size=size,
        )

        items = [
            RequestSummaryItem(
                request_uid=row.request_uid,
                source_system=row.source_system,
                client_request_id=row.client_request_id,
                status=RequestStatus(row.status),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
        return RequestListResponse(page=page, size=size, total=total, items=items)
