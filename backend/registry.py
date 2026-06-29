"""Persistent registry of ingested repositories.

DevBrain is multi-repo: any number of ``owner/repo`` targets can be ingested
through the REST API or the MCP server. This registry records which repos have
been ingested so that:

  * ``list_repos`` can report them to an agent,
  * the weekly memory refresh can iterate every known repo (rather than a single
    hard-coded one).

Storage is a small JSON file — zero infra, good enough for hackathon scale.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from backend.config import settings

_LOCK = threading.Lock()


def _registry_path() -> Path:
    path = Path(settings.REGISTRY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read() -> list[str]:
    path = _registry_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write(repos: list[str]) -> None:
    _registry_path().write_text(json.dumps(sorted(set(repos)), indent=2))


def add_repo(repo: str) -> None:
    """Record a repo as ingested (idempotent)."""
    with _LOCK:
        repos = _read()
        if repo not in repos:
            repos.append(repo)
            _write(repos)


def list_repos() -> list[str]:
    """Return all ingested repos, sorted."""
    with _LOCK:
        return sorted(set(_read()))


def has_repo(repo: str) -> bool:
    return repo in list_repos()


def remove_repo(repo: str) -> None:
    """Forget that a repo was ingested (does not touch Cognee data)."""
    with _LOCK:
        repos = [r for r in _read() if r != repo]
        _write(repos)
