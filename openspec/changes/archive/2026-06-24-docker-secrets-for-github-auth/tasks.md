## 1. Secret Loader Implementation

- [x] 1.1 Add `load_secret(name)` helper function in `agent/coding/config.py` that reads from `/run/secrets/<name>` first, falls back to `os.environ.get(name)`, and returns `None` if neither source provides a value
- [x] 1.2 Ensure the helper strips whitespace from file contents and raises `PermissionError` unhandled when the file exists but is unreadable

## 2. Compose Wiring

- [x] 2.0 Add top-level `secrets:` entries in `compose.yaml` pointing to `/secrets/<NAME>` and mount them into the `agent` service; remove the three GitHub secrets from the `environment` block

## 4. Config Wiring

- [x] 2.1 Replace `os.environ["GITHUB_WEBHOOK_SECRET"]` with `load_secret("GITHUB_WEBHOOK_SECRET")` and add a startup assertion that the value is non-empty
- [x] 2.2 Replace `os.environ.get("GITHUB_APP_ID")` with `load_secret("GITHUB_APP_ID")` and keep the existing non-empty check and `RuntimeError`
- [x] 2.3 Replace `os.environ.get("GITHUB_APP_PRIVATE_KEY")` with `load_secret("GITHUB_APP_PRIVATE_KEY")` and keep the existing non-empty check, `RuntimeError`, and `replace("\\n", "\n")` normalization

## 5. Verification

- [ ] 3.1 Manually verify local dev still works: run the agent with env vars set (no secret files present) and confirm startup succeeds
- [x] 3.2 Write a quick smoke test or verify with a mock that `load_secret` returns file content when `/run/secrets/<name>` exists, env var value when file is absent, and `None` when both are missing
