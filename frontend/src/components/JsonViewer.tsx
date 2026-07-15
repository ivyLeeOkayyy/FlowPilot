import type { AutomationFlow } from "../types/flow";

interface JsonViewerProps {
  flow: AutomationFlow | null;
}

export function JsonViewer({ flow }: JsonViewerProps) {
  return (
    <details className="rounded-2xl bg-[#FAFCFE]/80 p-6 shadow-sm ring-1 ring-[#D6E2EC]">
      <summary className="cursor-pointer text-sm font-semibold text-[#587891]">
        Raw workflow JSON
      </summary>
      <pre className="mt-4 max-h-[420px] overflow-auto rounded-2xl bg-[#2F4B63] p-4 font-mono text-xs leading-5 text-[#E8F0F7]">
        {flow ? JSON.stringify(flow, null, 2) : "Generate a workflow to inspect the JSON artifact."}
      </pre>
    </details>
  );
}
