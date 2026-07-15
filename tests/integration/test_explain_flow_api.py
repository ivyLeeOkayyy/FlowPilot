import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_explain_lead_routing_example_returns_explanation() -> None:
    client = TestClient(app)
    payload = json.loads(Path("examples/lead-routing.json").read_text())

    response = client.post("/api/flows/explain", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["flow_name"] == "Lead routing"
    assert body["steps"]
    assert body["outcomes"]
    assert any(risk["code"] == "SUSPICIOUS_CYCLE" for risk in body["risks"])
    assert body["is_safe_to_simulate"] is True


def test_explain_flow_api_returns_422_for_malformed_request() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/explain",
        json={
            "id": "",
            "name": "Broken",
            "trigger_node_id": "missing",
            "nodes": [],
        },
    )

    assert response.status_code == 422
