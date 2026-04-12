from datetime import datetime

from pydantic import BaseModel


class DashboardFailedItem(BaseModel):
    request_uid: str
    source_system: str
    status: str
    error_code: str | None = None
    updated_at: datetime | None = None


class DashboardSummaryResponse(BaseModel):
    date: str
    total_requests_today: int
    failed_today: int
    avg_latency_ms: int | None = None
    status_counts: dict[str, int]
    recent_failed: list[DashboardFailedItem]
