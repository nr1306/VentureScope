"""
Eval runner — iterates over the golden dataset, runs the agent,
scores each report, and persists results to the database.

Run directly:  python -m evals.eval_runner
Run via API:   POST /api/eval/run
"""
from __future__ import annotations
import asyncio
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from db.session import AsyncSessionLocal, commit_with_retry
from db.models import EvalResult
from agents.orchestrator import run_orchestrator
from evals.metrics import compute_all_metrics
from evals.llm_judge import judge_report

GOLDEN_DIR = Path(__file__).parent / "golden_dataset"


async def run_all_evals() -> list[dict]:
    """Run eval suite against all golden dataset companies."""
    results = []
    golden_files = list(GOLDEN_DIR.glob("*.json"))

    for gf in golden_files:
        golden = json.loads(await asyncio.to_thread(gf.read_text))

        company_name = golden["company_name"]
        ground_truth = golden["ground_truth"]
        report_id = str(uuid.uuid4())

        print(f"\n[EVAL] Running agent for: {company_name}")

        try:
            # No RAG for evals (no uploaded docs) — use a no-op retriever
            async def noop_retrieve(query: str, top_k: int = 5):
                return []

            report = await run_orchestrator(
                report_id=report_id,
                company_name=company_name,
                rag_retrieve=noop_retrieve,
            )

            # Deterministic metrics
            metrics = compute_all_metrics(report, ground_truth)

            # LLM-as-judge
            judge_scores = await judge_report(report, ground_truth)

            all_scores = {**metrics, "judge": judge_scores}

            # Aggregate judge score
            judge_avgs = [v.get("average", 0.5) for v in judge_scores.values()]
            all_scores["judge_average"] = round(sum(judge_avgs) / max(len(judge_avgs), 1), 2)

            print(f"[EVAL] {company_name} — metrics: {metrics}")
            print(f"[EVAL] {company_name} — judge avg: {all_scores['judge_average']:.2f}")

            # Persist to DB
            async with AsyncSessionLocal() as db:
                eval_result = EvalResult(
                    id=str(uuid.uuid4()),
                    run_at=datetime.now(timezone.utc),
                    company_name=company_name,
                    report_id=report_id,
                    scores=all_scores,
                    judge_feedback={k: v.get("feedback", "") for k, v in judge_scores.items()},
                )
                db.add(eval_result)
                await commit_with_retry(db)

            results.append({"company": company_name, "scores": all_scores})

        except Exception as e:
            print(f"[EVAL] ERROR for {company_name}: {e}")
            results.append({"company": company_name, "error": str(e)})

    return results


if __name__ == "__main__":
    asyncio.run(run_all_evals())
