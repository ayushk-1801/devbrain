# DevBrain

A living engineering memory for software teams. DevBrain ingests GitHub commits, pull
requests, issues, ADRs, and codebase structure into [Cognee](https://www.cognee.ai)'s
hybrid graph + vector memory, then answers *"why was this changed?"* questions with
sourced provenance.

---

## How it works

```
[Maintainer's server]
  FastAPI backend  ←  GitHub webhooks (push, PR, issues, review comments)
    ├── GitHub Token + Cognee + LLM keys (stays on server)
    └── REST API  (:8000)

          ↕  HTTP

[Each user's machine]
  MCP server  ←  Claude Code / Cursor / OpenCode
    └── Only needs: DEVBRAIN_API_URL
```

A maintainer hosts one backend. Every user on the team points the lightweight MCP
client at that URL — no GitHub token, no Cognee config, no LLM keys required on
the user's side.

---

## For maintainers — hosting the backend

### 1. Clone and install

```bash
git clone https://github.com/your-org/devbrain
cd devbrain
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# LLM backend — pick one

# Option A: Cognee Cloud (recommended for teams)
COGNEE_API_KEY=...          # from cognee.ai — use code COGNEE-35 for a free dev plan
COGNEE_BASE_URL=...         # your hosted Cognee instance URL

# Option B: Local Gemini (no extra infra, good for solo/small teams)
GEMINI_API_KEY=...          # from https://aistudio.google.com/apikey
LLM_MODEL=gemini/gemini-2.0-flash-exp
EMBEDDING_MODEL=gemini/text-embedding-004
EMBEDDING_DIMENSIONS=768
COGNEE_SKIP_CONNECTION_TEST=true

# GitHub
GITHUB_TOKEN=ghp_...        # needs repo read scope
GITHUB_WEBHOOK_SECRET=...   # any random string; paste the same into GitHub's webhook form

# Optional: default repo for /query without ?repo=
GITHUB_REPO=owner/repo-name
```

### 3. Start the backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Or with Docker:

```bash
docker-compose up devbrain-api
```

### 4. Ingest a repo

```bash
curl -X POST http://localhost:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{"repo": "owner/your-repo", "sync_history_days": 90}'
```

This pulls 90 days of commits, PRs, issues, ADRs, and code structure into the
knowledge graph. The response includes per-source counts:

```json
{
  "repo": "owner/your-repo",
  "ingested": { "commits": 312, "prs": 47, "issues": 83, "adrs": 6, "ast_modules": 24 }
}
```

### 5. Set up GitHub webhooks

In your repo: **Settings → Webhooks → Add webhook**

| Field | Value |
|-------|-------|
| Payload URL | `https://your-domain.com/webhook/github` |
| Content type | `application/json` |
| Secret | Same value as `GITHUB_WEBHOOK_SECRET` in `.env` |
| Events | Select **individual events** and tick: |
| | `Pushes` |
| | `Pull requests` |
| | `Issues` |
| | `Issue comments` |
| | `Pull request review comments` |

For local development, expose the backend with:

```bash
ngrok http 8000
# or
cloudflared tunnel --url http://localhost:8000
```

After saving the webhook, GitHub will send a ping event — you should see HTTP 200
in the webhook delivery log.

**What gets captured automatically after this:**

| GitHub event | When DevBrain ingests |
|---|---|
| Push | Every commit that touches files |
| Pull request | Opened, edited, updated, and merged |
| Issues | Opened, labeled, and closed |
| Issue comment | Any new comment on an issue or PR conversation thread |
| PR review comment | Any new inline code review comment |

---

## For users — connecting to the hosted backend

You only need the URL of the hosted backend. Ask your maintainer for it.

### Claude Code

```bash
DEVBRAIN_API_URL=https://devbrain.your-company.com \
  claude mcp add devbrain -- python -m backend.mcp_server
```

Or add it permanently to your Claude Code config:

```bash
claude mcp add devbrain \
  --env DEVBRAIN_API_URL=https://devbrain.your-company.com \
  -- python -m backend.mcp_server
```

### OpenCode

```bash
opencode mcp add devbrain -- python -m backend.mcp_server
opencode mcp env devbrain DEVBRAIN_API_URL https://devbrain.your-company.com
```

Or copy and edit the example config:

```bash
cp opencode.example.jsonc opencode.jsonc
# set DEVBRAIN_API_URL in opencode.jsonc
```

### Verify the connection

After registering, ask your agent:

```
list_repos()
```

You should see the repos the maintainer has already ingested.

---

## MCP tools

| Tool | What it does |
|------|-------------|
| `ingest_repo(repo, sync_history_days?)` | Full sync: commits, PRs, issues, ADRs, code structure |
| `query_devbrain(question, repo?, mode?)` | NL query over the knowledge graph |
| `forget_module(repo, module)` | Prune a deprecated module's subgraph |
| `list_repos()` | List all ingested repos |
| `refresh_memory(repo?)` | Run memify enrichment (expensive — use deliberately) |

**Query modes:**

| Mode | Best for |
|------|----------|
| `hybrid` (default) | Most questions — auto-routes between semantic and graph |
| `why` | "Why was X changed?" — deep multi-hop graph traversal |
| `chunks` | Raw text retrieval when you want the exact source text |

**Example queries:**

```
"Why was the authentication module decoupled from the user service?"
"Who approved the migration to microservices?"
"What issues were labeled 'security' in Q1?"
"Which modules depend on PaymentGateway?"
"What was the fix for the last session timeout bug?"
```

---

## REST API reference

```bash
uvicorn backend.main:app --reload --port 8000
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Status check |
| `GET`  | `/repos` | List all ingested repos |
| `POST` | `/ingest` | Full historical sync (`{"repo": "owner/repo", "sync_history_days": 90}`) |
| `GET`  | `/query?q=...&repo=...&mode=...` | Natural language recall |
| `POST` | `/refresh?repo=...` | Run memify for one repo (omit `repo` for all) |
| `DELETE` | `/module/{owner}/{repo}/{module}` | Surgical module pruning |
| `POST` | `/webhook/github` | GitHub webhook receiver (HMAC-verified) |

### curl examples

```bash
# Query
curl "localhost:8000/query?q=why+was+auth+refactored&repo=owner/your-repo&mode=why"

# Trigger memify refresh
curl -X POST "localhost:8000/refresh?repo=owner/your-repo"

# Prune a deprecated module
curl -X DELETE localhost:8000/module/owner/your-repo/legacy_payment_v1
```

---

## Cognee integration

| DevBrain concept | Cognee SDK call |
|---|---|
| Ingest anything | `cognee.remember(payload, dataset_name=...)` |
| Query | `cognee.recall(q)` / `cognee.search(SearchType.GRAPH_COMPLETION)` |
| Self-improving memory | `cognee.memify(dataset=...)` — runs weekly automatically |
| Surgical pruning | `cognee.forget(dataset=...)` |

Datasets follow the pattern `repo_{owner}_{repo}_{type}` where `type` is one of
`commits`, `prs`, `issues`, `adrs`, `ast`.
