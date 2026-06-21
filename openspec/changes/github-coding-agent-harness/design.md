## Context

The repo currently runs a single Docker Compose service: `qwen`, a llama.cpp server exposing an OpenAI-compatible API on port 8080. The model (Qwen3.5-2B) supports tool/function calling. The goal is to add a second service—`agent`—that receives GitHub events and drives autonomous coding tasks through that model endpoint.

No prior agent infrastructure exists. The stack is minimal (just Compose + CUDA), so the design should stay lean: no message queues, no orchestration frameworks.

## Goals / Non-Goals

**Goals:**
- Accept GitHub webhook payloads and validate HMAC signatures
- Dispatch supported event types (issue comments with `/agent` trigger, PR review requests, issue labeling) to an agent
- Run an agent loop: send context + tools to the local LLM, parse tool calls, execute them, iterate until done or max steps
- Support a baseline tool set: read file, write file, run shell command, list directory, GitHub API (create branch, commit, push, open PR, post comment)
- Operate entirely within Docker Compose—no cloud dependencies

**Non-Goals:**
- Multi-tenant or multi-repo support (single configured repo per deployment)
- Long-running background agents (each run is synchronous within a webhook request timeout, or offloaded to a short-lived subprocess)
- Fine-tuning or training (separate concern)
- Supporting non-OpenAI-compatible model backends

## Decisions

### 1. Language: Python

Python is chosen over Node/Go because the llama.cpp OpenAI-compatible API is most naturally consumed via `openai` Python SDK, the GitHub API ecosystem (PyGithub / `httpx`) is mature, and the team's tooling already leans ML/Python. Alternatives considered: Node (lighter runtime but weaker ML ecosystem), Go (fast but more boilerplate for tool dispatch).

### 2. Web framework: FastAPI

FastAPI gives async request handling, automatic request validation, and minimal overhead. The webhook endpoint needs low latency for the initial 200 response; agent work is kicked off in a background task. Alternative: Flask (sync-only without workarounds).

### 3. Agent loop: PydanticAI over llama.cpp's OpenAI-compatible endpoint

llama.cpp's server exposes a `/v1/chat/completions` endpoint with `tools` support. PydanticAI is used as the agent library rather than the raw `openai` SDK. PydanticAI wraps the same OpenAI tool-calling protocol but adds automatic Pydantic validation of tool call inputs before they reach the executor — important because Qwen3.5-2B (and small models generally) frequently produce malformed tool arguments. It also integrates natively with FastAPI since both share the same type system.

Alternatives considered:
- **Raw `openai` SDK**: Full control, minimal deps, but tool input validation is manual — exactly the place small models fail most often.
- **LangChain/LangGraph**: Heavy dependency tree, opaque abstractions, frequent API churn. Overkill for a single-agent loop.
- **Pi** (pi.dev, Node.js coding agent): Designed for interactive terminal use with a human in the loop. Headless/webhook-triggered operation is not its intended use case, and it introduces a Node.js runtime into an otherwise Python stack. Set aside.

PydanticAI is configured with `base_url` pointing at the llama.cpp service (`http://qwen:8080/v1`). Swapping to a larger model later requires only changing `LLAMA_ARG_MODEL` in compose.yaml — no code changes.

### 4. Workspace isolation: ephemeral git clone per run

Each agent invocation clones the target repo into a temp directory under `/workspace`. This prevents concurrent runs from interfering and gives the agent a clean working tree. The executor commits and pushes a new branch; the original clone is discarded after the run. Alternative: shared checkout with branch switching (race conditions).

### 5. GitHub integration: GitHub App (preferred) or PAT

A GitHub App provides per-installation tokens, scoped permissions, and webhook delivery. A PAT is simpler but tied to a user account. The service accepts either; the token is injected via environment variable. Webhook secret is also injected via env var.

### 6. Trigger mechanism: `/agent` command in issue/PR comments

To avoid running on every comment, the dispatcher only activates when an issue comment or PR review comment begins with `/agent`. This is a well-understood pattern (slash commands) and avoids accidental triggers. A label-based trigger (`agent-task`) is also supported for issues.

## Risks / Trade-offs

- **Model capability**: Qwen3.5-2B is small. Complex multi-file refactors may produce poor tool calls or hallucinate file paths. Mitigation: limit max tool call iterations (default 20), validate paths before write, always show diffs in PR description.
- **Webhook timeout**: GitHub expects a 200 within 10 seconds. If the agent runs sync in the request handler it will time out. Mitigation: return 202 immediately and run the agent in a background thread/task.
- **Security—arbitrary shell execution**: The task executor can run shell commands in the workspace. A compromised GitHub webhook (or prompt injection via issue body) could execute malicious code. Mitigation: HMAC signature validation on every webhook; shell commands run in a restricted subprocess with no host network access (Docker network isolation); consider allowlisting permitted commands in a later iteration.
- **Clone latency**: Large repos are slow to clone per-run. Mitigation: use shallow clone (`--depth=1`) and only fetch the target branch.
- **Concurrent runs**: Multiple webhooks arriving simultaneously each spin up their own clone. Resource usage is unbounded. Mitigation: add a simple semaphore (configurable max concurrency, default 2).

## Migration Plan

1. Add `agent/` directory with Python service (Dockerfile, `main.py`, `requirements.txt`)
2. Add `agent` service to `compose.yaml`, linked to `qwen` network, with env vars for GitHub token + webhook secret
3. Configure GitHub App or repo webhook to point at `http://<host>:<port>/github/webhook`
4. No changes needed to existing `qwen` service

Rollback: remove the `agent` service from Compose and delete the webhook in GitHub settings. The `qwen` service is unaffected.

## Open Questions

- Should the agent post a "starting..." comment immediately on trigger so users know it's working?
- What is the right max-iterations default given Qwen3.5-2B's context window (32k tokens)?
- Should failed runs post an error comment on the issue/PR, or just log silently?
