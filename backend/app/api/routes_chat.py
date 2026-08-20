"""
Two surfaces over the same agentic RAG pipeline (app/agents/crew.py):

  * /api/v1/query          - "native" endpoint, rich response (sources,
                              approval status, optional full agent trace).
  * /v1/chat/completions
    /v1/models              - OpenAI-compatible surface so OpenWebUI (or any
                              OpenAI SDK client) can talk to this backend by
                              just setting it as a custom "OpenAI API" base
                              URL -- no OpenWebUI plugin/pipeline needed.

Also exposes /api/v1/search for raw retrieval (no generation) -- handy for
debugging what the index actually contains.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.api.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ModelInfo,
    ModelListResponse,
    RagQueryRequest,
    RagQueryResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SourceRef,
)
from app.config import get_settings

logger = logging.getLogger(__name__)

native_router = APIRouter(prefix="/query", tags=["rag"])
search_router = APIRouter(prefix="/search", tags=["rag"])
openai_router = APIRouter(tags=["openwebui-compat"])


@native_router.post("", response_model=RagQueryResponse)
async def query(req: RagQueryRequest) -> RagQueryResponse:
    from app.agents.crew import run_agentic_rag

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    result = await run_in_threadpool(run_agentic_rag, question=req.question, chat_history=req.chat_history or "")
    return RagQueryResponse(
        question=req.question,
        answer=result.answer,
        approved=result.approved,
        iterations=result.iterations,
        sources=[SourceRef(**s) for s in result.sources],
        trace=result.trace if req.include_trace else None,
    )


@search_router.post("", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    from app.retrieval.query_engine import retrieve

    chunks = await run_in_threadpool(retrieve, req.query, top_k=req.top_k)
    return SearchResponse(query=req.query, results=[SearchResultItem(**c) for c in chunks])


def _messages_to_question_and_history(messages: list[ChatMessage]) -> tuple[str, str]:
    """OpenWebUI sends the full chat history each turn (OpenAI Chat
    Completions convention). We treat the last user message as the current
    question and flatten everything before it into a chat_history string
    for the Query Analyzer agent to resolve references against.
    """
    if not messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    user_messages = [m for m in messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="no user message found")
    question = user_messages[-1].content

    history_lines = []
    for m in messages[:-1]:
        if m.role == "system":
            continue
        history_lines.append(f"{m.role}: {m.content}")
    return question, "\n".join(history_lines)


@openai_router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(req: ChatCompletionRequest) -> ChatCompletionResponse:
    from app.agents.crew import run_agentic_rag

    if req.stream:
        # Streaming isn't implemented in this reference build (the crew
        # produces one final answer per turn, not incremental tokens).
        # OpenWebUI degrades gracefully to a non-streamed render if the
        # response isn't SSE-formatted, but we reject explicitly so a
        # misconfigured client gets a clear error instead of a silent hang.
        raise HTTPException(
            status_code=400,
            detail="stream=true is not supported by this endpoint; set stream=false in OpenWebUI's connection settings.",
        )

    question, history = _messages_to_question_and_history(req.messages)
    result = await run_in_threadpool(run_agentic_rag, question=question, chat_history=history)

    content = result.answer
    if result.sources:
        src_lines = "\n".join(f"- {s['source_file']} ({s['section_path']})" for s in result.sources)
        content = f"{content}\n\n**Sources**\n{src_lines}"
    if not result.approved:
        content = f"_(unverified -- the reviewer agent could not fully confirm this answer is grounded)_\n\n{content}"

    return ChatCompletionResponse(
        model=req.model,
        choices=[ChatCompletionChoice(index=0, message=ChatMessage(role="assistant", content=content))],
    )


@openai_router.get("/v1/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    settings = get_settings()
    return ModelListResponse(data=[ModelInfo(id=settings.openai_compat_default_model_name)])
