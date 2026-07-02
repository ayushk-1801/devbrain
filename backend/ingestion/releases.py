"""Release / tag / deployment ingestion: structures release lifecycle into memory."""

from __future__ import annotations

from typing import Any

from backend.config import dataset_name
from backend.ingestion import github_client
from backend.memory import client as memory


def _release_payload(owner: str, repo: str, release: dict[str, Any]) -> str:
    assets = "\n".join(
        f"  - {a['name']} ({a['size']} bytes, {a['download_count']} downloads)"
        for a in release.get("assets", [])
    )
    return (
        f"# Release {release['tag']} in {owner}/{repo}: {release['name']}\n\n"
        f"Author: {release['author']}\n"
        f"Published: {release['published_at']}\n"
        f"Pre-release: {release['prerelease']}\n\n"
        f"## Notes\n{release['body'] or '(no release notes)'}\n\n"
        f"## Assets\n{assets or '  (none)'}\n"
    )


def _tag_payload(owner: str, repo: str, tag: dict[str, Any]) -> str:
    return (
        f"# Tag {tag['name']} in {owner}/{repo}\n\n"
        f"SHA: {tag['sha']}\n"
        f"Author: {tag['author']}\n"
        f"Date: {tag['date']}\n\n"
        f"## Commit message\n{tag['message']}\n"
    )


def _deployment_payload(owner: str, repo: str, dep: dict[str, Any]) -> str:
    status = dep.get("status")
    status_text = (
        f"State: {status['state']}\nDescription: {status['description']}\n"
        if status
        else "(no status)"
    )
    return (
        f"# Deployment #{dep['id']} in {owner}/{repo}\n\n"
        f"Ref: {dep['ref']}\n"
        f"SHA: {dep['sha']}\n"
        f"Environment: {dep['environment']}\n"
        f"Creator: {dep['creator']}\n"
        f"Created: {dep['created_at']}\n\n"
        f"## Status\n{status_text}\n"
    )


async def ingest_release(owner: str, repo: str, release: dict[str, Any]) -> None:
    """Remember a single release into the repo's releases dataset."""
    payload = _release_payload(owner, repo, release)
    await memory.remember(payload, dataset_name(owner, repo, "releases"))


async def ingest_releases(owner: str, repo: str) -> int:
    """Fetch and ingest all GitHub releases. Returns count."""
    releases = github_client.fetch_releases(owner, repo)
    for release in releases:
        await ingest_release(owner, repo, release)
    return len(releases)


async def ingest_tag(owner: str, repo: str, tag: dict[str, Any]) -> None:
    """Remember a single tag into the repo's releases dataset."""
    payload = _tag_payload(owner, repo, tag)
    await memory.remember(payload, dataset_name(owner, repo, "releases"))


async def ingest_tags(owner: str, repo: str) -> int:
    """Fetch and ingest all git tags. Returns count."""
    tags = github_client.fetch_tags(owner, repo)
    for tag in tags:
        await ingest_tag(owner, repo, tag)
    return len(tags)


async def ingest_deployment(owner: str, repo: str, dep: dict[str, Any]) -> None:
    """Remember a single deployment into the repo's releases dataset."""
    payload = _deployment_payload(owner, repo, dep)
    await memory.remember(payload, dataset_name(owner, repo, "releases"))


async def ingest_deployments(owner: str, repo: str) -> int:
    """Fetch and ingest all deployments. Returns count."""
    deps = github_client.fetch_deployments(owner, repo)
    for dep in deps:
        await ingest_deployment(owner, repo, dep)
    return len(deps)


async def ingest_all_releases(owner: str, repo: str) -> dict[str, int]:
    """Ingest releases + tags + deployments. Returns counts."""
    return {
        "releases": await ingest_releases(owner, repo),
        "tags": await ingest_tags(owner, repo),
        "deployments": await ingest_deployments(owner, repo),
    }
