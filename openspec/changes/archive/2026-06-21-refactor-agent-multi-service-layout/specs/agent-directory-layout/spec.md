## ADDED Requirements

### Requirement: Each agent is a self-contained service directory
Each agent SHALL live in its own subdirectory under `agent/` (e.g. `agent/coding/`, `agent/email/`) and SHALL contain its own `Dockerfile` and `requirements.txt`. No shared runtime infrastructure or common entry point between agents is required.

#### Scenario: Adding a new agent
- **WHEN** a developer creates a new agent named `<name>`
- **THEN** they SHALL create `agent/<name>/Dockerfile` and `agent/<name>/requirements.txt` as the minimum required files

#### Scenario: Building a specific agent
- **WHEN** `docker compose build` is run
- **THEN** each agent service SHALL build from its own subdirectory context (`./agent/<name>`)

### Requirement: Coding agent modules are split by responsibility
The coding agent SHALL be organized into the following modules within `agent/coding/`:
- `config.py` — environment variable constants
- `workspace.py` — `EventContext` dataclass and `Workspace` class
- `github.py` — GitHub API helpers (`gh_post_comment`, `gh_push_and_open_pr`)
- `agent.py` — PydanticAI agent definition, tool functions, and `run_agent()`
- `app.py` — FastAPI application, webhook route, and event dispatcher

#### Scenario: Locating agent tool definitions
- **WHEN** a developer needs to add or modify an agent tool
- **THEN** all tool definitions SHALL be found in `agent/coding/agent.py`

#### Scenario: Locating GitHub API integration
- **WHEN** a developer needs to update the GitHub API interaction
- **THEN** all GitHub API calls SHALL be found in `agent/coding/github.py`
