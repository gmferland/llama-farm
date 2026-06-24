import os


def load_secret(name: str) -> str | None:
    path = f"/run/secrets/{name}"
    try:
        with open(path) as f:
            value = f.read().strip()
        return value or None
    except FileNotFoundError:
        return os.environ.get(name) or None


LLM_BASE_URL = os.environ.get("LLM_BASE_URL")
LLM_MODEL = os.environ.get("LLM_MODEL")
AGENT_MAX_ITERATIONS = int(os.environ.get("AGENT_MAX_ITERATIONS", "20"))
AGENT_MAX_CONCURRENCY = int(os.environ.get("AGENT_MAX_CONCURRENCY", "20"))

_webhook_secret = load_secret("GITHUB_WEBHOOK_SECRET")
if not _webhook_secret:
    raise RuntimeError("GITHUB_WEBHOOK_SECRET is required but not set (checked /run/secrets/GITHUB_WEBHOOK_SECRET and env)")
GITHUB_WEBHOOK_SECRET: bytes = _webhook_secret.encode()

_app_id_raw = load_secret("GITHUB_APP_ID")
_app_key_raw = load_secret("GITHUB_APP_PRIVATE_KEY")

if not _app_id_raw:
    raise RuntimeError("GITHUB_APP_ID is required but not set (checked /run/secrets/GITHUB_APP_ID and env)")
if not _app_key_raw:
    raise RuntimeError("GITHUB_APP_PRIVATE_KEY is required but not set (checked /run/secrets/GITHUB_APP_PRIVATE_KEY and env)")

GITHUB_APP_ID: int = int(_app_id_raw)
GITHUB_APP_PRIVATE_KEY: str = _app_key_raw.replace("\\n", "\n")
