## Context

The coding agent reads three GitHub secrets at startup via `os.environ` in `agent/coding/config.py`: `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, and `GITHUB_WEBHOOK_SECRET`. Environment variables are convenient for local development but are a weak secret delivery mechanism in containerized production deployments — they appear in `/proc/<pid>/environ`, are inherited by every subprocess, and often surface in container inspection output.

Docker secrets mount files at `/run/secrets/<name>` inside the container with 0400 permissions, readable only by root (or the designated secret consumer). This is the idiomatic Docker Swarm / Compose v3 pattern for injecting sensitive values.

## Goals / Non-Goals

**Goals:**
- Read each GitHub secret from `/run/secrets/<name>` when running in Docker, with transparent fallback to `os.environ` for local development.
- Centralize the fallback logic in a single helper so it's consistent and easy to audit.
- Preserve startup fail-fast behavior with clear error messages naming both sources.

**Non-Goals:**
- Supporting secret backends other than Docker secrets (Vault, AWS Secrets Manager, etc.).
- Rotating secrets at runtime (secrets are read once at startup).
- Changing how secrets are consumed downstream in `github.py` or `app.py`.

## Decisions

### 1. File-first, env-var fallback (not env-var-first)

**Decision:** Try reading `/run/secrets/<name>` first; only fall back to `os.environ[name]` if the file does not exist.

**Rationale:** Makes Docker deployments strictly better without requiring env vars to be unset. Local dev (no mounted secrets) continues to work unchanged. If we reversed the order, a stale env var would silently shadow a mounted secret, which defeats the purpose.

**Alternative considered:** Require operators to unset env vars when using Docker secrets. Rejected — adds deployment friction and breaks existing CI pipelines.

### 2. Single `load_secret(name)` helper in `config.py`

**Decision:** Add a module-level helper function in `config.py` rather than a separate module.

**Rationale:** There are only three call sites, all in the same file. A separate `secrets.py` module would be over-engineering for this scope. If the project adds more secrets later, it can be extracted then.

**Alternative considered:** Inline the file-read logic at each call site. Rejected — three copies of the same try/except/strip pattern is error-prone and harder to audit.

### 3. Strip whitespace from file contents

**Decision:** Call `.strip()` on the value read from the secret file.

**Rationale:** Secret files often have a trailing newline added by the tooling that creates them. Stripping is safe for all three secrets (IDs are numeric, keys are PEM blocks that don't end in significant whitespace, webhook secrets are hex strings).

### 4. Keep the `replace("\\n", "\n")` normalization for `GITHUB_APP_PRIVATE_KEY`

**Decision:** Apply the existing `\\n` → `\n` normalization after loading the key, regardless of source.

**Rationale:** When the key is delivered via env var in some CI systems (e.g., GitHub Actions secrets), literal `\n` sequences replace real newlines. Docker secret files will contain real newlines, so the replace is a no-op for them — but keeping it unified avoids a conditional branch and handles mixed deployment scenarios.

## Risks / Trade-offs

- **File permission misconfiguration** → The secret file exists but is not readable by the container user. Mitigation: the `open()` call will raise `PermissionError` at startup, failing loudly rather than silently falling through to a missing env var.
- **Secret file present but empty** → `load_secret` returns `""`, which fails the existing non-empty checks already in `config.py`. No new risk introduced.
- **Local dev silently using stale env vars** → This is existing behavior; the change doesn't make it worse.

## Migration Plan

1. Deploy the updated `config.py` image (Docker secret file absent → falls back to env vars, zero behavior change for existing deployments).
2. Add Docker secrets to the Swarm service or Compose file with names matching the three secret names.
3. Redeploy — the container now reads from `/run/secrets/` files.
4. Optionally remove the env var entries from the deployment config.

**Rollback:** Roll back to the previous image; env vars were never removed in step 3, so the service restores cleanly.
