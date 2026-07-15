import logging

import pytest
from pydantic import ValidationError

from app.models import (
    AutomationFlow,
    FlowValidationResult,
    GenerationMode,
    GenerationRequest,
    GenerationStatus,
)
from app.services.generation_service import FlowGenerationService


def generate(prompt: str, **overrides: object):
    request = GenerationRequest(prompt=prompt, **overrides)
    return FlowGenerationService().generate(request)


def test_blank_prompt_rejected_by_pydantic() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(prompt="   ")


def test_lead_routing_prompt_selects_lead_template() -> None:
    response = generate(
        "When a new contact arrives, ask if they are a buyer or seller and route sales leads."
    )

    assert response.flow is not None
    assert response.flow.name == "Lead routing"
    assert any(node.id == "route-contact-type" for node in response.flow.nodes)


def test_support_prompt_selects_support_template() -> None:
    response = generate(
        "Support request: route billing to finance and account access to support or a human agent."
    )

    assert response.flow is not None
    assert response.flow.name == "Support triage"
    assert any(node.id == "route-human-support" for node in response.flow.nodes)


def test_order_prompt_selects_order_template() -> None:
    response = generate("Check order status by order ID using an API.")

    assert response.flow is not None
    assert response.flow.name == "Order status"
    assert any(node.type == "api_call" for node in response.flow.nodes)


def test_vague_prompt_returns_clarification_required() -> None:
    response = generate("Please automate this process.")

    assert response.status is GenerationStatus.CLARIFICATION_REQUIRED
    assert response.flow is None
    assert response.clarification_question
    assert response.provider == "mock"


def test_generated_flows_parse_as_automation_flow() -> None:
    response = generate("Route buyer and seller leads to sales from a contact form.")

    assert isinstance(response.flow, AutomationFlow)


def test_generated_flow_metadata_contains_source_prompt() -> None:
    prompt = "Route buyer and seller leads to sales from a contact form."

    response = generate(prompt)

    assert response.flow is not None
    assert response.flow.metadata.source_prompt == prompt
    assert response.flow.metadata.generator == "mock"


def test_generated_flow_ids_are_unique_across_calls() -> None:
    prompt = "Route buyer and seller leads to sales from a contact form."

    first = generate(prompt)
    second = generate(prompt)

    assert first.flow is not None
    assert second.flow is not None
    assert first.flow.id != second.flow.id


def test_mock_generation_is_deterministic_in_logical_structure() -> None:
    prompt = "Route buyer and seller leads to sales from a contact form."

    first = generate(prompt).flow
    second = generate(prompt).flow

    assert first is not None
    assert second is not None
    assert [node.id for node in first.nodes] == [node.id for node in second.nodes]
    assert [node.type for node in first.nodes] == [node.type for node in second.nodes]


class RecordingValidationService:
    def __init__(self, result: FlowValidationResult | None = None) -> None:
        self.called = False
        self.result = result or FlowValidationResult(is_valid=True, findings=[])

    def validate(self, flow: AutomationFlow) -> FlowValidationResult:
        self.called = True
        return self.result


def test_validation_is_called() -> None:
    validation_service = RecordingValidationService()
    service = FlowGenerationService(validation_service=validation_service)

    service.generate(GenerationRequest(prompt="Route buyer and seller leads."))

    assert validation_service.called is True


def test_explanation_is_included_by_default() -> None:
    response = generate("Route buyer and seller leads to sales from a contact form.")

    assert response.explanation is not None


def test_explanation_can_be_disabled() -> None:
    response = generate(
        "Route buyer and seller leads to sales from a contact form.",
        include_explanation=False,
    )

    assert response.explanation is None


def test_warnings_produce_generated_with_warnings() -> None:
    response = generate("Route buyer and seller leads to sales from a contact form.")

    assert response.status is GenerationStatus.GENERATED_WITH_WARNINGS
    assert response.validation is not None
    assert any(finding.severity == "warning" for finding in response.validation.findings)


def test_validation_errors_produce_failed() -> None:
    invalid_validation = FlowValidationResult(
        is_valid=False,
        findings=[
            {
                "severity": "error",
                "message": "Broken generated graph.",
                "code": "BROKEN_GRAPH",
            }
        ],
    )
    service = FlowGenerationService(
        validation_service=RecordingValidationService(invalid_validation)
    )

    response = service.generate(
        GenerationRequest(prompt="Route buyer and seller leads to sales.")
    )

    assert response.status is GenerationStatus.FAILED
    assert response.error_code == "GENERATED_FLOW_INVALID"
    assert response.flow is not None


def test_service_does_not_mutate_input() -> None:
    request = GenerationRequest(
        prompt="  Route buyer and seller leads to sales.  ",
        flow_name="Custom leads",
        include_explanation=False,
    )
    before = request.model_dump(mode="json")

    FlowGenerationService().generate(request)

    assert request.model_dump(mode="json") == before


def test_llm_mode_without_configuration_returns_llm_not_configured(monkeypatch) -> None:
    for name in ["LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"]:
        monkeypatch.delenv(name, raising=False)

    response = FlowGenerationService().generate(
        GenerationRequest(prompt="Route leads.", mode=GenerationMode.LLM)
    )

    assert response.status is GenerationStatus.FAILED
    assert response.error_code == "LLM_NOT_CONFIGURED"
    assert response.flow is None


def test_invalid_llm_json_path_is_not_used_in_disabled_adapter(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test")
    monkeypatch.setenv("LLM_API_KEY", "secret-test-key")
    monkeypatch.setenv("LLM_MODEL", "demo-model")

    response = FlowGenerationService().generate(
        GenerationRequest(prompt="Route leads.", mode=GenerationMode.LLM)
    )

    assert response.status is GenerationStatus.FAILED
    assert response.error_code == "LLM_NOT_CONFIGURED"


def test_no_api_key_appears_in_logs_or_responses(monkeypatch, caplog) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example.test")
    monkeypatch.setenv("LLM_API_KEY", "secret-test-key")
    monkeypatch.setenv("LLM_MODEL", "demo-model")

    with caplog.at_level(logging.INFO):
        response = FlowGenerationService().generate(
            GenerationRequest(prompt="Route leads.", mode=GenerationMode.LLM)
        )

    serialized_response = response.model_dump_json()
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "secret-test-key" not in serialized_response
    assert "secret-test-key" not in log_text
