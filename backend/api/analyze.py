import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models import Report
from models.report import AnalyzeRequest, AnalyzeResponse
from guardrails.input_guardrails import validate_company_input
from workers.tasks import run_due_diligence

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    # Input guardrail — raises HTTPException on violation
    validate_company_input(request.company_name)

    report_id = str(uuid.uuid4())
    report = Report(
        id=report_id,
        company_name=request.company_name,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(report)
    await db.commit()

    # Dispatch async Celery task
    task = run_due_diligence.delay(report_id, request.company_name)

    report.celery_task_id = task.id
    report.status = "running"
    await db.commit()

    return AnalyzeResponse(
        report_id=report_id,
        status="running",
        message=f"Analysis started for '{request.company_name}'. Poll /api/report/{report_id} for results.",
    )
