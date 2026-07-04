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
from backend import pr_service
from backend import commit_service
from backend import history_service
from backend import search_service
from backend import git_service
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


@app.get("/changelog/user/{username}/notifications")
async def changelog_user_notifications(
    username: str,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    """Return new @mentions and file-touch notifications for the user since the last check."""
    try:
        from datetime import datetime, timezone, timedelta
        
        # Get the last check time for the agent
        last_seen = await cl_tracker.get_last_agent_seen(repo, username)
        now = datetime.now(timezone.utc)
        
        # If no last_seen exists, default to 24 hours ago
        since = last_seen or (now - timedelta(hours=24))
        
        # Query Redis via cl_profile
        mentions = await cl_profile.get_mentions_since(repo, username, since)
        touches = await cl_profile.get_file_touches_since(repo, username, since)
        
        # Update the agent seen watermark
        await cl_tracker.set_last_agent_seen(repo, username, now)
        
        return {
            "repo": repo,
            "username": username,
            "since": since.isoformat(),
            "checked_at": now.isoformat(),
            "new_mentions_count": len(mentions),
            "new_touches_count": len(touches),
            "mentions": mentions,
            "touches": touches,
        }
    except Exception as exc:
        logger.exception("Failed to fetch user notifications for %s", username)
        raise HTTPException(status_code=500, detail=str(exc))


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


class CreatePullRequestRequest(BaseModel):
    title: str
    head: str
    base: str
    body: str = ""
    draft: bool = False

class UpdatePullRequestRequest(BaseModel):
    title: str = None
    body: str = None
    state: str = None
    base: str = None

class MergePullRequestRequest(BaseModel):
    commit_title: str = None
    commit_message: str = None
    merge_method: str = "merge"


# --- Git Request Models ---

class GitCommitRequest(BaseModel):
    message: str
    repo_path: str | None = None
    add_all: bool = True

class GitPushRequest(BaseModel):
    repo_path: str | None = None
    remote: str = "origin"
    branch: str | None = None
    force: bool = False

class GitPullRequest(BaseModel):
    repo_path: str | None = None
    remote: str = "origin"
    branch: str | None = None
    rebase: bool = False

class GitSwitchBranchRequest(BaseModel):
    branch: str
    repo_path: str | None = None
    create: bool = False

class GitCreateBranchRequest(BaseModel):
    name: str
    from_ref: str | None = None
    repo_path: str | None = None
    checkout: bool = False

class GitMergeRequest(BaseModel):
    branch: str
    repo_path: str | None = None
    strategy: str | None = None
    no_ff: bool = True
    message: str | None = None

class GitRebaseRequest(BaseModel):
    onto: str
    repo_path: str | None = None
    interactive: bool = False

class GitStashRequest(BaseModel):
    action: str = "push"
    message: str | None = None
    repo_path: str | None = None
    index: int | None = None

class GitSyncRequest(BaseModel):
    repo_path: str | None = None
    remote: str = "origin"
    branch: str | None = None

class GitSmartPushRequest(BaseModel):
    message: str
    repo_path: str | None = None
    remote: str = "origin"
    branch: str | None = None
    add_all: bool = True
    force: bool = False
    pull_before_push: bool = True


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


# --- GitHub Pull Requests REST API Endpoints ---

@app.post("/pulls")
async def api_create_pull_request(
    req: CreatePullRequestRequest,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await pr_service.create_pull_request(
            repo, req.title, req.head, req.base, req.body, req.draft
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/pulls/search")
async def api_search_pull_requests(
    q: str = Query(..., description="search query"),
    repo: str = Query(..., description="owner/repo"),
) -> list[dict]:
    try:
        return await pr_service.search_pull_requests(repo, q)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/pulls/{number}")
async def api_get_pull_request(
    number: int,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await pr_service.get_pull_request(repo, number)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.patch("/pulls/{number}")
async def api_update_pull_request(
    number: int,
    req: UpdatePullRequestRequest,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await pr_service.update_pull_request(
            repo, number, req.title, req.body, req.state, req.base
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/pulls/{number}/close")
async def api_close_pull_request(
    number: int,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await pr_service.close_pull_request(repo, number)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/pulls/{number}/reopen")
async def api_reopen_pull_request(
    number: int,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await pr_service.reopen_pull_request(repo, number)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/pulls/{number}/merge")
async def api_merge_pull_request(
    number: int,
    req: MergePullRequestRequest,
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await pr_service.merge_pull_request(
            repo, number, req.commit_title, req.commit_message, req.merge_method
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/pulls")
async def api_list_pull_requests(
    repo: str = Query(..., description="owner/repo"),
    state: str = Query("open", description="open | closed | all"),
    head: str = Query(None),
    base: str = Query(None),
    sort: str = Query("created", description="created | updated | popularity | long-running"),
    direction: str = Query("desc", description="asc | desc"),
) -> list[dict]:
    try:
        return await pr_service.list_pull_requests(
            repo, state, head, base, sort, direction
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- Commit Inspection & Context Endpoints ---

@app.get("/commits/{sha}/diff")
async def api_get_commit_diff(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.get_commit_diff(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/files")
async def api_get_commit_files(sha: str, repo: str = Query(..., description="owner/repo")) -> list:
    try:
        return await commit_service.get_commit_files(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/patch")
async def api_get_commit_patch(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.get_commit_patch(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/stats")
async def api_get_commit_stats(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.get_commit_stats(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/author")
async def api_get_commit_author(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.get_commit_author(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/parents")
async def api_get_commit_parents(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.get_commit_parents(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/branches")
async def api_get_commit_branches(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.get_commit_branches(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/tags")
async def api_get_commit_tags(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.get_commit_tags(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/signature")
async def api_get_commit_signature(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.get_commit_signature(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/status")
async def api_get_commit_status(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.get_commit_status(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/pulls")
async def api_commit_pull_request(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.commit_pull_request(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/issues")
async def api_commit_issue(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.commit_issue(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/reviews")
async def api_commit_reviews(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.commit_reviews(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/discussions")
async def api_commit_discussions(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.commit_discussions(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/release")
async def api_commit_release(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.commit_release(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/workflows")
async def api_commit_workflows(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.commit_workflows(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/commits/{sha}/deployments")
async def api_commit_deployments(sha: str, repo: str = Query(..., description="owner/repo")) -> dict:
    try:
        return await commit_service.commit_deployments(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- History & Blame Endpoints ---

@app.get("/history/commits")
async def api_commit_history(
    repo: str = Query(..., description="owner/repo"),
    branch: str = Query("main"),
    path: str = Query(None),
    since: str = Query(None),
    until: str = Query(None),
    author: str = Query(None),
    max_count: int = Query(50),
) -> dict:
    try:
        return await history_service.commit_history(
            repo, branch, path, since, until, author, max_count
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/history/file")
async def api_file_history(
    path: str = Query(..., description="relative file path"),
    repo: str = Query(..., description="owner/repo"),
    branch: str = Query("main"),
    max_count: int = Query(50),
) -> dict:
    try:
        return await history_service.file_history(repo, path, branch, max_count)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/history/author")
async def api_author_history(
    author: str = Query(..., description="GitHub login or email"),
    repo: str = Query(..., description="owner/repo"),
    since: str = Query(None),
    until: str = Query(None),
    max_count: int = Query(50),
) -> dict:
    try:
        return await history_service.author_history(repo, author, since, until, max_count)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/history/branch")
async def api_branch_history(
    branch: str = Query(..., description="branch name"),
    repo: str = Query(..., description="owner/repo"),
    base: str = Query(None),
    max_count: int = Query(50),
) -> dict:
    try:
        return await history_service.branch_history(repo, branch, base, max_count)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/history/graph")
async def api_commit_graph(
    repo: str = Query(..., description="owner/repo"),
    branch: str = Query("main"),
    max_count: int = Query(50),
) -> dict:
    try:
        return await history_service.commit_graph(repo, branch, max_count)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/history/blame")
async def api_blame_history(
    path: str = Query(..., description="relative file path"),
    repo: str = Query(..., description="owner/repo"),
    branch: str = Query("main"),
) -> dict:
    try:
        return await history_service.blame_history(repo, path, branch)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- Search Endpoints ---

@app.get("/search/commits")
async def api_search_commits(
    q: str = Query(..., description="search query"),
    repo: str = Query(..., description="owner/repo"),
    max_results: int = Query(30),
) -> dict:
    try:
        return await search_service.search_commits(repo, q, max_results)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/search/commits/message")
async def api_search_commit_message(
    message: str = Query(..., description="message text"),
    repo: str = Query(..., description="owner/repo"),
    max_results: int = Query(30),
) -> dict:
    try:
        return await search_service.search_commit_message(repo, message, max_results)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/search/commits/author")
async def api_search_by_author(
    author: str = Query(..., description="author name or email"),
    repo: str = Query(..., description="owner/repo"),
    max_results: int = Query(30),
) -> dict:
    try:
        return await search_service.search_by_author(repo, author, max_results)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/search/commits/file")
async def api_search_by_file(
    path: str = Query(..., description="file path"),
    repo: str = Query(..., description="owner/repo"),
    max_results: int = Query(30),
) -> dict:
    try:
        return await search_service.search_by_file(repo, path, max_results)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/search/commits/date")
async def api_search_by_date(
    since: str = Query(..., description="since date"),
    repo: str = Query(..., description="owner/repo"),
    until: str = Query(None),
    max_results: int = Query(30),
) -> dict:
    try:
        return await search_service.search_by_date(repo, since, until, max_results)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/search/commits/hash")
async def api_search_by_hash(
    sha: str = Query(..., description="full or partial SHA"),
    repo: str = Query(..., description="owner/repo"),
) -> dict:
    try:
        return await search_service.search_by_hash(repo, sha)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- Local Git Operation Endpoints ---

@app.get("/git/status")
async def api_git_status(repo_path: str = Query(None)) -> dict:
    try:
        return await git_service.git_status(repo_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/commit")
async def api_git_commit(req: GitCommitRequest) -> dict:
    try:
        return await git_service.git_commit(req.message, req.repo_path, req.add_all)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/push")
async def api_git_push(req: GitPushRequest) -> dict:
    try:
        return await git_service.git_push(req.repo_path, req.remote, req.branch, req.force)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/pull")
async def api_git_pull(req: GitPullRequest) -> dict:
    try:
        return await git_service.git_pull(req.repo_path, req.remote, req.branch, req.rebase)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/switch")
async def api_git_switch(req: GitSwitchBranchRequest) -> dict:
    try:
        return await git_service.git_switch_branch(req.branch, req.repo_path, req.create)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/branch")
async def api_git_branch(req: GitCreateBranchRequest) -> dict:
    try:
        return await git_service.git_create_branch(req.name, req.from_ref, req.repo_path, req.checkout)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/merge")
async def api_git_merge(req: GitMergeRequest) -> dict:
    try:
        return await git_service.git_merge(req.branch, req.repo_path, req.strategy, req.no_ff, req.message)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/rebase")
async def api_git_rebase(req: GitRebaseRequest) -> dict:
    try:
        return await git_service.git_rebase(req.onto, req.repo_path, req.interactive)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/stash")
async def api_git_stash(req: GitStashRequest) -> dict:
    try:
        return await git_service.git_stash(req.action, req.message, req.repo_path, req.index)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/sync")
async def api_git_sync(req: GitSyncRequest) -> dict:
    try:
        return await git_service.git_sync(req.repo_path, req.remote, req.branch)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/git/smart-push")
async def api_git_smart_push(req: GitSmartPushRequest) -> dict:
    try:
        return await git_service.git_smart_push(
            req.message, req.repo_path, req.remote, req.branch, req.add_all, req.force, req.pull_before_push
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
