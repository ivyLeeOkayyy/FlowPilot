from copy import deepcopy

from app.models import (
    ApiCallConfig,
    AutomationFlow,
    FlowNode,
    NodeType,
    SendMessageConfig,
)
from app.services import FlowValidationService


def transition(target: str, **overrides: object) -> dict[str, object]:
    return {"target_node_id": target, **overrides}


def node(
    node_id: str,
    node_type: str,
    config: dict[str, object],
    *,
    name: str | None = None,
    transitions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        "id": node_id,
        "type": node_type,
        "name": name or node_id.replace("-", " ").title(),
        "config": config,
    }
    if transitions is not None:
        data["transitions"] = transitions
    return data


def flow_from_nodes(
    nodes: list[dict[str, object]],
    *,
    trigger_node_id: str = "trigger",
) -> AutomationFlow:
    return AutomationFlow.model_validate(
        {
            "id": "test-flow",
            "name": "Test flow",
            "trigger_node_id": trigger_node_id,
            "nodes": nodes,
        }
    )


def validate(flow: AutomationFlow):
    return FlowValidationService().validate(flow)


def finding_codes(flow: AutomationFlow) -> list[str]:
    return [finding.code for finding in validate(flow).findings]


def valid_acyclic_flow() -> AutomationFlow:
    return flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("message")],
            ),
            node(
                "message",
                "send_message",
                {"message": "Hello"},
                transitions=[transition("done")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )


def test_valid_acyclic_flow_has_no_findings() -> None:
    result = validate(valid_acyclic_flow())

    assert result.is_valid is True
    assert result.findings == []


def test_dangling_transition() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("missing")],
            )
        ]
    )

    codes = finding_codes(flow)

    assert "DANGLING_TRANSITION" in codes
    assert validate(flow).is_valid is False


def test_unreachable_node() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("done")],
            ),
            node("done", "end", {"outcome": "complete"}),
            node("orphan", "end", {"outcome": "orphaned"}),
        ]
    )

    assert "UNREACHABLE_NODE" in finding_codes(flow)


def test_condition_missing_fallback() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("route")],
            ),
            node(
                "route",
                "condition",
                {"variable_name": "intent"},
                transitions=[
                    transition(
                        "done",
                        label="Known",
                        condition="intent == 'known'",
                    )
                ],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    result = validate(flow)

    assert "MISSING_FALLBACK" in [finding.code for finding in result.findings]
    assert result.is_valid is True


def test_condition_with_multiple_fallbacks() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("route")],
            ),
            node(
                "route",
                "condition",
                {"variable_name": "intent"},
                transitions=[
                    transition("fallback-one", is_fallback=True),
                    transition("fallback-two", is_fallback=True),
                ],
            ),
            node("fallback-one", "end", {"outcome": "one"}),
            node("fallback-two", "end", {"outcome": "two"}),
        ]
    )

    result = validate(flow)

    assert "MULTIPLE_FALLBACKS" in [finding.code for finding in result.findings]
    assert result.is_valid is False


def test_condition_without_transitions() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("route")],
            ),
            node("route", "condition", {"variable_name": "intent"}),
        ]
    )

    assert "CONDITION_WITHOUT_TRANSITIONS" in finding_codes(flow)


def test_end_node_with_transitions() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("done")],
            ),
            node(
                "done",
                "end",
                {"outcome": "complete"},
                transitions=[transition("trigger")],
            ),
        ]
    )

    assert "END_NODE_HAS_TRANSITIONS" in finding_codes(flow)


def test_non_end_dead_end_node() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("message")],
            ),
            node("message", "send_message", {"message": "Hello"}),
        ]
    )

    assert "DEAD_END_NODE" in finding_codes(flow)


def test_reachable_node_with_no_terminal_path() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("wait")],
            ),
            node(
                "wait",
                "wait",
                {"duration_seconds": 1},
                transitions=[transition("trigger")],
            ),
        ]
    )

    assert "NO_TERMINAL_PATH" in finding_codes(flow)


def test_intentional_clarification_cycle_warns_but_remains_valid() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("ask")],
            ),
            node(
                "ask",
                "ask_question",
                {
                    "question": "Buyer or seller?",
                    "variable_name": "lead_type",
                    "expected_answers": ["buyer", "seller"],
                },
                transitions=[transition("route")],
            ),
            node(
                "route",
                "condition",
                {"variable_name": "lead_type"},
                transitions=[
                    transition(
                        "done",
                        label="Buyer",
                        condition="lead_type == 'buyer'",
                    ),
                    transition("clarify", label="Other", is_fallback=True),
                ],
            ),
            node(
                "clarify",
                "send_message",
                {"message": "Please answer buyer or seller."},
                transitions=[transition("ask")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    result = validate(flow)

    assert "SUSPICIOUS_CYCLE" in [finding.code for finding in result.findings]
    assert result.is_valid is True


def test_duplicate_transition() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[
                    transition("done", condition="ok", is_fallback=False),
                    transition("done", condition="ok", is_fallback=False),
                ],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    assert "DUPLICATE_TRANSITION" in finding_codes(flow)


def test_api_call_missing_success_path() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("api")],
            ),
            node(
                "api",
                "api_call",
                {
                    "method": "GET",
                    "url": "https://example.invalid/status",
                    "timeout_seconds": 5,
                    "mock_success_response": {"ok": True},
                    "mock_failure_status": 500,
                },
                transitions=[transition("done", label="failure")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    assert "API_CALL_MISSING_SUCCESS_PATH" in finding_codes(flow)


def test_api_call_missing_failure_path() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("api")],
            ),
            node(
                "api",
                "api_call",
                {
                    "method": "GET",
                    "url": "https://example.invalid/status",
                    "timeout_seconds": 5,
                    "mock_success_response": {"ok": True},
                    "mock_failure_status": 500,
                },
                transitions=[transition("done", label="success")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    assert "API_CALL_MISSING_FAILURE_PATH" in finding_codes(flow)


def test_ask_question_without_expected_answers() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("ask")],
            ),
            node(
                "ask",
                "ask_question",
                {
                    "question": "What do you need?",
                    "variable_name": "request",
                },
                transitions=[transition("done")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    assert "QUESTION_WITHOUT_EXPECTED_ANSWERS" in finding_codes(flow)


def test_unused_question_variable() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("ask")],
            ),
            node(
                "ask",
                "ask_question",
                {
                    "question": "Buyer or seller?",
                    "variable_name": "lead_type",
                    "expected_answers": ["buyer", "seller"],
                },
                transitions=[transition("done")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    assert "UNUSED_VARIABLE" in finding_codes(flow)


def test_empty_message_resiliency_for_constructed_objects() -> None:
    flow = AutomationFlow.model_construct(
        id="constructed-flow",
        name="Constructed flow",
        trigger_node_id="trigger",
        nodes=[
            FlowNode.model_construct(
                id="trigger",
                type=NodeType.TRIGGER,
                name="Trigger",
                config={"event": "new_message"},
                transitions=[],
            ),
            FlowNode.model_construct(
                id="message",
                type=NodeType.SEND_MESSAGE,
                name="Message",
                config=SendMessageConfig.model_construct(message=" "),
                transitions=[],
            ),
            FlowNode.model_construct(
                id="done",
                type=NodeType.END,
                name="Done",
                config={"outcome": "complete"},
                transitions=[],
            ),
        ],
    )

    assert "EMPTY_MESSAGE" in finding_codes(flow)


def test_multiple_errors_make_result_invalid() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("missing")],
            )
        ]
    )

    result = validate(flow)

    assert result.is_valid is False
    assert sum(finding.severity == "error" for finding in result.findings) > 1


def test_warnings_only_keep_result_valid() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("route")],
            ),
            node(
                "route",
                "condition",
                {"variable_name": "intent"},
                transitions=[transition("done", condition="intent == 'known'")],
            ),
            node("done", "end", {"outcome": "complete"}),
            node("orphan", "end", {"outcome": "unused"}),
        ]
    )

    result = validate(flow)

    assert result.is_valid is True
    assert {finding.severity for finding in result.findings} == {"warning"}


def test_deterministic_finding_ordering() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("beta")],
            ),
            node("beta", "send_message", {"message": "Beta"}),
            node("alpha", "send_message", {"message": "Alpha"}),
        ]
    )

    findings = validate(flow).findings
    sort_keys = [
        (
            {"error": 0, "warning": 1, "info": 2}[finding.severity],
            finding.node_id or "",
            finding.code or "",
            finding.message,
        )
        for finding in findings
    ]

    assert sort_keys == sorted(sort_keys)


def test_validator_does_not_mutate_input_flow() -> None:
    flow = valid_acyclic_flow()
    before = deepcopy(flow.model_dump(mode="json"))

    validate(flow)

    assert flow.model_dump(mode="json") == before
