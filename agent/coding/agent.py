import asyncio
import json
import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from config import AGENT_MAX_ITERATIONS, LLM_BASE_URL, LLM_MODEL
from github import gh_post_comment, gh_push_and_open_pr
from workspace import Workspace

log = logging.getLogger(__name__)

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
    url = await gh_post_comment(ws.event.repo_full_name, ws.event.issue_number, body, token=ws.token)
    return f"Comment posted: {url}"


async def run_agent(ws: Workspace) -> None:
    try:
        await ws.init()
        await gh_post_comment(
            ws.event.repo_full_name,
            ws.event.issue_number,
            f"Agent started: {ws.event.task[:80]}",
            token=ws.token,
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
                token=ws.token,
            )

        if not reached_limit:
            if ws.commit_count > 0:
                pr_url = await gh_push_and_open_pr(ws, summary, token=ws.token)
                await gh_post_comment(
                    ws.event.repo_full_name,
                    ws.event.issue_number,
                    f"Agent completed. PR: {pr_url}",
                    token=ws.token,
                )
            else:
                await gh_post_comment(
                    ws.event.repo_full_name,
                    ws.event.issue_number,
                    "Agent completed but made no changes.",
                    token=ws.token,
                )

    except Exception as e:
        log.exception("Agent run failed")
        try:
            await gh_post_comment(
                ws.event.repo_full_name,
                ws.event.issue_number,
                f"Agent failed: {type(e).__name__}: {e}",
                token=ws.token,
            )
        except Exception:
            log.exception("Failed to post error comment")
    finally:
        ws.cleanup()
