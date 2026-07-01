"""PyGithub fetch helpers.

These functions talk to the GitHub API and return plain dicts. PyGithub objects
never leave this module, so the ingestion modules stay decoupled from the client
library and are easy to test with fixtures.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from backend.config import github_client

# ADR locations to probe, per AGENTS.md.
ADR_DIRS = ["docs/decisions", "adr", "docs/adr", ".decisions"]


def _get_repo(owner: str, repo: str):
    return github_client().get_repo(f"{owner}/{repo}")


def fetch_commits(owner: str, repo: str, since_days: Optional[int] = None) -> list[dict[str, Any]]:
    """Return commits as plain dicts, optionally limited to the last N days."""
    gh_repo = _get_repo(owner, repo)
    kwargs: dict[str, Any] = {}
    if since_days:
        kwargs["since"] = datetime.now(timezone.utc) - timedelta(days=since_days)

    out: list[dict[str, Any]] = []
    for commit in gh_repo.get_commits(**kwargs):
        out.append(_commit_to_dict(commit))
    return out


def fetch_commit(owner: str, repo: str, sha: str) -> dict[str, Any]:
    """Return a single commit (used by the push webhook for incremental ingest)."""
    gh_repo = _get_repo(owner, repo)
    return _commit_to_dict(gh_repo.get_commit(sha))


def _commit_to_dict(commit) -> dict[str, Any]:
    files = getattr(commit, "files", []) or []
    author = commit.commit.author
    return {
        "sha": commit.sha,
        "message": commit.commit.message,
        "author": author.name if author else "unknown",
        "author_email": author.email if author else "",
        "date": author.date.isoformat() if author and author.date else "",
        "files_changed": [f.filename for f in files],
        "diff_summary": [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
            }
            for f in files
        ],
    }


def fetch_pull_requests(
    owner: str, repo: str, since_days: Optional[int] = None
) -> list[dict[str, Any]]:
    """Return merged PRs as plain dicts, optionally limited to the last N days."""
    gh_repo = _get_repo(owner, repo)
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=since_days) if since_days else None
    )

    out: list[dict[str, Any]] = []
    for pr in gh_repo.get_pulls(state="closed", sort="updated", direction="desc"):
        if not pr.merged_at:
            continue
        if cutoff and pr.merged_at < cutoff:
            # Sorted by updated desc; once we pass the cutoff we can stop.
            break
        out.append(_pr_to_dict(pr))
    return out


def fetch_pull_request(owner: str, repo: str, number: int) -> dict[str, Any]:
    """Return a single PR (used by the pull_request webhook)."""
    gh_repo = _get_repo(owner, repo)
    return _pr_to_dict(gh_repo.get_pull(number))


def _pr_to_dict(pr) -> dict[str, Any]:
    review_comments = [
        {"author": c.user.login if c.user else "unknown", "body": c.body}
        for c in pr.get_review_comments()
    ]
    discussion_comments = [
        {"author": c.user.login if c.user else "unknown", "body": c.body}
        for c in pr.get_issue_comments()
    ]
    approvals = [
        r.user.login
        for r in pr.get_reviews()
        if r.state == "APPROVED" and r.user
    ]
    reviews = _extract_reviews(pr)
    return {
        "number": pr.number,
        "title": pr.title,
        "body": pr.body or "",
        "author": pr.user.login if pr.user else "unknown",
        "merged_at": pr.merged_at.isoformat() if pr.merged_at else "",
        "files_changed": [f.filename for f in pr.get_files()],
        "review_comments": review_comments,
        "discussion_comments": discussion_comments,
        "approvals": approvals,
        "reviews": reviews,
    }


def _extract_reviews(pr) -> list[dict[str, Any]]:
    """Extract full PR review summaries (APPROVED, REQUEST_CHANGES, COMMENT, etc.)."""
    reviews = []
    for r in pr.get_reviews():
        if not r.user:
            continue
        reviews.append({
            "author": r.user.login,
            "state": r.state,
            "body": r.body or "",
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else "",
        })
    return reviews


def fetch_issues(
    owner: str, repo: str, since_days: Optional[int] = None
) -> list[dict[str, Any]]:
    """Return issues (not PRs) as plain dicts, optionally limited to the last N days."""
    gh_repo = _get_repo(owner, repo)
    kwargs: dict[str, Any] = {"state": "all", "sort": "updated", "direction": "desc"}
    if since_days:
        kwargs["since"] = datetime.now(timezone.utc) - timedelta(days=since_days)

    out: list[dict[str, Any]] = []
    for issue in gh_repo.get_issues(**kwargs):
        # Issues API returns PRs too — skip them; PRs are covered by the prs dataset.
        if issue.pull_request is not None:
            continue
        out.append(_issue_to_dict(issue))
    return out


def fetch_issue(owner: str, repo: str, number: int) -> dict[str, Any]:
    """Return a single issue (used by the issues webhook)."""
    gh_repo = _get_repo(owner, repo)
    return _issue_to_dict(gh_repo.get_issue(number))


def _issue_to_dict(issue) -> dict[str, Any]:
    comments = [
        {"author": c.user.login if c.user else "unknown", "body": c.body}
        for c in issue.get_comments()
    ]
    return {
        "number": issue.number,
        "title": issue.title,
        "body": issue.body or "",
        "state": issue.state,
        "author": issue.user.login if issue.user else "unknown",
        "labels": [label.name for label in issue.labels],
        "created_at": issue.created_at.isoformat() if issue.created_at else "",
        "closed_at": issue.closed_at.isoformat() if issue.closed_at else "",
        "comments": comments,
    }


def fetch_pr_review_comment(owner: str, repo: str, comment_id: int) -> dict[str, Any]:
    """Return a single PR review comment (used by the pull_request_review_comment webhook)."""
    gh_repo = _get_repo(owner, repo)
    comment = gh_repo.get_pull_review_comment(comment_id)
    # Parse PR number from the pull_request_url field (ends with /pulls/<number>).
    pr_number = int(comment.pull_request_url.rstrip("/").split("/")[-1])
    return {
        "id": comment.id,
        "pr_number": pr_number,
        "author": comment.user.login if comment.user else "unknown",
        "body": comment.body or "",
        "path": comment.path,
        "diff_hunk": comment.diff_hunk or "",
        "created_at": comment.created_at.isoformat() if comment.created_at else "",
    }


def fetch_adrs(owner: str, repo: str) -> list[dict[str, Any]]:
    """Return markdown ADR files found in the conventional ADR directories."""
    gh_repo = _get_repo(owner, repo)
    out: list[dict[str, Any]] = []
    for directory in ADR_DIRS:
        try:
            contents = gh_repo.get_contents(directory)
        except Exception:
            continue  # directory doesn't exist in this repo
        if not isinstance(contents, list):
            contents = [contents]
        for item in contents:
            if item.type == "file" and item.name.lower().endswith(".md"):
                out.append(
                    {
                        "path": item.path,
                        "name": item.name,
                        "text": item.decoded_content.decode("utf-8", errors="replace"),
                    }
                )
    return out


def fetch_repo_tree(owner: str, repo: str) -> dict[str, Any]:
    """Return the repo's file tree plus default branch, for structure ingestion."""
    gh_repo = _get_repo(owner, repo)
    branch = gh_repo.default_branch
    tree = gh_repo.get_git_tree(branch, recursive=True)
    files = [
        {"path": el.path, "type": el.type, "size": getattr(el, "size", None)}
        for el in tree.tree
        if el.type == "blob"
    ]
    return {"default_branch": branch, "files": files}


def fetch_releases(owner: str, repo: str) -> list[dict[str, Any]]:
    """Return GitHub releases as plain dicts."""
    gh_repo = _get_repo(owner, repo)
    out: list[dict[str, Any]] = []
    for release in gh_repo.get_releases():
        out.append({
            "tag": release.tag_name,
            "name": release.title or release.tag_name,
            "body": release.body or "",
            "author": release.author.login if release.author else "unknown",
            "created_at": release.created_at.isoformat() if release.created_at else "",
            "published_at": release.published_at.isoformat() if release.published_at else "",
            "prerelease": release.prerelease,
            "draft": release.draft,
            "assets": [
                {"name": a.name, "size": a.size, "download_count": a.download_count}
                for a in release.get_assets()
            ],
        })
    return out


def fetch_tags(owner: str, repo: str) -> list[dict[str, Any]]:
    """Return git tags as plain dicts."""
    gh_repo = _get_repo(owner, repo)
    out: list[dict[str, Any]] = []
    for tag in gh_repo.get_tags():
        commit = tag.commit
        out.append({
            "name": tag.name,
            "sha": commit.sha if commit else "",
            "message": commit.commit.message if commit and commit.commit else "",
            "author": commit.commit.author.name if commit and commit.commit and commit.commit.author else "unknown",
            "date": commit.commit.author.date.isoformat() if commit and commit.commit and commit.commit.author and commit.commit.author.date else "",
        })
    return out


def fetch_deployments(owner: str, repo: str) -> list[dict[str, Any]]:
    """Return recent deployments as plain dicts."""
    gh_repo = _get_repo(owner, repo)
    out: list[dict[str, Any]] = []
    try:
        for dep in gh_repo.get_deployments():
            status = None
            try:
                statuses = list(dep.get_statuses())
                if statuses:
                    latest = statuses[0]
                    status = {
                        "state": latest.state,
                        "description": latest.description or "",
                        "created_at": latest.created_at.isoformat() if latest.created_at else "",
                    }
            except Exception:
                pass
            out.append({
                "id": dep.id,
                "ref": dep.ref,
                "sha": dep.sha,
                "environment": dep.environment or "",
                "description": dep.description or "",
                "creator": dep.creator.login if dep.creator else "unknown",
                "created_at": dep.created_at.isoformat() if dep.created_at else "",
                "status": status,
            })
    except Exception:
        pass  # Some repos may not have deployments permission
    return out



