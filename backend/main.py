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
from backend import issues_service
from backend.changelog import notifier as cl_notifier
from backend.changelog import profile as cl_profile
from backend.changelog import tracker as cl_tracker
from backend.changelog.global_changelog import (
    generate_global_changelog,
    get_global_changelog_path,
)
from backend.changelog.user_updates import (
    generate_user_updates,
    get_user_updates_path,
)
from backend.config import settings, split_repo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devbrain")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The API process never opens Kuzu directly — all DB access goes through
    # the ARQ worker, which holds the single Kuzu connection.
    logger.info("DevBrain REST started in %s mode", settings.COGNEE_MODE)
    yield


app = FastAPI(title="DevBrain", version="0.1.0", lifespan=lifespan)

# Keeps strong references to background tasks so the GC cannot collect them
# mid-execution. Tasks remove themselves when done.
_bg_tasks: set[asyncio.Task] = set()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models --------------------------------------------------------------


class IngestRequest(BaseModel):
    repo: str
    sync_history_days: int | None = None


class SubscribeRequest(BaseModel):
    repo: str
    username: str
    notify_webhook: str | None = None  # optional webhook URL for push notifications


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
    """Enqueue a full historical sync for a repo. Returns a job_id immediately."""
    try:
        job_id = await service.enqueue_full_sync(req.repo, req.sync_history_days)
        return {"job_id": job_id, "status": "queued", "repo": req.repo}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/jobs/{job_id}")
async def job_status(job_id: str) -> dict:
    """Poll the status of an enqueued job. Status: queued | in_progress | complete | not_found."""
    return await service.get_job_status(job_id)


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


@app.get("/graph")
async def graph_data(repo: str | None = Query(None)) -> dict:
    """Return the full knowledge graph (nodes + edges) for visualization."""
    try:
        return await service.get_graph_data(repo=repo)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# --- Changelog & user-update routes -------------------------------------


@app.post("/changelog/generate")
async def changelog_generate(
    repo: str = Query(..., description="owner/repo"),
    notify: bool = Query(False, description="Send notifications after generating"),
) -> dict:
    """Generate (or regenerate) the global changelog for a repo and optionally
    notify all subscribed users.

    Returns a summary JSON and writes two types of Markdown files:
    - ``GLOBAL_CHANGELOG_{repo}.md`` — every event since the last run
    - ``USER_UPDATES_{user}_{repo}.md`` — one per subscribed user
    """
    try:
        owner, name = split_repo(repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        cl, md_path = await generate_global_changelog(owner, name)
    except Exception as exc:
        logger.exception("Failed to generate global changelog for %s", repo)
        raise HTTPException(status_code=500, detail=str(exc))

    user_updates_map: dict = {}
    subscribed = await cl_tracker.list_subscribed_users(repo)
    for username in subscribed:
        try:
            updates, _ = await generate_user_updates(
                owner, name, username, global_changelog=cl
            )
            user_updates_map[username] = updates
        except Exception:
            logger.exception(
                "Failed to generate user updates for %s on %s", username, repo
            )

    if notify:
        _t = asyncio.create_task(cl_notifier.dispatch_all_users(repo, cl, user_updates_map))
        _bg_tasks.add(_t)
        _t.add_done_callback(_bg_tasks.discard)

    return {
        "repo": repo,
        "global_changelog_file": str(md_path),
        "total_events": cl.total_events(),
        "counts": {
            "commits": len(cl.commits),
            "pull_requests": len(cl.pull_requests),
            "issues": len(cl.issues),
            "releases": len(cl.releases),
        },
        "since": cl.since.isoformat() if cl.since else None,
        "generated_at": cl.generated_at.isoformat(),
        "users_notified": list(user_updates_map.keys()),
    }


@app.post("/changelog/backfill")
async def changelog_backfill(
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    """Manually trigger historical backfilling of the Redis user profiles.

    Retrieves all past commits, PRs, comments, and reviews for a repo
    and populates Redis file ownership, mentions, and file touches.
    """
    try:
        owner, name = split_repo(repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        await cl_profile.backfill_profiles(repo)
        return {
            "repo": repo,
            "status": "success",
            "message": "Historical profile backfill completed successfully.",
        }
    except Exception as exc:
        logger.exception("Failed to run backfill for %s", repo)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/changelog")
async def changelog_read(
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    """Read the latest global changelog for a repo.

    Returns the raw Markdown content plus metadata.  Generate it first with
    ``POST /changelog/generate`` if it does not exist yet.
    """
    try:
        owner, name = split_repo(repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    path = get_global_changelog_path(owner, name)
    if not path:
        raise HTTPException(
            status_code=404,
            detail=f"No changelog found for {repo}. Run POST /changelog/generate first.",
        )

    content = path.read_text(encoding="utf-8")
    last_sync = await cl_tracker.get_last_global_sync(repo)
    return {
        "repo": repo,
        "file": str(path),
        "last_generated": last_sync.isoformat() if last_sync else None,
        "content": content,
    }


@app.get("/changelog/user/{username}")
async def changelog_user(
    username: str,
    repo: str = Query(..., description="owner/repo"),
    refresh: bool = Query(
        False, description="Re-fetch from GitHub instead of reading cached file"
    ),
) -> dict:
    """Return the update digest for a specific user.

    By default returns the cached Markdown file.  Pass ``?refresh=true`` to
    re-generate it from GitHub and update the user's watermark.
    """
    try:
        owner, name = split_repo(repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if refresh:
        try:
            updates, path = await generate_user_updates(owner, name, username)
            await cl_notifier.dispatch_user(repo, username, updates)
        except Exception as exc:
            logger.exception(
                "Failed to generate user updates for %s on %s", username, repo
            )
            raise HTTPException(status_code=500, detail=str(exc))
    else:
        path = get_user_updates_path(owner, name, username)
        if not path:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No updates file found for @{username} on {repo}. "
                    f"Run GET /changelog/user/{username}?repo={repo}&refresh=true to generate."
                ),
            )

    content = path.read_text(encoding="utf-8")
    last_seen = await cl_tracker.get_last_user_seen(repo, username)
    return {
        "repo": repo,
        "username": username,
        "file": str(path),
        "last_generated": last_seen.isoformat() if last_seen else None,
        "content": content,
    }


@app.post("/changelog/subscribe")
async def changelog_subscribe(req: SubscribeRequest) -> dict:
    """Register a user to receive update digests for a repo.

    Optionally provide a ``notify_webhook`` URL — DevBrain will POST a JSON
    summary there every time ``POST /changelog/generate?notify=true`` is called.
    """
    try:
        split_repo(req.repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Registering the user without a webhook is valid (they can poll the API).
    if req.notify_webhook:
        await cl_tracker.set_user_webhook(req.repo, req.username, req.notify_webhook)
    else:
        # Touch the user entry so they appear in list_subscribed_users().
        from datetime import datetime, timezone

        existing = await cl_tracker.get_last_user_seen(req.repo, req.username)
        await cl_tracker.set_last_user_seen(
            req.repo, req.username, existing or datetime.now(timezone.utc)
        )

    return {
        "status": "subscribed",
        "repo": req.repo,
        "username": req.username,
        "webhook_registered": bool(req.notify_webhook),
    }


@app.get("/changelog/subscribers")
async def changelog_subscribers(
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    """List all users subscribed to changelog updates for a repo."""
    try:
        split_repo(repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    users = await cl_tracker.list_subscribed_users(repo)
    return {"repo": repo, "subscribers": users}


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
    """Enqueue incremental ingest for each pushed commit."""
    # Update user profiles from the push payload (zero extra API calls —
    # the payload already contains message, author, and changed file lists).
    try:
        await cl_profile.update_from_push(repo, payload)
    except Exception:
        logger.exception("profile update failed for push on %s", repo)

    for commit_ref in payload.get("commits", []):
        sha = commit_ref.get("id")
        if not sha:
            continue
        try:
            job_id = await service.enqueue_single_commit(repo, sha)
            logger.info("enqueued commit %s → job %s", sha, job_id)
        except Exception:
            logger.exception("failed to enqueue pushed commit %s", sha)


async def _handle_pull_request(repo: str, payload: dict) -> None:
    """Enqueue PR ingest on open/edit/sync and on merge."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    if action not in ("opened", "edited", "synchronize", "closed"):
        return
    if action == "closed" and not pr.get("merged"):
        return

    # Scan PR body for @mentions on open and edit only (not every sync).
    if action in ("opened", "edited"):
        try:
            await cl_profile.update_from_pull_request(repo, payload)
        except Exception:
            logger.exception(
                "profile update failed for PR #%s on %s", pr.get("number"), repo
            )

    try:
        job_id = await service.enqueue_single_pr(repo, pr["number"])
        logger.info("enqueued PR #%s → job %s", pr["number"], job_id)
    except Exception:
        logger.exception("failed to enqueue PR #%s", pr.get("number"))


async def _handle_issue(repo: str, payload: dict) -> None:
    """Enqueue issue ingest when opened, labeled, or closed."""
    if payload.get("action") not in ("opened", "labeled", "closed"):
        return
    issue = payload.get("issue", {})

    # Scan issue body for @mentions when opened.
    if payload.get("action") == "opened":
        try:
            await cl_profile.update_from_issue(repo, payload)
        except Exception:
            logger.exception(
                "profile update failed for issue #%s on %s", issue.get("number"), repo
            )

    try:
        job_id = await service.enqueue_single_issue(repo, issue["number"])
        logger.info("enqueued issue #%s → job %s", issue["number"], job_id)
    except Exception:
        logger.exception("failed to enqueue issue #%s", issue.get("number"))


async def _handle_pr_review_comment(repo: str, payload: dict) -> None:
    """Enqueue ingest of a newly created PR inline review comment."""
    if payload.get("action") != "created":
        return
    comment = payload.get("comment", {})

    # Scan inline comment body for @mentions.
    try:
        await cl_profile.update_from_pr_review_comment(repo, payload)
    except Exception:
        logger.exception(
            "profile update failed for review comment #%s on %s",
            comment.get("id"),
            repo,
        )

    try:
        job_id = await service.enqueue_pr_review_comment(repo, comment["id"])
        logger.info("enqueued review comment %s → job %s", comment["id"], job_id)
    except Exception:
        logger.exception("failed to enqueue PR review comment #%s", comment.get("id"))


async def _handle_release(repo: str, payload: dict) -> None:
    """Enqueue ingest when a release is published."""
    if payload.get("action") != "published":
        return
    try:
        release = payload.get("release", {})
        tag = release.get("tag_name", "")
        await service.enqueue_release(repo, tag)
        logger.info("enqueued release %s for %s", tag, repo)
    except Exception:
        logger.exception("failed to enqueue release for %s", repo)


async def _handle_pull_request_review(repo: str, payload: dict) -> None:
    """Enqueue ingest of a PR review summary."""
    # Record the reviewer and scan the review body for @mentions.
    try:
        await cl_profile.update_from_pr_review(repo, payload)
    except Exception:
        logger.exception("profile update failed for PR review on %s", repo)

    try:
        pr_number = payload.get("pull_request", {}).get("number")
        review_id = payload.get("review", {}).get("id")
        if pr_number and review_id:
            await service.enqueue_pr_review(repo, pr_number, review_id)
            logger.info("enqueued PR review %s for PR #%s", review_id, pr_number)
    except Exception:
        logger.exception("failed to enqueue PR review for %s", repo)


_WEBHOOK_DISPATCH = {
    "push": _handle_push,
    "pull_request": _handle_pull_request,
    "issues": _handle_issue,
    "pull_request_review_comment": _handle_pr_review_comment,
    "release": _handle_release,
    "pull_request_review": _handle_pull_request_review,
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
        await handler(full_name, payload)
        return {"status": "accepted", "event": event}
    return {"status": "ignored", "event": event}


# --- GitHub Issues REST API Endpoints ---

class CreateIssueRequest(BaseModel):
    title: str
    body: str = ""
    labels: list[str] = None
    assignees: list[str] = None
    milestone: int = None

class UpdateIssueRequest(BaseModel):
    title: str = None
    body: str = None
    state: str = None
    labels: list[str] = None
    milestone: int = None
    assignees: list[str] = None

class AddLabelsRequest(BaseModel):
    labels: list[str]

class CreateLabelRequest(BaseModel):
    name: str
    color: str
    description: str = ""

class AssignIssueRequest(BaseModel):
    assignees: list[str]

class CommentIssueRequest(BaseModel):
    body: str


@app.post("/issues")
async def api_create_issue(
    req: CreateIssueRequest,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.create_issue(
            repo, req.title, req.body, req.labels, req.assignees, req.milestone
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/issues/{number}")
async def api_get_issue(
    number: int,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.get_issue(repo, number)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.patch("/issues/{number}")
async def api_update_issue(
    number: int,
    req: UpdateIssueRequest,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.update_issue(
            repo, number, req.title, req.body, req.state, req.labels, req.milestone, req.assignees
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/issues/{number}/close")
async def api_close_issue(
    number: int,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.close_issue(repo, number)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/issues/{number}/reopen")
async def api_reopen_issue(
    number: int,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.reopen_issue(repo, number)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/issues")
async def api_list_issues(
    repo: str = Query(..., description="owner/repo"),
    state: str = Query("open", description="open | closed | all"),
    assignee: str = Query(None),
    creator: str = Query(None),
    mentioned: str = Query(None),
    labels: list[str] = Query(None),
) -> list[dict]:
    try:
        return await issues_service.list_issues(
            repo, state, assignee, creator, mentioned, labels
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/issues/search")
async def api_search_issues(
    q: str = Query(..., description="search query"),
    repo: str = Query(..., description="owner/repo"),
) -> list[dict]:
    try:
        return await issues_service.search_issues(repo, q)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/issues/my-issues")
async def api_list_my_issues(
    username: str = Query(..., description="GitHub username"),
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.list_my_issues(repo, username)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/issues/{number}/labels")
async def api_add_labels(
    number: int,
    req: AddLabelsRequest,
    repo: str = Query(..., description="owner/repo"),
) -> list[str]:
    try:
        return await issues_service.add_labels(repo, number, req.labels)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/issues/{number}/labels/{label_name}")
async def api_remove_label(
    number: int,
    label_name: str,
    repo: str = Query(..., description="owner/repo"),
) -> list[str]:
    try:
        return await issues_service.remove_label(repo, number, label_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/issues/{number}/labels")
async def api_replace_labels(
    number: int,
    req: AddLabelsRequest,
    repo: str = Query(..., description="owner/repo"),
) -> list[str]:
    try:
        return await issues_service.replace_labels(repo, number, req.labels)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/labels")
async def api_list_labels(
    repo: str = Query(..., description="owner/repo"),
) -> list[dict]:
    try:
        return await issues_service.list_labels(repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/labels")
async def api_create_label(
    req: CreateLabelRequest,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.create_label(repo, req.name, req.color, req.description)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/issues/{number}/assign")
async def api_assign_issue(
    number: int,
    req: AssignIssueRequest,
    repo: str = Query(..., description="owner/repo"),
) -> list[str]:
    try:
        return await issues_service.assign_issue(repo, number, req.assignees)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/issues/{number}/unassign")
async def api_unassign_issue(
    number: int,
    req: AssignIssueRequest,
    repo: str = Query(..., description="owner/repo"),
) -> list[str]:
    try:
        return await issues_service.unassign_issue(repo, number, req.assignees)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/assignees")
async def api_list_assignees(
    repo: str = Query(..., description="owner/repo"),
) -> list[str]:
    try:
        return await issues_service.list_assignees(repo)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/issues/{number}/comments")
async def api_comment_issue(
    number: int,
    req: CommentIssueRequest,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.comment_issue(repo, number, req.body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.patch("/comments/{comment_id}")
async def api_edit_comment(
    comment_id: int,
    req: CommentIssueRequest,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.edit_comment(repo, comment_id, req.body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/comments/{comment_id}")
async def api_delete_comment(
    comment_id: int,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await issues_service.delete_comment(repo, comment_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/issues/{number}/comments")
async def api_list_comments(
    number: int,
    repo: str = Query(..., description="owner/repo"),
) -> list[dict]:
    try:
        return await issues_service.list_comments(repo, number)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
