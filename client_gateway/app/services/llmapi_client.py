from typing import Any

import httpx

from app.core.config import settings


class LLMAPIClient:
    def __init__(self):
        self.base_url = settings.LLMAPI_BASE_URL.rstrip("/")
        self.timeout = settings.LLMAPI_TIMEOUT_SECONDS

    async def analyze_sync(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/analyze", json=payload)
            return response.status_code, self._safe_json(response)

    async def analyze_async_enqueue(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/analyze/async", json=payload)
            return response.status_code, self._safe_json(response)

    async def analyze_async_status(self, job_id: str) -> tuple[int, dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/analyze/async/{job_id}")
            return response.status_code, self._safe_json(response)

    async def health(self) -> tuple[int, dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            return response.status_code, self._safe_json(response)

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
            if isinstance(data, dict):
                return data
            return {"data": data}
        except Exception:
            return {"raw": response.text}
