"""DevBrain MCP server — thin HTTP client over the hosted DevBrain backend.

This process runs locally (stdio transport) for each user and proxies every tool
call to the DevBrain REST API at DEVBRAIN_API_URL. Users need only that URL — no
GitHub token, no Cognee config, no LLM keys for read/query tools.

The one exception: tools that create attributed GitHub content (opening issues,
commenting, labeling, assigning, closing/reopening) run as *your* GitHub account,
not the server's central bot token. Set GITHUB_USER_TOKEN to a fine-grained PAT
scoped to just the repo(s) you use, with only the "Issues: Read and write"
permission and an expiration date:

    claude mcp add devbrain -s project \\
      -e DEVBRAIN_API_URL="https://devbrain.example.com" \\
      -e GITHUB_USER_TOKEN="github_pat_..." \\
      -- python -m backend.mcp_server

The token is forwarded per-call as the X-GitHub-User-Token header and is never
stored server-side — the backend uses it in-memory for that one GitHub API call
and discards it. There is no fallback to the server's central token: if
GITHUB_USER_TOKEN isn't set, attributed write tools fail with a clear error
rather than silently acting as the shared bot account.

The maintainer runs one backend (main.py) with all other secrets; users point
this server at it:

    DEVBRAIN_API_URL=https://devbrain.example.com \\
      claude mcp add devbrain -- python -m backend.mcp_server

Run locally (backend on the same machine):
    DEVBRAIN_API_URL=http://localhost:8000 python -m backend.mcp_server
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devbrain.mcp")

DEVBRAIN_API_URL = os.getenv("DEVBRAIN_API_URL", "http://localhost:8000").rstrip("/")

_http: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    if _http is None:
        raise RuntimeError("MCP server not initialised")
    return _http


def _user_token_headers() -> dict[str, str]:
    """Headers for tools that create attributed GitHub content.

    Reads GITHUB_USER_TOKEN fresh on every call (not cached at import time) so a
    user can update it without restarting the MCP process. Deliberately raises
    instead of falling back to no header — the backend has no central-token
    fallback for these actions either, so failing fast here gives a clearer
    error than a round-trip 401.
    """
    token = os.getenv("GITHUB_USER_TOKEN", "")
    if not token:
        raise RuntimeError(
            "GITHUB_USER_TOKEN is not set. This action creates GitHub content "
            "attributed to your account and requires your own personal access "
            "token — set GITHUB_USER_TOKEN when configuring this MCP server."
        )
    return {"X-GitHub-User-Token": token}


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_error:
        raise RuntimeError(
            f"DevBrain API error {response.status_code}: {response.text[:200]}"
        )


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    global _http
    async with httpx.AsyncClient(base_url=DEVBRAIN_API_URL, timeout=120) as client:
        _http = client
        logger.info("DevBrain MCP client connected to %s", DEVBRAIN_API_URL)
        yield
    _http = None


mcp = FastMCP(
    "DevBrain",
    instructions=(
        "DevBrain is a living engineering memory. It ingests a GitHub repo's "
        "commits, pull requests, issues, ADRs, and code structure into a knowledge graph, "
        "then answers 'why was this changed?' questions with sourced provenance. "
        "Call `ingest_repo` first for a repo, then `query_devbrain`. All tools take "
        "an explicit `repo` of the form 'owner/repo'."
    ),
    lifespan=lifespan,
)


@mcp.tool()
async def ingest_repo(repo: str, sync_history_days: int | None = None) -> dict:
    """Enqueue ingestion of a GitHub repo's history into DevBrain's memory.

    Returns immediately with a job_id. The actual ingestion (commits, PRs,
    issues, ADRs, code structure) runs asynchronously in the background.
    Use `job_status(job_id)` to check progress.

    Args:
        repo: Target repository as "owner/repo".
        sync_history_days: Optional window (days). None = all history.

    Returns:
        {"job_id": "...", "status": "queued", "repo": "..."}
    """
    client = _client()
    body: dict = {"repo": repo}
    if sync_history_days is not None:
        body["sync_history_days"] = sync_history_days
    response = await client.post("/ingest", json=body)
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def job_status(job_id: str) -> dict:
    """Check the status of an enqueued ingestion job.

    Args:
        job_id: The job_id returned by ingest_repo.

    Returns:
        {"job_id": "...", "status": "queued|in_progress|complete|not_found",
         "result": {...}}  # result present when status is complete
    """
    client = _client()
    response = await client.get(f"/jobs/{job_id}")
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def query_devbrain(question: str, repo: str | None = None, mode: str = "hybrid") -> dict:
    """Ask a natural-language question about a repo's history and decisions.

    Args:
        question: e.g. "Why was the auth module decoupled from the user service?"
        repo: Optional "owner/repo" to scope context (helps provenance).
        mode: "hybrid" (default, auto-routed), "why" (graph completion, best for
            why-questions), or "chunks" (raw matching text).

    Returns:
        A dict with the synthesized `answer` and supporting `results`.
    """
    client = _client()
    params: dict = {"q": question, "mode": mode}
    if repo:
        params["repo"] = repo
    response = await client.get("/query", params=params)
    _raise_for_status(response)
    data = response.json()
    # Ensure results are always strings so the payload is JSON-serialisable.
    data["results"] = [str(r) for r in (data.get("results") or [])]
    return data


@mcp.tool()
async def forget_module(repo: str, module: str) -> dict:
    """Surgically prune a deprecated module's subgraph from a repo's memory.

    Args:
        repo: Target repository as "owner/repo".
        module: The module/path being deprecated (required, must be non-empty).

    Returns:
        Status of the prune operation.
    """
    owner, name = repo.split("/", 1)
    client = _client()
    response = await client.delete(f"/module/{owner}/{name}/{module}")
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def list_repos() -> dict:
    """List all repositories that have been ingested into DevBrain."""
    client = _client()
    response = await client.get("/repos")
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def refresh_memory(repo: str | None = None) -> dict:
    """Run Cognee's memify enrichment for one repo, or all if omitted.

    Strengthens frequently-traversed paths and derives new facts. This is a
    heavy operation — invoke deliberately, not on every change.

    Args:
        repo: Optional "owner/repo". Omit to refresh every ingested repo.
    """
    client = _client()
    params: dict = {}
    if repo:
        params["repo"] = repo
    response = await client.post("/refresh", params=params)
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def create_issue(
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] = None,
    assignees: list[str] = None,
    milestone: int = None,
) -> dict:
    """Create a new GitHub issue in a repository.

    Args:
        repo: Repository as "owner/repo".
        title: Title of the issue.
        body: Optional description of the issue.
        labels: Optional list of label names to apply.
        assignees: Optional list of usernames to assign.
        milestone: Optional milestone ID.
    """
    client = _client()
    body_data = {
        "title": title,
        "body": body,
    }
    if labels is not None:
        body_data["labels"] = labels
    if assignees is not None:
        body_data["assignees"] = assignees
    if milestone is not None:
        body_data["milestone"] = milestone

    response = await client.post(
        "/issues", params={"repo": repo}, json=body_data, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def get_issue(repo: str, number: int) -> dict:
    """Get comprehensive details of a specific issue.

    Returns the complete structured information for an issue in a single call,
    including Metadata, Comments (with reactions), Timeline events, Issue events,
    Linked PRs, Linked commits, Assignees, Labels, Milestone, Project info,
    Reactions summary & details, State, Created/Updated timestamps, and Author.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
    """
    client = _client()
    response = await client.get(f"/issues/{number}", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def update_issue(
    repo: str,
    number: int,
    title: str = None,
    body: str = None,
    state: str = None,
    labels: list[str] = None,
    milestone: int = None,
    assignees: list[str] = None,
) -> dict:
    """Update details of a specific issue.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
        title: Optional new title.
        body: Optional new description.
        state: Optional state ("open" or "closed").
        labels: Optional list of label names to replace all existing labels.
        milestone: Optional milestone number (0 to clear).
        assignees: Optional list of assignees to replace all existing assignees.
    """
    client = _client()
    body_data = {}
    if title is not None:
        body_data["title"] = title
    if body is not None:
        body_data["body"] = body
    if state is not None:
        body_data["state"] = state
    if labels is not None:
        body_data["labels"] = labels
    if milestone is not None:
        body_data["milestone"] = milestone
    if assignees is not None:
        body_data["assignees"] = assignees

    response = await client.patch(
        f"/issues/{number}", params={"repo": repo}, json=body_data, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def close_issue(repo: str, number: int) -> dict:
    """Close a GitHub issue.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
    """
    client = _client()
    response = await client.post(
        f"/issues/{number}/close", params={"repo": repo}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def reopen_issue(repo: str, number: int) -> dict:
    """Reopen a closed GitHub issue.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
    """
    client = _client()
    response = await client.post(
        f"/issues/{number}/reopen", params={"repo": repo}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def list_issues(
    repo: str,
    state: str = "open",
    assignee: str = None,
    creator: str = None,
    mentioned: str = None,
    labels: list[str] = None,
) -> list:
    """List issues in a repository with optional filters.

    Args:
        repo: Repository as "owner/repo".
        state: Issue state ("open", "closed", or "all").
        assignee: Optional user assigned to the issue.
        creator: Optional user who created the issue.
        mentioned: Optional user mentioned in the issue.
        labels: Optional list of label names to filter by.
    """
    client = _client()
    params = {"repo": repo, "state": state}
    if assignee:
        params["assignee"] = assignee
    if creator:
        params["creator"] = creator
    if mentioned:
        params["mentioned"] = mentioned
    if labels:
        params["labels"] = labels
    response = await client.get("/issues", params=params)
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def search_issues(repo: str, query: str) -> list:
    """Search for issues in a repository by a text query.

    Args:
        repo: Repository as "owner/repo".
        query: Search term (e.g. "authentication", "label:bug", "assignee:arpit").
    """
    client = _client()
    response = await client.get("/issues/search", params={"repo": repo, "q": query})
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def list_my_issues(repo: str, username: str) -> dict:
    """List issues that are assigned to, created by, or mention the current user.

    Args:
        repo: Repository as "owner/repo".
        username: GitHub username.
    """
    client = _client()
    response = await client.get("/issues/my-issues", params={"repo": repo, "username": username})
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def add_labels(repo: str, number: int, labels: list[str]) -> list:
    """Add labels to an issue.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
        labels: List of label names to add.
    """
    client = _client()
    response = await client.post(
        f"/issues/{number}/labels", params={"repo": repo}, json={"labels": labels}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def remove_label(repo: str, number: int, label_name: str) -> list:
    """Remove a label from an issue.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
        label_name: Name of the label to remove.
    """
    client = _client()
    response = await client.delete(
        f"/issues/{number}/labels/{label_name}", params={"repo": repo}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def replace_labels(repo: str, number: int, labels: list[str]) -> list:
    """Replace all labels on an issue.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
        labels: List of new label names to set.
    """
    client = _client()
    response = await client.put(
        f"/issues/{number}/labels", params={"repo": repo}, json={"labels": labels}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def list_labels(repo: str) -> list:
    """List all labels available in a repository.

    Args:
        repo: Repository as "owner/repo".
    """
    client = _client()
    response = await client.get("/labels", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def create_label(repo: str, name: str, color: str, description: str = "") -> dict:
    """Create a new label in a repository.

    Args:
        repo: Repository as "owner/repo".
        name: Name of the label.
        color: Hex color code (without hash, e.g. "ff0000").
        description: Optional label description.
    """
    client = _client()
    response = await client.post("/labels", params={"repo": repo}, json={"name": name, "color": color, "description": description})
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def assign_issue(repo: str, number: int, assignees: list[str]) -> list:
    """Assign users to an issue.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
        assignees: List of GitHub usernames to assign.
    """
    client = _client()
    response = await client.post(
        f"/issues/{number}/assign", params={"repo": repo}, json={"assignees": assignees}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def unassign_issue(repo: str, number: int, assignees: list[str]) -> list:
    """Remove users from an issue's assignees list.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
        assignees: List of GitHub usernames to unassign.
    """
    client = _client()
    response = await client.post(
        f"/issues/{number}/unassign", params={"repo": repo}, json={"assignees": assignees}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def list_assignees(repo: str) -> list:
    """List all users who can be assigned to issues in a repository.

    Args:
        repo: Repository as "owner/repo".
    """
    client = _client()
    response = await client.get("/assignees", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def comment_issue(repo: str, number: int, body: str) -> dict:
    """Add a comment to an issue.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
        body: Content of the comment.
    """
    client = _client()
    response = await client.post(
        f"/issues/{number}/comments", params={"repo": repo}, json={"body": body}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def edit_comment(repo: str, comment_id: int, body: str) -> dict:
    """Edit an existing issue comment.

    Args:
        repo: Repository as "owner/repo".
        comment_id: The ID of the comment to edit.
        body: The new body content.
    """
    client = _client()
    response = await client.patch(
        f"/comments/{comment_id}", params={"repo": repo}, json={"body": body}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def delete_comment(repo: str, comment_id: int) -> dict:
    """Delete an issue comment.

    Args:
        repo: Repository as "owner/repo".
        comment_id: The ID of the comment to delete.
    """
    client = _client()
    response = await client.delete(
        f"/comments/{comment_id}", params={"repo": repo}, headers=_user_token_headers()
    )
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def list_comments(repo: str, number: int) -> list:
    """List all comments on a specific issue.

    Args:
        repo: Repository as "owner/repo".
        number: The issue number.
    """
    client = _client()
    response = await client.get(f"/issues/{number}/comments", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


# --- GitHub Pull Requests MCP Tools ---

@mcp.tool()
async def create_pull_request(
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
    draft: bool = False,
) -> dict:
    """Create a new Pull Request in a repository.

    Args:
        repo: Repository as "owner/repo".
        title: Title of the pull request.
        head: The name of the branch where your changes are implemented.
        base: The name of the branch you want to merge your changes into (e.g. "main").
        body: Optional body description for the pull request.
        draft: Optional draft status (True to create a draft PR).
    """
    client = _client()
    body_data = {
        "title": title,
        "head": head,
        "base": base,
        "body": body,
        "draft": draft,
    }
    response = await client.post("/pulls", params={"repo": repo}, json=body_data)
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def get_pull_request(repo: str, number: int) -> dict:
    """Get comprehensive details of a specific Pull Request.

    Returns the complete structured information for a PR in a single call,
    including metadata, commits, reviews, issue comments, review comments,
    and changed files.

    Args:
        repo: Repository as "owner/repo".
        number: The PR number.
    """
    client = _client()
    response = await client.get(f"/pulls/{number}", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def update_pull_request(
    repo: str,
    number: int,
    title: str = None,
    body: str = None,
    state: str = None,
    base: str = None,
) -> dict:
    """Update details of a specific Pull Request.

    Args:
        repo: Repository as "owner/repo".
        number: The PR number.
        title: Optional new title.
        body: Optional new description.
        state: Optional state ("open" or "closed").
        base: Optional base branch to change to.
    """
    client = _client()
    body_data = {}
    if title is not None:
        body_data["title"] = title
    if body is not None:
        body_data["body"] = body
    if state is not None:
        body_data["state"] = state
    if base is not None:
        body_data["base"] = base

    response = await client.patch(f"/pulls/{number}", params={"repo": repo}, json=body_data)
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def close_pull_request(repo: str, number: int) -> dict:
    """Close a Pull Request.

    Args:
        repo: Repository as "owner/repo".
        number: The PR number.
    """
    client = _client()
    response = await client.post(f"/pulls/{number}/close", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def reopen_pull_request(repo: str, number: int) -> dict:
    """Reopen a closed Pull Request.

    Args:
        repo: Repository as "owner/repo".
        number: The PR number.
    """
    client = _client()
    response = await client.post(f"/pulls/{number}/reopen", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def merge_pull_request(
    repo: str,
    number: int,
    commit_title: str = None,
    commit_message: str = None,
    merge_method: str = "merge",
) -> dict:
    """Merge a Pull Request.

    Args:
        repo: Repository as "owner/repo".
        number: The PR number.
        commit_title: Optional title for the merge commit.
        commit_message: Optional message for the merge commit.
        merge_method: The merge method to use ("merge", "squash", or "rebase").
    """
    client = _client()
    body_data = {
        "merge_method": merge_method
    }
    if commit_title is not None:
        body_data["commit_title"] = commit_title
    if commit_message is not None:
        body_data["commit_message"] = commit_message

    response = await client.post(f"/pulls/{number}/merge", params={"repo": repo}, json=body_data)
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def list_pull_requests(
    repo: str,
    state: str = "open",
    head: str = None,
    base: str = None,
    sort: str = "created",
    direction: str = "desc",
) -> list:
    """List Pull Requests in a repository with optional filters.

    Args:
        repo: Repository as "owner/repo".
        state: PR state ("open", "closed", or "all").
        head: Filter by head branch (format: "user:ref-name" or "ref-name").
        base: Filter by base branch (e.g. "main").
        sort: Sort field ("created", "updated", "popularity", "long-running").
        direction: Sort direction ("asc" or "desc").
    """
    client = _client()
    params = {"repo": repo, "state": state, "sort": sort, "direction": direction}
    if head:
        params["head"] = head
    if base:
        params["base"] = base
    response = await client.get("/pulls", params=params)
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def search_pull_requests(repo: str, query: str) -> list:
    """Search for Pull Requests in a repository by a text query.

    Args:
        repo: Repository as "owner/repo".
        query: Search term (e.g. "auth refactor", "state:open author:arpit").
    """
    client = _client()
    response = await client.get("/pulls/search", params={"repo": repo, "q": query})
    _raise_for_status(response)
    return response.json()


# --- Commit Inspection MCP Tools ---

@mcp.tool()
async def get_commit_diff(repo: str, sha: str) -> dict:
    """Get the unified diff for all changes in a commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/diff", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def get_commit_files(repo: str, sha: str) -> list:
    """List all files changed in a commit with additions/deletions.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/files", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def get_commit_patch(repo: str, sha: str) -> dict:
    """Get the raw patches for changed files in a commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/patch", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def get_commit_stats(repo: str, sha: str) -> dict:
    """Get line addition/deletion stats for a commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/stats", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def get_commit_author(repo: str, sha: str) -> dict:
    """Get git author and GitHub login for a commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/author", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def get_commit_parents(repo: str, sha: str) -> dict:
    """Get the parent commit SHAs of a commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/parents", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def get_commit_branches(repo: str, sha: str) -> dict:
    """Get branches where this commit is the HEAD or part of.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/branches", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def get_commit_tags(repo: str, sha: str) -> dict:
    """Get tags pointing to this commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/tags", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def get_commit_signature(repo: str, sha: str) -> dict:
    """Get GPG/SSH signature verification status for a commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/signature", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def get_commit_status(repo: str, sha: str) -> dict:
    """Get the combined status checks and Action run conclusions for a commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/status", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


# --- Commit Context MCP Tools ---

@mcp.tool()
async def commit_pull_request(repo: str, sha: str) -> dict:
    """Get pull requests containing this commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/pulls", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def commit_issue(repo: str, sha: str) -> dict:
    """Get issues closed or referenced by PRs containing this commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/issues", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def commit_reviews(repo: str, sha: str) -> dict:
    """Get PR review approvals and comments for PRs containing this commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/reviews", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def commit_discussions(repo: str, sha: str) -> dict:
    """Get discussion comments and inline code review notes touching this commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/discussions", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def commit_release(repo: str, sha: str) -> dict:
    """Get the GitHub Release associated with this commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/release", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def commit_workflows(repo: str, sha: str) -> dict:
    """Get Actions workflow runs triggered by this commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/workflows", params={"repo": repo})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def commit_deployments(repo: str, sha: str) -> dict:
    """Get deployments containing this commit.

    Args:
        repo: Repository as "owner/repo".
        sha: The commit SHA.
    """
    client = _client()
    response = await client.get(f"/commits/{sha}/deployments", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


# --- History & Blame MCP Tools ---

@mcp.tool()
async def commit_history(
    repo: str,
    branch: str = "main",
    path: str = None,
    since: str = None,
    until: str = None,
    author: str = None,
    max_count: int = 50,
) -> dict:
    """Get commit history logs with optional path, date, and author filters.

    Args:
        repo: Repository as "owner/repo".
        branch: Branch to walk history from (default "main").
        path: Optional file path to filter.
        since: Optional ISO date start.
        until: Optional ISO date end.
        author: Optional author name or email filter.
        max_count: Max commits to return.
    """
    client = _client()
    params = {"repo": repo, "branch": branch, "max_count": max_count}
    if path:
        params["path"] = path
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if author:
        params["author"] = author
    response = await client.get("/history/commits", params=params)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def file_history(repo: str, path: str, branch: str = "main", max_count: int = 50) -> dict:
    """Get the commit history for a specific file (git log --follow).

    Args:
        repo: Repository as "owner/repo".
        path: Relative path to the file.
        branch: Branch name (default "main").
        max_count: Max commits to return.
    """
    client = _client()
    response = await client.get("/history/file", params={"repo": repo, "path": path, "branch": branch, "max_count": max_count})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def author_history(repo: str, author: str, since: str = None, until: str = None, max_count: int = 50) -> dict:
    """Get commits authored by a specific user.

    Args:
        repo: Repository as "owner/repo".
        author: GitHub username or email.
        since: Optional ISO date start.
        until: Optional ISO date end.
        max_count: Max commits to return.
    """
    client = _client()
    params = {"repo": repo, "author": author, "max_count": max_count}
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    response = await client.get("/history/author", params=params)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def branch_history(repo: str, branch: str, base: str = None, max_count: int = 50) -> dict:
    """Get commits on a branch since diverging from a base branch.

    Args:
        repo: Repository as "owner/repo".
        branch: The branch name.
        base: Optional base branch (e.g. "main").
        max_count: Max commits to return.
    """
    client = _client()
    params = {"repo": repo, "branch": branch, "max_count": max_count}
    if base:
        params["base"] = base
    response = await client.get("/history/branch", params=params)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def commit_graph(repo: str, branch: str = "main", max_count: int = 50) -> dict:
    """Get the commit DAG (nodes + parent edges) for visualization.

    Args:
        repo: Repository as "owner/repo".
        branch: Branch to walk (default "main").
        max_count: Max commits to return.
    """
    client = _client()
    response = await client.get("/history/graph", params={"repo": repo, "branch": branch, "max_count": max_count})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def blame_history(repo: str, path: str, branch: str = "main") -> dict:
    """Get line-level blame (author, date, commit) for a file.

    Args:
        repo: Repository as "owner/repo".
        path: Relative path to the file.
        branch: Branch name (default "main").
    """
    client = _client()
    response = await client.get("/history/blame", params={"repo": repo, "path": path, "branch": branch})
    _raise_for_status(response)
    return response.json()


# --- Search MCP Tools ---

@mcp.tool()
async def search_commits(repo: str, query: str, max_results: int = 30) -> dict:
    """Search commits using GitHub search query qualifiers.

    Args:
        repo: Repository as "owner/repo".
        query: Full search text.
        max_results: Max results to return.
    """
    client = _client()
    response = await client.get("/search/commits", params={"repo": repo, "q": query, "max_results": max_results})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def search_commit_message(repo: str, message: str, max_results: int = 30) -> dict:
    """Search commits by message content.

    Args:
        repo: Repository as "owner/repo".
        message: Text phrase to search in commit messages.
        max_results: Max results to return.
    """
    client = _client()
    response = await client.get("/search/commits/message", params={"repo": repo, "message": message, "max_results": max_results})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def search_by_author(repo: str, author: str, max_results: int = 30) -> dict:
    """Search commits authored by a specific user.

    Args:
        repo: Repository as "owner/repo".
        author: Username or email.
        max_results: Max results to return.
    """
    client = _client()
    response = await client.get("/search/commits/author", params={"repo": repo, "author": author, "max_results": max_results})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def search_by_file(repo: str, path: str, max_results: int = 30) -> dict:
    """Search commits that touched a file path.

    Args:
        repo: Repository as "owner/repo".
        path: File path.
        max_results: Max results to return.
    """
    client = _client()
    response = await client.get("/search/commits/file", params={"repo": repo, "path": path, "max_results": max_results})
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def search_by_date(repo: str, since: str, until: str = None, max_results: int = 30) -> dict:
    """Search commits within a date range.

    Args:
        repo: Repository as "owner/repo".
        since: Start date ISO.
        until: Optional end date ISO.
        max_results: Max results to return.
    """
    client = _client()
    params = {"repo": repo, "since": since, "max_results": max_results}
    if until:
        params["until"] = until
    response = await client.get("/search/commits/date", params=params)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def search_by_hash(repo: str, sha: str) -> dict:
    """Get commit by full or partial SHA hash.

    Args:
        repo: Repository as "owner/repo".
        sha: Hash prefix or full SHA.
    """
    client = _client()
    response = await client.get("/search/commits/hash", params={"repo": repo, "sha": sha})
    _raise_for_status(response)
    return response.json()


# --- Local Git Operation MCP Tools ---

@mcp.tool()
async def git_status(repo_path: str = None) -> dict:
    """Show porcelain status of the local repository.

    Args:
        repo_path: Optional local repository absolute path.
    """
    client = _client()
    params = {}
    if repo_path:
        params["repo_path"] = repo_path
    response = await client.get("/git/status", params=params)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_commit(message: str, repo_path: str = None, add_all: bool = True) -> dict:
    """Stage and commit local files.

    Args:
        message: Commit message description.
        repo_path: Optional local repository absolute path.
        add_all: Automatically stage all changes (default: True).
    """
    client = _client()
    body = {"message": message, "add_all": add_all}
    if repo_path:
        body["repo_path"] = repo_path
    response = await client.post("/git/commit", json=body)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_push(repo_path: str = None, remote: str = "origin", branch: str = None, force: bool = False) -> dict:
    """Push local commits to a remote.

    Args:
        repo_path: Optional local repository absolute path.
        remote: Remote name (default "origin").
        branch: Branch to push.
        force: Force push with lease verification.
    """
    client = _client()
    body = {"remote": remote, "force": force}
    if repo_path:
        body["repo_path"] = repo_path
    if branch:
        body["branch"] = branch
    response = await client.post("/git/push", json=body)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_pull(repo_path: str = None, remote: str = "origin", branch: str = None, rebase: bool = False) -> dict:
    """Pull upstream commits.

    Args:
        repo_path: Optional local repository absolute path.
        remote: Remote name (default "origin").
        branch: Branch to pull.
        rebase: Pull with rebase instead of merge.
    """
    client = _client()
    body = {"remote": remote, "rebase": rebase}
    if repo_path:
        body["repo_path"] = repo_path
    if branch:
        body["branch"] = branch
    response = await client.post("/git/pull", json=body)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_switch_branch(branch: str, repo_path: str = None, create: bool = False) -> dict:
    """Switch/checkout a local branch.

    Args:
        branch: Branch name to switch to.
        repo_path: Optional local repository absolute path.
        create: Create the branch if it does not exist.
    """
    client = _client()
    body = {"branch": branch, "create": create}
    if repo_path:
        body["repo_path"] = repo_path
    response = await client.post("/git/switch", json=body)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_create_branch(name: str, from_ref: str = None, repo_path: str = None, checkout: bool = False) -> dict:
    """Create a new local branch.

    Args:
        name: Name of the branch to create.
        from_ref: Optional source ref (tag/sha/branch).
        repo_path: Optional local repository absolute path.
        checkout: Checkout the new branch immediately.
    """
    client = _client()
    body = {"name": name, "checkout": checkout}
    if from_ref:
        body["from_ref"] = from_ref
    if repo_path:
        body["repo_path"] = repo_path
    response = await client.post("/git/branch", json=body)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_merge(branch: str, repo_path: str = None, strategy: str = None, no_ff: bool = True, message: str = None) -> dict:
    """Merge a branch into the active branch.

    Args:
        branch: Branch name to merge.
        repo_path: Optional local repository absolute path.
        strategy: Custom merge strategy.
        no_ff: Create merge commit instead of fast-forwarding.
        message: Custom merge commit message.
    """
    client = _client()
    body = {"branch": branch, "no_ff": no_ff}
    if repo_path:
        body["repo_path"] = repo_path
    if strategy:
        body["strategy"] = strategy
    if message:
        body["message"] = message
    response = await client.post("/git/merge", json=body)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_rebase(onto: str, repo_path: str = None, interactive: bool = False) -> dict:
    """Rebase active commits onto a base branch.

    Args:
        onto: Base branch or SHA.
        repo_path: Optional local repository absolute path.
        interactive: Run in interactive mode.
    """
    client = _client()
    body = {"onto": onto, "interactive": interactive}
    if repo_path:
        body["repo_path"] = repo_path
    response = await client.post("/git/rebase", json=body)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_stash(action: str = "push", message: str = None, repo_path: str = None, index: int = None) -> dict:
    """Stash/Pop changes.

    Args:
        action: push, pop, list, apply, drop, show.
        message: Optional comment for push action.
        repo_path: Optional local repository absolute path.
        index: Stash index.
    """
    client = _client()
    body = {"action": action}
    if message:
        body["message"] = message
    if repo_path:
        body["repo_path"] = repo_path
    if index is not None:
        body["index"] = index
    response = await client.post("/git/stash", json=body)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_sync(repo_path: str = None, remote: str = "origin", branch: str = None) -> dict:
    """Synchronize with remote (pull with rebase, then push).

    Args:
        repo_path: Optional local repository absolute path.
        remote: Remote name (default "origin").
        branch: Target branch to sync.
    """
    client = _client()
    body = {"remote": remote}
    if repo_path:
        body["repo_path"] = repo_path
    if branch:
        body["branch"] = branch
    response = await client.post("/git/sync", json=body)
    _raise_for_status(response)
    return response.json()

@mcp.tool()
async def git_smart_push(
    message: str,
    repo_path: str = None,
    remote: str = "origin",
    branch: str = None,
    add_all: bool = True,
    force: bool = False,
    pull_before_push: bool = True,
) -> dict:
    """Stage, commit, pull rebase, and push in one action.

    Args:
        message: The commit message.
        repo_path: Optional local repository absolute path.
        remote: Remote name (default "origin").
        branch: Target branch to push.
        add_all: Stage all changes before committing.
        force: Force push with lease verification.
        pull_before_push: Rebase with remote changes before pushing.
    """
    client = _client()
    body = {
        "message": message,
        "remote": remote,
        "add_all": add_all,
        "force": force,
        "pull_before_push": pull_before_push,
    }
    if repo_path:
        body["repo_path"] = repo_path
    if branch:
        body["branch"] = branch
    response = await client.post("/git/smart-push", json=body)
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def check_user_notifications(repo: str, username: str = None) -> dict:
    """Check for new @mentions and file-touch notifications for a user.

    If username is not provided, defaults to the current active user configured via
    the CURRENT_USER environment variable (default: 'arpit').

    Args:
        repo: Repository as "owner/repo".
        username: Optional GitHub username to check.
    """
    if not username:
        username = os.getenv("CURRENT_USER", "arpit")
    client = _client()
    response = await client.get(f"/changelog/user/{username}/notifications", params={"repo": repo})
    _raise_for_status(response)
    return response.json()


def main() -> None:
    import sys
    global DEVBRAIN_API_URL
    for i, arg in enumerate(sys.argv):
        if arg == "--api-url" and i + 1 < len(sys.argv):
            DEVBRAIN_API_URL = sys.argv[i + 1].rstrip("/")
            # Remove from sys.argv so FastMCP doesn't complain about unknown args
            sys.argv.pop(i) # pop --api-url
            sys.argv.pop(i) # pop value
            break
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
