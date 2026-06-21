## Why

This project already runs a self-hosted LLM (Qwen3.5-2B via llama.cpp), but that model sits idle with no way to trigger autonomous coding work. Building a coding agent harness lets GitHub events—issues, PR comments, labels—automatically dispatch tasks to the local model, turning the farm into a self-hosted alternative to cloud coding agents.

## What Changes

- Add a webhook listener service that receives GitHub events and validates signatures
- Add a coding agent loop that translates GitHub event context into tool-calling interactions with the local LLM endpoint (`http://localhost:8080`)
- Add a task executor that can clone repos, apply file edits, run shell commands, and push branches/open PRs via the GitHub API
- Add a dispatcher that maps incoming event types to agent task prompts
- Wire everything into the existing Docker Compose stack as a new service

## Capabilities

### New Capabilities

- `github-webhook-listener`: Receive and validate GitHub webhook payloads; route events to the dispatcher
- `coding-agent`: Core agent loop—send context + tool schema to the local LLM, parse tool calls, execute them, and iterate until done or a stop condition is reached
- `task-executor`: Execute coding tasks—git clone/checkout, file read/write/patch, shell command execution, GitHub API calls (create branch, commit, push, open PR, post comment)

### Modified Capabilities

<!-- none -->

## Impact

- New Docker Compose service (`agent`) alongside the existing `qwen` service
- Requires a GitHub App or Personal Access Token with repo + webhook scopes
- Network: the agent service must reach both the `qwen` service (port 8080) and the GitHub API
- Adds Python runtime dependency for the agent service
- No changes to the existing llama.cpp service configuration
