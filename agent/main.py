import asyncio
import hashlib
import hmac
import json
import logging
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, Request, Response
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"].encode()
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://qwen:8080")
LLM_MODEL = os.environ.get("LLM_MODEL", "unsloth/Qwen3.5-2B-GGUF")
AGENT_MAX_ITERATIONS = int(os.environ.get("AGENT_MAX_ITERATIONS", "20"))
AGENT_MAX_CONCURRENCY = int(os.environ.get("AGENT_MAX_CONCURRENCY", "20"))
GITHUB_REPO = os.environ["GITHUB_REPO"]

_active_runs = 0


# ---------------------------------------------------------------------------
# Event context
# ---------------------------------------------------------------------------


@dataclass
class EventContext:
    repo_url: str
    repo_full_name: str
    default_branch: str
    issue_number: int
    is_pr: bool
    title: str
    task: str


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


@dataclass
class Workspace:
    event: EventContext
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    path: Path | None = None
    commit_count: int = 0

    @property
    def branch(self) -> str:
        return f"agent/{self.run_id}"

    async def init(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="agent-ws-")
        self.path = Path(tmpdir)
        auth_url = self.event.repo_url.replace(
            "https://", f"https://x-access-token:{GITHUB_TOKEN}@"
        )
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth=1", auth_url, ".",
            cwd=str(self.path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            shutil.rmtree(self.path, ignore_errors=True)
            self.path = None
            raise RuntimeError(f"git clone failed: {stderr.decode()}")

        for cmd in (
            ["git", "config", "user.email", "agent@llama-farm"],
            ["git", "config", "user.name", "Llama Farm Agent"],
            ["git", "checkout", "-b", self.branch],
        ):
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

    def cleanup(self) -> None:
        if self.path:
            shutil.rmtree(self.path, ignore_errors=True)
            self.path = None

    def resolve(self, rel_path: str) -> Path | None:
        if self.path is None:
            return None
        try:
            base = self.path.resolve()
            target = (self.path / rel_path).resolve()
        except Exception:
            return None
        if target != base and not str(target).startswith(str(base) + os.sep):
            return None
        return target


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def _gh_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


async def gh_post_comment(repo: str, issue_number: int, body: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
            headers=_gh_headers(),
            json={"body": body},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("html_url", "")


async def gh_push_and_open_pr(ws: Workspace, summary: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", "push", "origin", ws.branch,
        cwd=str(ws.path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"git push failed: {stderr.decode()}")

    pr_body = f"Automated changes by Llama Farm agent.\n\nTask: {ws.event.task}"
    if summary:
        pr_body += f"\n\n{summary}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{ws.event.repo_full_name}/pulls",
            headers=_gh_headers(),
            json={
                "head": ws.branch,
                "base": ws.event.default_branch,
                "title": ws.event.task[:72],
                "body": pr_body,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("html_url", "")


# ---------------------------------------------------------------------------
# PydanticAI agent
# ---------------------------------------------------------------------------

_provider = OpenAIProvider(base_url=f"{LLM_BASE_URL}/v1", api_key="dummy")
_model = OpenAIChatModel(LLM_MODEL, provider=_provider)
agent: Agent[Workspace, str] = Agent(_model, deps_type=Workspace, output_type=str)


@agent.system_prompt
async def _system_prompt(ctx: RunContext[Workspace]) -> str:
    ws = ctx.deps
    return (
        f"You are a coding agent working on the GitHub repository {ws.event.repo_full_name}.\n"
        f"Your task: {ws.event.task}\n"
        f"Context: {ws.event.title}\n\n"
        "Use your tools to complete the task. Available tools:\n"
        "- read_file(path): read a file by path relative to the repo root\n"
        "- write_file(path, content): create or overwrite a file\n"
        "- list_directory(path): list directory contents as JSON\n"
        "- run_shell(command): run a shell command in the repo directory (60s timeout)\n"
        "- commit_changes(message): stage all changes and create a git commit\n"
        "- post_comment(body): post a comment on the triggering issue or PR\n\n"
        "When you have finished the task, call commit_changes with a descriptive message. "
        "If the task is already done or no changes are needed, explain why in your response."
    )


@agent.tool
async def read_file(ctx: RunContext[Workspace], path: str) -> str:
    resolved = ctx.deps.resolve(path)
    if resolved is None:
        return f"Error: '{path}' is outside the workspace"
    if not resolved.exists():
        return f"Error: file not found: {path}"
    return resolved.read_text(errors="replace")


@agent.tool
async def write_file(ctx: RunContext[Workspace], path: str, content: str) -> str:
    resolved = ctx.deps.resolve(path)
    if resolved is None:
        return f"Error: '{path}' is outside the workspace"
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    return f"Written: {path}"


@agent.tool
async def list_directory(ctx: RunContext[Workspace], path: str = ".") -> str:
    resolved = ctx.deps.resolve(path)
    if resolved is None:
        return f"Error: '{path}' is outside the workspace"
    if not resolved.is_dir():
        return f"Error: not a directory: {path}"
    entries = [
        {"name": e.name, "type": "dir" if e.is_dir() else "file"}
        for e in sorted(resolved.iterdir())
    ]
    return json.dumps(entries)


@agent.tool
async def run_shell(ctx: RunContext[Workspace], command: str) -> str:
    ws = ctx.deps
    if ws.path is None:
        return json.dumps({"stdout": "", "stderr": "No workspace", "exit_code": -1})
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=str(ws.path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        return json.dumps({
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "exit_code": proc.returncode,
        })
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return json.dumps({"stdout": "", "stderr": "Timed out after 60s", "exit_code": -1})


@agent.tool
async def commit_changes(ctx: RunContext[Workspace], message: str) -> str:
    ws = ctx.deps
    if ws.path is None:
        return "Error: no workspace"

    add_proc = await asyncio.create_subprocess_exec(
        "git", "add", "-A",
        cwd=str(ws.path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await add_proc.wait()

    commit_proc = await asyncio.create_subprocess_exec(
        "git", "commit", "-m", message,
        cwd=str(ws.path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await commit_proc.communicate()
    output = stdout.decode() + stderr.decode()

    if commit_proc.returncode == 0:
        sha_proc = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "HEAD",
            cwd=str(ws.path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        sha_out, _ = await sha_proc.communicate()
        ws.commit_count += 1
        return f"Committed: {sha_out.decode().strip()}"

    if "nothing to commit" in output:
        return "Nothing to commit"
    return f"Commit failed: {output.strip()}"


@agent.tool
async def post_comment(ctx: RunContext[Workspace], body: str) -> str:
    ws = ctx.deps
    url = await gh_post_comment(ws.event.repo_full_name, ws.event.issue_number, body)
    return f"Comment posted: {url}"


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------


async def run_agent(ws: Workspace) -> None:
    try:
        await ws.init()
        await gh_post_comment(
            ws.event.repo_full_name,
            ws.event.issue_number,
            f"Agent started: {ws.event.task[:80]}",
        )

        reached_limit = False
        summary = ""
        try:
            result = await agent.run(
                ws.event.task,
                deps=ws,
                usage_limits=UsageLimits(request_limit=AGENT_MAX_ITERATIONS),
            )
            summary = result.response.text or ""
        except UsageLimitExceeded:
            reached_limit = True
            await gh_post_comment(
                ws.event.repo_full_name,
                ws.event.issue_number,
                "Agent reached iteration limit.",
            )

        if not reached_limit:
            if ws.commit_count > 0:
                pr_url = await gh_push_and_open_pr(ws, summary)
                await gh_post_comment(
                    ws.event.repo_full_name,
                    ws.event.issue_number,
                    f"Agent completed. PR: {pr_url}",
                )
            else:
                await gh_post_comment(
                    ws.event.repo_full_name,
                    ws.event.issue_number,
                    "Agent completed but made no changes.",
                )

    except Exception as e:
        log.exception("Agent run failed")
        try:
            await gh_post_comment(
                ws.event.repo_full_name,
                ws.event.issue_number,
                f"Agent failed: {type(e).__name__}: {e}",
            )
        except Exception:
            log.exception("Failed to post error comment")
    finally:
        ws.cleanup()


# ---------------------------------------------------------------------------
# Event dispatcher
# ---------------------------------------------------------------------------


def parse_event(payload: dict, event_type: str) -> EventContext | None:
    if event_type == "issue_comment":
        body: str = payload.get("comment", {}).get("body", "")
        stripped = body.lstrip()
        if not stripped.lower().startswith("/agent"):
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
        )

    if event_type == "pull_request_review_comment":
        body = payload.get("comment", {}).get("body", "")
        stripped = body.lstrip()
        if not stripped.lower().startswith("/agent"):
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
        )

    if event_type == "issues":
        if payload.get("action") != "labeled":
            return None
        if payload.get("label", {}).get("name") != "agent-task":
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
        )

    return None


async def dispatch(payload: dict, event_type: str) -> None:
    global _active_runs
    ctx = parse_event(payload, event_type)
    if ctx is None:
        return

    if _active_runs >= AGENT_MAX_CONCURRENCY:
        await gh_post_comment(
            ctx.repo_full_name,
            ctx.issue_number,
            "Agent busy: system at capacity, try again later.",
        )
        return

    _active_runs += 1
    try:
        ws = Workspace(event=ctx)
        await run_agent(ws)
    finally:
        _active_runs -= 1


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI()


def _verify_signature(body: bytes, sig_header: str) -> bool:
    if not sig_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)


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
