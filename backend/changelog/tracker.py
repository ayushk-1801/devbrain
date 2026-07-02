"""Persistent state tracker for the changelog subsystem — backed by Redis.

All state that previously lived in ``.devbrain/changelog_state.json`` now lives
in Redis so it survives container restarts and is consistent across replicas.

Redis key schema
----------------
devbrain:cl:sync:global:{safe_repo}       STRING  ISO-8601 timestamp
devbrain:cl:sync:user:{safe_repo}:{user}  STRING  ISO-8601 timestamp
devbrain:cl:webhook:{safe_repo}:{user}    STRING  webhook URL
devbrain:cl:subs:{safe_repo}              SET     subscribed usernames

``{safe_repo}`` replaces "/" with ":" and lowercases everything.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import redis.asyncio as aioredis

from backend.config import settings

logger = logging.getLogger("devbrain.changelog.tracker")

_PREFIX = "devbrain:cl"

# ---------------------------------------------------------------------------
# Redis connection — lazy singleton pool
# ---------------------------------------------------------------------------

_pool: Optional[aioredis.Redis] = None
_pool_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _pool_lock
    if _pool_lock is None:
        _pool_lock = asyncio.Lock()
    return _pool_lock


async def _redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        async with _get_lock():
            if _pool is None:  # re-check inside the lock
                _pool = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _pool


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def _safe(repo: str) -> str:
    return repo.replace("/", ":").replace("-", "_").lower()


def _key_global(repo: str) -> str:
    return f"{_PREFIX}:sync:global:{_safe(repo)}"


def _key_user(repo: str, username: str) -> str:
    return f"{_PREFIX}:sync:user:{_safe(repo)}:{username.lower()}"


def _key_webhook(repo: str, username: str) -> str:
    return f"{_PREFIX}:webhook:{_safe(repo)}:{username.lower()}"


def _key_subs(repo: str) -> str:
    return f"{_PREFIX}:subs:{_safe(repo)}"


def _parse_ts(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    dt = datetime.fromisoformat(raw)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


# ---------------------------------------------------------------------------
# Public API — all async
# ---------------------------------------------------------------------------


async def get_last_global_sync(repo: str) -> Optional[datetime]:
    """Return the UTC datetime of the last global changelog generation, or None."""
    r = await _redis()
    return _parse_ts(await r.get(_key_global(repo)))


async def set_last_global_sync(repo: str, when: datetime) -> None:
    """Persist the global sync timestamp for *repo*."""
    r = await _redis()
    await r.set(_key_global(repo), when.isoformat())


async def get_last_user_seen(repo: str, username: str) -> Optional[datetime]:
    """Return when *username* last fetched their personal update digest."""
    r = await _redis()
    return _parse_ts(await r.get(_key_user(repo, username)))


async def set_last_user_seen(repo: str, username: str, when: datetime) -> None:
    """Persist the user-level last-seen timestamp and register the subscriber."""
    r = await _redis()
    await r.set(_key_user(repo, username), when.isoformat())
    await r.sadd(_key_subs(repo), username.lower())  # type: ignore[misc]


async def get_user_webhook(repo: str, username: str) -> Optional[str]:
    """Return the notification webhook URL registered for *username*, if any."""
    r = await _redis()
    return await r.get(_key_webhook(repo, username))


async def set_user_webhook(repo: str, username: str, webhook_url: str) -> None:
    """Register or update a notification webhook URL for *username*."""
    r = await _redis()
    await r.set(_key_webhook(repo, username), webhook_url)
    await r.sadd(_key_subs(repo), username.lower())  # type: ignore[misc]


async def list_subscribed_users(repo: str) -> list[str]:
    """Return all usernames subscribed to changelog updates for *repo*."""
    r = await _redis()
    return list(await r.smembers(_key_subs(repo)))  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Markdown output directory — local filesystem, output artifacts only
# ---------------------------------------------------------------------------


def changelogs_dir() -> Path:
    """Return (and create) the local directory for rendered Markdown files.

    The Markdown files are rendered output only; all persistent state lives
    in Redis and Cognee Cloud.
    """
    base = Path(settings.REGISTRY_PATH).parent / "changelogs"
    base.mkdir(parents=True, exist_ok=True)
    return base
