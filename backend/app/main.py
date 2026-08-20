"""
FastAPI application entrypoint.

Wires together: CORS, the API routers, Phoenix tracing initialization (once,
at startup, covering every inference call made afterwards), and the
auto-generated OpenAPI/Swagger docs served at /docs and /openapi.json.

Run directly:
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Or via docker-compose (see repo root docker-compose.yml).
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes_chat import native_router, openai_router, search_router
from app.api.routes_eval import router as eval_router
from app.api.routes_health import router as health_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_prompts import router as prompts_router
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Document Search Platform -- Agentic RAG API",
    description=(
        "REST API for an agentic Retrieval-Augmented Generation backend: "
        "Docling document preprocessing, LlamaIndex + PGVector indexing and "
        "retrieval, a CrewAI multi-agent contextual RAG pipeline (query "
        "analysis -> retrieval -> synthesis -> verification), Arize Phoenix "
        "tracing, and RAGAs-based evaluation. Also exposes an "
        "OpenAI-compatible `/v1/chat/completions` surface so OpenWebUI (or "
        "any OpenAI SDK client) can use this backend directly."
    ),
    version=__version__,
    contact={"name": "Document Search Platform"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production (see README "Security notes")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    from app.retrieval.vector_store import configure_llama_index_settings
    from app.tracing.phoenix_setup import init_tracing

    # Tracing is initialized first and unconditionally so every LlamaIndex /
    # CrewAI / LiteLLM call made from any request handler is instrumented --
    # satisfies "implement tracing for all inference calls".
    init_tracing(settings)
    configure_llama_index_settings(settings)
    logger.info("Startup complete: environment=%s", settings.environment)


app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(ingest_router, prefix=settings.api_prefix)
app.include_router(native_router, prefix=settings.api_prefix)
app.include_router(search_router, prefix=settings.api_prefix)
app.include_router(prompts_router, prefix=settings.api_prefix)
app.include_router(eval_router, prefix=settings.api_prefix)
# OpenAI-compatible routes are intentionally mounted at the root (/v1/...),
# matching the convention OpenWebUI / OpenAI SDK clients expect for a custom
# "OpenAI API base URL" -- not nested under /api/v1.
app.include_router(openai_router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "doc-search-agentic-rag",
        "version": __version__,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
