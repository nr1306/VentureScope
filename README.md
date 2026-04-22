# VentureScope

**Multi-agent AI system for investment due diligence.** Enter a company name — a team of specialized Claude agents researches the market, financials, competitors, and risks, then synthesizes a structured report with guardrails, evals, and full observability.

## AI Engineering Concepts Demonstrated

| Concept | Implementation |
|---|---|
| Multi-agent orchestration | Orchestrator fans out to 4 specialist sub-agents |
| Raw tool use (no LangChain) | Claude API tool_use loop in `agents/base.py` |
| RAG pipeline | pgvector + chunking + OpenAI embeddings |
| Input guardrails | Prompt injection detection, upload validation |
| Output guardrails | Citation enforcer, tone normalizer, confidence flagging |
| LLM-as-judge evals | Second Claude call scores each report section 1-5 |
| Deterministic evals | Competitor recall, citation rate, risk coverage metrics |
| Structured outputs | Typed Pydantic schemas throughout |
| Observability | Langfuse traces — every agent step, tool call, token count |
| Async task queue | Celery + Redis for non-blocking agent runs |

## Architecture

```
POST /api/analyze
       │
       ▼
  Celery Worker
       │
       ▼
  Orchestrator Agent
  ┌────┴──────────────────────────────────┐
  │                                       │
  ▼           ▼           ▼              ▼
Market    Financial   Competitor       Risk
Agent     Agent       Agent            Agent
  │           │           │              │
  ▼           ▼           ▼              ▼
web_search  web_search  web_search    web_search
doc_retriever doc_retriever           doc_retriever
  │
  ▼ (all results)
Synthesizer (Claude) → DueDiligenceReport (Pydantic)
  │
  ▼
Output Guardrails (citation_enforcer, tone_normalizer)
  │
  ▼
Langfuse trace flushed
  │
  ▼
Persisted to Postgres
```

## Stack

- **LLM**: Claude claude-sonnet-4-6 (Anthropic API, raw tool use)
- **Backend**: Python 3.12 + FastAPI + Celery
- **Database**: Postgres + pgvector extension
- **Embeddings**: OpenAI text-embedding-3-small
- **Observability**: Langfuse
- **Web search**: Tavily
- **Document parsing**: unstructured
- **Frontend**: Next.js 15 + Tailwind CSS
- **Infra**: Docker Compose

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, TAVILY_API_KEY, OPENAI_API_KEY
# Optionally: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY for traces

# 2. Start all services
docker compose up --build

# 3. Run database migrations
docker compose exec backend alembic upgrade head

# 4. Open the app
open http://localhost:3000
```

## Running Evals

```bash
# Trigger via API
curl -X POST http://localhost:8000/api/eval/run

# Or run directly (with Python env)
cd backend
python -m evals.eval_runner

# View results
curl http://localhost:8000/api/eval/results | jq
```

## Project Structure

```
venturesscope/
├── backend/
│   ├── main.py                  # FastAPI entrypoint
│   ├── config.py                # All settings via pydantic-settings
│   ├── observability.py         # Langfuse tracer wrapper
│   ├── agents/
│   │   ├── base.py              # Agentic tool-use loop
│   │   ├── orchestrator.py      # Fan-out + synthesis
│   │   ├── market_agent.py
│   │   ├── financial_agent.py
│   │   ├── competitor_agent.py
│   │   └── risk_agent.py
│   ├── guardrails/
│   │   ├── input_guardrails.py  # Injection detection, upload validation
│   │   └── output_guardrails.py # Citation enforcer, tone normalizer
│   ├── rag/
│   │   ├── ingestor.py          # parse → chunk → embed → pgvector
│   │   ├── retriever.py         # cosine similarity search
│   │   ├── chunker.py           # recursive text splitter
│   │   └── embedder.py          # OpenAI embeddings
│   ├── evals/
│   │   ├── golden_dataset/      # 5 company ground-truth JSONs
│   │   ├── eval_runner.py       # Full eval suite
│   │   ├── llm_judge.py         # Claude-as-judge rubric scorer
│   │   └── metrics.py           # Deterministic metrics
│   ├── api/                     # FastAPI routers
│   ├── workers/tasks.py         # Celery tasks
│   └── db/                      # SQLAlchemy models + Alembic
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Home — search + recent reports
│   │   ├── report/[id]/page.tsx # Full report with all panels
│   │   └── upload/page.tsx      # Document upload
│   └── lib/api.ts               # Typed API client
└── docker-compose.yml
```

## Guardrails Explained

**Input guardrails** run before any agent call:
- Prompt injection detector — regex + pattern matching on company name field
- File type and size validation on document uploads

**Output guardrails** run on each sub-agent response:
- **Citation enforcer**: Detects numeric claims (`$X`, `X%`, `Xx`) not followed by a URL within 250 chars. Appends a visible warning to the section.
- **Tone normalizer**: Replaces overconfident language ("definitely will", "guaranteed to") with appropriately hedged alternatives.
- **Confidence flagging**: Sections with confidence < 0.4 are marked `needs_review` and highlighted in the UI.

## Eval Pipeline

Golden dataset: 5 companies (Stripe, Notion, Figma, Linear, Airbnb) with ground-truth JSON files containing known competitors, market sizes, investors, and risk topics.

**Deterministic metrics:**
- `competitor_recall` — fraction of known competitors found
- `citation_rate` — numeric claims with source URLs
- `risk_coverage` — fraction of known risk topics addressed
- `hallucination_proxy` — inverse of guardrail trigger rate

**LLM-as-judge:** Separate Claude call scores each section 1-5 on accuracy, completeness, reasoning, and citation quality. Returns structured JSON.

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `TAVILY_API_KEY` | Tavily web search |
| `OPENAI_API_KEY` | OpenAI embeddings |
| `LANGFUSE_PUBLIC_KEY` | Langfuse observability (optional) |
| `LANGFUSE_SECRET_KEY` | Langfuse observability (optional) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis for Celery |
