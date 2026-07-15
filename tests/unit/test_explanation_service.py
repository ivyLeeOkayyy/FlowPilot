from copy import deepcopy
import json
from pathlib import Path

from app.models import AutomationFlow
from app.services import FlowExplanationService


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
            "id": "explanation-test-flow",
            "name": "Explanation test flow",
            "trigger_node_id": "trigger",
            "metadata": {"assumptions": ["Demo assumption."]},
            "nodes": nodes,
        }
    )


def explain(flow: AutomationFlow):
    return FlowExplanationService().explain(flow)


def lead_routing_flow() -> AutomationFlow:
    return AutomationFlow.model_validate(
        json.loads(Path("examples/lead-routing.json").read_text())
    )


def test_lead_routing_summary_is_accurate() -> None:
    explanation = explain(lead_routing_flow())

    assert "new contact sends a message" in explanation.summary
    assert "buyer" in explanation.summary.lower()
    assert "seller" in explanation.summary.lower()
    assert "sales" in explanation.summary.lower()


def test_trigger_description_is_readable() -> None:
    explanation = explain(lead_routing_flow())

    assert explanation.trigger_description == (
        "The workflow starts when a new contact sends a message."
    )


def test_only_reachable_nodes_are_in_steps() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("done")],
            ),
            node("done", "end", {"outcome": "complete"}),
            node("orphan", "end", {"outcome": "unreachable"}),
        ]
    )

    explanation = explain(flow)

    assert [step.node_id for step in explanation.steps] == ["trigger", "done"]


def test_breadth_first_ordering_is_deterministic() -> None:
    flow = flow_from_nodes(
        [
            node(
                "trigger",
                "trigger",
                {"event": "new_message"},
                transitions=[transition("left"), transition("right")],
            ),
            node("left", "send_message", {"message": "Left"}, transitions=[transition("end-left")]),
            node("right", "send_message", {"message": "Right"}, transitions=[transition("end-right")]),
            node("end-left", "end", {"outcome": "left_done"}),
            node("end-right", "end", {"outcome": "right_done"}),
        ]
    )

    explanation = explain(flow)

    assert [step.node_id for step in explanation.steps] == [
        "trigger",
        "left",
        "right",
        "end-left",
        "end-right",
    ]


def test_each_reachable_node_appears_once() -> None:
    explanation = explain(lead_routing_flow())
    node_ids = [step.node_id for step in explanation.steps]

    assert len(node_ids) == len(set(node_ids))


def test_send_message_includes_message_content() -> None:
    explanation = explain(lead_routing_flow())
    step = next(step for step in explanation.steps if step.node_id == "seller-help")

    assert "Here is a help article for sellers." in step.description


def test_ask_question_includes_variable_and_expected_answers() -> None:
    explanation = explain(lead_routing_flow())
    step = next(step for step in explanation.steps if step.node_id == "ask-contact-type")

    assert "contact_type" in step.description
    assert "buyer and seller" in step.description


def test_free_text_question_explanation_when_expected_answers_empty() -> None:
    flow = flow_from_nodes(
        [
            node("trigger", "trigger", {"event": "new_message"}, transitions=[transition("ask")]),
            node(
                "ask",
                "ask_question",
                {"question": "How can we help?", "variable_name": "request"},
                transitions=[transition("done")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    step = next(step for step in explain(flow).steps if step.node_id == "ask")

    assert "free-text" in step.description


def test_condition_explanation_includes_conditional_and_fallback_branches() -> None:
    step = next(
        step for step in explain(lead_routing_flow()).steps if step.node_id == "route-contact-type"
    )

    assert "contact_type == 'buyer'" in step.description
    assert "fallback" in step.description


def test_assign_to_team_includes_team_name() -> None:
    step = next(step for step in explain(lead_routing_flow()).steps if step.node_id == "route-buyer")

    assert "sales team" in step.description


def test_wait_explanation_states_no_real_sleep() -> None:
    flow = flow_from_nodes(
        [
            node("trigger", "trigger", {"event": "new_message"}, transitions=[transition("wait")]),
            node("wait", "wait", {"duration_seconds": 10}, transitions=[transition("done")]),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    step = next(step for step in explain(flow).steps if step.node_id == "wait")

    assert "10 seconds" in step.description
    assert "does not actually sleep" in step.description


def test_end_explanation_includes_outcome() -> None:
    step = next(step for step in explain(lead_routing_flow()).steps if step.node_id == "buyer-complete")

    assert "buyer routed to sales" in step.description


def test_api_call_explanation_states_execution_is_mocked() -> None:
    flow = api_flow("https://api.example.test/orders")

    step = next(step for step in explain(flow).steps if step.node_id == "api")

    assert "mocked GET request" in step.description
    assert "does not perform a real network request" in step.description


def test_api_call_query_parameter_values_are_redacted() -> None:
    flow = api_flow("https://api.example.test/orders?token=secret&customer_id=123")

    step = next(step for step in explain(flow).steps if step.node_id == "api")

    assert "secret" not in step.description
    assert "123" not in step.description
    assert "customer_id=<redacted>" in step.description
    assert "token=<redacted>" in step.description


def api_flow(url: str) -> AutomationFlow:
    return flow_from_nodes(
        [
            node("trigger", "trigger", {"event": "new_message"}, transitions=[transition("api")]),
            node(
                "api",
                "api_call",
                {
                    "method": "GET",
                    "url": url,
                    "timeout_seconds": 5,
                    "mock_success_response": {"ok": True},
                    "mock_failure_status": 500,
                },
                transitions=[
                    transition("done", label="success"),
                    transition("failed", label="failure"),
                ],
            ),
            node("done", "end", {"outcome": "success"}),
            node("failed", "end", {"outcome": "failure"}),
        ]
    )


def test_dangling_transitions_do_not_crash_explanation() -> None:
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

    explanation = explain(flow)

    assert explanation.steps[0].next_steps == ["Continue to missing (missing node)."]


def test_unreachable_nodes_appear_as_risks_but_not_steps() -> None:
    flow = flow_from_nodes(
        [
            node("trigger", "trigger", {"event": "new_message"}, transitions=[transition("done")]),
            node("done", "end", {"outcome": "complete"}),
            node("orphan", "end", {"outcome": "unreachable"}),
        ]
    )

    explanation = explain(flow)

    assert "orphan" not in [step.node_id for step in explanation.steps]
    assert any(risk.code == "UNREACHABLE_NODE" and risk.node_id == "orphan" for risk in explanation.risks)


def test_validation_errors_set_is_safe_to_simulate_false() -> None:
    flow = flow_from_nodes(
        [
            node("trigger", "trigger", {"event": "new_message"}, transitions=[transition("missing")])
        ]
    )

    assert explain(flow).is_safe_to_simulate is False


def test_warning_only_flow_remains_safe_to_simulate() -> None:
    flow = flow_from_nodes(
        [
            node("trigger", "trigger", {"event": "new_message"}, transitions=[transition("route")]),
            node(
                "route",
                "condition",
                {"variable_name": "kind"},
                transitions=[transition("done", condition="kind == 'known'")],
            ),
            node("done", "end", {"outcome": "complete"}),
        ]
    )

    assert explain(flow).is_safe_to_simulate is True


def test_risks_preserve_fields() -> None:
    flow = flow_from_nodes(
        [
            node("trigger", "trigger", {"event": "new_message"}, transitions=[transition("missing")])
        ]
    )

    risk = next(risk for risk in explain(flow).risks if risk.code == "DANGLING_TRANSITION")

    assert risk.severity == "error"
    assert risk.node_id == "trigger"
    assert "missing" in risk.summary
    assert risk.recommendation is None


def test_outcomes_include_only_reachable_end_nodes() -> None:
    flow = flow_from_nodes(
        [
            node("trigger", "trigger", {"event": "new_message"}, transitions=[transition("done")]),
            node("done", "end", {"outcome": "reachable_done"}),
            node("orphan", "end", {"outcome": "unreachable_done"}),
        ]
    )

    assert explain(flow).outcomes == ["reachable done"]


def test_assumptions_are_copied() -> None:
    assert explain(lead_routing_flow()).assumptions == [
        "Buyer and seller are the expected lead categories.",
        "Unexpected answers should be clarified before routing.",
    ]


def test_relevant_notes_are_included() -> None:
    notes = explain(lead_routing_flow()).notes

    assert "Conditions support only a constrained syntax during simulation." in notes
    assert "Repeated question input is reused by node ID in the current simulator." in notes


def test_irrelevant_notes_are_omitted() -> None:
    notes = explain(flow_from_nodes([
        node("trigger", "trigger", {"event": "new_message"}, transitions=[transition("done")]),
        node("done", "end", {"outcome": "complete"}),
    ])).notes

    assert notes == []


def test_explanation_does_not_mutate_flow() -> None:
    flow = lead_routing_flow()
    before = deepcopy(flow.model_dump(mode="json"))

    explain(flow)

    assert flow.model_dump(mode="json") == before


def test_repeated_calls_return_equivalent_output() -> None:
    flow = lead_routing_flow()

    first = explain(flow)
    second = explain(flow)

    assert first == second
