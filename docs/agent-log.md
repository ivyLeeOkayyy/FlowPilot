# Agent Log

## 2026-07-14 - Initial Project Setup

### Task

Complete the initial FlowPilot project setup for a public hackathon-style FastAPI demo, including project metadata, package structure, health endpoint, tests, repository guidance, and documentation updates.

### Codex Contribution

- Read the existing README before making changes.
- Inspected the repository structure, current git status, git remote, and git user configuration.
- Created the initial backend-first FastAPI application structure.
- Added a typed Pydantic health response model and `GET /health` route.
- Added project metadata, runtime dependencies, development dependencies, and pytest configuration.
- Added repository rules for future agent-assisted work.
- Added an integration test for the health endpoint.

### Manual Review Checklist

- [ ] Confirm the MIT license holder is correct.
- [ ] Confirm the package metadata in `pyproject.toml` is appropriate for public release.
- [ ] Review `AGENTS.md` project rules and adjust any team-specific conventions.
- [ ] Run the local setup commands in a fresh virtual environment.
- [ ] Review the health endpoint response and API metadata in FastAPI docs.

### Tests Executed

- `pytest` - failed because `pytest` was not installed on the shell path.
- `python3 -m pytest` - failed because the system Python did not have `pytest` installed.
- `python3 -m venv .venv` - created a local virtual environment.
- `.venv/bin/python -m pip install -e '.[dev]'` - first failed due restricted network access, then failed due local certificate verification, then exposed a Hatch package-selection issue.
- `.venv/bin/python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -e '.[dev]'` - passed after adding the explicit Hatch wheel package target.
- `.venv/bin/python -m pytest` - passed with 1 test and 1 upstream deprecation warning from FastAPI/Starlette test client imports.

### Assumptions

- The repository owner's display name can be safely determined from `git config user.name` as `Ivy Lee`.
- The current project version is `0.1.0`.
- No workflow generation, validation, explanation, simulation, or LLM integration should be implemented in this setup task.

## 2026-07-15 - Initial Setup Verification

### Task

Re-check the initial FlowPilot project setup against the requested public hackathon demo requirements.

### Codex Contribution

- Re-read the README before making changes.
- Inspected the repository structure, git status, git remote, git user configuration, application files, tests, metadata, license, environment example, and agent rules.
- Confirmed the initial FastAPI health endpoint setup is already present.
- Removed a duplicated README `Run tests` block.
- Re-ran the full test suite.

### Manual Review Checklist

- [ ] Confirm the MIT license holder is correct.
- [ ] Confirm the README local development commands work in the repository owner's preferred Python environment.
- [ ] Review the FastAPI docs metadata in a browser.
- [ ] Confirm the upstream FastAPI/Starlette test-client deprecation warning does not need immediate dependency pinning.

### Tests Executed

- `.venv/bin/python -m pytest` - passed with 1 test and 1 upstream deprecation warning from FastAPI/Starlette test client imports.

### Assumptions

- The previous initial setup files should be preserved because they already match the requested architecture and behavior.
- The repository owner's display name remains safely determined from `git config user.name` as `Ivy Lee`.
- No workflow generation, validation, explanation, simulation, or LLM integration should be implemented in this verification pass.

## 2026-07-15 - Public Model Exports

### Task

Fix `from app.models import AutomationFlow` and related public workflow model imports, then prove the direct import and lead-routing example validation work.

### Codex Contribution

- Inspected the current model package, tests, examples, git status, and agent rules.
- Found that `app/models/__init__.py` had no public exports and the requested workflow model source files were not present in the worktree.
- Added workflow and validation model source files with the requested public symbols.
- Exported the public models and enums from `app.models` with an explicit `__all__`.
- Added a lead-routing example workflow fixture.
- Added unit and integration-style tests for public imports and `AutomationFlow.model_validate(...)`.

### Manual Review Checklist

- [ ] Confirm the newly added workflow model field names match the intended schema.
- [ ] Confirm the lead-routing example reflects the repository owner's preferred sample workflow.
- [ ] Decide whether stricter graph-level validation belongs in a future service layer rather than these Pydantic models.
- [ ] Confirm the upstream FastAPI/Starlette test-client deprecation warning does not need immediate dependency pinning.

### Tests Executed

- `.venv/bin/python -m pytest` - passed with 3 tests and 1 upstream deprecation warning from FastAPI/Starlette test client imports.

### Assumptions

- Because the workflow model files were absent, adding the smallest source files for the requested public symbols was necessary to make the exports work.
- The public import surface should live in `app/models/__init__.py`; model behavior should remain limited to Pydantic schema validation.
- No health endpoint, workflow execution, simulation, LLM integration, or external API behavior should be changed.

## 2026-07-15 - Public Domain Schema Correction

### Task

Refactor the workflow domain models and lead-routing example to match the agreed FlowPilot public contract before implementing services.

### Initial Schema Mismatch

- `AutomationFlow` used `start_node_id` instead of `trigger_node_id`.
- `name`, `description`, and `version` were incorrectly nested inside `FlowMetadata`.
- `FlowNode` did not include a human-readable `name`.
- Several config fields used incompatible names, including `variable`, `options`, `team`, and `reason`.
- The lead-routing example placed routing conditions directly on the `ask_question` node instead of using a separate `condition` node.

### Why This Was Corrected Before Services

The Pydantic models define FlowPilot's public domain contract. Correcting the contract now prevents API handlers, repositories, validation services, simulation code, examples, and tests from building against an incompatible shape that would need to be unwound later.

### Codex Contribution

- Inspected the current workflow model, public exports, tests, example workflow, git status, and agent rules before editing.
- Moved public flow identity fields to top-level `AutomationFlow` fields.
- Reworked `FlowMetadata` into generation/provenance metadata.
- Renamed node configuration fields to the agreed schema.
- Added model-level trigger validation for unique node IDs, exactly one trigger node, and valid `trigger_node_id`.
- Rewrote the lead-routing example with a separate condition node, fallback branch, clarification message, and terminal outcomes.
- Expanded regression tests for public fields, example parsing, fallback behavior, config names, validation failures, and serialization round-trip.

### Manual Review Checklist

- [ ] Confirm the public schema matches the intended FlowPilot write-up and demo contract.
- [ ] Review `examples/lead-routing.json` for product clarity and demo usefulness.
- [ ] Confirm the current model-level validation scope is intentionally limited to trigger and node ID checks.
- [ ] Decide whether graph validation, reachability, fallback coverage, and terminal-path checks should be implemented in a later validation service.
- [ ] Confirm the upstream FastAPI/Starlette test-client deprecation warning does not need immediate dependency pinning.

### Tests Executed

- `.venv/bin/python -m pytest` - passed with 9 tests and 1 upstream deprecation warning from FastAPI/Starlette test client imports.

### Assumptions

- The project is still early enough to remove incompatible schema fields instead of preserving backward compatibility.
- Dangling transition targets, reachability, loop, fallback, and terminal-path graph validation belong in a future validation service, not this model refactor.
- No health endpoint, API endpoint, generation service, simulation engine, or LLM integration should be changed in this task.

## 2026-07-15 - Deterministic Workflow Validation Service

### Task

Implement deterministic graph and business-rule validation for `AutomationFlow`, expose it through `POST /api/flows/validate`, and document the validation behavior.

### Codex Contribution

- Read `README.md` and `AGENTS.md` before making changes.
- Inspected the current workflow models, validation result models, example workflow, routes, service package, tests, and git status.
- Added `FlowValidationService` with stable finding codes, deterministic finding ordering, and `is_valid` semantics based on error findings.
- Added `POST /api/flows/validate` without storage, mutation, generation, simulation, explanation, or external calls.
- Exported `FlowValidationService` from `app.services`.
- Added unit tests for graph validation rules and integration tests for the validation endpoint.
- Updated the README with a concise validation section.

### Graph Algorithms Proposed

- Build an adjacency list from node transitions.
- Use iterative traversal from `trigger_node_id` to compute reachable nodes while ignoring dangling targets safely.
- Use reverse adjacency from end nodes to compute which nodes have at least one terminal path.
- Use DFS over the reachable subgraph to detect cycles, then canonicalize each cycle to avoid duplicate findings.
- Detect duplicate transitions per node using `(target_node_id, condition, is_fallback)` keys.

### Assumptions Made

- API-call transition classification is conservative and text-based, using labels and conditions for common success and failure indicators.
- Fallback transitions from API-call nodes count as failure paths.
- Cycles are warnings because retry and clarification loops can be intentional.
- Dangling transition targets should not crash traversal or cycle detection.
- Graph libraries are unnecessary for this project scope.

### Manual Review Checklist

- [ ] Confirm the validation finding messages are clear enough for the hackathon demo.
- [ ] Confirm the API success/failure path heuristics match the intended workflow authoring language.
- [ ] Review whether cycle warnings should include more or less path detail.
- [ ] Decide whether additional graph checks should be added later in a dedicated validation iteration.
- [ ] Confirm the upstream FastAPI/Starlette test-client deprecation warning does not need immediate dependency pinning.

### Tests Executed

- `.venv/bin/python -m pytest` - passed with 31 tests and 1 upstream deprecation warning from FastAPI/Starlette test client imports.

## 2026-07-15 - Mock Workflow Simulation Engine

### Task

Implement deterministic mock execution for `AutomationFlow` using supplied user inputs and mock API outcomes, expose it through `POST /api/flows/simulate`, add runnable examples, and document the behavior.

### Codex Contribution

- Read `README.md` and `AGENTS.md` before making changes.
- Inspected the current workflow models, validation models, public exports, validation service, flows route, lead-routing example, and tests.
- Added typed simulation models for status, transcript entries, trace entries, mock API outcomes, requests, and results.
- Added `FlowSimulationService` with pre-execution validation, bounded node-by-node execution, deterministic transition selection, transcript recording, and trace recording.
- Added the `POST /api/flows/simulate` endpoint without persistence or external calls.
- Added buyer, seller, and unexpected-answer simulation request examples.
- Added comprehensive unit tests and FastAPI integration tests.
- Updated public model and service exports.
- Updated README documentation for mock simulation behavior.

### Execution Model Proposed

- Run `FlowValidationService` directly before simulation and stop before execution if error findings exist.
- Start at `flow.trigger_node_id`.
- Execute one node per step, append trace entries, and stop on completion, waiting for input, failure, or step-limit exhaustion.
- Store runtime variables in a local copy seeded from `initial_variables`.
- Record bot/user transcript entries for message and question nodes.
- Store mock API results under `variables["api_results"][node_id]`.
- Use the first deterministic normal transition for non-branching nodes.

### Unsafe Approaches Explicitly Rejected

- No `eval` or `exec`.
- No real HTTP or external API calls.
- No general expression engine.
- No persistence or repository writes.
- No LLM generation, explanation generation, or natural-language generation.
- No frontend code.

### Assumptions

- User inputs are keyed by ask-question node ID and reused on each visit in this MVP.
- Reused unexpected answers may intentionally hit the maximum step limit in fallback loops.
- API success and failure branch selection is conservative and based on labels, simple conditions, and fallback flags.
- Missing user input is a waiting state, not a failure.
- Warnings and info findings from validation do not block simulation.

### Manual Review Checklist

- [ ] Confirm transcript and trace detail fields are useful for the demo.
- [ ] Confirm repeated user input reuse is acceptable for the MVP.
- [ ] Review API branch label heuristics for expected authoring language.
- [ ] Confirm example simulation request files are clear enough for Swagger/API demos.
- [ ] Confirm the upstream FastAPI/Starlette test-client deprecation warning does not need immediate dependency pinning.

### Tests Executed

- `.venv/bin/python -m pytest` - passed with 66 tests and 1 upstream deprecation warning from FastAPI/Starlette test client imports.

## 2026-07-15 - Plain-English Workflow Explanation Service

### Task

Implement deterministic, human-readable explanation for existing `AutomationFlow` artifacts and validation findings, expose it through `POST /api/flows/explain`, and generate an example explanation output.

### Codex Contribution

- Read `README.md` and `AGENTS.md` before making changes.
- Inspected workflow, validation, simulation, routing, examples, tests, and current git status.
- Added typed explanation models for step explanations, risk explanations, and full flow explanations.
- Added `FlowExplanationService` with validation-risk mapping, reachable-node BFS ordering, node-specific explanation text, outcome collection, contextual MVP notes, and API URL query-value redaction.
- Added the `POST /api/flows/explain` endpoint without persistence, LLM calls, external calls, or changes to health, validation, or simulation behavior.
- Generated `examples/explanations/lead-routing-explanation.json` from the actual service output.
- Added unit and integration tests for explanation behavior, redaction, risks, notes, ordering, and non-mutation.
- Updated README documentation for plain-English explanation.

### Explanation Structure Proposed

- A concise flow summary.
- A trigger description derived from `TriggerConfig.event`.
- Reachable step explanations in deterministic breadth-first order.
- Reachable end outcomes only.
- Assumptions copied from flow metadata.
- Validation findings mapped into risk explanations.
- Contextual notes only when relevant node types or cycles are present.

### Redaction and Safety Decisions

- No LLM or external NLP dependency is used.
- No real HTTP requests are made.
- API URL query parameter values are replaced with `<redacted>` while retaining parameter names.
- Dangling transition targets are described as missing nodes instead of crashing explanation.
- Validation warning and info findings are preserved in risks.

### Assumptions

- Summary wording should be deterministic and accurate rather than literary.
- Branch descriptions should reflect transition labels, conditions, and fallback flags without inventing hidden business semantics.
- `ValidationFinding` does not currently expose a `suggestion` field, so risk recommendations are `null` unless that field is added later.
- Only reachable nodes belong in normal step and outcome explanations; unreachable-node findings remain visible as risks.

### Manual Review Checklist

- [ ] Confirm summary wording is clear enough for the hackathon demo.
- [ ] Review branch wording for condition and fallback transitions.
- [ ] Confirm API URL redaction behavior is appropriate for future API-call examples.
- [ ] Decide whether validation findings should grow an explicit recommendation/suggestion field.
- [ ] Confirm the generated example explanation is useful for README or demo material.
- [ ] Confirm the upstream FastAPI/Starlette test-client deprecation warning does not need immediate dependency pinning.

### Tests Executed

- `.venv/bin/python -m pytest` - passed with 93 tests and 1 upstream deprecation warning from FastAPI/Starlette test client imports.

## 2026-07-15 - Natural-Language Workflow Generation

### Task

Implement focused natural-language workflow generation for the hackathon demo, with deterministic mock templates, structured failures, validation, and optional explanation.

### Codex Contribution

- Read `README.md` and `AGENTS.md` before making changes.
- Inspected the current models, routes, services, configuration, examples, tests, and git status.
- Added typed generation request and response models.
- Added `FlowGenerationService` with deterministic prompt classification, mock template factories, validation, optional explanation, and structured failure responses.
- Added `POST /api/flows/generate`.
- Added environment placeholders for optional OpenAI-compatible LLM configuration.
- Added request and response examples generated from the real service.
- Added unit and integration tests for mock generation, clarification, validation boundaries, explanation inclusion, LLM disabled behavior, uniqueness, and API behavior.
- Updated public exports and README documentation.

### Template-Generation Design

- Keyword-based classifier selects one of three fresh template factories: lead routing, support triage, or order status.
- Each generated flow receives a unique ID and fresh timezone-aware `created_at`.
- Template metadata includes `source_prompt`, `generator="mock"`, and assumptions documenting the template interpretation.
- Templates are built as fresh dictionaries and parsed through `AutomationFlow.model_validate`.

### Optional Provider Design

- `llm` mode is configuration-gated by `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.
- This hackathon build returns `LLM_NOT_CONFIGURED` for LLM mode rather than adding provider complexity or network behavior.
- No API key is logged or returned in responses.

### Validation Boundary

- Raw generated dictionaries are never returned as executable flows.
- Every generated template is parsed as `AutomationFlow`.
- Every parsed flow is passed through `FlowValidationService`.
- Validation errors return `GENERATED_FLOW_INVALID`; warnings and info return `generated_with_warnings`.
- Explanation is generated only after parsing and validation, and can be disabled per request.

### Unsafe Approaches Rejected

- No database, background jobs, agent framework, RAG, embeddings, or prompt history.
- No mock-mode network access or API keys.
- No automatic execution of generated flows.
- No weakening of existing validation, simulation, explanation, or health behavior.
- No hard-coded secrets.

### Manual Review Checklist

- [ ] Confirm keyword classification is intuitive enough for demo prompts.
- [ ] Review generated support triage and order status flows for product/demo wording.
- [ ] Decide whether a real LLM adapter should be added later and which HTTP dependency to use.
- [ ] Confirm response examples are acceptable despite unique IDs and timestamps.
- [ ] Confirm the upstream FastAPI/Starlette test-client deprecation warning does not need immediate dependency pinning.

### Tests Executed

- `.venv/bin/python -m pytest` - passed with 117 tests and 1 upstream deprecation warning from FastAPI/Starlette test client imports.

## 2026-07-15 - Frontend Demo

### Task

Create a polished minimal React, TypeScript, Vite, and Tailwind CSS frontend demo for FlowPilot's prompt-to-generate-to-validate-to-explain-to-simulate flow.

### Codex Contribution

- Read `README.md` and `AGENTS.md` before making changes.
- Inspected the repository structure, backend models, generation/simulation APIs, and existing examples.
- Created a standalone `frontend/` Vite app.
- Added typed frontend interfaces matching the backend response shapes.
- Added fetch wrappers for workflow generation and simulation.
- Built focused UI components for the header, prompt panel, workflow summary, validation findings, explanation timeline, JSON viewer, and simulation panel.
- Added narrow local-development CORS support for the Vite frontend origins.
- Added frontend setup instructions to `README.md`.

### Design Decisions

- Used a single-page app with local React state rather than routing or a state-management framework.
- Used a restrained developer-tool visual style with white panels, slate borders, compact metrics, severity badges, and a monospaced JSON viewer.
- Kept the layout desktop/laptop oriented, with a main workflow column and a sticky-feeling JSON side column through page structure rather than complex behavior.
- Kept simulation inputs derived from detected `ask_question` nodes so the demo stays tied to generated workflow structure.

### Manual Review Checklist

- [ ] Run the backend locally and verify generation and simulation from the browser.
- [ ] Review visual polish in Chrome/Safari at laptop and desktop widths.
- [ ] Confirm API error messages are friendly enough for demo use.
- [ ] Confirm local-development CORS origins are sufficient for the demo environment.
- [ ] Review whether example prompts should be adjusted for the live demo narrative.

### Tests Performed

- `npm install --strict-ssl=false` - passed after local npm registry certificate issues blocked the normal install.
- `npm install --strict-ssl=false --save-dev @types/react @types/react-dom` - passed.
- `npm run build` - passed.
- `.venv/bin/python -m pytest` - passed with 117 tests and 1 upstream deprecation warning from FastAPI/Starlette test client imports.
- Final `npm run build` - passed.

## 2026-07-15 - Frontend Product UI Refactor

### Task

Refactor the functional frontend from an internal-dashboard feel into a polished AI product demo interface while keeping the backend API unchanged.

### Codex Contribution

- Read `README.md` and `AGENTS.md` before making changes.
- Inspected the existing React, TypeScript, Vite, and Tailwind frontend.
- Reworked the app shell into a responsive `max-w-7xl mx-auto w-full` layout with a desktop two-column workspace and single-column smaller-screen layout.
- Added a visual workflow timeline component without React Flow.
- Refined prompt, overview, validation, explanation, simulation, and JSON sections with softer cards, clearer hierarchy, polished empty/loading/result states, and secondary raw JSON treatment.

### Design Decisions

- Kept the demo as a single-page product workflow: prompt builder, workflow overview, validation and explanation, simulation, then raw JSON.
- Used rounded panels, subtle shadows, restrained slate neutrals, severity colors, and compact badges to align with modern developer-tool UI.
- Kept animations minimal and limited to existing loading spinners.
- Avoided new state-management, routing, visualization, or authentication dependencies.

### Manual Review Checklist

- [ ] Verify the UI visually at 1280px, 1024px, 768px, and a mobile-width viewport.
- [ ] Run the backend locally and confirm generate and simulate flows work end to end from the browser.
- [ ] Confirm the timeline descriptions are clear enough for demo narration.
- [ ] Confirm raw JSON being collapsed by default fits the intended demo flow.

### Tests Performed

- `npm run build` - passed.

## Final Review Preparation

### Documentation Review

- Reworked `README.md` for public GitHub presentation with sections for overview, demo, features, architecture, lifecycle, agentic development, quality and safety, testing, trade-offs, future improvements, and local setup.
- Added `docs/write-up.md` as a concise engineering write-up for judges or reviewers.
- Added `docs/demo-script.md` for a 3-5 minute hackathon-style presentation.
- Added `docs/architecture.md` with frontend/backend/service responsibilities and a Mermaid diagram.
- Added `docs/final-checklist.md` for final manual submission readiness.
- Added `docs/images/` placeholder directory for future demo screenshots.

### Demo Preparation

- Confirmed the documented API endpoints match the implemented FastAPI routes.
- Clarified that generation, validation, explanation, and simulation are implemented.
- Clarified that persistence, real integrations, authentication, analytics, and a visual graph editor are future work.
- Kept raw JSON and examples documented as demo artifacts rather than production workflow storage.

### Known Limitations

- Mock generation supports only the intended demo scenarios.
- LLM mode is configuration-gated and not the primary runnable path.
- Simulation uses supplied mock API outcomes and never calls external services.
- Workflow state is not persisted in a backend database.
- The frontend is a polished demo surface, not a full workflow editor.

### Verification Executed

- `pytest` - attempted, but the command was not available on the shell PATH.
- `.venv/bin/python -m pytest` - passed with 117 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `npm install` - passed, dependencies already up to date.
- `npm run build` - passed.

### Manual Review Checklist

- [ ] Repository owner reviews README claims against the final demo narrative.
- [ ] Repository owner adds or replaces screenshot placeholders under `docs/images/`.
- [ ] Repository owner runs the demo locally from a clean checkout.
- [ ] Repository owner confirms final checklist items before public submission.

## 2026-07-15 - DeepSeek LLM Generation Provider

### Task

Add an optional real LLM generation provider using DeepSeek's OpenAI-compatible API while preserving deterministic mock generation as the default stable path.

### Codex Contribution

- Read `README.md` and `AGENTS.md` before making changes.
- Inspected generation service, API route, frontend generation UI, configuration, and tests.
- Introduced a lightweight provider interface with mock and DeepSeek providers.
- Moved deterministic templates into `MockWorkflowGenerationProvider`.
- Added `DeepSeekProvider` with JSON-only prompt constraints, timeout handling, masked provider errors, and no API-key exposure.
- Updated `FlowGenerationService` to select mock for `mode=mock` and configured provider for `mode=llm`.
- Added frontend mode selection for Mock Generation and DeepSeek Generation.
- Added unit and integration tests using mocked provider behavior only.

### Provider Abstraction Rationale

- Provider selection isolates raw workflow generation from parsing, validation, explanation, and response semantics.
- Mock remains default because it is deterministic, offline, and reliable for demos and tests.
- DeepSeek is optional for production-oriented integration proof without adding frameworks, RAG, vector databases, or prompt-management systems.

### Safety Boundary

- Provider output is raw JSON-like data only.
- LLM JSON is parsed and validated with `AutomationFlow.model_validate`.
- Validation runs before explanation and before any simulation can happen.
- API keys are read from environment configuration and are never returned in structured errors.

### Manual Review Checklist

- [ ] Configure DeepSeek locally and run one real LLM generation request.
- [ ] Confirm the returned workflow matches the intended public schema.
- [ ] Confirm validation and explanation are present in the LLM response.
- [ ] Confirm API-key handling is acceptable for the demo environment.

### Tests Executed

- `.venv/bin/python -m pytest tests/unit/test_generation_service.py tests/integration/test_generate_flow_api.py` - passed with 31 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `.venv/bin/python -m pytest` - passed with 124 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `npm run build` - passed.

## 2026-07-15 - LLM Provider Configuration Fix

### Task

Fix LLM provider selection so `mode=llm` uses the configured DeepSeek provider and never silently falls back to mock generation.

### Codex Contribution

- Inspected actual configuration, route, generation model, provider, and service wiring.
- Confirmed the project uses a module-level `Settings` instance plus direct `os.getenv` calls, not `get_settings`, pydantic-settings, dependency injection, or automatic dotenv loading.
- Added a small repository-root `.env` loader in `app.core.config`.
- Updated provider selection so `mode=mock` uses mock, while `mode=llm` requires `LLM_PROVIDER=deepseek` or returns `LLM_NOT_CONFIGURED`.
- Added safe INFO logs for requested mode, selected provider, and model.
- Added `scripts/check_llm_config.py` for redacted configuration diagnostics.
- Added regression tests for mock selection, DeepSeek selection, missing keys, no silent fallback, provider reporting, and diagnostic redaction.

### Root Cause

The previous code read `LLM_PROVIDER` only from process environment or the default `settings.llm_provider`. The repository-root `.env` file was not loaded, so local DeepSeek configuration was invisible unless manually exported. When `mode=llm` saw the default provider value `mock`, the generation service returned the mock provider, which produced `clarification_required` for unsupported prompts.

### Safety Decisions

- The diagnostic script prints only whether the DeepSeek API key is configured.
- Logs do not include API keys, prompts, or provider response bodies.
- Tests mock all DeepSeek network behavior.

### Tests Executed

- `.venv/bin/python -m pytest tests/unit/test_generation_service.py tests/integration/test_generate_flow_api.py` - passed with 35 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `pytest` - attempted, but the executable is not available on PATH in this shell.
- `.venv/bin/python -m pytest` - passed with 128 tests and 1 upstream FastAPI/Starlette deprecation warning.

## 2026-07-15 - DeepSeek Provider Request/Parsing Fix

### Task

Fix the DeepSeek provider implementation after direct DeepSeek API calls succeeded but FlowPilot still returned `LLM_PROVIDER_ERROR`.

### Codex Contribution

- Inspected the actual DeepSeek provider implementation before editing.
- Compared the request payload against the known-good DeepSeek request shape.
- Added `max_tokens` and `stream=false` to the provider payload.
- Kept the final endpoint normalized as `base_url.rstrip("/") + "/chat/completions"`.
- Expanded the system prompt with JSON-only instructions, schema details, no unsupported fields, and a compact valid `AutomationFlow` example.
- Added defensive response parsing for missing choices, message, content, empty content, invalid JSON, and invalid schema.
- Added specific provider error mappings for timeout, connection failure, HTTP failure, invalid LLM output, invalid generated flow, and unexpected provider errors.
- Added safe provider diagnostics and local-development logs without API keys, authorization headers, full prompts, or generated workflow content.
- Added `scripts/check_deepseek_connection.py` to exercise the same provider code path as the application.

### Previous Parsing Path

- Read the raw urllib response body.
- `json.loads(response_body)`.
- Read `provider_response["choices"][0]["message"]["content"]`.
- `json.loads(content)`.
- Collapsed many provider failures into generic `LLM_PROVIDER_ERROR`.

### Corrected Parsing Path

- Read and log sanitized HTTP status and response content length.
- Parse the DeepSeek HTTP envelope.
- Defensively extract `choices[0].message.content`.
- Parse `content` as workflow JSON.
- Validate the parsed workflow JSON as `AutomationFlow`.
- Return structured provider errors by failure type.

### Tests Executed

- `.venv/bin/python -m pytest tests/unit/test_generation_service.py tests/integration/test_generate_flow_api.py` - passed with 44 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `pytest` - attempted, but the executable is not available on PATH in this shell.
- `.venv/bin/python -m pytest` - passed with 138 tests and 1 upstream FastAPI/Starlette deprecation warning.

## 2026-07-15 - DeepSeek HTTP Client Alignment

### Task

Align `DeepSeekProvider` with the verified working `httpx.Client(timeout=30.0, trust_env=True)` request path.

### Codex Contribution

- Inspected the existing provider before editing and confirmed it used stdlib `urllib.request.urlopen`, not `httpx`.
- Replaced the urllib request path with `httpx.Client(timeout=httpx.Timeout(configured_timeout), trust_env=True)`.
- Moved `httpx` into runtime dependencies because the DeepSeek provider imports it in application code.
- Kept the endpoint as `base_url.rstrip("/") + "/chat/completions"`.
- Preserved request headers and JSON payload shape.
- Added safe diagnostics for proxy environment presence, timeout, trust_env, exception class, and sanitized exception message.
- Added specific handling for `httpx.ProxyError`, `ConnectTimeout`, `ConnectError`, `ReadTimeout`, `HTTPStatusError`, JSON decoding, and Pydantic validation.
- Updated tests to mock the httpx client path and assert `trust_env=True`.

### Root Cause

The standalone verified request used `httpx.Client(..., trust_env=True)`, while the application provider used urllib. That meant proxy/environment/TLS behavior could differ from the proven working path and connection failures were being mapped through urllib-style exceptions.

### Tests Executed

- `.venv/bin/python -m pytest tests/unit/test_generation_service.py tests/integration/test_generate_flow_api.py` - passed with 46 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `pytest` - attempted, but the executable is not available on PATH in this shell.
- `.venv/bin/python -m pytest` - passed with 139 tests and 1 upstream FastAPI/Starlette deprecation warning.

## 2026-07-16 - DeepSeek JSON-Only Prompt Hardening

### Task

Improve DeepSeek workflow-generation prompt adherence and defensive output handling after the model returned natural-language text instead of an `AutomationFlow` JSON object.

### Codex Contribution

- Strengthened the system prompt with explicit JSON-only rules.
- Added required top-level `AutomationFlow` fields and supported node types.
- Added a compact valid JSON example.
- Added the instruction that any text outside the JSON object causes validation failure.
- Added conservative output cleanup that strips whitespace and accidental markdown fences.
- Kept invalid natural-language output rejected as `INVALID_LLM_OUTPUT`.
- Added regression tests for plain text rejection, fenced JSON cleanup, and valid JSON parsing.

### Tests Executed

- `.venv/bin/python -m pytest tests/unit/test_generation_service.py tests/integration/test_generate_flow_api.py` - passed with 49 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `pytest` - attempted, but the executable is not available on PATH in this shell.
- `.venv/bin/python -m pytest` - passed with 142 tests and 1 upstream FastAPI/Starlette deprecation warning.

## 2026-07-16 - DeepSeek AutomationFlow Schema Prompt Fix

### Task

Fix DeepSeek generation prompt and validation handling after the model returned a wrapped schema such as `{"automationFlow": {"steps": [...]}}` instead of the internal `AutomationFlow` schema.

### Codex Contribution

- Tightened the system prompt to explicitly forbid `automationFlow`, `workflow`, and `steps` wrappers.
- Added the exact required top-level `AutomationFlow` fields.
- Added exact node and transition shapes.
- Included a complete small example containing trigger, ask-question, condition, and end nodes.
- Added the instruction that output is validated directly by `AutomationFlow.model_validate()`.
- Added tests proving wrapped output fails, valid `AutomationFlow` JSON passes, and missing `nodes` fails.
- Did not add conversion logic, alternate workflow models, or wrapper unwrapping.

### Tests Executed

- `.venv/bin/python -m pytest tests/unit/test_generation_service.py tests/integration/test_generate_flow_api.py` - passed with 52 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `pytest` - attempted, but the executable is not available on PATH in this shell.
- `.venv/bin/python -m pytest` - passed with 145 tests and 1 upstream FastAPI/Starlette deprecation warning.
- Browser responsive smoke check at 1280px, 1024px, 768px, and 390px - passed with expected column behavior and no horizontal overflow.

## 2026-07-16 - LLM Generation Failure UI and Prompt Alignment

### Task

Trace why the frontend displayed `Generate a workflow to inspect the JSON artifact.` during failed DeepSeek generation and tighten the LLM path around the internal `AutomationFlow` schema.

### Codex Contribution

- Traced the message to the frontend raw JSON viewer empty-state placeholder, not the DeepSeek provider response.
- Added an explicit failed-generation state that shows status, provider, error code, and available failure reasons.
- Replaced the misleading JSON viewer placeholder with neutral empty/failure text.
- Aligned the DeepSeek system prompt with the current backend `NodeType` enum, including `wait`.
- Kept invalid wrapped or natural-language LLM output rejected instead of converting it into another schema.
- Added a prompt regression test to prevent future schema drift.

### Manual Review Checklist

- [ ] Verify the frontend failed-generation state with a real invalid DeepSeek response.
- [ ] Confirm the DeepSeek prompt performs acceptably with the configured production model.
- [ ] Review whether provider validation errors should expose more detailed Pydantic field paths in future work.

### Tests Executed

- `.venv/bin/python -m pytest tests/unit/test_generation_service.py tests/integration/test_generate_flow_api.py` - passed with 53 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `.venv/bin/python -m pytest` - passed with 146 tests and 1 upstream FastAPI/Starlette deprecation warning.
- `npm run build` from `frontend/` - passed.

## 2026-07-15 - Misty-Blue Frontend Visual Refactor

### Task

Refactor the FlowPilot frontend visual design into a calm professional misty-blue AI developer-tool theme without changing backend API usage, data models, business logic, or component responsibilities.

### Codex Contribution

- Updated the frontend color system around `#F3F6FA`, `#6B8EAE`, `#3F5F7A`, `#E8F0F7`, and `#8AA6B8`.
- Replaced the previous generic slate/black/white-heavy styling with misty-blue surfaces, primary actions, muted text, and softer status colors.
- Made workflow timeline nodes more visually prominent with blue cards, blue node markers, and connecting lines.
- Kept the responsive two-column desktop and single-column tablet/mobile layout intact.
- Kept raw JSON collapsed and visually secondary.

### Design Decisions

- Avoided pure black and broad pure-white card usage in favor of blue-tinted surfaces and dark blue text.
- Preserved existing component boundaries and frontend data flow.
- Kept visual changes CSS/Tailwind-only with no new dependencies.

### Manual Review Checklist

- [ ] Review the misty-blue palette in the browser against the intended Linear/Notion/developer-tool feel.
- [ ] Confirm contrast is comfortable for demo projection.
- [ ] Verify generated workflow, validation, explanation, simulation, and JSON states still feel visually balanced.

### Tests Performed

- `npm run build` - passed.
