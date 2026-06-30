"""DevBrain FastAPI application (REST + GitHub webhook).

This is one of two interfaces over the shared service layer (the other is the
MCP server in ``backend/mcp_server.py``). Both are fully multi-repo: the repo is
passed per request.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from backend import service
from backend.config import settings, split_repo
from backend.memory import client as memory
from backend.memory.improve import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devbrain")

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await memory.connect()
    global _scheduler
    _scheduler = start_scheduler()
    logger.info("DevBrain REST started in %s mode", settings.COGNEE_MODE)
    try:
        yield
    finally:
        if _scheduler:
            _scheduler.shutdown(wait=False)
        await memory.disconnect()


app = FastAPI(title="DevBrain", version="0.1.0", lifespan=lifespan)


# --- Models --------------------------------------------------------------


class IngestRequest(BaseModel):
    repo: str
    sync_history_days: int | None = None


# --- Routes --------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "cognee_mode": settings.COGNEE_MODE}


@app.get("/repos")
async def repos() -> dict:
    """List all ingested repos."""
    return {"repos": service.list_repos()}


@app.post("/ingest")
async def ingest(req: IngestRequest) -> dict:
    """Full historical sync for a repo (commits, PRs, ADRs, code structure)."""
    try:
        return await service.full_sync(req.repo, req.sync_history_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/query")
async def query(
    q: str = Query(..., description="natural language question"),
    repo: str | None = Query(None),
    mode: str = Query("hybrid", description="hybrid | why | chunks"),
) -> dict:
    """Natural language recall over the knowledge graph."""
    try:
        return await service.query(q, repo=repo, mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/refresh")
async def refresh(repo: str | None = Query(None)) -> dict:
    """Run Cognee memify enrichment for one repo, or all ingested repos if omitted."""
    try:
        return await service.refresh(repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/module/{owner}/{repo}/{module}")
async def prune_module(owner: str, repo: str, module: str) -> dict:
    """Surgically prune a deprecated module's subgraph."""
    try:
        return await service.forget_module(f"{owner}/{repo}", module)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- Webhook -------------------------------------------------------------


def _verify_signature(body: bytes, signature: str | None) -> bool:
    """Verify GitHub's X-Hub-Signature-256 HMAC against the configured secret."""
    secret = settings.GITHUB_WEBHOOK_SECRET
    if not secret:
        # No secret configured -> skip verification (dev convenience only).
        return True
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _handle_push(repo: str, payload: dict) -> None:
    """Incremental ingest of pushed commits (changed files only)."""
    for commit_ref in payload.get("commits", []):
        sha = commit_ref.get("id")
        if not sha:
            continue
        try:
            await service.ingest_single_commit(repo, sha)
        except Exception:
            logger.exception("failed to ingest pushed commit %s", sha)


async def _handle_pull_request(repo: str, payload: dict) -> None:
    """Ingest a PR on open/edit/sync (captures discussion before merge) and on merge."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    if action not in ("opened", "edited", "synchronize", "closed"):
        return
    if action == "closed" and not pr.get("merged"):
        return  # closed without merging — skip
    try:
        await service.ingest_single_pr(repo, pr["number"])
    except Exception:
        logger.exception("failed to ingest PR #%s", pr.get("number"))


async def _handle_issue(repo: str, payload: dict) -> None:
    """Ingest an issue when opened, labeled, or closed."""
    if payload.get("action") not in ("opened", "labeled", "closed"):
        return
    issue = payload.get("issue", {})
    try:
        await service.ingest_single_issue(repo, issue["number"])
    except Exception:
        logger.exception("failed to ingest issue #%s", issue.get("number"))


async def _handle_pr_review_comment(repo: str, payload: dict) -> None:
    """Ingest a newly created PR inline review comment."""
    if payload.get("action") != "created":
        return
    comment = payload.get("comment", {})
    try:
        await service.ingest_pr_review_comment(repo, comment["id"])
    except Exception:
        logger.exception("failed to ingest PR review comment #%s", comment.get("id"))


_WEBHOOK_DISPATCH = {
    "push": _handle_push,
    "pull_request": _handle_pull_request,
    "issues": _handle_issue,
    "pull_request_review_comment": _handle_pr_review_comment,
}


@app.post("/webhook/github")
async def github_webhook(request: Request) -> dict:
    """GitHub webhook receiver for push, pull_request, issues, and review comment events.

    Verifies the signature, then dispatches ingestion as a background task so the
    webhook returns immediately (never block the response).
    """
    body = await request.body()
    if not _verify_signature(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=401, detail="invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    full_name = payload.get("repository", {}).get("full_name", "")
    if "/" not in full_name:
        raise HTTPException(status_code=400, detail="missing repository.full_name")
    split_repo(full_name)

    handler = _WEBHOOK_DISPATCH.get(event)
    if handler:
        asyncio.create_task(handler(full_name, payload))
        return {"status": "accepted", "event": event}
    return {"status": "ignored", "event": event}
