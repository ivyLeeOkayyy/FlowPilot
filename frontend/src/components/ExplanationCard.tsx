import type { FlowExplanation } from "../types/flow";

interface ExplanationCardProps {
  explanation: FlowExplanation | null;
}

export function ExplanationCard({ explanation }: ExplanationCardProps) {
  if (!explanation) {
    return (
      <section className="rounded-2xl border border-dashed border-[#BFD0DE] bg-[#FAFCFE]/70 p-6">
        <h2 className="text-xl font-semibold tracking-tight text-[#3F5F7A]">Explanation</h2>
        <p className="mt-2 text-sm text-[#6D879B]">
          FlowPilot will summarize the generated workflow here.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl bg-[#FAFCFE] p-6 shadow-sm ring-1 ring-[#D6E2EC]">
      <p className="text-sm font-medium text-[#6B8EAE]">Explanation</p>
      <h2 className="mt-1 text-xl font-semibold tracking-tight text-[#3F5F7A]">Plain-English plan</h2>
      <p className="mt-4 text-sm leading-6 text-[#587891]">{explanation.summary}</p>
      <p className="mt-4 rounded-2xl bg-[#E8F0F7] p-4 text-sm text-[#3F5F7A]">
        {explanation.trigger_description}
      </p>

      <div className="mt-6">
        <h3 className="text-sm font-semibold text-[#3F5F7A]">Steps</h3>
        <div className="mt-3 space-y-0">
          {explanation.steps.map((step, index) => (
            <div key={step.node_id} className="grid grid-cols-[2rem_1fr] gap-3">
              <div className="flex flex-col items-center">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#6B8EAE] text-sm font-semibold text-[#F8FBFD]">
                  {step.order}
                </div>
                {index < explanation.steps.length - 1 && (
                  <div className="h-full min-h-8 w-px bg-[#BFD0DE]" />
                )}
              </div>
              <div className="pb-5">
                <p className="text-sm font-semibold text-[#3F5F7A]">{step.title}</p>
                <p className="mt-1 text-sm leading-6 text-[#587891]">{step.description}</p>
                {step.next_steps.length > 0 && (
                  <ul className="mt-2 space-y-1 text-xs text-[#6D879B]">
                    {step.next_steps.map((nextStep) => (
                      <li key={nextStep}>{nextStep}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <InfoList title="Outcomes" items={explanation.outcomes} />
      <InfoList title="Assumptions" items={explanation.assumptions} />
      <InfoList title="Notes" items={explanation.notes} />
    </section>
  );
}

function InfoList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="mt-5">
      <h3 className="text-sm font-semibold text-[#3F5F7A]">{title}</h3>
      <ul className="mt-2 space-y-1 text-sm text-[#587891]">
        {items.map((item) => (
          <li key={item} className="rounded-xl bg-[#E8F0F7] px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
