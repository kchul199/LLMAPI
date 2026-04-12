import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.core.config import settings
from src.schemas.analysis import AnalysisRequest
from src.services.llm import LLMUpstreamError, llm_service

logger = logging.getLogger(__name__)


class QueueUnavailableError(RuntimeError):
    """Raised when async queue operations are requested but Redis queue is unavailable."""


class AnalysisQueueService:
    def __init__(self):
        self.enabled = settings.REDIS_QUEUE_ENABLED
        self._redis: Optional[Redis] = None
        self._worker_tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self._ready = False

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _job_key(self, job_id: str) -> str:
        return f"{settings.REDIS_JOB_KEY_PREFIX}:{job_id}"

    async def startup(self) -> None:
        if not self.enabled:
            logger.info("Redis queue disabled by configuration", extra={"trace_id": "startup"})
            return

        self._redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

        try:
            await self._redis.ping()
        except Exception as exc:
            self._ready = False
            logger.error(
                f"Failed to connect Redis queue: {exc}",
                extra={"trace_id": "startup"},
            )
            return

        self._ready = True
        self._stop_event.clear()

        worker_count = max(1, settings.REDIS_QUEUE_WORKER_CONCURRENCY)
        self._worker_tasks = [
            asyncio.create_task(self._worker_loop(i), name=f"analysis-queue-worker-{i}")
            for i in range(worker_count)
        ]

        logger.info(
            f"Redis queue workers started: {worker_count}",
            extra={"trace_id": "startup"},
        )

    async def shutdown(self) -> None:
        self._stop_event.set()

        for task in self._worker_tasks:
            task.cancel()

        for task in self._worker_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._worker_tasks = []

        if self._redis is not None:
            await self._redis.close()
            self._redis = None

        self._ready = False

    def _ensure_ready(self) -> None:
        if not self.enabled:
            raise QueueUnavailableError("Redis queue is disabled")
        if not self._ready or self._redis is None:
            raise QueueUnavailableError("Redis queue is not connected")

    async def enqueue(self, request: AnalysisRequest) -> str:
        self._ensure_ready()

        job_id = f"{request.request_id}-{uuid4().hex[:10]}"
        now = self._utc_now()

        job_record: Dict[str, Any] = {
            "job_id": job_id,
            "request_id": request.request_id,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "request": {
                "text": request.text,
                "tasks": request.tasks,
                "target_speakers": request.target_speakers,
                "options": request.options.model_dump() if request.options else {},
            },
            "response": None,
            "error": None,
        }

        payload = json.dumps(job_record, ensure_ascii=False)

        pipe = self._redis.pipeline()
        pipe.set(self._job_key(job_id), payload, ex=settings.REDIS_JOB_TTL_SECONDS)
        pipe.rpush(settings.REDIS_QUEUE_KEY, job_id)
        await pipe.execute()

        return job_id

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_ready()

        raw = await self._redis.get(self._job_key(job_id))
        if not raw:
            return None

        return json.loads(raw)

    async def get_health(self) -> Dict[str, Any]:
        health = {
            "enabled": self.enabled,
            "ready": self._ready,
            "queue_key": settings.REDIS_QUEUE_KEY,
            "worker_concurrency": max(1, settings.REDIS_QUEUE_WORKER_CONCURRENCY),
            "queue_depth": None,
        }

        if self._ready and self._redis is not None:
            try:
                health["queue_depth"] = await self._redis.llen(settings.REDIS_QUEUE_KEY)
            except RedisError:
                health["ready"] = False

        return health

    async def _save_job(self, job: Dict[str, Any]) -> None:
        payload = json.dumps(job, ensure_ascii=False)
        await self._redis.set(self._job_key(job["job_id"]), payload, ex=settings.REDIS_JOB_TTL_SECONDS)

    async def _worker_loop(self, worker_index: int) -> None:
        logger.info(
            f"Queue worker loop started: {worker_index}",
            extra={"trace_id": "startup"},
        )

        while not self._stop_event.is_set():
            if not self._ready or self._redis is None:
                await asyncio.sleep(1)
                continue

            try:
                popped = await self._redis.blpop(settings.REDIS_QUEUE_KEY, timeout=1)
            except asyncio.CancelledError:
                raise
            except RedisError as exc:
                logger.error(
                    f"Queue worker Redis error: {exc}",
                    extra={"trace_id": "queue-worker"},
                )
                await asyncio.sleep(1)
                continue

            if not popped:
                continue

            _, job_id = popped
            await self._process_job(job_id)

    async def _process_job(self, job_id: str) -> None:
        try:
            job = await self.get_job(job_id)
        except QueueUnavailableError:
            return

        if not job:
            return

        request_id = job.get("request_id", job_id)

        job["status"] = "processing"
        job["updated_at"] = self._utc_now()
        await self._save_job(job)

        request = job.get("request", {})
        options = request.get("options") or {}

        try:
            llm_result = await llm_service.analyze(
                text=request.get("text", ""),
                tasks=request.get("tasks", []),
                target_speakers=request.get("target_speakers", "both"),
                request_id=request_id,
                prompt_version=options.get("prompt_version"),
            )

            job["status"] = "completed"
            job["response"] = {
                "results": llm_result.get("results", {}),
                "usage": llm_result.get("usage", {}),
                "is_fallback": llm_result.get("is_fallback", False),
            }
            job["error"] = None
        except LLMUpstreamError as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
            job["response"] = None
            logger.error(
                f"Async analyze upstream failure: {exc}",
                extra={"trace_id": request_id},
            )
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = f"Internal queue worker error: {exc}"
            job["response"] = None
            logger.exception(
                f"Async analyze unexpected failure: {exc}",
                extra={"trace_id": request_id},
            )

        job["updated_at"] = self._utc_now()
        await self._save_job(job)


analysis_queue_service = AnalysisQueueService()
