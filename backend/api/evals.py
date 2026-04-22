from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models import EvalResult
from workers.tasks import run_eval_suite

router = APIRouter(tags=["evals"])


@router.post("/eval/run")
async def trigger_eval():
    task = run_eval_suite.delay()
    return {"task_id": task.id, "message": "Eval suite started. Check /api/eval/results for scores."}


@router.get("/eval/results")
async def get_eval_results(limit: int = 10, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
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
