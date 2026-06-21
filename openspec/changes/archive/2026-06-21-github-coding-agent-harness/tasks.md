## 1. Project Setup

- [x] 1.1 Create `agent/` directory with `main.py`, `requirements.txt`, and `Dockerfile`
- [x] 1.2 Add `pydantic-ai`, `fastapi`, `uvicorn`, `httpx`, and `pygithub` to `requirements.txt`
- [x] 1.3 Write `Dockerfile` for the agent service (Python 3.11-slim base, install deps, run uvicorn)
- [x] 1.4 Add `agent` service to `compose.yaml` with env vars (`GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET`, `LLM_BASE_URL`, `AGENT_MAX_ITERATIONS`, `AGENT_MAX_CONCURRENCY`, `GITHUB_REPO`)

## 2. Webhook Listener

- [x] 2.1 Implement FastAPI app with POST `/github/webhook` endpoint that reads raw body and `X-Hub-Signature-256` header
- [x] 2.2 Implement HMAC-SHA256 signature validation using `GITHUB_WEBHOOK_SECRET`; return 401 on mismatch or missing header
- [x] 2.3 Implement event type routing: dispatch `issue_comment`, `pull_request_review_comment`, and `issues` (action=`labeled`); return 202 immediately for all others
- [x] 2.4 Return HTTP 202 before agent work starts; schedule agent invocation as a FastAPI background task
- [x] 2.5 Add GET `/health` endpoint returning `{"status": "ok"}`

## 3. Task Executor

- [x] 3.1 Implement `Workspace` class that clones the target repo (shallow `--depth=1`) into a temp dir and checks out a new branch `agent/<run-id>`
- [x] 3.2 Implement `read_file(path)` tool: resolve path relative to workspace root, reject traversal, return file contents or error string
- [x] 3.3 Implement `write_file(path, content)` tool: resolve path, reject traversal, create parent dirs, write file
- [x] 3.4 Implement `list_directory(path)` tool: return JSON array of `{name, type}` entries or error string
- [x] 3.5 Implement `run_shell(command)` tool: run command in workspace with 60-second timeout, return `{stdout, stderr, exit_code}`
- [x] 3.6 Implement `commit_changes(message)` tool: run `git add -A && git commit`, return commit SHA or "nothing to commit"
- [x] 3.7 Implement `post_comment(body)` tool: POST comment to the triggering issue or PR via GitHub API, return comment URL
- [x] 3.8 Implement workspace cleanup: delete temp directory after agent run regardless of outcome (use try/finally)
- [x] 3.9 Implement concurrency semaphore using `asyncio.Semaphore(AGENT_MAX_CONCURRENCY)`; reject runs over the limit with a "system busy" comment

## 4. Coding Agent

- [x] 4.1 Implement dispatcher: parse `issue_comment` and `pull_request_review_comment` events for `/agent <task>` trigger (case-insensitive)
- [x] 4.2 Implement dispatcher: parse `issues` event with action `labeled` and label name `agent-task`; use issue body as task description
- [x] 4.3 Implement `build_system_prompt(repo, event_context)`: include repo name, event title/body, and tool usage instructions
- [x] 4.4 Implement agent loop: send conversation + tool schema to `LLM_BASE_URL/v1/chat/completions`, parse `tool_calls`, execute via task executor, append `tool` role messages, repeat
- [x] 4.5 Post start comment ("Agent started: <task summary>") immediately after activation before the agent loop begins
- [x] 4.6 Enforce `AGENT_MAX_ITERATIONS` limit: halt loop and post "Agent reached iteration limit" comment if exceeded
- [x] 4.7 On successful loop completion with commits: push branch to GitHub and open PR with task-derived title and change summary body
- [x] 4.8 On successful loop completion with no commits: post "Agent completed but made no changes" comment; do not open PR
- [x] 4.9 On unrecoverable error: catch exception, post "Agent failed: <error summary>" comment, clean up workspace

## 5. Integration & Validation

- [x] 5.1 Verify `docker compose up` starts both `qwen` and `agent` services without errors
- [x] 5.2 Test webhook signature validation by sending a correctly-signed and an incorrectly-signed test payload to `/github/webhook`
- [ ] 5.3 Trigger the agent end-to-end with a `/agent` comment on a test issue and confirm it posts a start comment, opens a PR, or comments "no changes"
- [ ] 5.4 Set `AGENT_MAX_CONCURRENCY=2`, trigger two simultaneous agent runs, and confirm the third is rejected with a "system busy" comment
