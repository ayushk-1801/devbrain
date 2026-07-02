"""Application service layer — the shared core behind both the REST API and the
MCP server.

Every function takes an explicit ``repo`` ("owner/repo") so DevBrain is fully
multi-repo: the caller (an agent via MCP, or an HTTP client) decides which repo
to act on per request. This module is the single place where ingestion, query,
pruning, registry bookkeeping, and refresh are orchestrated.
"""

from __future__ import annotations

from typing import Any

from arq import create_pool
from arq.connections import RedisSettings

from backend import registry
from backend.config import settings, split_repo
from backend.ingestion import adrs, codebase, codegraph, commits, issues, pull_requests, releases

# ---------------------------------------------------------------------------
# ARQ queue helpers
# ---------------------------------------------------------------------------

async def get_queue():
    """Return a connected ARQ Redis pool for enqueueing jobs."""
    return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))


async def enqueue_full_sync(repo: str, sync_history_days: int | None = None) -> str:
    """Enqueue a full repo sync and return the job_id."""
    queue = await get_queue()
    job = await queue.enqueue_job("task_full_sync", repo, sync_history_days)
    await queue.aclose()
    return job.job_id


async def enqueue_single_commit(repo: str, sha: str) -> str:
    queue = await get_queue()
    job = await queue.enqueue_job("task_ingest_commit", repo, sha)
    await queue.aclose()
    return job.job_id


async def enqueue_single_pr(repo: str, number: int) -> str:
    queue = await get_queue()
    job = await queue.enqueue_job("task_ingest_pr", repo, number)
    await queue.aclose()
    return job.job_id


async def enqueue_single_issue(repo: str, number: int) -> str:
    queue = await get_queue()
    job = await queue.enqueue_job("task_ingest_issue", repo, number)
    await queue.aclose()
    return job.job_id


async def enqueue_pr_review_comment(repo: str, comment_id: int) -> str:
    queue = await get_queue()
    job = await queue.enqueue_job("task_ingest_pr_review_comment", repo, comment_id)
    await queue.aclose()
    return job.job_id


async def enqueue_release(repo: str, tag: str) -> str:
    queue = await get_queue()
    job = await queue.enqueue_job("task_ingest_release", repo, tag)
    await queue.aclose()
    return job.job_id


async def enqueue_pr_review(repo: str, pr_number: int, review_id: int) -> str:
    queue = await get_queue()
    job = await queue.enqueue_job("task_ingest_pr_review", repo, pr_number, review_id)
    await queue.aclose()
    return job.job_id


async def get_job_status(job_id: str) -> dict[str, Any]:
    """Return the current status and result of a queued job."""
    from arq.jobs import Job, JobStatus, DeserializationError
    queue = await get_queue()
    job = Job(job_id, redis=queue)
    status = await job.status()
    result: dict[str, Any] = {"job_id": job_id, "status": status.value}
    if status == JobStatus.complete:
        try:
            info = await job.result_info()
            if info:
                result["result"] = info.result
                result["success"] = info.success if hasattr(info, "success") else True
        except DeserializationError as exc:
            result["success"] = False
            result["error"] = f"Job failed with a non-deserializable exception: {exc}"
    await queue.aclose()
    return result


async def full_sync(repo: str, sync_history_days: int | None = None) -> dict[str, Any]:
    """Full historical sync of a repo (commits, PRs, issues, ADRs, code, releases).

    Records the repo in the registry so it participates in multi-repo listing
    and the weekly refresh. Returns per-source counts.
    """
    owner, name = split_repo(repo)
    counts = {
        "commits": await commits.ingest_commits(owner, name, since_days=sync_history_days),
        "prs": await pull_requests.ingest_prs(owner, name, since_days=sync_history_days),
        "issues": await issues.ingest_issues(owner, name, since_days=sync_history_days),
        "adrs": await adrs.ingest_adrs(owner, name),
        "releases": await releases.ingest_all_releases(owner, name),
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
    await issues.ingest_issue(owner, name, issue)
    registry.add_repo(repo)


async def ingest_pr_review_comment(repo: str, comment_id: int) -> None:
    """Incremental ingest of one PR review comment (used by the pull_request_review_comment webhook)."""
    from backend.ingestion import github_client

    owner, name = split_repo(repo)
    comment = github_client.fetch_pr_review_comment(owner, name, comment_id)
    await pull_requests.ingest_pr_review_comment(owner, name, comment)
    registry.add_repo(repo)


async def query(question: str, repo: str | None = None, mode: str = "hybrid") -> dict[str, Any]:
    """Natural-language recall — runs in the worker (concurrent with ingestion)."""
    queue = await get_queue()
    job = await queue.enqueue_job("task_query", question, repo, mode)
    result = await job.result(timeout=60)
    await queue.aclose()
    return result


async def forget_module(repo: str, module: str) -> dict[str, Any]:
    """Surgically prune a deprecated module's subgraph via the worker."""
    queue = await get_queue()
    job = await queue.enqueue_job("task_forget_module", repo, module)
    result = await job.result(timeout=60)
    await queue.aclose()
    return result


def list_repos() -> list[str]:
    """List all ingested repos."""
    return registry.list_repos()


async def refresh(repo: str | None = None) -> dict[str, Any]:
    """Run the (expensive) memify enrichment via the worker."""
    queue = await get_queue()
    job = await queue.enqueue_job("task_refresh", repo)
    result = await job.result(timeout=300)
    await queue.aclose()
    return result


async def get_graph_data(repo: str | None = None) -> dict[str, Any]:
    """Fetch the full knowledge graph (nodes + edges) via the worker."""
    queue = await get_queue()
    job = await queue.enqueue_job("task_get_graph_data", repo)
    result = await job.result(timeout=60)
    await queue.aclose()
    return result
