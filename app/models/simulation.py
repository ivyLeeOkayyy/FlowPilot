from enum import StrEnum
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.workflow import AutomationFlow, NodeType


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SimulationStatus(StrEnum):
    COMPLETED = "completed"
    WAITING_FOR_INPUT = "waiting_for_input"
    FAILED = "failed"
    STEP_LIMIT_EXCEEDED = "step_limit_exceeded"


class TranscriptRole(StrEnum):
    SYSTEM = "system"
    BOT = "bot"
    USER = "user"


class TranscriptEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: Annotated[int, Field(gt=0)]
    node_id: NonEmptyString
    role: TranscriptRole
    message: NonEmptyString


class ExecutionTraceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: Annotated[int, Field(gt=0)]
    node_id: NonEmptyString
    node_type: NodeType
    action: NonEmptyString
    selected_transition_target: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class MockApiOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: NonEmptyString
    success: bool
    status_code: Annotated[int, Field(ge=100, le=599)]
    response: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_status_matches_success(self) -> "MockApiOutcome":
        if self.success and self.status_code >= 400:
            raise ValueError("successful mock API outcomes must use status_code < 400")
        if not self.success and self.status_code < 400:
            raise ValueError("failed mock API outcomes must use status_code >= 400")
        return self


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: AutomationFlow
    user_inputs: dict[str, str] = Field(default_factory=dict)
    api_outcomes: dict[str, MockApiOutcome] = Field(default_factory=dict)
    initial_variables: dict[str, Any] = Field(default_factory=dict)
    max_steps: Annotated[int, Field(ge=1, le=500)] = 50

    @model_validator(mode="after")
    def validate_api_outcome_keys(self) -> "SimulationRequest":
        for key, outcome in self.api_outcomes.items():
            if outcome.node_id != key:
                raise ValueError(
                    f"api_outcomes key '{key}' must match outcome node_id "
                    f"'{outcome.node_id}'"
                )
        return self


class SimulationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: NonEmptyString = Field(default_factory=lambda: str(uuid4()))
    status: SimulationStatus
    current_node_id: str | None = None
    completed_outcome: str | None = None
    assigned_team: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    transcript: list[TranscriptEntry] = Field(default_factory=list)
    trace: list[ExecutionTraceEntry] = Field(default_factory=list)
    steps_executed: Annotated[int, Field(ge=0)]
    error_code: str | None = None
    error_message: str | None = None
