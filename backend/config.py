"""Central configuration for the DevBrain backend.

Loads environment variables, derives the Cognee mode (cloud vs local fallback),
exposes a cached PyGithub client, and provides the canonical dataset-name helper.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Process-wide settings sourced from the environment."""

    # --- Cognee Cloud ---
    COGNEE_BASE_URL: str = os.getenv("COGNEE_BASE_URL", "")
    COGNEE_API_KEY: str = os.getenv("COGNEE_API_KEY", "")

    # --- Cognee local mode: Gemini LLM + embeddings, file-based stores ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini/gemini-2.0-flash-exp")
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "gemini")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini/text-embedding-004")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
    COGNEE_DATA_DIR: str = os.getenv("COGNEE_DATA_DIR", "./.cognee/data")
    COGNEE_SYSTEM_DIR: str = os.getenv("COGNEE_SYSTEM_DIR", "./.cognee/system")

    # --- GitHub ---
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    # Optional convenience default repo (e.g. for /query without ?repo=). DevBrain
    # is multi-repo; the repo is normally passed per request / per MCP tool call.
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")
    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    # --- DevBrain ---
    # JSON file tracking which repos have been ingested (multi-repo support).
    REGISTRY_PATH: str = os.getenv("REGISTRY_PATH", "./.devbrain/repos.json")

    @property
    def COGNEE_MODE(self) -> str:
        """'cloud' when a Cognee API key is present, otherwise 'local'."""
        return "cloud" if self.COGNEE_API_KEY else "local"


settings = Settings()


def _export_local_env() -> None:
    """In local mode, normalise environment variables so Cognee's config and
    litellm both resolve Gemini correctly.

    This runs at import (before ``cognee`` is imported anywhere), so Cognee's
    settings pick up the values regardless of when its config objects are built.
    """
    if settings.COGNEE_MODE != "local":
        return
    key = settings.GEMINI_API_KEY
    env_defaults = {
        "GRAPH_DATABASE_PROVIDER": "kuzu",
        "VECTOR_DB_PROVIDER": "lancedb",
        "DB_PROVIDER": "sqlite",
        # Single-user local backend: disable multi-tenant access control so
        # remember/recall don't require an authenticated Cognee user.
        "ENABLE_BACKEND_ACCESS_CONTROL": "false",
        "LLM_PROVIDER": settings.LLM_PROVIDER,
        "LLM_MODEL": settings.LLM_MODEL,
        "EMBEDDING_PROVIDER": settings.EMBEDDING_PROVIDER,
        "EMBEDDING_MODEL": settings.EMBEDDING_MODEL,
        "EMBEDDING_DIMENSIONS": str(settings.EMBEDDING_DIMENSIONS),
    }
    for name, value in env_defaults.items():
        if value:
            os.environ.setdefault(name, value)
    if key:
        # litellm reads GEMINI_API_KEY for gemini/* models; Cognee reads
        # LLM_API_KEY / EMBEDDING_API_KEY.
        for name in ("GEMINI_API_KEY", "LLM_API_KEY", "EMBEDDING_API_KEY"):
            os.environ.setdefault(name, key)


_export_local_env()


@lru_cache(maxsize=1)
def github_client():
    """Return a cached PyGithub client. Imported lazily so the module loads
    even when PyGithub isn't installed (e.g. during isolated tests)."""
    from github import Github

    if not settings.GITHUB_TOKEN:
        # Unauthenticated access still works for public repos but is heavily
        # rate-limited; surface a clear hint rather than failing cryptically.
        return Github()
    return Github(settings.GITHUB_TOKEN)


def _safe(part: str) -> str:
    return part.replace("-", "_").replace(".", "_").lower()


def dataset_name(owner: str, repo: str, kind: str) -> str:
    """Build a dataset name following the required pattern
    ``repo_{owner}_{repo}_{type}`` (type ∈ commits|prs|adrs|ast).

    This is the single source of truth for dataset naming — never hand-build
    dataset strings elsewhere, or cross-source graph traversal breaks.
    """
    valid = {"commits", "prs", "adrs", "ast"}
    if kind not in valid:
        raise ValueError(f"unknown dataset kind {kind!r}; expected one of {sorted(valid)}")
    return f"repo_{_safe(owner)}_{_safe(repo)}_{kind}"


def split_repo(repo: str) -> tuple[str, str]:
    """Split an ``owner/repo`` string into ``(owner, repo)``."""
    if "/" not in repo:
        raise ValueError(f"repo must be in 'owner/repo' form, got {repo!r}")
    owner, name = repo.split("/", 1)
    return owner, name
