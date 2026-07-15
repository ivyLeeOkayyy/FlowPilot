import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def load_request(name: str) -> dict:
    return json.loads(Path(f"examples/simulations/{name}.json").read_text())


def test_simulate_buyer_example_returns_completed() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/simulate",
        json=load_request("lead-routing-buyer"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["completed_outcome"] == "buyer_routed_to_sales"
    assert body["assigned_team"] == "sales"


def test_simulate_seller_example_returns_completed() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/simulate",
        json=load_request("lead-routing-seller"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["completed_outcome"] == "seller_help_article_sent"
    assert any("help article" in item["message"] for item in body["transcript"])


def test_simulate_without_user_input_returns_waiting_for_input() -> None:
    client = TestClient(app)
    payload = {
        "flow": json.loads(Path("examples/lead-routing.json").read_text()),
    }

    response = client.post("/api/flows/simulate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "waiting_for_input"
    assert body["current_node_id"] == "ask-contact-type"


def test_simulate_unexpected_example_returns_step_limit_exceeded() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/simulate",
        json=load_request("lead-routing-unexpected"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "step_limit_exceeded"
    assert body["error_code"] == "STEP_LIMIT_EXCEEDED"


def test_simulate_flow_api_returns_422_for_malformed_request() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/simulate",
        json={
            "flow": {
                "id": "",
                "name": "Broken",
                "trigger_node_id": "missing",
                "nodes": [],
            },
            "max_steps": 0,
        },
    )

    assert response.status_code == 422
