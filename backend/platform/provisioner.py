"""Docker-based provisioner for per-tenant DevBrain instances."""
from __future__ import annotations
import logging
import os
from pathlib import Path

logger = logging.getLogger("devbrain.platform.provisioner")

PLATFORM_NETWORK = "devbrain-platform"
PLATFORM_DATA_DIR = os.getenv("PLATFORM_DATA_DIR", "/data/platform")
PLATFORM_IMAGE = os.getenv("DEVBRAIN_IMAGE", "devbrain-devbrain-api")
PLATFORM_PORT_START = int(os.getenv("PLATFORM_PORT_START", "8100"))
PLATFORM_PORT_END = int(os.getenv("PLATFORM_PORT_END", "8199"))


def _docker_client():
    try:
        import docker
        return docker.from_env()
    except Exception as exc:
        logger.error("Cannot connect to Docker: %s", exc)
        raise RuntimeError("Docker is not available") from exc


def _ensure_network() -> None:
    """Create the shared Docker network for tenant containers if it doesn't exist."""
    client = _docker_client()
    try:
        client.networks.get(PLATFORM_NETWORK)
    except Exception:
        client.networks.create(PLATFORM_NETWORK, driver="bridge")
        logger.info("Created Docker network: %s", PLATFORM_NETWORK)


def _find_free_port(used_ports: set[int]) -> int:
    """Find the next available port in the configured range."""
    for port in range(PLATFORM_PORT_START, PLATFORM_PORT_END + 1):
        if port not in used_ports:
            return port
    raise RuntimeError(f"No free ports available in {PLATFORM_PORT_START}-{PLATFORM_PORT_END}")


def _ensure_network_attached(container_name: str) -> None:
    """Verify the container is on the platform network; connect if not."""
    client = _docker_client()
    try:
        container = client.containers.get(container_name)
        networks = container.attrs["NetworkSettings"]["Networks"] or {}
        if PLATFORM_NETWORK not in networks:
            client.networks.get(PLATFORM_NETWORK).connect(container)
            logger.info("Attached %s to network %s", container_name, PLATFORM_NETWORK)
    except Exception as exc:
        logger.warning("Could not verify network for %s: %s", container_name, exc)


async def provision_instance(instance_id: str, repo: str, port: int, secrets: dict) -> dict:
    """
    Provision three Docker containers for a tenant:
      - redis-{id}          : Redis job queue
      - devbrain-{id}-api   : FastAPI server
      - devbrain-{id}-worker: ARQ worker

    Returns a dict with container names and status.
    """
    client = _docker_client()
    _ensure_network()

    redis_name  = f"devbrain-{instance_id}-redis"
    api_name    = f"devbrain-{instance_id}-api"
    worker_name = f"devbrain-{instance_id}-worker"

    data_dir = Path(PLATFORM_DATA_DIR) / instance_id
    data_dir.mkdir(parents=True, exist_ok=True)

    env = {
        "GITHUB_TOKEN":          secrets.get("github_token", ""),
        "COGNEE_API_KEY":        secrets.get("cognee_api_key", ""),
        "COGNEE_BASE_URL":       secrets.get("cognee_url", ""),
        "GEMINI_API_KEY":        secrets.get("gemini_api_key", ""),
        "LLM_PROVIDER":          os.getenv("LLM_PROVIDER", "gemini") if secrets.get("gemini_api_key") else "openai",
        "LLM_MODEL":             os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite") if secrets.get("gemini_api_key") else "openai/gpt-4o",
        "EMBEDDING_PROVIDER":    os.getenv("EMBEDDING_PROVIDER", "gemini") if secrets.get("gemini_api_key") else "openai",
        "EMBEDDING_MODEL":       os.getenv("EMBEDDING_MODEL", "gemini/gemini-embedding-2") if secrets.get("gemini_api_key") else "openai/text-embedding-3-small",
        "EMBEDDING_DIMENSIONS":  os.getenv("EMBEDDING_DIMENSIONS", "768"),
        "COGNEE_SKIP_CONNECTION_TEST": "true",
        "LLM_API_KEY":           secrets.get("cognee_api_key") or secrets.get("gemini_api_key", ""),
        "EMBEDDING_API_KEY":     secrets.get("cognee_api_key") or secrets.get("gemini_api_key", ""),
        "GITHUB_REPO":           repo,
        "GITHUB_WEBHOOK_SECRET": secrets.get("webhook_secret", ""),
        "REDIS_URL":             f"redis://{redis_name}:6379",
        "COGNEE_DATA_DIR":       f"/data/{instance_id}/cognee",
        "COGNEE_SYSTEM_DIR":     f"/data/{instance_id}/cognee-system",
        "REGISTRY_PATH":         f"/data/{instance_id}/repos.json",
    }

    volumes = {
        str(data_dir): {"bind": f"/data/{instance_id}", "mode": "rw"},
    }

    # 1. Redis
    try:
        existing = client.containers.get(redis_name)
        if existing.status != "running":
            existing.start()
        _ensure_network_attached(redis_name)
        logger.info("Redis container %s already exists", redis_name)
    except Exception:
        client.containers.run(
            "redis:7-alpine",
            name=redis_name,
            detach=True,
            network=PLATFORM_NETWORK,
            restart_policy={"Name": "unless-stopped"},
        )
        _ensure_network_attached(redis_name)
        logger.info("Started Redis container: %s", redis_name)

    # 2. API
    try:
        existing = client.containers.get(api_name)
        if existing.status != "running":
            existing.start()
        _ensure_network_attached(api_name)
        logger.info("API container %s already exists", api_name)
    except Exception:
        client.containers.run(
            PLATFORM_IMAGE,
            name=api_name,
            detach=True,
            network=PLATFORM_NETWORK,
            ports={"8000/tcp": port},
            environment=env,
            volumes=volumes,
            restart_policy={"Name": "unless-stopped"},
        )
        _ensure_network_attached(api_name)
        logger.info("Started API container: %s on port %d", api_name, port)

    # 3. Worker
    try:
        existing = client.containers.get(worker_name)
        if existing.status != "running":
            existing.start()
        _ensure_network_attached(worker_name)
        logger.info("Worker container %s already exists", worker_name)
    except Exception:
        client.containers.run(
            PLATFORM_IMAGE,
            name=worker_name,
            command=["python", "-m", "arq", "backend.worker.WorkerSettings"],
            detach=True,
            network=PLATFORM_NETWORK,
            environment=env,
            volumes=volumes,
            restart_policy={"Name": "unless-stopped"},
        )
        _ensure_network_attached(worker_name)
        logger.info("Started Worker container: %s", worker_name)

    return {
        "container_api_name":    api_name,
        "container_worker_name": worker_name,
        "container_redis_name":  redis_name,
        "status":                "running",
    }


async def stop_instance(instance_id: str) -> None:
    """Stop and remove all three containers for a tenant instance."""
    client = _docker_client()
    for suffix in ("api", "worker", "redis"):
        name = f"devbrain-{instance_id}-{suffix}"
        try:
            container = client.containers.get(name)
            container.stop(timeout=10)
            container.remove(force=True)
            logger.info("Removed container: %s", name)
        except Exception:
            pass  # already gone


def get_instance_status(instance_id: str) -> str:
    """Return the current status of the tenant's API container."""
    client = _docker_client()
    api_name = f"devbrain-{instance_id}-api"
    try:
        container = client.containers.get(api_name)
        status = container.status
        return "running" if status == "running" else "stopped"
    except Exception:
        return "not_found"


def allocate_port(used_ports: list[int]) -> int:
    """Allocate the next free port, given a list of already-used ports."""
    return _find_free_port(set(used_ports))
