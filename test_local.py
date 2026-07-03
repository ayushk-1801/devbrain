"""Quick test script — runs ingestion directly without Redis/ARQ.

Usage:
    python test_local.py <owner>/<repo> [sync_history_days]

Examples:
    python test_local.py topoteretes/cognee 30
    python test_local.py microsoft/vscode 7
"""

import asyncio
import sys
import os

# Ensure backend is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    if len(sys.argv) < 2:
        print("Usage: python test_local.py <owner>/<repo> [sync_history_days]")
        print("Example: python test_local.py topoteretes/cognee 30")
        sys.exit(1)

    repo = sys.argv[1]
    sync_days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    print(f"\n{'='*60}")
    print(f"DevBrain Local Test — Ingesting {repo}")
    print(f"{'='*60}\n")

    # 1. Connect to Cognee
    from backend.memory import client as memory
    print("[1/4] Connecting to Cognee...")
    await memory.connect()
    print("  OK\n")

    # 2. Run full sync
    from backend import service
    print(f"[2/4] Ingesting {repo} (last {sync_days} days)...")
    result = await service.full_sync(repo, sync_days)
    print(f"  OK: {result}\n")

    # 3. Run a test query
    from backend.memory.query import ask_devbrain
    print("[3/4] Running test query...")
    query_result = await ask_devbrain(
        "What is the main architecture of this project?",
        repo=repo,
        mode="hybrid",
    )
    print(f"  Answer: {query_result.get('answer', 'N/A')}\n")

    # 4. Disconnect
    print("[4/4] Disconnecting...")
    await memory.disconnect()

    print(f"{'='*60}")
    print("Done! Ingestion complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
