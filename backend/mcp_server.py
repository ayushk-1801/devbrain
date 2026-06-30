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


def _raise_for_status(response: httpx.Response) -> None:
    """Surface HTTP errors as readable MCP tool errors."""
    if response.is_error:
        raise RuntimeError(
            f"DevBrain API error {response.status_code}: {response.text[:200]}"
        )


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    async with httpx.AsyncClient(base_url=DEVBRAIN_API_URL, timeout=120) as client:
        server.state.http = client
        logger.info("DevBrain MCP client connected to %s", DEVBRAIN_API_URL)
        yield


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
    """Ingest a GitHub repo's history into DevBrain's memory.

    Fetches commits, pull requests, issues, ADRs, and code structure and builds
    the knowledge graph. Run this once per repo before querying. Use
    `sync_history_days` to limit how far back history is pulled.

    Args:
        repo: Target repository as "owner/repo".
        sync_history_days: Optional window (days). None = all history.

    Returns:
        Per-source ingestion counts.
    """
    client: httpx.AsyncClient = mcp.state.http
    body: dict = {"repo": repo}
    if sync_history_days is not None:
        body["sync_history_days"] = sync_history_days
    response = await client.post("/ingest", json=body)
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
    client: httpx.AsyncClient = mcp.state.http
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
    client: httpx.AsyncClient = mcp.state.http
    response = await client.delete(f"/module/{owner}/{name}/{module}")
    _raise_for_status(response)
    return response.json()


@mcp.tool()
async def list_repos() -> dict:
    """List all repositories that have been ingested into DevBrain."""
    client: httpx.AsyncClient = mcp.state.http
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
    client: httpx.AsyncClient = mcp.state.http
    params: dict = {}
    if repo:
        params["repo"] = repo
    response = await client.post("/refresh", params=params)
    _raise_for_status(response)
    return response.json()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
