from fastapi.testclient import TestClient

from app.main import app


def test_get_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "flowpilot",
        "version": "0.1.0",
    }
    assert response.headers["content-type"].startswith("application/json")
