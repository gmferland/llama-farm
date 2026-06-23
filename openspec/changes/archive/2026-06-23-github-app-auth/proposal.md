## Why

The coding agent currently authenticates to GitHub with a Personal Access Token tied to a specific user account. This limits the agent to repositories that user can access and creates a credential that expires, dies with the account, and carries broader permissions than needed. Moving to a GitHub App gives each installed repository its own scoped installation token, cleanly supports multi-repo use, and positions the agent for future distribution to other users.

## What Changes

- Replace static `GITHUB_TOKEN` PAT with GitHub App authentication (App ID + RSA private key)
- Generate short-lived JWT tokens locally to exchange for per-installation access tokens via the GitHub API
- Cache installation tokens (1-hour TTL) to avoid redundant API calls
- Extract `installation.id` from each webhook payload and thread it through `EventContext`
- Remove `GITHUB_REPO` env var (no longer needed — repo context comes from the webhook)
- Add `PyJWT` and `cryptography` dependencies for JWT signing

## Capabilities

### New Capabilities
- `github-app-token-provider`: Issues and caches short-lived installation access tokens for a given GitHub App installation, replacing the static PAT credential model.

### Modified Capabilities
- `github-webhook-listener`: Webhook payloads now carry `installation.id`; the listener must extract it and include it in the event context passed to the dispatcher.
- `coding-agent`: Credentials for cloning, pushing, and calling the GitHub API are now fetched dynamically per event rather than read from a static env var.

## Impact

- `agent/coding/config.py`: Remove `GITHUB_TOKEN`, `GITHUB_REPO`; add `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`
- `agent/coding/github.py`: Add JWT generation and installation token fetching/caching; update all API call helpers to accept a token parameter
- `agent/coding/workspace.py`: `EventContext` gains `installation_id` field; `Workspace.init()` fetches an installation token for the clone URL
- `agent/coding/app.py`: `parse_event()` extracts `installation.id` from payload
- `agent/coding/requirements.txt`: Add `PyJWT>=2.8` and `cryptography`
