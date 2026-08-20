from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from starlette.concurrency import run_in_threadpool

from app.api.schemas import IngestRequest, IngestResponse
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingestion"])

_last_result = {}


def _run_and_store(source_dir: str | None) -> None:
    from app.ingestion.pipeline import run_ingestion

    try:
        result = run_ingestion(source_dir=source_dir)
        _last_result["result"] = result
    except Exception:
        logger.exception("Background ingestion failed")
        _last_result["error"] = True


@router.post("", response_model=IngestResponse)
async def ingest(req: IngestRequest, background_tasks: BackgroundTasks) -> IngestResponse:
    """Runs the full Docling -> split -> embed -> PGVector-index pipeline
    over `source_dir` (defaults to SOURCE_DOCUMENTS_DIR, e.g. the mounted
    `sample_docs/` directory)."""
    settings = get_settings()
    source_dir = req.source_dir or settings.source_documents_dir

    if req.run_async:
        background_tasks.add_task(_run_and_store, source_dir)
        return IngestResponse(status="started")

    from app.ingestion.pipeline import run_ingestion

    try:
        result = await run_in_threadpool(run_ingestion, source_dir=source_dir)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    _last_result["result"] = result
    _last_result.pop("error", None)

    return IngestResponse(
        status="completed",
        documents_processed=result.documents_processed,
        chunks_indexed=result.chunks_indexed,
        duration_seconds=round(result.duration_seconds, 2),
        skipped_files=result.skipped_files,
    )


@router.get("/status", response_model=IngestResponse)
async def ingest_status() -> IngestResponse:
    """Polls the result of the most recent background ingestion run."""
    if "error" in _last_result:
        raise HTTPException(status_code=500, detail="Last background ingestion run failed; check server logs.")
    result = _last_result.get("result")
    if result is None:
        return IngestResponse(status="started")
    return IngestResponse(
        status="completed",
        documents_processed=result.documents_processed,
        chunks_indexed=result.chunks_indexed,
        duration_seconds=round(result.duration_seconds, 2),
        skipped_files=result.skipped_files,
    )
