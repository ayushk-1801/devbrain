"""ARQ worker — all long-running ingestion tasks run here, off the API process.

The API enqueues a job and returns a job_id immediately. This worker process
picks it up from Redis and runs it asynchronously.

Start the worker:
    python -m arq backend.worker.WorkerSettings
Or via docker-compose:
    docker compose up devbrain-worker
"""

from __future__ import annotations

import logging

from arq.connections import RedisSettings

from backend.config import settings
from backend.memory import client as memory

logger = logging.getLogger("devbrain.worker")


# ---------------------------------------------------------------------------
# Task functions
# Each receives a ctx dict as its first argument (ARQ convention).
# ---------------------------------------------------------------------------

async def task_full_sync(ctx: dict, repo: str, sync_history_days: int | None = None) -> dict:
    """Full historical ingest of a repo (commits, PRs, issues, ADRs, code structure)."""
    from backend import service
    logger.info("task_full_sync started: repo=%s days=%s", repo, sync_history_days)
    result = await service.full_sync(repo, sync_history_days)
    logger.info("task_full_sync done: %s", result)
    return result


async def task_ingest_commit(ctx: dict, repo: str, sha: str) -> None:
    """Incremental ingest of one pushed commit."""
    from backend import service
    logger.info("task_ingest_commit: repo=%s sha=%s", repo, sha)
    await service.ingest_single_commit(repo, sha)


async def task_ingest_pr(ctx: dict, repo: str, number: int) -> None:
    """Incremental ingest of one PR (opened / updated / merged)."""
    from backend import service
    logger.info("task_ingest_pr: repo=%s pr=#%s", repo, number)
    await service.ingest_single_pr(repo, number)


async def task_ingest_issue(ctx: dict, repo: str, number: int) -> None:
    """Incremental ingest of one issue."""
    from backend import service
    logger.info("task_ingest_issue: repo=%s issue=#%s", repo, number)
    await service.ingest_single_issue(repo, number)


async def task_ingest_pr_review_comment(ctx: dict, repo: str, comment_id: int) -> None:
    """Incremental ingest of one PR inline review comment."""
    from backend import service
    logger.info("task_ingest_pr_review_comment: repo=%s comment=%s", repo, comment_id)
    await service.ingest_pr_review_comment(repo, comment_id)


async def task_query(ctx: dict, question: str, repo: str | None, mode: str) -> dict:
    """Run a natural-language query against the knowledge graph."""
    from backend.memory.query import ask_devbrain
    logger.info("task_query: q=%r repo=%s mode=%s", question, repo, mode)
    return await ask_devbrain(question, repo=repo, mode=mode)


async def task_refresh(ctx: dict, repo: str | None) -> dict:
    """Run Cognee memify enrichment for one repo or all."""
    from backend.memory import improve as improve_mod
    from backend import registry
    if repo:
        await improve_mod.refresh_repo(repo)
        return {"refreshed": [repo]}
    await improve_mod.weekly_memory_refresh()
    return {"refreshed": registry.list_repos()}


async def task_forget_module(ctx: dict, repo: str, module: str) -> dict:
    """Surgically prune a deprecated module's subgraph."""
    from backend.memory.forget import deprecate_module
    from backend.config import split_repo
    owner, name = split_repo(repo)
    logger.info("task_forget_module: repo=%s module=%s", repo, module)
    return await deprecate_module(owner, name, module)


async def task_ingest_release(ctx: dict, repo: str, tag: str) -> None:
    """Ingest a single published release."""
    from backend import service
    from backend.config import split_repo
    from backend.ingestion import releases as rel_mod, github_client
    owner, name = split_repo(repo)
    logger.info("task_ingest_release: repo=%s tag=%s", repo, tag)
    releases = github_client.fetch_releases(owner, name)
    for r in releases:
        if r["tag"] == tag:
            await rel_mod.ingest_release(owner, name, r)
            return
    logger.warning("release tag %s not found for %s", tag, repo)


async def task_ingest_pr_review(ctx: dict, repo: str, pr_number: int, review_id: int) -> None:
    """Ingest a single PR review summary."""
    from backend import service
    logger.info("task_ingest_pr_review: repo=%s pr=#%s review=%s", repo, pr_number, review_id)
    # Re-ingest the full PR which now includes the review summaries
    await service.ingest_single_pr(repo, pr_number)


# ---------------------------------------------------------------------------
# Startup / shutdown hooks — connect Cognee once per worker process
# ---------------------------------------------------------------------------

async def startup(ctx: dict) -> None:
    await memory.connect()
    logger.info("ARQ worker started in %s mode", settings.COGNEE_MODE)


async def shutdown(ctx: dict) -> None:
    await memory.disconnect()
    logger.info("ARQ worker shut down")


# ---------------------------------------------------------------------------
# Worker configuration
# ---------------------------------------------------------------------------

class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions = [
        task_full_sync,
        task_ingest_commit,
        task_ingest_pr,
        task_ingest_issue,
        task_ingest_pr_review_comment,
        task_ingest_release,
        task_ingest_pr_review,
        task_query,
        task_refresh,
        task_forget_module,
    ]
    on_startup = startup
    on_shutdown = shutdown
    # Keep job results in Redis for 24 hours so the API can poll status.
    keep_result = 3600 * 24
    # Retry failed jobs once before marking them failed.
    max_tries = 2
    # Allow ingestion and query tasks to run concurrently in the same process.
    # Queries share the single Kuzu connection opened at startup and never wait
    # behind an in-progress ingestion job.
    max_jobs = 10
