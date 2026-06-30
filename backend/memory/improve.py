"""Self-improving memory: enrichment of the knowledge graph via memify.

This is expensive. The weekly cron is the only *automatic* caller — never run it
inline from a query or webhook handler (AGENTS.md rule). It may also be triggered
explicitly (e.g. an MCP ``refresh_memory`` tool) for demos.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend import registry
from backend.config import dataset_name, split_repo
from backend.memory import client as memory

logger = logging.getLogger("devbrain.improve")

# Dataset kinds enriched on each refresh.
_KINDS = ("commits", "prs", "adrs", "ast", "issues")


async def refresh_repo(repo: str) -> None:
    """Run memify across one repo's datasets to strengthen its graph."""
    owner, name = split_repo(repo)
    for kind in _KINDS:
        ds = dataset_name(owner, name, kind)
        try:
            await memory.improve(ds)
            logger.info("memify completed for %s", ds)
        except Exception:  # one dataset failing shouldn't abort the rest
            logger.exception("memify failed for %s", ds)


async def weekly_memory_refresh() -> None:
    """Run memify across every ingested repo (driven by the registry)."""
    repos = registry.list_repos()
    if not repos:
        logger.info("weekly_memory_refresh: no repos ingested yet, nothing to do")
        return
    for repo in repos:
        await refresh_repo(repo)


def start_scheduler() -> AsyncIOScheduler:
    """Create and start the weekly refresh scheduler (every 7 days)."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        weekly_memory_refresh,
        trigger="interval",
        days=7,
        id="weekly_memory_refresh",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Weekly memory refresh scheduled (every 7 days)")
    return scheduler
