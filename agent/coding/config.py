import os

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
LLM_BASE_URL = os.environ.get("LLM_BASE_URL")
LLM_MODEL = os.environ.get("LLM_MODEL")
AGENT_MAX_ITERATIONS = int(os.environ.get("AGENT_MAX_ITERATIONS", "20"))
AGENT_MAX_CONCURRENCY = int(os.environ.get("AGENT_MAX_CONCURRENCY", "20"))
GITHUB_REPO = os.environ["GITHUB_REPO"]
