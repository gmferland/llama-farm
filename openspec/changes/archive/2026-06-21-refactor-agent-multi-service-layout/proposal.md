## Why

The `agent/` directory currently holds a single monolithic service with all concerns in one file. As additional agents (e.g. an email summarizer) are planned, the directory needs a layout that treats each agent as a separate, self-contained service so they can be developed, deployed, and scaled independently.

## What Changes

- Move `agent/Dockerfile`, `agent/requirements.txt`, and `agent/main.py` into `agent/coding/`
- Split `agent/coding/main.py` into focused modules: `config.py`, `workspace.py`, `github.py`, `agent.py`, `app.py`
- Update `compose.yaml` build context from `./agent` to `./agent/coding`
- No logic changes — purely structural

## Capabilities

### New Capabilities

- `agent-directory-layout`: Convention for housing multiple agents as sibling service directories under `agent/`, each self-contained with its own `Dockerfile` and `requirements.txt`

### Modified Capabilities

- `coding-agent`: Internal module structure changes (no requirement changes)
- `github-webhook-listener`: Build path in `compose.yaml` changes from `./agent` to `./agent/coding` (no behavioral changes)
- `task-executor`: Now lives in `agent/coding/agent.py` instead of `agent/main.py` (no behavioral changes)

## Impact

- `agent/` directory structure
- `compose.yaml` service build path
- Future agents: new agents are added as `agent/<name>/` sibling directories
