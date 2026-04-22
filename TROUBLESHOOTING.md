# VentureScope — Bug Log & Resolutions

A chronological record of every significant error encountered during setup and development, what caused it, and how it was fixed.

---

## 1. `unstructured==0.16.10` — package not found

**Error:** `pip install` failed — version 0.16.10 does not exist on PyPI.

**Cause:** Incorrect version pinned in `requirements.txt`.

**Fix:** Changed to `unstructured==0.16.19` (nearest available release).

---

## 2. `ollama 0.4.4` conflicts with `httpx==0.28.1`

**Error:** pip dependency conflict — `ollama 0.4.4` requires `httpx<0.28`, but other deps needed `httpx>=0.28`.

**Cause:** ollama Python SDK 0.4.x has a strict upper bound on httpx that conflicts with newer packages.

**Fix:** Upgraded to `ollama>=0.5.1` which relaxed the httpx constraint, and loosened httpx to `>=0.27.0`.

---

## 3. `unstructured` requires `numpy<2` / pulls PyTorch

**Error:** `unstructured[pdf,docx]` transitively requires `torch`, which has no Python 3.14 wheels.

**Cause:** `unstructured` bundles ML models and depends on torch/transformers for certain parsers.

**Fix:** Removed `unstructured` entirely. Replaced with `pypdf>=4.3.0` (PDF parsing) and `python-docx>=1.1.0` (DOCX parsing). Rewrote `backend/rag/ingestor.py` to use these directly.

---

## 4. `pydantic-core` PyO3 version caps at Python 3.13

**Error:**
```
ERROR: pydantic-core-2.27.1 requires Python <3.14
```

**Cause:** pydantic-core 2.27.x uses PyO3 0.22 which only compiled wheels up to Python 3.13.

**Fix:** Upgraded to `pydantic>=2.11.0` which ships pydantic-core 2.28+ built with PyO3 0.23 (Python 3.14 support).

---

## 5. `.env` file not found — settings load with empty values

**Error:** All settings loaded as empty strings; API keys were blank despite being in `.env`.

**Cause:** `pydantic-settings` resolves `env_file=".env"` relative to the current working directory. When running from `backend/`, it looked for `backend/.env` instead of the project root `.env`.

**Fix:** Anchored the path in `config.py`:
```python
_ENV_FILE = Path(__file__).parent.parent / ".env"
```

---

## 6. `sqlalchemy 2.0.36` — `Union.__getitem__` incompatible with Python 3.14

**Error:**
```
TypeError: 'type' object is not subscriptable
```
Raised during SQLAlchemy model inspection on Python 3.14.

**Cause:** Python 3.14 changed how `Union` behaves in certain contexts; SQLAlchemy 2.0.36 used an incompatible pattern.

**Fix:** Upgraded to `sqlalchemy[asyncio]>=2.0.40`.

---

## 7. Alembic migration fails — `anthropic_api_key` required field

**Error:** Alembic tried to instantiate `Settings` to read `database_url` and failed because `anthropic_api_key` had no default.

**Cause:** `anthropic_api_key: str` with no default means pydantic raises a `ValidationError` if the variable is absent.

**Fix:** Changed all optional keys to `= ""` defaults. Fields are checked at runtime where needed.

---

## 8. System PostgreSQL on port 5432 shadowing Docker

**Error:** `alembic upgrade head` connected to the local macOS system Postgres (port 5432) instead of the Docker container, causing schema mismatches.

**Cause:** macOS ships with PostgreSQL running on 5432; Docker's default mapping `5432:5432` silently connected to the wrong instance.

**Fix:** Changed `docker-compose.yml` postgres port to `"5433:5432"` and updated `DATABASE_URL` to `localhost:5433`.

---

## 9. `langfuse==2.57.3` — pydantic v1 incompatible with Python 3.14

**Error:**
```
UserWarning: Core Pydantic V1 functionality isn't compatible with Python 3.14
```
Followed by import-time crashes inside the langfuse SDK.

**Cause:** Langfuse 2.x internally uses pydantic v1 compatibility shims that break on Python 3.14.

**Fix:** Upgraded to `langfuse>=4.0.0`, which is fully pydantic v2 native.

---

## 10. Celery worker — `ModuleNotFoundError: No module named 'db'`

**Error:**
```
ModuleNotFoundError: No module named 'db'
```
Raised when Celery tried to execute the task in a fork worker.

**Cause (first occurrence):** All imports (`from db.session import ...`) were inside the task function body. Fork workers inherit `sys.path` from the parent process at the time of fork, but lazy imports inside the task body ran after the fork in a context where `backend/` was not on `sys.path`.

**Cause (second occurrence):** Even after moving imports to module level, the worker was started from the project root (`celery -A backend.workers.tasks worker`) instead of `backend/`. The module-level imports ran correctly only when `backend/` is the working directory.

**Fix:**
1. Added explicit `sys.path` manipulation at the very top of `tasks.py` (before any local imports):
   ```python
   _backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
   if _backend_dir not in sys.path:
       sys.path.insert(0, _backend_dir)
   ```
2. Moved all local imports to module level.
3. Always start the worker from `backend/`: `cd backend && celery -A workers.tasks worker ...`

---

## 11. `'Langfuse' object has no attribute 'trace'`

**Error:**
```
AttributeError: 'Langfuse' object has no attribute 'trace'
```

**Cause:** Langfuse v4 completely removed the `.trace()` method. The v2 stateful API (`lf.trace()`, `trace.span()`) was replaced with an OpenTelemetry-based API (`start_observation(type="trace", ...)`). Additionally, the `.env` placeholder values (`your_langfuse_public_key_here`) are non-empty strings, so `get_langfuse()` was initializing a real Langfuse client even though no real keys were configured.

**Fix:** Rewrote `backend/observability.py` to:
1. Detect placeholder key values and skip client initialization.
2. Use the v4 API: `lf.start_observation(type="trace", ...)` instead of `lf.trace(...)`.
3. Wrap all Langfuse calls in `try/except` so any future API drift degrades silently.

---

## 12. `operator does not exist: character varying = uuid`

**Error:**
```
sqlalchemy.exc.ProgrammingError: operator does not exist: character varying = uuid
[SQL: UPDATE reports SET ... WHERE reports.id = $3::UUID]
```

**Cause:** The Alembic migration created `reports.id` as `character varying(36)` (plain string), but the SQLAlchemy model declared it as `UUID(as_uuid=False)`. Even with `as_uuid=False`, SQLAlchemy still uses PostgreSQL's native UUID type in generated SQL, producing `$3::UUID` casts that PostgreSQL cannot compare against a `varchar` column.

**Fix:** Changed all `UUID(as_uuid=False)` column declarations in `db/models.py` to `String(36)`, matching what the migration actually created. Also removed the `from sqlalchemy.dialects.postgresql import UUID` import.

---

## 13. `RuntimeError: There is no current event loop in thread 'MainThread'`

**Error:**
```
RuntimeError: There is no current event loop in thread 'MainThread'.
File "workers/tasks.py", line 39, in _run_async
    return asyncio.get_event_loop().run_until_complete(coro)
```

**Cause:** `asyncio.get_event_loop()` was deprecated in Python 3.10. In Python 3.12+ it raises `RuntimeError` when called in a thread that has no running event loop (e.g. a Celery fork worker's main thread after forking).

**Fix:** Replaced `asyncio.get_event_loop().run_until_complete(coro)` with `asyncio.run(coro)`, which always creates a fresh event loop.

---

## 14. `TypeError: 'coroutine' object is not iterable`

**Error:**
```
TypeError: 'coroutine' object is not iterable
File "tools/document_retriever.py", line 40, in format_retrieval_results
    for r in results:
```

**Cause:** `rag_retrieve` (defined in the Celery task as `async def`) was called without `await` inside `_dispatch_tool`. Because `_dispatch_tool` was a plain synchronous method, the call returned a coroutine object instead of executing it. The coroutine was then passed to `format_retrieval_results` which tried to iterate it.

**Fix:** Made the entire agent pipeline async end-to-end:
- `BaseAgent.run()` → `async def`
- `BaseAgent._dispatch_tool()` → `async def`
- All four specialist agents' `_dispatch_tool` → `async def`, with `await rag_retrieve(...)`
- `run_orchestrator()` → `async def`, with `await` on every agent `.run()` call
- `run_orchestrator(...)` call in `tasks.py` → `await run_orchestrator(...)`
- Switched from `openai.OpenAI` to `openai.AsyncOpenAI` throughout

---

## 15. `RuntimeError: Future attached to a different loop`

**Error:**
```
RuntimeError: Task ... got Future ... attached to a different loop
```
Also accompanied by:
```
RuntimeError: Event loop is closed
```
on asyncpg connection teardown.

**Cause:** Two separate module-level objects were binding to the event loop at import time:

1. **SQLAlchemy async engine** (`create_async_engine(...)` in `db/session.py`) — the connection pool holds asyncpg connections that reference the event loop that existed when the pool was first used. Since `asyncio.run()` creates a **new** loop each time, the pooled connections become invalid on the next task invocation.

2. **`AsyncOpenAI` client** (`_client = AsyncOpenAI(...)` at module level in `base.py` and `orchestrator.py`) — internally holds an `httpx.AsyncClient` which also binds to its creation-time event loop.

**Fix:**
1. Added `poolclass=NullPool` to the SQLAlchemy engine in `db/session.py`. `NullPool` disables all connection caching — every `async with session:` opens a fresh connection and closes it on exit, so there is nothing bound to a stale loop.
2. Changed `AsyncOpenAI` from module-level singletons to factory functions (`_get_client()`, `_get_openai_client()`) called inside the async path, so the client is created on the current loop.

---

## Summary Table

| # | Error | Root Cause | Fix |
|---|---|---|---|
| 1 | `unstructured==0.16.10` not found | Wrong version pinned | Use `0.16.19` |
| 2 | `ollama` vs `httpx` conflict | ollama 0.4.x strict httpx bound | `ollama>=0.5.1`, `httpx>=0.27.0` |
| 3 | PyTorch no Python 3.14 wheels | `unstructured` pulls torch | Replace with `pypdf` + `python-docx` |
| 4 | `pydantic-core` caps at Python 3.13 | PyO3 0.22 limitation | `pydantic>=2.11.0` |
| 5 | `.env` not loaded | Relative path resolved from cwd | Anchor path to `__file__` |
| 6 | SQLAlchemy `Union.__getitem__` | Python 3.14 breaking change | `sqlalchemy>=2.0.40` |
| 7 | Alembic fails on missing API key | Required field, no default | Add `= ""` defaults |
| 8 | Wrong Postgres instance | macOS Postgres on 5432 | Remap Docker to port 5433 |
| 9 | langfuse pydantic v1 crash | langfuse 2.x uses pydantic v1 | `langfuse>=4.0.0` |
| 10 | `No module named 'db'` | `sys.path` not set in fork worker | Explicit `sys.path` insert + run from `backend/` |
| 11 | `Langfuse has no attribute 'trace'` | v4 API removed `.trace()` | Rewrite observability.py for v4 + skip placeholders |
| 12 | `character varying = uuid` | Model used `UUID` type, DB has `varchar` | Change model columns to `String(36)` |
| 13 | `no current event loop` | `get_event_loop()` deprecated in 3.12+ | Use `asyncio.run()` |
| 14 | `coroutine object is not iterable` | Async `rag_retrieve` called without `await` | Make full agent chain async |
| 15 | `Future attached to a different loop` | Pooled connections + clients bound to old loop | `NullPool` + create `AsyncOpenAI` per-call |
