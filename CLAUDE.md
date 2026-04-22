# VentureScope

Multi-agent investment due diligence system. Given a company name (and optional uploaded documents), it fans out to four specialist agents, synthesizes results, and produces a structured due-diligence report with an invest / monitor / pass recommendation.

## Architecture

```
frontend (Next.js :3000)
    → POST /api/analyze  → Celery task (Redis broker)
                              → run_orchestrator()  [async]
                                  ├── MarketAgent   [async]
                                  ├── FinancialAgent [async]
                                  ├── CompetitorAgent [async]
                                  └── RiskAgent     [async]
                              → synthesizer (OpenAI gpt-4o-mini)
                              → DueDiligenceReport → PostgreSQL
```

**Backend:** FastAPI + Celery workers, Python 3.14, `.venv` at project root  
**Database:** PostgreSQL 16 + pgvector extension (via Alembic migrations), port **5433** (host)  
**Queue:** Redis 7  
**LLM:** OpenAI `gpt-4o-mini` via `openai` SDK — all agents, synthesis, and evals judge  
**Embeddings:** OpenAI `text-embedding-3-small` (1536 dims)  
**Web search:** Tavily  
**Observability:** Langfuse (optional — skipped gracefully when keys are not set)  
**Document parsing:** `pypdf` (PDF) + `python-docx` (DOCX)

## Development Setup

### Python environment
```bash
# Activate venv (created at project root)
source .venv/bin/activate

# Install backend deps
pip install -r backend/requirements.txt
```

### Required services (local)
```bash
# Start postgres (mapped to host port 5433) + redis
docker-compose up postgres redis -d
```

### Run migrations
```bash
cd backend
alembic upgrade head
```

### Start backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Start Celery worker (separate terminal)
```bash
# Must be run from backend/ so that db/, agents/, etc. are on sys.path
cd backend
celery -A workers.tasks worker --loglevel=info --concurrency=2
```

### Start frontend
```bash
cd frontend
npm install
npm run dev
```

### Full stack via Docker
```bash
docker-compose up --build
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Notes |
|---|---|---|
| `OPENAI_API_KEY` | Yes | All LLM calls (agents, synthesis, embeddings, evals) |
| `TAVILY_API_KEY` | Yes | Web search tool |
| `DATABASE_URL` | No | Default: `postgresql+asyncpg://venturesscope:venturesscope@localhost:5433/venturesscope` |
| `REDIS_URL` | No | Default: `redis://localhost:6379/0` |
| `EMBEDDING_MODEL` | No | Default: `text-embedding-3-small` |
| `LANGFUSE_PUBLIC_KEY` | No | Observability (optional — leave blank to disable) |
| `LANGFUSE_SECRET_KEY` | No | Observability (optional — leave blank to disable) |

## Key Files

| Path | Purpose |
|---|---|
| `backend/agents/base.py` | Async OpenAI function-calling agentic loop |
| `backend/agents/orchestrator.py` | Fan-out to sub-agents + synthesis (async) |
| `backend/agents/{market,financial,competitor,risk}_agent.py` | Specialist agents |
| `backend/rag/embedder.py` | OpenAI embeddings client (AsyncOpenAI) |
| `backend/rag/ingestor.py` | PDF/DOCX/text → chunks → pgvector |
| `backend/rag/retriever.py` | pgvector similarity search |
| `backend/workers/tasks.py` | Celery tasks (`run_due_diligence`) |
| `backend/db/session.py` | SQLAlchemy async engine with NullPool |
| `backend/observability.py` | Langfuse v4 wrapper (no-op when unconfigured) |
| `backend/guardrails/` | Input + output guardrails |
| `backend/evals/` | Eval harness + golden dataset |
| `backend/config.py` | All settings via pydantic-settings |
| `frontend/lib/api.ts` | Frontend API client |

## Dependency Notes

Python 3.14 compatibility constraints (as of April 2026):
- `pydantic>=2.11.0` — pydantic-core 2.27.x uses PyO3 0.22 which caps at Python 3.13
- `sqlalchemy[asyncio]>=2.0.40` — 2.0.36 has a `Union.__getitem__` incompatibility with Python 3.14
- `langfuse>=4.0.0` — v2 uses pydantic v1 which is incompatible with Python 3.14
- `numpy>=1.26.4,<2.0` — upper bound required by some transitive deps
- `httpx>=0.27.0` — relaxed upper bound to avoid conflicts
- `unstructured` removed entirely — replaced with `pypdf` + `python-docx` to avoid PyTorch dependency chain (no Python 3.14 wheels for torch)
- `anthropic` removed — all LLM calls use `openai` SDK only

## Agent Pattern

Each specialist agent extends `BaseAgent` (`backend/agents/base.py`):
- Define `SYSTEM_PROMPT`, `TOOLS` (OpenAI function-calling schemas), `NAME`
- Override `async _dispatch_tool(tool_name, tool_input, context)` to handle tool calls
- The base class runs the async OpenAI tool-use loop until the model stops calling tools
- `run()` is async — always `await` it from the orchestrator

Available tools across agents: `web_search` (Tavily), `document_retriever` (RAG via pgvector).

## Critical Architecture Notes

### Async throughout
The entire agent pipeline is async end-to-end:
- `BaseAgent.run()` → async, uses `AsyncOpenAI`
- `_dispatch_tool()` → async, awaits `rag_retrieve`
- `run_orchestrator()` → async, awaits all agent runs
- Celery task uses `asyncio.run()` to bridge sync→async

### NullPool for Celery compatibility
`db/session.py` uses `NullPool` (no connection caching). This is required because Celery's `asyncio.run()` creates a fresh event loop per task — a pooled asyncpg connection bound to the previous loop would raise `RuntimeError: Future attached to a different loop`.

### OpenAI client creation
`AsyncOpenAI` clients are created **per-call** (not as module-level singletons) for the same reason — `httpx.AsyncClient` internally binds to the event loop at creation time.

### Langfuse keys
The Langfuse client is only initialized when both `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set to non-placeholder values. Leave them blank or as `your_*` to disable tracing entirely.

### sys.path in Celery
`backend/workers/tasks.py` manually prepends `backend/` to `sys.path` at module load. The Celery worker **must** be started from the `backend/` directory (`cd backend && celery -A workers.tasks worker ...`).

## Database Migrations

```bash
cd backend
# Create new migration
alembic revision --autogenerate -m "description"
# Apply
alembic upgrade head
# Rollback one step
alembic downgrade -1
```

Note: All `id` columns are `String(36)` (UUID stored as varchar) — do not use `UUID()` column type in models as it creates a type mismatch with the varchar schema.

## Evals

Golden dataset in `backend/evals/golden_dataset/` (Stripe, Notion, Figma, Linear, Airbnb).

```bash
# Run eval suite
cd backend
python -m evals.eval_runner
# Or via API
POST /api/evals/run
```
