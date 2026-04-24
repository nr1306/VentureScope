from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import commit_with_retry, execute_with_retry, get_db
from db.models import Report
from models.report import ReportStatusResponse, DueDiligenceReport

router = APIRouter(tags=["reports"])


@router.get("/report/{report_id}", response_model=ReportStatusResponse)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    result = await execute_with_retry(db, select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    full_report = None
    if report.status == "completed" and report.result:
        try:
            full_report = DueDiligenceReport(**report.result)
        except ValidationError as exc:
            raise HTTPException(status_code=500, detail="Stored report payload is invalid.") from exc

    return ReportStatusResponse(
        report_id=report.id,
        status=report.status,
        company_name=report.company_name,
        created_at=report.created_at,
        completed_at=report.completed_at,
        report=full_report,
        error=report.error,
    )


@router.get("/reports", response_model=list[ReportStatusResponse])
async def list_reports(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await execute_with_retry(
        db,
        select(Report).order_by(desc(Report.created_at)).limit(limit)
    )
    reports = result.scalars().all()
    return [
        ReportStatusResponse(
            report_id=r.id,
            status=r.status,
            company_name=r.company_name,
            created_at=r.created_at,
            completed_at=r.completed_at,
            error=r.error,
        )
        for r in reports
    ]


@router.delete("/report/{report_id}", status_code=204)
async def delete_report(report_id: str, db: AsyncSession = Depends(get_db)):
    result = await execute_with_retry(db, select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.delete(report)
    await commit_with_retry(db)


@router.delete("/reports", status_code=204)
async def delete_all_reports(db: AsyncSession = Depends(get_db)):
    await execute_with_retry(db, delete(Report))
    await commit_with_retry(db)
