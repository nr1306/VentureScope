from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import execute_with_retry, get_db
from db.models import EvalResult
from workers.tasks import run_eval_suite

router = APIRouter(tags=["evals"])


@router.post("/eval/run")
async def trigger_eval():
    try:
        task = run_eval_suite.delay()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to start eval suite right now.") from exc
    return {"task_id": task.id, "message": "Eval suite started. Check /api/eval/results for scores."}


@router.get("/eval/results")
async def get_eval_results(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await execute_with_retry(
        db,
        select(EvalResult).order_by(desc(EvalResult.run_at)).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "run_at": r.run_at,
            "company_name": r.company_name,
            "report_id": r.report_id,
            "scores": r.scores,
            "judge_feedback": r.judge_feedback,
        }
        for r in rows
    ]
