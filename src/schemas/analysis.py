from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Dict, Optional, Any, Literal

SupportedTask = Literal["summary", "sentiment", "category"]
AsyncJobStatus = Literal["pending", "processing", "completed", "failed"]

class AnalysisOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str = "ko"
    prompt_version: str = "v1.0"

class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique ID for the request",
        examples=["req_20240410_001"],
    )
    text: str = Field(..., min_length=1, description="Target text for analysis (PII masked)")
    tasks: List[SupportedTask] = Field(
        ...,
        min_length=1,
        description="List of tasks: summary, sentiment, category",
        examples=[["summary", "sentiment"]],
    )
    target_speakers: Literal["agent", "customer", "both"] = Field(
        default="both", 
        description="Who to analyze: agent, customer, or both"
    )
    options: Optional[AnalysisOptions] = Field(default_factory=AnalysisOptions)

    @field_validator("request_id", "text", mode="before")
    @classmethod
    def _strip_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("tasks")
    @classmethod
    def _deduplicate_tasks(cls, value: List[SupportedTask]) -> List[SupportedTask]:
        # Preserve order but drop duplicates so the response schema stays stable.
        return list(dict.fromkeys(value))

class AnalysisUsage(BaseModel):
    total_tokens: int = 0
    latency_ms: int = 0
    model: Optional[str] = None

class AnalysisResponse(BaseModel):
    request_id: str
    status: str = "success"
    results: Dict[str, Any] = Field(..., description="Results for each requested task")
    is_fallback: bool = False
    usage: AnalysisUsage = Field(default_factory=AnalysisUsage)
    error: Optional[str] = None

class AsyncAnalyzeEnqueueResponse(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"

class AsyncAnalyzeStatusResponse(BaseModel):
    job_id: str
    request_id: str
    status: AsyncJobStatus
    created_at: str
    updated_at: str
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
