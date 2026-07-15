import json
from pathlib import Path

from app.models import (
    AskQuestionConfig,
    AssignToTeamConfig,
    AutomationFlow,
    EndConfig,
    NodeType,
)


def test_lead_routing_example_validates_as_automation_flow() -> None:
    example_path = Path("examples/lead-routing.json")
    example_data = json.loads(example_path.read_text())

    flow = AutomationFlow.model_validate(example_data)

    assert flow.id == "lead-routing"
    assert flow.name == "Lead routing"
    assert flow.trigger_node_id == "new-contact"
    assert isinstance(flow.version, int)
    assert flow.metadata.created_at.tzinfo is not None
    assert flow.metadata.created_at.utcoffset() is not None
    assert flow.nodes[0].type is NodeType.TRIGGER

    route_node = next(node for node in flow.nodes if node.id == "route-contact-type")
    fallback_transition = next(
        transition for transition in route_node.transitions if transition.is_fallback
    )
    assert fallback_transition.target_node_id == "clarify-contact-type"

    ask_node = next(node for node in flow.nodes if node.type is NodeType.ASK_QUESTION)
    assert isinstance(ask_node.config, AskQuestionConfig)
    assert ask_node.config.variable_name == "contact_type"
    assert ask_node.config.expected_answers == ["buyer", "seller"]

    buyer_node = next(node for node in flow.nodes if node.type is NodeType.ASSIGN_TO_TEAM)
    assert isinstance(buyer_node.config, AssignToTeamConfig)
    assert buyer_node.config.team_name == "sales"

    end_nodes = [node for node in flow.nodes if node.type is NodeType.END]
    assert end_nodes
    assert all(isinstance(node.config, EndConfig) for node in end_nodes)
    assert {node.config.outcome for node in end_nodes} == {
        "buyer_routed_to_sales",
        "seller_help_article_sent",
    }


def test_lead_routing_example_round_trips_through_serialization() -> None:
    example_path = Path("examples/lead-routing.json")
    example_data = json.loads(example_path.read_text())
    flow = AutomationFlow.model_validate(example_data)

    serialized = flow.model_dump(mode="json")
    reparsed_flow = AutomationFlow.model_validate(serialized)

    assert reparsed_flow == flow
