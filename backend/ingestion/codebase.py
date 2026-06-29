"""Codebase structure ingestion.

Backend-MVP approach: ingest the repository's file tree and per-directory
structure as a text summary. Cognee extracts module/dependency relationships
during cognify. (Deeper AST via ``cognee[codegraph]`` is a local-only follow-up;
see the plan's open follow-ups.)
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from backend.config import dataset_name
from backend.memory import client as memory
from backend.ingestion import github_client

# File extensions worth describing as code modules.
CODE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".cs", ".php", ".rb",
}


def _structure_payload(owner: str, repo: str, tree: dict[str, Any]) -> str:
    by_dir: dict[str, list[str]] = defaultdict(list)
    for f in tree["files"]:
        path = f["path"]
        ext = os.path.splitext(path)[1].lower()
        if ext in CODE_EXTS:
            directory = os.path.dirname(path) or "."
            by_dir[directory].append(os.path.basename(path))

    lines = [
        f"# Codebase structure of {owner}/{repo} "
        f"(branch: {tree['default_branch']})\n",
        "Module / directory layout and the source files each contains:\n",
    ]
    for directory in sorted(by_dir):
        files = ", ".join(sorted(by_dir[directory]))
        lines.append(f"- Module `{directory}` contains: {files}")
    return "\n".join(lines) + "\n"


async def ingest_repo_structure(owner: str, repo: str) -> int:
    """Remember the repo's code structure. Returns the number of code dirs found."""
    tree = github_client.fetch_repo_tree(owner, repo)
    payload = _structure_payload(owner, repo, tree)
    await memory.remember(payload, dataset_name(owner, repo, "ast"))
    # Count distinct code-bearing directories for the ingest summary.
    dirs = {
        os.path.dirname(f["path"]) or "."
        for f in tree["files"]
        if os.path.splitext(f["path"])[1].lower() in CODE_EXTS
    }
    return len(dirs)
