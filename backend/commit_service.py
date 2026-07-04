"""Commit inspection and context service.

All functions use PyGithub via asyncio.to_thread() for non-blocking I/O.

Commit Inspection  — read raw commit data from GitHub
Commit Context     — cross-reference a SHA to associated PRs, issues,
                     releases, workflow runs, and deployments.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from backend.config import github_client, split_repo, settings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_repo(repo: str):
    gh = github_client()
    owner, name = split_repo(repo)
    return gh.get_repo(f"{owner}/{name}")


def _get_commit(repo_obj, sha: str):
    return repo_obj.get_commit(sha)


# ---------------------------------------------------------------------------
# Commit Inspection
# ---------------------------------------------------------------------------


async def get_commit_diff(repo: str, sha: str) -> dict[str, Any]:
    """Return the unified diff for every file changed in a commit.

    Returns a dict with:
      - sha: the commit SHA
      - files: list of {filename, patch} where patch is the unified diff text
      - raw_diff: all patches concatenated into one string
    """
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    commit = await asyncio.to_thread(_get_commit, gh_repo, sha)
    files = list(commit.files)
    result = []
    for f in files:
        result.append({
            "filename": f.filename,
            "status": f.status,
            "patch": getattr(f, "patch", None) or "",
        })
    raw_diff = "\n".join(
        f"--- a/{f['filename']}\n+++ b/{f['filename']}\n{f['patch']}"
        for f in result if f["patch"]
    )
    return {"sha": commit.sha, "files": result, "raw_diff": raw_diff}


async def get_commit_files(repo: str, sha: str) -> list[dict[str, Any]]:
    """Return the list of files changed in a commit with status and line stats."""
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    commit = await asyncio.to_thread(_get_commit, gh_repo, sha)
    return [
        {
            "filename": f.filename,
            "status": f.status,
            "additions": f.additions,
            "deletions": f.deletions,
            "changes": f.changes,
            "raw_url": f.raw_url,
            "blob_url": f.blob_url,
        }
        for f in commit.files
    ]


async def get_commit_patch(repo: str, sha: str) -> dict[str, Any]:
    """Return the raw .patch text for every changed file, keyed by filename."""
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    commit = await asyncio.to_thread(_get_commit, gh_repo, sha)
    patches = {
        f.filename: getattr(f, "patch", None) or ""
        for f in commit.files
    }
    return {"sha": commit.sha, "patches": patches}


async def get_commit_stats(repo: str, sha: str) -> dict[str, Any]:
    """Return addition/deletion/total statistics for a commit."""
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    commit = await asyncio.to_thread(_get_commit, gh_repo, sha)
    stats = commit.stats
    return {
        "sha": commit.sha,
        "additions": stats.additions,
        "deletions": stats.deletions,
        "total": stats.total,
        "files_count": len(list(commit.files)),
    }


async def get_commit_author(repo: str, sha: str) -> dict[str, Any]:
    """Return author information for a commit (both git author and GitHub login)."""
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    commit = await asyncio.to_thread(_get_commit, gh_repo, sha)
    git_author = commit.commit.author
    committer = commit.commit.committer
    return {
        "sha": commit.sha,
        "author_name": git_author.name if git_author else None,
        "author_email": git_author.email if git_author else None,
        "author_date": git_author.date.isoformat() if git_author and git_author.date else None,
        "github_login": commit.author.login if commit.author else None,
        "committer_name": committer.name if committer else None,
        "committer_email": committer.email if committer else None,
        "committer_date": committer.date.isoformat() if committer and committer.date else None,
        "github_committer": commit.committer.login if commit.committer else None,
    }


async def get_commit_parents(repo: str, sha: str) -> dict[str, Any]:
    """Return the parent commit SHAs for a commit.

    A merge commit will have two parents; the initial commit will have none.
    """
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    commit = await asyncio.to_thread(_get_commit, gh_repo, sha)
    parents = [{"sha": p.sha, "url": p.html_url} for p in commit.parents]
    return {
        "sha": commit.sha,
        "parents": parents,
        "is_merge_commit": len(parents) > 1,
        "is_root_commit": len(parents) == 0,
    }


async def get_commit_branches(repo: str, sha: str) -> dict[str, Any]:
    """Return branches that contain this commit.

    Uses the GitHub REST API directly since PyGithub doesn't expose
    the branches-where-head endpoint; falls back to listing all branches
    and checking each.
    """
    import httpx
    owner, name = split_repo(repo)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    url = f"https://api.github.com/repos/{owner}/{name}/commits/{sha}/branches-where-head"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                branches = resp.json()
                return {
                    "sha": sha,
                    "branches": [{"name": b["name"], "protected": b.get("protected", False)} for b in branches],
                }
    except Exception:
        pass

    # Fallback: use PyGithub to find branches whose HEAD matches
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    all_branches = await asyncio.to_thread(lambda: list(gh_repo.get_branches()))
    containing = [b.name for b in all_branches if b.commit.sha == sha]
    return {"sha": sha, "branches": [{"name": b, "protected": False} for b in containing]}


async def get_commit_tags(repo: str, sha: str) -> dict[str, Any]:
    """Return tags that point to this commit SHA."""
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    all_tags = await asyncio.to_thread(lambda: list(gh_repo.get_tags()))
    matching = [
        {"name": t.name, "sha": t.commit.sha}
        for t in all_tags
        if t.commit.sha == sha
    ]
    return {"sha": sha, "tags": matching}


async def get_commit_signature(repo: str, sha: str) -> dict[str, Any]:
    """Return the GPG/SSH signature verification info for a commit."""
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    commit = await asyncio.to_thread(_get_commit, gh_repo, sha)
    v = commit.commit.verification
    return {
        "sha": commit.sha,
        "verified": v.verified if v else False,
        "reason": v.reason if v else "unsigned",
        "signature": v.signature if v else None,
        "payload": v.payload if v else None,
    }


async def get_commit_status(repo: str, sha: str) -> dict[str, Any]:
    """Return the combined CI/check status for a commit.

    Returns the GitHub combined status (state: pending/success/failure/error)
    plus individual per-context statuses and check runs.
    """
    gh_repo = await asyncio.to_thread(_get_repo, repo)

    combined = await asyncio.to_thread(gh_repo.get_commit_combined_status, sha)
    statuses = [
        {
            "context": s.context,
            "state": s.state,
            "description": s.description,
            "target_url": s.target_url,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in combined.statuses
    ]

    # Also fetch check runs via REST (GitHub Actions)
    import httpx
    owner, name = split_repo(repo)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    check_runs = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/commits/{sha}/check-runs",
                headers=headers,
            )
            if resp.status_code == 200:
                for cr in resp.json().get("check_runs", []):
                    check_runs.append({
                        "name": cr.get("name"),
                        "status": cr.get("status"),
                        "conclusion": cr.get("conclusion"),
                        "started_at": cr.get("started_at"),
                        "completed_at": cr.get("completed_at"),
                        "html_url": cr.get("html_url"),
                    })
    except Exception:
        pass

    return {
        "sha": sha,
        "state": combined.state,
        "total_count": combined.total_count,
        "statuses": statuses,
        "check_runs": check_runs,
    }


# ---------------------------------------------------------------------------
# Commit Context
# ---------------------------------------------------------------------------


async def commit_pull_request(repo: str, sha: str) -> dict[str, Any]:
    """Return pull requests that contain this commit.

    Uses GitHub's list-pull-requests-associated-with-commit endpoint.
    """
    import httpx
    owner, name = split_repo(repo)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    prs = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/commits/{sha}/pulls",
                headers=headers,
            )
            if resp.status_code == 200:
                for pr in resp.json():
                    prs.append({
                        "number": pr.get("number"),
                        "title": pr.get("title"),
                        "state": pr.get("state"),
                        "html_url": pr.get("html_url"),
                        "merged_at": pr.get("merged_at"),
                        "user": pr.get("user", {}).get("login"),
                    })
    except Exception:
        pass

    return {"sha": sha, "pull_requests": prs}


async def commit_issue(repo: str, sha: str) -> dict[str, Any]:
    """Return issues linked to any PRs that contain this commit.

    Finds associated PRs first, then collects issues mentioned/linked in them.
    """
    pr_data = await commit_pull_request(repo, sha)
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issues = []
    seen_numbers: set[int] = set()

    for pr_info in pr_data.get("pull_requests", []):
        pr_number = pr_info.get("number")
        if not pr_number:
            continue
        try:
            pr = await asyncio.to_thread(gh_repo.get_pull, pr_number)
            # Parse issue refs from PR body
            body = pr.body or ""
            import re
            refs = re.findall(r"(?:closes?|fixes?|resolves?)\s+#(\d+)", body, re.IGNORECASE)
            for issue_num in refs:
                num = int(issue_num)
                if num in seen_numbers:
                    continue
                seen_numbers.add(num)
                try:
                    issue = await asyncio.to_thread(gh_repo.get_issue, num)
                    issues.append({
                        "number": issue.number,
                        "title": issue.title,
                        "state": issue.state,
                        "html_url": issue.html_url,
                        "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
                        "referenced_from_pr": pr_number,
                    })
                except Exception:
                    pass
        except Exception:
            continue

    return {"sha": sha, "issues": issues}


async def commit_reviews(repo: str, sha: str) -> dict[str, Any]:
    """Return all PR reviews on pull requests that contain this commit."""
    pr_data = await commit_pull_request(repo, sha)
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    reviews = []

    for pr_info in pr_data.get("pull_requests", []):
        pr_number = pr_info.get("number")
        if not pr_number:
            continue
        try:
            pr = await asyncio.to_thread(gh_repo.get_pull, pr_number)
            pr_reviews = await asyncio.to_thread(lambda: list(pr.get_reviews()))
            for r in pr_reviews:
                reviews.append({
                    "pr_number": pr_number,
                    "id": r.id,
                    "user": r.user.login if r.user else None,
                    "state": r.state,
                    "body": r.body,
                    "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                })
        except Exception:
            continue

    return {"sha": sha, "reviews": reviews}


async def commit_discussions(repo: str, sha: str) -> dict[str, Any]:
    """Return issue + review comments from PRs associated with this commit."""
    pr_data = await commit_pull_request(repo, sha)
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    discussions = []

    for pr_info in pr_data.get("pull_requests", []):
        pr_number = pr_info.get("number")
        if not pr_number:
            continue
        try:
            pr = await asyncio.to_thread(gh_repo.get_pull, pr_number)
            # Issue-level comments
            issue_comments = await asyncio.to_thread(lambda: list(pr.get_issue_comments()))
            for c in issue_comments:
                discussions.append({
                    "pr_number": pr_number,
                    "type": "issue_comment",
                    "id": c.id,
                    "user": c.user.login if c.user else None,
                    "body": c.body,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                })
            # Inline review comments
            review_comments = await asyncio.to_thread(lambda: list(pr.get_comments()))
            for c in review_comments:
                discussions.append({
                    "pr_number": pr_number,
                    "type": "review_comment",
                    "id": c.id,
                    "user": c.user.login if c.user else None,
                    "body": c.body,
                    "path": c.path,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                })
        except Exception:
            continue

    return {"sha": sha, "discussions": discussions}


async def commit_release(repo: str, sha: str) -> dict[str, Any]:
    """Return the release (if any) that this commit is associated with.

    A commit is considered part of a release if its SHA matches the release's
    target commitish or if it is the tagged commit of that release.
    """
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    releases = await asyncio.to_thread(lambda: list(gh_repo.get_releases()))

    for release in releases:
        try:
            tag = await asyncio.to_thread(gh_repo.get_git_ref, f"tags/{release.tag_name}")
            tag_sha = tag.object.sha
            # Dereference annotated tag to the commit SHA
            if tag.object.type == "tag":
                tag_obj = await asyncio.to_thread(gh_repo.get_git_tag, tag_sha)
                tag_sha = tag_obj.object.sha
            if tag_sha == sha:
                return {
                    "sha": sha,
                    "release": {
                        "tag": release.tag_name,
                        "name": release.title or release.tag_name,
                        "html_url": release.html_url,
                        "published_at": release.published_at.isoformat() if release.published_at else None,
                        "prerelease": release.prerelease,
                    },
                }
        except Exception:
            continue

    return {"sha": sha, "release": None}


async def commit_workflows(repo: str, sha: str) -> dict[str, Any]:
    """Return GitHub Actions workflow runs triggered by or associated with this commit."""
    import httpx
    owner, name = split_repo(repo)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    runs = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/actions/runs",
                headers=headers,
                params={"head_sha": sha, "per_page": 50},
            )
            if resp.status_code == 200:
                for run in resp.json().get("workflow_runs", []):
                    runs.append({
                        "id": run.get("id"),
                        "name": run.get("name"),
                        "workflow_id": run.get("workflow_id"),
                        "status": run.get("status"),
                        "conclusion": run.get("conclusion"),
                        "event": run.get("event"),
                        "created_at": run.get("created_at"),
                        "updated_at": run.get("updated_at"),
                        "html_url": run.get("html_url"),
                        "run_number": run.get("run_number"),
                    })
    except Exception:
        pass

    return {"sha": sha, "workflow_runs": runs}


async def commit_deployments(repo: str, sha: str) -> dict[str, Any]:
    """Return deployments tied to this commit SHA."""
    import httpx
    owner, name = split_repo(repo)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    deployments = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/deployments",
                headers=headers,
                params={"sha": sha, "per_page": 50},
            )
            if resp.status_code == 200:
                for dep in resp.json():
                    # Fetch the latest status for each deployment
                    status = None
                    try:
                        st_resp = await client.get(
                            f"https://api.github.com/repos/{owner}/{name}/deployments/{dep['id']}/statuses",
                            headers=headers,
                            params={"per_page": 1},
                        )
                        statuses = st_resp.json()
                        if statuses:
                            status = {
                                "state": statuses[0].get("state"),
                                "description": statuses[0].get("description"),
                                "environment_url": statuses[0].get("environment_url"),
                            }
                    except Exception:
                        pass

                    deployments.append({
                        "id": dep.get("id"),
                        "ref": dep.get("ref"),
                        "environment": dep.get("environment"),
                        "description": dep.get("description"),
                        "creator": dep.get("creator", {}).get("login"),
                        "created_at": dep.get("created_at"),
                        "status": status,
                    })
    except Exception:
        pass

    return {"sha": sha, "deployments": deployments}
