"""Notification dispatcher for the changelog subsystem.

Supports two notification channels:

1. **Webhook** — POST a JSON summary to a URL registered per user via
   ``POST /changelog/subscribe``.
2. **Log** — Always logs a summary at INFO level (useful as a fallback and
   during development).

Future channels (email, Slack, Discord) can be added here by implementing
the ``_notify_*`` pattern and wiring into ``dispatch()``.
"""

from __future__ import annotations

import logging

import httpx

from backend.changelog import tracker
from backend.changelog.global_changelog import GlobalChangelog
from backend.changelog.user_updates import UserUpdates

logger = logging.getLogger("devbrain.changelog.notifier")


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _global_summary(cl: GlobalChangelog) -> dict:
    return {
        "type": "global_changelog",
        "repo": cl.repo,
        "since": cl.since.isoformat() if cl.since else None,
        "generated_at": cl.generated_at.isoformat(),
        "total_events": cl.total_events(),
        "counts": {
            "commits": len(cl.commits),
            "pull_requests": len(cl.pull_requests),
            "issues": len(cl.issues),
            "releases": len(cl.releases),
        },
        "recent_prs": [
            {"number": p.number, "title": p.title, "state": p.state, "url": p.url}
            for p in cl.pull_requests[:5]
        ],
        "recent_releases": [
            {"tag": r.tag, "name": r.name, "url": r.url} for r in cl.releases[:3]
        ],
    }


def _user_summary(u: UserUpdates) -> dict:
    return {
        "type": "user_updates",
        "repo": u.repo,
        "username": u.username,
        "since": u.since.isoformat() if u.since else None,
        "generated_at": u.generated_at.isoformat(),
        "total_events": u.total_events(),
        "counts": {
            "my_commits": len(u.my_commits),
            "my_prs": len(u.my_prs),
            "my_issues": len(u.my_issues),
            "files_touched_by_others": len(u.touched_files_activity),
            "releases": len(u.releases),
        },
        "my_recent_prs": [
            {"number": p.number, "title": p.title, "state": p.state, "url": p.url}
            for p in u.my_prs[:5]
        ],
        "files_changed_by_others": [
            {
                "file": a.filepath,
                "by": a.changed_by,
                "commit": a.commit_sha[:7],
                "message": a.commit_message,
            }
            for a in u.touched_files_activity[:5]
        ],
    }


# ---------------------------------------------------------------------------
# Channel implementations
# ---------------------------------------------------------------------------


async def _notify_webhook(url: str, payload: dict) -> None:
    """POST the JSON payload to the webhook URL; log failures non-fatally."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "DevBrain/1.0",
                },
            )
            resp.raise_for_status()
            logger.info(
                "Webhook notification sent to %s (HTTP %s)", url, resp.status_code
            )
    except Exception as exc:
        logger.warning("Webhook notification to %s failed: %s", url, exc)


def _log_global(cl: GlobalChangelog) -> None:
    logger.info(
        "[GlobalChangelog] %s — %d events (commits=%d prs=%d issues=%d releases=%d) "
        "since %s",
        cl.repo,
        cl.total_events(),
        len(cl.commits),
        len(cl.pull_requests),
        len(cl.issues),
        len(cl.releases),
        cl.since,
    )


def _log_user(u: UserUpdates) -> None:
    logger.info(
        "[UserUpdates] @%s on %s — %d events (commits=%d prs=%d issues=%d files=%d) since %s",
        u.username,
        u.repo,
        u.total_events(),
        len(u.my_commits),
        len(u.my_prs),
        len(u.my_issues),
        len(u.touched_files_activity),
        u.since,
    )


# ---------------------------------------------------------------------------
# Public dispatchers
# ---------------------------------------------------------------------------


async def dispatch_global(cl: GlobalChangelog) -> None:
    """Log a summary of the global changelog.  Extend here for Slack/email."""
    _log_global(cl)


async def dispatch_user(repo: str, username: str, updates: UserUpdates) -> None:
    """Log a summary and POST to the user's webhook (if registered)."""
    _log_user(updates)
    webhook = await tracker.get_user_webhook(repo, username)
    if webhook:
        await _notify_webhook(webhook, _user_summary(updates))


async def dispatch_all_users(
    repo: str, cl: GlobalChangelog, user_updates_map: dict[str, UserUpdates]
) -> None:
    """Notify every subscribed user for a repo in one call."""
    await dispatch_global(cl)
    for username, updates in user_updates_map.items():
        await dispatch_user(repo, username, updates)
