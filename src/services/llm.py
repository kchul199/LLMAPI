import json
import logging
import time
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.services.prompts import PromptManager

logger = logging.getLogger(__name__)


class LLMUpstreamError(RuntimeError):
    """Raised when upstream LLM engines are unavailable or failed."""


class CircuitBreaker:
    def __init__(self, name: str):
        self.name = name
        self.failure_threshold = max(1, settings.LLM_CB_FAILURE_THRESHOLD)
        self.recovery_seconds = max(1, settings.LLM_CB_RECOVERY_SECONDS)
        self.half_open_max_calls = max(1, settings.LLM_CB_HALF_OPEN_MAX_CALLS)

        self._state = "closed"
        self._failure_count = 0
        self._opened_at: Optional[float] = None
        self._half_open_calls = 0

    def _transition_if_recovery_elapsed(self) -> None:
        if self._state != "open" or self._opened_at is None:
            return

        if (time.monotonic() - self._opened_at) >= self.recovery_seconds:
            self._state = "half_open"
            self._half_open_calls = 0

    def allow_request(self) -> bool:
        self._transition_if_recovery_elapsed()

        if self._state == "open":
            return False

        if self._state == "half_open":
            if self._half_open_calls >= self.half_open_max_calls:
                return False
            self._half_open_calls += 1

        return True

    def on_success(self) -> None:
        self._state = "closed"
        self._failure_count = 0
        self._opened_at = None
        self._half_open_calls = 0

    def on_failure(self) -> None:
        self._failure_count += 1
        if self._state == "half_open" or self._failure_count >= self.failure_threshold:
            self._state = "open"
            self._opened_at = time.monotonic()
            self._half_open_calls = 0

    def snapshot(self) -> Dict[str, Any]:
        self._transition_if_recovery_elapsed()

        open_remaining_seconds = 0
        if self._state == "open" and self._opened_at is not None:
            elapsed = time.monotonic() - self._opened_at
            open_remaining_seconds = max(0, int(self.recovery_seconds - elapsed))

        return {
            "name": self.name,
            "state": self._state,
            "failure_count": self._failure_count,
            "open_remaining_seconds": open_remaining_seconds,
        }


class LLMService:
    def __init__(self):
        self.main_client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY or "not-needed",
            timeout=max(settings.LLM_TIMEOUT_MIN_SECONDS, settings.LLM_TIMEOUT_SUMMARY_SECONDS),
        )
        self.backup_client = AsyncOpenAI(
            base_url=settings.LLM_BACKUP_BASE_URL,
            api_key="not-needed",
            timeout=max(settings.LLM_TIMEOUT_MIN_SECONDS, settings.LLM_TIMEOUT_SUMMARY_SECONDS),
        )

        self.main_breaker = CircuitBreaker(name="main")
        self.backup_breaker = CircuitBreaker(name="backup")

    @retry(
        stop=stop_after_attempt(max(1, settings.LLM_RETRY_ATTEMPTS)),
        wait=wait_exponential(
            multiplier=1,
            min=max(1, settings.LLM_RETRY_MIN_WAIT_SECONDS),
            max=max(1, settings.LLM_RETRY_MAX_WAIT_SECONDS),
        ),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _call_inference(
        self,
        client: AsyncOpenAI,
        model: str,
        system_prompt: str,
        user_message: str,
        request_timeout: float,
    ):
        """Actual inference call with retry policy."""
        request_args = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "timeout": request_timeout,
        }

        if model and "llama" in model.lower():
            request_args["response_format"] = {"type": "json_object"}

        return await client.chat.completions.create(**request_args)

    @staticmethod
    def _normalize_results(raw_results: Any, tasks: List[str]) -> Dict[str, Any]:
        if not isinstance(raw_results, dict):
            raw_results = {"raw_result": raw_results}

        normalized = {task: raw_results.get(task) for task in tasks}
        if "error" in raw_results:
            normalized["error"] = raw_results["error"]
        return normalized

    @staticmethod
    def _safe_json_loads(content: str) -> Dict[str, Any]:
        try:
            loaded = json.loads(content)
            if isinstance(loaded, dict):
                return loaded
            return {"raw_result": loaded}
        except json.JSONDecodeError:
            return {"error": "JSON 파싱 실패", "raw_content": content}

    @staticmethod
    def _resolve_timeout(tasks: List[str], is_fallback: bool = False) -> float:
        timeout_map = {
            "summary": settings.LLM_TIMEOUT_SUMMARY_SECONDS,
            "sentiment": settings.LLM_TIMEOUT_SENTIMENT_SECONDS,
            "category": settings.LLM_TIMEOUT_CATEGORY_SECONDS,
        }

        base = max([timeout_map.get(task, settings.LLM_TIMEOUT_SUMMARY_SECONDS) for task in tasks], default=settings.LLM_TIMEOUT_SUMMARY_SECONDS)
        overhead = max(0.0, settings.LLM_TIMEOUT_MULTI_TASK_OVERHEAD_SECONDS) * max(0, len(tasks) - 1)
        resolved = base + overhead

        if is_fallback:
            resolved = resolved * max(0.1, settings.LLM_TIMEOUT_BACKUP_MULTIPLIER)

        return max(settings.LLM_TIMEOUT_MIN_SECONDS, resolved)

    async def _attempt_with_breaker(
        self,
        breaker: CircuitBreaker,
        client: AsyncOpenAI,
        model: str,
        system_prompt: str,
        user_message: str,
        request_timeout: float,
        request_id: str,
    ):
        if not breaker.allow_request():
            raise LLMUpstreamError(f"{breaker.name} circuit breaker is open")

        try:
            response = await self._call_inference(
                client=client,
                model=model,
                system_prompt=system_prompt,
                user_message=user_message,
                request_timeout=request_timeout,
            )
            breaker.on_success()
            return response
        except Exception:
            breaker.on_failure()
            raise

    async def analyze(
        self,
        text: str,
        tasks: List[str],
        target_speakers: str,
        request_id: str = "-",
        prompt_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analysis flow:
        1) Main model + retry + circuit breaker
        2) On main failure, fallback model + breaker
        """
        system_prompt = PromptManager.get_analysis_system_prompt(
            tasks=tasks,
            target_speakers=target_speakers,
            prompt_version=prompt_version,
        )
        user_message = PromptManager.get_analysis_user_message(
            text=text,
            prompt_version=prompt_version,
        )

        main_timeout = self._resolve_timeout(tasks=tasks, is_fallback=False)
        backup_timeout = self._resolve_timeout(tasks=tasks, is_fallback=True)

        current_model = settings.LLM_MODEL_NAME
        is_fallback = False
        response = None
        main_error: Optional[Exception] = None

        try:
            logger.info(
                f"LLM Call [Main]: {current_model}",
                extra={"trace_id": request_id, "timeout": main_timeout},
            )
            response = await self._attempt_with_breaker(
                breaker=self.main_breaker,
                client=self.main_client,
                model=current_model,
                system_prompt=system_prompt,
                user_message=user_message,
                request_timeout=main_timeout,
                request_id=request_id,
            )
        except Exception as exc:
            main_error = exc
            logger.warning(
                f"Main Engine Failed: {exc}. Triggering fail-over to backup.",
                extra={"trace_id": request_id},
            )

        if response is None:
            if not settings.LLM_BACKUP_MODEL_NAME:
                raise LLMUpstreamError("메인 LLM 호출 실패 및 백업 모델 미설정 상태입니다.") from main_error

            is_fallback = True
            current_model = settings.LLM_BACKUP_MODEL_NAME

            try:
                logger.info(
                    f"LLM Call [Backup]: {current_model}",
                    extra={"trace_id": request_id, "timeout": backup_timeout},
                )
                response = await self._attempt_with_breaker(
                    breaker=self.backup_breaker,
                    client=self.backup_client,
                    model=current_model,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    request_timeout=backup_timeout,
                    request_id=request_id,
                )
            except Exception as backup_error:
                logger.error(
                    f"Critical Error: Both Main and Backup engines failed. {backup_error}",
                    extra={"trace_id": request_id},
                )
                raise LLMUpstreamError("메인/백업 LLM 호출 모두 실패했습니다.") from backup_error

        content = response.choices[0].message.content or "{}"
        parsed_results = self._safe_json_loads(content)
        normalized_results = self._normalize_results(parsed_results, tasks)

        usage = getattr(response, "usage", None)
        total_tokens = getattr(usage, "total_tokens", 0) or 0

        return {
            "results": normalized_results,
            "is_fallback": is_fallback,
            "usage": {
                "total_tokens": total_tokens,
                "model": current_model,
            },
        }

    def get_runtime_health(self) -> Dict[str, Any]:
        return {
            "retry": {
                "attempts": settings.LLM_RETRY_ATTEMPTS,
                "min_wait_seconds": settings.LLM_RETRY_MIN_WAIT_SECONDS,
                "max_wait_seconds": settings.LLM_RETRY_MAX_WAIT_SECONDS,
            },
            "timeout_policy": {
                "min_seconds": settings.LLM_TIMEOUT_MIN_SECONDS,
                "summary_seconds": settings.LLM_TIMEOUT_SUMMARY_SECONDS,
                "sentiment_seconds": settings.LLM_TIMEOUT_SENTIMENT_SECONDS,
                "category_seconds": settings.LLM_TIMEOUT_CATEGORY_SECONDS,
                "multi_task_overhead_seconds": settings.LLM_TIMEOUT_MULTI_TASK_OVERHEAD_SECONDS,
                "backup_multiplier": settings.LLM_TIMEOUT_BACKUP_MULTIPLIER,
            },
            "circuit_breaker": {
                "main": self.main_breaker.snapshot(),
                "backup": self.backup_breaker.snapshot(),
            },
        }


llm_service = LLMService()
