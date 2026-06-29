# AGENTS.md — DevBrain

> **DevBrain** is a living engineering memory for software teams.  
> It ingests GitHub commits, pull requests, ADRs, and codebase AST into a persistent,
> self-improving knowledge graph powered by Cognee's hybrid graph-vector memory layer.
> Agents using this file operate inside that system.

---

## What This Project Does

DevBrain solves institutional knowledge loss — the "why was this changed?" problem that
every engineering team faces. It captures not just what the code looks like, but why it
became what it is, and makes that knowledge permanently queryable by both humans and AI
coding agents.

**Core capability:** Ask anything about your codebase's history. Get sourced answers,
not guesses, with full provenance back to the original PR, commit, or ADR.

---

## Project Structure

```
devbrain/
├── AGENTS.md                        ← you are here
├── README.md
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── main.py                      # FastAPI app + webhook endpoint
│   ├── ingestion/
│   │   ├── commits.py               # ingest_commit()
│   │   ├── pull_requests.py         # ingest_pr()
│   │   ├── adrs.py                  # ingest_adrs()
│   │   └── codebase.py              # ingest_repo_structure()
│   ├── memory/
│   │   ├── query.py                 # ask_devbrain() / recall()
│   │   ├── improve.py               # weekly_memory_refresh()
│   │   └── forget.py                # deprecate_module()
│   └── config.py                    # Cognee + GitHub config
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── GraphViz.jsx         # D3.js force-directed graph
│   │   │   ├── QueryBar.jsx         # Natural language query input
│   │   │   ├── ResultPanel.jsx      # Answer + provenance display
│   │   │   └── Timeline.jsx         # Decision timeline view
│   │   └── api.js
│   └── package.json
│
└── cognee-mcp/                      # Cognee MCP server (git submodule)
```

---

## Memory Architecture

DevBrain uses Cognee's hybrid graph-vector memory layer. Every piece of engineering
knowledge lives in one of three stores, and all three are queried simultaneously at
recall time.

```
GitHub Repository
  Commits · Pull Requests · ADRs · Code Files
          │
          ▼
DevBrain Ingestion Server (FastAPI)
  • Fetches event payload + changed files via GitHub API
  • Structures context into memory payloads
  • Calls cognee.remember() for each event
          │
          ▼
Cognee Memory Engine — 6-Stage ECL Pipeline
  1. Classify documents
  2. Check permissions
  3. Extract chunks
  4. LLM: extract entities + relationships
  5. Generate summaries
  6. Embed → vector store + commit to graph
          │
  ┌───────┼───────┐
  ▼       ▼       ▼
Graph   Vector  Relational
Store   Store   Store
Kuzu/   Lance   SQLite
Neo4j   DB
          │
  ┌───────┴──────────┐
  ▼                  ▼
Cognee MCP       DevBrain Web UI
Server           React + D3.js
  │
  ▼
Claude Code / Cursor / any MCP agent
```

---

## The Four Cognee APIs — How DevBrain Uses Them

Every agent working on this project must understand all four APIs and where they are
called. Judges score "Best Use of Cognee" explicitly.

### `remember()` — Permanent Ingestion

Called automatically on every GitHub push and every merged PR. Structures raw event
data into the knowledge graph via Cognee's 6-stage ECL pipeline.

```python
await cognee.remember(
    memory_payload,
    dataset_name="repo_owner_repo_commits"
)
```

**Where it's called:** `backend/ingestion/commits.py`, `backend/ingestion/pull_requests.py`,
`backend/ingestion/adrs.py`, `backend/ingestion/codebase.py`

---

### `recall()` — Hybrid Query Routing

Natural language queries automatically route between semantic vector similarity (fuzzy
concept matching) and deep graph traversal (multi-hop relationship following).
A single question hits both layers simultaneously.

```python
results = await cognee.recall("why was the auth module refactored?")
```

For explicit retrieval mode control:

```python
from cognee.api.v1.search import SearchType

results = await cognee.search(
    query_text="which modules depend on PaymentGateway?",
    query_type=SearchType.GRAPH_COMPLETION   # best for "why" questions
)
```

**Available modes:** `GRAPH_COMPLETION` (best for why-questions), `HYBRID` (best for
most queries), `CHUNKS` (raw PR text retrieval).

**Where it's called:** `backend/memory/query.py`

---

### `improve()` / `memify()` — Self-Improving Memory

Runs on a weekly cron job. Prunes stale decision nodes, strengthens frequently-queried
paths with higher edge weights, and adds derived facts Cognee infers from the existing
graph.

```python
await cognee.improve()   # runs memify under the hood
```

**Where it's called:** `backend/memory/improve.py`  
**Schedule:** every 7 days via APScheduler or OS cron

---

### `forget()` — Surgical Pruning

When a module is deprecated or replaced, its entire subgraph is cleanly removed.
The rest of the graph is untouched. This is also a live demo moment — nodes dissolve
from the D3 visualization in real time.

```python
await cognee.forget(
    dataset="repo_owner_repo_ast",
    filter_by={"module": "legacy_payment_v1"}
)
```

**Where it's called:** `backend/memory/forget.py`  
**REST endpoint:** `DELETE /module/{repo}/{module}`

---

## Data Sources and Graph Schema

### GitHub Commits
- **Ingests:** message, diff summary, author, timestamp, files changed
- **Graph nodes:** `Commit`, `Developer`, `File`
- **Graph edges:** `COMMIT → MODIFIED → File`, `Commit → AUTHORED_BY → Developer`

### Pull Requests
- **Ingests:** title, description, review comments, approval decisions, linked issues
- **Graph nodes:** `PullRequest`, `Developer`, `File`, `Issue`
- **Graph edges:** `PR → CHANGED → File`, `PR → MOTIVATED_BY → Issue`, `PR → APPROVED_BY → Developer`

### Architecture Decision Records (ADRs)
- **Ingests:** markdown files from `/docs/decisions/`, `/adr/`, `/docs/adr/`, `/.decisions/`
- **Graph nodes:** `ADR`, `Module`
- **Graph edges:** `ADR → JUSTIFIES → Module`, `ADR → SUPERSEDES → ADR`

### Codebase (AST via `cognee[codegraph]`)
- **Ingests:** functions, classes, modules, imports, call graphs
- **Graph nodes:** `Function`, `Class`, `Module`
- **Graph edges:** `Function → CALLS → Function`, `Class → INHERITS → Class`, `Module → DEPENDS_ON → Module`
- **Install:** `pip install cognee[codegraph]`
- **Languages supported:** Python, JS, TS, Go, Rust, Java, C#, PHP, Ruby

---

## Environment Variables

All secrets live in `.env`. Copy `.env.example` and fill in:

```bash
OPENAI_API_KEY=sk-...          # or any Cognee-supported LLM provider
GITHUB_TOKEN=ghp_...           # needs repo read + webhook access
GITHUB_REPO=owner/repo-name    # default repo to ingest
GITHUB_WEBHOOK_SECRET=...      # for webhook signature verification
COGNEE_DATA_DIR=./.cognee/data
COGNEE_SYSTEM_DIR=./.cognee/system
```

Cognee Cloud alternative: sign up at cognee.ai and use code `COGNEE-35` for a free
Developer plan ($35 value). No local vector/graph stores required.

---

## Running the Project

**One-command start (Docker):**

```bash
docker-compose up
```

This starts three services: `devbrain-api` (FastAPI on :8000), `devbrain-mcp` (Cognee
MCP server on :8765), and `devbrain-ui` (React on :3000). A shared `cognee-data` volume
persists the knowledge graph across restarts.

**First ingestion:**

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{"repo": "owner/your-repo", "sync_history_days": 90}'
```

**First query:**

```bash
curl "http://localhost:8000/query?q=why+was+auth+refactored&repo=owner/your-repo"
```

**Connect to Claude Code:**

```bash
claude mcp add devbrain -s project \
  -e LLM_API_KEY="$OPENAI_API_KEY" \
  -- uv --directory ./cognee-mcp run cognee-mcp
```

Once connected, Claude Code calls DevBrain automatically in every session — no
explicit prompting required.

---

## REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest` | Full historical sync for a repo |
| `POST` | `/webhook/github` | GitHub webhook receiver (push + PR events) |
| `GET` | `/query?q=...&repo=...` | Natural language recall |
| `DELETE` | `/module/{repo}/{module}` | Surgical module pruning via `forget()` |

---

## Webhook Setup

Register a GitHub webhook pointing to `https://your-domain/webhook/github` with:
- **Content type:** `application/json`
- **Events:** `push`, `pull_request`
- **Secret:** same value as `GITHUB_WEBHOOK_SECRET` in `.env`

For local development, use ngrok or Cloudflare Tunnel to expose the FastAPI server.

---

## Agent Guidelines

If you are an AI coding agent (Claude Code, Cursor, or similar) working inside this
project, follow these rules:

**Before modifying any ingestion file**, run a recall query to understand the current
schema and dataset naming convention:
```python
await cognee.recall("what datasets exist and what is the naming convention?")
```

**Dataset names follow the pattern:** `repo_{owner}_{repo}_{type}` where type is one
of `commits`, `decisions`, `adrs`, or `ast`. Never invent a new naming convention —
consistency is critical for cross-source multi-hop traversal to work.

**Never call `cognee.forget()` without an explicit, specific `filter_by` argument.**
Calling it on a dataset without filtering deletes the entire dataset. This is
destructive and irreversible.

**The `cognee.improve()` call is expensive.** Do not call it inline during a user
query or a webhook handler. It belongs only in the scheduled cron in
`backend/memory/improve.py`.

**Incremental ingestion only.** When processing a `push` webhook, only ingest
changed files — do not trigger a full repo re-scan. Full scans happen only on the
initial `/ingest` endpoint call.

**All ingestion is async.** Every `cognee.remember()` call must be awaited inside
an async function and dispatched as a background task from webhook handlers using
`asyncio.create_task()` — never block the webhook response.

---

## Key Queries to Test Against

These are the canonical test cases. If a query returns a sourced, accurate answer,
the memory graph for that data source is working correctly.

```
"Why was the authentication module decoupled from the user service?"
"Who made the decision to use PostgreSQL over MongoDB?"
"What was the fix for the last session timeout bug?"
"Which modules depend on PaymentGateway and were they updated after the refactor?"
"What architectural decisions were made in Q1 2025?"
"Why was the v1 API deprecated?"
"Who approved the migration to microservices?"
```

Multi-hop traversal test (requires both AST graph and PR decision graph populated):
```
"Which modules depend on PaymentGateway and have any of them been modified
since the last refactor?"
```

This query should follow `DEPENDS_ON` edges across 3 hops in the AST graph, then
cross-reference with the commit graph to surface which impacted modules were and
weren't updated post-refactor.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Memory engine | `cognee[codegraph]` | Core requirement; AST parsing built in |
| Graph store | Kuzu (local) / Neo4j (demo) | Zero infra locally; Neo4j for graph viz |
| Vector store | LanceDB (file-based) | Zero infra; fast for hackathon scale |
| Ingestion API | FastAPI + uvicorn | Async-native; fast to build |
| GitHub integration | PyGithub + webhooks | Commit/PR fetching + real-time events |
| Agent interface | Cognee MCP server | Native Claude Code + Cursor support |
| Frontend | React + D3.js | Live force-directed graph visualization |
| Deployment | Docker Compose | One-command setup |
| LLM | OpenAI GPT-4o or Claude claude-sonnet-4-6 | Via Cognee config |

---

## Hackathon Context

**Event:** WeMakeDevs × Cognee — "The Hangover Part AI"  
**Dates:** June 29 – July 5, 2026  
**Prizes:** MacBook Neo (Open Source track) · iPhone 17 (Cognee Cloud track) · $100/PR (open source contributions)  
**Side prizes:** Keychron keyboard (best blog) · Exclusive swag (top 10 social posts)

**Judging criteria this project addresses:**

| Criterion | How DevBrain addresses it |
|-----------|--------------------------|
| Potential Impact | Engineering knowledge loss affects every team with >5 engineers and >6 months of history |
| Creativity & Innovation | No existing tool combines code AST + PR decisions + ADRs in a self-improving graph |
| Technical Excellence | Hybrid retrieval, incremental ingestion, MCP-native, Docker deployment |
| Best Use of Cognee | All 4 APIs used in meaningful, non-trivial ways; codegraph extra for AST |
| User Experience | Live D3 graph viz, NL query bar, one-command Docker setup |
| Presentation Quality | 5 scripted demo moments, clean README, architecture diagram, blog post |

---

## Key Links

| Resource | URL |
|----------|-----|
| Hackathon page | https://www.wemakedevs.org/hackathons/cognee |
| Cognee GitHub | https://github.com/topoteretes/cognee |
| Cognee docs | https://docs.cognee.ai |
| Cognee MCP docs | https://docs.cognee.ai/cognee-mcp/integrations/claude-code |
| CodeGraph example | https://docs.cognee.ai/examples/code-assistants |
| Cognee Cloud | cognee.ai — use code `COGNEE-35` for free Developer plan |

---

*Built for WeMakeDevs × Cognee Hackathon · Jun 29 – Jul 5, 2026*  
*"Your AI woke up in Vegas with no memory of last night. DevBrain fixes that."*