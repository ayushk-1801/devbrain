"""Commit history, file history, author history, branch history,
commit graph, and line-level blame — all via GitHub API.

All functions use asyncio.to_thread() for PyGithub calls and httpx
for GitHub REST endpoints that PyGithub doesn't expose.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from backend.config import github_client, split_repo, settings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_repo(repo: str):
    gh = github_client()
    owner, name = split_repo(repo)
    return gh.get_repo(f"{owner}/{name}")


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


def _serialize_commit(c) -> dict[str, Any]:
    author = c.commit.author
    return {
        "sha": c.sha,
        "message": c.commit.message,
        "author_name": author.name if author else None,
        "author_email": author.email if author else None,
        "author_date": _iso(author.date) if author else None,
        "github_login": c.author.login if c.author else None,
        "html_url": c.html_url,
        "parents": [p.sha for p in c.parents],
    }


def _gh_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


# ---------------------------------------------------------------------------
# History functions
# ---------------------------------------------------------------------------


async def commit_history(
    repo: str,
    branch: str = "main",
    path: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    author: Optional[str] = None,
    max_count: int = 50,
) -> dict[str, Any]:
    """Return commit history for a branch, optionally filtered by path/author/date.

    Args:
        repo: Repository as "owner/repo".
        branch: Branch name or SHA to walk from. Defaults to "main".
        path: If set, only commits that touched this file path are returned.
        since: ISO-8601 date string — only commits after this date.
        until: ISO-8601 date string — only commits before this date.
        author: GitHub login or email to filter by.
        max_count: Maximum number of commits to return (default 50, max 200).
    """
    gh_repo = await asyncio.to_thread(_get_repo, repo)

    kwargs: dict[str, Any] = {"sha": branch}
    if path:
        kwargs["path"] = path
    if since:
        kwargs["since"] = datetime.fromisoformat(since.replace("Z", "+00:00"))
    if until:
        kwargs["until"] = datetime.fromisoformat(until.replace("Z", "+00:00"))
    if author:
        kwargs["author"] = author

    max_count = min(max_count, 200)

    def _fetch():
        commits_paged = gh_repo.get_commits(**kwargs)
        result = []
        for c in commits_paged:
            result.append(_serialize_commit(c))
            if len(result) >= max_count:
                break
        return result

    commits = await asyncio.to_thread(_fetch)
    return {
        "repo": repo,
        "branch": branch,
        "path": path,
        "count": len(commits),
        "commits": commits,
    }


async def file_history(
    repo: str,
    path: str,
    branch: str = "main",
    max_count: int = 50,
) -> dict[str, Any]:
    """Return all commits that touched a specific file path.

    This is equivalent to `git log --follow -- <path>`.

    Args:
        repo: Repository as "owner/repo".
        path: Relative file path from repo root (e.g. "backend/main.py").
        branch: Branch to walk from.
        max_count: Maximum number of commits to return.
    """
    return await commit_history(repo, branch=branch, path=path, max_count=max_count)


async def author_history(
    repo: str,
    author: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    max_count: int = 50,
) -> dict[str, Any]:
    """Return all commits made by a specific author.

    Args:
        repo: Repository as "owner/repo".
        author: GitHub login or email address.
        since: Optional ISO-8601 start date.
        until: Optional ISO-8601 end date.
        max_count: Maximum number of commits to return.
    """
    return await commit_history(
        repo, author=author, since=since, until=until, max_count=max_count
    )


async def branch_history(
    repo: str,
    branch: str,
    base: Optional[str] = None,
    max_count: int = 50,
) -> dict[str, Any]:
    """Return commits on a branch since it diverged from a base branch.

    If base is None, returns commits from the beginning of the branch.

    Args:
        repo: Repository as "owner/repo".
        branch: The topic/feature branch to inspect.
        base: The base branch (e.g. "main") — commits reachable from base
              are excluded. If omitted all commits on branch are returned.
        max_count: Maximum number of commits to return.
    """
    owner, name = split_repo(repo)

    if base:
        # Use GitHub compare API to get only the branch-specific commits
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/compare/{base}...{branch}",
                headers=_gh_headers(),
                params={"per_page": min(max_count, 250)},
            )
            if resp.status_code == 200:
                data = resp.json()
                commits_raw = data.get("commits", [])
                commits = [
                    {
                        "sha": c["sha"],
                        "message": c["commit"]["message"],
                        "author_name": c["commit"]["author"]["name"],
                        "author_email": c["commit"]["author"]["email"],
                        "author_date": c["commit"]["author"]["date"],
                        "github_login": (c.get("author") or {}).get("login"),
                        "html_url": c.get("html_url"),
                        "parents": [p["sha"] for p in c.get("parents", [])],
                    }
                    for c in commits_raw[:max_count]
                ]
                return {
                    "repo": repo,
                    "branch": branch,
                    "base": base,
                    "ahead_by": data.get("ahead_by", 0),
                    "behind_by": data.get("behind_by", 0),
                    "count": len(commits),
                    "commits": commits,
                }

    # Fallback: just return branch commit history without base filtering
    return await commit_history(repo, branch=branch, max_count=max_count)


async def commit_graph(
    repo: str,
    branch: str = "main",
    max_count: int = 50,
) -> dict[str, Any]:
    """Return the commit DAG structure: nodes with SHA, parents, message, author, date.

    Useful for rendering a visual commit graph.

    Args:
        repo: Repository as "owner/repo".
        branch: Branch to walk from.
        max_count: Maximum number of commits to include in the graph.
    """
    gh_repo = await asyncio.to_thread(_get_repo, repo)

    def _fetch():
        commits_paged = gh_repo.get_commits(sha=branch)
        nodes = []
        for c in commits_paged:
            author = c.commit.author
            nodes.append({
                "sha": c.sha,
                "short_sha": c.sha[:8],
                "message": c.commit.message.split("\n")[0],  # subject line only
                "author_name": author.name if author else None,
                "author_date": _iso(author.date) if author else None,
                "github_login": c.author.login if c.author else None,
                "parents": [p.sha for p in c.parents],
                "html_url": c.html_url,
            })
            if len(nodes) >= max_count:
                break
        return nodes

    nodes = await asyncio.to_thread(_fetch)
    return {
        "repo": repo,
        "branch": branch,
        "node_count": len(nodes),
        "nodes": nodes,
    }


async def blame_history(
    repo: str,
    path: str,
    branch: str = "main",
) -> dict[str, Any]:
    """Return line-level blame for a file: who last modified each line and when.

    Uses GitHub's blame REST API (not available in PyGithub).

    Args:
        repo: Repository as "owner/repo".
        path: Relative file path from repo root (e.g. "backend/main.py").
        branch: Branch or SHA to read the blame from.
    """
    owner, name = split_repo(repo)

    # GitHub GraphQL blame is most reliable for this
    # Fallback: use the blame REST API via Accept header trick
    graphql_url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {settings.GITHUB_TOKEN}"} if settings.GITHUB_TOKEN else {}

    query = """
    query($owner: String!, $name: String!, $expression: String!) {
      repository(owner: $owner, name: $name) {
        object(expression: $expression) {
          ... on Commit {
            blame(path: $expression_path) {
              ranges {
                startingLine
                endingLine
                commit {
                  oid
                  message
                  author {
                    name
                    email
                    date
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    # Use simpler REST commits-for-file approach as GraphQL blame needs path separately
    # Use the git blame via commits-per-file approach
    blame_lines = []
    try:
        # Get file content to know total lines
        async with httpx.AsyncClient(timeout=30) as client:
            # Fetch file content
            content_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/contents/{path}",
                headers={**_gh_headers(), "Accept": "application/vnd.github.raw+json"},
                params={"ref": branch},
            )
            if content_resp.status_code != 200:
                return {"repo": repo, "path": path, "branch": branch, "blame": [], "error": "Could not fetch file"}

            # Use GitHub's blame via GraphQL (proper blame API)
            gql_query = """
query($owner: String!, $repo: String!, $ref: String!, $path: String!) {
  repository(owner: $owner, name: $repo) {
    ref(qualifiedName: $ref) {
      target {
        ... on Commit {
          blame(path: $path) {
            ranges {
              startingLine
              endingLine
              commit {
                oid
                messageHeadline
                author {
                  name
                  email
                  date
                }
              }
            }
          }
        }
      }
    }
  }
}"""
            gql_resp = await client.post(
                graphql_url,
                headers={**headers, "Content-Type": "application/json"},
                json={"query": gql_query, "variables": {"owner": owner, "repo": name, "ref": branch, "path": path}},
            )
            if gql_resp.status_code == 200:
                gql_data = gql_resp.json()
                ranges = (
                    gql_data.get("data", {})
                    .get("repository", {})
                    .get("ref", {})
                    .get("target", {})
                    .get("blame", {})
                    .get("ranges", [])
                )
                for r in ranges:
                    commit_info = r.get("commit", {})
                    blame_lines.append({
                        "starting_line": r.get("startingLine"),
                        "ending_line": r.get("endingLine"),
                        "sha": commit_info.get("oid"),
                        "message": commit_info.get("messageHeadline"),
                        "author_name": (commit_info.get("author") or {}).get("name"),
                        "author_email": (commit_info.get("author") or {}).get("email"),
                        "author_date": (commit_info.get("author") or {}).get("date"),
                    })
    except Exception as e:
        return {"repo": repo, "path": path, "branch": branch, "blame": [], "error": str(e)}

    return {
        "repo": repo,
        "path": path,
        "branch": branch,
        "range_count": len(blame_lines),
        "blame": blame_lines,
    }
