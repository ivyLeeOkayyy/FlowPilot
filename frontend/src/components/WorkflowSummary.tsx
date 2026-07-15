import type { AutomationFlow } from "../types/flow";

interface WorkflowSummaryProps {
  flow: AutomationFlow | null;
}

export function WorkflowSummary({ flow }: WorkflowSummaryProps) {
  if (!flow) {
    return (
      <section className="rounded-2xl border border-dashed border-[#BFD0DE] bg-[#FAFCFE]/70 p-6 text-sm leading-6 text-[#6D879B]">
        The generated workflow summary will appear here with node count, trigger, version, and generator metadata.
      </section>
    );
  }

  return (
    <section className="rounded-2xl bg-[#FAFCFE] p-6 shadow-sm ring-1 ring-[#D6E2EC]">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[#6B8EAE]">Workflow Result</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-[#3F5F7A]">{flow.name}</h2>
        </div>
        <span className="w-fit rounded-full bg-[#E6F4EE] px-3 py-1 text-xs font-semibold text-[#4E8167]">
          Generated
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[#6D879B]">
        {flow.description || "No description provided."}
      </p>

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="Nodes" value={String(flow.nodes.length)} />
        <Metric label="Trigger" value={flow.trigger_node_id} />
        <Metric label="Version" value={`v${flow.version}`} />
        <Metric label="Generator" value={flow.metadata.generator} />
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-[#E8F0F7] p-3">
      <p className="text-xs font-medium uppercase text-[#6B8EAE]">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-[#3F5F7A]">{value}</p>
    </div>
  );
}
