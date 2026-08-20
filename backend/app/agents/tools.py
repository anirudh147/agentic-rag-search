"""
CrewAI tool that gives the Retriever agent access to the LlamaIndex +
PGVector knowledge base. Kept as a thin adapter: all actual retrieval logic
(top_k, similarity cutoff) lives in app/retrieval/query_engine.py and is
shared with the plain `/search` REST endpoint.
"""
from __future__ import annotations

import json
from typing import Type

from pydantic import BaseModel, Field


class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(..., description="A focused search query (not the full conversation).")
    top_k: int = Field(default=6, description="Maximum number of passages to return.")


def _build_search_tool():
    """Deferred import of crewai_tools.BaseTool so this module (and anything
    that imports it, e.g. for unit tests) doesn't require CrewAI installed
    unless the tool is actually instantiated.
    """
    from crewai.tools import BaseTool

    class SearchKnowledgeBaseTool(BaseTool):
        name: str = "search_knowledge_base"
        description: str = (
            "Semantic search over the organization's indexed documents. "
            "Input is a focused search query string. Returns the top matching "
            "passages with their source document name, section path, and "
            "relevance score. Use one focused query per call rather than the "
            "full user question verbatim."
        )
        args_schema: Type[BaseModel] = SearchKnowledgeBaseInput

        def _run(self, query: str, top_k: int = 6) -> str:
            from app.retrieval.query_engine import retrieve

            chunks = retrieve(query, top_k=top_k)
            if not chunks:
                return json.dumps({"query": query, "results": [], "note": "No relevant passages found."})
            return json.dumps({"query": query, "results": chunks}, ensure_ascii=False)

    return SearchKnowledgeBaseTool()


def get_search_tool():
    return _build_search_tool()
