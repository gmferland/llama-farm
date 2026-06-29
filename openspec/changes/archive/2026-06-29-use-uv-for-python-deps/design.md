## Context

The `agent/coding` service currently manages Python dependencies via a flat `requirements.txt` file installed with `pip install --no-cache-dir`. There is no lock file, so installs are not reproducible across machines or CI runs — a new package release can silently change behavior. Developers bootstrapping locally must manage their own virtualenv manually.

`uv` is a fast, Rust-based Python package manager that replaces `pip` + `venv` + `pip-tools` in a single tool. It produces a `uv.lock` file for deterministic installs and integrates cleanly with Docker via `uv sync --frozen`.

## Goals / Non-Goals

**Goals:**
- Reproducible dependency installs in Docker and locally via `uv.lock`
- Standard Python project metadata in `pyproject.toml` (PEP 621)
- Simple local dev workflow: `uv run uvicorn ...` or `uv sync` + activate venv
- Minimal Docker image size impact

**Non-Goals:**
- Multi-package monorepo workspaces (only one service is in scope)
- Publishing the package to PyPI
- Changing any runtime application code or behavior

## Decisions

### 1. `pyproject.toml` over keeping `requirements.txt`

`pyproject.toml` is the modern PEP 621 standard for declaring project metadata and dependencies. `uv` uses it as the source of truth, and `uv lock` generates `uv.lock` from it. `requirements.txt` is removed entirely — it becomes redundant and risks drift.

*Alternative considered*: Keep `requirements.txt` and use `uv pip install -r requirements.txt`. Rejected: this skips lock file generation and doesn't improve reproducibility.

### 2. `uv sync --frozen` in Docker

The Dockerfile will install `uv`, copy `pyproject.toml` + `uv.lock` before copying application code, then run `uv sync --frozen --no-dev`. `--frozen` fails the build if `uv.lock` is out of sync with `pyproject.toml`, catching drift at build time rather than at runtime.

*Alternative considered*: `uv pip install` without a venv inside Docker. Rejected: `uv sync` is the idiomatic path and automatically manages the venv at `.venv/`.

### 3. Run the app via `uv run` in Docker CMD

The Docker `CMD` uses `uv run uvicorn app:app ...`. This activates the managed venv transparently without requiring an explicit `source .venv/bin/activate` step, keeping the Dockerfile clean.

*Alternative considered*: Explicitly activate the venv with `RUN source .venv/bin/activate` as a shell form. Rejected: shell activation doesn't persist across `RUN` layers; `uv run` is the recommended approach.

## Risks / Trade-offs

- **uv version pinning in Dockerfile** → Pin `uv` via `COPY --from=ghcr.io/astral-sh/uv:latest` or install a pinned version to avoid surprise breakage from uv updates. Use the official distroless Docker image layer.
- **uv.lock committed to repo** → The lock file is ~50–200 lines; acceptable to commit. It must be regenerated whenever `pyproject.toml` dependencies change (`uv lock`).
- **Docker layer caching** → `pyproject.toml` + `uv.lock` are copied before source files so the `uv sync` layer is cached unless dependencies change — a net improvement over the current setup.
