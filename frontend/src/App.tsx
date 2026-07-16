import { useMemo, useState } from "react";
import { generateWorkflow, simulateWorkflow } from "./api/flowApi";
import { ExplanationCard } from "./components/ExplanationCard";
import { Header } from "./components/Header";
import { JsonViewer } from "./components/JsonViewer";
import { PromptPanel } from "./components/PromptPanel";
import { SimulationPanel } from "./components/SimulationPanel";
import { ValidationCard } from "./components/ValidationCard";
import { WorkflowSummary } from "./components/WorkflowSummary";
import { WorkflowTimeline } from "./components/WorkflowTimeline";
import type { GenerationMode, GenerationResponse, SimulationResult } from "./types/flow";

const DEFAULT_PROMPT =
  "When a new contact messages us, ask whether they are a buyer or seller. Route buyers to the sales team and send sellers a help article.";

export default function App() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [generationMode, setGenerationMode] = useState<GenerationMode>("mock");
  const [generation, setGeneration] = useState<GenerationResponse | null>(null);
  const [simulation, setSimulation] = useState<SimulationResult | null>(null);
  const [simulationInputs, setSimulationInputs] = useState<Record<string, string>>({});
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const flow = generation?.flow ?? null;
  const generationFailure = generation?.status === "failed" ? generation : null;
  const failureReasons = generationFailure
    ? [
        generationFailure.error_message,
        ...(generationFailure.validation?.findings.map((finding) => finding.message) ?? [])
      ].filter((reason): reason is string => Boolean(reason))
    : [];
  const questionDefaults = useMemo(() => {
    const defaults: Record<string, string> = {};
    flow?.nodes
      .filter((node) => node.type === "ask_question")
      .forEach((node) => {
        defaults[node.id] = simulationInputs[node.id] ?? "";
      });
    return defaults;
  }, [flow, simulationInputs]);

  async function handleGenerate() {
    setIsGenerating(true);
    setError(null);
    setSimulation(null);
    try {
      const response = await generateWorkflow(prompt, generationMode);
      setGeneration(response);
      const nextInputs: Record<string, string> = {};
      response.flow?.nodes
        .filter((node) => node.type === "ask_question")
        .forEach((node) => {
          nextInputs[node.id] = "";
        });
      setSimulationInputs(nextInputs);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to generate workflow.");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleRunSimulation() {
    if (!flow) {
      return;
    }

    setIsSimulating(true);
    setError(null);
    try {
      const response = await simulateWorkflow({
        flow,
        user_inputs: questionDefaults,
        max_steps: 50
      });
      setSimulation(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to run simulation.");
    } finally {
      setIsSimulating(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F3F6FA]">
      <Header />
      <main className="mx-auto w-full max-w-7xl space-y-8 px-4 pb-12 pt-8 sm:px-6 lg:px-8">
        <section className="grid w-full grid-cols-1 gap-6 lg:grid-cols-2">
          <PromptPanel
            prompt={prompt}
            generationMode={generationMode}
            isLoading={isGenerating}
            onPromptChange={setPrompt}
            onGenerationModeChange={setGenerationMode}
            onGenerate={handleGenerate}
          />

          <div className="space-y-6">
            <WorkflowTimeline flow={flow} />
            <WorkflowSummary flow={flow} />
          </div>
        </section>

        {error && (
          <div className="rounded-2xl bg-[#FCEEEE] p-4 text-sm font-medium text-[#9A4B4B] shadow-sm ring-1 ring-[#F0CACA]">
            {error}
          </div>
        )}

        {generationFailure && (
          <section className="rounded-2xl bg-[#FCEEEE] p-5 shadow-sm ring-1 ring-[#F0CACA]">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-[#F4D5D5] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[#9A4B4B]">
                {generationFailure.status}
              </span>
              <span className="text-sm font-medium text-[#6C7F8F]">
                Provider: {generationFailure.provider}
              </span>
              {generationFailure.error_code && (
                <span className="rounded-full bg-[#FAFCFE]/80 px-3 py-1 font-mono text-xs text-[#9A4B4B] ring-1 ring-[#F0CACA]">
                  {generationFailure.error_code}
                </span>
              )}
            </div>
            <h2 className="mt-4 text-lg font-semibold text-[#3F5F7A]">
              Workflow generation failed.
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#587891]">
              The AI response could not be converted into a valid workflow.
            </p>
            {failureReasons.length > 0 && (
              <div className="mt-4 rounded-xl bg-[#FAFCFE]/75 p-4 text-sm text-[#587891] ring-1 ring-[#F0CACA]/70">
                <p className="font-semibold text-[#3F5F7A]">Reason</p>
                <ul className="mt-2 space-y-1">
                  {failureReasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {generation?.status === "clarification_required" && (
          <div className="rounded-2xl bg-[#E8F0F7] p-4 text-sm font-medium text-[#3F5F7A] shadow-sm ring-1 ring-[#D6E2EC]">
            {generation.clarification_question}
          </div>
        )}

        <section className="grid w-full grid-cols-1 gap-6 lg:grid-cols-2">
          <ValidationCard validation={generation?.validation ?? null} />
          <ExplanationCard explanation={generation?.explanation ?? null} />
        </section>

        <SimulationPanel
          flow={flow}
          inputs={questionDefaults}
          result={simulation}
          isRunning={isSimulating}
          onInputChange={(nodeId, value) =>
            setSimulationInputs((current) => ({ ...current, [nodeId]: value }))
          }
          onRun={handleRunSimulation}
        />

        <JsonViewer flow={flow} generation={generation} />
      </main>
    </div>
  );
}
