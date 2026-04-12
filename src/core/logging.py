import logging
import sys

try:
    from pythonjsonlogger import jsonlogger
except ImportError:  # pragma: no cover - optional dependency fallback
    jsonlogger = None

from src.core.config import settings

class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Ensure trace_id is always present for stable JSON log schema.
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        return True

def setup_logging():
    logger = logging.getLogger()
    
    # 설정된 로그 레벨 적용
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 핸들러 설정 (표준 출력)
    log_handler = logging.StreamHandler(sys.stdout)
    
    # JSON 포맷터 적용 (운영성 지표 포함)
    if jsonlogger is not None:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s trace_id=%(trace_id)s"
        )
    log_handler.setFormatter(formatter)
    log_handler.addFilter(TraceIdFilter())
    
    # 기존 핸들러 제거 후 신규 추가
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(log_handler)

    # FastAPI 관련 로그도 정형화하도록 전역 설정
    logging.getLogger("uvicorn.access").handlers = [log_handler]
    logging.getLogger("uvicorn.error").handlers = [log_handler]
