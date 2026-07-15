export function Header() {
  return (
    <header className="border-b border-[#D6E2EC] bg-[#F8FBFD]/85 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:flex-row lg:items-end lg:justify-between lg:px-8">
        <div className="max-w-3xl">
          <p className="text-sm font-semibold uppercase text-[#6B8EAE]">
            FlowPilot
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[#3F5F7A] sm:text-5xl">
            AI-assisted workflow builder
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[#587891]">
            Turn plain-English automation ideas into validated and executable workflows.
          </p>
        </div>
        <div className="w-fit rounded-full bg-[#E8F0F7] px-4 py-2 text-xs font-semibold text-[#3F5F7A] shadow-sm ring-1 ring-[#D6E2EC] sm:text-sm">
          Prompt {"->"} Generate {"->"} Validate {"->"} Explain {"->"} Simulate
        </div>
      </div>
    </header>
  );
}
