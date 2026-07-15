export type NodeType =
  | "trigger"
  | "send_message"
  | "ask_question"
  | "condition"
  | "api_call"
  | "assign_to_team"
  | "wait"
  | "end";

export type ValidationSeverity = "error" | "warning" | "info";
export type GenerationStatus =
  | "generated"
  | "generated_with_warnings"
  | "clarification_required"
  | "failed";
export type SimulationStatus =
  | "completed"
  | "waiting_for_input"
  | "failed"
  | "step_limit_exceeded";

export interface Transition {
  target_node_id: string;
  label: string | null;
  condition: string | null;
  is_fallback: boolean;
}

export interface FlowNode {
  id: string;
  type: NodeType;
  name: string;
  config: Record<string, unknown>;
  transitions: Transition[];
}

export interface FlowMetadata {
  source_prompt: string | null;
  generator: string;
  model_name: string | null;
  created_at: string;
  assumptions: string[];
  warnings: string[];
}

export interface AutomationFlow {
  id: string;
  name: string;
  description: string | null;
  version: number;
  trigger_node_id: string;
  nodes: FlowNode[];
  metadata: FlowMetadata;
}

export interface ValidationFinding {
  severity: ValidationSeverity;
  message: string;
  node_id: string | null;
  code: string | null;
}

export interface FlowValidationResult {
  is_valid: boolean;
  findings: ValidationFinding[];
}

export interface FlowStepExplanation {
  order: number;
  node_id: string;
  node_type: NodeType;
  title: string;
  description: string;
  next_steps: string[];
}

export interface RiskExplanation {
  code: string;
  severity: ValidationSeverity;
  node_id: string | null;
  summary: string;
  recommendation: string | null;
}

export interface FlowExplanation {
  flow_id: string;
  flow_name: string;
  summary: string;
  trigger_description: string;
  steps: FlowStepExplanation[];
  outcomes: string[];
  assumptions: string[];
  risks: RiskExplanation[];
  is_safe_to_simulate: boolean;
  notes: string[];
}

export interface GenerationResponse {
  status: GenerationStatus;
  flow: AutomationFlow | null;
  validation: FlowValidationResult | null;
  explanation: FlowExplanation | null;
  clarification_question: string | null;
  assumptions: string[];
  provider: string;
  model_name: string | null;
  error_code: string | null;
  error_message: string | null;
}

export interface MockApiOutcome {
  node_id: string;
  success: boolean;
  status_code: number;
  response: Record<string, unknown>;
  error_message: string | null;
}

export interface SimulationRequest {
  flow: AutomationFlow;
  user_inputs: Record<string, string>;
  api_outcomes?: Record<string, MockApiOutcome>;
  initial_variables?: Record<string, unknown>;
  max_steps?: number;
}

export interface TranscriptEntry {
  step: number;
  node_id: string;
  role: "system" | "bot" | "user";
  message: string;
}

export interface ExecutionTraceEntry {
  step: number;
  node_id: string;
  node_type: NodeType;
  action: string;
  selected_transition_target: string | null;
  details: Record<string, unknown>;
}

export interface SimulationResult {
  trace_id: string;
  status: SimulationStatus;
  current_node_id: string | null;
  completed_outcome: string | null;
  assigned_team: string | null;
  variables: Record<string, unknown>;
  transcript: TranscriptEntry[];
  trace: ExecutionTraceEntry[];
  steps_executed: number;
  error_code: string | null;
  error_message: string | null;
}
