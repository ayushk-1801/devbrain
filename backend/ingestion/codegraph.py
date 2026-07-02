"""Deep AST/code graph ingestion via ``cognee.remember()`` with file paths.

Downloads the repo archive, then feeds every supported source file into
Cognee's built-in pipeline (add → cognify → improve). Cognee's default
loaders handle code files and extract functions, classes, imports, and
their relationships into the knowledge graph.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from backend.config import dataset_name
from backend.ingestion import github_client
from backend.memory import client as memory

logger = logging.getLogger("devbrain.codegraph")

CODEGRAPH_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".rs", ".java", ".cs", ".php", ".rb",
}


def _collect_source_files(repo_path: Path) -> list[str]:
    files: list[str] = []
    for root, _dirs, entries in os.walk(repo_path):
        for name in entries:
            ext = os.path.splitext(name)[1].lower()
            if ext in CODEGRAPH_EXTS:
                files.append(os.path.join(root, name))
    return sorted(files)


def _manifest_payload(
    owner: str, repo: str, code_files: list[str], branch: str
) -> str:
    by_lang: dict[str, int] = {}
    for fp in code_files:
        ext = os.path.splitext(fp)[1].lower().lstrip(".")
        by_lang[ext] = by_lang.get(ext, 0) + 1

    lines = [
        f"# CodeGraph manifest for {owner}/{repo}",
        "",
        f"Default branch: `{branch}`",
        f"Canonical DevBrain AST dataset: `{dataset_name(owner, repo, 'ast')}`",
        f"Source files ingested: {len(code_files)}",
        "",
        "Cognee ingestion was run on a local archive of this repository.",
        "Each source file was fed to `cognee.remember()`, which runs the",
        "default add → cognify → improve pipeline for entity extraction.",
        "",
        "## Languages detected",
    ]
    for lang, count in sorted(by_lang.items()):
        lines.append(f"- {lang}: {count} files")
    return "\n".join(lines) + "\n"


async def ingest_codegraph(owner: str, repo: str) -> int:
    """Ingest source code by downloading the repo and feeding files to Cognee.

    Returns the number of source files ingested.
    """
    ast_dataset = dataset_name(owner, repo, "ast")

    with tempfile.TemporaryDirectory(prefix="devbrain-codegraph-") as tmpdir:
        repo_path = github_client.download_repo_archive(owner, repo, tmpdir)
        code_files = _collect_source_files(repo_path)

        if not code_files:
            logger.warning("No supported source files found in %s/%s", owner, repo)
            return 0

        logger.info(
            "Ingesting %d source files into dataset %s", len(code_files), ast_dataset
        )
        await memory.remember(code_files, ast_dataset)

    branch = github_client.fetch_repo_tree(owner, repo).get("default_branch", "main")
    await memory.remember(
        _manifest_payload(owner, repo, code_files, branch), ast_dataset
    )
    return len(code_files)
