# DevBrain

A living engineering memory for software teams. DevBrain ingests GitHub commits, pull
requests, ADRs, and codebase structure into [Cognee](https://www.cognee.ai)'s hybrid
graph + vector memory, then answers *"why was this changed?"* questions with sourced
provenance.

DevBrain exposes **two interfaces** over a shared multi-repo service layer:

- **MCP server** (`backend/mcp_server.py`) — for AI coding agents (Claude Code, Cursor, etc.)
- **REST API** (`backend/main.py`) — for humans, curl, and GitHub webhooks

## Cognee mode (cloud or local)

The backend auto-selects its memory backend at startup:

- **Local (default)** — used when `COGNEE_API_KEY` is empty. Self-hosted Cognee with
  file-based stores (Kuzu graph + LanceDB vector + SQLite) under `COGNEE_DATA_DIR` /
  `COGNEE_SYSTEM_DIR`. **LLM + embeddings are served by Google Gemini**, so the only key
  you need is `GEMINI_API_KEY` (get one at https://aistudio.google.com/apikey). No OpenAI
  key required. Installs via the `cognee[gemini]` extra.
- **Cognee Cloud** — used when `COGNEE_API_KEY` is set. All Cognee SDK calls are routed to
  your hosted instance (`COGNEE_BASE_URL`). Sign up at cognee.ai with code `COGNEE-35`.

### Local Gemini settings (in `.env`)

```
GEMINI_API_KEY=...                              # required for local mode
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-3.1-flash-lite
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini/gemini-embedding-2
EMBEDDING_DIMENSIONS=3072
COGNEE_SKIP_CONNECTION_TEST=true                # bypasses the 30s LLM preflight check
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then set GEMINI_API_KEY + GITHUB_TOKEN (local mode)
```

## MCP Server (for AI agents)

Run on stdio (default):

```bash
python -m backend.mcp_server
```

### OpenCode

Add DevBrain to your `opencode.jsonc` — copy the example and fill in your tokens:

```bash
cp opencode.example.jsonc opencode.jsonc
# edit opencode.jsonc with your paths, GITHUB_TOKEN, and GEMINI_API_KEY
```

Or register directly with the CLI:

```bash
opencode mcp add devbrain -- python -m backend.mcp_server
opencode mcp env devbrain GITHUB_TOKEN ghp_xxx
opencode mcp env devbrain GEMINI_API_KEY your_gemini_key
opencode mcp env devbrain COGNEE_SKIP_CONNECTION_TEST true
```

List connected servers and auth status:

```bash
opencode mcp list
```

The server is fully multi-repo — every tool takes an explicit `repo` param.

### Claude Code

Register the MCP server with your GitHub and Gemini credentials:

```bash
claude mcp add devbrain \
  --env GITHUB_TOKEN=ghp_xxx \
  --env GEMINI_API_KEY=your_gemini_key \
  --env COGNEE_SKIP_CONNECTION_TEST=true \
  -- python -m backend.mcp_server
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `ingest_repo(repo, sync_history_days?)` | Full sync of a repo (commits, PRs, ADRs, AST) |
| `query_devbrain(question, repo?, mode?)` | NL query over the knowledge graph |
| `forget_module(repo, module)` | Prune a deprecated module's subgraph |
| `list_repos()` | List all ingested repos |
| `refresh_memory(repo?)` | Run memify enrichment for one or all repos |

## REST API (for humans and webhooks)

```bash
uvicorn backend.main:app --reload --port 8000
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest` | Full historical sync of a repo (`{"repo": "...", "sync_history_days": 90}`) |
| `POST` | `/webhook/github` | GitHub webhook receiver (push + pull_request), HMAC-verified |
| `GET`  | `/query?q=...&repo=...&mode=...` | Natural language recall (`mode`: `hybrid` \| `why` \| `chunks`) |
| `DELETE` | `/module/{owner}/{repo}/{module}` | Surgical module pruning via Cognee `forget()` |

### Examples

```bash
# Ingest
curl -X POST localhost:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{"repo":"owner/your-repo","sync_history_days":90}'

# Query
curl "localhost:8000/query?q=why+was+auth+refactored&repo=owner/your-repo&mode=why"

# Prune a module
curl -X DELETE localhost:8000/module/owner/your-repo/legacy_payment_v1
```

## How DevBrain uses Cognee

| DevBrain concept | Real Cognee SDK call |
|---|---|
| Permanent ingestion | `cognee.remember(payload, dataset_name=...)` (runs add → cognify → improve) |
| Hybrid query | `cognee.recall(q)` / `cognee.search(query_type=SearchType.GRAPH_COMPLETION)` |
| Self-improving memory | `cognee.memify(dataset=...)` (weekly cron) |
| Surgical pruning | `cognee.forget(dataset=...)` |

Datasets follow the pattern `repo_{owner}_{repo}_{type}` where type is one of
`commits`, `prs`, `adrs`, `ast`.
