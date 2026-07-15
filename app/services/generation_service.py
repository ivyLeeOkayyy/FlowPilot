import json
import logging
import os
from typing import Callable

from pydantic import ValidationError

from app.core.config import settings
from app.models import (
    AutomationFlow,
    FlowValidationResult,
    GenerationMode,
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    ValidationSeverity,
)
from app.services.explanation_service import FlowExplanationService
from app.services.providers import (
    DeepSeekProvider,
    GenerationProviderError,
    MockWorkflowGenerationProvider,
    WorkflowGenerationProvider,
)
from app.services.validation_service import FlowValidationService


ProviderFactory = Callable[[GenerationRequest], WorkflowGenerationProvider]
logger = logging.getLogger(__name__)


class FlowGenerationService:
    def __init__(
        self,
        validation_service: FlowValidationService | None = None,
        explanation_service: FlowExplanationService | None = None,
        mock_provider_factory: ProviderFactory | None = None,
        llm_provider_factory: ProviderFactory | None = None,
    ) -> None:
        self.validation_service = validation_service or FlowValidationService()
        self.explanation_service = explanation_service or FlowExplanationService()
        self.mock_provider_factory = mock_provider_factory or (
            lambda request: MockWorkflowGenerationProvider(flow_name=request.flow_name)
        )
        self.llm_provider_factory = llm_provider_factory or self._configured_llm_provider

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        try:
            provider = self._provider_for_request(request)
        except GenerationProviderError as exc:
            provider_name = self._configured_provider_name()
            logger.info(
                "Workflow generation provider selection failed: mode=%s provider=%s model=%s",
                request.mode.value,
                provider_name,
                None,
            )
            return GenerationResponse(
                status=GenerationStatus.FAILED,
                provider=provider_name,
                model_name=None,
                error_code=exc.code,
                error_message=exc.message,
            )

        logger.info(
            "Workflow generation requested: mode=%s provider=%s model=%s",
            request.mode.value,
            provider.provider_name,
            provider.model_name,
        )

        try:
            generated = provider.generate(request.prompt)
        except GenerationProviderError as exc:
            if exc.code == "CLARIFICATION_REQUIRED":
                return GenerationResponse(
                    status=GenerationStatus.CLARIFICATION_REQUIRED,
                    clarification_question=exc.message,
                    assumptions=[],
                    provider=provider.provider_name,
                    model_name=provider.model_name,
                )
            return GenerationResponse(
                status=GenerationStatus.FAILED,
                provider=provider.provider_name,
                model_name=provider.model_name,
                error_code=exc.code,
                error_message=exc.message,
            )

        return self._finalize_generated_flow(
            request=request,
            generated=generated,
            provider=provider.provider_name,
            model_name=provider.model_name,
        )

    def _provider_for_request(
        self, request: GenerationRequest
    ) -> WorkflowGenerationProvider:
        if request.mode is GenerationMode.MOCK:
            return self.mock_provider_factory(request)

        provider_name = self._configured_provider_name()
        if provider_name == "deepseek":
            return self.llm_provider_factory(request)

        raise GenerationProviderError(
            "LLM_NOT_CONFIGURED",
            (
                "LLM mode requires LLM_PROVIDER=deepseek. "
                f"Current configured provider is {provider_name!r}."
            ),
        )

    def _configured_provider_name(self) -> str:
        return (os.getenv("LLM_PROVIDER") or settings.llm_provider or "mock").lower()

    def _configured_llm_provider(
        self, request: GenerationRequest
    ) -> WorkflowGenerationProvider:
        return DeepSeekProvider()

    def _finalize_generated_flow(
        self,
        request: GenerationRequest,
        generated: dict,
        provider: str,
        model_name: str | None,
    ) -> GenerationResponse:
        try:
            flow = AutomationFlow.model_validate(generated)
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return GenerationResponse(
                status=GenerationStatus.FAILED,
                provider=provider,
                model_name=model_name,
                error_code="INVALID_GENERATED_FLOW",
                error_message=f"Generated flow could not be parsed: {exc}",
            )

        validation = self.validation_service.validate(flow)
        explanation = (
            self.explanation_service.explain(flow)
            if request.include_explanation
            else None
        )

        error_codes = [
            finding.code
            for finding in validation.findings
            if finding.severity is ValidationSeverity.ERROR and finding.code is not None
        ]
        if error_codes:
            return GenerationResponse(
                status=GenerationStatus.FAILED,
                flow=flow,
                validation=validation,
                explanation=explanation,
                assumptions=list(flow.metadata.assumptions),
                provider=provider,
                model_name=model_name,
                error_code="GENERATED_FLOW_INVALID",
                error_message=(
                    "Generated flow failed validation with errors: "
                    + ", ".join(sorted(error_codes))
                ),
            )

        status = (
            GenerationStatus.GENERATED_WITH_WARNINGS
            if validation.findings
            else GenerationStatus.GENERATED
        )
        return GenerationResponse(
            status=status,
            flow=flow,
            validation=validation,
            explanation=explanation,
            assumptions=list(flow.metadata.assumptions),
            provider=provider,
            model_name=model_name,
        )
