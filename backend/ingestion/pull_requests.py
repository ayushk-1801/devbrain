"""Pull request ingestion: structures PR context (the 'why') into memory."""

from __future__ import annotations

from typing import Any

from backend.config import dataset_name
from backend.ingestion import github_client
from backend.memory import client as memory


def _pr_payload(owner: str, repo: str, pr: dict[str, Any]) -> str:
    comments = "\n".join(
        f"  - {c['author']}: {c['body']}" for c in pr.get("review_comments", [])
    )
    approvals = ", ".join(pr.get("approvals", [])) or "(none)"
    files = "\n".join(f"  - {f}" for f in pr.get("files_changed", []))
    return (
        f"# Pull Request #{pr['number']} in {owner}/{repo}: {pr['title']}\n\n"
        f"Author: {pr['author']}\n"
        f"Merged: {pr['merged_at']}\n"
        f"Approved by: {approvals}\n\n"
        f"## Description\n{pr['body'] or '(no description)'}\n\n"
        f"## Files changed\n{files or '  (none)'}\n\n"
        f"## Review comments\n{comments or '  (none)'}\n"
    )


async def ingest_pr(owner: str, repo: str, pr: dict[str, Any]) -> None:
    """Remember a single pull request into the repo's prs dataset."""
    payload = _pr_payload(owner, repo, pr)
    await memory.remember(payload, dataset_name(owner, repo, "prs"))


async def ingest_prs(owner: str, repo: str, since_days: int | None = None) -> int:
    """Fetch and ingest merged PRs (optionally within a window). Returns count."""
    prs = github_client.fetch_pull_requests(owner, repo, since_days=since_days)
    for pr in prs:
        await ingest_pr(owner, repo, pr)
    return len(prs)
