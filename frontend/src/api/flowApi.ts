import type { GenerationResponse, SimulationRequest, SimulationResult } from "../types/flow";

const BASE_URL = "http://localhost:8000";

async function requestJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    let detail = "Request failed. Check that the FlowPilot backend is running.";
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export function generateWorkflow(prompt: string): Promise<GenerationResponse> {
  return requestJson<GenerationResponse>("/api/flows/generate", {
    prompt,
    mode: "mock",
    include_explanation: true
  });
}

export function simulateWorkflow(request: SimulationRequest): Promise<SimulationResult> {
  return requestJson<SimulationResult>("/api/flows/simulate", request);
}
