## Why

The agent project uses a bare `requirements.txt` with `pip install`, which provides no lock file, no reproducible installs, and slow dependency resolution. Switching to `uv` gives fast, deterministic dependency management via `pyproject.toml` + `uv.lock`, while also making it trivial to run the agent locally in an isolated virtual environment.

## What Changes

- Replace `agent/coding/requirements.txt` with `pyproject.toml` declaring the project and its dependencies
- Add `uv.lock` (generated) for reproducible installs
- Update `agent/coding/Dockerfile` to install `uv` and use `uv sync` instead of `pip install`
- Local development workflow: developers use `uv run` or `uv venv` + `source .venv/bin/activate` instead of managing a venv manually

## Capabilities

### New Capabilities

- `python-dependency-management`: Declarative Python project metadata and dependency locking using `uv` and `pyproject.toml` within the agent coding service

### Modified Capabilities

<!-- No existing spec-level requirement changes -->

## Impact

- `agent/coding/requirements.txt` — removed
- `agent/coding/pyproject.toml` — new file
- `agent/coding/uv.lock` — new generated file
- `agent/coding/Dockerfile` — updated to install `uv` and use `uv sync --frozen`
- No runtime behavior changes; only tooling and build process affected
