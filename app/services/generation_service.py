from datetime import datetime, timezone
import json
import os
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.core.config import settings
from app.models import (
    AutomationFlow,
    FlowExplanation,
    FlowValidationResult,
    GenerationMode,
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    ValidationSeverity,
)
from app.services.explanation_service import FlowExplanationService
from app.services.validation_service import FlowValidationService


class FlowGenerationService:
    def __init__(
        self,
        validation_service: FlowValidationService | None = None,
        explanation_service: FlowExplanationService | None = None,
    ) -> None:
        self.validation_service = validation_service or FlowValidationService()
        self.explanation_service = explanation_service or FlowExplanationService()

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if request.mode is GenerationMode.LLM:
            return self._generate_with_llm(request)

        template = self._mock_template_for_prompt(request)
        if template is None:
            return GenerationResponse(
                status=GenerationStatus.CLARIFICATION_REQUIRED,
                clarification_question=(
                    "Should this workflow route leads, triage support requests, "
                    "or check order status?"
                ),
                assumptions=[],
                provider="mock",
            )

        return self._finalize_generated_template(
            request=request,
            template=template,
            provider="mock",
            model_name=None,
        )

    def _generate_with_llm(self, request: GenerationRequest) -> GenerationResponse:
        config = self._llm_config()
        if not all([config["base_url"], config["api_key"], config["model"]]):
            return GenerationResponse(
                status=GenerationStatus.FAILED,
                provider="llm",
                model_name=config["model"],
                error_code="LLM_NOT_CONFIGURED",
                error_message=(
                    "LLM mode requires LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL."
                ),
            )

        return GenerationResponse(
            status=GenerationStatus.FAILED,
            provider="llm",
            model_name=config["model"],
            error_code="LLM_NOT_CONFIGURED",
            error_message=(
                "LLM mode is intentionally disabled in this hackathon build; "
                "mock mode is the runnable generation path."
            ),
        )

    def _finalize_generated_template(
        self,
        request: GenerationRequest,
        template: dict[str, Any],
        provider: str,
        model_name: str | None,
    ) -> GenerationResponse:
        try:
            flow = AutomationFlow.model_validate(template)
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

    def _mock_template_for_prompt(
        self,
        request: GenerationRequest,
    ) -> dict[str, Any] | None:
        prompt = request.prompt.lower()
        if self._matches_order_status(prompt):
            return self._order_status_template(request)
        if self._matches_support_triage(prompt):
            return self._support_triage_template(request)
        if self._matches_lead_routing(prompt):
            return self._lead_routing_template(request)
        return None

    def _matches_lead_routing(self, prompt: str) -> bool:
        terms = ["buyer", "seller", "sales", "lead", "contact"]
        return sum(term in prompt for term in terms) >= 2

    def _matches_support_triage(self, prompt: str) -> bool:
        terms = ["billing", "account access", "support", "finance", "human agent"]
        return sum(term in prompt for term in terms) >= 2

    def _matches_order_status(self, prompt: str) -> bool:
        terms = ["order", "order id", "status", "api"]
        return "order" in prompt and sum(term in prompt for term in terms) >= 2

    def _base_flow(
        self,
        request: GenerationRequest,
        slug: str,
        default_name: str,
        assumptions: list[str],
    ) -> dict[str, Any]:
        return {
            "id": f"{slug}-{uuid4().hex[:8]}",
            "name": request.flow_name or default_name,
            "description": request.prompt,
            "version": 1,
            "metadata": {
                "source_prompt": request.prompt,
                "generator": "mock",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "assumptions": assumptions,
                "warnings": [],
            },
        }

    def _lead_routing_template(self, request: GenerationRequest) -> dict[str, Any]:
        flow = self._base_flow(
            request,
            "lead-routing",
            "Lead routing",
            [
                "Template selected because the prompt mentions lead/contact routing.",
                "Buyer and seller are treated as the expected lead categories.",
                "Unexpected answers are clarified and asked again.",
            ],
        )
        flow.update(
            {
                "trigger_node_id": "new-contact",
                "nodes": [
                    {
                        "id": "new-contact",
                        "type": "trigger",
                        "name": "New contact message",
                        "config": {"event": "new_contact_message"},
                        "transitions": [{"target_node_id": "ask-contact-type"}],
                    },
                    {
                        "id": "ask-contact-type",
                        "type": "ask_question",
                        "name": "Ask lead type",
                        "config": {
                            "question": "Are you a buyer or a seller?",
                            "variable_name": "contact_type",
                            "expected_answers": ["buyer", "seller"],
                        },
                        "transitions": [{"target_node_id": "route-contact-type"}],
                    },
                    {
                        "id": "route-contact-type",
                        "type": "condition",
                        "name": "Route lead type",
                        "config": {"variable_name": "contact_type"},
                        "transitions": [
                            {
                                "target_node_id": "route-buyer",
                                "label": "Buyer",
                                "condition": "contact_type == 'buyer'",
                            },
                            {
                                "target_node_id": "seller-help",
                                "label": "Seller",
                                "condition": "contact_type == 'seller'",
                            },
                            {
                                "target_node_id": "clarify-contact-type",
                                "label": "Unexpected answer",
                                "is_fallback": True,
                            },
                        ],
                    },
                    {
                        "id": "route-buyer",
                        "type": "assign_to_team",
                        "name": "Route buyer to sales",
                        "config": {"team_name": "sales"},
                        "transitions": [{"target_node_id": "buyer-complete"}],
                    },
                    {
                        "id": "seller-help",
                        "type": "send_message",
                        "name": "Send seller help article",
                        "config": {"message": "Here is a help article for sellers."},
                        "transitions": [{"target_node_id": "seller-complete"}],
                    },
                    {
                        "id": "clarify-contact-type",
                        "type": "send_message",
                        "name": "Clarify unexpected answer",
                        "config": {
                            "message": "I can help if you reply with buyer or seller."
                        },
                        "transitions": [
                            {
                                "target_node_id": "ask-contact-type",
                                "label": "Ask again",
                            }
                        ],
                    },
                    {
                        "id": "buyer-complete",
                        "type": "end",
                        "name": "Buyer routing complete",
                        "config": {"outcome": "buyer_routed_to_sales"},
                    },
                    {
                        "id": "seller-complete",
                        "type": "end",
                        "name": "Seller help complete",
                        "config": {"outcome": "seller_help_article_sent"},
                    },
                ],
            }
        )
        return flow

    def _support_triage_template(self, request: GenerationRequest) -> dict[str, Any]:
        flow = self._base_flow(
            request,
            "support-triage",
            "Support triage",
            [
                "Template selected because the prompt mentions support triage.",
                "Billing is routed to finance and account access is routed to support.",
                "Other or unexpected issues are routed to a human support team.",
            ],
        )
        flow.update(
            {
                "trigger_node_id": "support-message",
                "nodes": [
                    {
                        "id": "support-message",
                        "type": "trigger",
                        "name": "Support message",
                        "config": {"event": "support_message"},
                        "transitions": [{"target_node_id": "ask-issue-type"}],
                    },
                    {
                        "id": "ask-issue-type",
                        "type": "ask_question",
                        "name": "Ask issue type",
                        "config": {
                            "question": (
                                "Is this about billing, account access, or something else?"
                            ),
                            "variable_name": "issue_type",
                            "expected_answers": [
                                "billing",
                                "account access",
                                "something else",
                            ],
                        },
                        "transitions": [{"target_node_id": "route-issue-type"}],
                    },
                    {
                        "id": "route-issue-type",
                        "type": "condition",
                        "name": "Route issue type",
                        "config": {"variable_name": "issue_type"},
                        "transitions": [
                            {
                                "target_node_id": "route-billing",
                                "label": "Billing",
                                "condition": "issue_type == 'billing'",
                            },
                            {
                                "target_node_id": "route-account-access",
                                "label": "Account access",
                                "condition": "issue_type == 'account access'",
                            },
                            {
                                "target_node_id": "route-human-support",
                                "label": "Other or unexpected issue",
                                "is_fallback": True,
                            },
                        ],
                    },
                    {
                        "id": "route-billing",
                        "type": "assign_to_team",
                        "name": "Route billing to finance",
                        "config": {"team_name": "finance"},
                        "transitions": [{"target_node_id": "billing-complete"}],
                    },
                    {
                        "id": "route-account-access",
                        "type": "assign_to_team",
                        "name": "Route account access to support",
                        "config": {"team_name": "support"},
                        "transitions": [{"target_node_id": "account-access-complete"}],
                    },
                    {
                        "id": "route-human-support",
                        "type": "assign_to_team",
                        "name": "Route other issue to human support",
                        "config": {"team_name": "human support"},
                        "transitions": [{"target_node_id": "human-support-complete"}],
                    },
                    {
                        "id": "billing-complete",
                        "type": "end",
                        "name": "Billing routed",
                        "config": {"outcome": "billing_routed_to_finance"},
                    },
                    {
                        "id": "account-access-complete",
                        "type": "end",
                        "name": "Account access routed",
                        "config": {"outcome": "account_access_routed_to_support"},
                    },
                    {
                        "id": "human-support-complete",
                        "type": "end",
                        "name": "Human support routed",
                        "config": {"outcome": "other_issue_routed_to_human_support"},
                    },
                ],
            }
        )
        return flow

    def _order_status_template(self, request: GenerationRequest) -> dict[str, Any]:
        flow = self._base_flow(
            request,
            "order-status",
            "Order status",
            [
                "Template selected because the prompt mentions order status.",
                "The API call is mocked and never performs a real external request.",
                "API failure routes the conversation to support.",
            ],
        )
        flow.update(
            {
                "trigger_node_id": "order-inquiry",
                "nodes": [
                    {
                        "id": "order-inquiry",
                        "type": "trigger",
                        "name": "Order inquiry",
                        "config": {"event": "order_status_inquiry"},
                        "transitions": [{"target_node_id": "ask-order-id"}],
                    },
                    {
                        "id": "ask-order-id",
                        "type": "ask_question",
                        "name": "Ask for order ID",
                        "config": {
                            "question": "What is your order ID?",
                            "variable_name": "order_id",
                            "expected_answers": [],
                        },
                        "transitions": [{"target_node_id": "check-order-status"}],
                    },
                    {
                        "id": "check-order-status",
                        "type": "api_call",
                        "name": "Check order status",
                        "config": {
                            "method": "GET",
                            "url": "https://api.example.test/orders/status?order_id={order_id}",
                            "timeout_seconds": 10,
                            "mock_success_response": {
                                "status": "shipped",
                                "eta": "tomorrow",
                            },
                            "mock_failure_status": 500,
                        },
                        "transitions": [
                            {
                                "target_node_id": "send-order-result",
                                "label": "success",
                                "condition": "status < 400",
                            },
                            {
                                "target_node_id": "route-api-failure",
                                "label": "failure",
                                "condition": "status >= 400",
                            },
                        ],
                    },
                    {
                        "id": "send-order-result",
                        "type": "send_message",
                        "name": "Send order result",
                        "config": {
                            "message": (
                                "Your order status is available in the mock API response."
                            )
                        },
                        "transitions": [{"target_node_id": "order-status-complete"}],
                    },
                    {
                        "id": "route-api-failure",
                        "type": "assign_to_team",
                        "name": "Route API failure to support",
                        "config": {"team_name": "support"},
                        "transitions": [{"target_node_id": "support-routing-complete"}],
                    },
                    {
                        "id": "order-status-complete",
                        "type": "end",
                        "name": "Order status sent",
                        "config": {"outcome": "order_status_sent"},
                    },
                    {
                        "id": "support-routing-complete",
                        "type": "end",
                        "name": "Support routing complete",
                        "config": {"outcome": "order_status_failure_routed_to_support"},
                    },
                ],
            }
        )
        return flow

    def _llm_config(self) -> dict[str, str | int | None]:
        return {
            "base_url": os.getenv("LLM_BASE_URL") or settings.llm_base_url,
            "api_key": os.getenv("LLM_API_KEY") or settings.llm_api_key,
            "model": os.getenv("LLM_MODEL") or settings.llm_model,
            "timeout_seconds": int(
                os.getenv("LLM_TIMEOUT_SECONDS") or settings.llm_timeout_seconds
            ),
        }
