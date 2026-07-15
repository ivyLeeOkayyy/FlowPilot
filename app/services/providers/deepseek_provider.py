import json
import logging
import os
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.models import AutomationFlow
from app.services.providers.base import GenerationProviderError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a workflow generation assistant for FlowPilot.
Return only one valid JSON object matching the AutomationFlow schema.
Do not use markdown fences.
Do not add unsupported fields.

Supported node types:
- trigger
- send_message
- ask_question
- condition
- api_call
- assign_to_team
- wait
- end

AutomationFlow schema:
- id: non-empty string
- name: non-empty string
- description: optional string
- version: positive integer
- trigger_node_id: non-empty string referencing exactly one trigger node
- nodes: non-empty array of FlowNode
- metadata: object with source_prompt, generator, model_name, created_at, assumptions, warnings

FlowNode schema:
- id: non-empty string
- type: one supported node type
- name: non-empty human-readable string
- config: typed config matching node type
- transitions: array of transitions

Transition schema:
- target_node_id: non-empty string
- label: optional string
- condition: optional string
- is_fallback: boolean

Config schemas:
- trigger: {"event": string}
- send_message: {"message": string}
- ask_question: {"question": string, "variable_name": string, "expected_answers": string[]}
- condition: {"variable_name": string}
- api_call: {"method": "GET"|"POST"|"PUT"|"PATCH"|"DELETE", "url": string, "timeout_seconds": positive integer, "mock_success_response": object, "mock_failure_status": integer 400-599}
- assign_to_team: {"team_name": string}
- wait: {"duration_seconds": positive integer}
- end: {"outcome": string}

Compact valid example:
{"id":"example-flow","name":"Example flow","description":"Example","version":1,"trigger_node_id":"start","nodes":[{"id":"start","type":"trigger","name":"Start","config":{"event":"example_event"},"transitions":[{"target_node_id":"finish"}]},{"id":"finish","type":"end","name":"Finished","config":{"outcome":"complete"},"transitions":[]}],"metadata":{"source_prompt":"Example","generator":"deepseek","model_name":"deepseek-chat","assumptions":[],"warnings":[]}}

Safety rules:
- Do not generate executable code.
- Do not include secrets.
- Do not describe real external execution.
- API calls are mockable workflow nodes only.
- Generated workflows must be valid before execution.
"""


class DeepSeekProvider:
    provider_name = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout_seconds: int | None = None,
        client_factory: Any | None = None,
    ) -> None:
        self.api_key = (
            api_key
            if api_key is not None
            else os.getenv("DEEPSEEK_API_KEY") or settings.deepseek_api_key
        )
        self.base_url = (
            base_url
            if base_url is not None
            else os.getenv("DEEPSEEK_BASE_URL") or settings.deepseek_base_url
        ).rstrip("/")
        self.model_name = (
            model_name
            if model_name is not None
            else os.getenv("DEEPSEEK_MODEL") or settings.deepseek_model
        )
        self.timeout_seconds = int(
            timeout_seconds
            if timeout_seconds is not None
            else os.getenv("LLM_TIMEOUT_SECONDS") or settings.llm_timeout_seconds
        )
        self.trust_env = True
        self._client_factory = client_factory or self._default_client_factory
        self.last_diagnostics: dict[str, Any] = {
            "endpoint": self.endpoint,
            "requested_model": self.model_name,
            "http_status": None,
            "provider_model": None,
            "choices_present": False,
            "message_present": False,
            "content_present": False,
            "content_json_valid": False,
            "automation_flow_valid": False,
            "error_code": None,
            "error_message": None,
            "trust_env": self.trust_env,
            "timeout_seconds": self.timeout_seconds,
            "http_proxy_configured": bool(os.getenv("HTTP_PROXY")),
            "https_proxy_configured": bool(os.getenv("HTTPS_PROXY")),
            "all_proxy_configured": bool(os.getenv("ALL_PROXY")),
        }

    @property
    def endpoint(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    def generate(self, prompt: str) -> dict:
        try:
            workflow_data = self.generate_workflow_data(prompt)
        except GenerationProviderError:
            raise
        except Exception as exc:
            self._record_error("LLM_PROVIDER_ERROR", "Unexpected DeepSeek provider error.")
            logger.info(
                "DeepSeek provider failure: stage=%s endpoint=%s model=%s exception=%s",
                "unexpected",
                self.endpoint,
                self.model_name,
                exc.__class__.__name__,
            )
            raise GenerationProviderError(
                "LLM_PROVIDER_ERROR",
                "Unexpected DeepSeek provider error.",
            ) from None
        try:
            AutomationFlow.model_validate(workflow_data)
        except ValidationError as exc:
            self.last_diagnostics["automation_flow_valid"] = False
            self._record_error("INVALID_GENERATED_FLOW", "DeepSeek JSON did not match AutomationFlow schema.")
            logger.info(
                "DeepSeek provider failure: stage=%s endpoint=%s model=%s exception=%s",
                "automation_flow_validation",
                self.endpoint,
                self.model_name,
                exc.__class__.__name__,
            )
            raise GenerationProviderError(
                "INVALID_GENERATED_FLOW",
                "DeepSeek JSON did not match AutomationFlow schema.",
            ) from None

        self.last_diagnostics["automation_flow_valid"] = True
        return workflow_data

    def generate_workflow_data(self, prompt: str) -> dict:
        if not self.api_key:
            self._record_error("LLM_NOT_CONFIGURED", "DeepSeek generation requires DEEPSEEK_API_KEY.")
            raise GenerationProviderError(
                "LLM_NOT_CONFIGURED",
                "DeepSeek generation requires DEEPSEEK_API_KEY.",
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info(
            "DeepSeek request prepared: endpoint=%s model=%s trust_env=%s timeout=%s proxies_present=%s",
            self.endpoint,
            self.model_name,
            self.trust_env,
            self.timeout_seconds,
            self._proxy_presence(),
        )

        try:
            with self._client_factory() as client:
                response = client.post(
                    self.endpoint,
                    headers=headers,
                    json=self._payload(prompt),
                )
                self.last_diagnostics["http_status"] = response.status_code
                logger.info(
                    "DeepSeek response received: endpoint=%s model=%s status=%s content_length=%s",
                    self.endpoint,
                    self.model_name,
                    self.last_diagnostics["http_status"],
                    len(response.text),
                )
                response.raise_for_status()
                provider_response = response.json()
        except httpx.ProxyError as exc:
            return self._connection_failed("proxy", exc)
        except httpx.ConnectTimeout as exc:
            self._record_error("LLM_PROVIDER_TIMEOUT", "DeepSeek provider request timed out.")
            logger.info(
                "DeepSeek provider failure: stage=%s endpoint=%s model=%s exception=%s message=%s trust_env=%s timeout=%s proxies_present=%s",
                "connect_timeout",
                self.endpoint,
                self.model_name,
                exc.__class__.__name__,
                self._sanitize_exception_message(exc),
                self.trust_env,
                self.timeout_seconds,
                self._proxy_presence(),
            )
            raise GenerationProviderError(
                "LLM_PROVIDER_TIMEOUT",
                "DeepSeek provider request timed out.",
            ) from None
        except httpx.ReadTimeout as exc:
            self._record_error("LLM_PROVIDER_TIMEOUT", "DeepSeek provider request timed out while reading.")
            logger.info(
                "DeepSeek provider failure: stage=%s endpoint=%s model=%s exception=%s message=%s trust_env=%s timeout=%s proxies_present=%s",
                "read_timeout",
                self.endpoint,
                self.model_name,
                exc.__class__.__name__,
                self._sanitize_exception_message(exc),
                self.trust_env,
                self.timeout_seconds,
                self._proxy_presence(),
            )
            raise GenerationProviderError(
                "LLM_PROVIDER_TIMEOUT",
                "DeepSeek provider request timed out while reading.",
            ) from None
        except httpx.ConnectError as exc:
            return self._connection_failed("connect", exc)
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            self.last_diagnostics["http_status"] = status_code
            self._record_error("LLM_PROVIDER_ERROR", f"DeepSeek provider returned HTTP status {status_code}.")
            logger.info(
                "DeepSeek provider failure: stage=%s endpoint=%s model=%s status=%s exception=%s",
                "http_status",
                self.endpoint,
                self.model_name,
                status_code,
                exc.__class__.__name__,
            )
            raise GenerationProviderError(
                "LLM_PROVIDER_ERROR",
                f"DeepSeek provider returned HTTP status {status_code}.",
            ) from None
        except json.JSONDecodeError as exc:
            return self._invalid_output("http_response_json", exc)
        except httpx.RequestError as exc:
            return self._connection_failed("request", exc)
        if not isinstance(provider_response, dict):
            return self._invalid_output(
                "http_response_json_object",
                TypeError("provider response JSON is not an object"),
            )

        self.last_diagnostics["provider_model"] = provider_response.get("model")
        content = self._extract_content(provider_response)
        try:
            parsed = json.loads(content)
            self.last_diagnostics["content_json_valid"] = True
        except json.JSONDecodeError as exc:
            return self._invalid_output("content_json", exc)

        if not isinstance(parsed, dict):
            return self._invalid_output("content_json_object", TypeError("content JSON is not an object"))
        return parsed

    def _extract_content(self, provider_response: dict[str, Any]) -> str:
        choices = provider_response.get("choices")
        if not isinstance(choices, list) or not choices:
            return self._invalid_output("choices", ValueError("missing or empty choices"))

        self.last_diagnostics["choices_present"] = True
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return self._invalid_output("choices", TypeError("choice is not an object"))

        message = first_choice.get("message")
        if not isinstance(message, dict):
            return self._invalid_output("message", ValueError("missing message"))

        self.last_diagnostics["message_present"] = True
        content = message.get("content")
        if not isinstance(content, str):
            return self._invalid_output("content", TypeError("content is not a string"))
        if not content.strip():
            return self._invalid_output("content", ValueError("content is empty"))

        self.last_diagnostics["content_present"] = True
        logger.info(
            "DeepSeek content extracted: endpoint=%s model=%s content_length=%s",
            self.endpoint,
            self.model_name,
            len(content),
        )
        return content

    def _invalid_output(self, stage: str, exc: Exception) -> Any:
        self._record_error("INVALID_LLM_OUTPUT", f"Invalid DeepSeek response at stage: {stage}.")
        logger.info(
            "DeepSeek provider failure: stage=%s endpoint=%s model=%s exception=%s",
            stage,
            self.endpoint,
            self.model_name,
            exc.__class__.__name__,
        )
        raise GenerationProviderError(
            "INVALID_LLM_OUTPUT",
            f"Invalid DeepSeek response at stage: {stage}.",
        ) from None

    def _record_error(self, code: str, message: str) -> None:
        self.last_diagnostics["error_code"] = code
        self.last_diagnostics["error_message"] = message

    def _payload(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 4000,
            "stream": False,
            "temperature": 0.2,
        }

    def _default_client_factory(self) -> httpx.Client:
        return httpx.Client(
            timeout=httpx.Timeout(self.timeout_seconds),
            trust_env=self.trust_env,
        )

    def _connection_failed(self, stage: str, exc: Exception) -> Any:
        self._record_error("LLM_PROVIDER_CONNECTION_FAILED", "DeepSeek provider connection failed.")
        logger.info(
            "DeepSeek provider failure: stage=%s endpoint=%s model=%s exception=%s message=%s trust_env=%s timeout=%s proxies_present=%s",
            stage,
            self.endpoint,
            self.model_name,
            exc.__class__.__name__,
            self._sanitize_exception_message(exc),
            self.trust_env,
            self.timeout_seconds,
            self._proxy_presence(),
        )
        raise GenerationProviderError(
            "LLM_PROVIDER_CONNECTION_FAILED",
            "DeepSeek provider connection failed.",
        ) from None

    def _proxy_presence(self) -> dict[str, bool]:
        return {
            "HTTP_PROXY": bool(os.getenv("HTTP_PROXY")),
            "HTTPS_PROXY": bool(os.getenv("HTTPS_PROXY")),
            "ALL_PROXY": bool(os.getenv("ALL_PROXY")),
        }

    def _sanitize_exception_message(self, exc: Exception) -> str:
        message = str(exc)
        api_key = self.api_key
        if api_key:
            message = message.replace(api_key, "[redacted]")
        return message[:240]
