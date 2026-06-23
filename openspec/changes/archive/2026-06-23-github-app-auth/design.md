## Context

The coding agent authenticates to GitHub using a static Personal Access Token set in the `GITHUB_TOKEN` environment variable. The token is embedded in git clone URLs and passed in API call headers. It is a module-level constant read once at startup.

GitHub Apps offer a superior model: the App is registered once with Anthropic-style scoped permissions, users install it on their orgs/repos, and the agent obtains short-lived installation access tokens on demand. Each token is scoped to exactly one installation, lasting one hour.

The system currently handles webhook delivery from GitHub and dispatches agent runs per event. The webhook payload already carries `installation.id`, making installation-scoped auth straightforward.

## Goals / Non-Goals

**Goals:**
- Replace PAT with GitHub App credentials (App ID + RSA private key)
- Dynamically obtain and cache installation access tokens per event
- Thread `installation_id` through `EventContext` so all downstream code has what it needs
- Keep the existing webhook validation and dispatch logic unchanged
- Support unlimited repositories by design

**Non-Goals:**
- GitHub App registration or OAuth flow (handled externally, credentials are provided via env vars)
- Rotating or storing the RSA private key (deployer responsibility)
- Supporting multiple GitHub App IDs (one App, many installations)
- Persistent token storage across process restarts (in-memory cache is sufficient)

## Decisions

### Decision: In-memory token cache keyed by installation_id

Installation tokens last one hour. Fetching a new one on every webhook event would add ~200ms latency and burn API rate limit. A simple `dict[int, tuple[str, datetime]]` cache in `github.py` covers the common case (multiple events from the same installation within an hour).

**Alternatives considered:**
- No caching — simplest but adds latency and wastes rate limit on busy repos
- Redis/external cache — needed if running multiple replicas; overkill for a single-process deployment. Can be added later if horizontal scaling is required.

Cache invalidation strategy: check expiry on each read, evict and re-fetch if within 5 minutes of expiration (conservative buffer against clock skew and API latency).

### Decision: Pass installation token as a parameter, not a module-level variable

The old `GITHUB_TOKEN` was a module-level constant. With per-installation tokens, the token is dynamic. Rather than a global mutable, functions that need a token (`_gh_headers`, `gh_post_comment`, `gh_push_and_open_pr`) accept a `token: str` parameter. The token is resolved once per agent run (at `Workspace.init()` time) and stored on the `Workspace` object.

**Alternatives considered:**
- Thread-local / contextvars — avoids parameter threading but hides the dependency and complicates testing
- Re-fetch on every call — safe but wasteful; no benefit given the 1-hour TTL

### Decision: RSA private key via environment variable (PEM content)

Keeping credentials as env vars matches the existing pattern (`GITHUB_WEBHOOK_SECRET`, etc.) and works cleanly with Docker secrets (mount as file, read into env var at entrypoint, or pass directly). The PEM is newline-sensitive; the env var must preserve literal newlines or use `\n` escape sequences that the token provider normalizes.

**Alternatives considered:**
- File path env var pointing to mounted secret — marginally cleaner for large keys but adds deployment complexity with no security benefit in a containerized setup

### Decision: Remove GITHUB_REPO env var

`GITHUB_REPO` was a leftover constraint from the single-repo model. All repo context now comes from the webhook payload. Removing it simplifies config and makes multi-repo support implicit.

## Risks / Trade-offs

- **Private key compromise** → tokens can be minted for any installation of the App. Mitigation: treat the private key like a root credential; rotate immediately if exposed; use Docker secrets or a secrets manager rather than plain env vars in production.
- **Token cache is not shared across processes** → if the service is ever horizontally scaled, each replica maintains its own cache and makes independent token-fetch calls. Mitigation: acceptable for now; add a shared cache (Redis) before scaling beyond one replica.
- **JWT clock skew** → JWT tokens use `iat` and `exp` claims based on system clock. If the server clock drifts, GitHub may reject JWTs. Mitigation: keep system clock synced (NTP); generate JWTs with a small `iat` backdate (-60s) as a buffer.
- **Installation ID missing from payload** → some GitHub event types do not include `installation` when the App is not involved. Mitigation: `parse_event()` treats a missing `installation.id` as unrecognized and silently returns `None` (existing behavior for unrecognized events).

## Migration Plan

1. Register a GitHub App with required permissions (`contents: write`, `issues: write`, `pull_requests: write`, `metadata: read`) and note the App ID and generated private key.
2. Install the App on all target repositories.
3. Deploy the updated service with the new env vars (`GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`) and remove `GITHUB_TOKEN` and `GITHUB_REPO`.
4. Update the GitHub webhook configuration to point to the existing `/github/webhook` endpoint (no URL change needed).
5. Send a test event (e.g., add `agent-task` label to an issue) and verify the agent activates and comments.

**Rollback:** Redeploy the previous image with `GITHUB_TOKEN` and `GITHUB_REPO` env vars restored.

## Open Questions

- Should the JWT `iat` backdate be configurable, or is -60s always sufficient?
- Is there a need to support GitHub Enterprise Server (different API base URL)? If so, the API base URL should be configurable.
