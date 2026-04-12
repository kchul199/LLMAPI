import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.main import app
from src.services.llm import LLMUpstreamError


class TestAPIContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_contract(self):
        response = self.client.get("/v1/health")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("version", data)
        self.assertIn("llm", data)
        self.assertIn("prompt_config", data)
        self.assertIn("queue", data)
        self.assertIn("runtime", data["llm"])

    def test_analyze_rejects_empty_tasks(self):
        payload = {
            "request_id": "req_empty_tasks",
            "text": "고객: 배송 지연이 심해요.",
            "tasks": [],
            "target_speakers": "customer",
        }
        response = self.client.post("/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_analyze_rejects_invalid_task(self):
        payload = {
            "request_id": "req_invalid_task",
            "text": "고객: 배송 지연이 심해요.",
            "tasks": ["summary", "unknown_task"],
            "target_speakers": "customer",
        }
        response = self.client.post("/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 422)

    @patch("src.api.v1.endpoints.llm_service.analyze", new_callable=AsyncMock)
    def test_analyze_success(self, mock_analyze):
        mock_analyze.return_value = {
            "results": {
                "summary": "배송 지연 문의",
                "sentiment": "불만",
                "category": "배송/물류",
            },
            "is_fallback": False,
            "usage": {"total_tokens": 42, "model": "llama3.2:3b"},
        }

        payload = {
            "request_id": "req_success",
            "text": "고객: 배송이 늦어요. 상담원: 확인하겠습니다.",
            "tasks": ["summary", "sentiment", "category", "summary"],
            "target_speakers": "customer",
        }
        response = self.client.post("/v1/analyze", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["request_id"], "req_success")
        self.assertEqual(data["results"]["sentiment"], "불만")
        self.assertEqual(data["usage"]["total_tokens"], 42)

        called_tasks = mock_analyze.await_args.kwargs["tasks"]
        self.assertEqual(called_tasks, ["summary", "sentiment", "category"])
        self.assertEqual(mock_analyze.await_args.kwargs["prompt_version"], "v1.0")

    @patch("src.api.v1.endpoints.llm_service.analyze", new_callable=AsyncMock)
    def test_analyze_upstream_error(self, mock_analyze):
        mock_analyze.side_effect = LLMUpstreamError("upstream failed")

        payload = {
            "request_id": "req_upstream_error",
            "text": "고객: 문의드립니다.",
            "tasks": ["summary"],
            "target_speakers": "customer",
        }
        response = self.client.post("/v1/analyze", json=payload)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json()["detail"],
            "LLM 추론 엔진 호출에 실패했습니다.",
        )

    def test_async_analyze_unavailable_when_queue_disabled(self):
        payload = {
            "request_id": "req_async_disabled",
            "text": "고객: 배송 문의입니다.",
            "tasks": ["summary"],
            "target_speakers": "customer",
        }
        response = self.client.post("/v1/analyze/async", json=payload)
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
