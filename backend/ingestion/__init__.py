"""GitHub data source ingestion modules."""

from backend.ingestion import (
    adrs,
    codebase,
    codegraph,
    commits,
    github_client,
    issues,
    pull_requests,
    releases,
)

__all__ = [
    "adrs",
    "codebase",
    "codegraph",
    "commits",
    "github_client",
    "issues",
    "pull_requests",
    "releases",
]