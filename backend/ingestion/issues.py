"""Issue ingestion: structures issue context (discussion decisions) into memory."""

from __future__ import annotations

from typing import Any

from backend.config import dataset_name
from backend.ingestion import github_client
from backend.memory import client as memory


def _issue_payload(owner: str, repo: str, issue: dict[str, Any]) -> str:
    """Format an issue with its comment discussions into a memory payload."""
    comments = "\n".join(
        f"  - {c['author']}: {c['body']}" for c in issue.get("comments", [])
    )
    return (
        f"# Issue #{issue['number']} in {owner}/{repo}: {issue['title']}\n\n"
        f"Author: {issue['author']}\n"
        f"Closed: {issue['closed_at']}\n"
        f"State: {issue['state']}\n\n"
        f"## Description\n{issue['body'] or '(no description)'}\n\n"
        f"## Comments\n{comments or '  (none)'}\n"
    )


async def ingest_issue(owner: str, repo: str, issue: dict[str, Any]) -> None:
    """Remember a single issue into the repo's issues dataset."""
    payload = _issue_payload(owner, repo, issue)
    await memory.remember(payload, dataset_name(owner, repo, "issues"))


async def ingest_issues(owner: str, repo: str, since_days: int | None = None) -> int:
    """Fetch and ingest closed issues (optionally within a window). Returns count."""
    issues = github_client.fetch_issues(owner, repo, since_days=since_days)
    for issue in issues:
        await ingest_issue(owner, repo, issue)
    return len(issues)
