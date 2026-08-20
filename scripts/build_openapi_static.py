"""
Builds doc/api/openapi.json / openapi.yaml WITHOUT requiring FastAPI to be
installed -- only `pydantic` (already present) is needed.

Why this exists: `scripts/export_openapi.py` is the normal/preferred path
(it imports the live `app.main.app` and calls `app.openapi()`, so it's
always byte-for-byte what `/openapi.json` actually serves) and should be
re-run after any route/schema change. This script is a fallback for
environments where installing the full `backend/requirements.txt` isn't
possible yet -- it hand-assembles an equivalent OpenAPI 3.1 document
directly from the same Pydantic models and the route definitions in
`app/api/routes_*.py`, so the two stay in lockstep with the actual code
paths/methods/schemas even though FastAPI itself never runs.

Run from the backend/ directory:
    cd backend && python ../scripts/build_openapi_static.py

Prefer `scripts/export_openapi.py` once `pip install -r requirements.txt`
is possible -- see README "Known limitations of this build".
"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pydantic  # noqa: E402
import yaml  # noqa: E402
from pydantic.json_schema import models_json_schema  # noqa: E402

from app import __version__  # noqa: E402
from app.api import schemas as S  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "doc", "api")
os.makedirs(OUT_DIR, exist_ok=True)

# --------------------------------------------------------------------------- #
# 1. Component schemas -- every Pydantic model in app/api/schemas.py
# --------------------------------------------------------------------------- #
models = [
    m
    for _, m in inspect.getmembers(S)
    if inspect.isclass(m) and issubclass(m, pydantic.BaseModel) and m.__module__ == S.__name__
]
pairs = [(m, "validation") for m in models]
_, top_schema = models_json_schema(pairs, ref_template="#/components/schemas/{model}")
component_schemas = dict(top_schema.get("$defs", {}))

# Standard FastAPI validation-error shape, referenced by every endpoint that
# accepts a request body (mirrors what FastAPI auto-generates).
component_schemas["ValidationError"] = {
    "title": "ValidationError",
    "type": "object",
    "properties": {
        "loc": {"title": "Location", "type": "array", "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]}},
        "msg": {"title": "Message", "type": "string"},
        "type": {"title": "Error Type", "type": "string"},
    },
    "required": ["loc", "msg", "type"],
}
component_schemas["HTTPValidationError"] = {
    "title": "HTTPValidationError",
    "type": "object",
    "properties": {
        "detail": {"title": "Detail", "type": "array", "items": {"$ref": "#/components/schemas/ValidationError"}}
    },
}


def ref(model_name: str) -> dict:
    return {"$ref": f"#/components/schemas/{model_name}"}


def json_body(model_name: str) -> dict:
    return {"required": True, "content": {"application/json": {"schema": ref(model_name)}}}


def json_response(description: str, model_name: str | None = None) -> dict:
    if model_name is None:
        return {"description": description}
    return {"description": description, "content": {"application/json": {"schema": ref(model_name)}}}


VALIDATION_ERROR_RESPONSE = json_response("Validation Error", "HTTPValidationError")

# --------------------------------------------------------------------------- #
# 2. Paths -- hand-mirrored from app/api/routes_*.py + app/main.py mounting
# --------------------------------------------------------------------------- #
paths: dict = {}


def add(path: str, method: str, *, tags, summary, description, request_model=None, response_model=None, response_desc="Successful Response"):
    op = {
        "tags": tags,
        "summary": summary,
        "description": description,
        "operationId": f"{method}_{path.strip('/').replace('/', '_')}",
        "responses": {"200": json_response(response_desc, response_model)},
    }
    if request_model:
        op["requestBody"] = json_body(request_model)
        op["responses"]["422"] = VALIDATION_ERROR_RESPONSE
    paths.setdefault(path, {})[method] = op


# Health
add("/api/v1/health", "get", tags=["health"], summary="Health",
    description="Liveness + dependency checks (Postgres, Ollama, Phoenix).",
    response_model="HealthResponse")

# Ingestion
add("/api/v1/ingest", "post", tags=["ingestion"], summary="Ingest",
    description="Runs the full Docling -> split -> embed -> PGVector-index pipeline over "
                 "`source_dir` (defaults to SOURCE_DOCUMENTS_DIR, e.g. the mounted `sample_docs/` directory).",
    request_model="IngestRequest", response_model="IngestResponse")
add("/api/v1/ingest/status", "get", tags=["ingestion"], summary="Ingest Status",
    description="Polls the result of the most recent background ingestion run.",
    response_model="IngestResponse")

# Native RAG query + raw search
add("/api/v1/query", "post", tags=["rag"], summary="Query",
    description="Native rich RAG query: runs the CrewAI agentic crew and returns the answer, "
                 "citations, verifier approval status, and (optionally) the full execution trace.",
    request_model="RagQueryRequest", response_model="RagQueryResponse")
add("/api/v1/search", "post", tags=["rag"], summary="Search",
    description="Raw retrieval only (no generation) -- useful for debugging what the index contains.",
    request_model="SearchRequest", response_model="SearchResponse")

# Prompts
add("/api/v1/prompts", "get", tags=["prompts"], summary="List Prompts",
    description="Introspection endpoint over the externalized prompt library "
                 "(app/prompts/library/*.yaml) -- lets an operator confirm which prompt versions are live.",
    response_model="PromptListResponse")
add("/api/v1/prompts/reload", "post", tags=["prompts"], summary="Reload Prompts",
    description="Hot-reloads prompt YAML files from disk without restarting the service.",
    response_model="PromptListResponse")

# Evaluation
add("/api/v1/eval/run", "post", tags=["evaluation"], summary="Run Eval",
    description="Runs the RAGAs evaluation harness over the curated Q&A dataset and returns "
                 "aggregate faithfulness / answer relevancy / context precision / context recall scores.",
    request_model="EvalRunRequest", response_model="EvalRunResponse")
add("/api/v1/eval/status", "get", tags=["evaluation"], summary="Eval Status",
    description="Polls the result of the most recent background evaluation run.",
    response_model="EvalRunResponse")

# OpenAI-compatible surface (mounted at the root, not under /api/v1)
add("/v1/chat/completions", "post", tags=["openwebui-compat"], summary="Chat Completions",
    description="OpenAI-compatible surface consumed by OpenWebUI (or any OpenAI SDK client). "
                 "`stream=true` is rejected with a 400 -- this endpoint returns one final, verified answer per turn.",
    request_model="ChatCompletionRequest", response_model="ChatCompletionResponse")
add("/v1/models", "get", tags=["openwebui-compat"], summary="List Models",
    description="OpenAI-compatible model list -- advertises the single `agentic-rag` model.",
    response_model="ModelListResponse")

# --------------------------------------------------------------------------- #
# 3. Assemble the document
# --------------------------------------------------------------------------- #
openapi = {
    "openapi": "3.1.0",
    "info": {
        "title": "Document Search Platform -- Agentic RAG API",
        "description": (
            "REST API for an agentic Retrieval-Augmented Generation backend: Docling document "
            "preprocessing, LlamaIndex + PGVector indexing and retrieval, a CrewAI multi-agent "
            "contextual RAG pipeline (query analysis -> retrieval -> synthesis -> verification), "
            "Arize Phoenix tracing, and RAGAs-based evaluation. Also exposes an OpenAI-compatible "
            "`/v1/chat/completions` surface so OpenWebUI (or any OpenAI SDK client) can use this "
            "backend directly."
        ),
        "version": __version__,
        "contact": {"name": "Document Search Platform"},
        "license": {"name": "MIT"},
    },
    "servers": [{"url": "http://localhost:8000", "description": "Local docker-compose deployment"}],
    "paths": paths,
    "components": {"schemas": dict(sorted(component_schemas.items()))},
}

json_path = os.path.join(OUT_DIR, "openapi.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(openapi, f, indent=2)
print(f"wrote {json_path} ({len(paths)} paths, {len(component_schemas)} component schemas)")

yaml_path = os.path.join(OUT_DIR, "openapi.yaml")
with open(yaml_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(openapi, f, sort_keys=False)
print(f"wrote {yaml_path}")
