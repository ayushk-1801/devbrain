"""Global changelog generator.

Fetches every event (commits, PRs, issues, releases) that occurred in a GitHub
repo *since the last generation run* and writes a structured Markdown file.

The generated file is saved to:
    ``.devbrain/changelogs/GLOBAL_CHANGELOG_{safe_repo}.md``

It also updates the ``last_global_sync`` timestamp so the next run only returns
genuinely new events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.changelog import tracker
from backend.config import github_client

logger = logging.getLogger("devbrain.changelog.global")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CommitEntry:
    sha: str
    short_sha: str
    message: str
    author: str
    url: str
    timestamp: datetime


@dataclass
class PREntry:
    number: int
    title: str
    author: str
    state: str  # "open" | "merged" | "closed"
    url: str
    created_at: datetime
    merged_at: Optional[datetime] = None
    labels: list[str] = field(default_factory=list)


@dataclass
class IssueEntry:
    number: int
    title: str
    author: str
    state: str  # "open" | "closed"
    url: str
    created_at: datetime
    closed_at: Optional[datetime] = None
    assignees: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)


@dataclass
class ReleaseEntry:
    tag: str
    name: str
    author: str
    url: str
    published_at: datetime
    prerelease: bool = False


@dataclass
class GlobalChangelog:
    repo: str
    since: Optional[datetime]
    generated_at: datetime
    commits: list[CommitEntry] = field(default_factory=list)
    pull_requests: list[PREntry] = field(default_factory=list)
    issues: list[IssueEntry] = field(default_factory=list)
    releases: list[ReleaseEntry] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.commits or self.pull_requests or self.issues or self.releases)

    def total_events(self) -> int:
        return (
            len(self.commits)
            + len(self.pull_requests)
            + len(self.issues)
            + len(self.releases)
        )


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------


def _safe_repo_name(repo: str) -> str:
    return repo.replace("/", "_").replace("-", "_").lower()


def _fetch_commits(gh_repo, since: Optional[datetime]) -> list[CommitEntry]:
    entries: list[CommitEntry] = []
    kwargs: dict = {}
    if since:
        kwargs["since"] = since
    try:
        for c in gh_repo.get_commits(**kwargs):
            commit = c.commit
            author_name = (
                c.author.login
                if c.author
                else (commit.author.name if commit.author else "unknown")
            )
            entries.append(
                CommitEntry(
                    sha=c.sha,
                    short_sha=c.sha[:7],
                    message=commit.message.split("\n")[0],  # subject only
                    author=author_name,
                    url=c.html_url,
                    timestamp=commit.author.date.replace(tzinfo=timezone.utc)
                    if commit.author and commit.author.date
                    else datetime.now(timezone.utc),
                )
            )
            if len(entries) >= 100:  # safety cap
                break
    except Exception as exc:
        logger.warning("Failed to fetch commits: %s", exc)
    return entries


def _fetch_prs(gh_repo, since: Optional[datetime]) -> list[PREntry]:
    entries: list[PREntry] = []
    try:
        # Get recently updated PRs (both open and closed)
        for pr in gh_repo.get_pulls(state="all", sort="updated", direction="desc"):
            if since and pr.updated_at.replace(tzinfo=timezone.utc) < since:
                break
            state = "merged" if pr.merged else pr.state
            entries.append(
                PREntry(
                    number=pr.number,
                    title=pr.title,
                    author=pr.user.login if pr.user else "unknown",
                    state=state,
                    url=pr.html_url,
                    created_at=pr.created_at.replace(tzinfo=timezone.utc),
                    merged_at=pr.merged_at.replace(tzinfo=timezone.utc)
                    if pr.merged_at
                    else None,
                    labels=[lbl.name for lbl in pr.labels],
                )
            )
            if len(entries) >= 50:
                break
    except Exception as exc:
        logger.warning("Failed to fetch PRs: %s", exc)
    return entries


def _fetch_issues(gh_repo, since: Optional[datetime]) -> list[IssueEntry]:
    entries: list[IssueEntry] = []
    kwargs: dict = {"state": "all", "sort": "updated", "direction": "desc"}
    if since:
        kwargs["since"] = since
    try:
        for issue in gh_repo.get_issues(**kwargs):
            if issue.pull_request:
                continue  # skip PRs that appear as issues
            entries.append(
                IssueEntry(
                    number=issue.number,
                    title=issue.title,
                    author=issue.user.login if issue.user else "unknown",
                    state=issue.state,
                    url=issue.html_url,
                    created_at=issue.created_at.replace(tzinfo=timezone.utc),
                    closed_at=issue.closed_at.replace(tzinfo=timezone.utc)
                    if issue.closed_at
                    else None,
                    assignees=[a.login for a in issue.assignees],
                    labels=[lbl.name for lbl in issue.labels],
                )
            )
            if len(entries) >= 50:
                break
    except Exception as exc:
        logger.warning("Failed to fetch issues: %s", exc)
    return entries


def _fetch_releases(gh_repo, since: Optional[datetime]) -> list[ReleaseEntry]:
    entries: list[ReleaseEntry] = []
    try:
        for rel in gh_repo.get_releases():
            if (
                since
                and rel.published_at
                and rel.published_at.replace(tzinfo=timezone.utc) < since
            ):
                break
            entries.append(
                ReleaseEntry(
                    tag=rel.tag_name,
                    name=rel.title or rel.tag_name,
                    author=rel.author.login if rel.author else "unknown",
                    url=rel.html_url,
                    published_at=rel.published_at.replace(tzinfo=timezone.utc)
                    if rel.published_at
                    else datetime.now(timezone.utc),
                    prerelease=rel.prerelease,
                )
            )
            if len(entries) >= 20:
                break
    except Exception as exc:
        logger.warning("Failed to fetch releases: %s", exc)
    return entries


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def _render_markdown(cl: GlobalChangelog) -> str:
    repo = cl.repo
    since_str = (
        cl.since.strftime("%Y-%m-%d %H:%M UTC") if cl.since else "beginning of time"
    )
    now_str = cl.generated_at.strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"# 📋 Global Changelog — `{repo}`",
        "",
        f"**Period:** {since_str} → {now_str}  ",
        f"**Total events:** {cl.total_events()}",
        "",
        "---",
        "",
    ]

    # --- Releases ---
    if cl.releases:
        lines += [f"## 🚀 Releases ({len(cl.releases)})", ""]
        for r in cl.releases:
            pre = " *(pre-release)*" if r.prerelease else ""
            lines.append(
                f"- **[{r.tag}]({r.url})** — {r.name}{pre}  "
                f"by @{r.author}  "
                f"· {r.published_at.strftime('%Y-%m-%d')}"
            )
        lines.append("")

    # --- Pull Requests ---
    if cl.pull_requests:
        state_emoji = {"merged": "🔀", "open": "🟢", "closed": "🔴"}
        lines += [f"## 🔀 Pull Requests ({len(cl.pull_requests)})", ""]
        for pr in cl.pull_requests:
            emoji = state_emoji.get(pr.state, "❓")
            label_str = f" `{'` `'.join(pr.labels)}`" if pr.labels else ""
            lines.append(
                f"- {emoji} **[#{pr.number}]({pr.url})** {pr.title}  "
                f"by @{pr.author}{label_str}  "
                f"· *{pr.state}* · {pr.created_at.strftime('%Y-%m-%d')}"
            )
        lines.append("")

    # --- Issues ---
    if cl.issues:
        lines += [f"## 🐛 Issues ({len(cl.issues)})", ""]
        for iss in cl.issues:
            emoji = "✅" if iss.state == "closed" else "🔵"
            assignee_str = f" → @{', @'.join(iss.assignees)}" if iss.assignees else ""
            label_str = f" `{'` `'.join(iss.labels)}`" if iss.labels else ""
            lines.append(
                f"- {emoji} **[#{iss.number}]({iss.url})** {iss.title}  "
                f"by @{iss.author}{assignee_str}{label_str}  "
                f"· *{iss.state}* · {iss.created_at.strftime('%Y-%m-%d')}"
            )
        lines.append("")

    # --- Commits ---
    if cl.commits:
        lines += [f"## 📝 Commits ({len(cl.commits)})", ""]
        for c in cl.commits:
            lines.append(
                f"- [`{c.short_sha}`]({c.url}) {c.message}  "
                f"by @{c.author} · {c.timestamp.strftime('%Y-%m-%d')}"
            )
        lines.append("")

    if cl.is_empty:
        lines += ["*No new events since the last changelog generation.*", ""]

    lines += [
        "---",
        f"*Generated by DevBrain on {now_str}*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def generate_global_changelog(
    owner: str,
    repo: str,
    force_since: Optional[datetime] = None,
) -> tuple[GlobalChangelog, Path]:
    """Fetch all events since the last run and write the global changelog file.

    Parameters
    ----------
    owner, repo:
        GitHub owner and repository name.
    force_since:
        Override the stored timestamp with a specific datetime (useful for
        backfilling a specific window).

    Returns
    -------
    (GlobalChangelog, Path)
        The structured changelog object and the path to the written .md file.
    """
    full_repo = f"{owner}/{repo}"
    since = force_since or await tracker.get_last_global_sync(full_repo)
    generated_at = datetime.now(timezone.utc)

    logger.info("Generating global changelog for %s (since=%s)", full_repo, since)

    gh = github_client()
    gh_repo = gh.get_repo(full_repo)

    changelog = GlobalChangelog(
        repo=full_repo,
        since=since,
        generated_at=generated_at,
        commits=_fetch_commits(gh_repo, since),
        pull_requests=_fetch_prs(gh_repo, since),
        issues=_fetch_issues(gh_repo, since),
        releases=_fetch_releases(gh_repo, since),
    )

    # Persist the markdown file
    safe = _safe_repo_name(full_repo)
    md_path = tracker.changelogs_dir() / f"GLOBAL_CHANGELOG_{safe}.md"
    md_path.write_text(_render_markdown(changelog), encoding="utf-8")

    # Update the watermark in Redis
    await tracker.set_last_global_sync(full_repo, generated_at)

    logger.info(
        "Global changelog written to %s (%d events)", md_path, changelog.total_events()
    )
    return changelog, md_path


def get_global_changelog_path(owner: str, repo: str) -> Optional[Path]:
    """Return the path to the existing global changelog file, or None."""
    safe = _safe_repo_name(f"{owner}/{repo}")
    path = tracker.changelogs_dir() / f"GLOBAL_CHANGELOG_{safe}.md"
    return path if path.exists() else None
