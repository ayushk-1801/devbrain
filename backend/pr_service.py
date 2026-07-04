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

def _serialize_pr(pr) -> dict[str, Any]:
    return {
        "number": pr.number,
        "title": pr.title,
        "body": pr.body,
        "state": pr.state,
        "html_url": pr.html_url,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
        "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
        "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
        "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
        "merged": pr.merged,
        "mergeable": pr.mergeable,
        "mergeable_state": pr.mergeable_state,
        "head": {
            "ref": pr.head.ref,
            "sha": pr.head.sha,
            "repo": pr.head.repo.full_name if pr.head.repo else None,
        },
        "base": {
            "ref": pr.base.ref,
            "sha": pr.base.sha,
            "repo": pr.base.repo.full_name if pr.base.repo else None,
        },
        "user": pr.user.login if pr.user else None,
        "comments_count": pr.comments,
        "review_comments_count": pr.review_comments,
        "commits_count": pr.commits,
        "additions": pr.additions,
        "deletions": pr.deletions,
        "changed_files": pr.changed_files,
    }

async def create_pull_request(
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
    draft: bool = False,
) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    pr = await asyncio.to_thread(
        gh_repo.create_pull,
        title=title,
        body=body if body else NotSet,
        head=head,
        base=base,
        draft=draft,
    )
    
    from backend import service
    await service.enqueue_single_pr(repo, pr.number)
    
    return _serialize_pr(pr)

async def update_pull_request(
    repo: str,
    number: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    state: Optional[str] = None,
    base: Optional[str] = None,
) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    pr = await asyncio.to_thread(gh_repo.get_pull, number)
    
    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    if body is not None:
        kwargs["body"] = body
    if state is not None:
        kwargs["state"] = state
    if base is not None:
        kwargs["base"] = base
        
    if kwargs:
        await asyncio.to_thread(pr.edit, **kwargs)
        # Re-fetch to get the updated state from GitHub
        pr = await asyncio.to_thread(gh_repo.get_pull, number)

    from backend import service
    await service.enqueue_single_pr(repo, number)

    return _serialize_pr(pr)

async def get_pull_request(repo: str, number: int) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    pr = await asyncio.to_thread(gh_repo.get_pull, number)
    
    # 1. Base Serialization
    data = _serialize_pr(pr)
    
    # 2. Get Commits
    commits_list = []
    try:
        pr_commits = await asyncio.to_thread(lambda: list(pr.get_commits()))
        for c in pr_commits:
            commits_list.append({
                "sha": c.sha,
                "message": c.commit.message,
                "author": c.commit.author.name if c.commit.author else None,
                "date": c.commit.author.date.isoformat() if c.commit.author and c.commit.author.date else None,
            })
    except Exception:
        pass
    data["commits"] = commits_list
    
    # 3. Get Reviews
    reviews_list = []
    try:
        pr_reviews = await asyncio.to_thread(lambda: list(pr.get_reviews()))
        for r in pr_reviews:
            reviews_list.append({
                "id": r.id,
                "user": r.user.login if r.user else None,
                "state": r.state,
                "body": r.body,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            })
    except Exception:
        pass
    data["reviews"] = reviews_list
    
    # 4. Get Issue Comments (General/Discussion comments)
    issue_comments = []
    try:
        pr_issue_comments = await asyncio.to_thread(lambda: list(pr.get_issue_comments()))
        for c in pr_issue_comments:
            issue_comments.append({
                "id": c.id,
                "user": c.user.login if c.user else None,
                "body": c.body,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            })
    except Exception:
        pass
    data["issue_comments"] = issue_comments
    
    # 5. Get Review Comments (Inline comments on files)
    review_comments = []
    try:
        pr_review_comments = await asyncio.to_thread(lambda: list(pr.get_comments()))
        for c in pr_review_comments:
            review_comments.append({
                "id": c.id,
                "user": c.user.login if c.user else None,
                "body": c.body,
                "path": c.path,
                "position": c.position,
                "original_position": c.original_position,
                "commit_id": c.commit_id,
                "original_commit_id": c.original_commit_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            })
    except Exception:
        pass
    data["review_comments"] = review_comments
    
    # 6. Get Files
    files_list = []
    try:
        pr_files = await asyncio.to_thread(lambda: list(pr.get_files()))
        for f in pr_files:
            files_list.append({
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
                "patch": f.patch,
                "raw_url": f.raw_url,
            })
    except Exception:
        pass
    data["files"] = files_list
    
    return data

async def list_pull_requests(
    repo: str,
    state: str = "open",
    head: Optional[str] = None,
    base: Optional[str] = None,
    sort: str = "created",
    direction: str = "desc",
) -> list[dict[str, Any]]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    
    kwargs = {"state": state, "sort": sort, "direction": direction}
    if head is not None:
        kwargs["head"] = head
    if base is not None:
        kwargs["base"] = base
        
    pulls = await asyncio.to_thread(lambda: list(gh_repo.get_pulls(**kwargs)))
    return [_serialize_pr(p) for p in pulls]

async def search_pull_requests(repo: str, query: str) -> list[dict[str, Any]]:
    gh = github_client()
    full_query = f"{query} repo:{repo} type:pr"
    
    results = await asyncio.to_thread(lambda: list(gh.search_issues(full_query)))
    
    serialized = []
    for issue in results:
        serialized.append({
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "state": issue.state,
            "html_url": issue.html_url,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
            "user": issue.user.login if issue.user else None,
        })
    return serialized

async def close_pull_request(repo: str, number: int) -> dict[str, Any]:
    return await update_pull_request(repo, number, state="closed")

async def reopen_pull_request(repo: str, number: int) -> dict[str, Any]:
    return await update_pull_request(repo, number, state="open")

async def merge_pull_request(
    repo: str,
    number: int,
    commit_title: Optional[str] = None,
    commit_message: Optional[str] = None,
    merge_method: str = "merge",
) -> dict[str, Any]:
    gh_repo = await asyncio.to_thread(_get_repo, repo)
    pr = await asyncio.to_thread(gh_repo.get_pull, number)
    
    kwargs = {}
    if commit_title is not None:
        kwargs["commit_title"] = commit_title
    if commit_message is not None:
        kwargs["commit_message"] = commit_message
    if merge_method is not None:
        kwargs["merge_method"] = merge_method
        
    result = await asyncio.to_thread(pr.merge, **kwargs)
    
    from backend import service
    await service.enqueue_single_pr(repo, number)
    
    if result.merged and result.sha:
        try:
            await service.enqueue_single_commit(repo, result.sha)
        except Exception:
            pass
        
    return {
        "merged": result.merged,
        "message": result.message,
        "sha": result.sha,
    }
