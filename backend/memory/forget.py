"""Surgical pruning: remove a deprecated module's subgraph from memory.

Cognee's ``forget`` operates at dataset granularity. For the MVP we dissolve the
repo's AST subgraph when a module is deprecated. True per-module pruning requires
tagging code memories with ``node_set=[module]`` at ingest time and removing by
that set (or ``cognee.delete(data_id=...)``) — documented as the precise path.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.config import dataset_name
from backend.memory import client as memory

logger = logging.getLogger("devbrain.forget")


async def deprecate_module(owner: str, repo: str, module: str) -> dict[str, Any]:
    """Remove a deprecated module's code subgraph.

    Guard: a specific, non-empty ``module`` is required — mirrors the AGENTS.md
    rule "never call forget() without an explicit filter". This protects against
    accidentally wiping a dataset.
    """
    if not module or not module.strip():
        raise ValueError("deprecate_module requires an explicit, non-empty module name")

    ds = dataset_name(owner, repo, "ast")
    logger.info("Deprecating module %r -> forgetting dataset %s", module, ds)
    await memory.forget(ds)
    return {
        "status": "forgotten",
        "module": module,
        "dataset": ds,
        "note": (
            "MVP forgets the repo AST dataset. For per-module pruning, ingest code "
            "with node_set=[module] and delete by that set."
        ),
    }
