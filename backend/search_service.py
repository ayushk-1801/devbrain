"""Commit search service — all backed by GitHub's Search API.

GitHub's commit search requires the preview Accept header:
  application/vnd.github.cloak-preview

PyGithub's search_commits() handles this automatically; we also offer
direct httpx calls for endpoints where we need more control.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import httpx

from backend.config import github_client, split_repo, settings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _gh():
    return github_client()


def _gh_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.cloak-preview+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


def _serialize_search_commit(item: dict) -> dict[str, Any]:
    """Normalize a GitHub commit search result item."""
    commit = item.get("commit", {})
    author = commit.get("author", {})
    committer = commit.get("committer", {})
    return {
        "sha": item.get("sha"),
        "message": commit.get("message"),
        "author_name": author.get("name"),
        "author_email": author.get("email"),
        "author_date": author.get("date"),
        "committer_name": committer.get("name"),
        "committer_date": committer.get("date"),
        "github_login": (item.get("author") or {}).get("login"),
        "html_url": item.get("html_url"),
        "repository": (item.get("repository") or {}).get("full_name"),
    }


async def _github_commit_search(q: str, per_page: int = 30) -> list[dict[str, Any]]:
    """Run a raw commit search query against the GitHub Search API."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://api.github.com/search/commits",
            headers=_gh_headers(),
            params={"q": q, "per_page": min(per_page, 100), "sort": "committer-date", "order": "desc"},
        )
        if resp.status_code != 200:
            return []
        return [_serialize_search_commit(item) for item in resp.json().get("items", [])]


# ---------------------------------------------------------------------------
# Search functions
# ---------------------------------------------------------------------------


async def search_commits(repo: str, query: str, max_results: int = 30) -> dict[str, Any]:
    """Free-text search across commit messages and metadata in a repo.

    Args:
        repo: Repository as "owner/repo".
        query: Search query (GitHub commit search syntax supported,
               e.g. "fix login author:alice" or "feat: auth").
        max_results: Maximum results to return (max 100).
    """
    full_q = f"{query} repo:{repo}"
    results = await _github_commit_search(full_q, per_page=max_results)
    return {"repo": repo, "query": query, "count": len(results), "commits": results}


async def search_commit_message(repo: str, message_text: str, max_results: int = 30) -> dict[str, Any]:
    """Search commits whose message contains a specific text string.

    Args:
        repo: Repository as "owner/repo".
        message_text: Text to search for in commit messages.
        max_results: Maximum results to return.
    """
    # Wrap in quotes to search for the phrase; remove quotes from user input for safety
    safe_text = message_text.replace('"', '')
    full_q = f'"{safe_text}" repo:{repo}'
    results = await _github_commit_search(full_q, per_page=max_results)
    return {
        "repo": repo,
        "message_text": message_text,
        "count": len(results),
        "commits": results,
    }


async def search_by_author(repo: str, author: str, max_results: int = 30) -> dict[str, Any]:
    """Return commits authored by a specific GitHub user or email.

    Args:
        repo: Repository as "owner/repo".
        author: GitHub login (e.g. "alice") or email address.
        max_results: Maximum results to return.
    """
    if "@" in author:
        full_q = f"author-email:{author} repo:{repo}"
    else:
        full_q = f"author:{author} repo:{repo}"
    results = await _github_commit_search(full_q, per_page=max_results)
    return {"repo": repo, "author": author, "count": len(results), "commits": results}


async def search_by_file(repo: str, filepath: str, max_results: int = 30) -> dict[str, Any]:
    """Return commits that touched a specific file path.

    This uses GitHub's commit search filtered by the file path token.

    Args:
        repo: Repository as "owner/repo".
        filepath: File path relative to the repo root (e.g. "backend/main.py").
        max_results: Maximum results to return.
    """
    # GitHub doesn't have a direct "file path" commit search qualifier,
    # so we use the PyGithub get_commits(path=...) approach via REST.
    gh_repo = await asyncio.to_thread(
        lambda: github_client().get_repo(repo)
    )

    def _fetch():
        commits_paged = gh_repo.get_commits(path=filepath)
        out = []
        for c in commits_paged:
            author = c.commit.author
            out.append({
                "sha": c.sha,
                "message": c.commit.message,
                "author_name": author.name if author else None,
                "author_email": author.email if author else None,
                "author_date": author.date.isoformat() if author and author.date else None,
                "github_login": c.author.login if c.author else None,
                "html_url": c.html_url,
            })
            if len(out) >= max_results:
                break
        return out

    results = await asyncio.to_thread(_fetch)
    return {"repo": repo, "filepath": filepath, "count": len(results), "commits": results}


async def search_by_date(
    repo: str,
    since: str,
    until: Optional[str] = None,
    max_results: int = 30,
) -> dict[str, Any]:
    """Return commits within a date range.

    Args:
        repo: Repository as "owner/repo".
        since: ISO-8601 start date (e.g. "2025-01-01" or "2025-01-01T00:00:00Z").
        until: Optional ISO-8601 end date. Defaults to now.
        max_results: Maximum results to return.
    """
    from datetime import datetime, timezone

    def _normalise(ds: str) -> str:
        """Ensure date string is in YYYY-MM-DDTHH:MM:SSZ format for GitHub."""
        if "T" not in ds:
            ds = ds + "T00:00:00Z"
        if not ds.endswith("Z") and "+" not in ds:
            ds = ds + "Z"
        return ds

    since_q = _normalise(since)
    if until:
        until_q = _normalise(until)
        date_qualifier = f"committer-date:{since_q}..{until_q}"
    else:
        date_qualifier = f"committer-date:>={since_q}"

    full_q = f"{date_qualifier} repo:{repo}"
    results = await _github_commit_search(full_q, per_page=max_results)
    return {
        "repo": repo,
        "since": since,
        "until": until,
        "count": len(results),
        "commits": results,
    }


async def search_by_hash(repo: str, sha_prefix: str) -> dict[str, Any]:
    """Look up a commit by full or partial SHA.

    For a full SHA, uses the GitHub API directly for an exact lookup.
    For a partial SHA (< 40 chars), falls back to the search API.

    Args:
        repo: Repository as "owner/repo".
        sha_prefix: Full (40-char) or abbreviated (7+ char) commit SHA.
    """
    gh_repo = await asyncio.to_thread(lambda: github_client().get_repo(repo))
    sha_prefix = sha_prefix.strip()

    if len(sha_prefix) == 40:
        # Exact lookup
        try:
            commit = await asyncio.to_thread(gh_repo.get_commit, sha_prefix)
            author = commit.commit.author
            result = {
                "sha": commit.sha,
                "message": commit.commit.message,
                "author_name": author.name if author else None,
                "author_email": author.email if author else None,
                "author_date": author.date.isoformat() if author and author.date else None,
                "github_login": commit.author.login if commit.author else None,
                "html_url": commit.html_url,
            }
            return {"repo": repo, "sha_prefix": sha_prefix, "count": 1, "commits": [result]}
        except Exception as e:
            return {"repo": repo, "sha_prefix": sha_prefix, "count": 0, "commits": [], "error": str(e)}

    # Partial SHA — use search
    full_q = f"hash:{sha_prefix} repo:{repo}"
    results = await _github_commit_search(full_q, per_page=10)
    return {"repo": repo, "sha_prefix": sha_prefix, "count": len(results), "commits": results}
