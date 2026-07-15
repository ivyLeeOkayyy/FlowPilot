from collections import defaultdict, deque
from collections.abc import Iterable

from app.models import (
    ApiCallConfig,
    AskQuestionConfig,
    AutomationFlow,
    ConditionConfig,
    EndConfig,
    FlowNode,
    FlowValidationResult,
    NodeType,
    SendMessageConfig,
    ValidationFinding,
    ValidationSeverity,
)


class FlowValidationService:
    def validate(self, flow: AutomationFlow) -> FlowValidationResult:
        nodes_by_id = {node.id: node for node in flow.nodes}
        adjacency = self._build_adjacency(flow)
        reachable_node_ids = self._compute_reachable_nodes(flow.trigger_node_id, adjacency)
        terminal_reaching_node_ids = self._compute_nodes_that_can_reach_end(
            flow.nodes,
            adjacency,
        )

        findings: list[ValidationFinding] = []
        findings.extend(self._validate_dangling_transitions(flow, nodes_by_id))
        findings.extend(self._validate_reachability(flow, reachable_node_ids))
        findings.extend(self._validate_condition_nodes(flow))
        findings.extend(self._validate_end_nodes(flow))
        findings.extend(self._validate_dead_end_nodes(flow))
        findings.extend(
            self._validate_terminal_paths(
                flow,
                reachable_node_ids,
                terminal_reaching_node_ids,
            )
        )
        findings.extend(self._detect_cycles(adjacency, reachable_node_ids))
        findings.extend(self._validate_duplicate_transitions(flow))
        findings.extend(self._validate_api_call_paths(flow))
        findings.extend(self._validate_ask_questions(flow))
        findings.extend(self._validate_empty_messages(flow))
        findings.extend(self._validate_unused_variables(flow))

        sorted_findings = sorted(findings, key=self._finding_sort_key)
        return FlowValidationResult(
            is_valid=not any(
                finding.severity is ValidationSeverity.ERROR
                for finding in sorted_findings
            ),
            findings=sorted_findings,
        )

    def _build_adjacency(self, flow: AutomationFlow) -> dict[str, list[str]]:
        return {
            node.id: [transition.target_node_id for transition in node.transitions]
            for node in flow.nodes
        }

    def _compute_reachable_nodes(
        self,
        start_node_id: str,
        adjacency: dict[str, list[str]],
    ) -> set[str]:
        reachable: set[str] = set()
        pending: deque[str] = deque([start_node_id])

        while pending:
            node_id = pending.popleft()
            if node_id in reachable or node_id not in adjacency:
                continue

            reachable.add(node_id)
            pending.extend(adjacency[node_id])

        return reachable

    def _compute_nodes_that_can_reach_end(
        self,
        nodes: Iterable[FlowNode],
        adjacency: dict[str, list[str]],
    ) -> set[str]:
        nodes_by_id = {node.id: node for node in nodes}
        reverse_adjacency: dict[str, list[str]] = defaultdict(list)
        for source_id, target_ids in adjacency.items():
            for target_id in target_ids:
                if target_id in nodes_by_id:
                    reverse_adjacency[target_id].append(source_id)

        terminal_reaching: set[str] = set()
        pending: deque[str] = deque(
            node.id for node in nodes_by_id.values() if node.type is NodeType.END
        )

        while pending:
            node_id = pending.popleft()
            if node_id in terminal_reaching:
                continue

            terminal_reaching.add(node_id)
            pending.extend(reverse_adjacency[node_id])

        return terminal_reaching

    def _validate_dangling_transitions(
        self,
        flow: AutomationFlow,
        nodes_by_id: dict[str, FlowNode],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for node in flow.nodes:
            for transition in node.transitions:
                if transition.target_node_id not in nodes_by_id:
                    findings.append(
                        self._finding(
                            ValidationSeverity.ERROR,
                            "DANGLING_TRANSITION",
                            node.id,
                            (
                                f"Node '{node.id}' transitions to missing target "
                                f"'{transition.target_node_id}'."
                            ),
                        )
                    )
        return findings

    def _validate_reachability(
        self,
        flow: AutomationFlow,
        reachable_node_ids: set[str],
    ) -> list[ValidationFinding]:
        return [
            self._finding(
                ValidationSeverity.WARNING,
                "UNREACHABLE_NODE",
                node.id,
                f"Node '{node.id}' is not reachable from the trigger node.",
            )
            for node in flow.nodes
            if node.id not in reachable_node_ids
        ]

    def _validate_condition_nodes(self, flow: AutomationFlow) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for node in flow.nodes:
            if node.type is not NodeType.CONDITION:
                continue

            fallback_count = sum(
                transition.is_fallback for transition in node.transitions
            )
            if not node.transitions:
                findings.append(
                    self._finding(
                        ValidationSeverity.ERROR,
                        "CONDITION_WITHOUT_TRANSITIONS",
                        node.id,
                        f"Condition node '{node.id}' has no transitions.",
                    )
                )
            if fallback_count == 0:
                findings.append(
                    self._finding(
                        ValidationSeverity.WARNING,
                        "MISSING_FALLBACK",
                        node.id,
                        f"Condition node '{node.id}' has no fallback transition.",
                    )
                )
            if fallback_count > 1:
                findings.append(
                    self._finding(
                        ValidationSeverity.ERROR,
                        "MULTIPLE_FALLBACKS",
                        node.id,
                        f"Condition node '{node.id}' has multiple fallback transitions.",
                    )
                )
        return findings

    def _validate_end_nodes(self, flow: AutomationFlow) -> list[ValidationFinding]:
        return [
            self._finding(
                ValidationSeverity.ERROR,
                "END_NODE_HAS_TRANSITIONS",
                node.id,
                f"End node '{node.id}' must not have transitions.",
            )
            for node in flow.nodes
            if node.type is NodeType.END and node.transitions
        ]

    def _validate_dead_end_nodes(self, flow: AutomationFlow) -> list[ValidationFinding]:
        return [
            self._finding(
                ValidationSeverity.ERROR,
                "DEAD_END_NODE",
                node.id,
                f"Non-end node '{node.id}' has no outgoing transitions.",
            )
            for node in flow.nodes
            if node.type is not NodeType.END and not node.transitions
        ]

    def _validate_terminal_paths(
        self,
        flow: AutomationFlow,
        reachable_node_ids: set[str],
        terminal_reaching_node_ids: set[str],
    ) -> list[ValidationFinding]:
        return [
            self._finding(
                ValidationSeverity.ERROR,
                "NO_TERMINAL_PATH",
                node.id,
                f"Reachable node '{node.id}' cannot reach an end node.",
            )
            for node in flow.nodes
            if (
                node.id in reachable_node_ids
                and node.id not in terminal_reaching_node_ids
            )
        ]

    def _detect_cycles(
        self,
        adjacency: dict[str, list[str]],
        reachable_node_ids: set[str],
    ) -> list[ValidationFinding]:
        visited: set[str] = set()
        active: set[str] = set()
        stack: list[str] = []
        canonical_cycles: dict[tuple[str, ...], list[str]] = {}

        def visit(node_id: str) -> None:
            visited.add(node_id)
            active.add(node_id)
            stack.append(node_id)

            for target_id in adjacency.get(node_id, []):
                if target_id not in reachable_node_ids:
                    continue
                if target_id not in visited:
                    visit(target_id)
                elif target_id in active:
                    cycle = stack[stack.index(target_id) :] + [target_id]
                    canonical_cycles.setdefault(
                        self._canonical_cycle_key(cycle),
                        cycle,
                    )

            stack.pop()
            active.remove(node_id)

        for node_id in sorted(reachable_node_ids):
            if node_id not in visited:
                visit(node_id)

        return [
            self._finding(
                ValidationSeverity.WARNING,
                "SUSPICIOUS_CYCLE",
                cycle[0],
                f"Cycle detected: {' -> '.join(cycle)}.",
            )
            for cycle in canonical_cycles.values()
        ]

    def _validate_duplicate_transitions(
        self,
        flow: AutomationFlow,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for node in flow.nodes:
            seen: set[tuple[str, str | None, bool]] = set()
            duplicates: set[tuple[str, str | None, bool]] = set()

            for transition in node.transitions:
                key = (
                    transition.target_node_id,
                    transition.condition,
                    transition.is_fallback,
                )
                if key in seen:
                    duplicates.add(key)
                seen.add(key)

            for target_node_id, condition, is_fallback in sorted(duplicates):
                findings.append(
                    self._finding(
                        ValidationSeverity.WARNING,
                        "DUPLICATE_TRANSITION",
                        node.id,
                        (
                            f"Node '{node.id}' has duplicate transition to "
                            f"'{target_node_id}'"
                            f" with condition '{condition}'"
                            f" and fallback={is_fallback}."
                        ),
                    )
                )
        return findings

    def _validate_api_call_paths(self, flow: AutomationFlow) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for node in flow.nodes:
            if node.type is not NodeType.API_CALL:
                continue

            has_success = False
            has_failure = False
            for transition in node.transitions:
                transition_text = " ".join(
                    part
                    for part in [transition.label, transition.condition]
                    if part is not None
                )
                has_success = has_success or self._is_success_transition(
                    transition_text
                )
                has_failure = has_failure or self._is_failure_transition(
                    transition_text,
                    transition.is_fallback,
                )

            if not has_success:
                findings.append(
                    self._finding(
                        ValidationSeverity.WARNING,
                        "API_CALL_MISSING_SUCCESS_PATH",
                        node.id,
                        f"API call node '{node.id}' has no recognizable success path.",
                    )
                )
            if not has_failure:
                findings.append(
                    self._finding(
                        ValidationSeverity.WARNING,
                        "API_CALL_MISSING_FAILURE_PATH",
                        node.id,
                        f"API call node '{node.id}' has no recognizable failure path.",
                    )
                )
        return findings

    def _validate_ask_questions(self, flow: AutomationFlow) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for node in flow.nodes:
            if (
                node.type is NodeType.ASK_QUESTION
                and isinstance(node.config, AskQuestionConfig)
                and not node.config.expected_answers
            ):
                findings.append(
                    self._finding(
                        ValidationSeverity.INFO,
                        "QUESTION_WITHOUT_EXPECTED_ANSWERS",
                        node.id,
                        (
                            f"Ask-question node '{node.id}' has no expected answers; "
                            "free-text input is allowed but harder to route."
                        ),
                    )
                )
        return findings

    def _validate_empty_messages(self, flow: AutomationFlow) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for node in flow.nodes:
            if (
                node.type is NodeType.SEND_MESSAGE
                and isinstance(node.config, SendMessageConfig)
                and not node.config.message.strip()
            ):
                findings.append(
                    self._finding(
                        ValidationSeverity.ERROR,
                        "EMPTY_MESSAGE",
                        node.id,
                        f"Send-message node '{node.id}' has an empty message.",
                    )
                )
        return findings

    def _validate_unused_variables(self, flow: AutomationFlow) -> list[ValidationFinding]:
        question_nodes_by_variable: dict[str, list[FlowNode]] = defaultdict(list)
        variables_read_by_conditions: set[str] = set()

        for node in flow.nodes:
            if node.type is NodeType.ASK_QUESTION and isinstance(
                node.config,
                AskQuestionConfig,
            ):
                question_nodes_by_variable[node.config.variable_name].append(node)
            if node.type is NodeType.CONDITION and isinstance(
                node.config,
                ConditionConfig,
            ):
                variables_read_by_conditions.add(node.config.variable_name)

        findings: list[ValidationFinding] = []
        for variable_name, question_nodes in sorted(question_nodes_by_variable.items()):
            if variable_name in variables_read_by_conditions:
                continue

            for node in question_nodes:
                findings.append(
                    self._finding(
                        ValidationSeverity.INFO,
                        "UNUSED_VARIABLE",
                        node.id,
                        (
                            f"Question variable '{variable_name}' from node "
                            f"'{node.id}' is not used by any condition node."
                        ),
                    )
                )
        return findings

    def _canonical_cycle_key(self, cycle: list[str]) -> tuple[str, ...]:
        unique_cycle = cycle[:-1]
        rotations = [
            tuple(unique_cycle[index:] + unique_cycle[:index])
            for index in range(len(unique_cycle))
        ]
        return min(rotations)

    def _is_success_transition(self, transition_text: str) -> bool:
        normalized = transition_text.lower()
        compact = normalized.replace(" ", "")
        return any(
            indicator in normalized or indicator in compact
            for indicator in ["success", "succeeded", "2xx", "status<400"]
        )

    def _is_failure_transition(
        self,
        transition_text: str,
        is_fallback: bool,
    ) -> bool:
        if is_fallback:
            return True

        normalized = transition_text.lower()
        compact = normalized.replace(" ", "")
        return any(
            indicator in normalized or indicator in compact
            for indicator in [
                "failure",
                "failed",
                "error",
                "timeout",
                "status>=400",
            ]
        )

    def _finding(
        self,
        severity: ValidationSeverity,
        code: str,
        node_id: str | None,
        message: str,
    ) -> ValidationFinding:
        return ValidationFinding(
            severity=severity,
            code=code,
            node_id=node_id,
            message=message,
        )

    def _finding_sort_key(
        self,
        finding: ValidationFinding,
    ) -> tuple[int, str, str, str]:
        severity_order = {
            ValidationSeverity.ERROR: 0,
            ValidationSeverity.WARNING: 1,
            ValidationSeverity.INFO: 2,
        }
        return (
            severity_order[finding.severity],
            finding.node_id or "",
            finding.code or "",
            finding.message,
        )
