"""Pydantic request/response models for the REST API.

Kept as a dedicated module (rather than inline in route files) so the
generated OpenAPI/Swagger schema (see app/main.py + scripts/export_openapi.py)
has clean, named component schemas.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    postgres: bool
    ollama: bool
    phoenix: bool


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #
class IngestRequest(BaseModel):
    source_dir: Optional[str] = Field(
        default=None,
        description="Directory of documents to ingest. Defaults to SOURCE_DOCUMENTS_DIR.",
    )
    run_async: bool = Field(default=True, description="If true, run ingestion in the background and return immediately.")


class IngestResponse(BaseModel):
    status: Literal["started", "completed"]
    documents_processed: Optional[int] = None
    chunks_indexed: Optional[int] = None
    duration_seconds: Optional[float] = None
    skipped_files: List[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Search (raw retrieval, no generation -- useful for debugging the index)
# --------------------------------------------------------------------------- #
class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=6, ge=1, le=50)


class SearchResultItem(BaseModel):
    text: str
    score: float
    source_file: str
    section_path: str
    node_id: str


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]


# --------------------------------------------------------------------------- #
# Native RAG query (rich response incl. agent trace + verification status)
# --------------------------------------------------------------------------- #
class RagQueryRequest(BaseModel):
    question: str
    chat_history: Optional[str] = Field(default="", description="Freeform prior-turn context, if any.")
    include_trace: bool = Field(default=False, description="Include the full multi-agent execution trace.")


class SourceRef(BaseModel):
    source_file: str
    section_path: str


class RagQueryResponse(BaseModel):
    question: str
    answer: str
    approved: bool = Field(description="Whether the Verifier agent approved the answer as grounded.")
    iterations: int
    sources: List[SourceRef]
    trace: Optional[List[Dict[str, Any]]] = None


# --------------------------------------------------------------------------- #
# OpenAI-compatible chat completions (consumed by OpenWebUI)
# --------------------------------------------------------------------------- #
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "agentic-rag"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.1
    stream: Optional[bool] = False


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage = Field(default_factory=ChatCompletionUsage)


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "doc-search-agentic-rag"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


# --------------------------------------------------------------------------- #
# Prompts (introspection of the externalized prompt library)
# --------------------------------------------------------------------------- #
class PromptInfo(BaseModel):
    name: str
    version: str
    summary: str
    fields: List[str]
    input_variables: List[str]


class PromptListResponse(BaseModel):
    prompts: List[PromptInfo]


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
class EvalRunRequest(BaseModel):
    dataset_path: Optional[str] = None
    run_async: bool = True


class EvalMetricScores(BaseModel):
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None


class EvalRunResponse(BaseModel):
    status: Literal["started", "completed"]
    num_questions: Optional[int] = None
    scores: Optional[EvalMetricScores] = None
    report_path: Optional[str] = None
