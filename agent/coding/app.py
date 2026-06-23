import hashlib
import hmac
import json
import logging

from fastapi import BackgroundTasks, FastAPI, Header, Request, Response

from agent import run_agent
from config import AGENT_MAX_CONCURRENCY, GITHUB_WEBHOOK_SECRET
from github import get_installation_token, gh_post_comment
from workspace import EventContext, Workspace

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_active_runs = 0

app = FastAPI()


def _verify_signature(body: bytes, sig_header: str) -> bool:
    if not sig_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)


def parse_event(payload: dict, event_type: str) -> EventContext | None:
    installation_id: int | None = payload.get("installation", {}).get("id")

    if event_type == "issue_comment":
        body: str = payload.get("comment", {}).get("body", "")
        stripped = body.lstrip()
        if not stripped.lower().startswith("/agent"):
            return None
        if installation_id is None:
            return None
        task = stripped[len("/agent"):].strip()
        issue = payload["issue"]
        repo = payload["repository"]
        return EventContext(
            repo_url=repo["clone_url"],
            repo_full_name=repo["full_name"],
            default_branch=repo.get("default_branch", "main"),
            issue_number=issue["number"],
            is_pr="pull_request" in issue,
            title=issue.get("title", ""),
            task=task or issue.get("title", ""),
            installation_id=installation_id,
        )

    if event_type == "pull_request_review_comment":
        body = payload.get("comment", {}).get("body", "")
        stripped = body.lstrip()
        if not stripped.lower().startswith("/agent"):
            return None
        if installation_id is None:
            return None
        task = stripped[len("/agent"):].strip()
        pr = payload["pull_request"]
        repo = payload["repository"]
        return EventContext(
            repo_url=repo["clone_url"],
            repo_full_name=repo["full_name"],
            default_branch=repo.get("default_branch", "main"),
            issue_number=pr["number"],
            is_pr=True,
            title=pr.get("title", ""),
            task=task or pr.get("title", ""),
            installation_id=installation_id,
        )

    if event_type == "issues":
        if payload.get("action") != "labeled":
            return None
        if payload.get("label", {}).get("name") != "agent-task":
            return None
        if installation_id is None:
            return None
        issue = payload["issue"]
        repo = payload["repository"]
        return EventContext(
            repo_url=repo["clone_url"],
            repo_full_name=repo["full_name"],
            default_branch=repo.get("default_branch", "main"),
            issue_number=issue["number"],
            is_pr=False,
            title=issue.get("title", ""),
            task=issue.get("body", "") or issue.get("title", ""),
            installation_id=installation_id,
        )

    return None


async def dispatch(payload: dict, event_type: str) -> None:
    global _active_runs
    ctx = parse_event(payload, event_type)
    if ctx is None:
        return

    if _active_runs >= AGENT_MAX_CONCURRENCY:
        token = await get_installation_token(ctx.installation_id)
        await gh_post_comment(
            ctx.repo_full_name,
            ctx.issue_number,
            "Agent busy: system at capacity, try again later.",
            token=token,
        )
        return

    _active_runs += 1
    try:
        ws = Workspace(event=ctx)
        await run_agent(ws)
    finally:
        _active_runs -= 1


@app.post("/github/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> Response:
    body = await request.body()

    if not x_hub_signature_256:
        return Response(status_code=401, content="Missing signature")
    if not _verify_signature(body, x_hub_signature_256):
        log.warning("Invalid webhook signature, event=%s", x_github_event)
        return Response(status_code=401, content="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON")

    recognized = {"issue_comment", "pull_request_review_comment", "issues"}
    if x_github_event in recognized:
        background_tasks.add_task(dispatch, payload, x_github_event)

    return Response(status_code=202)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
