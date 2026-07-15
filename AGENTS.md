# Project Rules

- Python 3.12+
- FastAPI
- Pydantic v2
- Pytest
- In-memory storage
- Structured logging
- Backend-first architecture
- Do not add a frontend unless explicitly requested
- Do not make real external API calls
- Generated workflows must be validated before simulation
- Prevent infinite loops with a maximum execution step count
- Return structured errors instead of raw exceptions
- Keep API, models, services, executors, repositories, and core utilities separated
- Add or update tests for every implementation task
- Do not silently modify unrelated files
- Record meaningful agent-assisted design, review, debugging, and testing work in docs/agent-log.md
