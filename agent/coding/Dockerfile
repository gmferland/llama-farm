FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY *.py .
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
