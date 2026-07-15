from fastapi.testclient import TestClient

from app.main import app
from app.services.providers import MockWorkflowGenerationProvider


def test_generate_lead_routing_prompt_returns_flow() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/generate",
        json={"prompt": "Route buyer and seller leads from a new contact to sales."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["flow"] is not None
    assert body["flow"]["name"] == "Lead routing"


def test_generate_support_prompt_returns_flow() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/generate",
        json={
            "prompt": (
                "Triage support requests for billing, account access, finance, "
                "or a human agent."
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["flow"] is not None
    assert body["flow"]["name"] == "Support triage"


def test_generate_order_status_prompt_returns_api_call_flow() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/generate",
        json={"prompt": "Check order status by order ID using an API."},
    )

    assert response.status_code == 200
    body = response.json()
    assert any(node["type"] == "api_call" for node in body["flow"]["nodes"])


def test_generate_vague_prompt_returns_clarification_required() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/generate",
        json={"prompt": "Please automate this."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "clarification_required"
    assert body["flow"] is None


def test_generate_blank_prompt_returns_422() -> None:
    client = TestClient(app)

    response = client.post("/api/flows/generate", json={"prompt": "   "})

    assert response.status_code == 422


def test_generate_include_explanation_false_returns_null_explanation() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/flows/generate",
        json={
            "prompt": "Route buyer and seller leads from a new contact to sales.",
            "include_explanation": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["explanation"] is None


def test_generate_llm_mode_uses_mocked_deepseek_provider(monkeypatch) -> None:
    class FakeDeepSeekProvider:
        provider_name = "deepseek"
        model_name = "deepseek-chat"

        def generate(self, prompt: str) -> dict:
            return MockWorkflowGenerationProvider().generate(
                "Route buyer and seller leads from a new contact to sales."
            )

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setattr(
        "app.services.generation_service.DeepSeekProvider",
        lambda: FakeDeepSeekProvider(),
    )
    client = TestClient(app)

    response = client.post(
        "/api/flows/generate",
        json={"prompt": "Route leads with DeepSeek.", "mode": "llm"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["flow"] is not None
    assert body["provider"] == "deepseek"
    assert body["validation"] is not None
    assert body["explanation"] is not None
