from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: ValidationSeverity
    message: str
    node_id: str | None = None
    code: str | None = None


class FlowValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    findings: list[ValidationFinding] = Field(default_factory=list)
