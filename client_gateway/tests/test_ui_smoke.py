import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_ui_pages_and_api_smoke():
    os.environ["MYSQL_DSN"] = "sqlite+pysqlite:////tmp/client_gateway_test.db"
    os.environ["QUEUE_ENABLED"] = "false"

    from app.main import create_app

    with TestClient(create_app()) as client:
        assert client.get("/ui").status_code == 200
        assert client.get("/ui/test").status_code == 200
        assert client.get("/ui/history").status_code == 200
        assert client.get("/ui/history/sample-request").status_code == 200
        assert client.get("/ui/static/css/ui.css").status_code == 200
        assert client.get("/ui/static/js/ui_test.js").status_code == 200

        summary_resp = client.get("/ui/api/dashboard-summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert "total_requests_today" in summary
        assert "status_counts" in summary

        history_resp = client.get("/ui/api/requests")
        assert history_resp.status_code == 200
        history = history_resp.json()
        assert history["page"] == 1
        assert "items" in history

        health_resp = client.get("/ui/api/health")
        assert health_resp.status_code == 200
        health = health_resp.json()
        assert health["status"] in ("healthy", "degraded")
