# DevBrain — Complete Codebase Documentation

> **DevBrain** is a living engineering memory for software teams. It ingests GitHub commits, pull requests, issues, ADRs, and codebase AST into a hybrid graph + vector memory (powered by [Cognee](https://www.cognee.ai)), then answers *"why was this changed?"* questions with sourced provenance.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & System Design](#2-architecture--system-design)
3. [Directory Structure](#3-directory-structure)
4. [Backend — FastAPI REST API](#4-backend--fastapi-rest-api)
5. [Backend — MCP Server](#5-backend--mcp-server)
6. [Ingestion Layer](#6-ingestion-layer)
7. [Memory / Query Layer](#7-memory--query-layer)
8. [GitHub Service Layer](#8-github-service-layer)
9. [Changelog & Notification Subsystem](#9-changelog--notification-subsystem)
10. [Platform Service (Auth + Multi-Tenant)](#10-platform-service-auth--multi-tenant)
11. [Frontend — React + TypeScript](#11-frontend--react--typescript)
12. [Infrastructure & Deployment](#12-infrastructure--deployment)
13. [Configuration & Environment Variables](#13-configuration--environment-variables)
14. [Testing](#14-testing)
15. [Key Features Checklist](#15-key-features-checklist)
16. [FAQ & Troubleshooting](#16-faq--troubleshooting)

---

## 1. Project Overview

DevBrain solves institutional knowledge loss — the "why was this changed?" problem. It captures not just what the code looks like, but *why* it became what it is, and makes that knowledge permanently queryable by both humans and AI coding agents.

**Tagline:** *Your Codebase Has a Memory*

**Core promise:** Ask anything about your codebase's history. Get sourced answers, not guesses, with full provenance back to the original PR, commit, or ADR.

### Who is it for?
- **Engineering teams** — Onboard new hires faster, preserve institutional knowledge when senior engineers leave
- **AI coding agents** (Claude Code, Cursor, Codex) — Give agents permanent memory of your codebase's history via MCP
- **Open-source maintainers** — Document design decisions and architecture rationale permanently

### Key differentiators
- **Fully multi-repo** — ingest any number of `owner/repo` targets
- **Self-hosted or cloud** — runs fully local (Kuzu + LanceDB + SQLite) or via Cognee Cloud
- **Agent-first** — native MCP integration for Claude Code, Cursor, Codex, OpenCode
- **Real-time webhook sync** — capture commits, PRs, issues as they happen
- **Surgical memory pruning** — remove deprecated modules without wiping the entire graph

---

## 2. Architecture & System Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Maintainer's Server                          │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │ FastAPI API  │◄───│ GitHub       │    │ ARQ Worker        │  │
│  │ (:8000)      │    │ Webhooks     │    │ (ingestion)       │  │
│  │              │    └──────────────┘    │                   │  │
│  │ REST + MCP   │                       │ Cognee Kuzu       │  │
│  │ endpoints    │                       │ (single conn)     │  │
│  └──────┬───────┘                       └────────┬──────────┘  │
│         │                                        │             │
│         │    ┌──────────────────────┐            │             │
│         └────►    Redis (:6379)     ◄────────────┘             │
│              │  Job Queue + Results │                          │
│              └──────────────────────┘                          │
└────────────────────────────────────────────────────────────────┘
         ↕ HTTP (DEVBRAIN_API_URL)
┌─────────────────────────────────────────────────────────────────┐
│                    Each User's Machine                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ MCP Server (python -m backend.mcp_server)                │   │
│  │  - stdio transport for Claude Code / Cursor / OpenCode   │   │
│  │  - No GitHub token, no Cognee config, no LLM keys needed │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Two-Interface Design

The backend exposes **two interfaces** over the same service layer:

| Interface | Port | Purpose | User |
|-----------|------|---------|------|
| **FastAPI REST** (`backend/main.py`) | 8000 | Webhook receiver, tenant DevBrain API | Maintainer |
| **MCP Server** (`backend/mcp_server.py`) | stdio | Agent tools for Claude Code / Cursor | Every team member |

### Job Queue Architecture

- **API process** never touches the graph DB directly
- **ARQ worker** holds the single Kuzu connection and runs ingestion + queries concurrently as asyncio tasks
- **Redis** serves as the job queue broker and result store
- Optionally, a lightweight **in-process job tracker** (`backend/jobs.py`) replaces ARQ to avoid file-lock conflicts (FIFO, 500 job limit)

### Two-Layer Design: Platform + Tenant Instances

The **Platform service** (port 9000) handles:
- GitHub OAuth login (users authenticate with their GitHub account)
- Per-user instance provisioning (Docker containers spun up on demand)
- JWT-based session management

Each **tenant instance** is a full DevBrain API (port 8000) provisioned via Docker with its own Redis + worker.

---

## 3. Directory Structure

```
devbrain/
├── .env.example                  # Environment config template
├── .gitignore                    # Git ignore rules
├── .mcp.json                     # Local MCP server config (Claude Code)
├── AGENTS.md                     # AI agent context (source of truth for agent behavior)
├── CLAUDE.md                     # Claude-specific agent instructions
├── Dockerfile                    # Backend container image
├── README.md                     # Project README
├── docker-compose.yml            # Multi-service orchestration
├── opencode.example.jsonc        # OpenCode MCP config example
├── opencode.jsonc                # OpenCode local config (gitignored)
├── plan_h.txt                    # Implementation plans / notes
├── requirements.txt              # Python dependencies
├── test_local.py                 # Quick ingestion test script
│
├── backend/                      # Python backend
│   ├── main.py                   # FastAPI app + webhook handler (port 8000)
│   ├── mcp_server.py             # MCP server (stdio transport)
│   ├── config.py                 # Central configuration (settings, PyGithub client)
│   ├── service.py                # Application service layer (orchestration)
│   ├── registry.py               # Persistent ingested-repo registry (JSON file)
│   ├── worker.py                 # ARQ worker (background ingestion)
│   ├── jobs.py                   # In-process job tracker (alternative to ARQ)
│   ├── issues_service.py         # GitHub issue CRUD (per-user token support)
│   ├── pr_service.py             # GitHub PR CRUD
│   ├── commit_service.py         # GitHub commit inspection + context
│   ├── history_service.py        # Commit history, blame, file/author/branch history
│   ├── search_service.py         # GitHub commit search (Search API)
│   ├── git_service.py            # Local git operations (subprocess)
│   │
│   ├── ingestion/                # GitHub data ingestion modules
│   │   ├── __init__.py           # Module exports
│   │   ├── github_client.py      # PyGithub fetch helpers (returns plain dicts)
│   │   ├── commits.py            # Commit ingestion
│   │   ├── pull_requests.py      # PR ingestion + review comments
│   │   ├── issues.py             # Issue ingestion
│   │   ├── releases.py           # Release / tag / deployment ingestion
│   │   ├── codebase.py           # File tree structure ingestion
│   │   ├── codegraph.py          # Deep AST ingestion via cognee[codegraph]
│   │   └── adrs.py               # ADR ingestion
│   │
│   ├── memory/                   # Cognee memory interface
│   │   ├── __init__.py           # (empty)
│   │   ├── client.py             # Cognee SDK mapping (remember/recall/improve/forget)
│   │   ├── query.py              # Natural-language query routing
│   │   ├── improve.py            # Weekly memory refresh consolidation
│   │   └── forget.py             # Surgical memory pruning
│   │
│   ├── changelog/                # Changelog & update-tracking subsystem
│   │   ├── __init__.py           # Subsystem overview
│   │   ├── global_changelog.py   # Global changelog generator (all events)
│   │   ├── user_updates.py       # Per-user update digest generator
│   │   ├── profile.py            # User profile store (Redis + Cognee)
│   │   ├── tracker.py            # Persistent state tracker (Redis)
│   │   └── notifier.py           # Notification dispatcher (webhook + log)
│   │
│   └── platform/                 # Platform service (auth + provisioning)
│       ├── __init__.py           # (empty)
│       ├── app.py                # FastAPI app (port 9000)
│       ├── router.py             # Auth + instance management endpoints
│       ├── auth.py               # GitHub OAuth + JWT helpers
│       ├── models.py             # SQLModel: User, Instance
│       ├── db.py                 # SQLite database engine
│       ├── crypto.py             # Fernet encryption for tenant secrets
│       └── provisioner.py        # Docker-based per-tenant instance provisioning
│
├── frontend/                     # React + TypeScript frontend (port 3000)
│   ├── index.html                # HTML entry point
│   ├── package.json              # Node dependencies
│   ├── tsconfig.json             # TypeScript config
│   ├── vite.config.ts            # Vite build config
│   ├── source.config.ts          # Fumadocs MDX config
│   ├── .env.example              # Frontend env vars
│   ├── metadata.json             # Site metadata
│   ├── lib/
│   │   ├── source.ts             # Fumadocs source loader
│   │   └── path-polyfill.ts      # Node path polyfill
│   ├── public/                   # Static assets
│   ├── content/docs/             # MDX documentation files
│   ├── src/
│   │   ├── main.tsx              # React entry point
│   │   ├── App.tsx               # Router configuration
│   │   ├── index.css             # Tailwind + custom theme
│   │   ├── context/
│   │   │   └── AuthContext.tsx    # Authentication context + token management
│   │   └── components/
│   │       ├── LandingPage.tsx   # Landing page (Hero + About + Features + UseCases + Benefits + Footer)
│   │       ├── Hero.tsx          # Animated hero section with Gemini effect
│   │       ├── HeroDiagram.tsx   # Scroll-triggered diagram
│   │       ├── About.tsx         # "One graph. Every decision." section
│   │       ├── Features.tsx      # Tabbed feature showcase (Commits, PRs, ADRs, AST)
│   │       ├── UseCases.tsx      # Use case tabs (Onboarding, Code Review, AI Agents)
│   │       ├── Benefits.tsx      # Sticky-card benefits stack
│   │       ├── RadialDiagram.tsx # SVG radial knowledge graph diagram
│   │       ├── GraphVisualize.tsx # Interactive D3 force-directed graph
│   │       ├── DocsPage.tsx      # Fumadocs documentation viewer
│   │       ├── LoginPage.tsx     # GitHub OAuth login page
│   │       ├── Dashboard.tsx     # User dashboard (instance management)
│   │       ├── NewInstance.tsx   # Multi-step instance creation wizard
│   │       ├── InstanceCard.tsx  # Instance status card component
│   │       ├── ConfigSheet.tsx   # MCP configuration panel
│   │       ├── ProtectedRoute.tsx # Auth guard component
│   │       ├── Navbar.tsx        # Responsive navigation bar
│   │       ├── Footer.tsx        # Animated SVG footer
│   │       └── ui/               # UI primitives (Logo, gemini-effect, etc.)
```

---

## 4. Backend — FastAPI REST API

**File:** `backend/main.py`
**Port:** 8000
**Framework:** FastAPI 0.1.0

### Purpose
The primary REST API and GitHub webhook receiver. Routes every request through the shared service layer (`backend/service.py`).

### Webhook Endpoints

| Route | Event | Handler |
|-------|-------|---------|
| `POST /webhook` | Push | `_handle_push()` — ingests pushed commits |
| `POST /webhook` | Pull requests | `_handle_pr()` — ingests PR + triggers review comment sync |
| `POST /webhook` | Issues | `_handle_issue()` — ingests closed issues |
| `POST /webhook` | Pull request review | `_handle_pr_review()` — ingests review comments |
| `POST /webhook` | Release | `_handle_release()` — ingests published releases |

Webhooks verify the `X-Hub-Signature-256` HMAC against `GITHUB_WEBHOOK_SECRET`.

### REST API Endpoints

#### Query & Recall
| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/query` | Ask a natural-language question (supports `?repo=`, `?mode=hybrid\|why\|chunks`) |
| `GET` | `/recall` | Raw memory recall with optional dataset filter |
| `GET` | `/graph` | Export full knowledge graph (JSON with nodes + edges) |
| `GET` | `/health` | Health check |

#### Ingestion
| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/sync` | Trigger full repo sync (body: `{repo, sync_history_days}`) |
| `POST` | `/ingest/commit` | Ingest single commit (body: `{repo, sha}`) |
| `POST` | `/ingest/pr` | Ingest single PR (body: `{repo, number}`) |
| `POST` | `/ingest/issue` | Ingest single issue (body: `{repo, number}`) |

#### Registry
| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/repos` | List all ingested repos |
| `POST` | `/repos/add` | Register a repo (body: `{repo}`) |
| `DELETE` | `/repos/remove` | Remove a repo (body: `{repo}`) |

#### GitHub Read / Write Operations
| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/commits/{sha}/diff` | Get commit diff |
| `GET` | `/commits/{sha}/context` | Get commit context (PRs, issues, releases, deployments) |
| `GET` | `/history/commits` | List commits (supports pagination, sha, branch, path, author filters) |
| `GET` | `/history/file` | File change history |
| `GET` | `/history/author` | Author contribution history |
| `GET` | `/history/branches` | Branch list |
| `GET` | `/history/commit-graph` | Commit graph (branch topology) |
| `GET` | `/history/blame` | Line-level blame for a file |
| `GET` | `/search/commits` | Search commits by query |
| `GET` | `/prs/{number}` | Get PR details |
| `POST` | `/prs` | Create a pull request |
| `POST` | `/prs/{number}/merge` | Merge a pull request |
| `POST` | `/prs/{number}/comment` | Add PR review comment |
| `GET` | `/issues/{number}` | Get issue details |
| `POST` | `/issues` | Create an issue |
| `PATCH` | `/issues/{number}` | Update an issue |
| `POST` | `/issues/{number}/comments` | Add issue comment |
| `POST` | `/issues/{number}/label` | Add label |
| `DELETE` | `/issues/{number}/label` | Remove label |
| `POST` | `/issues/{number}/assign` | Add assignees |
| `DELETE` | `/issues/{number}/assign` | Remove assignees |
| `POST` | `/issues/{number}/close` | Close an issue |
| `POST` | `/issues/{number}/reopen` | Reopen an issue |

#### Changelog
| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/changelog/generate/global` | Generate global changelog |
| `POST` | `/changelog/generate/user` | Generate user update digest |
| `POST` | `/changelog/subscribe` | Register webhook URL for notifications |
| `POST` | `/changelog/subscribe/user` | Subscribe a user to updates |
| `DELETE` | `/changelog/subscribe/user` | Unsubscribe a user |
| `GET` | `/changelog/subscribers` | List subscribed users |

#### Memory Management
| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/memory/refresh` | Trigger weekly memory refresh for all repos |
| `POST` | `/memory/forget` | Deprecate a module |
| `POST` | `/memory/forget/repo` | Forget a repo entirely |

#### Jobs
| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/jobs` | List recent jobs |
| `GET` | `/jobs/{job_id}` | Get job status |

#### Local Git Operations
| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/git/status` | Git status |
| `POST` | `/git/log` | Git log |
| `POST` | `/git/diff` | Git diff |
| `POST` | `/git/show` | Show commit |
| `POST` | `/git/branch` | List branches |
| `POST` | `/git/diff-branch` | Diff branches |
| `POST` | `/git/commit` | Create commit |
| `POST` | `/git/stage` | Stage files |
| `POST` | `/git/push` | Push to remote |
| `POST` | `/git/pull` | Pull from remote |
| `POST` | `/git/rebase` | Rebase (with warnings) |
| `POST` | `/git/reset` | Reset (with warnings) |
| `POST` | `/git/smart-push` | Stage → commit → push (atomic) |
| `GET` | `/git/read-file` | Read file from git |

---

## 5. Backend — MCP Server

**File:** `backend/mcp_server.py`
**Transport:** stdio (via `python -m backend.mcp_server`)
**Protocol:** MCP (Model Context Protocol) via `mcp` package

### Purpose
A thin HTTP client that proxies every tool call to the DevBrain REST API at `DEVBRAIN_API_URL`. Users need only that URL — no GitHub tokens, no Cognee config, no LLM keys for read/query tools.

### MCP Tools Exposed

#### Query & Memory
| Tool | Description |
|------|-------------|
| `ask_devbrain` | Ask a natural-language question |
| `recall` | Raw memory recall with dataset filter |
| `list_repos` | List all ingested repos |
| `list_ingested_datasets` | List datasets for a repo |
| `get_graph` | Export full knowledge graph |
| `refresh_memory` | Trigger weekly memory refresh |
| `forget_module` | Deprecate a module from memory |

#### Ingestion
| Tool | Description |
|------|-------------|
| `sync_repo` | Full repo sync (commits, PRs, issues, ADRs, code structure, AST) |
| `ingest_commit` | Ingest a single commit |
| `ingest_pr` | Ingest a single PR |
| `ingest_issues` | Ingest issues for a repo |

#### Commit Inspection & Context
| Tool | Description |
|------|-------------|
| `get_commit_diff` | Get unified diff for a commit |
| `get_commit_context` | Cross-reference a SHA to associated PRs, issues, releases, workflow runs, deployments |
| `get_commit_history` | List commits with pagination and filtering |
| `get_file_history` | File revision history |
| `get_author_history` | Author contribution history |
| `get_branches` | List branches |
| `get_commit_graph` | Branch topology / commit graph |
| `get_blame` | Line-level blame for a file |
| `search_commits` | Full-text commit search via GitHub Search API |

#### GitHub Issue CRUD (per-user token)
| Tool | Description |
|------|-------------|
| `get_issue` | Get issue details |
| `create_issue` | Create an issue (attributed to caller via `GITHUB_USER_TOKEN`) |
| `update_issue` | Update issue title/body |
| `add_issue_comment` | Add issue comment |
| `add_issue_label` | Add label to issue |
| `remove_issue_label` | Remove label from issue |
| `add_issue_assignees` | Add assignees to issue |
| `remove_issue_assignees` | Remove assignees from issue |
| `close_issue` | Close an issue |
| `reopen_issue` | Reopen an issue |

#### GitHub PR Operations
| Tool | Description |
|------|-------------|
| `get_pr` | Get PR details |
| `create_pr` | Create a pull request |
| `merge_pr` | Merge a pull request |
| `add_pr_review_comment` | Add PR review comment |

#### Changelog
| Tool | Description |
|------|-------------|
| `generate_global_changelog` | Generate global changelog |
| `generate_user_updates` | Generate user-specific update digest |
| `subscribe_to_updates` | Subscribe to notifications |
| `subscribe_user` | Subscribe a user to updates |
| `unsubscribe_user` | Unsubscribe a user |
| `list_subscribers` | List subscribed users |

#### Local Git Operations
| Tool | Description |
|------|-------------|
| `git_status` | Git working tree status |
| `git_log` | Git log |
| `git_diff` | Git diff (unstaged, staged, between refs) |
| `git_show` | Show commit details |
| `git_branch_list` | List local (and optionally remote) branches |
| `git_diff_branches` | Diff two branches |
| `git_commit` | Stage + commit |
| `git_stage` | Stage specific files |
| `git_push` | Push to remote |
| `git_pull` | Pull from remote |
| `git_rebase` | Rebase (surfaces clear warnings) |
| `git_reset` | Reset (surfaces clear warnings) |
| `git_smart_push` | **Flagship tool** — stage → commit → push in one atomic call |
| `git_read_file` | Read file content from a specific ref |

### User Token Model (Attributed Write Actions)

Tools that create attributed GitHub content (opening issues, commenting, labeling, etc.) run as the **user's** GitHub account via `GITHUB_USER_TOKEN`, not the server's central bot token. The token is forwarded per-call as the `X-GitHub-User-Token` header and is never stored server-side.

---

## 6. Ingestion Layer

### `backend/ingestion/github_client.py` — Data Source

Pure fetch helpers that return **plain dicts** (no PyGithub objects leak out). Functions:

| Function | Description |
|----------|-------------|
| `fetch_commits(owner, repo, since_days)` | List commits with optional time window |
| `fetch_commit(owner, repo, sha)` | Single commit details |
| `fetch_prs(owner, repo, since_days)` | List PRs with reviews, review comments, discussion comments |
| `fetch_pr(owner, repo, number)` | Single PR with full details |
| `fetch_issues(owner, repo, since_days)` | List issues with comments |
| `fetch_issue(owner, repo, number)` | Single issue with comments |
| `fetch_releases(owner, repo)` | List releases with assets |
| `fetch_tags(owner, repo)` | List tags |
| `fetch_deployments(owner, repo)` | List deployments with statuses |
| `fetch_adrs(owner, repo)` | Scan conventional ADR directories |
| `fetch_repo_tree(owner, repo)` | Get file tree of default branch |
| `download_repo_archive(owner, repo, dest)` | Download ZIP archive for codegraph |

**ADR directories scanned:** `docs/decisions`, `adr`, `docs/adr`, `.decisions`

### `backend/ingestion/commits.py` — Commit Ingestion

Structures commit data into a memory payload:
- SHA (truncated), author, date, message
- Changed files (filename, status, +/- counts)

**Functions:** `ingest_commit()`, `ingest_commits()` (returns count)

### `backend/ingestion/pull_requests.py` — PR Ingestion

Structures full PR context:
- Title, author, merged date, approvals
- Files changed, reviews (state, author, body)
- Review comments (line-by-line feedback)
- Discussion comments (general conversation)

**Functions:** `ingest_pr()`, `ingest_review_comment()`, `ingest_prs()` (returns count)

### `backend/ingestion/issues.py` — Issue Ingestion

Structures issue context:
- Title, author, state, labels, timestamps
- Full discussion comments

**Functions:** `ingest_issue()`, `ingest_issues()` (returns count)

### `backend/ingestion/releases.py` — Release / Tag / Deployment Ingestion

Three ingestion targets:
- **Releases:** tag, name, author, published_at, prerelease, notes, assets
- **Tags:** name, SHA, author, date, commit message
- **Deployments:** ref, SHA, environment, creator, status (state, description)

**Functions:** `ingest_release()`, `ingest_releases()`, `ingest_tag()`, `ingest_tags()`, `ingest_deployment()`, `ingest_deployments()`

### `backend/ingestion/codebase.py` — Code Structure Ingestion

Ingests the repository's file tree as a text summary:
- Scans for code extensions (`{'.py', '.js', '.jsx', '.ts', '.tsx', '.go', '.rs', '.java', '.cs', '.php', '.rb'}`)
- Groups files by directory into module descriptions
- Returns count of code directories found

### `backend/ingestion/codegraph.py` — Deep AST Ingestion

Downloads the repo archive and feeds every supported source file into Cognee's built-in pipeline (add → cognify → improve). Cognee's default loaders handle code files and extract functions, classes, imports, and their relationships into the knowledge graph.

**Supported extensions:** `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.go`, `.rs`, `.java`, `.cs`, `.php`, `.rb`

### `backend/ingestion/adrs.py` — ADR Ingestion

Scans conventional ADR directories and remembers each Architecture Decision Record as a text document linked to the repo.

---

## 7. Memory / Query Layer

### `backend/memory/client.py` — Cognee Interface

The single chokepoint between DevBrain and the Cognee SDK. Maps AGENTS.md vocabulary to Cognee API:

| DevBrain Term | Cognee SDK Call | Description |
|--------------|----------------|-------------|
| `remember()` | `cognee.add()` → `cognee.cognify()` → `cognee.improve()` | Store data into memory |
| `recall()` | `cognee.recall()` / `cognee.search()` | Retrieve from memory |
| `improve()` | `cognee.memify()` | Strengthen existing memory |
| `forget()` | `cognee.forget()` | Remove from memory |

**Connection modes:**
- **Cloud:** `cognee.serve(url=..., api_key=...)`
- **Local:** Kuzu (graph) + LanceDB (vector) + SQLite (metadata) — all file-based

**Gemini key rotation:** On a 429 rate-limit error, rotates to the next configured key (supports `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`). Resets rotation on success.

### `backend/memory/query.py` — Natural Language Query Routing

**Function:** `ask_devbrain(question, repo=None, mode='hybrid')`

**Search modes:**

| Mode | SearchType | Use Case |
|------|-----------|----------|
| `hybrid` | Auto-routing via `recall()` | Default, good for most queries |
| `why` | `GRAPH_COMPLETION` | Best for "why was X changed?" questions |
| `chunks` | `CHUNKS` | Raw PR/commit text retrieval |

**Lock retry:** Retries up to 5 times with exponential backoff if the Kuzu graph DB is locked by concurrent ingestion.

### `backend/memory/improve.py` — Self-Improving Memory

- Runs `cognee.memify()` across all datasets (`commits`, `prs`, `adrs`, `ast`, `issues`) for every ingested repo
- Weekly cron via APScheduler (`AsyncIOScheduler`)
- One dataset failure doesn't abort the rest

### `backend/memory/forget.py` — Surgical Memory Pruning

- **Function:** `deprecate_module(owner, repo, module)`
- Guards against accidental full-dataset wipe: requires explicit, non-empty module name
- MVP: forgets the entire repo AST dataset (per-module pruning requires `node_set` tagging)

---

## 8. GitHub Service Layer

### `backend/config.py` — Central Configuration

**Class:** `Settings` — sourced from environment variables

Key settings:
- **Cognee:** base URL, API key, Gemini keys (primary + 2 fallbacks), LLM/embedding provider/model, data directories
- **GitHub:** token, optional default repo, webhook secret
- **DevBrain:** registry path, Redis URL, local repo path
- **Cognee mode:** auto-detected — `cloud` if `COGNEE_API_KEY` is set, `local` otherwise

**Key helpers:**
- `settings.COGNEE_MODE` — auto-detected: `"cloud"` if `COGNEE_API_KEY` is set, `"local"` otherwise
- `github_client()` — cached PyGithub client (singleton)
- `dataset_name(owner, repo, kind)` — canonical dataset name: `repo_{owner}_{repo}_{kind}`
- `split_repo(repo_str)` — split `"owner/repo"` into `(owner, repo)`

### `backend/issues_service.py` — GitHub Issue CRUD

Full read/write operations on GitHub issues:
- `create_issue()` — with title, body, labels, assignees, milestone
- `get_issue()` — full details with comments
- `update_issue()` — title, body, state
- `add_issue_comment()` / `get_issue_comments()`
- `add_issue_label()` / `remove_issue_label()`
- `add_issue_assignees()` / `remove_issue_assignees()`
- `close_issue()` / `reopen_issue()`

**Per-user token support:** When `token` is supplied (from MCP `GITHUB_USER_TOKEN`), builds a one-off PyGithub client so actions are performed as that user, not the server's bot account.

### `backend/pr_service.py` — GitHub PR Operations

- `create_pull_request()` — with title, head, base, body, draft, maintainer_modify
- `get_pull_request()` — serialized with review metadata
- `merge_pull_request()` — with merge method, commit title/message
- `add_pull_request_review_comment()` — with commit_id, path, position, body

### `backend/commit_service.py` — Commit Inspection & Context

**Commit Inspection:**
- `get_commit_diff(sha)` — unified diff per file
- `get_commit_context(sha)` — cross-references to:
  - Associated PRs (via commit SHA search)
  - Associated issues (extracted from commit message)
  - Associated releases (via tag SHA matching)
  - Workflow runs (GitHub Actions)
  - Deployments

### `backend/history_service.py` — Commit/File/Author/Branch History

- `get_commit_history(repo, **filters)` — paginated, filters: sha, branch, path, author, since, until
- `get_file_history(repo, path)` — file revision history with diffs
- `get_author_history(repo, author, **filters)` — author contributions with stats
- `get_branches(repo)` — branch list with commit info
- `get_commit_graph(repo, branch)` — branch topology with merge commits
- `get_blame(repo, path, ref)` — line-level blame

### `backend/search_service.py` — Commit Search

- `search_commits(query, repo, **params)` — full-text commit search via GitHub Search API
- `search_commits_advanced(query, repo, author, date_range, sort)` — with additional filters
- Uses preview header: `application/vnd.github.cloak-preview`

### `backend/git_service.py` — Local Git Operations

All functions execute real git subprocess commands in a configurable local repository path:
- `git_status()`, `git_log()`, `git_diff()`, `git_show()`
- `git_branch_list()`, `git_diff_branches()`
- `git_commit()`, `git_stage()`
- `git_push()`, `git_pull()`
- `git_rebase()` (with warnings), `git_reset()` (with warnings)
- `git_smart_push()` — **flagship orchestrator:** stages → commits → pushes in a single atomic call with structured step-by-step output
- `git_read_file()` — read file content from a specific ref

---

## 9. Changelog & Notification Subsystem

### Two-Layer Design

1. **Global Changelog** — every event in a repo between generations
2. **User Updates** — personalized digest per GitHub username

### `backend/changelog/global_changelog.py`

**Generated file:** `.devbrain/changelogs/GLOBAL_CHANGELOG_{safe_repo}.md`

Data models: `CommitEntry`, `PREntry`, `IssueEntry`, `ReleaseEntry`

**Core function:** `generate_global_changelog(owner, repo)`
- Fetches commits, PRs, issues, releases since last sync
- Returns `GlobalChangelog` dataclass + file path
- Updates `last_global_sync` timestamp

### `backend/changelog/user_updates.py`

**Generated file:** `.devbrain/changelogs/USER_UPDATES_{username}_{safe_repo}.md`

**What surfaces:**
1. **Their commits** — authored by the user in the window
2. **Their PRs** — opened + reviewed (from profile)
3. **Their issues** — created or assigned
4. **@Mentions** — every place someone tagged `@username` with context
5. **Files you own that changed** — modified by someone else

**Zero live GitHub API calls** for user-specific parts — all data from persisted profile.

### `backend/changelog/profile.py` — User Profile Store

**Dual storage:**
1. **Redis** (fast, exact): SETs for owned files, reviewed PRs; ZSETs for mentions and file touches
2. **Cognee Cloud** (background, non-blocking): rich text document for NL querying

**Redis key schema:**
```
devbrain:pr:users:{safe_repo}                         SET    known usernames
devbrain:pr:files:{safe_repo}:{user}                  SET    owned file paths
devbrain:pr:prs:{safe_repo}:{user}                    SET    reviewed PR numbers
devbrain:pr:mentions:{safe_repo}:{user}               ZSET   member="{type}:{id}"
devbrain:pr:mdata:{safe_repo}:{user}:{type}:{id}      STRING JSON of mention
devbrain:pr:touches:{safe_repo}:{user}                ZSET   member="{safe_path}::{sha7}"
devbrain:pr:tdata:{safe_repo}:{user}:{safe_path}::{sha7} STRING JSON of touch event
```

Profile is updated from GitHub webhook events (push, PR, issue, review) incrementally.

### `backend/changelog/tracker.py` — Persistent State Tracker

Redis-backed timestamps for changelog sync state:
```
devbrain:cl:sync:global:{safe_repo}       STRING  ISO-8601 timestamp
devbrain:cl:sync:user:{safe_repo}:{user}  STRING  ISO-8601 timestamp
devbrain:cl:webhook:{safe_repo}:{user}    STRING  webhook URL
devbrain:cl:subs:{safe_repo}              SET     subscribed usernames
```

### `backend/changelog/notifier.py` — Notification Dispatcher

**Channels:**
1. **Webhook** — POST JSON summary to user-registered URL
2. **Log** — Always logs at INFO level

Future channels (email, Slack, Discord) can be added via `_notify_*` pattern.

---

## 10. Platform Service (Auth + Multi-Tenant)

**File:** `backend/platform/app.py`
**Port:** 9000
**Framework:** FastAPI

### Purpose
Separate service (from the tenant DevBrain API on port 8000) that handles:
- GitHub OAuth login
- JWT-based session management
- Per-user instance provisioning (Docker containers)

### `backend/platform/auth.py` — GitHub OAuth + JWT

- `github_authorization_url(state)` — builds GitHub OAuth URL
- `exchange_code_for_token(code)` — exchanges code for access token
- `fetch_user_github_info(token)` — fetches user profile from GitHub API
- `create_access_token(user_id, github_login, avatar_url)` — issues HS256 JWT (24h expiry)
- `verify_access_token(token)` — validates JWT

### `backend/platform/models.py` — Database Models

```python
class User(SQLModel, table=True):
    id: int | None
    github_id: int (unique, indexed)
    github_login: str
    github_name: str | None
    avatar_url: str
    email: str | None
    created_at: datetime
    instances: list[Instance]

class Instance(SQLModel, table=True):
    id: str (UUID primary key)
    user_id: int (FK → user.id)
    repo: str ("owner/repo")
    port: int
    status: str ("pending" | "running" | "stopped" | "error")
    secrets_enc: str (Fernet-encrypted JSON)
    created_at: datetime
    container_api_name: str
    container_worker_name: str
    container_redis_name: str
```

### `backend/platform/router.py` — Auth & Instance Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/auth/github/login` | Redirect to GitHub OAuth |
| `GET` | `/auth/callback` | OAuth callback → JWT → redirect to frontend |
| `GET` | `/auth/me` | Get current user (requires token cookie) |
| `POST` | `/auth/logout` | Clear auth cookie |
| `GET` | `/instances` | List user's instances |
| `POST` | `/instances` | Provision new instance |
| `GET` | `/instances/{id}` | Get instance details |
| `POST` | `/instances/{id}/stop` | Stop an instance |
| `POST` | `/instances/{id}/start` | Start an instance |
| `DELETE` | `/instances/{id}` | Delete an instance |

### `backend/platform/provisioner.py` — Docker Provisioner

Provisions **three Docker containers** per tenant:
- `redis-{id}` — Redis job queue
- `devbrain-{id}-api` — FastAPI server (exposed on assigned port)
- `devbrain-{id}-worker` — ARQ worker

**Port range:** 8100–8199

**Details:**
- Creates shared Docker network `devbrain-platform`
- Encrypts tenant secrets (GitHub token, Cognee key, etc.) via Fernet before storing
- Sets up volume mounts for persistence

---

## 11. Frontend — React + TypeScript

**Stack:** React 19, TypeScript, Vite, Tailwind CSS v4, Fumadocs MDX, D3.js, Framer Motion, Lucide Icons

**Port:** 3000 (dev: `npm run dev`, build: `vite build`)

### Pages / Routes

| Path | Component | Auth Required | Description |
|------|-----------|---------------|-------------|
| `/` | `LandingPage` | No | Marketing landing page |
| `/visualize` | `GraphVisualize` | No | Interactive D3 knowledge graph |
| `/docs/*` | `DocsPage` | No | Fumadocs documentation |
| `/login` | `LoginPage` | No | GitHub OAuth login |
| `/dashboard` | `Dashboard` | Yes | Instance management dashboard |
| `/new-instance` | `NewInstance` | Yes | Multi-step instance creation wizard |

### Design System

**Color palette (custom Tailwind theme):**
- Background: `#FEFEF3` (warm cream)
- Background secondary: `#F3F3E8`
- Card background: `#F3F2DE`
- Text primary: `#040200` (near-black)
- Text muted: `#6B6A5E`
- Button dark: `#232120`
- Accent colors: mint, yellow, peach, orchid, blush, sage, powder

**Fonts:** Plus Jakarta Sans (display), JetBrains Mono (mono/code)

**Dark mode supported** — theme toggled via Navbar with localStorage persistence and system preference detection.

### Key Components

#### `LandingPage.tsx`
Composes the full marketing page: `Navbar` + `Hero` + `About` + `Features` + `UseCases` + `Benefits` + `Footer`

#### `Hero.tsx`
- Scroll-triggered Google Gemini effect animation
- "Your Codebase Has a Memory" headline
- "Ask questions. Get answers. No more 'I don't know, let me ask someone.'" subtitle
- Powered by Cognee badge
- CTA buttons: Explore Features → `/docs`, Visualize Graph → `/visualize`, Start → `/new-instance`

#### `Features.tsx`
Tabbed interface with 4 tabs:
- **Commits:** Every git push analyzed — message, diff, author, timestamp
- **Pull Requests:** Review comments and merge lineage
- **ADRs:** Auto-discover and link architecture decisions
- **Code AST:** Traverse live call graphs

Each tab has animated SVG illustrations with CSS animations.

#### `UseCases.tsx`
Three use-case tabs:
- **Onboarding:** New engineer ramp-up, codebase orientation, silent knowledge transfer
- **Code Review:** Prior art check, impact analysis, dependency-aware reviews
- **AI Agents:** Context-aware coding, automated PRs, agent debugging

#### `Benefits.tsx`
Sticky-card scroll stack with 5 benefits:
1. Self-Improving Memory (weekly background consolidation)
2. Automated GitHub Sync (real-time webhooks)
3. AST & Dependency Parsing (cognee[codegraph])
4. Hybrid Memory Engine (vector + graph databases)
5. Surgical Memory Pruning (forget API)

#### `GraphVisualize.tsx`
Full D3.js force-directed graph visualization:
- Node types with distinct colors (Commit→yellow, PullRequest→peach, Developer→mint, etc.)
- Interactive: drag, pan, zoom, hover for details
- Search nodes, filter by type
- Expand/collapse neighborhoods
- Details panel on selection
- Legend with togglable node types
- Auto-refresh with last-updated timestamp

#### `DocsPage.tsx`
Fumadocs-powered documentation with:
- MDX content from `content/docs/`
- Sidebar navigation with auto-generated page tree
- GitHub link
- Fallback 404 page

#### `Dashboard.tsx`
User dashboard showing:
- List of provisioned instances with status badges
- Skeleton loading state
- Empty state with CTA to create first instance
- Instance creation flow: New Instance → Config Sheet
- Responsive grid layout

#### `NewInstance.tsx`
Multi-step wizard:
1. **Repository** — input `owner/repo` with validation
2. **Secrets** — GitHub token, Cognee API key, Gemini key, LLM provider toggle
3. **Verify** — review mask-secret values
4. **Create** — spinning creation, success screen with connection commands
5. **Connect** — MCP setup instructions for Claude Code, Codex, OpenCode

#### `ConfigSheet.tsx`
Connection configuration panel:
- Agent tabs: Claude Code, Codex, OpenCode
- Python vs Docker setup methods
- Copyable command snippets with visual feedback
- Step-by-step instructions per agent

#### `LoginPage.tsx`
GitHub OAuth login with:
- Progress indicator steps
- Feature pills (Git History, PR Decisions, AST Graph)
- Animated gradient orbs
- Error handling with specific error messages
- Redirect to dashboard on success

#### `AuthContext.tsx`
React context managing:
- Token storage (localStorage + URL query parameter)
- JWT decode + expiry validation
- Login (redirect to GitHub OAuth)
- Logout (clear token + redirect)
- Auto-load on mount (checks URL for `?token=...`)

### Documentation (Fumadocs MDX)

Documentation is written in MDX format and lives in `frontend/content/docs/`. The Fumadocs pipeline:
- `source.config.ts` — defines docs collection pointing to `content/docs/`
- `lib/source.ts` — Fumadocs source loader with `/docs` base URL
- Rendered via `DocsPage.tsx` with `fumadocs-ui` components

---

## 12. Infrastructure & Deployment

### Docker Setup

**`Dockerfile`** — Python 3.12-slim, installs requirements, copies backend, serves via uvicorn:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
RUN mkdir -p .cognee/data .cognee/system .devbrain
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`docker-compose.yml`** — Three services:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `redis` | `redis:7-alpine` | 6379 | Job queue broker |
| `devbrain-api` | Built from Dockerfile | 8000 | FastAPI REST API |
| `devbrain-worker` | Built from Dockerfile | — | ARQ ingestion worker |

**Volumes:**
- `cognee-data` — `/data/cognee`
- `cognee-system` — `/data/cognee-system`
- `devbrain-registry` — `/data/devbrain`

**Scaling:** Worker can be scaled horizontally:
```bash
docker compose up --scale devbrain-worker=3
```

**Health checks:**
- Redis: `redis-cli ping`
- API: `curl http://localhost:8000/health`

### Local Development

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in credentials
uvicorn backend.main:app --reload --port 8000

# Worker (separate terminal)
python -m arq backend.worker.WorkerSettings

# Frontend
cd frontend
npm install
npm run dev  # port 3000

# Platform service (separate terminal)
uvicorn backend.platform.app:platform_app --port 9000
```

### MCP Setup (for AI agents)

**Claude Code:**
```bash
claude mcp add devbrain -s project \
  -e DEVBRAIN_API_URL="http://localhost:8000" \
  -- python -m backend.mcp_server
```

**With Docker:**
```bash
claude mcp add devbrain -s project \
  -e DEVBRAIN_API_URL="http://localhost:8000" \
  -- docker run -i --rm -e DEVBRAIN_API_URL="http://host.docker.internal:8000" devbrain-mcp
```

**With user token (for write operations):**
```bash
claude mcp add devbrain -s project \
  -e DEVBRAIN_API_URL="https://devbrain.example.com" \
  -e GITHUB_USER_TOKEN="github_pat_..." \
  -- python -m backend.mcp_server
```

---

## 13. Configuration & Environment Variables

### `.env` — Full Configuration

#### Cognee Cloud
| Variable | Description | Default |
|----------|-------------|---------|
| `COGNEE_BASE_URL` | Cognee Cloud instance URL | `""` |
| `COGNEE_API_KEY` | Cognee Cloud API key (blank = local mode) | `""` |

#### Local Mode (Gemini)
| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Primary Gemini API key | `""` |
| `GEMINI_API_KEY_2` | Fallback key 1 (rate-limit rotation) | `""` |
| `GEMINI_API_KEY_3` | Fallback key 2 (rate-limit rotation) | `""` |
| `LLM_PROVIDER` | LLM provider (`gemini`) | `"gemini"` |
| `LLM_MODEL` | LLM model | `"gemini/gemini-2.0-flash-exp"` |
| `EMBEDDING_PROVIDER` | Embedding provider (`gemini`) | `"gemini"` |
| `EMBEDDING_MODEL` | Embedding model | `"gemini/gemini-embedding-2"` |
| `EMBEDDING_DIMENSIONS` | Embedding dimensions | `768` |
| `COGNEE_DATA_DIR` | Local data directory | `./.cognee/data` |
| `COGNEE_SYSTEM_DIR` | Local system directory | `./.cognee/system` |
| `ENABLE_BACKEND_ACCESS_CONTROL` | Multi-tenant auth toggle | `false` |
| `COGNEE_SKIP_CONNECTION_TEST` | Skip Cognee connection test | `true` |

#### GitHub
| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | Server GitHub token (multi-repo) | `""` |
| `GITHUB_REPO` | Optional default repo | `""` |
| `GITHUB_WEBHOOK_SECRET` | Webhook HMAC secret | `""` |

#### DevBrain
| Variable | Description | Default |
|----------|-------------|---------|
| `REGISTRY_PATH` | Repo registry JSON path | `./.devbrain/repos.json` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `LOCAL_REPO_PATH` | Local git repo path | `"."` |

#### Platform
| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_OAUTH_CLIENT_ID` | GitHub OAuth App client ID | `""` |
| `GITHUB_OAUTH_CLIENT_SECRET` | GitHub OAuth App client secret | `""` |
| `GITHUB_OAUTH_REDIRECT_URI` | OAuth callback URL | `http://localhost:9000/auth/callback` |
| `PLATFORM_SECRET_KEY` | JWT signing + Fernet encryption key | `""` |
| `PLATFORM_DB_PATH` | Platform SQLite DB path | `./.devbrain/platform.db` |
| `FRONTEND_URL` | Frontend URL (CORS) | `http://localhost:3000` |
| `PLATFORM_DATA_DIR` | Platform data directory | `/data/platform` |
| `PLATFORM_PORT_START` | Tenant port range start | `8100` |
| `PLATFORM_PORT_END` | Tenant port range end | `8199` |
| `DEVBRAIN_IMAGE` | Docker image for tenants | `devbrain-devbrain-api` |

### `.env.example` — Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_PLATFORM_API` | Platform API URL | `http://localhost:9000` |
| `VITE_DEVBRAIN_API` | DevBrain API URL | `http://localhost:8000` |

---

## 14. Testing

### Quick Test Script

**File:** `test_local.py`

Tests ingestion end-to-end without Redis/ARQ:
```bash
python test_local.py topoteretes/cognee 30
python test_local.py microsoft/vscode 7
```

**Flow:**
1. Connect to Cognee
2. Run full sync (commits, PRs, issues, ADRs, code structure)
3. Run a test query
4. Disconnect

### Running the Worker

```bash
# ARQ worker
python -m arq backend.worker.WorkerSettings

# Via Docker
docker compose up devbrain-worker
```

### Health Check

```bash
# API
curl http://localhost:8000/health

# Platform
curl http://localhost:9000/health
```

---

## 15. Key Features Checklist

### Ingestion
- [x] GitHub commits (with diffs, files, metadata)
- [x] GitHub pull requests (with reviews, review comments, discussion comments)
- [x] GitHub issues (with full comment threads)
- [x] GitHub releases (with assets, notes)
- [x] GitHub tags
- [x] GitHub deployments (with statuses)
- [x] Architecture Decision Records (ADRs) — auto-discovery from 4 directory conventions
- [x] Codebase file structure (module/directory layout)
- [x] Deep AST/code graph (via `cognee[codegraph]`)

### Memory & Query
- [x] Hybrid search (vector + graph) via Cognee
- [x] Natural language querying ("why was this changed?")
- [x] Sourced answers with provenance
- [x] Full knowledge graph export (JSON with nodes and edges)
- [x] Multi-repo support
- [x] Dataset-scoped recall

### Memory Management
- [x] Self-improving memory (weekly consolidation via memify)
- [x] Surgical memory pruning (forget a module)
- [x] Full repo removal from memory
- [x] Rate-limit resilience (Gemini key rotation)

### Webhooks
- [x] Push events (incremental commit ingestion)
- [x] Pull request events (open/close/merge)
- [x] Pull request review events (review comments)
- [x] Issue events (issue close/reopen)
- [x] Release events
- [x] HMAC verification (SHA-256)

### GitHub Operations (via API)
- [x] Read commits, PRs, issues, files
- [x] Create issues (with labels, assignees, milestone)
- [x] Update issues
- [x] Add/remove labels
- [x] Add/remove assignees
- [x] Close/reopen issues
- [x] Create pull requests (with draft support)
- [x] Merge pull requests (merge/squash/rebase)
- [x] Add PR review comments
- [x] Per-user token attribution for write actions

### Search & History
- [x] Full-text commit search (GitHub Search API)
- [x] Commit history with filters (sha, branch, path, author, date range)
- [x] File revision history
- [x] Author contribution history
- [x] Branch list
- [x] Commit graph (branch topology)
- [x] Line-level blame

### Local Git Operations
- [x] Status, log, diff, show
- [x] Branch management
- [x] Stage, commit, push, pull
- [x] Rebase and reset (with safety warnings)
- [x] Smart push (stage → commit → push, atomic)

### Changelog & Notifications
- [x] Global changelog generation (commits, PRs, issues, releases)
- [x] Per-user update digests (their commits, PRs, mentions, files)
- [x] @Mention tracking with full context
- [x] File-ownership tracking (files you touched that changed)
- [x] Webhook notifications
- [x] Redis-backed persistent state
- [x] User profile in Redis + Cognee Cloud

### Platform (Multi-Tenant)
- [x] GitHub OAuth login
- [x] JWT session management
- [x] Per-user instance provisioning via Docker
- [x] Three containers per tenant (API, worker, Redis)
- [x] Port range management (8100-8199)
- [x] Encrypted secrets storage (Fernet)
- [x] Instance lifecycle management (create, start, stop, delete)
- [x] Connection configuration instructions per agent

### Frontend
- [x] Marketing landing page with animations
- [x] Interactive D3 knowledge graph visualization
- [x] Fumadocs documentation viewer (MDX)
- [x] GitHub OAuth login page
- [x] Dashboard with instance management
- [x] Multi-step instance creation wizard
- [x] MCP configuration panel (Claude Code, Codex, OpenCode)
- [x] Dark mode support
- [x] Responsive design
- [x] Scroll-triggered animations (Framer Motion)

### MCP Integration
- [x] Claude Code support
- [x] Cursor support
- [x] OpenCode support (via `opencode.jsonc`)
- [x] Codex support
- [x] stdio transport
- [x] Per-user token for attributed writes
- [x] Linux / macOS / Windows paths

### Infrastructure
- [x] Docker containerization
- [x] Docker Compose orchestration
- [x] Horizontal worker scaling
- [x] Health checks
- [x] Volume persistence
- [x] CORS configuration
- [x] Local development setup

---

## 16. FAQ & Troubleshooting

### How does DevBrain compare to GitHub Copilot / Cursor's built-in context?
DevBrain is a **persistent knowledge graph** of your engineering history — it remembers *why* code was written, not just what it looks like. Copilot/Cursor provide inline code completion; DevBrain provides long-term institutional memory.

### Do I need Cognee Cloud?
No. DevBrain runs fully local with Gemini (free tier) — Kuzu (graph DB), LanceDB (vector DB), and SQLite are all file-based. Cognee Cloud is optional for teams that want hosted infrastructure.

### How many repos can I ingest?
Unlimited. DevBrain is fully multi-repo — pass `?repo=owner/name` or `repo` parameter per request.

### What's the cost to run?
- **Local mode:** Only Gemini API costs (~$0 for free tier with 100 embeddings/min — key rotation helps)
- **Cognee Cloud:** Pricing at [cognee.ai](https://cognee.ai) (use code `COGNEE-35` for free dev plan)

### Can I run DevBrain without Docker?
Yes. The ARQ worker can run as a Python process:
```bash
python -m arq backend.worker.WorkerSettings
```

### How do I add a new Webhook on GitHub?
1. Go to your repo → Settings → Webhooks → Add webhook
2. Payload URL: `https://your-server.com/webhook`
3. Content type: `application/json`
4. Secret: Your `GITHUB_WEBHOOK_SECRET`
5. Events: Select individual events (pushes, pull requests, issues, issue comments, releases)

### Troubleshooting: MCP connection refused
- Ensure the DevBrain API is running on port 8000
- Check `DEVBRAIN_API_URL` points to the correct host/port
- For Docker, use `host.docker.internal` instead of `localhost`
- Verify no firewall is blocking the connection

### Troubleshooting: Graph DB locked
The Kuzu database uses file-level locking. If you see "Lock is held" in logs, wait for the current ingestion job to finish. The query layer retries automatically up to 5 times with exponential backoff.

### Troubleshooting: Gemini rate limits
DevBrain automatically rotates through `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3` on 429 errors. Configure multiple keys for the free tier (100 embeds/min per key).
