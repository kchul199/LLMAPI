from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import RequestStatus


class ClientAnalyzeOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = "ko"
    prompt_version: str = "v1.1"


class ClientAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_system: str = Field(..., min_length=1, max_length=64)
    client_request_id: str = Field(..., min_length=1, max_length=100)
    text: str = Field(..., min_length=1)
    tasks: list[Literal["summary", "sentiment", "category"]] = Field(..., min_length=1)
    target_speakers: Literal["agent", "customer", "both"] = "both"
    options: ClientAnalyzeOptions = Field(default_factory=ClientAnalyzeOptions)

    @field_validator("source_system", "client_request_id", "text", mode="before")
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class ClientAnalyzeUsage(BaseModel):
    total_tokens: int = 0
    latency_ms: int = 0


class ClientAnalyzeResponse(BaseModel):
    request_uid: str
    trace_id: str
    status: RequestStatus
    result: dict[str, Any]
    usage: ClientAnalyzeUsage = Field(default_factory=ClientAnalyzeUsage)
    error_code: str | None = None
    error_message: str | None = None


class ClientAsyncEnqueueResponse(BaseModel):
    request_uid: str
    trace_id: str
    job_id: str
    status: RequestStatus
    idempotent_replay: bool = False


class ClientAsyncStatusResponse(BaseModel):
    request_uid: str
    trace_id: str
    job_id: str
    status: RequestStatus
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


class RequestSummaryItem(BaseModel):
    request_uid: str
    source_system: str
    client_request_id: str
    status: RequestStatus
    created_at: datetime
    updated_at: datetime


class RequestListResponse(BaseModel):
    page: int
    size: int
    total: int
    items: list[RequestSummaryItem]


class RequestDetailResponse(BaseModel):
    request: dict[str, Any]
    result: dict[str, Any] | None
    status_history: list[dict[str, Any]]
