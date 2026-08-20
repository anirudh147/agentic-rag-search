from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks
from starlette.concurrency import run_in_threadpool

from app.api.schemas import EvalMetricScores, EvalRunRequest, EvalRunResponse
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/eval", tags=["evaluation"])

_last_result = {}


def _run_and_store(dataset_path: str | None) -> None:
    from app.evaluation.run_ragas import run_evaluation

    try:
        _last_result["result"] = run_evaluation(dataset_path=dataset_path)
    except Exception:
        logger.exception("Background RAGAs evaluation failed")
        _last_result["error"] = True


@router.post("/run", response_model=EvalRunResponse)
async def run_eval(req: EvalRunRequest, background_tasks: BackgroundTasks) -> EvalRunResponse:
    """Runs the RAGAs evaluation harness (app/evaluation/run_ragas.py) over
    the curated Q&A dataset and returns aggregate faithfulness / answer
    relevancy / context precision / context recall scores."""
    settings = get_settings()
    dataset_path = req.dataset_path or settings.eval_dataset_path

    if req.run_async:
        background_tasks.add_task(_run_and_store, dataset_path)
        return EvalRunResponse(status="started")

    from app.evaluation.run_ragas import run_evaluation

    result = await run_in_threadpool(run_evaluation, dataset_path=dataset_path)
    _last_result["result"] = result
    _last_result.pop("error", None)
    return EvalRunResponse(
        status="completed",
        num_questions=result.num_questions,
        scores=EvalMetricScores(**result.scores),
        report_path=result.report_path,
    )


@router.get("/status", response_model=EvalRunResponse)
async def eval_status() -> EvalRunResponse:
    if "error" in _last_result:
        return EvalRunResponse(status="started")
    result = _last_result.get("result")
    if result is None:
        return EvalRunResponse(status="started")
    return EvalRunResponse(
        status="completed",
        num_questions=result.num_questions,
        scores=EvalMetricScores(**result.scores),
        report_path=result.report_path,
    )
