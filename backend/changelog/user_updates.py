"""User-specific update digest generator.

Uses the persisted UserProfile (built incrementally by ``profile.py`` from
webhook events) to produce a digest with **zero live GitHub API calls** for the
user-specific parts.

What surfaces in a user's digest
---------------------------------
1. **Their commits** — commits authored by the user in the current window.
2. **Their PRs** — PRs they opened, *plus PRs they reviewed* (from profile).
3. **Their issues** — issues they created or are assigned to.
4. **@Mentions** — every place someone explicitly tagged ``@username`` in a
   commit message, PR body, PR review, inline review comment, or issue body.
   Includes the text context so the user can see *why* they were mentioned.
5. **Files you own that changed** — files the user has previously committed to
   that were modified by *someone else*.  Populated incrementally by the push
   webhook handler, so no history re-scan is ever needed.

Generated file
--------------
``.devbrain/changelogs/USER_UPDATES_{username}_{safe_repo}.md``
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.changelog import tracker
from backend.changelog.global_changelog import (
    CommitEntry,
    GlobalChangelog,
    IssueEntry,
    PREntry,
    ReleaseEntry,
    fetch_commits,
    fetch_issues,
    fetch_prs,
    fetch_releases,
    safe_repo_name,
)
from backend.changelog.profile import (
    get_file_touches_since,
    get_mentions_since,
    get_reviewed_prs,
)
from backend.config import github_client

logger = logging.getLogger("devbrain.changelog.user")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class MentionUpdate:
    """An explicit @mention of the user somewhere in the repo."""

    source_type: str  # "commit_message" | "pr_body" | "pr_review" | "pr_review_comment" | "issue_body"
    source_id: str  # PR/issue number or commit SHA
    source_url: str
    context: str  # ~160-char snippet showing the mention in context
    mentioned_by: str  # GitHub login of who wrote the text
    timestamp: datetime

    @property
    def source_label(self) -> str:
        labels = {
            "commit_message": "commit",
            "pr_body": "PR description",
            "pr_review": "PR review",
            "pr_review_comment": "review comment",
            "issue_body": "issue",
        }
        return labels.get(self.source_type, self.source_type)


@dataclass
class TouchedFileActivity:
    """A file the user owns that was changed by someone else."""

    filepath: str
    changed_by: str
    commit_sha: str
    commit_url: str
    commit_message: str
    timestamp: datetime


@dataclass
class UserUpdates:
    repo: str
    username: str
    since: Optional[datetime]
    generated_at: datetime
    my_commits: list[CommitEntry] = field(default_factory=list)
    my_prs: list[PREntry] = field(default_factory=list)
    my_issues: list[IssueEntry] = field(default_factory=list)
    mentions: list[MentionUpdate] = field(default_factory=list)
    touched_files_activity: list[TouchedFileActivity] = field(default_factory=list)
    releases: list[ReleaseEntry] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (
            self.my_commits
            or self.my_prs
            or self.my_issues
            or self.mentions
            or self.touched_files_activity
            or self.releases
        )

    def total_events(self) -> int:
        return (
            len(self.my_commits)
            + len(self.my_prs)
            + len(self.my_issues)
            + len(self.mentions)
            + len(self.touched_files_activity)
            + len(self.releases)
        )


# ---------------------------------------------------------------------------
# Filtering helpers (fast — no API calls)
# ---------------------------------------------------------------------------


def _filter_commits(commits: list[CommitEntry], username: str) -> list[CommitEntry]:
    return [c for c in commits if c.author.lower() == username.lower()]


def _filter_prs(prs: list[PREntry], username: str) -> list[PREntry]:
    return [p for p in prs if p.author.lower() == username.lower()]


def _filter_issues(issues: list[IssueEntry], username: str) -> list[IssueEntry]:
    return [
        i
        for i in issues
        if i.author.lower() == username.lower()
        or any(a.lower() == username.lower() for a in i.assignees)
    ]


def _mentions_from_dicts(raw: list[dict]) -> list[MentionUpdate]:
    """Convert raw Redis dicts to MentionUpdate objects."""
    result: list[MentionUpdate] = []
    for m in raw:
        try:
            ts = datetime.fromisoformat(m["timestamp"])
            ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
        except (KeyError, ValueError):
            continue
        result.append(
            MentionUpdate(
                source_type=m.get("source_type", "unknown"),
                source_id=m.get("source_id", ""),
                source_url=m.get("source_url", ""),
                context=m.get("context", ""),
                mentioned_by=m.get("mentioned_by", "unknown"),
                timestamp=ts,
            )
        )
    return sorted(result, key=lambda x: x.timestamp, reverse=True)


def _touches_from_dicts(raw: list[dict]) -> list[TouchedFileActivity]:
    """Convert raw Redis dicts to TouchedFileActivity objects."""
    result: list[TouchedFileActivity] = []
    for f in raw:
        try:
            ts = datetime.fromisoformat(f["timestamp"])
            ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
        except (KeyError, ValueError):
            continue
        result.append(
            TouchedFileActivity(
                filepath=f.get("filepath", ""),
                changed_by=f.get("changed_by", "unknown"),
                commit_sha=f.get("commit_sha", ""),
                commit_url=f.get("commit_url", ""),
                commit_message=f.get("commit_message", ""),
                timestamp=ts,
            )
        )
    return sorted(result, key=lambda x: x.timestamp, reverse=True)


def _reviewed_prs_from_numbers(
    reviewed_numbers: set[int], all_prs: list[PREntry], username: str
) -> list[PREntry]:
    """Return PRs the user reviewed that appear in the current changelog window."""
    authored_numbers: set[int] = {
        p.number for p in all_prs if p.author.lower() == username.lower()
    }
    return [
        pr
        for pr in all_prs
        if pr.number in reviewed_numbers and pr.number not in authored_numbers
    ]


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

_SOURCE_EMOJI = {
    "commit_message": "📝",
    "pr_body": "🔀",
    "pr_review": "👁",
    "pr_review_comment": "💬",
    "issue_body": "🐛",
}


def _render_markdown(u: UserUpdates) -> str:
    since_str = u.since.strftime("%Y-%m-%d %H:%M UTC") if u.since else "the beginning"
    now_str = u.generated_at.strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        f"# 👤 Your Updates — @{u.username} on `{u.repo}`",
        "",
        f"**Since:** {since_str}  ",
        f"**Generated:** {now_str}  ",
        f"**New events for you:** {u.total_events()}",
        "",
        "---",
        "",
    ]

    # --- @Mentions (most actionable — show first) ---
    if u.mentions:
        lines += [f"## 🔔 You Were Mentioned ({len(u.mentions)})", ""]
        for m in u.mentions:
            emoji = _SOURCE_EMOJI.get(m.source_type, "💬")
            lines.append(
                f"- {emoji} **@{m.mentioned_by}** mentioned you in a "
                f"[{m.source_label}]({m.source_url})  "
                f"· {m.timestamp.strftime('%Y-%m-%d')}  "
            )
            lines.append(f"  > {m.context}")
        lines.append("")

    # --- User's commits ---
    if u.my_commits:
        lines += [f"## 📝 Your Commits ({len(u.my_commits)})", ""]
        for c in u.my_commits:
            lines.append(
                f"- [`{c.short_sha}`]({c.url}) {c.message}  "
                f"· {c.timestamp.strftime('%Y-%m-%d')}"
            )
        lines.append("")

    # --- User's PRs (authored + reviewed) ---
    if u.my_prs:
        state_emoji = {"merged": "🔀", "open": "🟢", "closed": "🔴"}
        lines += [f"## 🔀 Your Pull Requests ({len(u.my_prs)})", ""]
        for pr in u.my_prs:
            emoji = state_emoji.get(pr.state, "❓")
            lines.append(
                f"- {emoji} **[#{pr.number}]({pr.url})** {pr.title}  "
                f"· *{pr.state}* · {pr.created_at.strftime('%Y-%m-%d')}"
            )
        lines.append("")

    # --- User's issues ---
    if u.my_issues:
        lines += [f"## 🐛 Your Issues ({len(u.my_issues)})", ""]
        for iss in u.my_issues:
            emoji = "✅" if iss.state == "closed" else "🔵"
            role = (
                "assigned"
                if u.username.lower() in [a.lower() for a in iss.assignees]
                else "authored"
            )
            lines.append(
                f"- {emoji} **[#{iss.number}]({iss.url})** {iss.title}  "
                f"· *{iss.state}* · {role} · {iss.created_at.strftime('%Y-%m-%d')}"
            )
        lines.append("")

    # --- Files the user owns that were changed by others ---
    if u.touched_files_activity:
        lines += [
            f"## 📂 Your Files Changed by Others ({len(u.touched_files_activity)})",
            "",
            "_Files you've previously committed to that received new changes:_",
            "",
        ]
        for a in u.touched_files_activity:
            lines.append(
                f"- `{a.filepath}`  "
                f"changed by @{a.changed_by} in [`{a.commit_sha[:7]}`]({a.commit_url})  "
                f'· "{a.commit_message}" · {a.timestamp.strftime("%Y-%m-%d")}'
            )
        lines.append("")

    # --- Releases ---
    if u.releases:
        lines += [f"## 🚀 New Releases ({len(u.releases)})", ""]
        for r in u.releases:
            lines.append(
                f"- **[{r.tag}]({r.url})** — {r.name}  "
                f"by @{r.author} · {r.published_at.strftime('%Y-%m-%d')}"
            )
        lines.append("")

    if u.is_empty:
        lines += [
            "_No new events relevant to you since the last check. You're all caught up! 🎉_",
            "",
        ]

    lines += [
        "---",
        f"*Generated by DevBrain on {now_str}*  ",
        f"*Run `GET /changelog/user/{u.username}?repo={u.repo}&refresh=true` to refresh.*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def generate_user_updates(
    owner: str,
    repo: str,
    username: str,
    global_changelog: Optional[GlobalChangelog] = None,
    force_since: Optional[datetime] = None,
) -> tuple[UserUpdates, Path]:
    """Generate and persist a user-specific update digest.

    All user-specific data (mentions, reviewed PRs, file-touch events) is read
    from Redis — built incrementally by the webhook handlers, zero live GitHub
    API calls needed.  The Cognee Cloud copy is queryable via NL at any time.

    Parameters
    ----------
    owner, repo:
        GitHub owner and repository name.
    username:
        GitHub login of the user requesting their digest.
    global_changelog:
        Pass an already-fetched GlobalChangelog to avoid a GitHub re-fetch.
    force_since:
        Override the stored ``last_seen`` timestamp for backfilling.
    """
    full_repo = f"{owner}/{repo}"
    since = force_since or await tracker.get_last_user_seen(full_repo, username)
    generated_at = datetime.now(timezone.utc)

    logger.info(
        "Generating user updates for %s on %s (since=%s)", username, full_repo, since
    )

    # --- Global events (shared, fetched once from GitHub) ---
    if global_changelog is not None:
        all_commits = global_changelog.commits
        all_prs = global_changelog.pull_requests
        all_issues = global_changelog.issues
        all_releases = global_changelog.releases
    else:
        gh = await asyncio.to_thread(github_client)
        gh_repo = await asyncio.to_thread(gh.get_repo, full_repo)
        all_commits, all_prs, all_issues, all_releases = await asyncio.gather(
            asyncio.to_thread(fetch_commits, gh_repo, since),
            asyncio.to_thread(fetch_prs, gh_repo, since),
            asyncio.to_thread(fetch_issues, gh_repo, since),
            asyncio.to_thread(fetch_releases, gh_repo, since),
        )

    # --- User-specific data from Redis (no GitHub API calls) ---
    my_commits = _filter_commits(all_commits, username)
    my_issues = _filter_issues(all_issues, username)
    my_prs = _filter_prs(all_prs, username)

    # Reviewed PRs: read from Redis SET
    reviewed_numbers = await get_reviewed_prs(full_repo, username)
    for rp in _reviewed_prs_from_numbers(reviewed_numbers, all_prs, username):
        my_prs.append(rp)

    # @Mentions: read from Redis ZSET (filtered by since timestamp)
    mentions = _mentions_from_dicts(
        await get_mentions_since(full_repo, username, since)
    )

    # Files touched by others: read from Redis ZSET (filtered by since timestamp)
    touched = _touches_from_dicts(
        await get_file_touches_since(full_repo, username, since)
    )

    updates = UserUpdates(
        repo=full_repo,
        username=username,
        since=since,
        generated_at=generated_at,
        my_commits=my_commits,
        my_prs=my_prs,
        my_issues=my_issues,
        mentions=mentions,
        touched_files_activity=touched,
        releases=all_releases,
    )

    # Write the rendered Markdown file (local output artifact).
    safe_repo = safe_repo_name(full_repo)
    safe_user = username.lower().replace("-", "_")
    md_path = tracker.changelogs_dir() / f"USER_UPDATES_{safe_user}_{safe_repo}.md"
    md_path.write_text(_render_markdown(updates), encoding="utf-8")

    # Update the user's watermark in Redis.
    await tracker.set_last_user_seen(full_repo, username, generated_at)

    logger.info(
        "User updates for %s written to %s (%d events)",
        username,
        md_path,
        updates.total_events(),
    )
    return updates, md_path


def get_user_updates_path(owner: str, repo: str, username: str) -> Optional[Path]:
    """Return the path to the existing user updates file, or None."""
    safe_repo = safe_repo_name(f"{owner}/{repo}")
    safe_user = username.lower().replace("-", "_")
    path = tracker.changelogs_dir() / f"USER_UPDATES_{safe_user}_{safe_repo}.md"
    return path if path.exists() else None
