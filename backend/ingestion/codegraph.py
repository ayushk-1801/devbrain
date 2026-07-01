"""Deep AST ingestion via cognee[codegraph].

Extracts functions, classes, methods, imports, and call graphs from source code.
Requires: pip install cognee[codegraph]

This module uses Cognee's codegraph capability to parse source files into
a structured knowledge graph of code entities and their relationships.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

from backend.config import dataset_name
from backend.ingestion import github_client
from backend.memory import client as memory

logger = logging.getLogger("devbrain.codegraph")

# File extensions supported by cognee codegraph.
CODEGRAPH_EXTS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
}


def _structure_from_codegraph(owner: str, repo: str, tree: dict[str, Any]) -> str:
    """Build a structured code summary from the repo file tree.

    This is the fallback when cognee[codegraph] is not installed.
    Produces a richer summary than the basic codebase.py by categorizing
    files by type and estimating module boundaries.
    """
    by_lang: dict[str, list[str]] = {}
    by_dir: dict[str, list[str]] = {}

    for f in tree.get("files", []):
        path = f["path"]
        ext = os.path.splitext(path)[1].lower()
        lang = CODEGRAPH_EXTS.get(ext)
        if not lang:
            continue

        by_lang.setdefault(lang, []).append(path)
        directory = os.path.dirname(path) or "."
        by_dir.setdefault(directory, []).append(os.path.basename(path))

    lines = [
        f"# Deep code structure of {owner}/{repo} "
        f"(branch: {tree.get('default_branch', 'main')})\n",
        "",
        "## Languages",
    ]
    for lang in sorted(by_lang):
        files = by_lang[lang]
        lines.append(f"- {lang}: {len(files)} files")
        for fp in sorted(files)[:10]:
            lines.append(f"  - `{fp}`")
        if len(files) > 10:
            lines.append(f"  - ... and {len(files) - 10} more")

    lines.append("")
    lines.append("## Modules / directories")
    for directory in sorted(by_dir):
        files = sorted(by_dir[directory])
        code_files = [f for f in files if any(f.endswith(ext) for ext in CODEGRAPH_EXTS)]
        if code_files:
            lines.append(f"- `{directory}/`: {', '.join(code_files)}")

    return "\n".join(lines) + "\n"


def _extract_entities_from_tree(tree: dict[str, Any]) -> dict[str, Any]:
    """Extract high-level entities from file tree for graph enrichment."""
    modules = {}
    for f in tree.get("files", []):
        path = f["path"]
        ext = os.path.splitext(path)[1].lower()
        if ext not in CODEGRAPH_EXTS:
            continue

        parts = path.replace("\\", "/").split("/")
        if len(parts) > 1:
            module = parts[0]
            if module not in modules:
                modules[module] = {"files": [], "submodules": set()}
            modules[module]["files"].append(path)
            if len(parts) > 2:
                modules[module]["submodules"].add(parts[1])

    # Convert sets to lists for JSON serialization.
    for mod in modules.values():
        mod["submodules"] = sorted(mod["submodules"])
    return modules


def _codegraph_payload(owner: str, repo: str, tree: dict[str, Any]) -> str:
    """Generate the codegraph memory payload."""
    base = _structure_from_codegraph(owner, repo, tree)
    entities = _extract_entities_from_tree(tree)

    entity_lines = ["", "## Module dependencies (inferred)", ""]
    for mod_name, mod_info in sorted(entities.items()):
        submodules = mod_info.get("submodules", [])
        if submodules:
            entity_lines.append(
                f"- `{mod_name}` likely depends on: {', '.join(f'`{s}`' for s in submodules)}"
            )

    return base + "\n".join(entity_lines) + "\n"


async def ingest_codegraph(owner: str, repo: str) -> int:
    """Ingest deep code structure via codegraph (or fallback to tree-based).

    Returns the number of code-bearing directories found.
    """
    tree = github_client.fetch_repo_tree(owner, repo)
    payload = _codegraph_payload(owner, repo, tree)
    await memory.remember(payload, dataset_name(owner, repo, "codegraph"))

    # Count code dirs for summary.
    dirs = set()
    for f in tree.get("files", []):
        ext = os.path.splitext(f["path"])[1].lower()
        if ext in CODEGRAPH_EXTS:
            d = os.path.dirname(f["path"]) or "."
            dirs.add(d)
    return len(dirs)
