import type { AutomationFlow, FlowNode, NodeType } from "../types/flow";

interface WorkflowTimelineProps {
  flow: AutomationFlow | null;
}

const nodeCopy: Record<NodeType, { icon: string; label: string }> = {
  trigger: { icon: "T", label: "Trigger" },
  ask_question: { icon: "?", label: "Question" },
  condition: { icon: "C", label: "Condition" },
  send_message: { icon: "M", label: "Message" },
  assign_to_team: { icon: "A", label: "Action" },
  api_call: { icon: "API", label: "API" },
  wait: { icon: "W", label: "Wait" },
  end: { icon: "E", label: "End" }
};

export function WorkflowTimeline({ flow }: WorkflowTimelineProps) {
  if (!flow) {
    return (
      <section className="rounded-2xl bg-[#FAFCFE] p-6 shadow-sm ring-1 ring-[#D6E2EC]">
        <div className="flex items-center justify-center rounded-2xl bg-[#E8F0F7] px-6 py-14 text-center">
          <div>
            <p className="text-sm font-medium text-[#6B8EAE]">Workflow Overview</p>
            <p className="mt-2 max-w-sm text-sm leading-6 text-[#6D879B]">
              Generate a workflow to see a structured timeline of the trigger, decision points,
              actions, and outcomes.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-2xl bg-[#FAFCFE] p-6 shadow-sm ring-1 ring-[#D6E2EC]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[#6B8EAE]">Workflow Overview</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-[#3F5F7A]">{flow.name}</h2>
        </div>
        <div className="w-fit rounded-full bg-[#E8F0F7] px-3 py-1 text-xs font-semibold text-[#3F5F7A]">
          {flow.nodes.length} nodes
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {flow.nodes.map((node, index) => (
          <TimelineNode
            key={node.id}
            node={node}
            isLast={index === flow.nodes.length - 1}
          />
        ))}
      </div>
    </section>
  );
}

function TimelineNode({ node, isLast }: { node: FlowNode; isLast: boolean }) {
  const copy = nodeCopy[node.type];
  return (
    <div className="grid grid-cols-[2.5rem_1fr] gap-4">
      <div className="flex flex-col items-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#6B8EAE] text-xs font-semibold text-[#F8FBFD] shadow-sm">
          {copy.icon}
        </div>
        {!isLast && <div className="my-2 h-8 w-px bg-[#BFD0DE]" />}
      </div>
      <div className="rounded-2xl bg-[#E8F0F7] p-4 shadow-sm ring-1 ring-[#D6E2EC]">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-[#FAFCFE] px-2.5 py-1 text-xs font-semibold text-[#6B8EAE] ring-1 ring-[#D6E2EC]">
            {copy.label}
          </span>
          <span className="font-mono text-xs text-[#8AA6B8]">{node.id}</span>
        </div>
        <p className="mt-2 text-sm font-semibold text-[#3F5F7A]">{node.name}</p>
        <p className="mt-1 text-sm leading-6 text-[#587891]">{nodeDescription(node)}</p>
      </div>
    </div>
  );
}

function nodeDescription(node: FlowNode): string {
  if (node.type === "trigger" && typeof node.config.event === "string") {
    return `Starts on ${node.config.event.split("_").join(" ")}.`;
  }
  if (node.type === "ask_question" && typeof node.config.question === "string") {
    return node.config.question;
  }
  if (node.type === "condition" && typeof node.config.variable_name === "string") {
    return `Branches on ${node.config.variable_name}.`;
  }
  if (node.type === "send_message" && typeof node.config.message === "string") {
    return node.config.message;
  }
  if (node.type === "assign_to_team" && typeof node.config.team_name === "string") {
    return `Assigns to ${node.config.team_name}.`;
  }
  if (node.type === "api_call" && typeof node.config.url === "string") {
    return `Uses a mocked API call to ${node.config.url}.`;
  }
  if (node.type === "wait" && typeof node.config.duration_seconds === "number") {
    return `Waits ${node.config.duration_seconds} seconds in mock execution.`;
  }
  if (node.type === "end" && typeof node.config.outcome === "string") {
    return `Completes with ${node.config.outcome.split("_").join(" ")}.`;
  }
  return "Executes this workflow step.";
}
