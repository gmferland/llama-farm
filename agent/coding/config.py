import os

GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
LLM_BASE_URL = os.environ.get("LLM_BASE_URL")
LLM_MODEL = os.environ.get("LLM_MODEL")
AGENT_MAX_ITERATIONS = int(os.environ.get("AGENT_MAX_ITERATIONS", "20"))
AGENT_MAX_CONCURRENCY = int(os.environ.get("AGENT_MAX_CONCURRENCY", "20"))

_app_id_raw = os.environ.get("GITHUB_APP_ID")
_app_key_raw = os.environ.get("GITHUB_APP_PRIVATE_KEY")

if not _app_id_raw:
    raise RuntimeError("GITHUB_APP_ID environment variable is required but not set")
if not _app_key_raw:
    raise RuntimeError("GITHUB_APP_PRIVATE_KEY environment variable is required but not set")

GITHUB_APP_ID: int = int(_app_id_raw)
GITHUB_APP_PRIVATE_KEY: str = _app_key_raw.replace("\\n", "\n")
