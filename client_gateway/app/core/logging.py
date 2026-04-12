import logging
import sys

from pythonjsonlogger import jsonlogger

from app.core.config import settings


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        return True


def setup_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s")
    handler.setFormatter(formatter)
    handler.addFilter(TraceIdFilter())

    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)
