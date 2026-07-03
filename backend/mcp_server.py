"""DevBrain MCP server — thin HTTP client over the hosted DevBrain backend.

This process runs locally (stdio transport) for each user and proxies every tool
call to the DevBrain REST API at DEVBRAIN_API_URL. Users need only that URL — no
GitHub token, no Cognee config, no LLM keys.

The maintainer runs one backend (main.py) with all secrets; users point this
server at it:

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

    response = await client.post("/issues", params={"repo": repo}, json=body_data)
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

    response = await client.patch(f"/issues/{number}", params={"repo": repo}, json=body_data)
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
    response = await client.post(f"/issues/{number}/close", params={"repo": repo})
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
    response = await client.post(f"/issues/{number}/reopen", params={"repo": repo})
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
    response = await client.post(f"/issues/{number}/labels", params={"repo": repo}, json={"labels": labels})
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
    response = await client.delete(f"/issues/{number}/labels/{label_name}", params={"repo": repo})
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
    response = await client.put(f"/issues/{number}/labels", params={"repo": repo}, json={"labels": labels})
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
    response = await client.post(f"/issues/{number}/assign", params={"repo": repo}, json={"assignees": assignees})
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
    response = await client.post(f"/issues/{number}/unassign", params={"repo": repo}, json={"assignees": assignees})
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
    response = await client.post(f"/issues/{number}/comments", params={"repo": repo}, json={"body": body})
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
    response = await client.patch(f"/comments/{comment_id}", params={"repo": repo}, json={"body": body})
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
    response = await client.delete(f"/comments/{comment_id}", params={"repo": repo})
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
