from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.validation import ValidationSeverity
from app.models.workflow import NodeType


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FlowStepExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: Annotated[int, Field(gt=0)]
    node_id: NonEmptyString
    node_type: NodeType
    title: NonEmptyString
    description: NonEmptyString
    next_steps: list[str] = Field(default_factory=list)


class RiskExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: NonEmptyString
    severity: ValidationSeverity
    node_id: str | None = None
    summary: NonEmptyString
    recommendation: str | None = None


class FlowExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_id: NonEmptyString
    flow_name: NonEmptyString
    summary: NonEmptyString
    trigger_description: NonEmptyString
    steps: list[FlowStepExplanation] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[RiskExplanation] = Field(default_factory=list)
    is_safe_to_simulate: bool
    notes: list[str] = Field(default_factory=list)
