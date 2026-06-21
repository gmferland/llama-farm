import asyncio
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from config import GITHUB_TOKEN


@dataclass
class EventContext:
    repo_url: str
    repo_full_name: str
    default_branch: str
    issue_number: int
    is_pr: bool
    title: str
    task: str


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
