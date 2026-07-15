import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_validate_lead_routing_example_returns_cycle_warning_and_valid_result() -> None:
    client = TestClient(app)
    payload = json.loads(Path("examples/lead-routing.json").read_text())

    response = client.post("/api/flows/validate", json=payload)

    assert response.status_code == 200
    body = response.json()
    codes = {finding["code"] for finding in body["findings"]}
    assert body["is_valid"] is True
    assert "SUSPICIOUS_CYCLE" in codes
    assert "DANGLING_TRANSITION" not in codes
    assert "MISSING_FALLBACK" not in codes
    assert "NO_TERMINAL_PATH" not in codes


def test_validate_flow_api_returns_422_for_malformed_pydantic_request() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/validate",
        json={
            "id": "",
            "name": "Broken",
            "trigger_node_id": "missing",
            "nodes": [],
        },
    )

    assert response.status_code == 422
