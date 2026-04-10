from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal

class AnalysisOptions(BaseModel):
    language: str = "ko"
    prompt_version: str = "v1.0"

class AnalysisRequest(BaseModel):
    request_id: str = Field(..., description="Unique ID for the request", examples=["req_20240410_001"])
    text: str = Field(..., description="Target text for analysis (PII masked)")
    tasks: List[str] = Field(..., description="List of tasks: summary, sentiment, category", examples=[["summary", "sentiment"]])
    target_speakers: Literal["agent", "customer", "both"] = Field(
        default="both", 
        description="Who to analyze: agent, customer, or both"
    )
    options: Optional[AnalysisOptions] = Field(default_factory=AnalysisOptions)

class AnalysisUsage(BaseModel):
    total_tokens: int = 0
    latency_ms: int = 0

class AnalysisResponse(BaseModel):
    request_id: str
    status: str = "success"
    results: Dict[str, Any] = Field(..., description="Results for each requested task")
    usage: AnalysisUsage = Field(default_factory=AnalysisUsage)
    error: Optional[str] = None
