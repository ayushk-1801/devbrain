"""Natural-language query routing over DevBrain's memory."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import cognee
from cognee import SearchType

from backend.memory import client as memory

logger = logging.getLogger("devbrain.query")

# Query modes exposed via the API.
#   hybrid  -> recall() auto-routing (default, good for most queries)
#   why     -> graph completion (best for 'why was X changed?' questions)
#   chunks  -> raw chunk retrieval (raw PR/commit text)
_SEARCH_TYPES = {
    "why": SearchType.GRAPH_COMPLETION,
    "chunks": SearchType.CHUNKS,
}


async def ask_devbrain(question: str, repo: str | None = None, mode: str = "hybrid") -> dict[str, Any]:
    """Answer a natural-language question against the knowledge graph.

    Returns a dict with the answer plus raw results for provenance display.
    Retries briefly if the graph database is locked by a concurrent ingestion job.
    """
    search_type = _SEARCH_TYPES.get(mode) if mode != "hybrid" else None
    if mode not in ("hybrid", *_SEARCH_TYPES):
        raise ValueError(
            f"unknown mode {mode!r}; expected one of "
            f"{['hybrid', *sorted(_SEARCH_TYPES)]}"
        )

    _LOCK_MSG = "Lock is held"
    for attempt in range(6):
        try:
            if mode == "hybrid":
                results = await memory.recall(question)
            else:
                results = await cognee.search(question, search_type=search_type)
            break
        except RuntimeError as exc:
            if _LOCK_MSG in str(exc) and attempt < 5:
                wait = 2 ** attempt
                logger.warning("Graph DB locked (ingestion running), retry in %ss", wait)
                await asyncio.sleep(wait)
            else:
                raise
    else:
        raise RuntimeError("Graph database is busy with ingestion. Try again in a moment.")

    # Cognee returns a list; the first element is the synthesized answer for
    # completion-style searches, individual hits for chunk searches.
    answer = results[0] if results else None
    return {
        "question": question,
        "repo": repo,
        "mode": mode,
        "answer": answer,
        "results": results,
    }
