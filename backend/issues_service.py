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

def _serialize_timeline_event(event) -> dict[str, Any]:
    out = {
        "id": getattr(event, "id", None),
        "event": getattr(event, "event", None),
        "actor": event.actor.login if getattr(event, "actor", None) else None,
        "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else None,
    }
    # Extract commit details if available
    if getattr(event, "commit_id", None):
        out["commit_id"] = event.commit_id
    # Extract source details (for cross-referenced, etc.)
    source = getattr(event, "source", None)
    if source:
        source_issue = getattr(source, "issue", None)
        if source_issue:
            out["source_issue"] = {
                "number": source_issue.number,
                "title": source_issue.title,
                "url": source_issue.html_url,
                "is_pr": source_issue.pull_request is not None,
            }
    # Extract project card details if available
    project_card = getattr(event, "project_card", None)
    if project_card:
        out["project_card"] = {
            "id": getattr(project_card, "id", None),
            "url": getattr(project_card, "url", None),
            "project_id": getattr(project_card, "project_id", None),
            "project_url": getattr(project_card, "project_url", None),
            "column_name": getattr(project_card, "column_name", None),
        }
    return out


def _serialize_issue_event(event) -> dict[str, Any]:
    out = {
        "id": getattr(event, "id", None),
        "event": getattr(event, "event", None),
        "actor": event.actor.login if getattr(event, "actor", None) else None,
        "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else None,
    }
    if getattr(event, "commit_id", None):
        out["commit_id"] = event.commit_id
    if getattr(event, "label", None):
        out["label"] = event.label.name
    if getattr(event, "assignee", None):
        out["assignee"] = event.assignee.login
    return out


async def get_issue(repo: str, number: int) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    issue = await asyncio.to_thread(gh_repo.get_issue, number)
    
    # Read details
    title = issue.title
    body = issue.body or ""
    state = issue.state
    
    # 1. Author
    author = issue.user.login if issue.user else "unknown"
    
    # 2. Created & Updated
    created_at = issue.created_at.isoformat() if issue.created_at else None
    updated_at = issue.updated_at.isoformat() if issue.updated_at else None
    
    # 3. Metadata
    metadata = {
        "locked": getattr(issue, "locked", False),
        "active_lock_reason": getattr(issue, "active_lock_reason", None),
        "comments_count": getattr(issue, "comments", 0),
        "closed_at": issue.closed_at.isoformat() if getattr(issue, "closed_at", None) else None,
        "closed_by": issue.closed_by.login if getattr(issue, "closed_by", None) else None,
        "draft": getattr(issue, "draft", None),
        "html_url": issue.html_url,
        "url": issue.url,
    }

    # 4. Comments (with reactions count if available in raw_data)
    comments = []
    for c in await asyncio.to_thread(lambda: list(issue.get_comments())):
        c_reactions = {}
        if c.raw_data and "reactions" in c.raw_data:
            for k, v in c.raw_data["reactions"].items():
                if k != "url":
                    c_reactions[k] = v
        
        comments.append({
            "id": c.id,
            "author": c.user.login if c.user else "unknown",
            "body": c.body,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "reactions": c_reactions,
        })

    # 5. Timeline, Linked PRs, Linked commits, Project
    linked_prs = []
    linked_commits = []
    serialized_timeline = []
    project_info = None

    try:
        timeline = await asyncio.to_thread(lambda: list(issue.get_timeline()))
        for event in timeline:
            serialized_timeline.append(_serialize_timeline_event(event))
            
            # Extract linked commits and PRs
            if event.event == "referenced" and getattr(event, "commit_id", None):
                linked_commits.append(event.commit_id)
            elif event.event == "cross-referenced" and getattr(event, "source", None):
                source = event.source
                if source and getattr(source, "type", None) == "issue" and getattr(source, "issue", None):
                    src_issue = source.issue
                    if getattr(src_issue, "pull_request", None):
                        linked_prs.append({
                            "number": src_issue.number,
                            "title": src_issue.title,
                            "state": src_issue.state,
                            "url": src_issue.html_url,
                        })
                        
            # Reconstruct project state
            if event.event in ("added_to_project", "added_to_project_v2", "moved_columns_in_project"):
                proj_card = getattr(event, "project_card", None) or {}
                proj_card_raw = event.raw_data.get("project_card") if hasattr(event, "raw_data") else {}
                
                proj_name = None
                proj_id = None
                proj_url = None
                column_name = None
                
                if proj_card_raw:
                    proj_id = proj_card_raw.get("project_id")
                    proj_url = proj_card_raw.get("project_url")
                    proj_name = proj_card_raw.get("project_name")
                    column_name = proj_card_raw.get("column_name")
                elif proj_card:
                    proj_id = getattr(proj_card, "project_id", None)
                    proj_url = getattr(proj_card, "project_url", None)
                    column_name = getattr(proj_card, "column_name", None)
                
                # Try to find V2 project info from raw_data
                if not proj_id and hasattr(event, "raw_data"):
                    # V2 event structure: project_item, project, etc.
                    v2_item = event.raw_data.get("project_item") or event.raw_data.get("project") or {}
                    if v2_item:
                        proj_id = v2_item.get("id")
                        proj_name = v2_item.get("title") or v2_item.get("name")
                        proj_url = v2_item.get("url")
                
                project_info = {
                    "id": proj_id,
                    "name": proj_name or (f"Project #{proj_id}" if proj_id else "Unknown Project"),
                    "url": proj_url,
                    "column": column_name,
                }
            elif event.event in ("removed_from_project", "removed_from_project_v2"):
                project_info = None
    except Exception:
        pass

    # Deduplicate linked PRs
    unique_prs = {}
    for pr in linked_prs:
        unique_prs[pr["number"]] = pr
    linked_prs = list(unique_prs.values())
    linked_commits = list(set(linked_commits))

    # 6. Events
    serialized_events = []
    try:
        events = await asyncio.to_thread(lambda: list(issue.get_events()))
        for event in events:
            serialized_events.append(_serialize_issue_event(event))
    except Exception:
        pass

    # 7. Assignees
    assignees = [
        {
            "login": a.login,
            "avatar_url": a.avatar_url,
            "html_url": a.html_url
        }
        for a in issue.assignees
    ]

    # 8. Labels
    labels = [
        {
            "name": l.name,
            "color": l.color,
            "description": l.description
        }
        for l in issue.labels
    ]

    # 9. Milestone
    milestone = None
    if issue.milestone:
        milestone = {
            "title": issue.milestone.title,
            "number": issue.milestone.number,
            "state": issue.milestone.state,
            "description": issue.milestone.description,
            "due_on": issue.milestone.due_on.isoformat() if issue.milestone.due_on else None,
        }

    # 10. Reactions
    reactions_summary = {}
    raw_reactions = issue.raw_data.get("reactions") if issue.raw_data else None
    if raw_reactions:
        for k, v in raw_reactions.items():
            if k != "url":
                reactions_summary[k] = v
    else:
        reactions_summary = {
            "total_count": 0,
            "+1": 0,
            "-1": 0,
            "laugh": 0,
            "confused": 0,
            "heart": 0,
            "hooray": 0,
            "rocket": 0,
            "eyes": 0
        }
    
    detailed_reactions = []
    try:
        for r in await asyncio.to_thread(lambda: list(issue.get_reactions())):
            detailed_reactions.append({
                "id": r.id,
                "content": r.content,
                "user": r.user.login if r.user else "unknown",
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
    except Exception:
        pass
    
    reactions = {
        "summary": reactions_summary,
        "details": detailed_reactions
    }

    return {
        "number": issue.number,
        "title": title,
        "body": body,
        "state": state,
        "created": created_at,
        "updated": updated_at,
        "author": author,
        "metadata": metadata,
        "comments": comments,
        "timeline": serialized_timeline,
        "events": serialized_events,
        "linked_prs": linked_prs,
        "linked_commits": linked_commits,
        "assignees": assignees,
        "labels": labels,
        "milestone": milestone,
        "project": project_info,
        "reactions": reactions,
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
