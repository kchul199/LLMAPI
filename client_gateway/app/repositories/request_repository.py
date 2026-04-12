from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.request import AnalysisRequestRecord
from app.models.result import AnalysisResultRecord
from app.models.status_history import AnalysisStatusHistoryRecord


class RequestRepository:
    @staticmethod
    def create_request(
        db: Session,
        *,
        request_uid: str,
        source_system: str,
        client_request_id: str,
        trace_id: str,
        mode: str,
        text_masked: str,
        text_sha256: str,
        tasks: list[str],
        target_speakers: str,
        prompt_version: str | None,
    ) -> AnalysisRequestRecord:
        row = AnalysisRequestRecord(
            request_uid=request_uid,
            source_system=source_system,
            client_request_id=client_request_id,
            trace_id=trace_id,
            mode=mode,
            status="RECEIVED",
            text_masked=text_masked,
            text_sha256=text_sha256,
            tasks=tasks,
            target_speakers=target_speakers,
            prompt_version=prompt_version,
            received_at=datetime.utcnow(),
        )
        db.add(row)
        db.flush()

        RequestRepository.add_status_history(db, request_id=row.id, prev_status=None, new_status="RECEIVED")
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def add_status_history(
        db: Session,
        *,
        request_id: int,
        prev_status: str | None,
        new_status: str,
        reason_code: str | None = None,
        reason_message: str | None = None,
        actor: str = "system",
    ) -> None:
        db.add(
            AnalysisStatusHistoryRecord(
                request_id=request_id,
                prev_status=prev_status,
                new_status=new_status,
                reason_code=reason_code,
                reason_message=reason_message,
                actor=actor,
                changed_at=datetime.utcnow(),
            )
        )

    @staticmethod
    def update_status(
        db: Session,
        *,
        request_row: AnalysisRequestRecord,
        new_status: str,
        reason_code: str | None = None,
        reason_message: str | None = None,
    ) -> AnalysisRequestRecord:
        prev_status = request_row.status
        request_row.status = new_status
        request_row.updated_at = datetime.utcnow()

        if new_status == "QUEUED":
            request_row.queued_at = datetime.utcnow()
        elif new_status == "PROCESSING":
            request_row.started_at = datetime.utcnow()
        elif new_status in ("COMPLETED", "FAILED", "TIMEOUT"):
            request_row.completed_at = datetime.utcnow()

        if reason_code:
            request_row.error_code = reason_code
        if reason_message:
            request_row.error_message = reason_message[:500]

        RequestRepository.add_status_history(
            db,
            request_id=request_row.id,
            prev_status=prev_status,
            new_status=new_status,
            reason_code=reason_code,
            reason_message=reason_message,
        )

        db.add(request_row)
        db.commit()
        db.refresh(request_row)
        return request_row

    @staticmethod
    def update_llmapi_meta(db: Session, *, request_row: AnalysisRequestRecord, llmapi_request_id: str | None, llmapi_http_status: int | None) -> None:
        request_row.llmapi_request_id = llmapi_request_id
        request_row.llmapi_http_status = llmapi_http_status
        request_row.updated_at = datetime.utcnow()
        db.add(request_row)
        db.commit()

    @staticmethod
    def increment_retry(db: Session, *, request_row: AnalysisRequestRecord) -> None:
        request_row.retry_count += 1
        request_row.updated_at = datetime.utcnow()
        db.add(request_row)
        db.commit()

    @staticmethod
    def save_result(
        db: Session,
        *,
        request_id: int,
        result_json: dict,
        summary: str | None,
        sentiment: str | None,
        category: str | None,
        total_tokens: int,
        latency_ms: int,
        llm_model: str | None,
        is_fallback: bool,
        prompt_version_applied: str | None,
        result_status: str = "SUCCESS",
    ) -> AnalysisResultRecord:
        existing = db.execute(select(AnalysisResultRecord).where(AnalysisResultRecord.request_id == request_id)).scalar_one_or_none()

        if existing:
            existing.result_status = result_status
            existing.summary = summary
            existing.sentiment = sentiment
            existing.category = category
            existing.result_json = result_json
            existing.usage_total_tokens = total_tokens
            existing.usage_latency_ms = latency_ms
            existing.llm_model = llm_model
            existing.is_fallback = is_fallback
            existing.prompt_version_applied = prompt_version_applied
            row = existing
        else:
            row = AnalysisResultRecord(
                request_id=request_id,
                result_status=result_status,
                summary=summary,
                sentiment=sentiment,
                category=category,
                result_json=result_json,
                usage_total_tokens=total_tokens,
                usage_latency_ms=latency_ms,
                llm_model=llm_model,
                is_fallback=is_fallback,
                prompt_version_applied=prompt_version_applied,
            )
            db.add(row)

        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def find_by_request_uid(db: Session, request_uid: str) -> AnalysisRequestRecord | None:
        return db.execute(select(AnalysisRequestRecord).where(AnalysisRequestRecord.request_uid == request_uid)).scalar_one_or_none()

    @staticmethod
    def find_by_job_id(db: Session, job_id: str) -> AnalysisRequestRecord | None:
        return db.execute(select(AnalysisRequestRecord).where(AnalysisRequestRecord.llmapi_request_id == job_id)).scalar_one_or_none()

    @staticmethod
    def find_by_idempotency_key(db: Session, source_system: str, client_request_id: str) -> AnalysisRequestRecord | None:
        return db.execute(
            select(AnalysisRequestRecord).where(
                and_(
                    AnalysisRequestRecord.source_system == source_system,
                    AnalysisRequestRecord.client_request_id == client_request_id,
                )
            )
        ).scalar_one_or_none()

    @staticmethod
    def list_requests(
        db: Session,
        *,
        source_system: str | None,
        status: str | None,
        from_dt: datetime | None,
        to_dt: datetime | None,
        page: int,
        size: int,
    ) -> tuple[int, list[AnalysisRequestRecord]]:
        conditions = []
        if source_system:
            conditions.append(AnalysisRequestRecord.source_system == source_system)
        if status:
            conditions.append(AnalysisRequestRecord.status == status)
        if from_dt:
            conditions.append(AnalysisRequestRecord.created_at >= from_dt)
        if to_dt:
            conditions.append(AnalysisRequestRecord.created_at <= to_dt)

        query = select(AnalysisRequestRecord)
        count_query = select(func.count(AnalysisRequestRecord.id))

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        total = db.execute(count_query).scalar_one() or 0

        rows = db.execute(
            query.order_by(AnalysisRequestRecord.created_at.desc()).offset((page - 1) * size).limit(size)
        ).scalars().all()

        return int(total), rows

    @staticmethod
    def get_result(db: Session, request_id: int) -> AnalysisResultRecord | None:
        return db.execute(select(AnalysisResultRecord).where(AnalysisResultRecord.request_id == request_id)).scalar_one_or_none()

    @staticmethod
    def get_status_history(db: Session, request_id: int) -> list[AnalysisStatusHistoryRecord]:
        return db.execute(
            select(AnalysisStatusHistoryRecord)
            .where(AnalysisStatusHistoryRecord.request_id == request_id)
            .order_by(AnalysisStatusHistoryRecord.changed_at.asc())
        ).scalars().all()
