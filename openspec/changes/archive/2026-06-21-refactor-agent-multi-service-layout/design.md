## Context

`agent/main.py` is a 490-line file containing five distinct concerns: configuration, workspace management, GitHub API helpers, the PydanticAI coding agent with its tools, and the FastAPI webhook server. The directory currently has three files and is built as a single Docker image.

The project will add more agents (e.g. an email summarizer) that have different trigger mechanisms and runtime models. Each new agent should be self-contained so it can be deployed, scaled, and iterated on independently.

## Goals / Non-Goals

**Goals:**
- Establish `agent/<name>/` as the convention for housing agents as sibling services
- Split `agent/main.py` into focused modules with single responsibilities
- Keep `compose.yaml` functional with no behavioral changes

**Non-Goals:**
- Shared library extraction (no `agent/lib/` — agents don't share enough to justify it yet)
- Any logic, behavior, or API changes
- Adding new agents (this change only restructures the existing one)

## Decisions

### 1. Separate service directories over a shared framework

Each agent lives in its own directory (`agent/coding/`, `agent/email/`, etc.) with its own `Dockerfile` and `requirements.txt`. No common entry point or plugin registry.

**Rationale:** The planned agents (GitHub coding, email summarizer) have different runtime models (webhook server vs. cron daemon), different dependencies, and different outputs. Coupling them into a single process or framework buys nothing and introduces operational risk. Separate directories are independently deployable and have clear ownership.

**Alternative considered:** A single container running multiple agents. Rejected because a failure in one agent would affect others, and dependency sets diverge over time.

### 2. Five-module split for `coding/`

```
agent/coding/
├── config.py      # env var constants
├── workspace.py   # EventContext dataclass + Workspace class
├── github.py      # gh_post_comment, gh_push_and_open_pr
├── agent.py       # PydanticAI agent, tool definitions, run_agent()
└── app.py         # FastAPI app, webhook route, dispatcher
```

**Rationale:** Each module has a single reason to change. `github.py` changes when the GitHub API integration changes. `workspace.py` changes when the git workflow changes. `agent.py` changes when the agent's capabilities or tools change. `app.py` changes when the HTTP interface or event routing changes.

**Alternative considered:** Two files (`core.py` + `app.py`). Rejected as it still mixes workspace, GitHub, and agent concerns in one file.

### 3. `app.py` owns the dispatcher

`parse_event()` and `dispatch()` live in `app.py` alongside the FastAPI routes, rather than in a separate `dispatcher.py`.

**Rationale:** The dispatcher is tightly coupled to the HTTP layer — it reads from the webhook payload and calls `background_tasks.add_task`. Separating it adds a file without adding clarity. If event routing grows complex (multiple agent types), a dedicated `dispatcher.py` can be extracted then.

## Risks / Trade-offs

- **Import path changes** → Any tooling (linters, type checkers, future tests) referencing `agent.main` will need updating. Low risk given there are no tests currently.
- **compose.yaml path change** → `build: ./agent` becomes `build: ./agent/coding`. Any CI or deployment scripts that reference the old path must be updated at the same time. Low risk — only `compose.yaml` needs changing.

## Migration Plan

1. Create `agent/coding/` directory
2. Move `Dockerfile` and `requirements.txt` into it unchanged
3. Split `main.py` into five modules, keeping all logic identical
4. Delete `agent/main.py`
5. Update `compose.yaml` build path
6. Verify `docker compose build` succeeds
