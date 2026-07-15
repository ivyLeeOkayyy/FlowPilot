from enum import StrEnum
from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class NodeType(StrEnum):
    TRIGGER = "trigger"
    SEND_MESSAGE = "send_message"
    ASK_QUESTION = "ask_question"
    CONDITION = "condition"
    API_CALL = "api_call"
    ASSIGN_TO_TEAM = "assign_to_team"
    WAIT = "wait"
    END = "end"


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class FlowMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_prompt: str | None = None
    generator: str = "manual"
    model_name: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Transition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_node_id: NonEmptyString
    label: str | None = None
    condition: str | None = None
    is_fallback: bool = False

    @field_validator("label", "condition", mode="before")
    @classmethod
    def normalize_blank_optional_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class TriggerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: NonEmptyString


class SendMessageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: NonEmptyString


class AskQuestionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: NonEmptyString
    variable_name: NonEmptyString
    expected_answers: list[str] = Field(default_factory=list)


class ConditionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable_name: NonEmptyString


class ApiCallConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: HttpMethod
    url: NonEmptyString
    timeout_seconds: Annotated[int, Field(gt=0)] = 10
    mock_success_response: dict[str, Any] = Field(default_factory=dict)
    mock_failure_status: Annotated[int, Field(ge=400, le=599)] = 500


class AssignToTeamConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_name: NonEmptyString


class WaitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_seconds: Annotated[int, Field(gt=0)]


class EndConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: NonEmptyString


NodeConfig = (
    TriggerConfig
    | SendMessageConfig
    | AskQuestionConfig
    | ConditionConfig
    | ApiCallConfig
    | AssignToTeamConfig
    | WaitConfig
    | EndConfig
)

NODE_CONFIG_BY_TYPE: dict[NodeType, type[BaseModel]] = {
    NodeType.TRIGGER: TriggerConfig,
    NodeType.SEND_MESSAGE: SendMessageConfig,
    NodeType.ASK_QUESTION: AskQuestionConfig,
    NodeType.CONDITION: ConditionConfig,
    NodeType.API_CALL: ApiCallConfig,
    NodeType.ASSIGN_TO_TEAM: AssignToTeamConfig,
    NodeType.WAIT: WaitConfig,
    NodeType.END: EndConfig,
}


class FlowNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    type: NodeType
    name: NonEmptyString
    config: NodeConfig
    transitions: list[Transition] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def validate_config_for_type(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        node_type = NodeType(data.get("type"))
        config_model = NODE_CONFIG_BY_TYPE[node_type]
        return {
            **data,
            "config": config_model.model_validate(data.get("config", {})),
        }


class AutomationFlow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    name: NonEmptyString
    description: str | None = None
    version: Annotated[int, Field(gt=0)] = 1
    trigger_node_id: NonEmptyString
    nodes: Annotated[list[FlowNode], Field(min_length=1)]
    metadata: FlowMetadata = Field(default_factory=FlowMetadata)

    @model_validator(mode="after")
    def validate_trigger_contract(self) -> "AutomationFlow":
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("node IDs must be unique")

        nodes_by_id = {node.id: node for node in self.nodes}
        trigger_node = nodes_by_id.get(self.trigger_node_id)
        if trigger_node is None:
            raise ValueError("trigger_node_id must reference an existing node")

        if trigger_node.type is not NodeType.TRIGGER:
            raise ValueError("trigger_node_id must reference a trigger node")

        trigger_count = sum(node.type is NodeType.TRIGGER for node in self.nodes)
        if trigger_count != 1:
            raise ValueError("exactly one trigger node must exist")

        return self
