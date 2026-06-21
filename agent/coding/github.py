import asyncio

import httpx

from config import GITHUB_TOKEN
from workspace import Workspace


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
