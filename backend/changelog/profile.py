"""User profile store — Redis for exact state, Cognee Cloud for semantics.

Every GitHub webhook event calls one of the ``update_from_*`` functions here.
Each call does two things:

1. **Redis** (fast, exact) — structured state per user:
   - ``owned_files``         → Redis SET   (O(1) membership check)
   - ``reviewed_pr_numbers`` → Redis SET
   - ``mention index``       → Redis ZSET  (score = unix timestamp → range queries)
   - ``file-touch index``    → Redis ZSET  (score = unix timestamp → range queries)
   - ``mention / touch data``→ Redis STRINGs (full JSON, keyed by source id)

2. **Cognee Cloud** (background task, non-blocking) — a rich text document
   ingested into ``repo_{owner}_{repo}_profiles`` so the profile is queryable
   via natural language: *"what has @alice been mentioned about this week?"*

Redis key schema
----------------
devbrain:pr:users:{safe_repo}                         SET    known usernames
devbrain:pr:files:{safe_repo}:{user}                  SET    owned file paths
devbrain:pr:prs:{safe_repo}:{user}                    SET    reviewed PR numbers
devbrain:pr:mentions:{safe_repo}:{user}               ZSET   member="{type}:{id}"
devbrain:pr:mdata:{safe_repo}:{user}:{type}:{id}      STRING JSON of mention
devbrain:pr:touches:{safe_repo}:{user}                ZSET   member="{safe_path}::{sha7}"
devbrain:pr:tdata:{safe_repo}:{user}:{safe_path}::{sha7}  STRING JSON of touch event
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis

from backend.config import dataset_name as _dataset_name
from backend.config import settings, split_repo

logger = logging.getLogger("devbrain.changelog.profile")

# ---------------------------------------------------------------------------
# Mention scanning
# ---------------------------------------------------------------------------

_MENTION_RE = re.compile(r"@([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?)")
_CONTEXT_WINDOW = 80


def scan_mentions(text: str) -> set[str]:
    """Return lowercase GitHub usernames @mentioned in *text*."""
    if not text:
        return set()
    return {m.lower() for m in _MENTION_RE.findall(text)}


def _context_snippet(text: str, username: str) -> str:
    needle = f"@{username.lower()}"
    idx = text.lower().find(needle)
    if idx == -1:
        return text[:_CONTEXT_WINDOW].replace("\n", " ")
    start = max(0, idx - 30)
    end = min(len(text), idx + _CONTEXT_WINDOW)
    snippet = text[start:end].replace("\n", " ").strip()
    return f"{'...' if start > 0 else ''}{snippet}{'...' if end < len(text) else ''}"


# ---------------------------------------------------------------------------
# Redis connection — lazy singleton
# ---------------------------------------------------------------------------

_pool: Optional[aioredis.Redis] = None
_pool_lock: asyncio.Lock | None = None
_PFX = "devbrain:pr"


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


def _safe(repo: str) -> str:
    return repo.replace("/", ":").replace("-", "_").lower()


# ---------------------------------------------------------------------------
# Redis key builders
# ---------------------------------------------------------------------------


def _k_users(repo: str) -> str:
    return f"{_PFX}:users:{_safe(repo)}"


def _k_files(repo: str, user: str) -> str:
    return f"{_PFX}:files:{_safe(repo)}:{user.lower()}"


def _k_prs(repo: str, user: str) -> str:
    return f"{_PFX}:prs:{_safe(repo)}:{user.lower()}"


def _k_mentions(repo: str, user: str) -> str:
    return f"{_PFX}:mentions:{_safe(repo)}:{user.lower()}"


def _k_mdata(repo: str, user: str, source_type: str, source_id: str) -> str:
    return f"{_PFX}:mdata:{_safe(repo)}:{user.lower()}:{source_type}:{source_id}"


def _k_touches(repo: str, user: str) -> str:
    return f"{_PFX}:touches:{_safe(repo)}:{user.lower()}"


def _k_tdata(repo: str, user: str, filepath: str, sha7: str) -> str:
    safe_path = filepath.replace(":", "_").replace("/", "|")
    return f"{_PFX}:tdata:{_safe(repo)}:{user.lower()}:{safe_path}::{sha7}"


# ---------------------------------------------------------------------------
# Public read helpers — used by user_updates.py
# ---------------------------------------------------------------------------


async def get_owned_files(repo: str, username: str) -> set[str]:
    r = await _redis()
    return await r.smembers(_k_files(repo, username))  # type: ignore[return-value]


async def get_reviewed_prs(repo: str, username: str) -> set[int]:
    r = await _redis()
    members: set[str] = await r.smembers(_k_prs(repo, username))  # type: ignore[assignment]
    return {int(m) for m in members if m.isdigit()}


async def get_mentions_since(
    repo: str, username: str, since: Optional[datetime]
) -> list[dict]:
    """Return mention dicts with timestamp > since, sorted oldest-first."""
    r = await _redis()
    min_score = since.timestamp() if since else 0
    members: list[str] = await r.zrangebyscore(  # type: ignore[assignment]
        _k_mentions(repo, username), min_score, "+inf"
    )
    results: list[dict] = []
    for member in members:
        parts = member.split(":", 1)
        if len(parts) != 2:
            continue
        source_type, source_id = parts
        raw = await r.get(_k_mdata(repo, username, source_type, source_id))
        if raw:
            try:
                results.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
    return results


async def get_file_touches_since(
    repo: str, username: str, since: Optional[datetime]
) -> list[dict]:
    """Return file-touch dicts with timestamp > since, sorted oldest-first."""
    r = await _redis()
    min_score = since.timestamp() if since else 0
    members: list[str] = await r.zrangebyscore(  # type: ignore[assignment]
        _k_touches(repo, username), min_score, "+inf"
    )
    results: list[dict] = []
    for member in members:
        parts = member.rsplit("::", 1)
        if len(parts) != 2:
            continue
        safe_path, sha7 = parts
        filepath = safe_path.replace("|", "/")
        raw = await r.get(_k_tdata(repo, username, filepath, sha7))
        if raw:
            try:
                results.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
    return results


async def list_known_users(repo: str) -> list[str]:
    """Return all usernames that have a profile entry for *repo*."""
    r = await _redis()
    return list(await r.smembers(_k_users(repo)))  # type: ignore[misc, arg-type]


# ---------------------------------------------------------------------------
# Cognee Cloud ingestion — rich text documents (background tasks)
# ---------------------------------------------------------------------------


def _profile_dataset(repo: str) -> str:
    owner, name = split_repo(repo)
    return _dataset_name(owner, name, "profiles")


async def _cognee_remember(text: str, dataset: str) -> None:
    """Ingest *text* into Cognee Cloud. Errors are logged, never raised."""
    try:
        from backend.memory import client as memory

        await memory.remember(text, dataset)
        logger.debug("Cognee profile ingestion complete (dataset=%s)", dataset)
    except Exception as exc:
        logger.warning("Cognee profile ingestion failed: %s", exc)


def _mention_text(
    repo: str,
    username: str,
    source_type: str,
    source_id: str,
    source_url: str,
    context: str,
    mentioned_by: str,
    timestamp: str,
) -> str:
    labels = {
        "commit_message": "commit",
        "pr_body": "pull request description",
        "pr_review": "pull request review",
        "pr_review_comment": "inline review comment",
        "issue_body": "issue",
    }
    return (
        f"# @mention of @{username} in {repo}\n\n"
        f"Mentioned by: @{mentioned_by}\n"
        f"Where: {labels.get(source_type, source_type)} (id: {source_id})\n"
        f"URL: {source_url}\n"
        f"When: {timestamp}\n\n"
        f"## Context\n{context}\n"
    )


def _touch_text(
    repo: str,
    owner_username: str,
    filepath: str,
    changed_by: str,
    commit_sha: str,
    commit_url: str,
    commit_message: str,
    timestamp: str,
) -> str:
    return (
        f"# File owned by @{owner_username} modified in {repo}\n\n"
        f"File: {filepath}\n"
        f"Owner: @{owner_username}\n"
        f"Changed by: @{changed_by}\n"
        f"Commit: {commit_sha[:7]} ({commit_url})\n"
        f"Message: {commit_message}\n"
        f"When: {timestamp}\n\n"
        f"@{owner_username} has previously committed to {filepath}. "
        f"@{changed_by} modified it in this commit.\n"
    )


# ---------------------------------------------------------------------------
# Internal write helpers
# ---------------------------------------------------------------------------


async def _record_mention(
    repo: str,
    username: str,
    source_type: str,
    source_id: str,
    source_url: str,
    context: str,
    mentioned_by: str,
    timestamp: datetime,
) -> bool:
    """Write a mention to Redis. Returns True if it was new (not a duplicate)."""
    r = await _redis()
    member = f"{source_type}:{source_id}"
    added = await r.zadd(
        _k_mentions(repo, username), {member: timestamp.timestamp()}, nx=True
    )
    if not added:
        return False
    data = {
        "source_type": source_type,
        "source_id": source_id,
        "source_url": source_url,
        "context": context,
        "mentioned_by": mentioned_by,
        "timestamp": timestamp.isoformat(),
    }
    await r.set(_k_mdata(repo, username, source_type, source_id), json.dumps(data))
    await r.sadd(_k_users(repo), username.lower())  # type: ignore[misc]
    return True


async def _record_file_touch(
    repo: str,
    username: str,
    filepath: str,
    changed_by: str,
    commit_sha: str,
    commit_url: str,
    commit_message: str,
    timestamp: datetime,
) -> bool:
    """Write a file-touch event to Redis. Returns True if it was new."""
    r = await _redis()
    sha7 = commit_sha[:7]
    safe_path = filepath.replace(":", "_").replace("/", "|")
    member = f"{safe_path}::{sha7}"
    added = await r.zadd(
        _k_touches(repo, username), {member: timestamp.timestamp()}, nx=True
    )
    if not added:
        return False
    data = {
        "filepath": filepath,
        "changed_by": changed_by,
        "commit_sha": commit_sha,
        "commit_url": commit_url,
        "commit_message": commit_message,
        "timestamp": timestamp.isoformat(),
    }
    await r.set(_k_tdata(repo, username, filepath, sha7), json.dumps(data))
    return True


# ---------------------------------------------------------------------------
# Core scanning logic
# ---------------------------------------------------------------------------


async def _scan_and_record_mentions(
    repo: str,
    text: str,
    source_type: str,
    source_id: str,
    source_url: str,
    mentioned_by: str,
    timestamp: datetime,
    exclude_user: Optional[str] = None,
) -> None:
    mentioned = scan_mentions(text)
    if exclude_user:
        mentioned.discard(exclude_user.lower())
    dataset = _profile_dataset(repo)
    for username in mentioned:
        context = _context_snippet(text, username)
        is_new = await _record_mention(
            repo=repo,
            username=username,
            source_type=source_type,
            source_id=source_id,
            source_url=source_url,
            context=context,
            mentioned_by=mentioned_by,
            timestamp=timestamp,
        )
        if is_new:
            asyncio.create_task(
                _cognee_remember(
                    _mention_text(
                        repo,
                        username,
                        source_type,
                        source_id,
                        source_url,
                        context,
                        mentioned_by,
                        timestamp.isoformat(),
                    ),
                    dataset,
                )
            )
            logger.debug(
                "@%s mentioned (%s %s) → Cognee queued",
                username,
                source_type,
                source_id,
            )


async def _check_file_ownership(
    repo: str,
    changed_files: list[str],
    changed_by: str,
    commit_sha: str,
    commit_url: str,
    commit_message: str,
    timestamp: datetime,
) -> None:
    if not changed_files:
        return
    changed_set = set(changed_files)
    dataset = _profile_dataset(repo)
    for username in await list_known_users(repo):
        if username.lower() == changed_by.lower():
            continue
        owned = await get_owned_files(repo, username)
        for filepath in owned & changed_set:
            is_new = await _record_file_touch(
                repo=repo,
                username=username,
                filepath=filepath,
                changed_by=changed_by,
                commit_sha=commit_sha,
                commit_url=commit_url,
                commit_message=commit_message,
                timestamp=timestamp,
            )
            if is_new:
                asyncio.create_task(
                    _cognee_remember(
                        _touch_text(
                            repo,
                            username,
                            filepath,
                            changed_by,
                            commit_sha,
                            commit_url,
                            commit_message,
                            timestamp.isoformat(),
                        ),
                        dataset,
                    )
                )
                logger.debug(
                    "File-touch @%s: %s by @%s → Cognee queued",
                    username,
                    filepath,
                    changed_by,
                )


def _parse_ts(raw: str) -> datetime:
    try:
        dt = datetime.fromisoformat(raw)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Public update functions — called from webhook handlers in main.py
# ---------------------------------------------------------------------------


async def update_from_push(repo: str, payload: dict) -> None:
    """Process a ``push`` event payload.

    - Adds changed files to the author's owned-files set in Redis.
    - Scans each commit message for @mentions.
    - Notifies owners of any files touched by someone else.
    """
    r = await _redis()
    for commit in payload.get("commits", []):
        sha: str = commit.get("id", "")
        if not sha:
            continue
        message: str = commit.get("message", "")
        url: str = commit.get("url", "")
        timestamp = _parse_ts(commit.get("timestamp") or "")
        author_info = commit.get("author", {})
        author: str = (
            author_info.get("username") or author_info.get("name") or "unknown"
        ).lower()
        changed_files: list[str] = (
            commit.get("added", [])
            + commit.get("modified", [])
            + commit.get("removed", [])
        )

        if author != "unknown" and changed_files:
            await r.sadd(_k_files(repo, author), *changed_files)  # type: ignore[misc]
            await r.sadd(_k_users(repo), author)  # type: ignore[misc]

        if message:
            await _scan_and_record_mentions(
                repo=repo,
                text=message,
                source_type="commit_message",
                source_id=sha,
                source_url=url,
                mentioned_by=author,
                timestamp=timestamp,
                exclude_user=author,
            )

        await _check_file_ownership(
            repo=repo,
            changed_files=changed_files,
            changed_by=author,
            commit_sha=sha,
            commit_url=url,
            commit_message=message.split("\n")[0],
            timestamp=timestamp,
        )


async def update_from_pull_request(repo: str, payload: dict) -> None:
    """Process a ``pull_request`` opened/edited event — scan body for @mentions."""
    pr = payload.get("pull_request", {})
    pr_number: int = pr.get("number", 0)
    if not pr_number:
        return
    author: str = ((pr.get("user") or {}).get("login") or "unknown").lower()
    url: str = pr.get("html_url", "")
    timestamp = _parse_ts(pr.get("updated_at") or "")
    text = f"{pr.get('title', '')} {pr.get('body') or ''}"
    await _scan_and_record_mentions(
        repo=repo,
        text=text,
        source_type="pr_body",
        source_id=str(pr_number),
        source_url=url,
        mentioned_by=author,
        timestamp=timestamp,
        exclude_user=author,
    )


async def update_from_pr_review(repo: str, payload: dict) -> None:
    """Process a ``pull_request_review`` event — record reviewer + scan body."""
    review = payload.get("review", {})
    pr_number: int = (payload.get("pull_request") or {}).get("number", 0)
    reviewer: str = ((review.get("user") or {}).get("login") or "unknown").lower()
    url: str = review.get("html_url", "")
    timestamp = _parse_ts(review.get("submitted_at") or "")
    body: str = review.get("body") or ""

    if reviewer != "unknown" and pr_number:
        r = await _redis()
        await r.sadd(_k_prs(repo, reviewer), str(pr_number))  # type: ignore[misc]
        await r.sadd(_k_users(repo), reviewer)  # type: ignore[misc]

    if body:
        await _scan_and_record_mentions(
            repo=repo,
            text=body,
            source_type="pr_review",
            source_id=str(pr_number),
            source_url=url,
            mentioned_by=reviewer,
            timestamp=timestamp,
            exclude_user=reviewer,
        )


async def update_from_pr_review_comment(repo: str, payload: dict) -> None:
    """Process a ``pull_request_review_comment`` event — scan body for @mentions."""
    comment = payload.get("comment", {})
    body: str = comment.get("body") or ""
    if not body:
        return
    author: str = ((comment.get("user") or {}).get("login") or "unknown").lower()
    url: str = comment.get("html_url", "")
    comment_id: str = str(comment.get("id", ""))
    timestamp = _parse_ts(comment.get("created_at") or "")
    await _scan_and_record_mentions(
        repo=repo,
        text=body,
        source_type="pr_review_comment",
        source_id=comment_id,
        source_url=url,
        mentioned_by=author,
        timestamp=timestamp,
        exclude_user=author,
    )


async def update_from_issue(repo: str, payload: dict) -> None:
    """Process an ``issues`` opened event — scan body for @mentions."""
    issue = payload.get("issue", {})
    issue_number: int = issue.get("number", 0)
    if not issue_number:
        return
    author: str = ((issue.get("user") or {}).get("login") or "unknown").lower()
    url: str = issue.get("html_url", "")
    timestamp = _parse_ts(issue.get("updated_at") or "")
    text = f"{issue.get('title', '')} {issue.get('body') or ''}"
    await _scan_and_record_mentions(
        repo=repo,
        text=text,
        source_type="issue_body",
        source_id=str(issue_number),
        source_url=url,
        mentioned_by=author,
        timestamp=timestamp,
        exclude_user=author,
    )


async def backfill_profiles(repo: str) -> None:
    """Historically backfill file ownership, mentions, and touches from commits and PRs."""
    owner, name = split_repo(repo)
    logger.info("Starting historical profile backfill for %s", repo)
    
    r = await _redis()
    
    try:
        from backend.config import github_client
        gh = github_client()
        gh_repo = await asyncio.to_thread(gh.get_repo, repo)
        
        # 1. Commits (build file ownership and touches)
        commits = await asyncio.to_thread(lambda: list(gh_repo.get_commits()))
        # Reverse to process chronologically (correct ownership progression)
        commits.reverse()
        
        for commit in commits:
            sha = commit.sha
            msg = commit.commit.message
            author = (commit.author.login if commit.author else "unknown").lower()
            date = commit.commit.author.date
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            url = commit.html_url
            
            # Changed files
            files = [f.filename for f in commit.files]
            
            if author != "unknown" and files:
                await r.sadd(_k_files(repo, author), *files)
                await r.sadd(_k_users(repo), author)
                
            # Scan message for mentions
            mentioned = scan_mentions(msg)
            for username in mentioned:
                if username.lower() != author:
                    context = _context_snippet(msg, username)
                    await _record_mention(
                        repo=repo,
                        username=username,
                        source_type="commit_message",
                        source_id=sha,
                        source_url=url,
                        context=context,
                        mentioned_by=author,
                        timestamp=date,
                    )
                    
            # Check touches by others
            known_users = [u.lower() for u in await r.smembers(_k_users(repo))]
            for other_user in known_users:
                if other_user == author:
                    continue
                owned = await get_owned_files(repo, other_user)
                overlapping = set(files) & set(owned)
                for filepath in overlapping:
                    await _record_file_touch(
                        repo=repo,
                        username=other_user,
                        filepath=filepath,
                        changed_by=author,
                        commit_sha=sha,
                        commit_url=url,
                        commit_message=msg.split("\n")[0],
                        timestamp=date,
                    )
                    
        # 2. PRs (extract PR description/review/comment mentions)
        pulls = await asyncio.to_thread(lambda: list(gh_repo.get_pulls(state="all")))
        for pr in pulls:
            pr_number = pr.number
            author = (pr.user.login if pr.user else "unknown").lower()
            pr_url = pr.html_url
            pr_date = pr.created_at
            if pr_date.tzinfo is None:
                pr_date = pr_date.replace(tzinfo=timezone.utc)
                
            # PR body
            body_text = f"{pr.title} {pr.body or ''}"
            mentioned = scan_mentions(body_text)
            for username in mentioned:
                if username.lower() != author:
                    context = _context_snippet(body_text, username)
                    await _record_mention(
                        repo=repo,
                        username=username,
                        source_type="pr_body",
                        source_id=str(pr_number),
                        source_url=pr_url,
                        context=context,
                        mentioned_by=author,
                        timestamp=pr_date,
                    )
                    
            # Issue comments
            comments = await asyncio.to_thread(lambda: list(pr.get_issue_comments()))
            for comment in comments:
                c_author = (comment.user.login if comment.user else "unknown").lower()
                c_date = comment.created_at
                if c_date.tzinfo is None:
                    c_date = c_date.replace(tzinfo=timezone.utc)
                c_text = comment.body or ""
                mentioned = scan_mentions(c_text)
                for username in mentioned:
                    if username.lower() != c_author:
                        context = _context_snippet(c_text, username)
                        await _record_mention(
                            repo=repo,
                            username=username,
                            source_type="pr_review_comment",
                            source_id=str(comment.id),
                            source_url=comment.html_url,
                            context=context,
                            mentioned_by=c_author,
                            timestamp=c_date,
                        )
                        
            # PR reviews
            reviews = await asyncio.to_thread(lambda: list(pr.get_reviews()))
            for review in reviews:
                reviewer = (review.user.login if review.user else "unknown").lower()
                r_date = review.submitted_at or pr_date
                if r_date.tzinfo is None:
                    r_date = r_date.replace(tzinfo=timezone.utc)
                r_text = review.body or ""
                
                if reviewer != "unknown":
                    await r.sadd(_k_prs(repo, reviewer), str(pr_number))
                    await r.sadd(_k_users(repo), reviewer)
                    
                mentioned = scan_mentions(r_text)
                for username in mentioned:
                    if username.lower() != reviewer:
                        context = _context_snippet(r_text, username)
                        await _record_mention(
                            repo=repo,
                            username=username,
                            source_type="pr_review",
                            source_id=str(pr_number),
                            source_url=review.html_url or pr_url,
                            context=context,
                            mentioned_by=reviewer,
                            timestamp=r_date,
                        )
        logger.info("Historical profile backfill for %s completed successfully", repo)
    except Exception as e:
        logger.error("Failed to backfill profiles for %s: %s", repo, e)
