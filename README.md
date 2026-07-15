# FlowPilot

FlowPilot is a lightweight AI-assisted automation builder created as a hackathon demo.

Users describe an automation in plain English, and FlowPilot converts that intent into a structured workflow, validates the generated flow, explains it in plain language, and allows the user to run a mock execution before using it.

Example:

> When a new customer contacts us, ask whether they need sales, support, or order help. Route sales inquiries to the sales team, send support users a help article, and ask order users for their order ID.

FlowPilot will:

1. generate a structured automation flow;
2. validate the flow and highlight risky or broken paths;
3. explain the automation in plain English;
4. run a mock conversation through the flow;
5. suggest fixes and test cases when problems are found.

---

## Problem

Creating automation workflows manually requires users to translate business intent into nodes, branches, conditions, and routing rules.

That process is error-prone because a flow may contain:

- unreachable nodes;
- missing fallback branches;
- invalid node references;
- unsafe API calls;
- loops without limits;
- routes that never reach a terminal action;
- missing handling for unexpected user input.

FlowPilot reduces that friction by converting natural-language intent into a concrete workflow artifact and reviewing it before execution.

---

## MVP Scope

The prototype intentionally prioritizes a small, working backend over a broad visual builder.

### Included

- Natural-language automation input
- Structured workflow generation
- JSON flow artifact
- Deterministic validation
- Plain-English explanation
- Mock conversation execution
- Agent-generated review suggestions
- Agent-generated test cases
- In-memory storage
- Basic execution logs and trace IDs
- Interactive API documentation through FastAPI

### Supported node types

- `trigger`
- `send_message`
- `ask_question`
- `condition`
- `api_call`
- `assign_to_team`
- `wait`
- `end`

### Out of scope

- Real messaging platform integration
- Authentication and multi-tenancy
- Persistent database storage
- Production-grade prompt management
- Full drag-and-drop graph editing
- Real external API execution
- Human approval workflows
- Deployment infrastructure

---

## Core Flow

```text
Describe -> Generate -> Validate -> Explain -> Simulate
```

---

## Example Prompts

### Lead qualification

> When a new contact messages us, ask whether they are a buyer or seller. Route buyers to the sales team and send sellers a help article.

### Support triage

> When a customer asks for help, ask whether the issue is billing, account access, or something else. Send billing questions to finance, account access issues to support, and route unknown issues to a human agent.

### Order status

> When a customer asks about an order, ask for the order ID, call the order status API, send the result, and route the conversation to support if the API fails.

---

## Architecture

```text
Client / Swagger UI
        |
        v
FastAPI API Layer
        |
        +--> Flow Generation Service
        +--> Flow Validation Service
        +--> Flow Explanation Service
        +--> Flow Simulation Engine
        +--> Test Case Generation Service
        +--> In-Memory Repository
```

### Main components

- **Flow Generation Service**: converts plain-English intent into a typed workflow.
- **Validation Service**: performs deterministic schema and graph checks.
- **Explanation Service**: describes the workflow in plain language.
- **Simulation Engine**: executes nodes with mock user input and mock API responses.
- **Test Generation Service**: proposes happy-path, fallback, and failure-path tests.
- **In-Memory Repository**: stores flows for the lifetime of the application process.

---

## Proposed Technology

- Python 3.12+
- FastAPI
- Pydantic v2
- Uvicorn
- Pytest
- Structured JSON logging
- Optional LLM provider integration

---

## Quality and Safety

The application will validate:

- unique node IDs;
- valid trigger nodes;
- valid transition targets;
- graph reachability;
- terminal path existence;
- fallback branches;
- possible infinite loops;
- API failure handling;
- unsupported node configuration;
- accidental secret exposure.

The simulation engine will use a maximum step limit and will never execute real external API calls in the MVP.

### Validation

FlowPilot uses Pydantic for schema validation and a deterministic validation service for graph and business-rule checks.

Validation findings use stable machine-readable codes and one of three severities:

- `error`: the flow is not valid.
- `warning`: the flow can still be used, but should be reviewed.
- `info`: the flow is valid, with a helpful note.

The validator checks transition targets, reachability, terminal paths, fallback branches, suspicious cycles, duplicate transitions, API success and failure paths, question variables, and empty messages.

### Mock Simulation

FlowPilot can run a deterministic mock execution of a validated workflow without calling external services.

The simulator supports trigger, message, question, condition, API call, team assignment, wait, and end nodes. User answers are supplied by ask-question node ID, and mock API outcomes are supplied by API-call node ID.

If a required user answer is missing, execution returns `waiting_for_input` instead of failing. API calls require explicit mock outcomes and never make real network requests.

Execution uses a maximum step count to stop retry loops safely. In this MVP, user inputs are reused by node ID, so repeated fallback loops with the same unexpected answer will eventually return `step_limit_exceeded`.

### Plain-English Explanation

FlowPilot can generate deterministic plain-English explanations for existing workflow artifacts without using an LLM.

The explanation service walks reachable nodes in breadth-first order from the trigger, describes each step, lists reachable completion outcomes, and includes validation risks with their severity and stable codes.

API URLs are described defensively so query parameter values are not exposed. Explanation output is intended for review and demo clarity; it does not generate or modify workflows.

---

## Agentic Development

Codex or another coding agent will be used intentionally for:

- architecture proposals;
- schema generation;
- implementation;
- code review;
- debugging;
- test design;
- regression analysis.

Agent output will be reviewed and validated rather than accepted blindly.

Important prompts, findings, and manual decisions will be recorded in:

```text
docs/agent-log.md
```

---

## Suggested Project Structure

```text
flowpilot/
├── app/
│   ├── api/
│   ├── models/
│   ├── services/
│   ├── executors/
│   ├── repositories/
│   ├── core/
│   └── main.py
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   ├── agent-log.md
│   ├── architecture.md
│   ├── write-up.md
│   └── demo-script.md
├── examples/
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Proposed API

```text
POST /api/flows/generate
POST /api/flows/validate
POST /api/flows/simulate
POST /api/flows/explain
POST /api/flows/{flow_id}/validate
GET  /api/flows/{flow_id}/explain
POST /api/flows/{flow_id}/simulate
POST /api/flows/{flow_id}/tests/generate
GET  /api/flows/{flow_id}
GET  /health
```

---

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Run tests:

```bash
pytest
```

---

## Trade-offs

- In-memory storage keeps the demo small and easy to run.
- Mock API calls avoid external dependencies and secret handling.
- Swagger UI provides a real interactive prototype without requiring a frontend.
- A constrained node vocabulary keeps the execution engine predictable.

---

## Possible V2 Features

- React Flow visual editor
- PostgreSQL persistence
- Workflow versioning and rollback
- Human approval before publishing
- Prompt and model version tracking
- Credential vault
- Role-based access control
- Workflow analytics
- Reusable templates
- Workflow diff and regression simulation
- Evaluation dataset for generation quality
