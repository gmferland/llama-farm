## 1. Create new directory structure

- [x] 1.1 Create `agent/coding/` directory
- [x] 1.2 Move `agent/Dockerfile` to `agent/coding/Dockerfile`
- [x] 1.3 Move `agent/requirements.txt` to `agent/coding/requirements.txt`

## 2. Split main.py into modules

- [x] 2.1 Create `agent/coding/config.py` with all env var constants (`GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET`, `LLM_BASE_URL`, `LLM_MODEL`, `AGENT_MAX_ITERATIONS`, `AGENT_MAX_CONCURRENCY`, `GITHUB_REPO`)
- [x] 2.2 Create `agent/coding/workspace.py` with `EventContext` dataclass and `Workspace` class (imports from `config.py`)
- [x] 2.3 Create `agent/coding/github.py` with `_gh_headers`, `gh_post_comment`, and `gh_push_and_open_pr` (imports from `config.py`)
- [x] 2.4 Create `agent/coding/agent.py` with the PydanticAI agent, all six tool functions, and `run_agent()` (imports from `config.py`, `workspace.py`, `github.py`)
- [x] 2.5 Create `agent/coding/app.py` with `parse_event`, `dispatch`, the FastAPI app, webhook route, and health endpoint (imports from `workspace.py`, `github.py`, `agent.py`, `config.py`)
- [x] 2.6 Delete `agent/main.py`

## 3. Update configuration

- [x] 3.1 Update `agent/coding/Dockerfile` `COPY` instruction to copy all `.py` files (or the directory) instead of just `main.py`, and update the `CMD` to `uvicorn app:app`
- [x] 3.2 Update `compose.yaml` build context from `./agent` to `./agent/coding`

## 4. Verify

- [x] 4.1 Run `docker compose build` and confirm it succeeds with no errors
