## Why

The coding agent currently reads `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, and `GITHUB_WEBHOOK_SECRET` from environment variables, which is a weak secret management pattern — env vars are visible in process listings, inherited by child processes, and commonly leaked in logs. Docker secrets mount files at `/run/secrets/<name>` inside the container, providing a safer delivery mechanism with tighter access controls.

## What Changes

- `config.py` will read each GitHub secret from its mounted Docker secret file first, falling back to the environment variable for local development compatibility.
- A helper function will encapsulate the file-read logic (try `/run/secrets/<name>`, fall back to `os.environ`).
- Startup validation error messages will reference both sources so operators know what to configure.

## Capabilities

### New Capabilities

- `docker-secret-loader`: A utility that reads a named value from a Docker secret file (`/run/secrets/<name>`) with fallback to an environment variable, used at startup by `config.py`.

### Modified Capabilities

- `github-app-token-provider`: The token provider's configuration source changes — `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` are now loaded via the secret loader rather than directly from `os.environ`. The behavioral requirements (JWT generation, token exchange, caching) are unchanged, but the requirement describing how credentials are sourced needs updating.

## Impact

- `agent/coding/config.py`: primary change — replace direct `os.environ` calls with secret loader calls for the three GitHub secrets.
- No changes to `github.py`, `app.py`, or any other module; they consume values already resolved by `config.py`.
- Deployments using Docker secrets must mount the secrets with names `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, and `GITHUB_WEBHOOK_SECRET` (or keep using env vars for local dev).
