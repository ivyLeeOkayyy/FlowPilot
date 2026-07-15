import pytest
from pydantic import ValidationError

from app.models import AutomationFlow, FlowNode, NodeType


def test_public_workflow_model_imports() -> None:
    assert AutomationFlow.__name__ == "AutomationFlow"
    assert FlowNode.__name__ == "FlowNode"
    assert NodeType.TRIGGER == "trigger"


def test_automation_flow_public_fields_are_exact() -> None:
    assert set(AutomationFlow.model_fields.keys()) == {
        "id",
        "name",
        "description",
        "version",
        "trigger_node_id",
        "nodes",
        "metadata",
    }


def make_minimal_flow() -> dict:
    return {
        "id": "minimal-flow",
        "name": "Minimal flow",
        "trigger_node_id": "trigger",
        "nodes": [
            {
                "id": "trigger",
                "type": "trigger",
                "name": "Start",
                "config": {"event": "new_message"},
            }
        ],
    }


def test_duplicate_node_ids_fail() -> None:
    flow_data = make_minimal_flow()
    flow_data["nodes"].append(
        {
            "id": "trigger",
            "type": "end",
            "name": "Duplicate ID",
            "config": {"outcome": "done"},
        }
    )

    with pytest.raises(ValidationError):
        AutomationFlow.model_validate(flow_data)


def test_multiple_trigger_nodes_fail() -> None:
    flow_data = make_minimal_flow()
    flow_data["nodes"].append(
        {
            "id": "second-trigger",
            "type": "trigger",
            "name": "Second trigger",
            "config": {"event": "another_message"},
        }
    )

    with pytest.raises(ValidationError):
        AutomationFlow.model_validate(flow_data)


def test_trigger_node_id_referencing_non_trigger_node_fails() -> None:
    flow_data = make_minimal_flow()
    flow_data["trigger_node_id"] = "not-trigger"
    flow_data["nodes"].append(
        {
            "id": "not-trigger",
            "type": "end",
            "name": "Not a trigger",
            "config": {"outcome": "done"},
        }
    )

    with pytest.raises(ValidationError):
        AutomationFlow.model_validate(flow_data)


def test_type_config_mismatches_fail() -> None:
    flow_data = make_minimal_flow()
    flow_data["nodes"][0]["config"] = {"message": "wrong config"}

    with pytest.raises(ValidationError):
        AutomationFlow.model_validate(flow_data)
