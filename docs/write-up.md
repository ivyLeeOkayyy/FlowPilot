# FlowPilot Engineering Write-Up

## Problem and MVP Scope

Automation builders often require users to translate business intent into nodes, branches, conditions, API calls, and terminal outcomes. That translation is easy to get wrong: workflows can miss fallback branches, reference missing nodes, loop forever, or fail to reach a terminal state.

FlowPilot focuses on a small MVP: turn plain-English automation ideas into structured workflow artifacts, validate them deterministically, explain them in readable language, and run safe mock simulations. The scope intentionally excludes production integrations, persistence, authentication, a full graph editor, and real external API calls.

## Architecture and Key Design Decisions

The core workflow data model is a typed `AutomationFlow` made of `FlowNode` objects, typed node configuration models, and explicit transitions. Pydantic v2 provides schema validation and rejects incompatible node/config pairs.

The backend is separated into focused services:

- generation creates a fresh workflow artifact from supported prompt templates;
- validation checks graph and business rules;
- explanation turns validated structure and findings into plain-English output;
- simulation runs deterministic mock execution.

Validation happens before simulation. This keeps unsafe or broken generated flows from being treated as executable. The frontend is separate from the FastAPI backend and demonstrates the product flow without adding workflow editing or complex state management.

## Agent Usage

Codex helped with architecture exploration, implementation scaffolding, test design, debugging, and documentation preparation. Examples include comparing schema options before service work, generating regression tests for graph validation and simulation behavior, and tightening README wording to match implemented APIs.

Agent outputs were treated as drafts and implementation assistance, not as final authority. Safety boundaries, MVP scope, and final project review remain human responsibilities.

## Manual Review

Recommended review areas before submission:

- data model review for public schema clarity;
- execution safety review for step limits and mock API boundaries;
- validation rule review for expected hackathon examples;
- test review for coverage of model exports, examples, services, and API endpoints;
- frontend review for demo clarity and responsive behavior.

## Trade-offs and V2

FlowPilot does not include persistence, auth, real integrations, a React Flow editor, background jobs, RAG, embeddings, or agent orchestration. The generation layer is intentionally template-based for reliable demo behavior.

V2 could add persistent workflow storage, versioning, visual editing, real integration connectors, approval workflows, analytics, and broader generation/evaluation coverage.
