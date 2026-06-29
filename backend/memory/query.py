"""Natural-language query routing over DevBrain's memory."""

from __future__ import annotations

from typing import Any

import cognee
from cognee import SearchType

from backend.memory import client as memory

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
    """
    if mode == "hybrid":
        results = await memory.recall(question)
    else:
        search_type = _SEARCH_TYPES.get(mode)
        if search_type is None:
            raise ValueError(
                f"unknown mode {mode!r}; expected one of "
                f"{['hybrid', *sorted(_SEARCH_TYPES)]}"
            )
        results = await cognee.search(query_text=question, query_type=search_type)

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
