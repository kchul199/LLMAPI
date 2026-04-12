import os

from fastapi.testclient import TestClient


def test_root_smoke():
    os.environ["MYSQL_DSN"] = "sqlite+pysqlite:////tmp/client_gateway_test.db"
    os.environ["QUEUE_ENABLED"] = "false"

    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "ui" in data
