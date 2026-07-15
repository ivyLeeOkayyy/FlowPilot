const EXAMPLES = [
  {
    label: "Lead Routing",
    prompt:
      "When a new contact messages us, ask whether they are a buyer or seller. Route buyers to the sales team and send sellers a help article."
  },
  {
    label: "Support Triage",
    prompt:
      "When a customer asks for support, ask whether the issue is billing, account access, or something else. Send billing questions to finance, account access issues to support, and route other issues to a human agent."
  },
  {
    label: "Order Status",
    prompt:
      "When a customer asks about an order, ask for the order ID, call the order status API, send the result on success, and route the conversation to support if the API fails."
  }
];

interface PromptPanelProps {
  prompt: string;
  isLoading: boolean;
  onPromptChange: (value: string) => void;
  onGenerate: () => void;
}

export function PromptPanel({
  prompt,
  isLoading,
  onPromptChange,
  onGenerate
}: PromptPanelProps) {
  return (
    <section className="rounded-2xl bg-[#FAFCFE] p-6 shadow-sm ring-1 ring-[#D6E2EC]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[#6B8EAE]">Prompt Builder</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-[#3F5F7A]">
            Describe an automation
          </h2>
          <p className="mt-2 text-sm leading-6 text-[#6D879B]">
            FlowPilot will generate a validated workflow, explain it, and prepare it for mock execution.
          </p>
        </div>
        <button
          onClick={onGenerate}
          disabled={isLoading || !prompt.trim()}
          className="inline-flex items-center justify-center rounded-xl bg-[#6B8EAE] px-4 py-2.5 text-sm font-semibold text-[#F8FBFD] shadow-sm transition hover:bg-[#5F819F] disabled:cursor-not-allowed disabled:bg-[#B9C8D3]"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#F8FBFD]/40 border-t-[#F8FBFD]" />
              Generating
            </span>
          ) : (
            "Generate"
          )}
        </button>
      </div>

      <textarea
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        className="mt-5 min-h-44 w-full resize-y rounded-2xl border border-[#D6E2EC] bg-[#E8F0F7] p-4 text-sm leading-6 text-[#3F5F7A] outline-none transition placeholder:text-[#8AA6B8] focus:border-[#6B8EAE] focus:bg-[#FAFCFE] focus:shadow-sm"
        placeholder="Example: Route buyer and seller leads from a new contact message..."
      />

      <div className="mt-4 flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example.label}
            onClick={() => onPromptChange(example.prompt)}
            className="rounded-full bg-[#E8F0F7] px-3 py-2 text-sm font-medium text-[#3F5F7A] transition hover:bg-[#DCE8F2]"
          >
            {example.label}
          </button>
        ))}
      </div>
    </section>
  );
}
