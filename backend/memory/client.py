"""The single chokepoint between DevBrain and the real Cognee SDK.

Everything else in the backend speaks the AGENTS.md vocabulary
(``remember`` / ``recall`` / ``improve`` / ``forget``); this module maps that
vocabulary onto the actual Cognee API and handles the cloud-vs-local connection
so no Cognee-name drift leaks into the rest of the codebase.

Verified mapping (Cognee docs via Context7):
    remember  -> cognee.remember()          (runs add -> cognify -> improve)
    recall    -> cognee.recall() / search()
    improve   -> cognee.memify()            ('improve' is not the canonical name)
    forget    -> cognee.forget(dataset=...)
"""

from __future__ import annotations

import logging
from typing import Any

import cognee

from backend.config import settings

logger = logging.getLogger("devbrain.memory")

_connected = False


async def connect() -> None:
    """Initialise the Cognee backend once, based on the configured mode.

    Cloud mode routes all SDK calls to the hosted instance. Local mode
    configures file-based stores (Kuzu / LanceDB / SQLite). Called from the
    FastAPI lifespan on startup.
    """
    global _connected
    if _connected:
        return

    if settings.COGNEE_MODE == "cloud":
        await cognee.serve(url=settings.COGNEE_BASE_URL, api_key=settings.COGNEE_API_KEY)
        logger.info("Cognee connected in CLOUD mode (%s)", settings.COGNEE_BASE_URL)
    else:
        # Local mode: self-hosted, file-based stores (Kuzu / LanceDB / SQLite)
        # with Gemini for LLM + embeddings. serve()/disconnect() are unused.
        # Provider/model/key env vars are already exported by backend.config
        # (_export_local_env); here we reinforce via Cognee's confirmed setters.
        if not settings.GEMINI_API_KEY:
            raise RuntimeError(
                "Local mode requires GEMINI_API_KEY (set it in .env, or set "
                "COGNEE_API_KEY to use Cognee Cloud)."
            )

        cognee.config.set_llm_provider(settings.LLM_PROVIDER)
        cognee.config.set_llm_model(settings.LLM_MODEL)
        cognee.config.set_llm_api_key(settings.GEMINI_API_KEY)
        cognee.config.set_embedding_dimensions(settings.EMBEDDING_DIMENSIONS)
        cognee.config.data_root_directory(settings.COGNEE_DATA_DIR)
        cognee.config.system_root_directory(settings.COGNEE_SYSTEM_DIR)
        logger.info(
            "Cognee configured in LOCAL mode (Gemini llm=%s embed=%s, data=%s)",
            settings.LLM_MODEL,
            settings.EMBEDDING_MODEL,
            settings.COGNEE_DATA_DIR,
        )

    _connected = True


async def disconnect() -> None:
    """Tear down the Cognee connection. No-op in local mode."""
    global _connected
    if not _connected:
        return
    if settings.COGNEE_MODE == "cloud":
        await cognee.disconnect()
        logger.info("Cognee disconnected (cloud)")
    _connected = False


# --- AGENTS.md vocabulary wrappers ---------------------------------------


async def remember(payload: str, dataset: str) -> Any:
    """Permanently ingest ``payload`` into ``dataset``.

    ``cognee.remember`` runs the full add -> cognify -> improve pipeline.
    """
    return await cognee.remember(payload, dataset_name=dataset, run_in_background=False)


async def recall(query: str) -> Any:
    """Hybrid query with Cognee's automatic search-strategy routing."""
    return await cognee.recall(query)


async def improve(dataset: str) -> Any:
    """Enrich an existing dataset's graph (maps to ``cognee.memify``)."""
    return await cognee.memify(dataset=dataset)


async def forget(dataset: str) -> Any:
    """Delete an entire dataset's subgraph (maps to ``cognee.forget``)."""
    return await cognee.forget(dataset=dataset)
