from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter

from app import __version__
from app.api.schemas import HealthResponse
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()

    postgres_ok = _check_postgres(settings)
    ollama_ok = await _check_ollama(settings)
    phoenix_ok = await _check_phoenix(settings) if settings.phoenix_enabled else True

    status = "ok" if (postgres_ok and ollama_ok and phoenix_ok) else "degraded"
    return HealthResponse(
        status=status,
        version=__version__,
        postgres=postgres_ok,
        ollama=ollama_ok,
        phoenix=phoenix_ok,
    )


def _check_postgres(settings) -> bool:
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        logger.warning("Postgres health check failed", exc_info=True)
        return False


async def _check_ollama(settings) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        logger.warning("Ollama health check failed", exc_info=True)
        return False


async def _check_phoenix(settings) -> bool:
    try:
        base = settings.phoenix_collector_endpoint.split("/v1/traces")[0]
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(base)
            return resp.status_code < 500
    except Exception:
        logger.warning("Phoenix health check failed", exc_info=True)
        return False
