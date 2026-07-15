import type { FlowValidationResult, ValidationFinding, ValidationSeverity } from "../types/flow";

const severityStyles: Record<ValidationSeverity, string> = {
  error: "border-[#F0CACA] bg-[#FCEEEE] text-[#9A4B4B]",
  warning: "border-[#E8D6A8] bg-[#F8F0D9] text-[#846B2E]",
  info: "border-[#C9DCEB] bg-[#E8F0F7] text-[#3F5F7A]"
};

interface ValidationCardProps {
  validation: FlowValidationResult | null;
}

export function ValidationCard({ validation }: ValidationCardProps) {
  if (!validation) {
    return <EmptyCard title="Validation" message="Findings will appear after generation." />;
  }

  return (
    <section className="rounded-2xl bg-[#FAFCFE] p-6 shadow-sm ring-1 ring-[#D6E2EC]">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-[#6B8EAE]">Validation</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-[#3F5F7A]">Graph checks</h2>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            validation.is_valid ? "bg-[#E6F4EE] text-[#4E8167]" : "bg-[#FCEEEE] text-[#9A4B4B]"
          }`}
        >
          {validation.is_valid ? "Safe to simulate" : "Blocked"}
        </span>
      </div>

      {validation.findings.length === 0 ? (
        <p className="mt-5 rounded-2xl bg-[#E6F4EE] p-4 text-sm font-medium text-[#4E8167] ring-1 ring-[#C7E6D8]">
          No validation findings.
        </p>
      ) : (
        <div className="mt-5 space-y-3">
          {validation.findings.map((finding, index) => (
            <FindingCard key={`${finding.code}-${finding.node_id}-${index}`} finding={finding} />
          ))}
        </div>
      )}
    </section>
  );
}

function FindingCard({ finding }: { finding: ValidationFinding }) {
  return (
    <div className="rounded-2xl bg-[#E8F0F7] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs font-semibold text-[#6B8EAE]">
            {finding.code || "UNKNOWN"}
          </p>
          <p className="mt-1 text-sm text-[#3F5F7A]">{finding.message}</p>
          <p className="mt-2 text-xs text-[#6D879B]">
            Suggestion: Review the referenced node and adjust the workflow if needed.
          </p>
        </div>
        <span
          className={`rounded-full border px-2 py-1 text-xs font-semibold ${severityStyles[finding.severity]}`}
        >
          {finding.severity}
        </span>
      </div>
    </div>
  );
}

function EmptyCard({ title, message }: { title: string; message: string }) {
  return (
    <section className="rounded-2xl border border-dashed border-[#BFD0DE] bg-[#FAFCFE]/70 p-6">
      <h2 className="text-xl font-semibold tracking-tight text-[#3F5F7A]">{title}</h2>
      <p className="mt-2 text-sm text-[#6D879B]">{message}</p>
    </section>
  );
}
