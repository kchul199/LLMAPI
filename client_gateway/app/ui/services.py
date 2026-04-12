from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.request import AnalysisRequestRecord
from app.models.result import AnalysisResultRecord
from app.schemas.common import RequestStatus
from app.ui.schemas import DashboardFailedItem, DashboardSummaryResponse


class UIService:
    @staticmethod
    def get_dashboard_summary(db: Session) -> DashboardSummaryResponse:
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_requests_today = (
            db.execute(
                select(func.count(AnalysisRequestRecord.id)).where(AnalysisRequestRecord.created_at >= start_of_day)
            ).scalar_one()
            or 0
        )

        failed_today = (
            db.execute(
                select(func.count(AnalysisRequestRecord.id)).where(
                    AnalysisRequestRecord.created_at >= start_of_day,
                    AnalysisRequestRecord.status.in_([RequestStatus.FAILED.value, RequestStatus.TIMEOUT.value]),
                )
            ).scalar_one()
            or 0
        )

        grouped_status = db.execute(
            select(AnalysisRequestRecord.status, func.count(AnalysisRequestRecord.id))
            .where(AnalysisRequestRecord.created_at >= start_of_day)
            .group_by(AnalysisRequestRecord.status)
        ).all()

        status_counts = {status.value: 0 for status in RequestStatus}
        for status, count in grouped_status:
            if status in status_counts:
                status_counts[status] = int(count)

        avg_latency_raw = db.execute(
            select(func.avg(AnalysisResultRecord.usage_latency_ms))
            .join(AnalysisRequestRecord, AnalysisResultRecord.request_id == AnalysisRequestRecord.id)
            .where(AnalysisRequestRecord.created_at >= start_of_day)
        ).scalar_one_or_none()

        recent_failed_rows = db.execute(
            select(
                AnalysisRequestRecord.request_uid,
                AnalysisRequestRecord.source_system,
                AnalysisRequestRecord.status,
                AnalysisRequestRecord.error_code,
                AnalysisRequestRecord.updated_at,
            )
            .where(AnalysisRequestRecord.status.in_([RequestStatus.FAILED.value, RequestStatus.TIMEOUT.value]))
            .order_by(AnalysisRequestRecord.updated_at.desc())
            .limit(5)
        ).all()

        recent_failed = [
            DashboardFailedItem(
                request_uid=row.request_uid,
                source_system=row.source_system,
                status=row.status,
                error_code=row.error_code,
                updated_at=row.updated_at,
            )
            for row in recent_failed_rows
        ]

        return DashboardSummaryResponse(
            date=now.date().isoformat(),
            total_requests_today=int(total_requests_today),
            failed_today=int(failed_today),
            avg_latency_ms=int(avg_latency_raw) if avg_latency_raw is not None else None,
            status_counts=status_counts,
            recent_failed=recent_failed,
        )
