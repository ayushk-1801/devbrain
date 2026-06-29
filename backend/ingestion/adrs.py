"""ADR ingestion: scans conventional ADR directories and remembers each record."""

from __future__ import annotations

from backend.config import dataset_name
from backend.ingestion import github_client
from backend.memory import client as memory


def _adr_payload(owner: str, repo: str, adr: dict[str, str]) -> str:
    return (
        f"# Architecture Decision Record — {adr['path']} ({owner}/{repo})\n\n"
        f"{adr['text']}\n"
    )


async def ingest_adrs(owner: str, repo: str) -> int:
    """Fetch and ingest all ADR markdown files. Returns count."""
    adrs = github_client.fetch_adrs(owner, repo)
    for adr in adrs:
        payload = _adr_payload(owner, repo, adr)
        await memory.remember(payload, dataset_name(owner, repo, "adrs"))
    return len(adrs)
