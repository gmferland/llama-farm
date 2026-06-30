## 1. Create pyproject.toml

- [x] 1.1 Create `agent/coding/pyproject.toml` with `[project]` table: `name`, `version`, `requires-python = ">=3.11"`, and all dependencies currently in `requirements.txt`

## 2. Generate lock file

- [x] 2.1 Run `uv lock` inside `agent/coding/` to generate `uv.lock`
- [x] 2.2 Verify `uv sync --frozen` completes successfully with the generated lock file

## 3. Update Dockerfile

- [x] 3.1 Add `uv` to the Docker image by copying from the official `ghcr.io/astral-sh/uv` image layer (e.g., `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/`)
- [x] 3.2 Replace `COPY requirements.txt .` + `RUN pip install ...` with `COPY pyproject.toml uv.lock ./` + `RUN uv sync --frozen --no-dev`
- [x] 3.3 Update `CMD` to use `uv run uvicorn app:app --host 0.0.0.0 --port 8000`

## 4. Remove requirements.txt

- [x] 4.1 Delete `agent/coding/requirements.txt`

## 5. Verify

- [x] 5.1 Run `docker build ./agent/coding` and confirm the image builds successfully
- [x] 5.2 Run `docker run` on the built image and confirm the service starts and responds on port 8000
- [x] 5.3 Add `agent/coding/.venv` to `.gitignore` if not already present
