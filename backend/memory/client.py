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
        if not settings.COGNEE_BASE_URL:
            raise RuntimeError(
                "Cloud mode requires COGNEE_BASE_URL (e.g. https://your-instance.cognee.ai). "
                "Set it in .env alongside COGNEE_API_KEY."
            )
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


async def get_graph_data(repo: str | None = None) -> dict:
    """Return raw graph nodes and edges from Cognee's graph engine.

    Serialises every node and edge into plain dicts so the result is
    JSON-safe for the REST ``/graph`` endpoint.
    """
    from cognee.infrastructure.databases.graph import get_graph_engine
    import sqlite3
    import os
    from backend.config import settings, split_repo, _safe
    from backend import registry

    # --- Query node-to-dataset mapping from SQLite -------------------------
    node_to_dataset: dict[str, str] = {}
    db_path = os.path.join(settings.COGNEE_SYSTEM_DIR, "databases", "cognee_db")
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.label, d.name
                FROM nodes n
                JOIN datasets d ON n.dataset_id = d.id
            """)
            for label, dataset_name in cursor.fetchall():
                node_to_dataset[label] = dataset_name
            conn.close()
        except Exception as exc:
            logger.warning("Failed to query node-dataset mapping from SQLite: %s", exc)

    # Reconstruct repo string from dataset name
    def get_repo_for_dataset(dataset_name: str) -> str | None:
        if not dataset_name:
            return None
        for r in registry.list_repos():
            try:
                owner, repo_name = split_repo(r)
                prefix = f"repo_{_safe(owner)}_{_safe(repo_name)}_"
                if dataset_name.startswith(prefix):
                    return r
            except Exception:
                continue
        return None

    graph_engine = await get_graph_engine()
    nodes, edges = await graph_engine.get_graph_data()

    # --- Serialise nodes ---------------------------------------------------
    serialized_nodes: list[dict] = []
    for node in nodes:
        n: dict = {}
        if isinstance(node, (list, tuple)) and len(node) == 2 and isinstance(node[1], dict):
            node_id = str(node[0])
            node_props = node[1]
            n = {
                "id": node_id,
                "type": str(node_props.get("type", "Unknown")),
                "name": str(node_props.get("name", node_props.get("text", node_id))),
            }
            # Add all other properties to the node dictionary
            for k, v in node_props.items():
                if k not in n:
                    n[k] = str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
        elif isinstance(node, dict):
            node_id = str(node.get("id", ""))
            n = {
                "id": node_id,
                "type": str(node.get("type", "Unknown")),
                "name": str(node.get("name", node.get("text", node_id))),
            }
            for k, v in node.items():
                if k not in n:
                    n[k] = str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
        else:
            node_id = str(getattr(node, "id", node))
            n = {
                "id": node_id,
                "name": str(getattr(node, "name", getattr(node, "id", node))),
                "type": str(getattr(node, "type", "Unknown")),
            }
            if hasattr(node, "__dict__"):
                for k, v in node.__dict__.items():
                    if k not in n:
                        n[k] = str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v

        # Enrich node with dataset and repo properties
        dataset = node_to_dataset.get(n["id"])
        if dataset:
            n["dataset"] = dataset
            node_repo = get_repo_for_dataset(dataset)
            if node_repo:
                n["repo"] = node_repo
        serialized_nodes.append(n)

    # --- Serialise edges ---------------------------------------------------
    serialized_edges: list[dict] = []
    for edge in edges:
        e: dict = {}
        if isinstance(edge, (list, tuple)) and len(edge) >= 3:
            edge_props = edge[3] if len(edge) > 3 and isinstance(edge[3], dict) else {}
            e = {
                "source": str(edge[0]),
                "target": str(edge[1]),
                "relationship_name": str(edge[2]),
            }
            for k, v in edge_props.items():
                if k not in e:
                    e[k] = str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
        elif isinstance(edge, dict):
            e = {
                "source": str(edge.get("source", edge.get("source_node_id", ""))),
                "target": str(edge.get("target", edge.get("target_node_id", ""))),
                "relationship_name": str(edge.get("relationship_name", edge.get("label", edge.get("type", "RELATED_TO")))),
            }
            for k, v in edge.items():
                if k not in e:
                    e[k] = str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
        else:
            e = {
                "source": str(getattr(edge, "source_node_id", getattr(edge, "source", ""))),
                "target": str(getattr(edge, "target_node_id", getattr(edge, "target", ""))),
                "relationship_name": str(
                    getattr(
                        edge,
                        "relationship_name",
                        getattr(edge, "label", getattr(edge, "type", "RELATED_TO")),
                    )
                ),
            }
            if hasattr(edge, "__dict__"):
                for k, v in edge.__dict__.items():
                    if k not in e:
                        e[k] = str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
        serialized_edges.append(e)

    # --- Apply backend repo filtering if requested -------------------------
    if repo:
        try:
            owner, repo_name = split_repo(repo)
            prefix = f"repo_{_safe(owner)}_{_safe(repo_name)}_"
            
            filtered_nodes = []
            for n in serialized_nodes:
                node_repo = n.get("repo")
                node_dataset = n.get("dataset")
                if node_repo == repo or (node_dataset and node_dataset.startswith(prefix)):
                    filtered_nodes.append(n)
                elif not node_repo and not node_dataset:
                    # Fallback check for safe repo name match in fields
                    safe_r = f"{_safe(owner)}_{_safe(repo_name)}"
                    if safe_r in n["id"].lower() or safe_r in n["name"].lower():
                        filtered_nodes.append(n)
            
            valid_node_ids = {n["id"] for n in filtered_nodes}
            filtered_edges = [
                e for e in serialized_edges
                if e["source"] in valid_node_ids and e["target"] in valid_node_ids
            ]
            return {"nodes": filtered_nodes, "edges": filtered_edges}
        except Exception as exc:
            logger.warning("Error filtering by repo in backend: %s", exc)

    return {"nodes": serialized_nodes, "edges": serialized_edges}



