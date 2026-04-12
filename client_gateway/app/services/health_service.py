from redis import Redis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.schemas.health import HealthChecks, HealthResponse
from app.services.llmapi_client import LLMAPIClient


async def collect_health() -> HealthResponse:
    mysql_status = "ok"
    redis_status = "skip" if not settings.QUEUE_ENABLED else "ok"
    llmapi_status = "ok"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        mysql_status = "error"

    if settings.QUEUE_ENABLED:
        try:
            redis_client = Redis.from_url(settings.REDIS_URL)
            redis_client.ping()
        except Exception:
            redis_status = "error"

    llmapi_client = LLMAPIClient()
    try:
        status_code, _ = await llmapi_client.health()
        if status_code >= 400:
            llmapi_status = "error"
    except Exception:
        llmapi_status = "error"

    required_checks_ok = mysql_status == "ok" and llmapi_status == "ok"
    queue_check_ok = redis_status in ("ok", "skip")
    overall = "healthy" if required_checks_ok and queue_check_ok else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        checks=HealthChecks(mysql=mysql_status, redis=redis_status, llmapi=llmapi_status),
    )
