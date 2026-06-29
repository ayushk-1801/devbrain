"""DevBrain MCP server.

Exposes DevBrain's living engineering memory to MCP-capable agents (Claude Code,
Cursor, etc.) over stdio. The agent supplies the target ``repo`` ("owner/repo")
as a parameter on each tool call, so a single server works across any number of
repositories the configured GITHUB_TOKEN can read.

GitHub access uses the server's env token (GITHUB_TOKEN); Cognee uses the same
local-Gemini / Cloud configuration as the REST app (see backend.memory.client).

Run:
    python -m backend.mcp_server          # stdio transport
or register with Claude Code:
    claude mcp add devbrain -- python -m backend.mcp_server
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from backend import service
from backend.config import settings
from backend.ingestion import issues
from backend.memory import client as memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devbrain.mcp")


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Connect Cognee once when the MCP server starts; disconnect on shutdown."""
    await memory.connect()
    logger.info("DevBrain MCP server started in %s mode", settings.COGNEE_MODE)
    try:
        yield
    finally:
        await memory.disconnect()


mcp = FastMCP(
    "DevBrain",
    instructions=(
        "DevBrain is a living engineering memory. It ingests a GitHub repo's "
        "commits, pull requests, ADRs, and code structure into a knowledge graph, "
        "then answers 'why was this changed?' questions with sourced provenance. "
        "Call `ingest_repo` first for a repo, then `query_devbrain`. All tools take "
        "an explicit `repo` of the form 'owner/repo'."
    ),
    lifespan=lifespan,
)


@mcp.tool()
async def ingest_repo(repo: str, sync_history_days: int | None = None) -> dict:
    """Ingest a GitHub repo's history into DevBrain's memory.

    Fetches commits, merged pull requests, ADRs, and code structure and builds
    the knowledge graph. Run this once per repo before querying. Use
    `sync_history_days` to limit how far back commits/PRs are pulled.

    Args:
        repo: Target repository as "owner/repo".
        sync_history_days: Optional window (days) for commits/PRs. None = all.

    Returns:
        Per-source ingestion counts.
    """
    return await service.full_sync(repo, sync_history_days)


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
    result = await service.query(question, repo=repo, mode=mode)
    # Stringify Cognee results so the payload is always JSON-serialisable.
    return {
        "question": result["question"],
        "repo": result["repo"],
        "mode": result["mode"],
        "answer": str(result["answer"]) if result["answer"] is not None else None,
        "results": [str(r) for r in (result.get("results") or [])],
    }


@mcp.tool()
async def forget_module(repo: str, module: str) -> dict:
    """Surgically prune a deprecated module's subgraph from a repo's memory.

    Args:
        repo: Target repository as "owner/repo".
        module: The module/path being deprecated (required, must be non-empty).

    Returns:
        Status of the prune operation.
    """
    return await service.forget_module(repo, module)


@mcp.tool()
async def list_repos() -> dict:
    """List all repositories that have been ingested into DevBrain."""
    return {"repos": service.list_repos()}


@mcp.tool()
async def refresh_memory(repo: str | None = None) -> dict:
    """Run Cognee's (expensive) memify enrichment for one repo, or all if omitted.

    Strengthens frequently-traversed paths and derives new facts. This is a
    heavy operation — invoke deliberately, not on every change.

    Args:
        repo: Optional "owner/repo". Omit to refresh every ingested repo.
    """
    return await service.refresh(repo)


@mcp.tool()
async def ingest_issues(owner: str, repo: str, sync_history_days: int | None = None) -> dict:
    """Ingest a GitHub repo's closed issues and their comment discussions into DevBrain's memory.

    Fetches closed issues and builds the knowledge graph with their discussion context.
    Run this once per repo before querying issue-related questions. Use
    `sync_history_days` to limit how far back issues are pulled.

    Args:
        owner: Repository owner as "owner".
        repo: Repository name as "repo_name".
        sync_history_days: Optional window (days) for issues. None = all closed issues.

    Returns:
        Per-source ingestion counts including issues.
    """
    return await service.full_sync(f"{owner}/{repo}", sync_history_days)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
