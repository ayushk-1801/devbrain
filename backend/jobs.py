"""Lightweight in-process job tracker using asyncio tasks.

Replaces ARQ so ingestion and queries share the same event loop and the same
Kuzu connection — eliminating file-lock conflicts entirely.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import OrderedDict
from typing import Any, Coroutine

# Keep the last 500 job results in memory (FIFO eviction).
_MAX_JOBS = 500
_JOBS: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _evict() -> None:
    while len(_JOBS) > _MAX_JOBS:
        _JOBS.popitem(last=False)


def create_job() -> str:
    job_id = uuid.uuid4().hex
    _JOBS[job_id] = {"status": "queued", "result": None, "success": None}
    _evict()
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    return _JOBS.get(job_id)


async def _run(job_id: str, coro: Coroutine) -> None:
    _JOBS[job_id]["status"] = "in_progress"
    try:
        result = await coro
        _JOBS[job_id].update({"status": "complete", "result": result, "success": True})
    except Exception as exc:
        _JOBS[job_id].update({"status": "complete", "result": str(exc), "success": False})


def enqueue(coro: Coroutine) -> str:
    """Schedule *coro* as a background asyncio task and return a job_id."""
    job_id = create_job()
    asyncio.create_task(_run(job_id, coro))
    return job_id
