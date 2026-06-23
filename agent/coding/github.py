import asyncio
from datetime import datetime, timezone

import httpx
import jwt

from config import GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY
from workspace import Workspace

_token_cache: dict[int, tuple[str, datetime]] = {}


def _generate_jwt() -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": GITHUB_APP_ID,
    }
    return jwt.encode(payload, GITHUB_APP_PRIVATE_KEY, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    cached = _token_cache.get(installation_id)
    if cached:
        token, expires_at = cached
        remaining = (expires_at - datetime.now(timezone.utc)).total_seconds()
        if remaining > 300:
            return token
        del _token_cache[installation_id]

    app_jwt = _generate_jwt()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    token = data["token"]
    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    _token_cache[installation_id] = (token, expires_at)
    return token


def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


async def gh_post_comment(repo: str, issue_number: int, body: str, token: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
            headers=_gh_headers(token),
            json={"body": body},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("html_url", "")


async def gh_push_and_open_pr(ws: Workspace, summary: str, token: str) -> str:
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
            headers=_gh_headers(token),
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
