from collections import deque
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from app.models import (
    ApiCallConfig,
    AskQuestionConfig,
    AssignToTeamConfig,
    AutomationFlow,
    ConditionConfig,
    EndConfig,
    FlowExplanation,
    FlowNode,
    FlowStepExplanation,
    NodeType,
    RiskExplanation,
    SendMessageConfig,
    TriggerConfig,
    ValidationFinding,
    WaitConfig,
)
from app.services.validation_service import FlowValidationService


class FlowExplanationService:
    def explain(self, flow: AutomationFlow) -> FlowExplanation:
        validation_result = FlowValidationService().validate(flow)
        nodes_by_id = {node.id: node for node in flow.nodes}
        reachable_nodes = self._reachable_nodes(flow, nodes_by_id)

        steps = [
            self._explain_step(index, node, nodes_by_id)
            for index, node in enumerate(reachable_nodes, start=1)
        ]
        outcomes = self._collect_outcomes(reachable_nodes)

        return FlowExplanation(
            flow_id=flow.id,
            flow_name=flow.name,
            summary=self._summary(flow, reachable_nodes, outcomes),
            trigger_description=self._trigger_description(flow, nodes_by_id),
            steps=steps,
            outcomes=outcomes,
            assumptions=list(flow.metadata.assumptions),
            risks=[
                self._risk_from_finding(finding)
                for finding in validation_result.findings
            ],
            is_safe_to_simulate=validation_result.is_valid,
            notes=self._notes(reachable_nodes),
        )

    def _reachable_nodes(
        self,
        flow: AutomationFlow,
        nodes_by_id: dict[str, FlowNode],
    ) -> list[FlowNode]:
        ordered: list[FlowNode] = []
        seen: set[str] = set()
        pending: deque[str] = deque([flow.trigger_node_id])

        while pending:
            node_id = pending.popleft()
            if node_id in seen:
                continue
            node = nodes_by_id.get(node_id)
            if node is None:
                continue

            seen.add(node_id)
            ordered.append(node)
            for transition in node.transitions:
                if transition.target_node_id not in seen:
                    pending.append(transition.target_node_id)

        return ordered

    def _explain_step(
        self,
        order: int,
        node: FlowNode,
        nodes_by_id: dict[str, FlowNode],
    ) -> FlowStepExplanation:
        return FlowStepExplanation(
            order=order,
            node_id=node.id,
            node_type=node.type,
            title=self._title(node),
            description=self._description(node),
            next_steps=self._next_steps(node, nodes_by_id),
        )

    def _title(self, node: FlowNode) -> str:
        prefix_by_type = {
            NodeType.TRIGGER: "Trigger",
            NodeType.SEND_MESSAGE: "Send message",
            NodeType.ASK_QUESTION: "Ask question",
            NodeType.CONDITION: "Condition",
            NodeType.API_CALL: "API call",
            NodeType.ASSIGN_TO_TEAM: "Assign to team",
            NodeType.WAIT: "Wait",
            NodeType.END: "End",
        }
        return f"{prefix_by_type[node.type]}: {node.name}"

    def _description(self, node: FlowNode) -> str:
        if node.type is NodeType.TRIGGER:
            return self._describe_trigger(node)
        if node.type is NodeType.SEND_MESSAGE:
            config = self._send_message_config(node)
            return f"The bot sends this message: \"{config.message}\""
        if node.type is NodeType.ASK_QUESTION:
            return self._describe_ask_question(node)
        if node.type is NodeType.CONDITION:
            return self._describe_condition(node)
        if node.type is NodeType.API_CALL:
            return self._describe_api_call(node)
        if node.type is NodeType.ASSIGN_TO_TEAM:
            config = self._assign_to_team_config(node)
            return f"The workflow assigns the conversation to the {config.team_name} team."
        if node.type is NodeType.WAIT:
            config = self._wait_config(node)
            return (
                f"The workflow waits for {config.duration_seconds} seconds. "
                "Mock simulation records the wait and does not actually sleep."
            )
        if node.type is NodeType.END:
            config = self._end_config(node)
            return f"The workflow completes with outcome: {self._humanize(config.outcome)}."
        return f"The workflow executes {node.name}."

    def _describe_trigger(self, node: FlowNode) -> str:
        config = self._trigger_config(node)
        return self._event_sentence(config.event)

    def _describe_ask_question(self, node: FlowNode) -> str:
        config = self._ask_question_config(node)
        if config.expected_answers:
            answers = self._join_readable(config.expected_answers)
            return (
                f"The bot asks \"{config.question}\" and stores the answer in "
                f"`{config.variable_name}`. Expected answers are {answers}."
            )
        return (
            f"The bot asks \"{config.question}\" and stores the free-text answer "
            f"in `{config.variable_name}`."
        )

    def _describe_condition(self, node: FlowNode) -> str:
        config = self._condition_config(node)
        branch_text: list[str] = []
        for transition in node.transitions:
            if transition.is_fallback:
                branch_text.append(
                    f"otherwise it follows the fallback to {transition.target_node_id}"
                )
            elif transition.condition:
                branch_text.append(
                    f"if `{transition.condition}` it goes to {transition.target_node_id}"
                )
            elif transition.label:
                branch_text.append(
                    f"for {transition.label} it goes to {transition.target_node_id}"
                )
            else:
                branch_text.append(f"it can continue to {transition.target_node_id}")

        if branch_text:
            return (
                f"The workflow evaluates `{config.variable_name}` and branches: "
                f"{'; '.join(branch_text)}."
            )
        return f"The workflow evaluates `{config.variable_name}`, but no branches are configured."

    def _describe_api_call(self, node: FlowNode) -> str:
        config = self._api_call_config(node)
        branch_parts: list[str] = []
        for transition in node.transitions:
            label = transition.label or transition.condition
            if transition.is_fallback:
                branch_parts.append(f"fallback to {transition.target_node_id}")
            elif label:
                branch_parts.append(f"{label} to {transition.target_node_id}")

        branch_sentence = (
            f" Recognized branches: {'; '.join(branch_parts)}."
            if branch_parts
            else ""
        )
        return (
            f"The workflow prepares a mocked {config.method} request to "
            f"{self._redact_url(config.url)} with a {config.timeout_seconds}-second "
            "timeout. The MVP uses supplied mock outcomes and does not perform a "
            f"real network request.{branch_sentence}"
        )

    def _next_steps(
        self,
        node: FlowNode,
        nodes_by_id: dict[str, FlowNode],
    ) -> list[str]:
        next_steps: list[str] = []
        for transition in node.transitions:
            target = nodes_by_id.get(transition.target_node_id)
            target_name = target.name if target else transition.target_node_id
            missing_suffix = " (missing node)" if target is None else ""

            if transition.is_fallback:
                next_steps.append(
                    f"Otherwise, continue to {target_name}{missing_suffix}."
                )
            elif transition.condition:
                next_steps.append(
                    f"If {transition.condition}, continue to {target_name}{missing_suffix}."
                )
            elif transition.label:
                next_steps.append(
                    f"On {transition.label}, continue to {target_name}{missing_suffix}."
                )
            else:
                next_steps.append(f"Continue to {target_name}{missing_suffix}.")
        return next_steps

    def _summary(
        self,
        flow: AutomationFlow,
        reachable_nodes: list[FlowNode],
        outcomes: list[str],
    ) -> str:
        trigger = next(
            (node for node in reachable_nodes if node.type is NodeType.TRIGGER),
            None,
        )
        questions = [
            self._ask_question_config(node).question
            for node in reachable_nodes
            if node.type is NodeType.ASK_QUESTION
        ]
        assignments = [
            self._assign_to_team_config(node).team_name
            for node in reachable_nodes
            if node.type is NodeType.ASSIGN_TO_TEAM
        ]
        messages = [
            self._send_message_config(node).message
            for node in reachable_nodes
            if node.type is NodeType.SEND_MESSAGE
        ]

        parts: list[str] = []
        if trigger is not None:
            parts.append(self._event_sentence(self._trigger_config(trigger).event))
        else:
            parts.append(f"This workflow is named {flow.name}.")
        if questions:
            parts.append(f"It asks: \"{questions[0]}\"")
        if assignments:
            parts.append(f"It can route work to the {self._join_readable(assignments)} team.")
        if messages:
            parts.append(f"It can send messages such as \"{messages[0]}\"")
        if outcomes:
            parts.append(f"It can complete with {self._join_readable(outcomes)}.")

        return " ".join(parts)

    def _trigger_description(
        self,
        flow: AutomationFlow,
        nodes_by_id: dict[str, FlowNode],
    ) -> str:
        trigger = nodes_by_id.get(flow.trigger_node_id)
        if trigger is None or trigger.type is not NodeType.TRIGGER:
            return "The workflow trigger cannot be described because the trigger node is missing."
        return self._describe_trigger(trigger)

    def _collect_outcomes(self, reachable_nodes: list[FlowNode]) -> list[str]:
        outcomes: list[str] = []
        seen: set[str] = set()
        for node in reachable_nodes:
            if node.type is not NodeType.END:
                continue
            outcome = self._humanize(self._end_config(node).outcome) or node.name
            if outcome not in seen:
                outcomes.append(outcome)
                seen.add(outcome)
        return outcomes

    def _risk_from_finding(self, finding: ValidationFinding) -> RiskExplanation:
        return RiskExplanation(
            code=finding.code or "UNKNOWN",
            severity=finding.severity,
            node_id=finding.node_id,
            summary=finding.message,
            recommendation=getattr(finding, "suggestion", None),
        )

    def _notes(self, reachable_nodes: list[FlowNode]) -> list[str]:
        notes: list[str] = []
        if any(node.type is NodeType.API_CALL for node in reachable_nodes):
            notes.append("API calls are simulated using supplied mock outcomes.")
        if any(node.type is NodeType.CONDITION for node in reachable_nodes):
            notes.append("Conditions support only a constrained syntax during simulation.")
        if self._has_cycle_involving_question(reachable_nodes):
            notes.append(
                "Repeated question input is reused by node ID in the current simulator."
            )
        return notes

    def _has_cycle_involving_question(self, reachable_nodes: list[FlowNode]) -> bool:
        nodes_by_id = {node.id: node for node in reachable_nodes}
        adjacency = {
            node.id: [
                transition.target_node_id
                for transition in node.transitions
                if transition.target_node_id in nodes_by_id
            ]
            for node in reachable_nodes
        }

        for question_node in [
            node for node in reachable_nodes if node.type is NodeType.ASK_QUESTION
        ]:
            seen: set[str] = set()
            pending: deque[str] = deque(adjacency[question_node.id])
            while pending:
                node_id = pending.popleft()
                if node_id == question_node.id:
                    return True
                if node_id in seen:
                    continue
                seen.add(node_id)
                pending.extend(adjacency.get(node_id, []))
        return False

    def _event_sentence(self, event: str) -> str:
        words = event.replace("_", " ").strip()
        if words == "new contact message":
            return "The workflow starts when a new contact sends a message."
        if words == "new customer message":
            return "The workflow starts when a new customer sends a message."
        if words.endswith(" message") and words.startswith("new "):
            actor = words.removeprefix("new ").removesuffix(" message")
            return f"The workflow starts when a new {actor} sends a message."
        if words.endswith(" created"):
            subject = words.removesuffix(" created")
            return f"The workflow starts when {self._article(subject)} {subject} is created."
        if words.startswith(("new ", "order ", "customer ", "contact ")):
            return f"The workflow starts when {self._article(words)} {words}."
        return f"The workflow starts when {words} occurs."

    def _article(self, phrase: str) -> str:
        return "an" if phrase[:1].lower() in {"a", "e", "i", "o", "u"} else "a"

    def _redact_url(self, url: str) -> str:
        split = urlsplit(url)
        if not split.query:
            return urlunsplit((split.scheme, split.netloc, split.path, "", ""))
        query_names = sorted({name for name, _ in parse_qsl(split.query, keep_blank_values=True)})
        redacted_query = "&".join(f"{name}=<redacted>" for name in query_names)
        return urlunsplit((split.scheme, split.netloc, split.path, redacted_query, ""))

    def _humanize(self, value: str) -> str:
        return value.replace("_", " ").replace("-", " ").strip()

    def _join_readable(self, values: list[str]) -> str:
        cleaned = [self._humanize(value) for value in values]
        if not cleaned:
            return ""
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return f"{cleaned[0]} and {cleaned[1]}"
        return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"

    def _trigger_config(self, node: FlowNode) -> TriggerConfig:
        return node.config  # type: ignore[return-value]

    def _send_message_config(self, node: FlowNode) -> SendMessageConfig:
        return node.config  # type: ignore[return-value]

    def _ask_question_config(self, node: FlowNode) -> AskQuestionConfig:
        return node.config  # type: ignore[return-value]

    def _condition_config(self, node: FlowNode) -> ConditionConfig:
        return node.config  # type: ignore[return-value]

    def _api_call_config(self, node: FlowNode) -> ApiCallConfig:
        return node.config  # type: ignore[return-value]

    def _assign_to_team_config(self, node: FlowNode) -> AssignToTeamConfig:
        return node.config  # type: ignore[return-value]

    def _wait_config(self, node: FlowNode) -> WaitConfig:
        return node.config  # type: ignore[return-value]

    def _end_config(self, node: FlowNode) -> EndConfig:
        return node.config  # type: ignore[return-value]
