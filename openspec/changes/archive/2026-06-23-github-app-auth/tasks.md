## 1. Dependencies

- [x] 1.1 Add `PyJWT>=2.8` and `cryptography` to `agent/coding/requirements.txt`

## 2. Configuration

- [x] 2.1 Remove `GITHUB_TOKEN` and `GITHUB_REPO` from `agent/coding/config.py`
- [x] 2.2 Add `GITHUB_APP_ID` (int) and `GITHUB_APP_PRIVATE_KEY` (str, PEM) to `agent/coding/config.py`; fail with a clear error at startup if either is missing

## 3. Token Provider

- [x] 3.1 Add `_generate_jwt()` in `agent/coding/github.py` — signs RS256 JWT with `iat` backdated 60s and `exp` 10 minutes from now using `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY`
- [x] 3.2 Add `_token_cache: dict[int, tuple[str, datetime]]` module-level cache in `agent/coding/github.py`
- [x] 3.3 Add `async def get_installation_token(installation_id: int) -> str` in `agent/coding/github.py` — checks cache (evicts if ≤5 min remaining), fetches via `POST /app/installations/{id}/access_tokens` using the App JWT, stores result with expiry, returns token

## 4. GitHub API Helpers

- [x] 4.1 Update `_gh_headers()` in `agent/coding/github.py` to accept a `token: str` parameter instead of reading from the module-level `GITHUB_TOKEN` constant
- [x] 4.2 Update `gh_post_comment()` to accept and pass through a `token: str` parameter
- [x] 4.3 Update `gh_push_and_open_pr()` to accept and pass through a `token: str` parameter

## 5. Event Context

- [x] 5.1 Add `installation_id: int` field to `EventContext` dataclass in `agent/coding/workspace.py`
- [x] 5.2 Add `token: str` field to `Workspace` dataclass in `agent/coding/workspace.py` (populated during `init()`)

## 6. Workspace Initialization

- [x] 6.1 Update `Workspace.init()` in `agent/coding/workspace.py` to call `get_installation_token(self.event.installation_id)`, store the result on `self.token`, and use it in the git clone URL

## 7. Webhook Parser

- [x] 7.1 Update `parse_event()` in `agent/coding/app.py` to extract `payload.get("installation", {}).get("id")` for each recognized event type
- [x] 7.2 Return `None` (skip dispatch) from `parse_event()` when `installation_id` is absent for a recognized event type

## 8. Agent Wiring

- [x] 8.1 Update `run_agent()` in `agent/coding/agent.py` to pass `ws.token` to `gh_post_comment()` and `gh_push_and_open_pr()` calls

## 9. Validation

- [x] 9.1 Build the Docker image (`docker build`) and confirm it starts without errors with `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` set
- [ ] 9.2 Send a test webhook event (e.g., label an issue with `agent-task`) and confirm the agent posts a start comment and completes a run
