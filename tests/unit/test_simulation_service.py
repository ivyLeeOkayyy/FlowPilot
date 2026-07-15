from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models import AutomationFlow, MockApiOutcome, SimulationRequest, SimulationStatus
from app.services import FlowSimulationService


def transition(target: str, **overrides: object) -> dict[str, object]:
    return {"target_node_id": target, **overrides}


def node(
    node_id: str,
    node_type: str,
    config: dict[str, object],
    *,
    transitions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {
        "id": node_id,
        "type": node_type,
        "name": node_id.replace("-", " ").title(),
        "config": config,
    }
    if transitions is not None:
        data["transitions"] = transitions
    return data


def flow_from_nodes(nodes: list[dict[str, object]]) -> AutomationFlow:
    return AutomationFlow.model_validate(
        {
            "id": "simulation-test-flow",
            "name": "Simulation test flow",
            "trigger_node_id": "trigger",
            "nodes": nodes,
        }
    )


def request_for(
    flow: AutomationFlow,
    *,
    user_inputs: dict[str, str] | None = None,
    api_outcomes: dict[str, MockApiOutcome] | None = None,
    initial_variables: dict[str, object] | None = None,
    max_steps: int = 50,
) -> SimulationRequest:
    return SimulationRequest(
        flow=flow,
        user_inputs=user_inputs or {},
        api_outcomes=api_outcomes or {},
        initial_variables=initial_variables or {},
        max_steps=max_steps,
    )


def simulate(request: SimulationRequest):
    return FlowSimulationService().simulate(request)


def basic_message_flow() -> AutomationFlow:
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


def lead_routing_request(answer: str, max_steps: int = 50) -> SimulationRequest:
    flow_data = json.loads(Path("examples/lead-routing.json").read_text())
    return SimulationRequest.model_validate(
        {
            "flow": flow_data,
            "user_inputs": {"ask-contact-type": answer},
            "max_steps": max_steps,
        }
    )


def test_validation_errors_block_execution() -> None:
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

    result = simulate(request_for(flow))

    assert result.status is SimulationStatus.FAILED
    assert result.error_code == "FLOW_VALIDATION_FAILED"
    assert result.steps_executed == 0


def test_trigger_execution_records_trace() -> None:
    result = simulate(request_for(basic_message_flow()))

    assert result.trace[0].node_id == "trigger"
    assert result.trace[0].action == "triggered"
    assert result.trace[0].details["event"] == "new_message"


def test_send_message_adds_transcript_entry() -> None:
    result = simulate(request_for(basic_message_flow()))

    assert any(entry.role == "bot" and entry.message == "Hello" for entry in result.transcript)


def test_ask_question_waits_when_no_answer_exists() -> None:
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
                {"question": "What do you need?", "variable_name": "need"},
                transitions=[transition("done")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    result = simulate(request_for(flow))

    assert result.status is SimulationStatus.WAITING_FOR_INPUT
    assert result.current_node_id == "ask"


def test_ask_question_stores_supplied_answer() -> None:
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
                {"question": "What do you need?", "variable_name": "need"},
                transitions=[transition("done")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    result = simulate(request_for(flow, user_inputs={"ask": "pricing"}))

    assert result.variables["need"] == "pricing"
    assert any(entry.role == "user" and entry.message == "pricing" for entry in result.transcript)


def test_buyer_path_completes_and_assigns_sales_team() -> None:
    result = simulate(lead_routing_request("buyer"))

    assert result.status is SimulationStatus.COMPLETED
    assert result.assigned_team == "sales"
    assert result.completed_outcome == "buyer_routed_to_sales"


def test_seller_path_completes_and_sends_help_message() -> None:
    result = simulate(lead_routing_request("seller"))

    assert result.status is SimulationStatus.COMPLETED
    assert result.completed_outcome == "seller_help_article_sent"
    assert any("help article" in entry.message for entry in result.transcript)


def test_unexpected_answer_follows_fallback() -> None:
    result = simulate(lead_routing_request("partner", max_steps=5))

    assert any(
        entry.node_id == "route-contact-type"
        and entry.selected_transition_target == "clarify-contact-type"
        for entry in result.trace
    )


def test_repeated_fallback_loop_reaches_step_limit() -> None:
    result = simulate(lead_routing_request("partner", max_steps=8))

    assert result.status is SimulationStatus.STEP_LIMIT_EXCEEDED
    assert result.error_code == "STEP_LIMIT_EXCEEDED"
    assert sum(entry.node_id == "ask-contact-type" for entry in result.transcript) > 1


def condition_flow(condition: str, fallback: bool = False) -> AutomationFlow:
    transitions = [transition("done", condition=condition)]
    if fallback:
        transitions.append(transition("fallback-done", is_fallback=True))
    nodes = [
        node(
            "trigger",
            "trigger",
            {"event": "new_message"},
            transitions=[transition("route")],
        ),
        node(
            "route",
            "condition",
            {"variable_name": "status"},
            transitions=transitions,
        ),
        node("done", "end", {"outcome": "matched"}),
    ]
    if fallback:
        nodes.append(node("fallback-done", "end", {"outcome": "fallback"}))
    return flow_from_nodes(nodes)


def test_condition_equality_with_single_quotes() -> None:
    result = simulate(
        request_for(condition_flow("status == 'open'"), initial_variables={"status": "open"})
    )

    assert result.completed_outcome == "matched"


def test_condition_equality_with_double_quotes() -> None:
    result = simulate(
        request_for(condition_flow('status == "open"'), initial_variables={"status": "open"})
    )

    assert result.completed_outcome == "matched"


def test_condition_inequality() -> None:
    result = simulate(
        request_for(condition_flow("status != 'closed'"), initial_variables={"status": "open"})
    )

    assert result.completed_outcome == "matched"


def test_unsupported_condition_syntax_uses_fallback_without_executing_code() -> None:
    result = simulate(
        request_for(
            condition_flow("__import__('os').system('echo unsafe')", fallback=True),
            initial_variables={"status": "open"},
        )
    )

    assert result.completed_outcome == "fallback"


def test_absent_variable_uses_fallback_when_available() -> None:
    result = simulate(request_for(condition_flow("status == 'open'", fallback=True)))

    assert result.completed_outcome == "fallback"


def test_absent_variable_without_fallback_fails() -> None:
    result = simulate(request_for(condition_flow("status == 'open'")))

    assert result.status is SimulationStatus.FAILED
    assert result.error_code == "VARIABLE_NOT_FOUND"


def test_assign_to_team_records_team() -> None:
    result = simulate(lead_routing_request("buyer"))

    assignment_trace = next(entry for entry in result.trace if entry.node_id == "route-buyer")
    assert assignment_trace.details["team_name"] == "sales"
    assert result.assigned_team == "sales"


def api_flow(transitions: list[dict[str, object]]) -> AutomationFlow:
    return flow_from_nodes(
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
                transitions=transitions,
            ),
            node("success-done", "end", {"outcome": "api_success"}),
            node("failure-done", "end", {"outcome": "api_failure"}),
        ]
    )


def mock_outcome(success: bool) -> MockApiOutcome:
    return MockApiOutcome(
        node_id="api",
        success=success,
        status_code=200 if success else 500,
        response={"ok": success},
        error_message=None if success else "failed",
    )


def test_api_call_does_not_make_real_network_request() -> None:
    flow = api_flow(
        [
            transition("success-done", label="success"),
            transition("failure-done", label="failure"),
        ]
    )

    result = simulate(request_for(flow, api_outcomes={"api": mock_outcome(True)}))

    assert result.status is SimulationStatus.COMPLETED
    assert result.variables["api_results"]["api"]["status_code"] == 200


def test_missing_mock_api_outcome_fails() -> None:
    flow = api_flow(
        [
            transition("success-done", label="success"),
            transition("failure-done", label="failure"),
        ]
    )

    result = simulate(request_for(flow))

    assert result.status is SimulationStatus.FAILED
    assert result.error_code == "MOCK_API_OUTCOME_REQUIRED"


def test_successful_mock_api_outcome_follows_success_branch() -> None:
    flow = api_flow(
        [
            transition("success-done", label="ok 2xx"),
            transition("failure-done", label="error 5xx"),
        ]
    )

    result = simulate(request_for(flow, api_outcomes={"api": mock_outcome(True)}))

    assert result.completed_outcome == "api_success"


def test_failed_mock_api_outcome_follows_failure_branch() -> None:
    flow = api_flow(
        [
            transition("success-done", label="success"),
            transition("failure-done", condition="status >= 400"),
        ]
    )

    result = simulate(request_for(flow, api_outcomes={"api": mock_outcome(False)}))

    assert result.completed_outcome == "api_failure"


def test_missing_success_branch_fails_safely() -> None:
    flow = api_flow([transition("failure-done", label="failure")])

    result = simulate(request_for(flow, api_outcomes={"api": mock_outcome(True)}))

    assert result.status is SimulationStatus.FAILED
    assert result.error_code == "API_SUCCESS_PATH_NOT_FOUND"


def test_missing_failure_branch_fails_safely() -> None:
    flow = api_flow([transition("success-done", label="success")])

    result = simulate(request_for(flow, api_outcomes={"api": mock_outcome(False)}))

    assert result.status is SimulationStatus.FAILED
    assert result.error_code == "API_FAILURE_PATH_NOT_FOUND"


def test_wait_node_does_not_sleep() -> None:
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
                {"duration_seconds": 30},
                transitions=[transition("done")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    result = simulate(request_for(flow))

    wait_trace = next(entry for entry in result.trace if entry.node_id == "wait")
    assert wait_trace.details == {"duration_seconds": 30, "slept": False}


def test_end_node_completes_with_outcome() -> None:
    result = simulate(request_for(basic_message_flow()))

    assert result.status is SimulationStatus.COMPLETED
    assert result.completed_outcome == "complete"


def test_result_includes_trace_id() -> None:
    result = simulate(request_for(basic_message_flow()))

    assert result.trace_id


def test_trace_steps_are_deterministic() -> None:
    result = simulate(request_for(basic_message_flow()))

    assert [entry.step for entry in result.trace] == [1, 2, 3]
    assert [entry.node_id for entry in result.trace] == ["trigger", "message", "done"]


def test_simulation_does_not_mutate_flow_or_request_dictionaries() -> None:
    request = lead_routing_request("buyer")
    before_flow = request.flow.model_dump(mode="json")
    before_inputs = deepcopy(request.user_inputs)
    before_api_outcomes = deepcopy(request.api_outcomes)
    before_variables = deepcopy(request.initial_variables)

    simulate(request)

    assert request.flow.model_dump(mode="json") == before_flow
    assert request.user_inputs == before_inputs
    assert request.api_outcomes == before_api_outcomes
    assert request.initial_variables == before_variables


def test_max_steps_boundaries_are_enforced() -> None:
    flow = basic_message_flow()

    with pytest.raises(ValidationError):
        request_for(flow, max_steps=0)

    with pytest.raises(ValidationError):
        request_for(flow, max_steps=501)

    assert request_for(flow, max_steps=1).max_steps == 1
    assert request_for(flow, max_steps=500).max_steps == 500


def test_mock_api_outcome_rejects_contradictory_status() -> None:
    with pytest.raises(ValidationError):
        MockApiOutcome(node_id="api", success=True, status_code=500)

    with pytest.raises(ValidationError):
        MockApiOutcome(node_id="api", success=False, status_code=200)


def test_mock_api_outcome_key_must_match_node_id() -> None:
    with pytest.raises(ValidationError):
        request_for(
            basic_message_flow(),
            api_outcomes={
                "wrong": MockApiOutcome(
                    node_id="api",
                    success=True,
                    status_code=200,
                )
            },
        )
