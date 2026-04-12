from pydantic import BaseModel


class HealthChecks(BaseModel):
    mysql: str
    redis: str
    llmapi: str


class HealthResponse(BaseModel):
    status: str
    version: str
    checks: HealthChecks
