import type { AutomationFlow, FlowNode, SimulationResult } from "../types/flow";

interface SimulationPanelProps {
  flow: AutomationFlow | null;
  inputs: Record<string, string>;
  result: SimulationResult | null;
  isRunning: boolean;
  onInputChange: (nodeId: string, value: string) => void;
  onRun: () => void;
}

export function SimulationPanel({
  flow,
  inputs,
  result,
  isRunning,
  onInputChange,
  onRun
}: SimulationPanelProps) {
  const questionNodes = flow?.nodes.filter((node) => node.type === "ask_question") ?? [];

  return (
    <section className="rounded-2xl bg-[#FAFCFE] p-6 shadow-sm ring-1 ring-[#D6E2EC]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[#6B8EAE]">Simulation</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-[#3F5F7A]">Run a mock execution</h2>
          <p className="mt-2 text-sm text-[#6D879B]">
            Run the generated workflow with mock user answers.
          </p>
        </div>
        <button
          onClick={onRun}
          disabled={!flow || isRunning}
          className="inline-flex items-center justify-center rounded-xl bg-[#6B8EAE] px-4 py-2.5 text-sm font-semibold text-[#F8FBFD] transition hover:bg-[#5F819F] disabled:cursor-not-allowed disabled:bg-[#B9C8D3]"
        >
          {isRunning ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#F8FBFD]/40 border-t-[#F8FBFD]" />
              Running
            </span>
          ) : (
            "Run Simulation"
          )}
        </button>
      </div>

      {!flow && (
        <div className="mt-5 rounded-2xl border border-dashed border-[#BFD0DE] bg-[#E8F0F7] p-5 text-sm text-[#6D879B]">
          Generate a workflow before simulating.
        </div>
      )}

      {questionNodes.length > 0 && (
        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
          {questionNodes.map((node) => (
            <QuestionInput
              key={node.id}
              node={node}
              value={inputs[node.id] ?? ""}
              onChange={(value) => onInputChange(node.id, value)}
            />
          ))}
        </div>
      )}

      {result && (
        <div className="mt-5 space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={result.status} />
            {result.assigned_team && <Pill label="Assigned team" value={result.assigned_team} />}
            {result.completed_outcome && <Pill label="Outcome" value={result.completed_outcome} />}
          </div>

          {result.error_message && (
            <p className="rounded-2xl bg-[#FCEEEE] p-4 text-sm text-[#9A4B4B] ring-1 ring-[#F0CACA]">
              {result.error_message}
            </p>
          )}

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <div>
            <h3 className="text-sm font-semibold text-[#3F5F7A]">Transcript</h3>
            <div className="mt-2 space-y-2">
              {result.transcript.length === 0 ? (
                <p className="text-sm text-[#6D879B]">No transcript entries yet.</p>
              ) : (
                result.transcript.map((entry) => (
                  <div key={`${entry.step}-${entry.node_id}-${entry.role}`} className="rounded-2xl bg-[#E8F0F7] p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-[#6B8EAE]">
                      {entry.role} · step {entry.step} · {entry.node_id}
                    </p>
                    <p className="mt-1 text-sm text-[#3F5F7A]">{entry.message}</p>
                  </div>
                ))
              )}
            </div>
            </div>

            <div>
            <h3 className="text-sm font-semibold text-[#3F5F7A]">Execution Trace</h3>
            <div className="mt-2 max-h-72 overflow-auto rounded-2xl bg-[#E8F0F7]">
              {result.trace.map((entry) => (
                <div key={`${entry.step}-${entry.node_id}-${entry.action}`} className="border-b border-[#D6E2EC] p-3 last:border-0">
                  <p className="font-mono text-xs text-[#6B8EAE]">
                    #{entry.step} {entry.node_id} · {entry.node_type}
                  </p>
                  <p className="mt-1 text-sm text-[#3F5F7A]">
                    {entry.action}
                    {entry.selected_transition_target ? ` -> ${entry.selected_transition_target}` : ""}
                  </p>
                </div>
              ))}
            </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function QuestionInput({
  node,
  value,
  onChange
}: {
  node: FlowNode;
  value: string;
  onChange: (value: string) => void;
}) {
  const question = typeof node.config.question === "string" ? node.config.question : node.name;
  return (
    <label className="block rounded-2xl bg-[#E8F0F7] p-4">
      <span className="text-xs font-semibold uppercase tracking-wide text-[#6B8EAE]">
        {node.name}
      </span>
      <span className="mt-1 block text-sm text-[#3F5F7A]">{question}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-3 w-full rounded-xl border border-[#D6E2EC] bg-[#FAFCFE] px-3 py-2 text-sm text-[#3F5F7A] outline-none transition placeholder:text-[#8AA6B8] focus:border-[#6B8EAE] focus:shadow-sm"
        placeholder="Type an answer"
      />
    </label>
  );
}

function StatusBadge({ status }: { status: string }) {
  const isGood = status === "completed";
  const isWaiting = status === "waiting_for_input";
  const classes = isGood
    ? "bg-[#E6F4EE] text-[#4E8167]"
    : isWaiting
      ? "bg-[#E8F0F7] text-[#3F5F7A]"
      : "bg-[#F8F0D9] text-[#846B2E]";

  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${classes}`}>{status}</span>;
}

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full bg-[#E8F0F7] px-3 py-1 text-xs text-[#587891]">
      {label}: <strong className="text-[#3F5F7A]">{value}</strong>
    </span>
  );
}
