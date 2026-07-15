from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models.explanation import FlowExplanation
from app.models.validation import FlowValidationResult
from app.models.workflow import AutomationFlow


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class GenerationMode(StrEnum):
    MOCK = "mock"
    LLM = "llm"


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: NonEmptyString
    mode: GenerationMode = GenerationMode.MOCK
    flow_name: str | None = None
    include_explanation: bool = True

    @field_validator("prompt", mode="before")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class GenerationStatus(StrEnum):
    GENERATED = "generated"
    GENERATED_WITH_WARNINGS = "generated_with_warnings"
    CLARIFICATION_REQUIRED = "clarification_required"
    FAILED = "failed"


class GenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: GenerationStatus
    flow: AutomationFlow | None = None
    validation: FlowValidationResult | None = None
    explanation: FlowExplanation | None = None
    clarification_question: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    provider: NonEmptyString
    model_name: str | None = None
    error_code: str | None = None
    error_message: str | None = None
