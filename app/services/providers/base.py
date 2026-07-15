from typing import Protocol


class GenerationProviderError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class WorkflowGenerationProvider(Protocol):
    provider_name: str
    model_name: str | None

    def generate(self, prompt: str) -> dict:
        """Return a raw workflow dictionary for later AutomationFlow validation."""
