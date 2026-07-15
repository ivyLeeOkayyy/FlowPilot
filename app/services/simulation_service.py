from copy import deepcopy
import re
from typing import Any

from app.models import (
    ApiCallConfig,
    AskQuestionConfig,
    AssignToTeamConfig,
    AutomationFlow,
    ConditionConfig,
    EndConfig,
    ExecutionTraceEntry,
    FlowNode,
    MockApiOutcome,
    NodeType,
    SendMessageConfig,
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
    TranscriptEntry,
    TranscriptRole,
    TriggerConfig,
    ValidationSeverity,
    WaitConfig,
)
from app.services.validation_service import FlowValidationService


class FlowSimulationService:
    def simulate(self, request: SimulationRequest) -> SimulationResult:
        validation_result = FlowValidationService().validate(request.flow)
        validation_errors = [
            finding.code
            for finding in validation_result.findings
            if finding.severity is ValidationSeverity.ERROR
        ]
        if validation_errors:
            error_codes = sorted(code for code in validation_errors if code is not None)
            return SimulationResult(
                status=SimulationStatus.FAILED,
                current_node_id=request.flow.trigger_node_id,
                variables=deepcopy(request.initial_variables),
                steps_executed=0,
                error_code="FLOW_VALIDATION_FAILED",
                error_message=(
                    "Flow validation failed with errors: "
                    + ", ".join(error_codes)
                ),
            )

        nodes_by_id = {node.id: node for node in request.flow.nodes}
        variables = deepcopy(request.initial_variables)
        user_inputs = dict(request.user_inputs)
        api_outcomes = deepcopy(request.api_outcomes)
        transcript: list[TranscriptEntry] = []
        trace: list[ExecutionTraceEntry] = []
        assigned_team: str | None = None
        current_node_id: str | None = request.flow.trigger_node_id
        steps_executed = 0

        while current_node_id is not None:
            if steps_executed >= request.max_steps:
                return self._result(
                    SimulationStatus.STEP_LIMIT_EXCEEDED,
                    current_node_id=current_node_id,
                    assigned_team=assigned_team,
                    variables=variables,
                    transcript=transcript,
                    trace=trace,
                    steps_executed=steps_executed,
                    error_code="STEP_LIMIT_EXCEEDED",
                    error_message=(
                        f"Execution reached max_steps={request.max_steps} before "
                        f"executing node '{current_node_id}'."
                    ),
                )

            node = nodes_by_id.get(current_node_id)
            if node is None:
                return self._result(
                    SimulationStatus.FAILED,
                    current_node_id=current_node_id,
                    assigned_team=assigned_team,
                    variables=variables,
                    transcript=transcript,
                    trace=trace,
                    steps_executed=steps_executed,
                    error_code="NODE_NOT_FOUND",
                    error_message=f"Node '{current_node_id}' was not found.",
                )

            steps_executed += 1
            step = steps_executed

            if node.type is NodeType.TRIGGER:
                next_node_id, entry = self._execute_trigger(node, step)
            elif node.type is NodeType.SEND_MESSAGE:
                next_node_id, entry = self._execute_send_message(
                    node,
                    step,
                    transcript,
                )
            elif node.type is NodeType.ASK_QUESTION:
                ask_result = self._execute_ask_question(
                    node,
                    step,
                    user_inputs,
                    variables,
                    transcript,
                )
                trace.append(ask_result["trace"])
                if ask_result["status"] is SimulationStatus.WAITING_FOR_INPUT:
                    return self._result(
                        SimulationStatus.WAITING_FOR_INPUT,
                        current_node_id=node.id,
                        assigned_team=assigned_team,
                        variables=variables,
                        transcript=transcript,
                        trace=trace,
                        steps_executed=steps_executed,
                    )
                if ask_result["status"] is SimulationStatus.FAILED:
                    return self._failed_from_trace(
                        node,
                        assigned_team,
                        variables,
                        transcript,
                        trace,
                        steps_executed,
                        "NO_TRANSITION",
                        f"Node '{node.id}' has no normal transition.",
                    )
                current_node_id = ask_result["next_node_id"]
                continue
            elif node.type is NodeType.CONDITION:
                condition_result = self._execute_condition(node, step, variables)
                trace.append(condition_result["trace"])
                if condition_result["status"] is SimulationStatus.FAILED:
                    return self._failed_from_trace(
                        node,
                        assigned_team,
                        variables,
                        transcript,
                        trace,
                        steps_executed,
                        condition_result["error_code"],
                        condition_result["error_message"],
                    )
                current_node_id = condition_result["next_node_id"]
                continue
            elif node.type is NodeType.ASSIGN_TO_TEAM:
                next_node_id, entry, assigned_team = self._execute_assign_to_team(
                    node,
                    step,
                    assigned_team,
                )
            elif node.type is NodeType.API_CALL:
                api_result = self._execute_api_call(node, step, api_outcomes, variables)
                trace.append(api_result["trace"])
                if api_result["status"] is SimulationStatus.FAILED:
                    return self._failed_from_trace(
                        node,
                        assigned_team,
                        variables,
                        transcript,
                        trace,
                        steps_executed,
                        api_result["error_code"],
                        api_result["error_message"],
                    )
                current_node_id = api_result["next_node_id"]
                continue
            elif node.type is NodeType.WAIT:
                next_node_id, entry = self._execute_wait(node, step)
            elif node.type is NodeType.END:
                trace.append(
                    ExecutionTraceEntry(
                        step=step,
                        node_id=node.id,
                        node_type=node.type,
                        action="completed",
                        details={"outcome": self._end_config(node).outcome},
                    )
                )
                return self._result(
                    SimulationStatus.COMPLETED,
                    current_node_id=node.id,
                    completed_outcome=self._end_config(node).outcome,
                    assigned_team=assigned_team,
                    variables=variables,
                    transcript=transcript,
                    trace=trace,
                    steps_executed=steps_executed,
                )
            else:
                return self._result(
                    SimulationStatus.FAILED,
                    current_node_id=node.id,
                    assigned_team=assigned_team,
                    variables=variables,
                    transcript=transcript,
                    trace=trace,
                    steps_executed=steps_executed,
                    error_code="UNSUPPORTED_NODE_TYPE",
                    error_message=f"Unsupported node type '{node.type}'.",
                )

            trace.append(entry)
            if next_node_id is None:
                return self._failed_from_trace(
                    node,
                    assigned_team,
                    variables,
                    transcript,
                    trace,
                    steps_executed,
                    "NO_TRANSITION",
                    f"Node '{node.id}' has no normal transition.",
                )
            current_node_id = next_node_id

        return self._result(
            SimulationStatus.FAILED,
            current_node_id=None,
            assigned_team=assigned_team,
            variables=variables,
            transcript=transcript,
            trace=trace,
            steps_executed=steps_executed,
            error_code="NO_TRANSITION",
            error_message="Execution stopped without a next node.",
        )

    def _execute_trigger(
        self,
        node: FlowNode,
        step: int,
    ) -> tuple[str | None, ExecutionTraceEntry]:
        transition = self._first_normal_transition(node)
        extra_transition_count = max(
            len([item for item in node.transitions if not item.is_fallback]) - 1,
            0,
        )
        details: dict[str, Any] = {"event": self._trigger_config(node).event}
        if extra_transition_count:
            details["warning"] = "multiple normal transitions; selected first"
        return (
            transition.target_node_id if transition else None,
            ExecutionTraceEntry(
                step=step,
                node_id=node.id,
                node_type=node.type,
                action="triggered",
                selected_transition_target=(
                    transition.target_node_id if transition else None
                ),
                details=details,
            ),
        )

    def _execute_send_message(
        self,
        node: FlowNode,
        step: int,
        transcript: list[TranscriptEntry],
    ) -> tuple[str | None, ExecutionTraceEntry]:
        message = self._send_message_config(node).message
        transcript.append(
            TranscriptEntry(
                step=step,
                node_id=node.id,
                role=TranscriptRole.BOT,
                message=message,
            )
        )
        transition = self._first_normal_transition(node)
        details: dict[str, Any] = {"message": message}
        if len([item for item in node.transitions if not item.is_fallback]) > 1:
            details["choice"] = "selected first normal transition"
        return (
            transition.target_node_id if transition else None,
            ExecutionTraceEntry(
                step=step,
                node_id=node.id,
                node_type=node.type,
                action="sent_message",
                selected_transition_target=(
                    transition.target_node_id if transition else None
                ),
                details=details,
            ),
        )

    def _execute_ask_question(
        self,
        node: FlowNode,
        step: int,
        user_inputs: dict[str, str],
        variables: dict[str, Any],
        transcript: list[TranscriptEntry],
    ) -> dict[str, Any]:
        config = self._ask_question_config(node)
        transcript.append(
            TranscriptEntry(
                step=step,
                node_id=node.id,
                role=TranscriptRole.BOT,
                message=config.question,
            )
        )
        if node.id not in user_inputs:
            return {
                "status": SimulationStatus.WAITING_FOR_INPUT,
                "trace": ExecutionTraceEntry(
                    step=step,
                    node_id=node.id,
                    node_type=node.type,
                    action="waiting_for_input",
                    details={"variable_name": config.variable_name},
                ),
            }

        answer = user_inputs[node.id]
        transcript.append(
            TranscriptEntry(
                step=step,
                node_id=node.id,
                role=TranscriptRole.USER,
                message=answer,
            )
        )
        variables[config.variable_name] = answer
        transition = self._first_normal_transition(node)
        return {
            "status": (
                SimulationStatus.COMPLETED
                if transition is not None
                else SimulationStatus.FAILED
            ),
            "next_node_id": transition.target_node_id if transition else None,
            "trace": ExecutionTraceEntry(
                step=step,
                node_id=node.id,
                node_type=node.type,
                action="captured_input",
                selected_transition_target=(
                    transition.target_node_id if transition else None
                ),
                details={
                    "variable_name": config.variable_name,
                    "answer": answer,
                },
            ),
        }

    def _execute_condition(
        self,
        node: FlowNode,
        step: int,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        config = self._condition_config(node)
        variable_present = config.variable_name in variables
        value = variables.get(config.variable_name)
        fallback_transition = self._single_fallback_transition(node)

        for transition in node.transitions:
            if transition.is_fallback:
                continue
            if transition.condition and self._condition_matches(
                transition.condition,
                config.variable_name,
                value,
                variable_present,
            ):
                return {
                    "status": SimulationStatus.COMPLETED,
                    "next_node_id": transition.target_node_id,
                    "trace": ExecutionTraceEntry(
                        step=step,
                        node_id=node.id,
                        node_type=node.type,
                        action="evaluated_condition",
                        selected_transition_target=transition.target_node_id,
                        details={
                            "variable_name": config.variable_name,
                            "value": value,
                            "selected_branch": transition.label,
                            "condition": transition.condition,
                        },
                    ),
                }

        if fallback_transition is not None:
            return {
                "status": SimulationStatus.COMPLETED,
                "next_node_id": fallback_transition.target_node_id,
                "trace": ExecutionTraceEntry(
                    step=step,
                    node_id=node.id,
                    node_type=node.type,
                    action="evaluated_condition",
                    selected_transition_target=fallback_transition.target_node_id,
                    details={
                        "variable_name": config.variable_name,
                        "value": value,
                        "selected_branch": fallback_transition.label,
                        "used_fallback": True,
                    },
                ),
            }

        if not variable_present:
            error_code = "VARIABLE_NOT_FOUND"
            error_message = (
                f"Variable '{config.variable_name}' was not found for condition "
                f"node '{node.id}'."
            )
        else:
            error_code = "NO_MATCHING_TRANSITION"
            error_message = f"Condition node '{node.id}' found no matching transition."
        return {
            "status": SimulationStatus.FAILED,
            "error_code": error_code,
            "error_message": error_message,
            "trace": ExecutionTraceEntry(
                step=step,
                node_id=node.id,
                node_type=node.type,
                action="condition_failed",
                details={
                    "variable_name": config.variable_name,
                    "value": value,
                    "error_code": error_code,
                },
            ),
        }

    def _execute_assign_to_team(
        self,
        node: FlowNode,
        step: int,
        previous_team: str | None,
    ) -> tuple[str | None, ExecutionTraceEntry, str]:
        team_name = self._assign_to_team_config(node).team_name
        transition = self._first_normal_transition(node)
        return (
            transition.target_node_id if transition else None,
            ExecutionTraceEntry(
                step=step,
                node_id=node.id,
                node_type=node.type,
                action="assigned_team",
                selected_transition_target=(
                    transition.target_node_id if transition else None
                ),
                details={
                    "team_name": team_name,
                    "previous_team": previous_team,
                },
            ),
            team_name,
        )

    def _execute_api_call(
        self,
        node: FlowNode,
        step: int,
        api_outcomes: dict[str, MockApiOutcome],
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        outcome = api_outcomes.get(node.id)
        if outcome is None:
            return {
                "status": SimulationStatus.FAILED,
                "error_code": "MOCK_API_OUTCOME_REQUIRED",
                "error_message": (
                    f"Mock API outcome is required for api_call node '{node.id}'."
                ),
                "trace": ExecutionTraceEntry(
                    step=step,
                    node_id=node.id,
                    node_type=node.type,
                    action="mock_api_missing",
                ),
            }

        variables.setdefault("api_results", {})[node.id] = {
            "success": outcome.success,
            "status_code": outcome.status_code,
            "response": deepcopy(outcome.response),
            "error_message": outcome.error_message,
        }

        transition = self._select_api_transition(node, outcome)
        if transition is None:
            error_code = (
                "API_SUCCESS_PATH_NOT_FOUND"
                if outcome.success
                else "API_FAILURE_PATH_NOT_FOUND"
            )
            return {
                "status": SimulationStatus.FAILED,
                "error_code": error_code,
                "error_message": (
                    f"API call node '{node.id}' has no matching "
                    f"{'success' if outcome.success else 'failure'} transition."
                ),
                "trace": ExecutionTraceEntry(
                    step=step,
                    node_id=node.id,
                    node_type=node.type,
                    action="mock_api_branch_missing",
                    details={
                        "status_code": outcome.status_code,
                        "success": outcome.success,
                        "error_code": error_code,
                    },
                ),
            }

        return {
            "status": SimulationStatus.COMPLETED,
            "next_node_id": transition.target_node_id,
            "trace": ExecutionTraceEntry(
                step=step,
                node_id=node.id,
                node_type=node.type,
                action="mock_api_call",
                selected_transition_target=transition.target_node_id,
                details={
                    "status_code": outcome.status_code,
                    "success": outcome.success,
                    "selected_branch": transition.label,
                },
            ),
        }

    def _execute_wait(
        self,
        node: FlowNode,
        step: int,
    ) -> tuple[str | None, ExecutionTraceEntry]:
        transition = self._first_normal_transition(node)
        duration_seconds = self._wait_config(node).duration_seconds
        return (
            transition.target_node_id if transition else None,
            ExecutionTraceEntry(
                step=step,
                node_id=node.id,
                node_type=node.type,
                action="waited",
                selected_transition_target=(
                    transition.target_node_id if transition else None
                ),
                details={"duration_seconds": duration_seconds, "slept": False},
            ),
        )

    def _first_normal_transition(self, node: FlowNode):
        return next(
            (transition for transition in node.transitions if not transition.is_fallback),
            None,
        )

    def _single_fallback_transition(self, node: FlowNode):
        return next(
            (transition for transition in node.transitions if transition.is_fallback),
            None,
        )

    def _condition_matches(
        self,
        expression: str,
        variable_name: str,
        value: Any,
        variable_present: bool,
    ) -> bool:
        if not variable_present:
            return False

        match = re.fullmatch(
            r"""\s*([A-Za-z_][A-Za-z0-9_]*)\s*(==|!=)\s*(['"])(.*?)\3\s*""",
            expression,
        )
        if match is None:
            return False

        expression_variable, operator, _, expected_value = match.groups()
        if expression_variable != variable_name:
            return False

        actual_value = str(value)
        if operator == "==":
            return actual_value == expected_value
        return actual_value != expected_value

    def _select_api_transition(self, node: FlowNode, outcome: MockApiOutcome):
        for transition in node.transitions:
            if outcome.success and self._is_success_transition(transition):
                return transition
            if not outcome.success and self._is_failure_transition(transition):
                return transition
        return None

    def _is_success_transition(self, transition) -> bool:
        text = self._transition_text(transition)
        compact = text.replace(" ", "")
        return any(
            indicator in text or indicator in compact
            for indicator in [
                "success",
                "succeeded",
                "ok",
                "2xx",
                "status<400",
                "success==true",
            ]
        )

    def _is_failure_transition(self, transition) -> bool:
        if transition.is_fallback:
            return True
        text = self._transition_text(transition)
        compact = text.replace(" ", "")
        return any(
            indicator in text or indicator in compact
            for indicator in [
                "failure",
                "failed",
                "error",
                "timeout",
                "4xx",
                "5xx",
                "status>=400",
                "success==false",
            ]
        )

    def _transition_text(self, transition) -> str:
        return " ".join(
            part.lower()
            for part in [transition.label, transition.condition]
            if part is not None
        )

    def _failed_from_trace(
        self,
        node: FlowNode,
        assigned_team: str | None,
        variables: dict[str, Any],
        transcript: list[TranscriptEntry],
        trace: list[ExecutionTraceEntry],
        steps_executed: int,
        error_code: str,
        error_message: str,
    ) -> SimulationResult:
        return self._result(
            SimulationStatus.FAILED,
            current_node_id=node.id,
            assigned_team=assigned_team,
            variables=variables,
            transcript=transcript,
            trace=trace,
            steps_executed=steps_executed,
            error_code=error_code,
            error_message=error_message,
        )

    def _result(
        self,
        status: SimulationStatus,
        current_node_id: str | None,
        assigned_team: str | None,
        variables: dict[str, Any],
        transcript: list[TranscriptEntry],
        trace: list[ExecutionTraceEntry],
        steps_executed: int,
        completed_outcome: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> SimulationResult:
        return SimulationResult(
            status=status,
            current_node_id=current_node_id,
            completed_outcome=completed_outcome,
            assigned_team=assigned_team,
            variables=deepcopy(variables),
            transcript=list(transcript),
            trace=list(trace),
            steps_executed=steps_executed,
            error_code=error_code,
            error_message=error_message,
        )

    def _trigger_config(self, node: FlowNode) -> TriggerConfig:
        return node.config  # type: ignore[return-value]

    def _send_message_config(self, node: FlowNode) -> SendMessageConfig:
        return node.config  # type: ignore[return-value]

    def _ask_question_config(self, node: FlowNode) -> AskQuestionConfig:
        return node.config  # type: ignore[return-value]

    def _condition_config(self, node: FlowNode) -> ConditionConfig:
        return node.config  # type: ignore[return-value]

    def _assign_to_team_config(self, node: FlowNode) -> AssignToTeamConfig:
        return node.config  # type: ignore[return-value]

    def _wait_config(self, node: FlowNode) -> WaitConfig:
        return node.config  # type: ignore[return-value]

    def _end_config(self, node: FlowNode) -> EndConfig:
        return node.config  # type: ignore[return-value]
