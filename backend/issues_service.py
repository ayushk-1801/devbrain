from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from backend.config import github_client, split_repo

from github.GithubObject import NotSet

def _get_repo(repo: str):
    gh = github_client()
    owner, name = split_repo(repo)
    return gh.get_repo(f"{owner}/{name}")

# --- CRUD Operations ---

async def create_issue(
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] = None,
    assignees: list[str] = None,
    milestone: Optional[int] = None,
) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    
    gh_milestone = NotSet
    if milestone is not None:
        gh_milestone = await asyncio.to_thread(gh_repo.get_milestone, milestone)

    issue = await asyncio.to_thread(
        gh_repo.create_issue,
        title=title,
        body=body if body else NotSet,
        labels=labels if labels is not None else NotSet,
        assignees=assignees if assignees is not None else NotSet,
        milestone=gh_milestone,
    )
    return {
        "number": issue.number,
        "title": issue.title,
        "state": issue.state,
        "url": issue.html_url,
    }

async def get_issue(repo: str, number: int) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    
    # Read details
    title = issue.title
    body = issue.body or ""
    state = issue.state
    labels = [l.name for l in issue.labels]
    assignees = [a.login for a in issue.assignees]
    author = issue.user.login if issue.user else "unknown"
    created_at = issue.created_at.isoformat()
    updated_at = issue.updated_at.isoformat()
    
    comments = []
    for c in await asyncio.to_thread(lambda: list(issue.get_comments())):
        comments.append({
            "id": c.id,
            "author": c.user.login if c.user else "unknown",
            "body": c.body,
            "created_at": c.created_at.isoformat(),
        })

    linked_prs = []
    linked_commits = []
    try:
        timeline = await asyncio.to_thread(lambda: list(issue.get_timeline()))
        for event in timeline:
            if event.event == "referenced" and event.commit_id:
                linked_commits.append(event.commit_id)
            elif event.event == "cross-referenced" and event.source and event.source.type == "issue" and event.source.issue:
                if getattr(event.source.issue, "pull_request", None):
                    linked_prs.append(event.source.issue.number)
    except Exception:
        pass

    return {
        "number": issue.number,
        "title": title,
        "body": body,
        "state": state,
        "labels": labels,
        "assignees": assignees,
        "author": author,
        "created_at": created_at,
        "updated_at": updated_at,
        "comments": comments,
        "linked_prs": list(set(linked_prs)),
        "linked_commits": list(set(linked_commits)),
    }

async def update_issue(
    repo: str,
    number: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    state: Optional[str] = None,
    labels: Optional[list[str]] = None,
    milestone: Optional[int] = None,
    assignees: Optional[list[str]] = None,
) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    
    kwargs: dict[str, Any] = {}
    if title is not None:
        kwargs["title"] = title
    if body is not None:
        kwargs["body"] = body
    if state is not None:
        kwargs["state"] = state
    if labels is not None:
        kwargs["labels"] = labels
    if milestone is not None:
        if milestone == 0:  # clear milestone
            kwargs["milestone"] = None
        else:
            gh_milestone = await asyncio.to_thread(gh_repo.get_milestone, milestone)
            kwargs["milestone"] = gh_milestone
    if assignees is not None:
        kwargs["assignees"] = assignees

    await asyncio.to_thread(issue.edit, **kwargs)
    return {
        "number": issue.number,
        "title": issue.title,
        "state": issue.state,
        "url": issue.html_url,
    }

async def close_issue(repo: str, number: int) -> dict[str, Any]:
    return await update_issue(repo, number, state="closed")

async def reopen_issue(repo: str, number: int) -> dict[str, Any]:
    return await update_issue(repo, number, state="open")

# --- Listing & Search ---

async def list_issues(
    repo: str,
    state: str = "open",
    assignee: Optional[str] = None,
    creator: Optional[str] = None,
    mentioned: Optional[str] = None,
    labels: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    
    kwargs: dict[str, Any] = {"state": state}
    if assignee:
        kwargs["assignee"] = assignee
    if creator:
        kwargs["creator"] = creator
    if mentioned:
        kwargs["mentioned"] = mentioned
    if labels:
        kwargs["labels"] = labels

    issues = await asyncio.to_thread(lambda: list(gh_repo.get_issues(**kwargs)))
    out = []
    for issue in issues:
        if issue.pull_request:
            continue
        out.append({
            "number": issue.number,
            "title": issue.title,
            "state": issue.state,
            "labels": [l.name for l in issue.labels],
            "assignees": [a.login for a in issue.assignees],
            "author": issue.user.login if issue.user else "unknown",
            "created_at": issue.created_at.isoformat(),
        })
    return out

async def search_issues(repo: str, query: str) -> list[dict[str, Any]]:
    gh = github_client()
    full_query = f"repo:{repo} is:issue {query}"
    issues = await asyncio.to_thread(lambda: list(gh.search_issues(full_query)))
    
    out = []
    for issue in issues:
        out.append({
            "number": issue.number,
            "title": issue.title,
            "state": issue.state,
            "labels": [l.name for l in issue.labels],
            "assignees": [a.login for a in issue.assignees],
            "author": issue.user.login if issue.user else "unknown",
            "created_at": issue.created_at.isoformat(),
        })
    return out

async def list_my_issues(repo: str, username: str) -> dict[str, list[dict[str, Any]]]:
    assigned = await list_issues(repo, state="all", assignee=username)
    created = await list_issues(repo, state="all", creator=username)
    mentioned = await list_issues(repo, state="all", mentioned=username)
    
    return {
        "assigned": assigned,
        "created": created,
        "mentioned": mentioned,
    }

# --- Labels ---

async def add_labels(repo: str, number: int, labels: list[str]) -> list[str]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    await asyncio.to_thread(issue.add_to_labels, *labels)
    updated_issue = await asyncio.to_thread(gh_repo.get_issue, number)
    return [l.name for l in updated_issue.labels]

async def remove_label(repo: str, number: int, label_name: str) -> list[str]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    await asyncio.to_thread(issue.remove_from_labels, label_name)
    updated_issue = await asyncio.to_thread(gh_repo.get_issue, number)
    return [l.name for l in updated_issue.labels]

async def replace_labels(repo: str, number: int, labels: list[str]) -> list[str]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    await asyncio.to_thread(issue.set_labels, *labels)
    updated_issue = await asyncio.to_thread(gh_repo.get_issue, number)
    return [l.name for l in updated_issue.labels]

async def list_labels(repo: str) -> list[dict[str, Any]]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    labels = await asyncio.to_thread(lambda: list(gh_repo.get_labels()))
    return [{"name": l.name, "color": l.color, "description": l.description} for l in labels]

async def create_label(repo: str, name: str, color: str, description: str = "") -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    label = await asyncio.to_thread(gh_repo.create_label, name=name, color=color, description=description)
    return {"name": label.name, "color": label.color, "description": label.description}

# --- Assignment ---

async def assign_issue(repo: str, number: int, assignees: list[str]) -> list[str]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    await asyncio.to_thread(issue.add_to_assignees, *assignees)
    updated_issue = await asyncio.to_thread(gh_repo.get_issue, number)
    return [a.login for a in updated_issue.assignees]

async def unassign_issue(repo: str, number: int, assignees: list[str]) -> list[str]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    await asyncio.to_thread(issue.remove_from_assignees, *assignees)
    updated_issue = await asyncio.to_thread(gh_repo.get_issue, number)
    return [a.login for a in updated_issue.assignees]

async def list_assignees(repo: str) -> list[str]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    assignees = await asyncio.to_thread(lambda: list(gh_repo.get_assignees()))
    return [a.login for a in assignees]

# --- Comments ---

async def comment_issue(repo: str, number: int, body: str) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    comment = await asyncio.to_thread(issue.create_comment, body)
    return {
        "id": comment.id,
        "author": comment.user.login if comment.user else "unknown",
        "body": comment.body,
        "created_at": comment.created_at.isoformat(),
    }

async def edit_comment(repo: str, comment_id: int, body: str) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    comment = await asyncio.to_thread(gh_repo.get_comment, comment_id)
    await asyncio.to_thread(comment.edit, body)
    return {
        "id": comment.id,
        "author": comment.user.login if comment.user else "unknown",
        "body": comment.body,
        "created_at": comment.created_at.isoformat(),
    }

async def delete_comment(repo: str, comment_id: int) -> dict[str, str]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    comment = await asyncio.to_thread(gh_repo.get_comment, comment_id)
    await asyncio.to_thread(comment.delete)
    return {"status": "success", "message": f"Comment {comment_id} deleted."}

async def list_comments(repo: str, number: int) -> list[dict[str, Any]]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    comments = await asyncio.to_thread(lambda: list(issue.get_comments()))
    return [{
        "id": c.id,
        "author": c.user.login if c.user else "unknown",
        "body": c.body,
        "created_at": c.created_at.isoformat(),
    } for c in comments]
