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
from sqlalchemy import select

from config import settings
from db.session import AsyncSessionLocal
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
    return asyncio.run(coro)


@celery_app.task(name="run_due_diligence", bind=True, max_retries=1)
def run_due_diligence(self, report_id: str, company_name: str):
    """Main agent task — runs the full orchestrator pipeline."""

    async def _execute():
        async with AsyncSessionLocal() as db:
            async def rag_retrieve(query: str, top_k: int = 5):
                return await retrieve(db=db, company_name=company_name, query=query, top_k=top_k)

            try:
                report = await run_orchestrator(
                    report_id=report_id,
                    company_name=company_name,
                    rag_retrieve=rag_retrieve,
                )

                result = await db.execute(select(Report).where(Report.id == report_id))
                db_report = result.scalar_one_or_none()
                if db_report:
                    db_report.status = "completed"
                    db_report.result = report.model_dump(mode="json")
                    db_report.completed_at = datetime.now(timezone.utc)
                    db_report.langfuse_trace_id = report.langfuse_trace_id
                    await db.commit()

            except Exception as exc:
                result = await db.execute(select(Report).where(Report.id == report_id))
                db_report = result.scalar_one_or_none()
                if db_report:
                    db_report.status = "failed"
                    db_report.error = str(exc)
                    await db.commit()
                raise

    _run_async(_execute())


@celery_app.task(name="run_eval_suite", bind=True)
def run_eval_suite(self):
    """Run the eval harness against the golden dataset."""
    _run_async(run_all_evals())
