"""Application service layer — the shared core behind both the REST API and the
MCP server.

Every function takes an explicit ``repo`` ("owner/repo") so DevBrain is fully
multi-repo: the caller (an agent via MCP, or an HTTP client) decides which repo
to act on per request. This module is the single place where ingestion, query,
pruning, registry bookkeeping, and refresh are orchestrated.
"""

from __future__ import annotations

from typing import Any

from backend import registry
from backend.config import split_repo
from backend.ingestion import adrs, codebase, commits, issues as issues_mod, pull_requests
from backend.memory import improve as improve_mod
from backend.memory.forget import deprecate_module
from backend.memory.query import ask_devbrain


async def full_sync(repo: str, sync_history_days: int | None = None) -> dict[str, Any]:
    """Full historical sync of a repo (commits, PRs, ADRs, code structure).

    Records the repo in the registry so it participates in multi-repo listing
    and the weekly refresh. Returns per-source counts.
    """
    owner, name = split_repo(repo)
    counts = {
        "commits": await commits.ingest_commits(owner, name, since_days=sync_history_days),
        "prs": await pull_requests.ingest_prs(owner, name, since_days=sync_history_days),
        "issues": await issues_mod.ingest_issues(owner, name, since_days=sync_history_days),
        "adrs": await adrs.ingest_adrs(owner, name),
        "ast_modules": await codebase.ingest_repo_structure(owner, name),
    }
    registry.add_repo(repo)
    return {"repo": repo, "ingested": counts}


async def ingest_single_commit(repo: str, sha: str) -> None:
    """Incremental ingest of one commit (used by the push webhook)."""
    from backend.ingestion import github_client

    owner, name = split_repo(repo)
    commit = github_client.fetch_commit(owner, name, sha)
    await commits.ingest_commit(owner, name, commit)
    registry.add_repo(repo)


async def ingest_single_pr(repo: str, number: int) -> None:
    """Incremental ingest of one PR (used by the pull_request webhook for all actions)."""
    from backend.ingestion import github_client

    owner, name = split_repo(repo)
    pr = github_client.fetch_pull_request(owner, name, number)
    await pull_requests.ingest_pr(owner, name, pr)
    registry.add_repo(repo)


async def ingest_single_issue(repo: str, number: int) -> None:
    """Incremental ingest of one issue (used by the issues webhook)."""
    from backend.ingestion import github_client

    owner, name = split_repo(repo)
    issue = github_client.fetch_issue(owner, name, number)
    await issues_mod.ingest_issue(owner, name, issue)
    registry.add_repo(repo)


async def ingest_pr_review_comment(repo: str, comment_id: int) -> None:
    """Incremental ingest of one PR review comment (used by the pull_request_review_comment webhook)."""
    from backend.ingestion import github_client

    owner, name = split_repo(repo)
    comment = github_client.fetch_pr_review_comment(owner, name, comment_id)
    await pull_requests.ingest_pr_review_comment(owner, name, comment)
    registry.add_repo(repo)


async def query(question: str, repo: str | None = None, mode: str = "hybrid") -> dict[str, Any]:
    """Natural-language recall over the knowledge graph."""
    return await ask_devbrain(question, repo=repo, mode=mode)


async def forget_module(repo: str, module: str) -> dict[str, Any]:
    """Surgically prune a deprecated module's subgraph."""
    owner, name = split_repo(repo)
    return await deprecate_module(owner, name, module)


def list_repos() -> list[str]:
    """List all ingested repos."""
    return registry.list_repos()


async def refresh(repo: str | None = None) -> dict[str, Any]:
    """Run the (expensive) memify enrichment for one repo, or all if omitted."""
    if repo:
        await improve_mod.refresh_repo(repo)
        return {"refreshed": [repo]}
    await improve_mod.weekly_memory_refresh()
    return {"refreshed": registry.list_repos()}
