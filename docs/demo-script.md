# FlowPilot Demo Script

## 0:00 Introduction

What to click:

- Open the frontend demo.
- Show the FlowPilot title and prompt builder.

Speaking points:

- FlowPilot is an AI-assisted workflow builder for turning plain-English automation ideas into structured workflows.
- The demo focuses on the safe core loop: generate, validate, explain, and simulate.
- It is intentionally scoped as a hackathon MVP rather than a full workflow platform.

## 0:30 Generate Workflow

What to click:

- Click the `Lead Routing` example prompt.
- Click `Generate`.

What to show:

- Generated workflow overview.
- Workflow metadata.
- Visual timeline.
- Raw JSON collapsed in the secondary section.

Speaking points:

- The prompt is converted into a typed `AutomationFlow`.
- The demo uses deterministic templates for supported scenarios so the flow is repeatable.
- The generated artifact is structured JSON, but the primary UI emphasizes workflow understanding.

## 1:30 Validation and Explanation

What to click:

- Scroll to the Validation and Explanation sections.

What to show:

- Validation findings and severity badges.
- Explanation summary.
- Step-by-step plain-English plan.
- Outcomes, assumptions, and notes.

Speaking points:

- Validation checks graph and business risks before execution.
- Warnings do not block simulation, but errors do.
- Explanation is deterministic and does not require an LLM.
- The intentional fallback loop in the lead-routing example appears as a warning, not a failure.

## 2:30 Simulation

What to click:

- In the simulation input, enter `buyer`.
- Click `Run Simulation`.

What to show:

- Completed status.
- Assigned team.
- Transcript.
- Execution trace.

Speaking points:

- Simulation is deterministic and uses supplied mock inputs.
- It never makes real external API calls.
- The transcript shows the business conversation.
- The trace shows how the engine moved through workflow nodes.

## 3:30 Risk Handling

What to click:

- Regenerate or edit the simulation answer to use an unexpected value, if demonstrating the fallback behavior.
- Run simulation again.

What to show:

- Repeated clarification behavior.
- Step-limit protection if the same unexpected answer loops.
- Validation warning for the cycle.

Speaking points:

- Retry loops can be intentional, but they must be bounded.
- FlowPilot flags suspicious cycles and the simulator enforces a maximum step count.
- This is the safety layer between AI-generated structure and execution.

## 4:30 Architecture and Closing

What to click:

- Show README architecture diagram or API docs.

What to show:

- FastAPI endpoints.
- Services: generation, validation, explanation, simulation.
- Tests and examples.

Speaking points:

- The architecture keeps models, services, API routes, and frontend concerns separated.
- Generation does not bypass validation.
- The MVP is ready for future additions like persistence, a React Flow editor, and real integrations.
