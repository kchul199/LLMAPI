from enum import Enum

from pydantic import BaseModel


class RequestStatus(str, Enum):
    RECEIVED = "RECEIVED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class ErrorResponse(BaseModel):
    error_code: str
    error_message: str
    trace_id: str | None = None
