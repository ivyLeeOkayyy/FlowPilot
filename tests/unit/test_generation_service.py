import logging

import httpx
import pytest
from pydantic import ValidationError

from app.models import (
    AutomationFlow,
    FlowValidationResult,
    GenerationMode,
    GenerationRequest,
    GenerationStatus,
)
from app.core.config import llm_config_diagnostics
from app.services.generation_service import FlowGenerationService
from app.services.providers import (
    DeepSeekProvider,
    GenerationProviderError,
    MockWorkflowGenerationProvider,
)
from app.services.providers.deepseek_provider import SYSTEM_PROMPT


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


def test_mock_provider_still_works() -> None:
    provider = MockWorkflowGenerationProvider()

    generated = provider.generate("Route buyer and seller leads to sales from a contact.")

    assert generated["name"] == "Lead routing"
    assert generated["trigger_node_id"] == "new-contact"


def test_mock_mode_selects_mock_provider_even_when_deepseek_is_configured(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")

    response = FlowGenerationService().generate(
        GenerationRequest(
            prompt="Route buyer and seller leads to sales from a contact.",
            mode=GenerationMode.MOCK,
        )
    )

    assert response.flow is not None
    assert response.provider == "mock"


def test_llm_mode_without_configuration_returns_llm_not_configured(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")

    response = FlowGenerationService(
        llm_provider_factory=lambda request: DeepSeekProvider(api_key="")
    ).generate(GenerationRequest(prompt="Route leads.", mode=GenerationMode.LLM))

    assert response.status is GenerationStatus.FAILED
    assert response.error_code == "LLM_NOT_CONFIGURED"
    assert response.flow is None


def test_deepseek_provider_missing_api_key_fails(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    provider = DeepSeekProvider(api_key="")

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate("Route leads.")

    assert exc_info.value.code == "LLM_NOT_CONFIGURED"


def test_llm_mode_never_silently_falls_back_to_mock(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    response = FlowGenerationService().generate(
        GenerationRequest(prompt="Please automate this process.", mode=GenerationMode.LLM)
    )

    assert response.status is GenerationStatus.FAILED
    assert response.error_code == "LLM_NOT_CONFIGURED"
    assert response.provider == "mock"
    assert response.clarification_question is None
    assert response.flow is None


def test_provider_selection_uses_configured_deepseek_provider(monkeypatch) -> None:
    class FakeProvider:
        provider_name = "deepseek"
        model_name = "deepseek-chat"

        def generate(self, prompt: str) -> dict:
            return MockWorkflowGenerationProvider().generate(
                "Route buyer and seller leads to sales from a contact."
            )

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")

    response = FlowGenerationService(
        llm_provider_factory=lambda request: FakeProvider(),
    ).generate(GenerationRequest(prompt="Route leads.", mode=GenerationMode.LLM))

    assert response.flow is not None
    assert response.provider == "deepseek"
    assert response.model_name == "deepseek-chat"


def test_invalid_json_response_is_handled_safely() -> None:
    provider = DeepSeekProvider(api_key="test-key", client_factory=FakeClientFactory("not-json"))

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate("Route leads.")

    assert exc_info.value.code == "INVALID_LLM_OUTPUT"


def test_successful_deepseek_content_extraction_and_json_parsing() -> None:
    provider_response = {
        "choices": [{"message": {"content": "{\"status\":\"ok\"}"}}],
    }
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump(provider_response)),
    )

    generated = provider.generate_workflow_data("Return status JSON.")

    assert generated == {"status": "ok"}
    assert provider.last_diagnostics["choices_present"] is True
    assert provider.last_diagnostics["message_present"] is True
    assert provider.last_diagnostics["content_present"] is True
    assert provider.last_diagnostics["content_json_valid"] is True


def test_plain_text_response_returns_invalid_llm_output() -> None:
    provider_response = {
        "choices": [
            {"message": {"content": "Generate a workflow to inspect the JSON artifact."}}
        ],
    }
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump(provider_response)),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate_workflow_data("Return a workflow.")

    assert exc_info.value.code == "INVALID_LLM_OUTPUT"


def test_deepseek_system_prompt_requires_internal_automation_flow_schema() -> None:
    assert "Do not wrap output inside automationFlow." in SYSTEM_PROMPT
    assert "Do not wrap output inside workflow." in SYSTEM_PROMPT
    assert "Do not use steps." in SYSTEM_PROMPT
    assert (
        "The output will be validated by Pydantic AutomationFlow.model_validate(). "
        "Any other format will fail."
    ) in SYSTEM_PROMPT
    assert '"trigger_node_id": "string"' in SYSTEM_PROMPT
    assert '"nodes": []' in SYSTEM_PROMPT
    assert "trigger | send_message | ask_question | condition | api_call | assign_to_team | wait | end" in SYSTEM_PROMPT


def test_markdown_json_response_is_cleaned_safely() -> None:
    provider_response = {
        "choices": [{"message": {"content": "```json\n{\"status\":\"ok\"}\n```"}}],
    }
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump(provider_response)),
    )

    generated = provider.generate_workflow_data("Return status JSON.")

    assert generated == {"status": "ok"}


def test_valid_json_object_response_passes_parsing() -> None:
    provider_response = {
        "choices": [{"message": {"content": "  {\"status\":\"ok\"}  "}}],
    }
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump(provider_response)),
    )

    generated = provider.generate_workflow_data("Return status JSON.")

    assert generated == {"status": "ok"}


def test_successful_deepseek_automation_flow_validation() -> None:
    flow = MockWorkflowGenerationProvider().generate(
        "Route buyer and seller leads to sales from a contact."
    )
    provider_response = {"choices": [{"message": {"content": json_dump(flow)}}]}
    provider = DeepSeekProvider(
        api_key="test-key",
        model_name="deepseek-chat",
        client_factory=FakeClientFactory(json_dump(provider_response)),
    )

    generated = provider.generate("Route leads.")

    assert generated["name"] == "Lead routing"
    assert provider.last_diagnostics["automation_flow_valid"] is True


def test_wrapped_automation_flow_response_fails_validation() -> None:
    provider_response = {
        "choices": [
            {
                "message": {
                    "content": json_dump(
                        {"automationFlow": minimal_valid_automation_flow()}
                    )
                }
            }
        ]
    }
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump(provider_response)),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate("Return a workflow.")

    assert exc_info.value.code == "INVALID_GENERATED_FLOW"


def test_valid_automation_flow_json_response_passes() -> None:
    provider_response = {
        "choices": [
            {"message": {"content": json_dump(minimal_valid_automation_flow())}}
        ]
    }
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump(provider_response)),
    )

    generated = provider.generate("Return a workflow.")

    assert generated["id"] == "test-flow"
    assert generated["nodes"][0]["type"] == "trigger"


def test_missing_nodes_response_fails_validation() -> None:
    invalid_flow = minimal_valid_automation_flow()
    invalid_flow.pop("nodes")
    provider_response = {
        "choices": [{"message": {"content": json_dump(invalid_flow)}}]
    }
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump(provider_response)),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate("Return a workflow.")

    assert exc_info.value.code == "INVALID_GENERATED_FLOW"


def test_missing_choices_returns_invalid_llm_output() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump({"choices": []})),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate_workflow_data("Route leads.")

    assert exc_info.value.code == "INVALID_LLM_OUTPUT"


def test_missing_message_returns_invalid_llm_output() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump({"choices": [{}]})),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate_workflow_data("Route leads.")

    assert exc_info.value.code == "INVALID_LLM_OUTPUT"


def test_missing_content_returns_invalid_llm_output() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump({"choices": [{"message": {}}]})),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate_workflow_data("Route leads.")

    assert exc_info.value.code == "INVALID_LLM_OUTPUT"


def test_invalid_content_json_returns_invalid_llm_output() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(json_dump({"choices": [{"message": {"content": "not-json"}}]})),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate_workflow_data("Route leads.")

    assert exc_info.value.code == "INVALID_LLM_OUTPUT"


def test_valid_json_with_invalid_automation_flow_schema_fails() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=FakeClientFactory(
            json_dump({"choices": [{"message": {"content": "{\"status\":\"ok\"}"}}]})
        ),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate("Route leads.")

    assert exc_info.value.code == "INVALID_GENERATED_FLOW"


def test_invalid_workflow_schema_returns_invalid_generated_flow(monkeypatch) -> None:
    class InvalidSchemaProvider:
        provider_name = "deepseek"
        model_name = "deepseek-chat"

        def generate(self, prompt: str) -> dict:
            return {"id": "not-a-flow"}

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")

    response = FlowGenerationService(
        llm_provider_factory=lambda request: InvalidSchemaProvider()
    ).generate(GenerationRequest(prompt="Route leads.", mode=GenerationMode.LLM))

    assert response.status is GenerationStatus.FAILED
    assert response.error_code == "INVALID_GENERATED_FLOW"


def test_valid_mocked_deepseek_json_generates_flow(monkeypatch) -> None:
    flow = MockWorkflowGenerationProvider().generate(
        "Route buyer and seller leads to sales from a contact."
    )
    provider_response = {"choices": [{"message": {"content": json_dump(flow)}}]}
    provider = DeepSeekProvider(
        api_key="test-key",
        model_name="deepseek-chat",
        client_factory=FakeClientFactory(json_dump(provider_response)),
    )

    generated = provider.generate("Route leads.")

    assert generated["name"] == "Lead routing"


def test_response_provider_is_deepseek_for_mocked_valid_deepseek_response(monkeypatch) -> None:
    class FakeProvider:
        provider_name = "deepseek"
        model_name = "deepseek-chat"

        def generate(self, prompt: str) -> dict:
            return MockWorkflowGenerationProvider().generate(
                "Route buyer and seller leads to sales from a contact."
            )

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")

    response = FlowGenerationService(
        llm_provider_factory=lambda request: FakeProvider()
    ).generate(GenerationRequest(prompt="Route leads.", mode=GenerationMode.LLM))

    assert response.flow is not None
    assert response.provider == "deepseek"


def test_timeout_handling_returns_provider_error() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=RaisingClientFactory(httpx.ConnectTimeout("timed out")),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate("Route leads.")

    assert exc_info.value.code == "LLM_PROVIDER_TIMEOUT"


def test_connection_failure_returns_connection_error() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=RaisingClientFactory(httpx.ConnectError("offline")),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate("Route leads.")

    assert exc_info.value.code == "LLM_PROVIDER_CONNECTION_FAILED"


def test_http_error_returns_provider_error() -> None:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    response = httpx.Response(401, request=request)
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=RaisingClientFactory(
            httpx.HTTPStatusError(
                "Unauthorized",
                request=request,
                response=response,
            )
        ),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate("Route leads.")

    assert exc_info.value.code == "LLM_PROVIDER_ERROR"


def test_unexpected_provider_error_returns_provider_error() -> None:
    provider = DeepSeekProvider(
        api_key="test-key",
        client_factory=RaisingClientFactory(RuntimeError("unexpected")),
    )

    with pytest.raises(GenerationProviderError) as exc_info:
        provider.generate("Route leads.")

    assert exc_info.value.code == "LLM_PROVIDER_ERROR"


def test_no_api_key_appears_in_logs_or_responses(monkeypatch, caplog) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-test-key")

    with caplog.at_level(logging.INFO):
        response = FlowGenerationService(
            llm_provider_factory=lambda request: DeepSeekProvider(
                api_key="secret-test-key",
                client_factory=RaisingClientFactory(
                    httpx.ConnectError("secret-test-key leaked by transport")
                ),
            )
        ).generate(
            GenerationRequest(prompt="Route leads.", mode=GenerationMode.LLM)
        )

    serialized_response = response.model_dump_json()
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "secret-test-key" not in serialized_response
    assert "secret-test-key" not in log_text


def test_configuration_diagnostics_never_expose_api_key(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "super-secret-test-key")

    diagnostics = llm_config_diagnostics()

    assert diagnostics["deepseek_api_key_configured"] is True
    assert "super-secret-test-key" not in str(diagnostics)


def test_deepseek_provider_default_client_uses_trust_env_true(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class CapturingClient:
        def __init__(self, *, timeout: httpx.Timeout, trust_env: bool) -> None:
            captured["timeout"] = timeout
            captured["trust_env"] = trust_env

    monkeypatch.setattr("app.services.providers.deepseek_provider.httpx.Client", CapturingClient)
    provider = DeepSeekProvider(api_key="test-key", timeout_seconds=30)

    client = provider._default_client_factory()

    assert isinstance(client, CapturingClient)
    assert captured["trust_env"] is True


def json_dump(value: object) -> str:
    import json

    return json.dumps(value)


def minimal_valid_automation_flow() -> dict:
    return {
        "id": "test-flow",
        "name": "Test flow",
        "description": "A small valid flow.",
        "version": 1,
        "trigger_node_id": "start",
        "nodes": [
            {
                "id": "start",
                "type": "trigger",
                "name": "Start",
                "config": {"event": "customer_message"},
                "transitions": [
                    {
                        "target_node_id": "ask-choice",
                        "label": None,
                        "condition": None,
                        "is_fallback": False,
                    }
                ],
            },
            {
                "id": "ask-choice",
                "type": "ask_question",
                "name": "Ask choice",
                "config": {
                    "question": "Morning or afternoon?",
                    "variable_name": "choice",
                    "expected_answers": ["morning", "afternoon"],
                },
                "transitions": [
                    {
                        "target_node_id": "route-choice",
                        "label": None,
                        "condition": None,
                        "is_fallback": False,
                    }
                ],
            },
            {
                "id": "route-choice",
                "type": "condition",
                "name": "Route choice",
                "config": {"variable_name": "choice"},
                "transitions": [
                    {
                        "target_node_id": "complete",
                        "label": "Morning",
                        "condition": "choice == 'morning'",
                        "is_fallback": False,
                    },
                    {
                        "target_node_id": "complete",
                        "label": "Fallback",
                        "condition": None,
                        "is_fallback": True,
                    },
                ],
            },
            {
                "id": "complete",
                "type": "end",
                "name": "Complete",
                "config": {"outcome": "choice_recorded"},
                "transitions": [],
            },
        ],
    }


class FakeResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body
        self.text = body
        self.status_code = status
        self.request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")

    def json(self) -> object:
        import json

        return json.loads(self._body)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "HTTP error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )


class FakeClient:
    def __init__(self, body: str, status: int = 200) -> None:
        self.body = body
        self.status = status

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def post(self, url: str, headers: dict[str, str], json: object) -> FakeResponse:
        return FakeResponse(self.body, self.status)


class FakeClientFactory:
    def __init__(self, body: str, status: int = 200) -> None:
        self.body = body
        self.status = status

    def __call__(self) -> FakeClient:
        return FakeClient(self.body, self.status)


class RaisingClient:
    def __init__(self, exception: Exception) -> None:
        self.exception = exception

    def __enter__(self) -> "RaisingClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def post(self, url: str, headers: dict[str, str], json: object) -> FakeResponse:
        raise self.exception


class RaisingClientFactory:
    def __init__(self, exception: Exception) -> None:
        self.exception = exception

    def __call__(self) -> RaisingClient:
        return RaisingClient(self.exception)
