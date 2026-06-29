"""Commit ingestion: structures commit data into a memory payload and remembers it."""

from __future__ import annotations

from typing import Any

from backend.config import dataset_name
from backend.ingestion import github_client
from backend.memory import client as memory


def _commit_payload(owner: str, repo: str, commit: dict[str, Any]) -> str:
    files = "\n".join(
        f"  - {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})"
        for f in commit.get("diff_summary", [])
    )
    return (
        f"# Commit {commit['sha'][:10]} in {owner}/{repo}\n\n"
        f"Author: {commit['author']} <{commit['author_email']}>\n"
        f"Date: {commit['date']}\n\n"
        f"## Message\n{commit['message']}\n\n"
        f"## Files changed\n{files or '  (none reported)'}\n"
    )


async def ingest_commit(owner: str, repo: str, commit: dict[str, Any]) -> None:
    """Remember a single commit into the repo's commits dataset."""
    payload = _commit_payload(owner, repo, commit)
    await memory.remember(payload, dataset_name(owner, repo, "commits"))


async def ingest_commits(owner: str, repo: str, since_days: int | None = None) -> int:
    """Fetch and ingest all commits (optionally within a window). Returns count."""
    commits = github_client.fetch_commits(owner, repo, since_days=since_days)
    for commit in commits:
        await ingest_commit(owner, repo, commit)
    return len(commits)
