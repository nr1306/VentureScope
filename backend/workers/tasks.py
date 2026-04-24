"""
Celery tasks — all agent runs happen here asynchronously.
"""
from __future__ import annotations
import asyncio
import os
import sys
from datetime import datetime, timezone

# Ensure backend/ is on sys.path before any local imports.
# This must happen before importing Celery or any project module so that
# fork workers inherit the correct path from the very first import.
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from celery import Celery
from httpx import ConnectError, ReadTimeout, TimeoutException
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from sqlalchemy import select

from config import settings
from db.session import AsyncSessionLocal, commit_with_retry, execute_with_retry, is_transient_db_error
from db.models import Report
from agents.orchestrator import run_orchestrator
from rag.retriever import retrieve
from evals.eval_runner import run_all_evals

celery_app = Celery("venturesscope", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


def _run_async(coro):
    """Run an async coroutine from sync Celery task context."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("Cannot call _run_async() from within an active event loop.")


async def _update_report_status(
    report_id: str,
    *,
    status: str,
    error: str | None = None,
    result: dict | None = None,
    langfuse_trace_id: str | None = None,
) -> None:
    async with AsyncSessionLocal() as db:
        db_report = await _get_report(db, report_id)
        if not db_report:
            return

        db_report.status = status
        db_report.error = error[:4000] if error else None
        if result is not None:
            db_report.result = result
        if langfuse_trace_id is not None:
            db_report.langfuse_trace_id = langfuse_trace_id
        if status == "completed":
            db_report.completed_at = datetime.now(timezone.utc)
        await commit_with_retry(db)


async def _get_report(db, report_id: str) -> Report | None:
    result = await execute_with_retry(db, select(Report).where(Report.id == report_id))
    return result.scalar_one_or_none()


def _is_retryable_task_error(exc: BaseException) -> bool:
    retryable_types = (
        APIConnectionError,
        APITimeoutError,
        ConnectError,
        RateLimitError,
        ReadTimeout,
        TimeoutException,
    )
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500
    return isinstance(exc, retryable_types) or is_transient_db_error(exc)


def _retry_countdown(retry_index: int) -> int:
    return min(2 ** retry_index, 30)


def _best_effort_update_report_status(report_id: str, **kwargs) -> None:
    try:
        _run_async(_update_report_status(report_id, **kwargs))
    except Exception as exc:
        print(f"[WORKER] Failed to update report {report_id} status: {exc}")


@celery_app.task(name="run_due_diligence", bind=True, max_retries=3)
def run_due_diligence(self, report_id: str, company_name: str):
    """Main agent task — runs the full orchestrator pipeline."""

    async def _execute():
        async with AsyncSessionLocal() as db:
            async def rag_retrieve(query: str, top_k: int = 5):
                return await retrieve(db=db, company_name=company_name, query=query, top_k=top_k)

            return await run_orchestrator(
                report_id=report_id,
                company_name=company_name,
                rag_retrieve=rag_retrieve,
            )

    try:
        report = _run_async(_execute())
        _best_effort_update_report_status(
            report_id,
            status="completed",
            result=report.model_dump(mode="json"),
            langfuse_trace_id=report.langfuse_trace_id,
        )
    except Exception as exc:
        if _is_retryable_task_error(exc) and self.request.retries < self.max_retries:
            _best_effort_update_report_status(
                report_id,
                status="running",
                error=f"Transient worker failure. Retrying ({self.request.retries + 1}/{self.max_retries}).",
            )
            raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))

        _best_effort_update_report_status(
            report_id,
            status="failed",
            error=str(exc),
        )
        raise


@celery_app.task(name="run_eval_suite", bind=True)
def run_eval_suite(self):
    """Run the eval harness against the golden dataset."""
    _run_async(run_all_evals())
